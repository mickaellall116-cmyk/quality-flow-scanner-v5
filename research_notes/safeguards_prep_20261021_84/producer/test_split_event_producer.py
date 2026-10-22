#!/usr/bin/env python3
"""
test_split_event_producer.py — SYNTHETIC FIXTURES for the split-event
producer deterministic core (task -84, Part B; GATE-E1…E5).

All inputs are synthetic: a hand-built XNYS-like calendar for
Jun–Jul 2024 and invented event records. No vendor data, no live
source, no network. The core under test is
producer/split_event_producer.py (isolated candidate, not integrated).

Calendar facts used below (real 2024 XNYS shape, supplied as fixture
data — the producer itself consults ONLY this object):
  sessions: weekdays 2024-05-29..2024-07-17 EXCEPT 2024-06-19
  (Juneteenth) and 2024-07-04 (Independence Day);
  early close: 2024-07-03.
Bars window for most cases: 2024-06-03..2024-07-12, so the first
in-window session is Mon 2024-06-03, prev session Fri 2024-05-31,
last in-window session Fri 2024-07-12, next session Mon 2024-07-15;
inclusion range = [2024-05-31, 2024-07-15].

Cases:
  P1  basic enumeration + envelope stamps + S2-contract fields.
  P2  stated effective on a non-session (Saturday; a holiday) ->
      normalized to the next session, EDGE flag, stated date kept.
  P3  effective on an early-close session -> kept, EDGE flag.
  P4  PIT: mode A excludes after-decision events (ledger records
      them); mode B includes them flagged + basis flips to
      RETROSPECTIVE_NON_TRADABLE; mode unset -> E3_MODE_UNSET.
  P5  duplicate (identical) and conflicting (same key, other factor)
      records -> DUPLICATE_OR_CONFLICTING_EVENT.
  P6  absent source -> state NO_PRODUCER_OUTPUT, events None;
      covered source with zero records -> state OK, events []
      (the two states are visibly different).
  P7  coverage: uncovered symbol / window beyond coverage ->
      COVERAGE_INCOMPLETE.
  P8  calendar not extending beyond the bars span ->
      CALENDAR_RANGE_INSUFFICIENT.
  P9  provenance: missing acquired_at -> PROVENANCE_UNBOUND;
      announced_at after dataset cutoff -> AS_OF_AFTER_DATASET_CUTOFF.
  P10 determinism: identical inputs -> byte-identical envelopes.
  P11 adjacency scope: an event effective the session just BEFORE
      the window is included; one far outside is not (and not an
      error).
  P12 malformed records: missing field -> MISSING_FIELD;
      non-positive factor -> INVALID_FACTOR.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import split_event_producer as P  # noqa: E402

RESULTS = []


def case(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")


def expect_refusal(name, code, fn):
    try:
        fn()
        case(name, False, "no refusal raised")
    except P.ProducerRefusal as e:
        case(name, e.code == code, f"raised {e.code}: {e.detail}")
    except Exception as e:  # noqa: BLE001
        case(name, False, f"wrong exception {type(e).__name__}: {e}")


def make_calendar(sessions=None):
    if sessions is None:
        days = []
        d = date(2024, 5, 29)
        while d <= date(2024, 7, 17):
            if d.weekday() < 5 and d not in (date(2024, 6, 19), date(2024, 7, 4)):
                days.append(d.isoformat())
            d += timedelta(days=1)
        sessions = days
    return P.Calendar(sessions, ["2024-07-03"], source="SYNTHETIC_FIXTURE_CALENDAR",
                      version="fixture-1", pin="fixture-pin-0000")


CAL = make_calendar()
DATASET_AS_OF = "2024-07-20T00:00:00+00:00"
DECISION = "2024-06-01T13:30:00+00:00"  # before all in-window decisions


def batch(records, **over):
    b = {
        "acquired_at": "2024-07-19T12:00:00+00:00",
        "source_pin": "synthetic-source-pin-1234",
        "coverage": {"symbols": ["NVDAX", "TSLAX", "AAPLX"],
                     "window_start": "2024-05-01", "window_end": "2024-08-31"},
        "records": records,
    }
    b.update(over)
    return b


def rec(symbol, eff, num, den, announced, source="SYNTHETIC_SOURCE"):
    return {"symbol": symbol, "effective_date": eff, "factor_num": num,
            "factor_den": den, "announced_at": announced, "source": source}


def run(b, **kw):
    args = dict(symbols=["NVDAX", "TSLAX", "AAPLX"], bars_start="2024-06-03",
                bars_end="2024-07-12", dataset_as_of=DATASET_AS_OF,
                decision_instant=DECISION, e3_mode="A")
    args.update(kw)
    return P.produce(b, CAL, **args)


def main():
    # P1 — basic enumeration.
    env = run(batch([
        rec("NVDAX", "2024-06-10", 10, 1, "2024-05-02T20:05:00+00:00"),
        rec("TSLAX", "2024-06-21", 3, 1, "2024-05-20T20:05:00+00:00"),
    ]))
    ev = env["events"]
    case("P1_state_ok", env["state"] == "OK" and env["event_count"] == 2)
    case("P1_sorted_and_shaped",
         [(e["symbol"], e["effective_session"]) for e in ev]
         == [("NVDAX", "2024-06-10"), ("TSLAX", "2024-06-21")]
         and ev[0]["factor_num"] == 10 and ev[0]["factor_den"] == 1)
    s2_fields = ("symbol", "effective_session", "source", "provenance", "as_of", "version")
    case("P1_s2_contract_fields",
         all(all(e.get(f) not in (None, "") for f in s2_fields) for e in ev))
    case("P1_envelope_stamps",
         env["calendar"]["pin"] == "fixture-pin-0000"
         and env["source_pin"] == "synthetic-source-pin-1234"
         and env["inclusion_range"] == ["2024-05-31", "2024-07-15"]
         and env["basis"] == "DECISION_TIME" and len(env["events_sha256"]) == 64)

    # P2 — non-session stated dates normalize to the next session.
    env2 = run(batch([
        rec("NVDAX", "2024-06-08", 2, 1, "2024-05-02T20:05:00+00:00"),   # Saturday
        rec("TSLAX", "2024-07-04", 3, 1, "2024-05-20T20:05:00+00:00"),   # holiday
    ]))
    by_sym = {e["symbol"]: e for e in env2["events"]}
    case("P2_saturday_normalized",
         by_sym["NVDAX"]["effective_session"] == "2024-06-10"
         and by_sym["NVDAX"]["effective_date_stated"] == "2024-06-08"
         and "EDGE_NONSESSION_STATED_DATE" in by_sym["NVDAX"]["edge_flags"])
    case("P2_holiday_normalized",
         by_sym["TSLAX"]["effective_session"] == "2024-07-05"
         and "EDGE_NONSESSION_STATED_DATE" in by_sym["TSLAX"]["edge_flags"])

    # P3 — early-close session keeps its session, flagged.
    env3 = run(batch([rec("AAPLX", "2024-07-03", 5, 4, "2024-05-25T20:05:00+00:00")]))
    case("P3_early_close_flagged",
         env3["events"][0]["effective_session"] == "2024-07-03"
         and "EDGE_EARLY_CLOSE_SESSION" in env3["events"][0]["edge_flags"]
         and "EDGE_NONSESSION_STATED_DATE" not in env3["events"][0]["edge_flags"])

    # P4 — PIT modes behind the unfrozen E3 switch.
    late = rec("NVDAX", "2024-06-10", 10, 1, "2024-06-05T20:05:00+00:00")  # after DECISION
    envA = run(batch([late]), e3_mode="A")
    case("P4_modeA_excludes",
         envA["event_count"] == 0 and len(envA["excluded"]) == 1
         and envA["excluded"][0]["excluded_reason"] == "PIT_ANNOUNCED_AFTER_DECISION"
         and envA["basis"] == "DECISION_TIME")
    envB = run(batch([late]), e3_mode="B")
    case("P4_modeB_includes_flagged",
         envB["event_count"] == 1
         and envB["events"][0]["pit_status"] == "ANNOUNCED_AFTER_DECISION"
         and envB["basis"] == "RETROSPECTIVE_NON_TRADABLE")
    expect_refusal("P4_mode_unset_refuses", "E3_MODE_UNSET",
                   lambda: run(batch([late]), e3_mode=None))

    # P5 — duplicates and conflicts fail closed.
    r = rec("NVDAX", "2024-06-10", 10, 1, "2024-05-02T20:05:00+00:00")
    expect_refusal("P5_identical_duplicate", "DUPLICATE_OR_CONFLICTING_EVENT",
                   lambda: run(batch([r, dict(r)])))
    expect_refusal("P5_conflicting_duplicate", "DUPLICATE_OR_CONFLICTING_EVENT",
                   lambda: run(batch([r, rec("NVDAX", "2024-06-10", 5, 1,
                                             "2024-05-03T20:05:00+00:00")])))

    # P6 — absent source is a state, not an empty list.
    env_none = run(None)
    case("P6_no_producer_output_state",
         env_none["state"] == "NO_PRODUCER_OUTPUT" and env_none["events"] is None)
    env_empty = run(batch([]))
    case("P6_covered_empty_is_ok_zero",
         env_empty["state"] == "OK" and env_empty["events"] == []
         and env_empty["event_count"] == 0)

    # P7 — coverage is proven, not assumed.
    expect_refusal("P7_uncovered_symbol", "COVERAGE_INCOMPLETE",
                   lambda: run(batch([]), symbols=["NVDAX", "MSFTX"]))
    expect_refusal("P7_window_beyond_coverage", "COVERAGE_INCOMPLETE",
                   lambda: run(batch([]), bars_end="2024-09-15"))

    # P8 — calendar must extend beyond the bars span on both sides.
    short_cal = make_calendar(sessions=[d.isoformat() for d in CAL.sessions
                                        if date(2024, 6, 3) <= d <= date(2024, 7, 12)])
    expect_refusal("P8_calendar_range", "CALENDAR_RANGE_INSUFFICIENT",
                   lambda: P.produce(batch([]), short_cal,
                                     symbols=["NVDAX"], bars_start="2024-06-03",
                                     bars_end="2024-07-12",
                                     dataset_as_of=DATASET_AS_OF,
                                     decision_instant=DECISION, e3_mode="A"))

    # P9 — provenance binding (GATE-E3).
    b_no_ts = batch([]); b_no_ts.pop("acquired_at")
    expect_refusal("P9_missing_acquired_at", "PROVENANCE_UNBOUND", lambda: run(b_no_ts))
    expect_refusal("P9_asof_after_cutoff", "AS_OF_AFTER_DATASET_CUTOFF",
                   lambda: run(batch([rec("NVDAX", "2024-06-10", 10, 1,
                                          "2024-07-25T20:05:00+00:00")])))

    # P10 — determinism: byte-identical envelopes on repeat.
    import json
    b10 = batch([rec("NVDAX", "2024-06-10", 10, 1, "2024-05-02T20:05:00+00:00"),
                 rec("TSLAX", "2024-07-04", 3, 1, "2024-05-20T20:05:00+00:00")])
    s1 = json.dumps(run(b10), sort_keys=True)
    s2 = json.dumps(run(b10), sort_keys=True)
    case("P10_deterministic_envelope", s1 == s2)

    # P11 — adjacency scope: prev-session event in, far-outside event out.
    env11 = run(batch([
        rec("NVDAX", "2024-05-31", 2, 1, "2024-05-02T20:05:00+00:00"),  # prev session
        rec("TSLAX", "2024-05-29", 3, 1, "2024-05-02T20:05:00+00:00"),  # outside range
    ]))
    case("P11_adjacency_scope",
         [e["symbol"] for e in env11["events"]] == ["NVDAX"]
         and env11["events"][0]["effective_session"] == "2024-05-31")

    # P12 — malformed records.
    bad = rec("NVDAX", "2024-06-10", 10, 1, "2024-05-02T20:05:00+00:00"); bad.pop("source")
    expect_refusal("P12_missing_field", "MISSING_FIELD", lambda: run(batch([bad])))
    expect_refusal("P12_invalid_factor", "INVALID_FACTOR",
                   lambda: run(batch([rec("NVDAX", "2024-06-10", 0, 1,
                                          "2024-05-02T20:05:00+00:00")])))

    n_pass = sum(1 for _, ok in RESULTS if ok)
    print(f"\n{n_pass}/{len(RESULTS)} checks passed")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
