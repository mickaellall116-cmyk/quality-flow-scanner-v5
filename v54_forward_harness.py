"""V5.4 forward-test harness — runs after each completed 4H bar.

One cycle (run_cycle):
1. Scan the frozen forward-test universe (UX51 — the research universe
   from hybrid_exit_test.py, so forward results stay comparable).
2. New qualified signals -> log the snapshot, stage a pending entry.
3. Pending entries with a new completed bar -> open at that bar's open
   (research convention: next-bar-open entry).
4. Open positions -> walk every new completed bar in order through the
   Mode B tracker, with the V5.3 scanner state per bar (EXIT detection).
5. Closes -> append the frozen-schema summary to the forward log.
6. Persist state; write latest_v54_signals.json (separate namespace).

One position per symbol: a new signal for a symbol with an open or
pending position is logged with a skip event, never double-traded.
Idempotent: reruns are safe (processed-bar sets, seen-signal ids).

Nothing here modifies V5.3.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

import hybrid_exit_test  # frozen UX51 universe (import-time safe: main() guarded)
import v54_universe_x2 as ux2  # frozen X2 universe (added 2026-09-15, day 1)
import v54_engine as eng
from v54_exit_tracker import ModeBTracker, close_summary
from v54_forward_log import ForwardLog

UX51_UNIVERSE: List[str] = list(hybrid_exit_test.UNIVERSE_X)
FORWARD_UNIVERSE: List[str] = UX51_UNIVERSE + list(ux2.UNIVERSE_X2)
THEME_MAP: Dict[str, str] = (
    {s: "Forward-UX51" for s in UX51_UNIVERSE}
    | {s: "Forward-X2" for s in ux2.UNIVERSE_X2}
)
COHORT_SIZES = {"UX51": len(UX51_UNIVERSE), "X2": len(ux2.UNIVERSE_X2)}
INTERVAL, PERIOD = "4h", "180d"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(BASE_DIR, "v54_forward", "state.json")
LOG_PATH = os.path.join(BASE_DIR, "v54_forward", "forward_test.jsonl")
OUTPUT_PATH = os.path.join(BASE_DIR, "latest_v54_signals.json")

# ---- AI Observer (AI-OBS-v1): observational only, never touches V5.4 ----
AI_OBS_VERSION = "AI-OBS-v1"
AI_OBS_PROMPT_VERSION = "v1"
AI_OBS_PROMPT_PATH = os.path.join(BASE_DIR, "v54_ai_observer_prompt_v1.md")
OBSERVER_LOG_PATH = os.path.join(BASE_DIR, "v54_forward", "ai_observer.jsonl")
OBSERVER_EXPORT_PATH = os.path.join(BASE_DIR, "forward_test",
                                     "v54_ai_observer.json")

# Raw market/structural facts the observer may see (allowlist). Model
# judgments — V5.4 grade fields, any score — are excluded by construction
# so the observer's read stays independent of the frozen grading system.
_OBS_RAW_FIELDS = [
    "symbol", "theme", "timeframe",
    "signal_bar_start_at", "signal_bar_close_at",
    "state", "entry", "protection",
    "price", "stop", "tp1", "risk_reward",
    "buy_zone", "above_vwap",
    "ema9", "ema21", "ema55", "ema200",
    "adx", "rel_vol",
    "market_gate", "market_regime",
    "daily_trend", "weekly_trend",
    "confirmation_15m", "confirmation_15m_at", "confirmation_15m_rel_vol",
    "pm_high", "pm_low", "pm_volume", "pm_vwap", "pm_last",
    "pm_gap_pct", "pm_range_pct", "pm_read",
    "v53_state", "v53_entry", "v53_would_veto",
    "v54_rule_version", "v54_scanner_version",
]

# Judgment fields that must never reach the observer (defense in depth;
# the allowlist above already excludes them).
_OBS_EXCLUDED_KEYS = {
    "v54_grade", "v54_grade_label", "v54_grade_reasons", "v54_eligible",
    "score", "v53_score", "v53_rank_score",
}


# ---------------------------------------------------------------------------
# Network-timeout hardening (infrastructure only — no strategy changes).
#
# Guards implemented (per 2026-09-28 adversarial review; MAYBE/REDLINE ->
# PASS only if all adopted):
#  1. No partial-universe new-entry decisions: any expected symbol lacking
#     fresh primary data => cycle DEGRADED, new entries suppressed. An
#     unknown symbol is never reinterpreted as "no signal".
#  2. Open positions: exits keep processing on valid data; missing data =>
#     exit_data_deferred (never assumed, never invented); chronological
#     catch-up on recovery; outage preserved in the audit log.
#  3. 429: honor Retry-After within budget; otherwise record
#     provider_rate_limited and stop further vendor requests for the cycle
#     (treated as global). Watchdog timeout: never retried (the vendor call
#     may still be alive). Other transient timeout/5xx that actually
#     returned or raised: at most one bounded retry.
#  4. Bounded runtime: 45s per-request ceiling, 10-minute cycle ceiling.
#  5. Coverage as first-class output; a degraded cycle is never "NO SIGNALS".
#  6. Delisting/corporate-action ambiguity fails closed: unresolved
#     security-event state; symbol never removed; no -0R synthesized.
#  7. Atomic state/output writes; finally-safe summary artifact.
#  8. Synthetic fault tests live in test_fault_injection.py (not deployed).
#
# Nothing here changes entries, exits, grades, ranking, market gate, or the
# observer. Strategy modules are imported read-only and never modified; the
# download wrappers below patch eng.m53 attributes in-process for the
# duration of one cycle only (restored in `finally`).
# ---------------------------------------------------------------------------

HARD_REQUEST_DEADLINE_S = 45.0
HARD_CYCLE_DEADLINE_S = 600.0
HARD_RETRY_BACKOFF_S = 5.0
HARD_MAX_RETRIES = 1
HARD_SIDECAR_DEADLINE_S = 120.0

CYCLE_HEALTHY = "HEALTHY"
CYCLE_DEGRADED = "DEGRADED"
CYCLE_ABORTED = "ABORTED"

REASON_TIMEOUT = "timeout"
REASON_TRANSIENT = "transient_error"
REASON_RATE_LIMITED = "rate_limited"
REASON_EMPTY_FRAME = "empty_frame"
REASON_MALFORMED_FRAME = "malformed_frame"
REASON_MALFORMED_TS = "malformed_timestamps"
REASON_UNRESOLVED_SECURITY = "unresolved_security_event"
REASON_BUDGET_EXHAUSTED = "cycle_budget_exhausted"
REASON_NOT_ATTEMPTED = "not_attempted"
REASON_UNKNOWN = "unknown_error"


class DataUnavailable(Exception):
    """Typed transport/data failure. Never a strategy signal."""

    def __init__(self, symbol: str, reason: str, detail: str = ""):
        super().__init__(f"{symbol}: {reason} {detail}".strip())
        self.symbol = symbol
        self.reason = reason
        self.detail = detail


class RateLimited(DataUnavailable):
    """HTTP 429. May trip the cycle-global rate-limit flag."""


@dataclass
class SymbolHealth:
    symbol: str
    status: str = "fresh"          # fresh | degraded
    reason: str = ""
    detail: str = ""
    retries: int = 0
    auxiliary: bool = False        # confirmation/premarket: tracked, never gating


class ProviderHealth:
    """Per-cycle vendor/data health accumulator (Guard 5)."""

    def __init__(self, expected_symbols: List[str],
                 cycle_deadline_s: float = HARD_CYCLE_DEADLINE_S):
        self.t0 = time.monotonic()
        self.cycle_deadline_s = cycle_deadline_s
        self.expected_symbols = list(expected_symbols)
        self.symbols: Dict[str, SymbolHealth] = {}
        self.global_rate_limited = False
        self.rate_limit_detail = ""
        self.total_retries = 0
        self.market_gap = ""
        self.aux_failures: List[Dict[str, str]] = []

    def remaining_budget_s(self) -> float:
        return self.cycle_deadline_s - (time.monotonic() - self.t0)

    def _get(self, symbol: str) -> SymbolHealth:
        h = self.symbols.get(symbol)
        if h is None:
            h = self.symbols[symbol] = SymbolHealth(symbol)
        return h

    def mark_fresh(self, symbol: str) -> None:
        h = self._get(symbol)
        h.status = "fresh"
        h.reason = ""
        h.detail = ""

    def note(self, symbol: str, reason: str, detail: str = "") -> None:
        h = self._get(symbol)
        h.status = "degraded"
        h.reason = reason
        h.detail = detail[:200]

    def note_aux(self, symbol: str, kind: str, reason: str) -> None:
        self.aux_failures.append({"symbol": symbol, "kind": kind,
                                  "reason": reason})

    def set_global_rate_limited(self, detail: str) -> None:
        self.global_rate_limited = True
        self.rate_limit_detail = detail[:200]

    def note_market_gap(self, reason: str) -> None:
        self.market_gap = reason[:200]

    @property
    def primary_failures(self) -> Dict[str, SymbolHealth]:
        return {s: h for s, h in self.symbols.items()
                if h.status == "degraded" and not h.auxiliary}

    def finalize(self) -> None:
        """Symbols never attempted count as failures (Guard 1 strictness)."""
        for s in self.expected_symbols:
            if s not in self.symbols:
                self.note(s, REASON_NOT_ATTEMPTED,
                          "no vendor request completed this cycle")

    @property
    def entries_suppressed(self) -> bool:
        return bool(self.primary_failures) or self.global_rate_limited

    def suppression_reason(self) -> str:
        bits = []
        pf = self.primary_failures
        if pf:
            names = sorted(pf)[:5]
            extra = f" (+{len(pf) - 5} more)" if len(pf) > 5 else ""
            bits.append(f"{len(pf)} symbol(s) lack fresh primary data: "
                        f"{', '.join(names)}{extra}")
        if self.global_rate_limited:
            bits.append(f"provider rate-limited ({self.rate_limit_detail})")
        return "; ".join(bits) or "n/a"

    @property
    def global_status(self) -> str:
        if self.global_rate_limited:
            return "rate_limited"
        if self.primary_failures:
            return "degraded"
        return "ok"

    def coverage_block(self, open_symbols=(),
                       entries_suppressed: bool = False) -> Dict[str, Any]:
        degraded = [{"symbol": s, "reason": h.reason, "detail": h.detail}
                    for s, h in sorted(self.symbols.items())
                    if h.status == "degraded" and not h.auxiliary]
        fresh = sorted(s for s, h in self.symbols.items()
                       if h.status == "fresh")
        return {
            "expected_symbols": len(self.expected_symbols),
            "fresh_symbols": len(fresh),
            "degraded_symbols": degraded,
            "unresolved_security_events": [
                d["symbol"] for d in degraded
                if d["reason"] == REASON_UNRESOLVED_SECURITY],
            "open_position_data_gaps": sorted(
                set(open_symbols) & {d["symbol"] for d in degraded}),
            "global_provider_status": self.global_status,
            "market_data_gap": self.market_gap,
            "retries": self.total_retries,
            "cycle_duration_s": round(time.monotonic() - self.t0, 1),
            "entries_suppressed": entries_suppressed,
            "auxiliary_failures": self.aux_failures,
        }


_RATE_PAT = re.compile(r"429|too many requests|ratelimit|rate[_ ]?limit",
                       re.IGNORECASE)
_DELIST_PAT = re.compile(r"delist", re.IGNORECASE)
_TIMEOUT_PAT = re.compile(r"timeout|timed out|deadline", re.IGNORECASE)
_TRANSIENT_PAT = re.compile(
    r"connect|connection|50[0234]|bad gateway|service unavailable|"
    r"gateway timeout|temporar|eof|reset by peer", re.IGNORECASE)


def classify_failure(symbol: str, exc: Optional[BaseException],
                     log_text: str = "") -> str:
    """Map a transport failure to a stable reason string."""
    text = f"{type(exc).__name__}: {exc} {log_text}" if exc is not None \
        else log_text
    if _RATE_PAT.search(text):
        return REASON_RATE_LIMITED
    if _DELIST_PAT.search(text):
        return REASON_UNRESOLVED_SECURITY
    if _TIMEOUT_PAT.search(text):
        return REASON_TIMEOUT
    if _TRANSIENT_PAT.search(text):
        return REASON_TRANSIENT
    return REASON_UNKNOWN


def validate_primary_frame(symbol: str, df: Any) -> None:
    """Structural validation for a primary 4H frame (Guard 8e).

    Raises DataUnavailable on empty/malformed frames. Never invents bars.
    Thin-but-valid history is NOT malformed — the frozen engine decides
    what is classifiable.
    """
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        raise DataUnavailable(symbol, REASON_EMPTY_FRAME,
                              "empty frame returned")
    if not isinstance(df, pd.DataFrame):
        raise DataUnavailable(symbol, REASON_MALFORMED_FRAME,
                              f"unexpected type {type(df).__name__}")
    idx = df.index
    if not isinstance(idx, pd.DatetimeIndex):
        raise DataUnavailable(symbol, REASON_MALFORMED_TS,
                              f"index type {type(idx).__name__}")
    if len(idx) == 0 or idx.hasnans:
        raise DataUnavailable(symbol, REASON_MALFORMED_TS,
                              "empty or NaT index")
    if not idx.is_monotonic_increasing:
        raise DataUnavailable(symbol, REASON_MALFORMED_TS,
                              "non-monotonic index")
    for col in ("Open", "High", "Low", "Close"):
        if col not in df.columns:
            raise DataUnavailable(symbol, REASON_MALFORMED_FRAME,
                                  f"missing column {col}")


class _WatchdogTimeout(TimeoutError):
    """Watchdog deadline exceeded while the vendor thread was still alive.

    The underlying vendor call may STILL BE IN FLIGHT (an abandoned daemon
    thread cannot be killed). It must therefore NEVER be retried: a retry
    would put two live requests for the same symbol on the wire and amplify
    the rate limiting this hardening is meant to contain. Only transient
    failures that actually returned or raised (no live abandoned call) are
    retriable.
    """


def _call_with_deadline(fn, args, kwargs, deadline_s: float):
    """Run fn in a daemon thread; (True, result) or (False, exception).

    On watchdog timeout the returned exception is a _WatchdogTimeout, so
    callers can distinguish "vendor call may still be alive" (non-retriable)
    from "vendor call raised" (retriable if transient). An abandoned thread
    cannot be killed (documented); it is daemonic so it never blocks
    process exit.
    """
    box: Dict[str, Any] = {}

    def _target():
        try:
            box["result"] = fn(*args, **kwargs)
        except BaseException as exc:  # noqa: BLE001 - transport parity
            box["exc"] = exc

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(deadline_s)
    if t.is_alive():
        return False, _WatchdogTimeout(
            f"watchdog deadline {deadline_s:g}s exceeded; vendor call may "
            f"still be in flight (abandoned daemon thread, non-retriable)")
    if "exc" in box:
        return False, box["exc"]
    return True, box.get("result")


@contextlib.contextmanager
def _capture_yfinance_logs():
    """Collect yfinance log records emitted during one call (for 429 /
    delist classification — yfinance often returns empty frames instead
    of raising)."""
    records: List[str] = []

    class _H(logging.Handler):
        def emit(self, rec):
            try:
                records.append(rec.getMessage())
            except Exception:
                pass

    logger = logging.getLogger("yfinance")
    h = _H()
    logger.addHandler(h)
    try:
        yield records
    finally:
        logger.removeHandler(h)


def _retry_after_s(exc: BaseException) -> Optional[int]:
    """Best-effort Retry-After extraction (seconds)."""
    resp = getattr(exc, "response", None)
    headers = getattr(resp, "headers", None) or {}
    try:
        ra = headers.get("Retry-After")
        return int(ra) if ra is not None else None
    except (TypeError, ValueError, AttributeError):
        return None


def hardened_call(symbol: str, kind: str, fn: Callable, *args,
                  health: ProviderHealth,
                  deadline_s: float = HARD_REQUEST_DEADLINE_S,
                  allow_retry: bool = True,
                  retry_backoff_s: float = HARD_RETRY_BACKOFF_S,
                  frame_validator: Optional[Callable] = None,
                  **kwargs):
    """Bounded, classified vendor call (Guards 3 + 4).

    kind: "primary" (gating) or "auxiliary" (tracked, never gating).
    Raises DataUnavailable / RateLimited on failure. At most one bounded
    retry for transient faults that actually returned or raised; a WATCHDOG
    timeout (vendor call may still be alive in its daemon thread) is NEVER
    retried. A 429 without a usable Retry-After trips the cycle-global
    rate-limit flag (primary only) so no further vendor requests are made
    this cycle.
    """
    if health.global_rate_limited:
        raise RateLimited(symbol, REASON_RATE_LIMITED,
                          "global rate limit already hit this cycle")
    if health.remaining_budget_s() <= 0:
        raise DataUnavailable(symbol, REASON_BUDGET_EXHAUSTED,
                              "cycle wall-clock budget exhausted")
    attempt = 0
    while True:
        with _capture_yfinance_logs() as logs:
            ok, res = _call_with_deadline(fn, args, kwargs, deadline_s)
        log_text = " ".join(logs[-8:])
        exc: Optional[BaseException] = None
        reason = REASON_UNKNOWN
        if not ok:
            # Thread-level timeout, or the call raised inside the thread.
            reason = classify_failure(symbol, res, log_text)
            exc = res if isinstance(res, BaseException) else TimeoutError(str(res))
        elif frame_validator is not None:
            try:
                frame_validator(symbol, res)
            except DataUnavailable as ve:
                # Sniff logs for a sharper cause on empty frames.
                sniffed = (classify_failure(symbol, None, log_text)
                           if ve.reason == REASON_EMPTY_FRAME else REASON_UNKNOWN)
                reason = sniffed if sniffed != REASON_UNKNOWN else ve.reason
                exc = DataUnavailable(symbol, reason, ve.detail)
        if exc is None:
            if kind != "auxiliary":
                health.mark_fresh(symbol)
            return res
        # ---- failure path ----
        retry_after = (_retry_after_s(exc) if reason == REASON_RATE_LIMITED
                       else None)
        if reason == REASON_RATE_LIMITED and retry_after is None:
            if kind != "auxiliary":
                health.set_global_rate_limited(f"{symbol}: {exc}"[:200])
                raise RateLimited(symbol, REASON_RATE_LIMITED, str(exc)[:200])
            health.note_aux(symbol, kind, reason)
            raise DataUnavailable(symbol, reason, str(exc)[:200])
        transient = (not isinstance(exc, _WatchdogTimeout)
                     and (reason in (REASON_TIMEOUT, REASON_TRANSIENT)
                          or (reason == REASON_RATE_LIMITED
                              and retry_after is not None)))
        if allow_retry and attempt < HARD_MAX_RETRIES and transient:
            sleep_s = (retry_after if retry_after is not None
                       else retry_backoff_s)
            if health.remaining_budget_s() >= sleep_s + deadline_s:
                time.sleep(sleep_s)
                health.total_retries += 1
                attempt += 1
                continue
        if kind == "auxiliary":
            health.note_aux(symbol, kind, reason)
            raise DataUnavailable(symbol, reason, str(exc)[:200])
        health.note(symbol, reason, str(exc)[:200])
        if reason == REASON_RATE_LIMITED:
            raise RateLimited(symbol, reason, str(exc)[:200])
        raise DataUnavailable(symbol, reason, str(exc)[:200])


@contextlib.contextmanager
def hardened_downloads(health: ProviderHealth):
    """Patch eng.m53 download entry points with hardened wrappers for one
    cycle. Restored in `finally`. Strategy code is untouched."""
    m53 = eng.m53
    orig_download = m53.download_data
    orig_conf = m53.download_confirmation_data
    orig_premarket = m53.premarket_fields

    def _primary(symbol, interval, period):
        return hardened_call(symbol, "primary", orig_download,
                             symbol, interval, period, health=health,
                             frame_validator=validate_primary_frame)

    def _conf(symbol, interval, period):
        # Frozen behavior: exceptions -> None (best-effort confirmation).
        try:
            return hardened_call(symbol, "auxiliary", orig_conf,
                                 symbol, interval, period, health=health,
                                 allow_retry=False, frame_validator=None)
        except DataUnavailable:
            return None

    def _premarket(symbol):
        # Frozen behavior: exceptions -> PM_EMPTY (best-effort premarket).
        try:
            return hardened_call(symbol, "auxiliary", orig_premarket,
                                 symbol, health=health,
                                 allow_retry=False, frame_validator=None)
        except DataUnavailable:
            return dict(m53.PM_EMPTY)

    m53.download_data = _primary
    m53.download_confirmation_data = _conf
    m53.premarket_fields = _premarket
    try:
        yield health
    finally:
        m53.download_data = orig_download
        m53.download_confirmation_data = orig_conf
        m53.premarket_fields = orig_premarket


def _atomic_write_json(path: str, payload: Dict[str, Any]) -> None:
    """Guard 7: temp + atomic replace. No half-written files."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    os.replace(tmp, path)


