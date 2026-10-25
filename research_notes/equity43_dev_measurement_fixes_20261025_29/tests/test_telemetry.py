"""P8 synthetic battery for qf_telemetry (prospective as-of journal).

Run: python3 tests/test_telemetry.py  (exit 0 = all assertions hold)
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "code"))
import qf_telemetry as qt  # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
    if not cond:
        FAILURES.append(name)


def expect_refusal(name, fn, needle=""):
    try:
        fn()
    except qt.TelemetryError as e:
        check(name, needle in str(e), f"({e})")
        return
    check(name, False, "no TelemetryError raised")


def signal_fire(**over):
    r = {
        "record_type": "SIGNAL_FIRE", "symbol": "AAA", "signal_idx": 300,
        "signal_time": "2026-11-02T09:30:00-05:00",
        "decision_time": "2026-11-02T13:30:00-05:00",
        "recorded_at": "2026-11-02T13:30:05-05:00",
        "bar_finalized": True,
        "predicates": {"confirmed": True, "breakout_buy": False,
                       "ready_buy": False, "score": 4, "score_threshold": 4},
        "adx": 27.5, "di_plus": 30.1, "di_minus": 12.4, "trend_score": 4,
        "vwap_distance": 0.012, "rel_volume": 1.35,
        "ema_state": {"e9": 101.2, "e21": 100.4, "e55": 98.9,
                      "e200": 95.0},
        "rs": 0.083, "benchmark_asof": "2026-10-30T16:00:00-04:00",
        "market_gate": "CONFIRM", "signal_grade": "A",
        "gate_reasons": [], "open_slots": 3,
        "sector_occupancy": {"SEMIS": 1}, "heat_before": 0.02,
        "heat_after": 0.03, "rank_margin": 0.011,
        "signal_close": 101.0, "atr": 2.5, "stop_threshold": 97.25,
        "tp1_level": 106.05, "intended_entry": 101.4,
        "disposition": "taken",
    }
    r.update(over)
    return r


def main():
    j = qt.TelemetryJournal()
    j.append(signal_fire())
    check("valid SIGNAL_FIRE appends", len(j.lines) == 1)
    ok, bad = qt.verify_lines(j.lines)
    check("chain verifies", ok and bad is None)

    expect_refusal("unfinalized bar refused",
                   lambda: j.append(signal_fire(signal_idx=301,
                                                bar_finalized=False)),
                   "bar_finalized")
    expect_refusal("lookahead decision refused",
                   lambda: j.append(signal_fire(
                       signal_idx=301,
                       decision_time="2026-11-02T11:30:00-05:00",
                       recorded_at="2026-11-02T11:30:05-05:00")),
                   "lookahead")
    expect_refusal("retro-stamped record refused",
                   lambda: j.append(signal_fire(
                       signal_idx=301,
                       recorded_at="2026-11-02T13:29:00-05:00")),
                   "retro-stamped")
    expect_refusal("missing T1 field (adx) refused",
                   lambda: j.append(signal_fire(signal_idx=301, adx=None)),
                   "adx")
    r = signal_fire(signal_idx=301)
    r["invented_field"] = 1
    expect_refusal("unknown field refused", lambda: j.append(r),
                   "unknown fields")
    expect_refusal("duplicate signal_idx refused (backfill)",
                   lambda: j.append(signal_fire(signal_idx=300)),
                   "strictly increasing")
    expect_refusal("EXECUTION refused in signal-only mode",
                   lambda: j.append({
                       "record_type": "EXECUTION", "symbol": "AAA",
                       "signal_idx": 300, "leg": "entry",
                       "order_time": "2026-11-02T13:30:00-05:00",
                       "ack_time": "2026-11-02T13:30:01-05:00",
                       "fill_time": "2026-11-02T13:30:01-05:00",
                       "fill_price": 101.4, "order_id": "x1",
                       "recorded_at": "2026-11-02T13:30:02-05:00"}),
                   "signal-only")

    # BAR_PATH + EXIT_DECISION (T3: decision bar close present).
    j.append({
        "record_type": "BAR_PATH", "symbol": "AAA", "signal_idx": 300,
        "bar_idx": 301, "bar_time": "2026-11-02T13:30:00-05:00",
        "decision_time": "2026-11-02T17:30:00-05:00",
        "recorded_at": "2026-11-02T17:30:05-05:00", "bar_finalized": True,
        "open_px": 101.4, "high": 103.0, "low": 100.9, "close": 102.5,
        "entry": 101.4, "stop_threshold": 97.25, "tp1_level": 106.05,
        "runner": 97.25, "tp1_touched": False, "stop_breached": False,
        "breach_count": 0, "bars_under_threshold": 0,
        "mae_input": -0.005, "mfe_input": 0.016})
    j.append({
        "record_type": "EXIT_DECISION", "symbol": "AAA", "signal_idx": 300,
        "decision_bar_idx": 305, "decision_bar_time":
        "2026-11-03T09:30:00-05:00",
        "decision_time": "2026-11-03T13:30:00-05:00",
        "recorded_at": "2026-11-03T13:30:05-05:00", "bar_finalized": True,
        "decision_bar_open": 99.0, "decision_bar_high": 99.4,
        "decision_bar_low": 96.8, "decision_bar_close": 97.0,
        "runner_in_force": 97.25, "ema55_in_force": 99.1,
        "decision": "exit", "exit_reason": "stop",
        "fill_time": "2026-11-03T13:30:00-05:00", "fill_price": 98.9})
    ok, bad = qt.verify_lines(j.lines)
    check("BAR_PATH + EXIT_DECISION append; chain verifies",
          ok and len(j.lines) == 3)

    # Tamper evidence: flip a value in line 2 -> verify fails at index 1.
    lines = list(j.lines)
    rec = json.loads(lines[1])
    rec["close"] = 1.0
    lines[1] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    ok, bad = qt.verify_lines(lines)
    check("tampered line detected at its index", (not ok) and bad == 1,
          f"ok={ok} bad={bad}")

    # File-backed journal: reload verifies chain; tampered file refuses.
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "journal.jsonl")
        jf = qt.TelemetryJournal(path=p)
        jf.append(signal_fire(symbol="BBB", signal_idx=10))
        jf2 = qt.TelemetryJournal(path=p)
        check("file journal reloads + chain ok", len(jf2.lines) == 1)
        with open(p, "a") as f:
            f.write('{"record_type":"SIGNAL_FIRE","prev_hash":"x",'
                    '"record_hash":"y"}\n')
        expect_refusal("tampered file refused on load",
                       lambda: qt.TelemetryJournal(path=p), "chain")

    # Execution-authorized lane accepts T6.
    jx = qt.TelemetryJournal(execution_authorized=True)
    jx.append({
        "record_type": "EXECUTION", "symbol": "AAA", "signal_idx": 300,
        "leg": "entry", "order_time": "2026-11-02T13:30:00-05:00",
        "ack_time": "2026-11-02T13:30:01-05:00",
        "fill_time": "2026-11-02T13:30:01-05:00", "fill_price": 101.4,
        "order_id": "x1", "recorded_at": "2026-11-02T13:30:02-05:00"})
    check("EXECUTION accepted when execution_authorized", len(jx.lines) == 1)

    print("SUMMARY", "FAIL" if FAILURES else "PASS", FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
