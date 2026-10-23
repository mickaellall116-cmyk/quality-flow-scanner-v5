"""QF-EQUITY-PIT-INTEGRITY-20261023-09 — B3 terminal-open coverage tally.

ZERO-P&L / COVERAGE-ONLY diagnostic on the SAME admitted DEV bytes and the
SAME phase pipeline as the -08 run (stage run_diagnostic.py phases 0-2,
imported read-only; phase 3 is never called — no portfolio, no performance).

Question answered (count only): the frozen pine_ranking.gen_candidates emits
only CLOSED trades. How many candidate positions were still open when the DEV
window ended and were therefore silently censored from the -08 ledger?

Method: run the pinned original gen_candidates (file hash asserted) for the
closed count; then run a counting variant produced by a mechanical, diffed
transformation of the extracted function source — the ONLY change replaces
the final `return trades, skipped_gap` with a terminal-position capture plus
`return trades, skipped_gap, _terminal`. The variant's closed-trade list is
asserted identical to the original's (symbol, signal_idx, entry_time) before
its terminal count is believed. No prices are aggregated into any P&L figure;
entry/stop of terminal positions are recorded as coverage facts only.
"""
import ast
import difflib
import hashlib
import importlib.util
import json
import os
import sys

STAGE08 = os.path.expanduser("~/workspace/qf_td08_stage")
sys.path.insert(0, os.path.join(STAGE08, "engine"))
sys.path.insert(0, os.path.join(STAGE08, "engine", "pine_stack"))
sys.path.insert(0, os.path.join(STAGE08, "engine", "pine_ranking"))
sys.path.insert(0, os.path.join(STAGE08, "engine", "pine_exposure"))
sys.path.insert(0, os.path.join(STAGE08, "engine", "pine_signal_quality"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pine_backtest as pb  # noqa: E402
from pine_ranking import gen_candidates  # noqa: E402

PIN_RANKING = "77afae0df120e3a2ad77a6d2d43247c8aea0ad296f08c273bff7d1cc833aaae6"
RANKING_PATH = os.path.join(STAGE08, "engine", "pine_ranking", "pine_ranking.py")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def counting_variant():
    """Extract gen_candidates source from the pinned file; apply the single
    mechanical terminal-capture transformation; return (callable, diff)."""
    src = open(RANKING_PATH).read()
    tree = ast.parse(src)
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "gen_candidates")
    lines = src.splitlines(keepends=True)
    fn_src = "".join(lines[fn.lineno - 1:fn.end_lineno])
    old_ret = "    return trades, skipped_gap\n"
    assert fn_src.count(old_ret) == 1
    new_ret = (
        "    _terminal = None\n"
        "    if in_trade:\n"
        "        _terminal = {\"symbol\": sym, \"signal_idx\": pos[\"signal_idx\"],\n"
        "                     \"signal_time\": str(df.index[pos[\"signal_idx\"]]),\n"
        "                     \"entry_time\": str(pos[\"entry_time\"]),\n"
        "                     \"entry\": pos[\"entry\"], \"stop\": pos[\"stop\"],\n"
        "                     \"tp1\": pos[\"tp1\"], \"tp_hit\": pos[\"tp_hit\"]}\n"
        "    return trades, skipped_gap, _terminal\n")
    variant_src = fn_src.replace(old_ret, new_ret)
    diff = "".join(difflib.unified_diff(
        fn_src.splitlines(keepends=True), variant_src.splitlines(keepends=True),
        fromfile="gen_candidates (pinned original)", tofile="counting variant"))
    ns = {"pb": pb, "np": np, "pd": pd}
    exec(compile(variant_src, "<counting-variant>", "exec"), ns)
    return ns["gen_candidates"], diff


def main():
    spec = importlib.util.spec_from_file_location(
        "run_diagnostic_08", os.path.join(STAGE08, "run_diagnostic.py"))
    rd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rd)

    rd.phase0()                      # archive/receipt/code pins (read-only)
    dev = rd.load_session_table()
    admitted = rd.phase1(dev)        # DEV legs only; HO never parsed
    bars = rd.phase2(admitted, dev)  # corrected session-anchored 4H bars
    assert not rd.failures, rd.failures

    assert sha256_file(RANKING_PATH) == PIN_RANKING, "pine_ranking.py pin drift"
    variant, diff = counting_variant()
    print("=== transformation diff (original -> counting variant) ===")
    print(diff)

    tally = {"task": "QF-EQUITY-PIT-INTEGRITY-20261023-09",
             "kind": "B3 terminal-open coverage tally — zero P&L, DEV only",
             "pine_ranking_sha256": PIN_RANKING,
             "per_symbol": {}, "terminal_open_total": 0, "closed_total": 0}
    for sym in rd.SYMBOLS:
        data = pb.add_pine_indicators(bars[sym])
        closed, skipped_gap = gen_candidates(sym, data)
        v_closed, v_skipped, terminal = variant(sym, data)
        key = lambda t: (t["symbol"], t["signal_idx"], str(t["entry_time"]))  # noqa: E731
        assert [key(t) for t in v_closed] == [key(t) for t in closed], sym
        assert v_skipped == skipped_gap, sym
        rec = {"bars_4h": int(len(data)), "closed_candidates": len(closed),
               "skipped_gap": skipped_gap,
               "terminal_open": [terminal] if terminal else []}
        tally["per_symbol"][sym] = rec
        tally["closed_total"] += len(closed)
        tally["terminal_open_total"] += len(rec["terminal_open"])
        print(f"{sym}: bars={len(data)} closed={len(closed)} "
              f"skipped_gap={skipped_gap} terminal_open={len(rec['terminal_open'])}"
              + (f" -> {terminal}" if terminal else ""))
    print(f"TOTAL: closed={tally['closed_total']} "
          f"terminal_open={tally['terminal_open_total']}")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "coverage_tally.json")
    with open(out, "w") as f:
        json.dump(tally, f, indent=1, default=str)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
