"""Synthetic fault-injection tests for the V5.4 forward-test harness's
network-timeout hardening (lab copy ONLY — never deployed).

Coverage:
  1. Watchdog timeout: a hung vendor call is cut off at the request deadline
     and NEVER retried (exactly 1 invocation — no duplicate in-flight
     request); the symbol is marked degraded. A transient failure that
     actually raised keeps its single bounded retry.
  2. HTTP 429: Retry-After honored when usable; otherwise the cycle goes
     globally rate-limited and no further vendor requests are made.
  3. HTTP 5xx: transient failures get exactly one bounded retry.
  4. Empty/partial frames, malformed timestamps, missing OHLC columns:
     classified and deferred, never treated as "no data available".
  5. One missing universe symbol: new-entry decisions suppressed for the
     whole cycle (no partial-universe entries); open positions with valid
     data keep processing exits.
  6. One missing open-position symbol: exit_data_deferred, nothing
     invented, and chronological catch-up on recovery.
  7. Global rate limit: new vendor requests halted for the rest of the cycle.
  8. Degraded cycles always report coverage; never "NO SIGNALS".
  9. Strategy-rule immutability: importing/running the hardened copy
     leaves every live strategy file byte-identical.

Run:  python3 test_harness_hardening.py
"""
import hashlib
import json
import os
import sys
import tempfile
import threading
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import v54_forward_harness as H  # the LAB COPY, never the live file

# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

PASS = []
FAIL = []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name
          + (f" -- {detail}" if detail and not cond else ""))


def make_bars(n=80, start="2026-09-01", seed=7, tz="UTC"):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start=start, periods=n, freq="4h", tz=tz)
    base = 100.0 + np.cumsum(rng.normal(0, 0.6, n))
    df = pd.DataFrame({
        "Open": base,
        "High": base + np.abs(rng.normal(0, 0.4, n)),
        "Low": base - np.abs(rng.normal(0, 0.4, n)),
        "Close": base + rng.normal(0, 0.3, n),
        "Volume": rng.integers(1000, 9000, n),
    }, index=idx)
    df["High"] = df[["Open", "Close", "High"]].max(axis=1)
    df["Low"] = df[["Open", "Close", "Low"]].min(axis=1)
    return df


def make_safe_bars(n=80, start="2026-09-01", entry=100.0, tz="UTC"):
    """Deterministic bars that never touch stop=entry-2 or tp1=entry+3.

    Used for exit-path tests so positions stay open unless the test
    itself triggers an exit.
    """
    idx = pd.date_range(start=start, periods=n, freq="4h", tz=tz)
    drift = np.linspace(0, 1.2, n)
    base = entry + drift
    return pd.DataFrame({
        "Open": base,
        "High": base + 0.3,
        "Low": base - 0.3,
        "Close": base + 0.05,
        "Volume": 5000,
    }, index=idx)


def fresh_state():
    return {"runs": 0, "last_run": None, "seen_signal_ids": [],
            "pending": {}, "snapshots": {}, "positions": {},
            "close_logged": {}, "data_outages": {}}


def new_tracker():
    return H.ModeBTracker()


def new_log(tmpdir):
    return H.ForwardLog(os.path.join(tmpdir, "forward_test.jsonl"))


def fake_signal(sid, symbol, bar_start):
    entry = 100.0
    return {"signal_id": sid, "symbol": symbol, "v54_grade": "A",
            "entry": entry, "stop": entry - 2.0, "tp1": entry + 3.0,
            "signal_bar_start_at": bar_start.isoformat()}


def monkeypatch_qualified(monkey_rows):
    orig = H.eng.v54_qualified_signals
    H.eng.v54_qualified_signals = lambda rows: list(monkey_rows)
    return orig


def restore_qualified(orig):
    H.eng.v54_qualified_signals = orig


# --------------------------------------------------------------------------
# 1-3. hardened_call: timeout, 429, 5xx
# --------------------------------------------------------------------------

