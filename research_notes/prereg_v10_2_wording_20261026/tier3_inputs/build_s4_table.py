#!/usr/bin/env python3
"""Build the FROZEN S4 aggregate table for the Tier 3 v1.0.1 amendment
(C1 finding 1) from the captured 2026-10-26 generator run outputs.

What the v1.0/v1.1 generator persisted (and therefore what can be frozen):
each run's tier3_list*.json output contains ONLY the 12 selected symbols'
step-8 aggregates (ADV20, last close, bars used) plus stage counts. The
per-candidate aggregates for the other 2,549 step-7 candidates were computed
in memory and never written to disk, in any run. This builder therefore
freezes exactly what exists — the 12 selected symbols' aggregates — and the
accompanying INPUTS_AND_GAPS.md discloses the gap precisely. No data is
fetched; this script reads only the captured run outputs in the Tier 3
staging directory.

Fail-closed: the three agreeing run outputs (runs 1, 3, 4) must be
byte-identical, and run 2's selection must match theirs, before any row
is emitted.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TIER3_STAGE = Path.home() / "workspace/qf_prereg_v10_stage/tier3_rule"
OUT = HERE / "S4_FROZEN_AGGREGATES.csv"
EXPECT_OUTPUT_SHA = "9e7ae05261b02cd6fde20909f86332a7b6cfda82bc330094136f56aba71f5d4e"
PROVENANCE = ("Yahoo Finance daily bars fetched 2026-10-26 for the 2561 "
              "step-7 candidates (public web data, no licensed API key); "
              "aggregate persisted in generator run outputs 1/3/4 "
              "(byte-identical, sha256 "
              "9e7ae05261b02cd6fde20909f86332a7b6cfda82bc330094136f56aba71f5d4e)")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    agreeing = []
    for name in ("tier3_list_run1.json", "tier3_list_run3.json",
                 "tier3_list.json"):
        raw = (TIER3_STAGE / name).read_bytes()
        if sha256_bytes(raw) != EXPECT_OUTPUT_SHA:
            print(f"FAIL: {name} hash mismatch — refusing to build S4 table")
            return 1
        agreeing.append(json.loads(raw))
    run2 = json.loads((TIER3_STAGE / "tier3_list_run2.json").read_text())
    sel = lambda d: [(e["symbol"], e["adv20_usd"], e["last_close_usd"],
                      e["bars_used"]) for e in d["tier3_list"]]
    if sel(run2) != sel(agreeing[0]):
        print("FAIL: run 2 selection differs from runs 1/3/4 — refusing")
        return 1

    rows = sel(agreeing[0])
    lines = ["symbol,sessions_window,bars_used,adv20_usd,last_close_usd,provenance"]
    for sym, adv, lc, nb in rows:
        lines.append(
            f'{sym},"completed sessions 2026-09-01..2026-10-25 '
            f'(last {nb} valid bars)",{nb},{adv:.2f},{lc:.4f},"{PROVENANCE}"')
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT} sha256={sha256_bytes(OUT.read_bytes())} rows={len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
