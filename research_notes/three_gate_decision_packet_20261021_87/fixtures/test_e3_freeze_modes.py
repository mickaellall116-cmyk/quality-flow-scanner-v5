#!/usr/bin/env python3
"""
test_e3_freeze_modes.py — Gate 2 fixtures (task -87).

Drives the -84 split-event producer core (byte copy in
fixtures/inputs/split_event_producer.py, sha256 ffa14a8d8dd28975...,
from research_notes/safeguards_prep_20261021_84/producer/, package
f7725bf) against the EXACT semantics the Gate 2 freeze texts propose:

  F-A (mode A, decision-time): an event may affect a decision only if
      its independently sourced announced_at <= the decision instant;
      later-announced events are EXCLUDED from that decision's event
      list (ledgered, never silent); equality (announced == decision)
      is INCLUDED (<= semantics).
  F-B (mode B, retrospective): later-announced events are INCLUDED,
      flagged, and the envelope basis flips to
      RETROSPECTIVE_NON_TRADABLE — it can never read as decision-time.
  BOTH: mode unset refuses (E3_MODE_UNSET — no default exists);
      a record without announced_at refuses (MISSING_FIELD — timing
      unknown is not evaluable, never defaulted); an event announced
      after the dataset as_of cutoff refuses the whole run
      (AS_OF_AFTER_DATASET_CUTOFF — a provenance defect in any mode).

Synthetic calendar/records (same fixture family as the -84 suite).
Offline, stdlib only. Exit 1 on any FAIL.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "inputs"))
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
        case(name, e.code == code, f"raised {e.code}")
    except Exception as e:  # noqa: BLE001
        case(name, False, f"wrong exception {type(e).__name__}: {e}")


def make_calendar():
    days = []
    d = date(2024, 5, 29)
    while d <= date(2024, 7, 17):
        if d.weekday() < 5 and d not in (date(2024, 6, 19), date(2024, 7, 4)):
            days.append(d.isoformat())
        d += timedelta(days=1)
    return P.Calendar(days, ["2024-07-03"], source="SYNTHETIC_FIXTURE_CALENDAR",
                      version="fixture-1", pin="fixture-pin-0000")


CAL = make_calendar()
DATASET_AS_OF = "2024-07-20T00:00:00+00:00"
DECISION = "2024-06-01T13:30:00+00:00"


def batch(records):
    return {"acquired_at": "2024-07-19T12:00:00+00:00",
            "source_pin": "synthetic-source-pin-1234",
            "coverage": {"symbols": ["NVDAX"], "window_start": "2024-05-01",
                         "window_end": "2024-08-31"},
            "records": records}


def rec(announced, eff="2024-06-10"):
    r = {"symbol": "NVDAX", "effective_date": eff, "factor_num": 10,
         "factor_den": 1, "source": "SYNTHETIC_SOURCE"}
    if announced is not None:
        r["announced_at"] = announced
    return r


def run(records, mode):
    return P.produce(batch(records), CAL, symbols=["NVDAX"],
                     bars_start="2024-06-03", bars_end="2024-07-12",
                     dataset_as_of=DATASET_AS_OF, decision_instant=DECISION,
                     e3_mode=mode)


BEFORE = "2024-05-02T20:05:00+00:00"       # announced before the decision
AFTER = "2024-06-05T20:05:00+00:00"        # announced after the decision
EQUAL = DECISION                           # announced exactly at the decision
PAST_CUTOFF = "2024-07-21T00:00:00+00:00"  # announced after dataset as_of


def main():
    # E3-1/E3-2 — fail-closed switch.
    expect_refusal("E3-1_unset_refuses", "E3_MODE_UNSET",
                   lambda: run([rec(BEFORE)], None))
    expect_refusal("E3-2_invalid_mode_refuses", "E3_MODE_INVALID",
                   lambda: run([rec(BEFORE)], "C"))

    # E3-3 — mode A, announced before decision: included, clean basis.
    env = run([rec(BEFORE)], "A")
    case("E3-3_modeA_before_included", env["event_count"] == 1
         and env["basis"] == "DECISION_TIME" and env["excluded"] == [],
         f"basis={env['basis']}")

    # E3-4 — mode A, announced after decision: excluded + ledgered.
    env = run([rec(AFTER)], "A")
    case("E3-4_modeA_after_excluded", env["event_count"] == 0
         and len(env["excluded"]) == 1
         and env["excluded"][0]["excluded_reason"] == "PIT_ANNOUNCED_AFTER_DECISION"
         and env["basis"] == "DECISION_TIME",
         f"excluded={len(env['excluded'])}")

    # E3-5 — mode A boundary: announced == decision instant is INSIDE
    # the rule (<= semantics written into freeze text F-A).
    env = run([rec(EQUAL)], "A")
    case("E3-5_modeA_equality_included", env["event_count"] == 1
         and env["events"][0]["pit_status"] == "ANNOUNCED_ON_OR_BEFORE_DECISION",
         "announced_at == decision -> included")

    # E3-6 — mode B, announced after decision: included, flagged,
    # basis flips so it can never read as decision-time.
    env = run([rec(AFTER)], "B")
    case("E3-6_modeB_after_flagged_nontradable", env["event_count"] == 1
         and env["events"][0]["pit_status"] == "ANNOUNCED_AFTER_DECISION"
         and env["basis"] == "RETROSPECTIVE_NON_TRADABLE",
         f"basis={env['basis']}")

    # E3-7 — mode B with nothing after the decision: basis stays
    # DECISION_TIME (no gratuitous flip).
    env = run([rec(BEFORE)], "B")
    case("E3-7_modeB_clean_stays_decision_time",
         env["basis"] == "DECISION_TIME" and env["event_count"] == 1,
         f"basis={env['basis']}")

    # E3-8 — timing unknown: a record with NO announced_at refuses in
    # both modes (never defaulted, never treated as timely).
    expect_refusal("E3-8a_missing_announced_modeA", "MISSING_FIELD",
                   lambda: run([rec(None)], "A"))
    expect_refusal("E3-8b_missing_announced_modeB", "MISSING_FIELD",
                   lambda: run([rec(None)], "B"))

    # E3-9 — announced after the dataset cutoff refuses the whole run
    # in both modes (provenance defect, not a PIT-mode question).
    expect_refusal("E3-9a_past_cutoff_modeA", "AS_OF_AFTER_DATASET_CUTOFF",
                   lambda: run([rec(PAST_CUTOFF)], "A"))
    expect_refusal("E3-9b_past_cutoff_modeB", "AS_OF_AFTER_DATASET_CUTOFF",
                   lambda: run([rec(PAST_CUTOFF)], "B"))

    n_fail = sum(1 for _, ok in RESULTS if not ok)
    print(f"\n{len(RESULTS) - n_fail}/{len(RESULTS)} PASS")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