def test_watchdog_timeout_non_retriable():
    """A watchdog timeout (vendor call may still be alive in its daemon
    thread) must NEVER launch a second request: exactly 1 invocation, no
    retry counted, symbol degraded, entries suppressed."""
    calls = []
    release = threading.Event()

    def hung_forever():
        calls.append(1)
        release.wait(30)  # still alive long after the watchdog fires

    h = H.ProviderHealth(expected_symbols=["AAA"])
    t0 = time.monotonic()
    try:
        H.hardened_call("AAA", "primary", hung_forever, health=h,
                        deadline_s=0.5, retry_backoff_s=0.1)
        raised = None
    except H.DataUnavailable as exc:
        raised = exc
    finally:
        release.set()
    dt = time.monotonic() - t0
    check("watchdog timeout raises DataUnavailable", raised is not None)
    check("watchdog timeout classified as timeout",
          raised is not None and raised.reason == H.REASON_TIMEOUT,
          getattr(raised, "reason", None))
    check("watchdog timeout: NO second request (1 call)",
          len(calls) == 1, f"calls={len(calls)}")
    check("watchdog timeout: no retry counted", h.total_retries == 0,
          f"retries={h.total_retries}")
    check("watchdog timeout: bounded wall clock (<5s for 0.5s deadline)",
          dt < 5, f"dt={dt:.1f}s")
    check("watchdog timeout marks symbol degraded",
          h.symbols["AAA"].status == "degraded")
    check("watchdog timeout entries suppressed", h.entries_suppressed)


def test_raised_transient_still_retries_once():
    """A transient failure that actually RAISED (no live abandoned call)
    keeps the single bounded retry."""
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise ConnectionError("connection reset by peer")
        return "ok"

    h = H.ProviderHealth(expected_symbols=["BBB"])
    out = H.hardened_call("BBB", "primary", flaky, health=h,
                          deadline_s=2.0, retry_backoff_s=0.1)
    check("raised transient: one retry then success",
          out == "ok" and len(calls) == 2, f"calls={len(calls)}")
    check("raised transient: retry counted", h.total_retries == 1,
          f"retries={h.total_retries}")
    check("raised transient: symbol fresh",
          h.symbols["BBB"].status == "fresh")


def test_429_without_retry_after_trips_global():
    calls = []

    def limited():
        calls.append(1)
        raise RuntimeError("HTTP 429 Too Many Requests")

    h = H.ProviderHealth(expected_symbols=["AAA", "BBB"])
    try:
        H.hardened_call("AAA", "primary", limited, health=h, deadline_s=5)
        raised = None
    except H.RateLimited as exc:
        raised = exc
    check("429 raises RateLimited", isinstance(raised, H.RateLimited))
    check("429 trips global flag", h.global_rate_limited)
    check("429: no retry storm (1 call)", len(calls) == 1, f"calls={len(calls)}")
    # further vendor requests in the same cycle are refused, not attempted
    try:
        H.hardened_call("BBB", "primary", limited, health=h, deadline_s=5)
        refused = None
    except H.RateLimited as exc:
        refused = exc
    check("post-429 vendor requests refused immediately",
          refused is not None and len(calls) == 1, f"calls={len(calls)}")


class _FakeResp:
    def __init__(self, headers):
        self.headers = headers


class _HTTP429(Exception):
    def __init__(self, retry_after):
        super().__init__("HTTP Error 429: Too Many Requests")
        self.response = _FakeResp({"Retry-After": str(retry_after)})


def test_429_with_retry_after_retries_once_then_succeeds():
    calls = []
    good = make_bars(10)

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise _HTTP429(retry_after=0)
        return good

    h = H.ProviderHealth(expected_symbols=["AAA"])
    t0 = time.monotonic()
    out = H.hardened_call("AAA", "primary", flaky, health=h, deadline_s=5,
                          retry_backoff_s=0.1,
                          frame_validator=H.validate_primary_frame)
    dt = time.monotonic() - t0
    check("429+Retry-After: one retry then success", out is good and len(calls) == 2,
          f"calls={len(calls)}")
    check("429+Retry-After: no global flag", not h.global_rate_limited)
    check("429+Retry-After: symbol fresh", h.symbols["AAA"].status == "fresh")
    check("429+Retry-After: fast", dt < 6, f"dt={dt:.1f}s")