def write_cycle_summary_atomic(summary: Dict[str, Any],
                               path: Optional[str] = None) -> None:
    """Guard 7: finally-safe summary artifact. Never raises."""
    try:
        _atomic_write_json(
            path or os.path.join(BASE_DIR, "v54_forward", "last_cycle_summary.json"),
            summary)
    except Exception as exc:
        try:
            print(f"summary write failed: {exc}", file=sys.stderr)
        except Exception:
            pass


@dataclass
class CycleContext:
    """Injectable data access: live (yfinance) or replay (cached)."""
    scan_rows: List[Dict[str, Any]]      # annotated V5.4 engine rows
    regime: Dict[str, Any]
    get_4h: Callable[[str], pd.DataFrame]      # symbol -> closed 4H bars
    get_market_4h: Callable[[], pd.DataFrame]  # QQQ closed 4H bars
    provider: Optional[ProviderHealth] = None  # None = replay/unhardened path


def blank_state() -> Dict[str, Any]:
    return {"seen_signal_ids": [], "pending": {}, "positions": {},
            "snapshots": {}, "close_logged": {}, "runs": 0, "last_run": None}


def load_state(path: str = STATE_PATH) -> Dict[str, Any]:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return blank_state()


def save_state(state: Dict[str, Any], path: str = STATE_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, default=str)
    os.replace(tmp, path)


