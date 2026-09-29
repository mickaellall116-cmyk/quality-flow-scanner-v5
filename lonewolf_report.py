#!/usr/bin/env python3
"""One-command report for the lone-wolf paper overlay.

Reads v54_forward/lonewolf_overlay.jsonl (read-only) and prints:
  - signals classified, would-have-blocked count + rate
  - realized R of blocked vs allowed (closed forward-test trades only)
  - per-symbol spread of would-block flags

Usage: python3 lonewolf_report.py
"""

import json
import os
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "v54_forward", "lonewolf_overlay.jsonl")


def main() -> int:
    if not os.path.exists(LOG):
        print("No overlay log yet -- run: python3 v54_lonewolf_overlay.py --cycle")
        return 1
    sigs, closes, cycles = [], [], []
    with open(LOG, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            t = r.get("type")
            if t == "signal_overlay":
                sigs.append(r)
            elif t == "close_overlay":
                closes.append(r)
            elif t == "cycle":
                cycles.append(r)

    n = len(sigs)
    blocked = [s for s in sigs if s.get("would_block")]
    print("=== lone-wolf overlay report (paper only) ===")
    print(f"signals classified : {n}")
    print(f"would-have-blocked  : {len(blocked)} ({100.0*len(blocked)/n:.1f}%)" if n else "would-have-blocked  : 0")
    print(f"overlay cycles run : {len(cycles)}"
          + (f" (last {cycles[-1]['finished_at']})" if cycles else ""))

    print("\n--- realized outcomes: blocked vs allowed (closed trades) ---")
    b_r = [c["blended_r"] for c in closes if c.get("would_block") and c.get("blended_r") is not None]
    a_r = [c["blended_r"] for c in closes if not c.get("would_block") and c.get("blended_r") is not None]
    if b_r or a_r:
        mb = f"{sum(b_r)/len(b_r):+.3f}" if b_r else "n/a (no blocked closes yet)"
        ma = f"{sum(a_r)/len(a_r):+.3f}" if a_r else "n/a (no allowed closes yet)"
        print(f"blocked : n={len(b_r)}  mean realized R = {mb}")
        print(f"allowed : n={len(a_r)}  mean realized R = {ma}")
    else:
        print("no closed mapped trades yet -- outcome comparison pending")

    print("\n--- per-symbol would-block spread ---")
    spread = Counter(s["symbol"] for s in blocked)
    seen = Counter(s["symbol"] for s in sigs)
    if spread:
        for sym, c in spread.most_common():
            print(f"  {sym:6s} blocked {c}/{seen[sym]}")
    else:
        print("  (none blocked so far)")
    unmapped = sum(1 for s in sigs if s.get("reason") == "no_sector_mapping")
    if unmapped:
        print(f"\nnote: {unmapped}/{n} signals had no sector mapping "
              f"(outside the 14-name P10 universe) -- logged, never blocked")
    print("\nforward validation in progress; revisit at the ~50-signal "
          "checkpoint (late Oct 2026).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