def test_5xx_single_bounded_retry():
    calls = []
    good = make_bars(10)

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise ConnectionError("503 Service Unavailable")
        return good

    h = H.ProviderHealth(expected_symbols=["AAA"])
    out = H.hardened_call("AAA", "primary", flaky, health=h, deadline_s=5,
                          retry_backoff_s=0.1,
                          frame_validator=H.validate_primary_frame)
    check("5xx: exactly one retry then success", out is good and len(calls) == 2,
          f"calls={len(calls)}")
    check("5xx: retry counted", h.total_retries == 1, f"retries={h.total_retries}")


def test_5xx_persistent_gives_up_after_one_retry():
    calls = []

    def dead():
        calls.append(1)
        raise ConnectionError("500 Internal Server Error")

    h = H.ProviderHealth(expected_symbols=["AAA"])
    try:
        H.hardened_call("AAA", "primary", dead, health=h, deadline_s=5,
                        retry_backoff_s=0.1)
        raised = None
    except H.DataUnavailable as exc:
        raised = exc
    check("persistent 5xx raises DataUnavailable", raised is not None)
    check("persistent 5xx: exactly 2 attempts", len(calls) == 2,
          f"calls={len(calls)}")
    check("persistent 5xx classified transient",
          raised is not None and raised.reason == H.REASON_TRANSIENT,
          getattr(raised, "reason", None))


# --------------------------------------------------------------------------
# 4. frame validation
# --------------------------------------------------------------------------

def test_frame_validation():
    good = make_bars(20)
    H.validate_primary_frame("AAA", good)  # must not raise
    check("valid frame passes validation", True)

    def expect(sym, df, reason):
        try:
            H.validate_primary_frame(sym, df)
            return None
        except H.DataUnavailable as exc:
            return exc.reason

    check("empty frame -> empty_frame",
          expect("E1", good.iloc[0:0], "") == H.REASON_EMPTY_FRAME)
    check("None frame -> empty_frame",
          expect("E2", None, "") == H.REASON_EMPTY_FRAME)
    bad_idx = good.copy()
    bad_idx.index = pd.RangeIndex(len(bad_idx))
    check("non-datetime index -> malformed_timestamps",
          expect("E3", bad_idx, "") == H.REASON_MALFORMED_TS)
    rev = good.iloc[::-1]
    check("non-monotonic index -> malformed_timestamps",
          expect("E4", rev, "") == H.REASON_MALFORMED_TS)
    noohlc = good.drop(columns=["Close"])
    check("missing OHLC column -> malformed_frame",
          expect("E5", noohlc, "") == H.REASON_MALFORMED_FRAME)
    nat = good.copy()
    nat.index = pd.DatetimeIndex([pd.NaT] * len(nat))
    check("NaT index -> malformed_timestamps",
          expect("E6", nat, "") == H.REASON_MALFORMED_TS)


def test_classify_failure():
    c = H.classify_failure
    check("429 text -> rate_limited",
          c("S", RuntimeError("429 Too Many Requests")) == H.REASON_RATE_LIMITED)
    check("delisted text -> unresolved_security_event",
          c("S", RuntimeError("symbol appears delisted")) == H.REASON_UNRESOLVED_SECURITY)
    check("timeout text -> timeout",
          c("S", TimeoutError("request timed out")) == H.REASON_TIMEOUT)
    check("500 text -> transient_error",
          c("S", ConnectionError("500 Internal Server Error")) == H.REASON_TRANSIENT)
    check("unknown text -> unknown_error",
          c("S", ValueError("weird")) == H.REASON_UNKNOWN)

# --------------------------------------------------------------------------
# 5-8. run_cycle integration: missing symbol, deferred exits, recovery
# --------------------------------------------------------------------------

def _ctx(tmpdir, health, frames, signals, market_frames=None):
    """Build a CycleContext over stub frames.

    frames: dict symbol -> DataFrame | Exception to raise from get_4h.
    signals: fake rows returned by eng.v54_qualified_signals.
    """
    def get_4h(symbol):
        v = frames.get(symbol, frames.get("*"))
        if isinstance(v, BaseException):
            raise v
        if v is None:
            raise H.DataUnavailable(symbol, H.REASON_EMPTY_FRAME, "stub empty")
        # the real run_once path records health inside the download wrapper;
        # the stub mirrors that bookkeeping.
        health.mark_fresh(symbol)
        return v

    def get_market_4h():
        if market_frames is None:
            return make_bars(20, seed=99)
        v = market_frames
        if isinstance(v, BaseException):
            raise v
        return v

    orig = monkeypatch_qualified(signals)
    ctx = H.CycleContext(scan_rows=[], regime={"regime": "UNKNOWN"},
                         get_4h=get_4h, get_market_4h=get_market_4h,
                         provider=health)
    return ctx, orig


