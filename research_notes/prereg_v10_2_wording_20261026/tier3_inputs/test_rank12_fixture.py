#!/usr/bin/env python3
"""Fixture for the v1.0.2 wording amendment (C1 re-review, Issue #1
comment 6429562606): the unknown rank-12 slot of the Tier 3 residual
list must remain EXPLICITLY empty.

Asserts, against the sibling regenerated output `tier3_list_v1_2.json`:

  1. The list has exactly 11 entries, with contiguous ranks 1..11 and
     no rank-12 entry.
  2. The output records `rank_12: null` with a `rank_12_status`
     stating UNKNOWN.
  3. The 2,549 step-7 candidates without a persisted S4 aggregate are
     recorded under the corrected label
     `s8_aggregate_not_persisted__not_re_evaluated` (= 2549), and the
     superseded label `s8_candidates_without_frozen_aggregate_fail_closed`
     appears nowhere in the output.
  4. The derivation is recorded as a residual list (original proven
     top-12 minus issuer-ineligible GOOG), and `selected_count` /
     `shortfall_vs_list_size` are 11 / 1.
  5. The 11 symbols are exactly, in order: BE, ACN, IREN, CRDO, TWLO,
     AAOI, MPWR, SPOT, BABA, COF, BLK.

Run: python3 test_rank12_fixture.py   (exit 0 = all assertions hold)
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "tier3_list_v1_2.json"
EXPECTED_SYMBOLS = ["BE", "ACN", "IREN", "CRDO", "TWLO", "AAOI",
                    "MPWR", "SPOT", "BABA", "COF", "BLK"]


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}: {name}")
    return bool(cond)


def main() -> int:
    raw = OUT.read_text()
    data = json.loads(raw)
    lst = data["tier3_list"]
    stage = data["stage_counts"]
    ok = True

    ok &= check("list has exactly 11 entries", len(lst) == 11)
    ok &= check("ranks are contiguous 1..11",
                [e["rank"] for e in lst] == list(range(1, 12)))
    ok &= check("no rank-12 entry in the list",
                all(e["rank"] != 12 for e in lst))
    ok &= check("rank_12 is recorded as null", data.get("rank_12") is None)
    ok &= check("rank_12_status states UNKNOWN",
                "UNKNOWN" in str(data.get("rank_12_status", "")))
    ok &= check("corrected label present with value 2549",
                stage.get("s8_aggregate_not_persisted__not_re_evaluated")
                == 2549)
    ok &= check("superseded fail_closed label absent from output",
                "s8_candidates_without_frozen_aggregate_fail_closed"
                not in raw)
    ok &= check("derivation recorded as residual_list",
                str(data.get("derivation", "")).startswith("residual_list"))
    ok &= check("selected_count == 11 and shortfall == 1",
                data.get("selected_count") == 11
                and data.get("shortfall_vs_list_size") == 1)
    ok &= check("symbols exactly the expected residual top-11, in order",
                [e["symbol"] for e in lst] == EXPECTED_SYMBOLS)

    print("FIXTURE RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