def _busy(state: Dict[str, Any], tracker: ModeBTracker, symbol: str) -> bool:
    if any(p["symbol"] == symbol for p in state["pending"].values()):
        return True
    return any(p["symbol"] == symbol and p["status"] != "closed"
               for p in tracker.positions.values())


def v53_state_for_bar(symbol: str, df_full: pd.DataFrame,
                      market_full: Optional[pd.DataFrame],
                      regime: Dict[str, Any], bar_ts: pd.Timestamp) -> Optional[str]:
    """V5.3 scanner state as of one completed bar (for EXIT detection).

    Uses only data available at that bar's close — the same information
    the live scanner would have had.
    """
    try:
        d = df_full[df_full.index <= bar_ts]
        m = market_full[market_full.index <= bar_ts] if market_full is not None else None
        row = eng.m53.classify_symbol(symbol, THEME_MAP.get(symbol, "Forward-UX51"),
                                      d, m, regime, INTERVAL)
        return (row or {}).get("state")
    except Exception:
        return None


def _process_symbol(sym: str, df: pd.DataFrame, ctx: CycleContext,
                    state: Dict[str, Any], log: ForwardLog,
                    tracker: ModeBTracker, summary: Dict[str, Any],
                    market_full: Optional[pd.DataFrame] = None) -> int:
    """Walk new completed bars for pending entries and open positions.

    market_full is supplied by the caller; the frozen exit path tolerates
    None (same as the old code when market data was absent). Returns the
    number of bars walked (for outage-recovery audit).
    """
    bars_walked = 0
    entry_bars: Dict[str, Any] = {}  # sids opened this cycle -> entry bar ts
    # Pending entries: open at the first completed bar after the signal bar.
    for sid, pend in list(state["pending"].items()):
        if pend.get("symbol") != sym:
            continue
        sig_start = pd.Timestamp(pend["signal_bar_start"])
        newbars = df[df.index > sig_start]
        if newbars.empty:
            continue  # no completed bar after the signal bar yet
        ts = newbars.index[0]
        snap = state["snapshots"][sid]
        pos = tracker.open_position(snap, float(newbars.iloc[0]["Open"]), ts.isoformat())
        if pos is None:
            log.log_event(sid, {"event": "entry_skipped",
                                "reason": "entry <= structural stop"})
        else:
            summary["opened"] += 1
            entry_bars[sid] = ts
        del state["pending"][sid]

    # Open positions: walk every new completed bar in order.
    for sid, pos in list(tracker.positions.items()):
        if pos.get("symbol") != sym or pos.get("status") == "closed":
            continue
        if sid in entry_bars:
            newbars = df[df.index >= entry_bars[sid]]
        else:
            last = pos.get("last_processed_bar") or pos.get("entry_bar")
            newbars = df[df.index > pd.Timestamp(last)] if last else df
        for ts, bar in newbars.iterrows():
            scanner_state = v53_state_for_bar(sym, df, market_full, ctx.regime, ts)
            tracker.process_bar(sid, {
                "bar_id": ts.isoformat(),
                "open": float(bar["Open"]), "high": float(bar["High"]),
                "low": float(bar["Low"]), "close": float(bar["Close"]),
                "scanner_state": scanner_state,
            })
            bars_walked += 1
    return bars_walked