def test_missing_universe_symbol_suppresses_entries_but_exits_continue():
    with tempfile.TemporaryDirectory() as td:
        bars_ok = make_safe_bars(80)
        bars_exit = make_safe_bars(80)
        health = H.ProviderHealth(expected_symbols=["NEW1", "EXIT1"])
        # scan-phase failure on NEW1 (partial universe)
        health.note("NEW1", H.REASON_TIMEOUT, "stub scan timeout")
        health.mark_fresh("EXIT1")

        state = fresh_state()
        log = new_log(td)
        tracker = new_tracker()
        # open position on EXIT1 entered at bar 40, last processed bar 50
        sig = fake_signal("SIG-EXIT1", "EXIT1", bars_exit.index[39])
        pos = tracker.open_position(sig, float(bars_exit.iloc[40]["Open"]),
                                    bars_exit.index[40].isoformat())
        for ts, bar in list(bars_exit.iloc[41:51].iterrows()):
            tracker.process_bar("SIG-EXIT1", {
                "bar_id": ts.isoformat(), "open": float(bar["Open"]),
                "high": float(bar["High"]), "low": float(bar["Low"]),
                "close": float(bar["Close"]), "scanner_state": None})
        last_before = pos["last_processed_bar"]

        new_sig = fake_signal("SIG-NEW1", "NEW1", bars_ok.index[70])
        ctx, orig = _ctx(td, health, {"EXIT1": bars_exit, "NEW1": bars_ok},
                         [new_sig])
        try:
            summary = H.run_cycle(ctx, state, log, tracker)
        finally:
            restore_qualified(orig)

        check("missing symbol: cycle DEGRADED", summary["cycle_status"] == H.CYCLE_DEGRADED)
        check("missing symbol: new entries suppressed", summary["entries_suppressed"])
        check("missing symbol: no pending entry staged for NEW1",
              not state["pending"], f"pending={state['pending']}")
        check("missing symbol: new signal not logged",
              "SIG-NEW1" not in state["seen_signal_ids"])
        check("open position on healthy symbol still advanced",
              pos["last_processed_bar"] != last_before,
              f"{last_before} -> {pos['last_processed_bar']}")
        check("coverage lists NEW1 degraded",
              any(d["symbol"] == "NEW1" for d in summary["coverage"]["degraded_symbols"]))
        check("never labeled NO SIGNALS",
              "NO SIGNALS" not in json.dumps(summary))


def test_open_position_gap_defers_never_invents():
    with tempfile.TemporaryDirectory() as td:
        bars = make_safe_bars(80)
        health = H.ProviderHealth(expected_symbols=["GAP1"])
        state = fresh_state()
        log = new_log(td)
        tracker = new_tracker()
        sig = fake_signal("SIG-GAP1", "GAP1", bars.index[39])
        pos = tracker.open_position(sig, float(bars.iloc[40]["Open"]),
                                    bars.index[40].isoformat())
        for ts, bar in list(bars.iloc[41:46].iterrows()):
            tracker.process_bar("SIG-GAP1", {
                "bar_id": ts.isoformat(), "open": float(bar["Open"]),
                "high": float(bar["High"]), "low": float(bar["Low"]),
                "close": float(bar["Close"]), "scanner_state": None})
        last_before = pos["last_processed_bar"]
        bars_before = list(pos["processed_bars"])

        gap_exc = H.DataUnavailable("GAP1", H.REASON_TIMEOUT, "stub timeout")
        ctx, orig = _ctx(td, health, {"GAP1": gap_exc}, [])
        try:
            summary = H.run_cycle(ctx, state, log, tracker)
        finally:
            restore_qualified(orig)

        check("gap: cycle DEGRADED", summary["cycle_status"] == H.CYCLE_DEGRADED)
        check("gap: exit_data_deferred recorded",
              any(d["kind"] == "exit" and d["signal_id"] == "SIG-GAP1"
                  for d in summary["data_deferred"]))
        check("gap: no bars invented", pos["processed_bars"] == bars_before)
        check("gap: last_processed_bar untouched",
              pos["last_processed_bar"] == last_before)
        check("gap: position still open", pos["status"] != "closed")
        check("gap: no exit synthesized", pos.get("exit") is None)
        # audit log carries the deferral
        events = log.get_events("SIG-GAP1")
        check("gap: log has exit_data_deferred event",
              any(ev.get("event") == "exit_data_deferred" for ev in events))
        check("gap: outage preserved in state",
              "GAP1" in state.get("data_outages", {}))


