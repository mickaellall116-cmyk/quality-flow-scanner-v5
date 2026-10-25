"""30 battery: transactional append + restart revalidation + horizon
acceptance (the -29r verdict's P8 blockers, exercised directly).

Run: python3 tests/test_telemetry_txn.py  (exit 0 = all hold)

The 29r defect, proven here as fail-before semantics in the test
design: _track() mutated before its final check, so a backdated
SIGNAL_FIRE advanced _last_signal_idx and inserted _fire_bin, then
raised on stream monotonicity — a refusal that CHANGED the journal
(a ghost parent a later ENTRY_OBSERVED could attach to). Every
fixture below snapshots the full journal state (lines, chain head,
and all four tracking dicts) and requires byte-identity after a
refusal, then proves the journal still works: the same signal_idx
accepts a valid record, and observations attach only to parents
that were actually accepted.
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


def snapshot(j):
    return (list(j.lines), j._last_hash, dict(j._last_signal_idx),
            dict(j._last_stream_time), dict(j._fire_bin),
            dict(j._exit_bin))


def signal_fire(**over):
    r = {
        "record_type": "SIGNAL_FIRE", "symbol": "AAA", "signal_idx": 300,
        "signal_time": "2025-11-03T09:30:00-05:00",
        "decision_time": "2025-11-03T13:30:00-05:00",
        "recorded_at": "2025-11-03T13:30:05-05:00",
        "bar_finalized": True,
        "predicates": {"confirmed": True, "breakout_buy": False,
                       "ready_buy": False, "score": 4,
                       "score_threshold": 4},
        "adx": 27.5, "di_plus": 30.1, "di_minus": 12.4,
        "trend_score": 4, "vwap_distance": 0.012, "rel_volume": 1.35,
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
    r = {"record_type": "ENTRY_OBSERVED", "symbol": "AAA",
         "signal_idx": 300, "entry_time": "2025-11-03T13:30:00-05:00",
         "entry_price": 101.4, "atr": 2.5, "tp1_level": 106.05,
         "recorded_at": "2025-11-03T13:30:06-05:00"}
    r.update(over)
    return r


def exit_decision(**over):
    r = {"record_type": "EXIT_DECISION", "symbol": "BBB",
         "signal_idx": 400, "decision_bar_idx": 405,
         "decision_bar_time": "2025-11-04T09:30:00-05:00",
         "decision_time": "2025-11-04T13:30:00-05:00",
         "recorded_at": "2025-11-04T13:30:05-05:00",
         "bar_finalized": True, "decision_bar_open": 99.0,
         "decision_bar_high": 99.4, "decision_bar_low": 96.8,
         "decision_bar_close": 97.0, "runner_in_force": 97.25,
         "ema55_in_force": 99.1, "decision": "exit",
         "exit_reason": "stop"}
    r.update(over)
    return r


def exit_fill(**over):
    r = {"record_type": "EXIT_FILL_OBSERVED", "symbol": "BBB",
         "signal_idx": 400, "fill_time": "2025-11-04T13:30:00-05:00",
         "fill_price": 98.9,
         "recorded_at": "2025-11-04T13:30:06-05:00"}
    r.update(over)
    return r


def main():
    # ---- Horizon acceptance (union calendar) ----------------------
    j = qt.TelemetryJournal()
    j.append(signal_fire(
        symbol="PLT", signal_idx=1,
        signal_time="2026-10-27T09:30:00-04:00",
        decision_time="2026-10-27T13:30:00-04:00",
        recorded_at="2026-10-27T13:30:05-04:00",
        benchmark_asof="2026-10-26T16:00:00-04:00"))
    j.append(entry_observed(
        symbol="PLT", signal_idx=1,
        entry_time="2026-10-27T13:30:00-04:00",
        recorded_at="2026-10-27T13:30:06-04:00"))
    check("pilot-week fire + entry observation append (2026-10-27)",
          len(j.lines) == 2)
    j.append(signal_fire(
        symbol="ECL", signal_idx=1,
        signal_time="2026-11-27T09:30:00-05:00",
        decision_time="2026-11-27T13:00:00-05:00",
        recorded_at="2026-11-27T13:00:05-05:00",
        benchmark_asof="2026-11-25T16:00:00-05:00"))
    check("extension early-close fire appends (2026-11-27, 13:00)",
          len(j.lines) == 3)
    expect_refusal("extension holiday refused (Thanksgiving 2026)",
                   lambda: j.append(signal_fire(
                       symbol="HOL", signal_idx=1,
                       signal_time="2026-11-26T09:30:00-05:00",
                       decision_time="2026-11-26T13:30:00-05:00",
                       recorded_at="2026-11-26T13:30:05-05:00")),
                   "bin")

    # ---- SIGNAL_FIRE poisoning ------------------------------------
    j = qt.TelemetryJournal()
    j.append(signal_fire(signal_idx=300,
                         signal_time="2025-11-03T13:30:00-05:00",
                         decision_time="2025-11-03T16:00:00-05:00",
                         recorded_at="2025-11-03T16:00:05-05:00"))
    snap = snapshot(j)
    # Backdated second fire: idx advances and (in 29r) the fire bin
    # was inserted BEFORE the stream check raised.
    expect_refusal("backdated SIGNAL_FIRE refused (stream order)",
                   lambda: j.append(signal_fire(signal_idx=301)),
                   "backfill")
    check("state byte-identical after refused SIGNAL_FIRE",
          snapshot(j) == snap)
    # No ghost parent: an entry observation for the rejected fire
    # must refuse as parentless (in 29r it attached to the ghost).
    expect_refusal("ENTRY_OBSERVED cannot attach to a rejected fire",
                   lambda: j.append(entry_observed(signal_idx=301)),
                   "no prior SIGNAL_FIRE")
    check("state byte-identical after ghost-attach refusal",
          snapshot(j) == snap)
    # The real parent still works, and the rejected index is
    # reusable by a valid later fire.
    j.append(entry_observed(
        signal_idx=300, entry_time="2025-11-04T09:30:00-05:00",
        recorded_at="2025-11-04T09:30:06-05:00"))
    check("ENTRY_OBSERVED appends for the accepted fire",
          len(j.lines) == 2)
    j.append(signal_fire(signal_idx=301,
                         signal_time="2025-11-04T13:30:00-05:00",
                         decision_time="2025-11-04T16:00:00-05:00",
                         recorded_at="2025-11-04T16:00:05-05:00"))
    check("same signal_idx accepts a valid record after refusal",
          len(j.lines) == 3)

    # A validation-stage refusal is likewise mutation-free.
    snap = snapshot(j)
    r = signal_fire(signal_idx=302)
    r["invented_field"] = 1
    expect_refusal("unknown-field refusal", lambda: j.append(r),
                   "unknown fields")
    check("state byte-identical after validation refusal",
          snapshot(j) == snap)

    # ---- EXIT_DECISION poisoning ----------------------------------
    j = qt.TelemetryJournal()
    j.append(signal_fire(symbol="BBB", signal_idx=400))
    j.append(exit_decision())
    snap = snapshot(j)
    # A second, earlier decision for the same position: in 29r this
    # overwrote _exit_bin BEFORE the stream check raised, silently
    # re-parenting the position's fill link to the wrong bar.
    expect_refusal("backdated second EXIT_DECISION refused",
                   lambda: j.append(exit_decision(
                       decision_bar_idx=402,
                       decision_bar_time="2025-11-03T13:30:00-05:00",
                       decision_time="2025-11-03T16:00:00-05:00",
                       recorded_at="2025-11-03T16:00:05-05:00")),
                   "backfill")
    check("state byte-identical after refused EXIT_DECISION",
          snapshot(j) == snap)
    expect_refusal("fill against the rejected decision's bin refused",
                   lambda: j.append(exit_fill(
                       fill_time="2025-11-04T09:30:00-05:00",
                       recorded_at="2025-11-04T09:30:06-05:00")),
                   "next bin start")
    j.append(exit_fill())
    check("fill appends against the accepted decision",
          len(j.lines) == 3)
    expect_refusal("EXIT_FILL_OBSERVED cannot attach to a rejected "
                   "decision (no decision ever accepted for idx 999)",
                   lambda: j.append(exit_fill(signal_idx=999)),
                   "no prior EXIT_DECISION")

    # ---- File-backed: refusal writes nothing -----------------------
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "journal.jsonl")
        jf = qt.TelemetryJournal(path=p)
        jf.append(signal_fire(symbol="FIL", signal_idx=10))
        before = open(p, "rb").read()
        expect_refusal("file journal: duplicate idx refused",
                       lambda: jf.append(signal_fire(
                           symbol="FIL", signal_idx=10)),
                       "strictly increasing")
        check("file bytes identical after refusals",
              open(p, "rb").read() == before)
        jf2 = qt.TelemetryJournal(path=p)
        check("file journal reloads cleanly after refusals",
              len(jf2.lines) == 1)

    # ---- Restart guard: hash-valid, semantically invalid ----------
    def crafted_line(record, prev_hash):
        record = dict(record)
        record["prev_hash"] = prev_hash
        record["record_hash"] = qt.record_hash(record)
        return json.dumps(record, sort_keys=True,
                          separators=(",", ":"))

    with tempfile.TemporaryDirectory() as d:
        # (a) decision stamped 17:30 — chain and hashes are correct;
        # only semantics are wrong. 29r accepted this state on load.
        p = os.path.join(d, "poison1.jsonl")
        bad = signal_fire(signal_idx=700,
                          signal_time="2025-11-03T13:30:00-05:00",
                          decision_time="2025-11-03T17:30:00-05:00",
                          recorded_at="2025-11-03T17:30:05-05:00")
        with open(p, "w") as f:
            f.write(crafted_line(bad, "GENESIS") + "\n")
        expect_refusal("restart refuses hash-valid 17:30 decision",
                       lambda: qt.TelemetryJournal(path=p), "bin_end")
        # (b) unfinalized bar, hash-valid.
        p = os.path.join(d, "poison2.jsonl")
        bad = signal_fire(signal_idx=700, bar_finalized=False)
        with open(p, "w") as f:
            f.write(crafted_line(bad, "GENESIS") + "\n")
        expect_refusal("restart refuses hash-valid unfinalized bar",
                       lambda: qt.TelemetryJournal(path=p),
                       "bar_finalized")
        # (c) unknown field, hash-valid, chained after a valid line.
        p = os.path.join(d, "poison3.jsonl")
        jf = qt.TelemetryJournal(path=p)
        jf.append(signal_fire(symbol="RLD", signal_idx=10))
        head = json.loads(jf.lines[-1])["record_hash"]
        bad = signal_fire(symbol="RLD", signal_idx=11,
                          signal_time="2025-11-03T13:30:00-05:00",
                          decision_time="2025-11-03T16:00:00-05:00",
                          recorded_at="2025-11-03T16:00:05-05:00")
        bad["smuggled"] = True
        with open(p, "a") as f:
            f.write(crafted_line(bad, head) + "\n")
        expect_refusal("restart refuses hash-valid unknown field",
                       lambda: qt.TelemetryJournal(path=p),
                       "unknown fields")
        # (d) a fully valid two-line journal still loads.
        p = os.path.join(d, "clean.jsonl")
        jf = qt.TelemetryJournal(path=p)
        jf.append(signal_fire(symbol="RLD", signal_idx=10))
        jf.append(entry_observed(symbol="RLD", signal_idx=10))
        jf2 = qt.TelemetryJournal(path=p)
        check("valid journal reloads under the restart guard",
              len(jf2.lines) == 2)

    print("SUMMARY", "FAIL" if FAILURES else "PASS", FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