def _defer_symbol_data(sym: str, exc: DataUnavailable,
                       sids_open: List[str], sids_pending: List[str],
                       state: Dict[str, Any], log: ForwardLog,
                       summary: Dict[str, Any]) -> None:
    """Guard 2: mark data-deferred; never assume an exit, never invent one.

    Open positions get `exit_data_deferred`; pending entries get
    `entry_data_deferred`. The outage is recorded in state so recovery can
    be audited (Guard 2) and last_processed_bar is untouched so catch-up
    stays chronological.
    """
    for sid in sids_open:
        summary["data_deferred"].append({"signal_id": sid, "symbol": sym,
                                          "kind": "exit", "reason": exc.reason,
                                          "detail": exc.detail[:200]})
        log.log_event(sid, {"event": "exit_data_deferred", "symbol": sym,
                            "reason": exc.reason, "detail": exc.detail[:200]})
    for sid in sids_pending:
        summary["data_deferred"].append({"signal_id": sid, "symbol": sym,
                                          "kind": "entry", "reason": exc.reason,
                                          "detail": exc.detail[:200]})
        log.log_event(sid, {"event": "entry_data_deferred", "symbol": sym,
                            "reason": exc.reason, "detail": exc.detail[:200]})
    outages = state.setdefault("data_outages", {})
    rec = outages.setdefault(sym, {"since": datetime.now(timezone.utc).isoformat(),
                                   "reason": exc.reason, "count": 0})
    rec["count"] += 1
    rec["reason"] = exc.reason


def _recover_symbol_outage(sym: str, sids: List[str], bars_caught_up: int,
                           state: Dict[str, Any], log: ForwardLog) -> None:
    """Guard 2: preserve the outage in the audit log on recovery."""
    outages = state.get("data_outages", {})
    rec = outages.pop(sym, None)
    if rec is None:
        return
    for sid in sids:
        log.log_event(sid, {"event": "data_outage_recovered", "symbol": sym,
                            "outage_since": rec.get("since"),
                            "outage_cycles": rec.get("count"),
                            "bars_caught_up": bars_caught_up,
                            "prior_reason": rec.get("reason")})