def test_outage_recovery_catches_up_chronologically():
    with tempfile.TemporaryDirectory() as td:
        bars = make_safe_bars(40)  # small: 5 setup + 14 catch-up < 30-bar cap
        health = H.ProviderHealth(expected_symbols=["REC1"])
        state = fresh_state()
        log = new_log(td)
        tracker = new_tracker()
        sig = fake_signal("SIG-REC1", "REC1", bars.index[19])
        pos = tracker.open_position(sig, float(bars.iloc[20]["Open"]),
                                    bars.index[20].isoformat())
        for ts, bar in list(bars.iloc[21:26].iterrows()):
            tracker.process_bar("SIG-REC1", {
                "bar_id": ts.isoformat(), "open": float(bar["Open"]),
                "high": float(bar["High"]), "low": float(bar["Low"]),
                "close": float(bar["Close"]), "scanner_state": None})
        n_before = len(pos["processed_bars"])

        # cycle 1: outage
        gap_exc = H.DataUnavailable("REC1", H.REASON_TIMEOUT, "stub outage")
        ctx, orig = _ctx(td, health, {"REC1": gap_exc}, [])
        try:
            s1 = H.run_cycle(ctx, state, log, tracker)
        finally:
            restore_qualified(orig)
        check("recovery: outage cycle deferred",
              any(d["signal_id"] == "SIG-REC1" for d in s1["data_deferred"]))
        check("recovery: no bars processed during outage",
              len(pos["processed_bars"]) == n_before)

        # cycle 2: recovery — full frame incl. the missed bars
        health2 = H.ProviderHealth(expected_symbols=["REC1"])
        health2.mark_fresh("REC1")
        ctx2, orig2 = _ctx(td, health2, {"REC1": bars}, [])
        try:
            s2 = H.run_cycle(ctx2, state, log, tracker)
        finally:
            restore_qualified(orig2)
        new_ids = pos["processed_bars"][n_before:]
        expected_ids = [ts.isoformat() for ts in bars.iloc[26:].index]
        check("recovery: every missed bar processed",
              new_ids == expected_ids,
              f"got {len(new_ids)}, want {len(expected_ids)}")
        check("recovery: chronological order",
              new_ids == sorted(new_ids))
        check("recovery: cycle 2 not degraded by this symbol",
              not any(d["symbol"] == "REC1"
                      for d in s2["coverage"]["degraded_symbols"]))
        events = log.get_events("SIG-REC1")
        rec = [ev for ev in events if ev.get("event") == "data_outage_recovered"]
        check("recovery: audit event preserved",
              len(rec) == 1 and rec[0]["bars_caught_up"] == len(expected_ids),
              str(rec[:1]))
        check("recovery: outage cleared from state",
              "REC1" not in state.get("data_outages", {}))


def test_empty_frame_defers():
    with tempfile.TemporaryDirectory() as td:
        health = H.ProviderHealth(expected_symbols=["E1"])
        state = fresh_state()
        log = new_log(td)
        tracker = new_tracker()
        bars = make_safe_bars(80)
        sig = fake_signal("SIG-E1", "E1", bars.index[39])
        pos = tracker.open_position(sig, float(bars.iloc[40]["Open"]),
                                    bars.index[40].isoformat())
        ctx, orig = _ctx(td, health, {"E1": bars.iloc[0:0]}, [])
        try:
            summary = H.run_cycle(ctx, state, log, tracker)
        finally:
            restore_qualified(orig)
        check("empty frame: deferred, not crashed",
              any(d["signal_id"] == "SIG-E1" and d["reason"] == H.REASON_EMPTY_FRAME
                  for d in summary["data_deferred"]))
        check("empty frame: cycle DEGRADED",
              summary["cycle_status"] == H.CYCLE_DEGRADED)


