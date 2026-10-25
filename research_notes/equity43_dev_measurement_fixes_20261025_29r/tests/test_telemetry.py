"""29r battery for the repaired qf_telemetry (prospective as-of journal).

Run: python3 tests/test_telemetry.py  (exit 0 = all assertions hold)

The -29 battery's 14 checks are retained in substance, re-based onto
sessions inside the pinned table (2025-11-03/04, EST). The repair
fixtures required by ChatGPT's -29 verdict are added:

  * 13:30->16:00 second bin: decision stamped 17:30 refused for
    SIGNAL_FIRE and BAR_PATH; decision stamped 16:00 accepted.
  * Early close (2025-07-03): the single bin ends 13:00 — a 13:30
    decision refused; a 13:30 bin start refused (gapped bin).
  * DST transition (2025-03-10, EDT): a decision stamped with the
    pre-transition offset (-05:00) refused — the instant is not the
    table bin end; 17:30 refused; 16:00-04:00 accepted.
  * Missing/gapped bins: non-session date, non-bin start, and a
    beyond-table date each refused.
  * Retro-stamped records: SIGNAL_FIRE (retained), BAR_PATH,
    EXIT_DECISION, ENTRY_OBSERVED, EXIT_FILL_OBSERVED each refused
    when recorded_at precedes its event instant.
  * Availability split: SIGNAL_FIRE carrying tp1_level or
    intended_entry refused (fields not knowable at fire time);
    EXIT_DECISION carrying fill_price refused; ENTRY_OBSERVED /
    EXIT_FILL_OBSERVED append only when linked to their fire /
    decision at the exact completion instant.
  * Append order is causal: records are appended in event order
    (an observation written at its event instant precedes any later
    bin's fire); a late duplicate observation appended after a later
    fire is refused as backfill by the stream monotonicity track.

Refusal behavior: append() raises qf_telemetry.TelemetryError and the
journal is left unchanged; this battery exits 0 only if every
expected refusal fires and every valid record appends.
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
        "signal_time": "2025-11-03T09:30:00-05:00",
        "decision_time": "2025-11-03T13:30:00-05:00",
        "recorded_at": "2025-11-03T13:30:05-05:00",
        "bar_finalized": True,
        "predicates": {"confirmed": True, "breakout_buy": False,
                       "ready_buy": False, "score": 4, "score_threshold": 4},
        "adx": 27.5, "di_plus": 30.1, "di_minus": 12.4, "trend_score": 4,
        "vwap_distance": 0.012, "rel_volume": 1.35,
        "ema_state": {"e9": 101.2, "e21": 100.4, "e55": 98.9,
                      "e200": 95.0},
        "rs": 0.083, "benchmark_asof": "2025-10-31T16:00:00-04:00",
        "market_gate": "CONFIRM", "signal_grade": "A",
        "gate_reasons": [], "open_slots": 3,
        "sector_occupancy": {"SEMIS": 1}, "heat_before": 0.02,
        "heat_after": 0.03, "rank_margin": 0.011,
        "signal_close": 101.0, "atr": 2.5, "stop_threshold": 97.25,
        "disposition": "taken",
    }
    r.update(over)
    return r


def entry_observed(**over):
    r = {
        "record_type": "ENTRY_OBSERVED", "symbol": "AAA",
        "signal_idx": 300, "entry_time": "2025-11-03T13:30:00-05:00",
        "entry_price": 101.4, "atr": 2.5, "tp1_level": 106.05,
        "recorded_at": "2025-11-03T13:30:06-05:00"}
    r.update(over)
    return r


def bar_path(**over):
    r = {
        "record_type": "BAR_PATH", "symbol": "AAA", "signal_idx": 300,
        "bar_idx": 301, "bar_time": "2025-11-03T13:30:00-05:00",
        "decision_time": "2025-11-03T16:00:00-05:00",
        "recorded_at": "2025-11-03T16:00:05-05:00", "bar_finalized": True,
        "open_px": 101.4, "high": 103.0, "low": 100.9, "close": 102.5,
        "entry": 101.4, "stop_threshold": 97.25, "tp1_level": 106.05,
        "runner": 97.25, "tp1_touched": False, "stop_breached": False,
        "breach_count": 0, "bars_under_threshold": 0,
        "mae_input": -0.005, "mfe_input": 0.016}
    r.update(over)
    return r


def exit_decision(**over):
    r = {
        "record_type": "EXIT_DECISION", "symbol": "AAA", "signal_idx": 300,
        "decision_bar_idx": 305,
        "decision_bar_time": "2025-11-04T09:30:00-05:00",
        "decision_time": "2025-11-04T13:30:00-05:00",
        "recorded_at": "2025-11-04T13:30:05-05:00", "bar_finalized": True,
        "decision_bar_open": 99.0, "decision_bar_high": 99.4,
        "decision_bar_low": 96.8, "decision_bar_close": 97.0,
        "runner_in_force": 97.25, "ema55_in_force": 99.1,
        "decision": "exit", "exit_reason": "stop"}
    r.update(over)
    return r


def exit_fill(**over):
    r = {
        "record_type": "EXIT_FILL_OBSERVED", "symbol": "AAA",
        "signal_idx": 300, "fill_time": "2025-11-04T13:30:00-05:00",
        "fill_price": 98.9,
        "recorded_at": "2025-11-04T13:30:06-05:00"}
    r.update(over)
    return r


def main():
    j = qt.TelemetryJournal()
    j.append(signal_fire())
    check("valid SIGNAL_FIRE appends (bin1 09:30->13:30)",
          len(j.lines) == 1)
    ok, bad = qt.verify_lines(j.lines)
    check("chain verifies", ok and bad is None)

    expect_refusal("unfinalized bar refused",
                   lambda: j.append(signal_fire(signal_idx=301,
                                                bar_finalized=False)),
                   "bar_finalized")
    expect_refusal("decision before bin end refused (11:30)",
                   lambda: j.append(signal_fire(
                       signal_idx=301,
                       decision_time="2025-11-03T11:30:00-05:00",
                       recorded_at="2025-11-03T11:30:05-05:00")),
                   "bin_end")
    expect_refusal("retro-stamped SIGNAL_FIRE refused",
                   lambda: j.append(signal_fire(
                       signal_idx=301,
                       recorded_at="2025-11-03T13:29:00-05:00")),
                   "retro-stamped")
    expect_refusal("missing T1 field (adx) refused",
                   lambda: j.append(signal_fire(signal_idx=301, adx=None)),
                   "adx")
    r = signal_fire(signal_idx=301)
    r["invented_field"] = 1
    expect_refusal("unknown field refused", lambda: j.append(r),
                   "unknown fields")
    expect_refusal("SIGNAL_FIRE with tp1_level refused (not knowable "
                   "at fire time)",
                   lambda: j.append(signal_fire(signal_idx=301,
                                                tp1_level=106.05)),
                   "unknown fields")
    expect_refusal("SIGNAL_FIRE with intended_entry refused (not "
                   "knowable at fire time)",
                   lambda: j.append(signal_fire(signal_idx=301,
                                                intended_entry=101.4)),
                   "unknown fields")
    expect_refusal("naive timestamp refused",
                   lambda: j.append(signal_fire(
                       signal_idx=301,
                       signal_time="2025-11-03T09:30:00",
                       decision_time="2025-11-03T13:30:00",
                       recorded_at="2025-11-03T13:30:05")),
                   "naive")
    expect_refusal("duplicate signal_idx refused (backfill)",
                   lambda: j.append(signal_fire(signal_idx=300)),
                   "strictly increasing")
    expect_refusal("SIGNAL_FIRE bin2 decision 17:30 refused",
                   lambda: j.append(signal_fire(
                       signal_idx=301,
                       signal_time="2025-11-03T13:30:00-05:00",
                       decision_time="2025-11-03T17:30:00-05:00",
                       recorded_at="2025-11-03T17:30:05-05:00")),
                   "bin_end")

    # Causal append order: the fire's entry observation is written at
    # its instant (13:30) before the next bin's fire exists (16:00).
    j.append(entry_observed())
    check("ENTRY_OBSERVED appends at the next bin start after the "
          "fire's bin", len(j.lines) == 2)
    j.append(signal_fire(signal_idx=301,
                         signal_time="2025-11-03T13:30:00-05:00",
                         decision_time="2025-11-03T16:00:00-05:00",
                         recorded_at="2025-11-03T16:00:05-05:00"))
    check("SIGNAL_FIRE bin2 decision 16:00 appends", len(j.lines) == 3)

    expect_refusal("ENTRY_OBSERVED at a wrong-bin instant refused",
                   lambda: j.append(entry_observed(
                       signal_idx=301,
                       entry_time="2025-11-03T13:30:00-05:00",
                       recorded_at="2025-11-03T13:30:06-05:00")),
                   "next bin start")
    expect_refusal("ENTRY_OBSERVED without prior fire refused",
                   lambda: j.append(entry_observed(signal_idx=999)),
                   "no prior SIGNAL_FIRE")
    expect_refusal("retro-stamped ENTRY_OBSERVED refused",
                   lambda: j.append(entry_observed(
                       signal_idx=301,
                       entry_time="2025-11-04T09:30:00-05:00",
                       recorded_at="2025-11-04T09:29:00-05:00")),
                   "retro-stamped")
    expect_refusal("late duplicate ENTRY_OBSERVED refused (backfill)",
                   lambda: j.append(entry_observed(
                       recorded_at="2025-11-03T16:30:00-05:00")),
                   "backfill")

    # BAR_PATH: bin-end + recorded-at guards (absent in -29).
    j.append(bar_path())
    check("BAR_PATH appends (bin2 decision 16:00)", len(j.lines) == 4)
    expect_refusal("BAR_PATH decision 17:30 refused",
                   lambda: j.append(bar_path(
                       bar_idx=302,
                       decision_time="2025-11-03T17:30:00-05:00",
                       recorded_at="2025-11-03T17:30:05-05:00")),
                   "bin_end")
    expect_refusal("retro-stamped BAR_PATH refused",
                   lambda: j.append(bar_path(
                       bar_idx=302, bar_time="2025-11-04T09:30:00-05:00",
                       decision_time="2025-11-04T13:30:00-05:00",
                       recorded_at="2025-11-04T13:29:00-05:00")),
                   "retro-stamped")

    # EXIT_DECISION: guards + no mandated fill; fill observed after.
    j.append(exit_decision())
    check("EXIT_DECISION appends without fill fields",
          len(j.lines) == 5)
    expect_refusal("EXIT_DECISION with fill_price refused (not "
                   "knowable at decision time)",
                   lambda: j.append(exit_decision(
                       decision_bar_idx=306,
                       decision_bar_time="2025-11-04T13:30:00-05:00",
                       decision_time="2025-11-04T16:00:00-05:00",
                       recorded_at="2025-11-04T16:00:05-05:00",
                       fill_price=98.9)),
                   "unknown fields")
    expect_refusal("retro-stamped EXIT_DECISION refused",
                   lambda: j.append(exit_decision(
                       decision_bar_idx=306,
                       decision_bar_time="2025-11-04T13:30:00-05:00",
                       decision_time="2025-11-04T16:00:00-05:00",
                       recorded_at="2025-11-04T15:59:00-05:00")),
                   "retro-stamped")
    j.append(exit_fill())
    check("EXIT_FILL_OBSERVED appends at the next bin start after "
          "the decision bar", len(j.lines) == 6)
    expect_refusal("EXIT_FILL_OBSERVED without prior decision refused",
                   lambda: j.append(exit_fill(signal_idx=999)),
                   "no prior EXIT_DECISION")
    expect_refusal("retro-stamped EXIT_FILL_OBSERVED refused",
                   lambda: j.append(exit_fill(
                       recorded_at="2025-11-04T13:29:00-05:00")),
                   "retro-stamped")
    ok, bad = qt.verify_lines(j.lines)
    check("full chain verifies after all record types",
          ok and bad is None and len(j.lines) == 6)

    # Early close (2025-07-03, close 13:00): single bin ends 13:00.
    j2 = qt.TelemetryJournal()
    j2.append(signal_fire(symbol="CCC", signal_idx=10,
                          signal_time="2025-07-03T09:30:00-04:00",
                          decision_time="2025-07-03T13:00:00-04:00",
                          recorded_at="2025-07-03T13:00:05-04:00",
                          benchmark_asof="2025-07-02T16:00:00-04:00"))
    check("early-close SIGNAL_FIRE appends (decision 13:00)",
          len(j2.lines) == 1)
    expect_refusal("early-close decision 13:30 refused",
                   lambda: j2.append(signal_fire(
                       symbol="CCC", signal_idx=11,
                       signal_time="2025-07-03T09:30:00-04:00",
                       decision_time="2025-07-03T13:30:00-04:00",
                       recorded_at="2025-07-03T13:30:05-04:00")),
                   "bin_end")
    expect_refusal("early-close 13:30 bin start refused (gapped bin)",
                   lambda: j2.append(signal_fire(
                       symbol="CCC", signal_idx=11,
                       signal_time="2025-07-03T13:30:00-04:00",
                       decision_time="2025-07-03T16:00:00-04:00",
                       recorded_at="2025-07-03T16:00:05-04:00")),
                   "bin")

    # DST transition (Mon 2025-03-10 is EDT, UTC-4).
    j2.append(signal_fire(symbol="DDD", signal_idx=10,
                          signal_time="2025-03-10T13:30:00-04:00",
                          decision_time="2025-03-10T16:00:00-04:00",
                          recorded_at="2025-03-10T16:00:05-04:00",
                          benchmark_asof="2025-03-07T16:00:00-05:00"))
    check("DST-session SIGNAL_FIRE appends (16:00-04:00)",
          len(j2.lines) == 2)
    expect_refusal("DST decision stamped with stale -05:00 offset "
                   "refused",
                   lambda: j2.append(signal_fire(
                       symbol="EEE", signal_idx=10,
                       signal_time="2025-03-10T09:30:00-04:00",
                       decision_time="2025-03-10T13:30:00-05:00",
                       recorded_at="2025-03-10T13:30:05-05:00")),
                   "bin_end")
    expect_refusal("DST decision 17:30 refused",
                   lambda: j2.append(signal_fire(
                       symbol="EEE", signal_idx=10,
                       signal_time="2025-03-10T13:30:00-04:00",
                       decision_time="2025-03-10T17:30:00-04:00",
                       recorded_at="2025-03-10T17:30:05-04:00")),
                   "bin_end")

    # Missing / gapped bins.
    expect_refusal("non-session date refused (Sat 2025-01-04)",
                   lambda: j2.append(signal_fire(
                       symbol="EEE", signal_idx=10,
                       signal_time="2025-01-04T09:30:00-05:00",
                       decision_time="2025-01-04T13:30:00-05:00",
                       recorded_at="2025-01-04T13:30:05-05:00")),
                   "bin")
    expect_refusal("non-bin start refused (10:30)",
                   lambda: j2.append(signal_fire(
                       symbol="EEE", signal_idx=10,
                       signal_time="2025-11-03T10:30:00-05:00",
                       decision_time="2025-11-03T13:30:00-05:00",
                       recorded_at="2025-11-03T13:30:05-05:00")),
                   "bin")
    expect_refusal("beyond-table date refused (2026-11-02)",
                   lambda: j2.append(signal_fire(
                       symbol="EEE", signal_idx=10,
                       signal_time="2026-11-02T09:30:00-05:00",
                       decision_time="2026-11-02T13:30:00-05:00",
                       recorded_at="2026-11-02T13:30:05-05:00")),
                   "bin")

    # EXECUTION gating (retained from -29).
    expect_refusal("EXECUTION refused in signal-only mode",
                   lambda: j.append({
                       "record_type": "EXECUTION", "symbol": "AAA",
                       "signal_idx": 300, "leg": "entry",
                       "order_time": "2025-11-03T13:30:00-05:00",
                       "ack_time": "2025-11-03T13:30:01-05:00",
                       "fill_time": "2025-11-03T13:30:01-05:00",
                       "fill_price": 101.4, "order_id": "x1",
                       "recorded_at": "2025-11-03T13:30:02-05:00"}),
                   "signal-only")
    jx = qt.TelemetryJournal(execution_authorized=True)
    jx.append({
        "record_type": "EXECUTION", "symbol": "AAA", "signal_idx": 300,
        "leg": "entry", "order_time": "2025-11-03T13:30:00-05:00",
        "ack_time": "2025-11-03T13:30:01-05:00",
        "fill_time": "2025-11-03T13:30:01-05:00", "fill_price": 101.4,
        "order_id": "x1", "recorded_at": "2025-11-03T13:30:02-05:00"})
    check("EXECUTION accepted when execution_authorized",
          len(jx.lines) == 1)

    # Tamper evidence: flip a value in line 2 -> verify fails there.
    lines = list(j.lines)
    rec = json.loads(lines[1])
    rec["entry_price"] = 1.0
    lines[1] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    ok, bad = qt.verify_lines(lines)
    check("tampered line detected at its index", (not ok) and bad == 1,
          f"ok={ok} bad={bad}")

    # File-backed journal: reload verifies chain; tampered file refuses.
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "journal.jsonl")
        jf = qt.TelemetryJournal(path=p)
        jf.append(signal_fire(symbol="BBB", signal_idx=10))
        jf.append(entry_observed(symbol="BBB", signal_idx=10))
        jf2 = qt.TelemetryJournal(path=p)
        check("file journal reloads + chain ok (links re-tracked)",
              len(jf2.lines) == 2)
        with open(p, "a") as f:
            f.write('{"record_type":"SIGNAL_FIRE","prev_hash":"x",'
                    '"record_hash":"y"}\n')
        expect_refusal("tampered file refused on load",
                       lambda: qt.TelemetryJournal(path=p), "chain")

    print("SUMMARY", "FAIL" if FAILURES else "PASS", FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