def run_cycle(ctx: CycleContext, state: Dict[str, Any],
              log: ForwardLog, tracker: ModeBTracker) -> Dict[str, Any]:
    """Run one forward-test cycle. Returns a summary dict.

    Guards 1/2/5: new entries are suppressed (never decided on partial
    data) when the provider health marks the cycle DEGRADED; exits keep
    processing on valid data and defer explicitly otherwise. A degraded
    cycle is reported as DEGRADED with full coverage — never "NO SIGNALS".
    """
    t0 = time.monotonic()
    provider: Optional[ProviderHealth] = getattr(ctx, "provider", None)
    seen = set(state["seen_signal_ids"])
    summary: Dict[str, Any] = {"new_signals": 0, "new_signal_ids": [],
                               "opened": 0, "closed": [], "errors": [],
                               "data_deferred": [],
                               "entries_suppressed": False,
                               "suppression_reason": "",
                               "cycle_status": CYCLE_HEALTHY}
    # Guard 8f: if the cycle wall-clock budget is already exhausted, no new
    # signal staging at all — exits for open positions may still be
    # processed from already-fetched data below.
    if provider is not None and provider.remaining_budget_s() <= 0:
        summary["entries_suppressed"] = True
        summary["suppression_reason"] = "cycle wall-clock budget exhausted"
        summary["cycle_status"] = CYCLE_DEGRADED
        summary["errors"].append({"scope": "cycle",
                                  "error": "budget exhausted before staging"})

    # 1. Detect new qualified signals — Guard 1: suppressed on DEGRADED
    # (or when the cycle budget was already exhausted on entry).
    if summary["entries_suppressed"]:
        pass  # suppression_reason already recorded above
    elif provider is not None and provider.entries_suppressed:
        summary["entries_suppressed"] = True
        summary["suppression_reason"] = provider.suppression_reason()
    else:
        for row in eng.v54_qualified_signals(ctx.scan_rows):
            sid = row["signal_id"]
            if sid in seen:
                continue
            seen.add(sid)
            state["snapshots"][sid] = row
            log.log_signal(row)
            summary["new_signals"] += 1
            summary["new_signal_ids"].append(sid)
            sym = row["symbol"]
            if _busy(state, tracker, sym):
                log.log_event(sid, {"event": "signal_skipped",
                                    "reason": "position already open/pending",
                                    "symbol": sym})
            else:
                state["pending"][sid] = {"symbol": sym,
                                         "signal_bar_start": row["signal_bar_start_at"]}
                log.log_event(sid, {"event": "pending_entry",
                                    "signal_bar_start": row["signal_bar_start_at"]})
    state["seen_signal_ids"] = sorted(seen)

    # 2. Advance pending entries and open positions — Guard 2: exits
    # continue on valid data; missing/malformed data defers explicitly.
    symbols = ({p["symbol"] for p in state["pending"].values()}
               | {p["symbol"] for p in tracker.positions.values()
                  if p.get("status") != "closed"})
    for sym in sorted(symbols):
        sids_open = [sid for sid, pos in tracker.positions.items()
                     if pos.get("symbol") == sym
                     and pos.get("status") != "closed"]
        sids_pending = [sid for sid, p in state["pending"].items()
                        if p.get("symbol") == sym]
        prov_health = (provider.symbols.get(sym) if provider else None)
        if (prov_health is not None and prov_health.status == "degraded"
                and not prov_health.auxiliary):
            _defer_symbol_data(sym, DataUnavailable(sym, prov_health.reason,
                                                    prov_health.detail),
                               sids_open, sids_pending, state, log, summary)
            continue
        try:
            df = ctx.get_4h(sym)
        except DataUnavailable as exc:
            if provider is not None:
                provider.note(sym, exc.reason, exc.detail)
            _defer_symbol_data(sym, exc, sids_open, sids_pending,
                               state, log, summary)
            continue
        except Exception as exc:  # never let one symbol kill the cycle
            summary["errors"].append({"symbol": sym, "error": str(exc)[:200]})
            continue
        try:
            validate_primary_frame(sym, df)
        except DataUnavailable as exc:
            if provider is not None:
                provider.note(sym, exc.reason, exc.detail)
            _defer_symbol_data(sym, exc, sids_open, sids_pending,
                               state, log, summary)
            continue
        # Market frame: the frozen exit path tolerates None (same as the
        # old code when market data was absent); a market gap never defers
        # exits, it is recorded in coverage.
        try:
            market_full = ctx.get_market_4h()
        except DataUnavailable as exc:
            market_full = None
            if provider is not None:
                provider.note_market_gap(exc.reason)
        except Exception as exc:
            market_full = None
            summary["errors"].append({"symbol": f"{sym}:market",
                                     "error": str(exc)[:200]})
        bars_walked = _process_symbol(sym, df, ctx, state, log, tracker,
                                      summary, market_full=market_full)
        _recover_symbol_outage(sym, sids_open + sids_pending, bars_walked,
                               state, log)

    # 3. Log closes (frozen schema).
    for sid, pos in tracker.positions.items():
        if pos.get("status") == "closed" and not state["close_logged"].get(sid):
            snap = state["snapshots"].get(sid) or log.get_signal(sid) or {}
            log.log_close(close_summary(pos, snap))
            state["close_logged"][sid] = True
            summary["closed"].append(sid)

    # Guard 5: coverage as first-class output.
    if provider is not None:
        provider.finalize()
        open_syms = sorted({p.get("symbol") for p in tracker.positions.values()
                            if p.get("status") != "closed"})
        summary["coverage"] = provider.coverage_block(
            open_symbols=open_syms,
            entries_suppressed=summary["entries_suppressed"])
        if provider.entries_suppressed or summary["data_deferred"]:
            summary["cycle_status"] = CYCLE_DEGRADED

    state["runs"] = state.get("runs", 0) + 1
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    summary["cycle_duration_s"] = round(time.monotonic() - t0, 1)
    return summary


def _grade_counts_by_cohort(log: ForwardLog) -> Dict[str, Dict[str, int]]:
    """Grade counts split by cohort theme (Forward-UX51 vs Forward-X2)."""
    out: Dict[str, Dict[str, int]] = {}
    for r in log._iter():
        if r.get("type") != "signal":
            continue
        theme = r.get("theme") or "unknown"
        g = r.get("v54_grade")
        if g not in ("A", "B", "C"):
            continue
        bucket = out.setdefault(theme, {"A": 0, "B": 0, "C": 0})
        bucket[g] += 1
    return out