def test_malformed_timestamps_defer():
    with tempfile.TemporaryDirectory() as td:
        health = H.ProviderHealth(expected_symbols=["M1"])
        state = fresh_state()
        log = new_log(td)
        tracker = new_tracker()
        bars = make_safe_bars(80)
        bad = bars.copy()
        bad.index = pd.RangeIndex(len(bad))
        sig = fake_signal("SIG-M1", "M1", bars.index[39])
        pos = tracker.open_position(sig, float(bars.iloc[40]["Open"]),
                                    bars.index[40].isoformat())
        ctx, orig = _ctx(td, health, {"M1": bad}, [])
        try:
            summary = H.run_cycle(ctx, state, log, tracker)
        finally:
            restore_qualified(orig)
        check("malformed ts: deferred with malformed_timestamps",
              any(d["signal_id"] == "SIG-M1" and d["reason"] == H.REASON_MALFORMED_TS
                  for d in summary["data_deferred"]))
        check("malformed ts: no exit synthesized", pos.get("exit") is None)


def test_unresolved_security_event_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        bars = make_safe_bars(80)
        health = H.ProviderHealth(expected_symbols=["DEL1", "OK1"])
        health.note("DEL1", H.REASON_UNRESOLVED_SECURITY,
                    "possibly delisted per vendor message")
        health.mark_fresh("OK1")
        state = fresh_state()
        log = new_log(td)
        tracker = new_tracker()
        sig = fake_signal("SIG-DEL1", "DEL1", bars.index[39])
        pos = tracker.open_position(sig, float(bars.iloc[40]["Open"]),
                                    bars.index[40].isoformat())
        ctx, orig = _ctx(td, health, {"DEL1": bars, "OK1": bars}, [])
        try:
            summary = H.run_cycle(ctx, state, log, tracker)
        finally:
            restore_qualified(orig)
        check("delist: cycle DEGRADED", summary["cycle_status"] == H.CYCLE_DEGRADED)
        check("delist: entry suppressed", summary["entries_suppressed"])
        check("delist: deferred, position kept",
              pos.get("status") != "closed" and pos.get("exit") is None)
        check("delist: no -0R close synthesized",
              not any(c.get("signal_id") == "SIG-DEL1" for c in summary["closed"]))
        check("delist: surfaced in coverage",
              "DEL1" in summary["coverage"]["unresolved_security_events"])


def test_global_rate_limit_halts_new_requests():
    with tempfile.TemporaryDirectory() as td:
        health = H.ProviderHealth(expected_symbols=["R1", "R2"])
        health.set_global_rate_limited("429 without Retry-After on scan")
        state = fresh_state()
        log = new_log(td)
        tracker = new_tracker()
        requested = []

        def get_4h(symbol):
            requested.append(symbol)
            raise AssertionError("no vendor request may be attempted")

        ctx = H.CycleContext(scan_rows=[], regime={"regime": "UNKNOWN"},
                             get_4h=get_4h,
                             get_market_4h=lambda: make_bars(5),
                             provider=health)
        orig = monkeypatch_qualified([])
        try:
            summary = H.run_cycle(ctx, state, log, tracker)
        finally:
            restore_qualified(orig)
        check("global 429: entries suppressed", summary["entries_suppressed"])
        check("global 429: DEGRADED", summary["cycle_status"] == H.CYCLE_DEGRADED)
        check("global 429: no vendor requests attempted", requested == [],
              f"requested={requested}")
        check("global 429: coverage says rate_limited",
              summary["coverage"]["global_provider_status"] == "rate_limited")


