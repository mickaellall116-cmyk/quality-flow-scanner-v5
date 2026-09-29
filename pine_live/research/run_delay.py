#!/usr/bin/env python3
"""Detection-delay report — observation-only research run.

Reads dual-ledger trade records from ``paper_state/ledger/trades.jsonl``
(READ-ONLY), slices drag per DELAY_STUDY_SPEC.md, and REGENERATES
``research/detection_delay_report.md`` from scratch each run.

Never writes to paper_state/, never affects trading. With zero qualifying
trades the report says INSUFFICIENT_DATA.

Usage: python3 -m pine_live.research.run_delay [--state-dir D] [--out-dir D]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from pine_live.research import delay  # noqa: E402

STATE_DIR_DEFAULT = os.path.join(REPO_ROOT, "pine_live", "paper_state")
OUT_DIR_DEFAULT = os.path.join(REPO_ROOT, "pine_live", "research")


def _read_jsonl(path: str) -> list:
    out = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    except OSError:
        pass
    return out


def _fmt(x, digits=1) -> str:
    return f"{x:.{digits}f}" if isinstance(x, (int, float)) else "n/a"


def _dim_section(dim: str, d: dict) -> list[str]:
    lines = [f"### {dim}", ""]
    ranked = d.get("ranked", [])
    small = d.get("insufficient_sample", [])
    if ranked:
        lines.append("| rank | bucket | n | mean drag (bps) | "
                     "median drag (bps) | mean drag (R) |")
        lines.append("|---|---|---|---|---|---|")
        for i, e in enumerate(ranked, 1):
            lines.append(
                f"| {i} | {e['bucket']} | {e['n']} | "
                f"{_fmt(e['mean_drag_bps'])} | "
                f"{_fmt(e['median_drag_bps'])} | "
                f"{_fmt(e['mean_drag_r_4bps'], 3)} |")
    else:
        lines.append(f"No qualifying bucket (need >= "
                     f"{delay.MIN_BUCKET_TRADES} trades per bucket).")
    if small:
        names = ", ".join(f"{e['bucket']} (n={e['n']})" for e in small)
        lines.append("")
        lines.append(f"_{delay.INSUFFICIENT_SAMPLE}: {names} — excluded "
                     f"from rankings, not shown above._")
    lines.append("")
    return lines


def build_report(trades: list) -> str:
    """Regenerate the full markdown report from ledger trades."""
    now = datetime.now(timezone.utc).isoformat()
    L = ["# Detection-delay report", "",
         f"_Regenerated {now} from `paper_state/ledger/trades.jsonl`. "
         "Observation only — drag = achievable minus canonical "
         "(positive = achievable worse). "
         "Bucket definitions frozen in `DELAY_STUDY_SPEC.md`; "
         f"buckets need >= {delay.MIN_BUCKET_TRADES} trades to be ranked._",
         ""]
    sliced = delay.slice_drag(trades)
    if sliced["n_trades"] == 0:
        L += ["## INSUFFICIENT_DATA", "",
              "No closed paper trades with dual-ledger drag data yet. "
              "Nothing is ranked or inferred.",
              ""]
        return "\n".join(L)

    L += [f"Qualifying closed trades with dual data: "
          f"**{sliced['n_trades']}**", ""]
    L += ["## Where a real-time feed would matter most", "",
          "_Top qualifying buckets by mean drag (bps) across all "
          "dimensions._", ""]
    top = delay.top_drag_buckets(sliced)
    if top:
        L.append("| rank | dimension | bucket | n | mean drag (bps) |")
        L.append("|---|---|---|---|---|")
        for i, e in enumerate(top, 1):
            L.append(f"| {i} | {e['dimension']} | {e['bucket']} | "
                     f"{e['n']} | {_fmt(e['mean_drag_bps'])} |")
    else:
        L.append(f"No bucket reaches the {delay.MIN_BUCKET_TRADES}-trade "
                 f"minimum yet — {delay.INSUFFICIENT_SAMPLE} everywhere.")
    L.append("")
    L.append("## Slices")
    L.append("")
    for dim in ("symbol", "vol", "tod", "gap", "regime"):
        d = sliced["dimensions"][dim]
        if dim == "regime" and not sliced["regime_available"]:
            L += ["### regime", "",
                  "Regime tagging not yet available in the trade ledger; "
                  "this slice reports unavailable rather than inventing "
                  "tags.", ""]
            continue
        L += _dim_section(dim, d)
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state-dir", default=STATE_DIR_DEFAULT)
    ap.add_argument("--out-dir", default=OUT_DIR_DEFAULT)
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)
    trades = _read_jsonl(os.path.join(args.state_dir, "ledger",
                                     "trades.jsonl"))
    report = build_report(trades)
    with open(os.path.join(args.out_dir, "detection_delay_report.md"),
              "w", encoding="utf-8") as f:
        f.write(report)
    print(json.dumps({"n_trades": len(trades),
                      "report": "detection_delay_report.md"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