def build_status_payload(state: Dict[str, Any], log: ForwardLog,
                         tracker: ModeBTracker) -> Dict[str, Any]:
    """Content for forward_test/v54_status.json (GitHub)."""
    now = datetime.now(timezone.utc).isoformat()
    closed = []
    for sid in state.get("close_logged", {}):
        c = log.get_close(sid)
        if c:
            closed.append(c)
    cum_r = round(sum((c.get("blended_r") or 0) for c in closed), 4)
    wins = sum(1 for c in closed if (c.get("blended_r") or 0) > 0)
    opens = []
    for sid, p in tracker.positions.items():
        if p["status"] == "closed":
            continue
        opens.append({
            "signal_id": sid, "symbol": p.get("symbol"), "grade": p.get("grade"),
            "entry": p.get("entry"), "entry_bar": p.get("entry_bar"),
            "stop": p.get("stop"), "tp1": p.get("tp1"),
            "status": p.get("status"), "bars_held": p.get("bars_held", 0),
            "tp1_taken": p.get("tp1_taken"),
            "profit_protect_armed": p.get("profit_protect_armed"),
            "mfe_r": p.get("mfe_r"), "mae_r": p.get("mae_r"),
        })
    pending = [{"signal_id": sid, "symbol": p["symbol"],
                "grade": (state["snapshots"].get(sid) or {}).get("v54_grade"),
                "signal_bar": p["signal_bar_start"]}
               for sid, p in state.get("pending", {}).items()]
    return {
        "as_of": now,
        "rule_set": "V5.4 frozen 2026-09-15 (structural + ADX>=20 entries, "
                    "Mode B exits, A/B/C grading)",
        "universe": f"UX51+X2 ({len(UX51_UNIVERSE)}+{len(ux2.UNIVERSE_X2)} symbols)",
        "cohort_sizes": COHORT_SIZES,
        "live_control": "V5.3 (unchanged)",
        "last_successful_cycle": state.get("last_run"),
        "signals_logged": len(state.get("seen_signal_ids", [])),
        "grade_counts": log.grade_counts(),
        "grade_counts_by_cohort": _grade_counts_by_cohort(log),
        "pending_entries": pending,
        "open_positions": opens,
        "closed_trades": len(closed),
        "cumulative_r": cum_r,
        "cumulative_r_note": "Sum of per-trade blended R at 1R risk each; "
                             "not compounded.",
        "avg_r_per_trade": round(cum_r / len(closed), 4) if closed else 0.0,
        "win_rate": round(wins / len(closed), 4) if closed else 0.0,
        "closed_v53_would_have_vetoed": sum(1 for c in closed if c.get("v53_vetoed")),
        "closed_vetoed_winners": sum(1 for c in closed
                                     if c.get("v53_vetoed")
                                     and (c.get("blended_r") or 0) > 0),
    }


def build_closed_trades_payload(state: Dict[str, Any],
                                log: ForwardLog) -> Dict[str, Any]:
    """Content for forward_test/v54_closed_trades.json (GitHub)."""
    trades = []
    for sid in state.get("close_logged", {}):
        c = log.get_close(sid)
        if c:
            trades.append(c)
    return {"as_of": datetime.now(timezone.utc).isoformat(),
            "count": len(trades),
            "trades": trades}