def test_healthy_cycle_no_suppression():
    with tempfile.TemporaryDirectory() as td:
        bars = make_safe_bars(80)
        health = H.ProviderHealth(expected_symbols=["H1"])
        state = fresh_state()
        log = new_log(td)
        tracker = new_tracker()
        sig = fake_signal("SIG-H1", "H1", bars.index[60])
        ctx, orig = _ctx(td, health, {"H1": bars}, [sig])
        try:
            summary = H.run_cycle(ctx, state, log, tracker)
        finally:
            restore_qualified(orig)
        check("healthy: not suppressed", not summary["entries_suppressed"])
        check("healthy: status HEALTHY", summary["cycle_status"] == H.CYCLE_HEALTHY)
        check("healthy: signal staged", "SIG-H1" in state["seen_signal_ids"])
        check("healthy: pending entry opened into a position",
              "SIG-H1" in tracker.positions
              and tracker.positions["SIG-H1"]["status"] != "closed"
              and not state["pending"],
              f"pending={state['pending']}")
        check("healthy: coverage ok",
              summary["coverage"]["global_provider_status"] == "ok")


def test_replay_path_without_provider():
    # provider=None keeps the pre-hardening behavior for replay tooling.
    with tempfile.TemporaryDirectory() as td:
        bars = make_bars(80, seed=81)
        state = fresh_state()
        log = new_log(td)
        tracker = new_tracker()
        sig = fake_signal("SIG-RP", "RP1", bars.index[60])
        ctx = H.CycleContext(scan_rows=[], regime={"regime": "UNKNOWN"},
                             get_4h=lambda s: bars,
                             get_market_4h=lambda: make_bars(5),
                             provider=None)
        orig = monkeypatch_qualified([sig])
        try:
            summary = H.run_cycle(ctx, state, log, tracker)
        finally:
            restore_qualified(orig)
        check("replay: no provider -> no suppression",
              not summary["entries_suppressed"])
        check("replay: signal staged", "SIG-RP" in state["seen_signal_ids"])


def test_degraded_never_no_signals_label():
    with tempfile.TemporaryDirectory() as td:
        health = H.ProviderHealth(expected_symbols=["Z1"])
        health.note("Z1", H.REASON_TIMEOUT, "stub")
        state = fresh_state()
        log = new_log(td)
        tracker = new_tracker()
        ctx, orig = _ctx(td, health, {}, [])
        try:
            summary = H.run_cycle(ctx, state, log, tracker)
        finally:
            restore_qualified(orig)
        blob = json.dumps(summary)
        check("degraded: zero signals still DEGRADED",
              summary["cycle_status"] == H.CYCLE_DEGRADED)
        check("degraded: coverage block present", "coverage" in summary)
        check("degraded: no 'NO SIGNALS' text", "NO SIGNALS" not in blob)

# --------------------------------------------------------------------------
# 9. atomic writes, patch hygiene, immutability
# --------------------------------------------------------------------------

def test_atomic_write_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "sub", "summary.json")
        payload = {"a": 1, "cycle_status": H.CYCLE_DEGRADED}
        H.write_cycle_summary_atomic(payload, path=p)
        check("atomic write: file exists", os.path.exists(p))
        check("atomic write: no .tmp left", not os.path.exists(p + ".tmp"))
        check("atomic write: valid JSON round-trip",
              json.load(open(p)) == payload)
        # never raises, even on a bad path
        try:
            H.write_cycle_summary_atomic(payload, path="/nonexistent-dir-xyz/f.json")
            ok = True
        except Exception:
            ok = False
        check("summary write never raises", ok)


def test_hardened_downloads_restores_patches():
    m53 = H.eng.m53
    before = (m53.download_data, m53.download_confirmation_data,
              m53.premarket_fields)
    h = H.ProviderHealth(expected_symbols=["X"])
    with H.hardened_downloads(h):
        during = (m53.download_data, m53.download_confirmation_data,
                  m53.premarket_fields)
        check("downloads patched in-context",
              all(a is not b for a, b in zip(during, before)))
    after = (m53.download_data, m53.download_confirmation_data,
             m53.premarket_fields)
    check("downloads restored after context", after == before)


def test_auxiliary_failures_never_gate():
    # confirmation/premarket failures are tracked but never suppress entries
    h = H.ProviderHealth(expected_symbols=["AUX1"])
    h.note_aux("AUX1", "auxiliary", H.REASON_TIMEOUT)
    check("aux failures do not suppress entries", not h.entries_suppressed)
    cov = h.coverage_block()
    check("aux failures reported in coverage",
          any(f["symbol"] == "AUX1" for f in cov["auxiliary_failures"]))
    check("aux failures excluded from degraded_symbols",
          not any(d["symbol"] == "AUX1" for d in cov["degraded_symbols"]))


def test_budget_exhaustion_aborts_new_signal_staging():
    with tempfile.TemporaryDirectory() as td:
        health = H.ProviderHealth(expected_symbols=["B1"], cycle_deadline_s=0.0)
        state = fresh_state()
        log = new_log(td)
        tracker = new_tracker()
        bars = make_bars(80, seed=91)
        sig = fake_signal("SIG-B1", "B1", bars.index[60])
        ctx, orig = _ctx(td, health, {"B1": bars}, [sig])
        try:
            summary = H.run_cycle(ctx, state, log, tracker)
        finally:
            restore_qualified(orig)
        check("budget exhausted: entries suppressed", summary["entries_suppressed"])
        check("budget exhausted: no signal staged",
              "SIG-B1" not in state["seen_signal_ids"])
        check("budget exhausted: DEGRADED", summary["cycle_status"] == H.CYCLE_DEGRADED)


STRATEGY_FILES = [
    "masterscanner_api.py", "v54_engine.py", "v54_rules.py",
    "scanner_rules.py", "v54_exit_tracker.py", "v54_universe_x2.py",
    "hybrid_exit_test.py", "v54_forward_log.py",
]


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def test_strategy_files_untouched():
    before = {f: _sha(os.path.join(REPO, f)) for f in STRATEGY_FILES}
    # run a full healthy + degraded cycle to prove no in-process mutation
    with tempfile.TemporaryDirectory() as td:
        bars = make_bars(80, seed=101)
        for seed_sym, note_it in (("S1", False), ("S2", True)):
            health = H.ProviderHealth(expected_symbols=[seed_sym])
            if note_it:
                health.note(seed_sym, H.REASON_TIMEOUT, "stub")
            else:
                health.mark_fresh(seed_sym)
            state = fresh_state()
            log = new_log(td)
            tracker = new_tracker()
            ctx, orig = _ctx(td, health, {seed_sym: bars}, [])
            try:
                H.run_cycle(ctx, state, log, tracker)
            finally:
                restore_qualified(orig)
        # hardened_downloads patch/restore cycle
        h = H.ProviderHealth(expected_symbols=["Z"])
        with H.hardened_downloads(h):
            pass
    after = {f: _sha(os.path.join(REPO, f)) for f in STRATEGY_FILES}
    changed = [f for f in STRATEGY_FILES if before[f] != after[f]]
    check("strategy files byte-identical after hardened cycles", not changed,
          f"changed={changed}")
    # eng still exposes the original strategy callables (no left-behind patch)
    check("eng.m53.download_data restored",
          H.eng.m53.download_data.__name__ == "download_data")


# --------------------------------------------------------------------------
# runner
# --------------------------------------------------------------------------

def main():
    tests = [
        test_watchdog_timeout_non_retriable,
        test_raised_transient_still_retries_once,
        test_429_without_retry_after_trips_global,
        test_429_with_retry_after_retries_once_then_succeeds,
        test_5xx_single_bounded_retry,
        test_5xx_persistent_gives_up_after_one_retry,
        test_frame_validation,
        test_classify_failure,
        test_missing_universe_symbol_suppresses_entries_but_exits_continue,
        test_open_position_gap_defers_never_invents,
        test_outage_recovery_catches_up_chronologically,
        test_empty_frame_defers,
        test_malformed_timestamps_defer,
        test_unresolved_security_event_fails_closed,
        test_global_rate_limit_halts_new_requests,
        test_healthy_cycle_no_suppression,
        test_replay_path_without_provider,
        test_degraded_never_no_signals_label,
        test_atomic_write_roundtrip,
        test_hardened_downloads_restores_patches,
        test_auxiliary_failures_never_gate,
        test_budget_exhaustion_aborts_new_signal_staging,
        test_strategy_files_untouched,
    ]
    for t in tests:
        print(f"\n--- {t.__name__} ---")
        try:
            t()
        except Exception as exc:
            FAIL.append(t.__name__)
            print(f"FAIL {t.__name__} -- raised {type(exc).__name__}: {exc}")
    print(f"\n==== {len(PASS)} passed, {len(FAIL)} failed ====")
    if FAIL:
        print("FAILED:", FAIL)
        sys.exit(1)


if __name__ == "__main__":
    main()