def _payload_fingerprint(payload: Dict[str, Any]) -> str:
    """Hash of the meaningful content, ignoring volatile timestamps."""
    import hashlib
    scrubbed = {k: v for k, v in payload.items()
                if k not in ("as_of", "last_successful_cycle",
                             "exported_at", "assessed_at")}
    blob = json.dumps(scrubbed, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def write_github_snapshot(state: Dict[str, Any], log: ForwardLog,
                          tracker: ModeBTracker) -> Dict[str, str]:
    """Write the two GitHub reporting files. Returns their paths."""
    outdir = os.path.join(BASE_DIR, "forward_test")
    os.makedirs(outdir, exist_ok=True)
    paths = {}
    for name, payload in (("v54_status.json",
                           build_status_payload(state, log, tracker)),
                          ("v54_closed_trades.json",
                           build_closed_trades_payload(state, log))):
        path = os.path.join(outdir, name)
        _atomic_write_json(path, payload)  # Guard 7: no half-written files
        paths[name] = path
    return paths


def _git_with_retry(git_fn, *args: str, attempts: int = 6,
                  base_sleep: int = 10) -> "subprocess.CompletedProcess":
    """Run a git command, retrying transient network failures.

    The egress proxy intermittently resets SSH connections; retries ride
    out those blips. Returns the last result.
    """
    import subprocess
    import time
    last = None
    for i in range(attempts):
        last = git_fn(*args)
        if last.returncode == 0:
            return last
        blob = (last.stderr or "") + (last.stdout or "")
        transient = any(s in blob for s in (
            "Connection reset", "Connection closed", "Could not read from",
            "kex_exchange_identification", "Network is unreachable",
            "Temporary failure", "Connection timed out"))
        if not transient or i == attempts - 1:
            return last
        time.sleep(base_sleep * (i + 1))
    return last


GH_OWNER = "mickaellall116-cmyk"
GH_REPO = "quality-flow-scanner-v5"
GH_CLI = os.path.expanduser("~/workspace/skills/github/bin/gh_contents.py")


def publish_snapshot() -> Dict[str, Any]:
    """Publish forward_test/ to origin/main via the GitHub Contents API.

    Pushes only when the meaningful content changed (timestamps alone
    don't trigger a commit). Uses the stored GitHub connector -- no git
    remote operations, so it works when SSH transport is blocked.
    """
    import subprocess

    def gh_cli(*args: str) -> Dict[str, Any]:
        r = subprocess.run([sys.executable, GH_CLI, *args],
                           capture_output=True, text=True, timeout=120)
        try:
            return json.loads((r.stdout or "").strip().splitlines()[-1])
        except Exception:
            return {"ok": False,
                    "error": f"cli failed: {(r.stderr or r.stdout)[-300:]}"}

    def gh_args(mode: str, **kw: str):
        out = [mode, "--owner", GH_OWNER, "--repo", GH_REPO, "--branch", "main"]
        for k, v in kw.items():
            out += [f"--{k}", v]
        return out

    result: Dict[str, Any] = {"ok": False}
    files = [("v54_status.json", "forward_test/v54_status.json"),
             ("v54_closed_trades.json", "forward_test/v54_closed_trades.json"),
             ("v54_ai_observer.json", "forward_test/v54_ai_observer.json")]

    # Meaningful change? Compare local payloads against the live GitHub
    # versions, ignoring volatile timestamps.
    to_push = []
    for name, remote in files:
        local_path = os.path.join(BASE_DIR, remote)
        try:
            cur = _payload_fingerprint(
                json.load(open(local_path, encoding="utf-8")))
        except Exception as e:
            result["step"] = "read-local"
            result["error"] = f"{name}: {e}"
            return result
        got = gh_cli(*gh_args("get", remote=remote))
        if not got.get("ok"):
            if got.get("error") == "not found":
                to_push.append((name, remote, local_path))
                continue
            result["step"] = "get-remote"
            result["error"] = f"{name}: {got.get('error')}"
            return result
        try:
            old = _payload_fingerprint(json.loads(got["content"]))
        except Exception:
            old = None
        if old != cur:
            to_push.append((name, remote, local_path))

    if not to_push:
        return {"ok": True, "pushed": False, "note": "up to date"}

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    commits = []
    for name, remote, local_path in to_push:
        put = gh_cli(*gh_args("put", local=local_path, remote=remote,
                              message=f"V5.4 forward-test snapshot {stamp}"))
        if not put.get("ok"):
            result["step"] = "put"
            result["error"] = f"{name}: {put.get('error')}"
            return result
        commits.append(put.get("commit"))
    result.update({"ok": True, "pushed": True, "commits": commits})
    return result


# ---------------------------------------------------------------------------
# AI Observer (AI-OBS-v1) helpers.
#
# The observer is observational only: it never vetoes, promotes, downgrades,
# resizes, enters, or exits a V5.4 trade, and V5.4's frozen rules, grades,
# exits, and logs are untouched by it.
#
# Protocol (enforced by the hourly worker, see cron body):
#   * Assess ONLY signal_ids in the current cycle's new_signal_ids — i.e.
#     at signal-generation time, before the outcome is known.
#   * The observer never sees the V5.4 grade (withheld by construction in
#     observer_snapshot_from_row) nor any later price action.
#   * Assessments are append-only and immutable: never regenerate or edit
#     an existing signal_id's assessment.
#   * INTC's 2026-09-15 signal predates the observer and is excluded.
# ---------------------------------------------------------------------------

def _observer_signal_row(signal_id: str) -> Dict[str, Any]:
    state = load_state()
    row = (state.get("snapshots") or {}).get(signal_id)
    if row:
        return row
    row = ForwardLog(LOG_PATH).get_signal(signal_id)
    if row:
        return row
    raise KeyError(f"unknown signal_id: {signal_id}")


def observer_snapshot_from_row(signal_id: str,
                               row: Dict[str, Any]) -> Dict[str, Any]:
    """Raw-feature snapshot for the AI observer.

    Allowlisted raw market/structural facts only. The V5.4 grade and all
    model-judgment fields are excluded by construction.
    """
    snap = {k: row.get(k) for k in _OBS_RAW_FIELDS if k in row}
    # Tripwire: fail loudly if a judgment field ever enters the allowlist.
    bad = _OBS_EXCLUDED_KEYS & set(snap.keys())
    assert not bad, f"observer snapshot leaked judgment fields: {sorted(bad)}"
    snap["signal_id"] = signal_id
    snap["entry_plan"] = ("next 4H bar open "
                          "(entry price unknown at signal time)")
    ref, stop = row.get("price"), row.get("stop")
    try:
        r = float(ref) - float(stop)
        snap["ref_price"] = float(ref)
        snap["plus1r_ref_price"] = round(float(ref) + r, 4)
    except (TypeError, ValueError):
        snap["ref_price"] = ref
        snap["plus1r_ref_price"] = None
    return snap


def observer_raw_snapshot(signal_id: str) -> Dict[str, Any]:
    """Raw-feature snapshot for a logged signal_id (grade excluded)."""
    return observer_snapshot_from_row(signal_id,
                                     _observer_signal_row(signal_id))


def observer_already_assessed(signal_id: str) -> bool:
    """True if an immutable assessment already exists (never regenerate)."""
    try:
        with open(OBSERVER_LOG_PATH, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    if json.loads(line).get("signal_id") == signal_id:
                        return True
                except Exception:
                    continue
    except FileNotFoundError:
        return False
    return False


def validate_assessment(obj: Dict[str, Any]) -> List[str]:
    """Schema check for one AI-OBS-v1 assessment. Returns error list."""
    errs = []
    if obj.get("observer") != AI_OBS_VERSION:
        errs.append("observer must be AI-OBS-v1")
    if obj.get("prompt_version") != AI_OBS_PROMPT_VERSION:
        errs.append("prompt_version must be v1")
    if not obj.get("signal_id"):
        errs.append("signal_id required")
    if obj.get("classification") not in ("FAVORABLE", "NEUTRAL", "CAUTION"):
        errs.append("classification must be FAVORABLE/NEUTRAL/CAUTION")
    c = obj.get("confidence")
    if not isinstance(c, int) or isinstance(c, bool) or not (0 <= c <= 100):
        errs.append("confidence must be integer 0-100")
    r = obj.get("reasons")
    if (not isinstance(r, list) or not (2 <= len(r) <= 4)
            or not all(isinstance(x, str) and x.strip() for x in r)):
        errs.append("reasons must be 2-4 non-empty strings")
    for k in ("primary_risk", "invalidation"):
        if not isinstance(obj.get(k), str) or not obj[k].strip():
            errs.append(f"{k} must be a non-empty string")
    if obj.get("timing") not in ("EARLY", "MATURE", "EXTENDED"):
        errs.append("timing must be EARLY/MATURE/EXTENDED")
    feats = obj.get("features")
    if not isinstance(feats, dict):
        errs.append("features must be the raw snapshot dict")
    else:
        leaked = _OBS_EXCLUDED_KEYS & set(feats.keys())
        if leaked:
            errs.append(f"grade/judgment leak in features: {sorted(leaked)}")
    return errs


def observer_append_assessment(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and append one assessment to the immutable observer log.

    Refuses (ok: False) when the schema fails, when the signal_id was
    already assessed, or when the assessment is stale (anything other
    than the current UTC date — backfills are contamination).
    """
    errs = validate_assessment(obj)
    sid = obj.get("signal_id") or ""
    if observer_already_assessed(sid):
        errs.append(f"{sid} already assessed: never regenerate")
    try:
        assessed_day = obj.get("assessed_at", "")[:10]
        today = datetime.now(timezone.utc).date().isoformat()
        if assessed_day != today:
            errs.append("assessed_at must be today (no backfills)")
    except Exception:
        errs.append("assessed_at unparseable")
    if errs:
        return {"ok": False, "errors": errs}
    os.makedirs(os.path.dirname(OBSERVER_LOG_PATH), exist_ok=True)
    with open(OBSERVER_LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, default=str) + "\n")
    return {"ok": True, "signal_id": sid}


def write_observer_export() -> str:
    """Write forward_test/v54_ai_observer.json from the append-only log.

    Machine-readable, no secrets: assessments + prompt fingerprint only.
    """
    import hashlib

    assessments: List[Dict[str, Any]] = []
    try:
        with open(OBSERVER_LOG_PATH, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    assessments.append(json.loads(line))
    except FileNotFoundError:
        pass
    try:
        with open(AI_OBS_PROMPT_PATH, "rb") as fh:
            prompt_sha = hashlib.sha256(fh.read()).hexdigest()[:12]
    except FileNotFoundError:
        prompt_sha = None
    payload = {
        "observer": AI_OBS_VERSION,
        "prompt_version": AI_OBS_PROMPT_VERSION,
        "prompt_sha256_12": prompt_sha,
        "assessment_count": len(assessments),
        "assessments": assessments,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    os.makedirs(os.path.dirname(OBSERVER_EXPORT_PATH), exist_ok=True)
    _atomic_write_json(OBSERVER_EXPORT_PATH, payload)  # Guard 7
    return OBSERVER_EXPORT_PATH


def _tracker_with_sink(log: ForwardLog) -> ModeBTracker:
    def _sink(event: Dict[str, Any]) -> None:
        event = dict(event)
        sid = event.pop("signal_id")
        log.log_event(sid, event)
    return ModeBTracker(event_sink=_sink)


def _write_heartbeat_atomic(summary: Dict[str, Any]) -> None:
    """Guard 7: watchdog heartbeat via temp+atomic replace (fail-closed:
    an aborted/degraded cycle is visible, never silently clean)."""
    hb = {"finished_at": datetime.now(timezone.utc).isoformat(),
          "cycle_status": summary.get("cycle_status", CYCLE_ABORTED),
          "entries_suppressed": bool(summary.get("entries_suppressed")),
          "new_signals": summary.get("new_signals", 0),
          "opened": summary.get("opened", 0),
          "closed": summary.get("closed", []),
          "errors": summary.get("errors", [])}
    if "publish" in summary:
        hb["publish"] = summary["publish"]
    if summary.get("coverage") is not None:
        hb["coverage"] = summary["coverage"]
    _atomic_write_json(os.path.join(BASE_DIR, "v54_forward", "last_cycle.json"), hb)


def run_once(publish: bool = False) -> Dict[str, Any]:
    """Live cycle: yfinance-backed scan + position management.

    Hardened (Guards 3/4/7): all vendor calls run through bounded,
    classified, single-retry wrappers; the summary artifact is written in
    a finally-safe path even on crash; every output write is atomic.
    Strategy semantics are unchanged.

    With publish=True and a HEALTHY cycle (no errors), the GitHub snapshot
    files are committed and pushed to origin/main. Degraded/aborted cycles
    are recorded locally but never pushed.
    """
    state = load_state()
    log = ForwardLog(LOG_PATH)
    tracker = _tracker_with_sink(log)
    tracker.positions = state.get("positions", {})

    market_sym = eng.m53.MARKET_SYMBOL
    health = ProviderHealth(
        expected_symbols=list(dict.fromkeys(
            list(FORWARD_UNIVERSE) + [market_sym, "QQQ", "SPY"])))
    summary: Dict[str, Any] = {
        "new_signals": 0, "new_signal_ids": [], "opened": 0, "closed": [],
        "errors": [], "data_deferred": [], "entries_suppressed": True,
        "suppression_reason": "cycle did not complete",
        "cycle_status": CYCLE_ABORTED}
    ctx: Optional[CycleContext] = None
    regime: Dict[str, Any] = {"regime": "UNKNOWN", "risk_on": False,
                              "score": 0, "gate": "BLOCK"}
    rows: List[Dict[str, Any]] = []
    t0 = time.monotonic()
    try:
        with hardened_downloads(health):
            try:
                rows, regime = eng.v54_scan_symbols(
                    FORWARD_UNIVERSE, THEME_MAP, INTERVAL, PERIOD)
            except DataUnavailable as exc:
                # Market-level fetch failed: no new-entry decisions are
                # possible this cycle, but exits for open positions are
                # still processed below (Guard 2).
                health.note(exc.symbol, exc.reason, exc.detail)
                rows = []
                regime = {"regime": "UNKNOWN", "risk_on": False, "score": 0,
                          "gate": "BLOCK",
                          "error": f"market fetch failed: {exc.reason}"}
            dl_cache: Dict[str, pd.DataFrame] = {}

            def _get_4h(symbol: str) -> pd.DataFrame:
                if symbol not in dl_cache:
                    # Patched by hardened_downloads: bounded + classified.
                    dl_cache[symbol] = eng.m53.download_data(
                        symbol, INTERVAL, PERIOD)
                return dl_cache[symbol]

            ctx = CycleContext(scan_rows=rows, regime=regime, get_4h=_get_4h,
                               get_market_4h=lambda: _get_4h(market_sym),
                               provider=health)
            summary = run_cycle(ctx, state, log, tracker)
        # Strategy state advances only through completed, validated cycle
        # operations (Guard 7): not persisted if the cycle raised.
        state["positions"] = tracker.positions
        save_state(state)

        qualified = eng.v54_qualified_signals(rows)
        payload = eng.v54_envelope(qualified, regime, INTERVAL, PERIOD)
        payload["forward_test"] = {
            "universe": "UX51+X2",
            "universe_size": len(FORWARD_UNIVERSE),
            "cohort_sizes": COHORT_SIZES,
            "signals_logged": len(state["seen_signal_ids"]),
            "open_positions": [sid for sid, p in tracker.positions.items()
                               if p.get("status") != "closed"],
            "pending_entries": list(state["pending"].keys()),
            "grade_counts": log.grade_counts(),
            "cycles_run": state["runs"],
            "cycle_status": summary.get("cycle_status", CYCLE_ABORTED),
            "entries_suppressed": bool(summary.get("entries_suppressed")),
            "last_cycle": summary,
        }
        _atomic_write_json(OUTPUT_PATH, payload)
        summary["output"] = OUTPUT_PATH

        # GitHub reporting files (local write every cycle; push only on --publish).
        snapshot_paths = write_github_snapshot(state, log, tracker)
        snapshot_paths["v54_ai_observer.json"] = write_observer_export()
        summary["snapshot_files"] = snapshot_paths
        if (publish and summary.get("cycle_status") == CYCLE_HEALTHY
                and not summary["errors"]):
            summary["publish"] = publish_snapshot()
        elif publish:
            summary["publish"] = {
                "ok": False, "skipped": True,
                "reason": (f"cycle {summary.get('cycle_status')}: "
                           "snapshot not pushed")}
        # Heartbeat for the watchdog.
        _write_heartbeat_atomic(summary)
    except Exception as exc:  # Guard 7: a crash must never look clean
        summary["aborted_error"] = str(exc)[:300]
        summary["errors"].append({"scope": "cycle", "error": str(exc)[:200]})
        summary["cycle_status"] = CYCLE_ABORTED
        summary["entries_suppressed"] = True
        try:
            _write_heartbeat_atomic(summary)
        except Exception:
            pass
    finally:
        # Guard 7: the summary artifact is always written, even on crash.
        summary["cycle_duration_s"] = round(time.monotonic() - t0, 1)
        write_cycle_summary_atomic(summary)
    # ---- FVG-entry paper sidecar (additive; fail-closed) ----
    # Runs AFTER the frozen cycle's outputs (snapshots, heartbeat) are
    # written, so it can never delay or alter them. Bounded by its own
    # deadline (Guard 4); any exception is contained here and reported in
    # summary["fvg_sidecar"].
    try:
        from v54_fvg_sidecar import run_sidecar_cycle

        def _sidecar():
            return run_sidecar_cycle(ctx, regime)

        ok, res = _call_with_deadline(_sidecar, (), {},
                                      HARD_SIDECAR_DEADLINE_S)
        summary["fvg_sidecar"] = (res if ok
                                  else {"ok": False, "error": "sidecar deadline exceeded"})
    except Exception as exc:  # noqa: BLE001 -- the frozen cycle must never break
        summary["fvg_sidecar"] = {"ok": False, "error": str(exc)[:200]}
    return summary


if __name__ == "__main__":
    import sys
    result = run_once(publish="--publish" in sys.argv)
    print(json.dumps(result, default=str, indent=2))
