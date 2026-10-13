#!/usr/bin/env python3
"""
warmup_math.py — EMA200 convergence analysis (ChatGPT 6037625281, blocker 2).

The archival pine_backtest.py computes EMA200 via pandas
`ewm(span=200, adjust=False)`. With adjust=False, pandas seeds the recursion
with the first observation and applies:

    alpha = 2 / (span + 1) = 2 / 201

After n updates, the weight remaining on the initial seed is:

    w_seed(n) = (1 - alpha)^n = (199/201)^n

WARMUP=215 reproduces the archival convention, but it does NOT prove EMA200
convergence. This module computes the exact seed weights and documents the
consequence for the pilot's decision-impact checks.

Usage:
  python3 warmup_math.py
  python3 warmup_math.py --span 200 --warmup 215
"""
import argparse
import math
import sys


def seed_weight(span: int, n: int) -> float:
    """Weight of the initial seed after n ewm(adjust=False) updates."""
    alpha = 2.0 / (span + 1)
    return (1.0 - alpha) ** n


def updates_for_seed_below(span: int, target: float) -> int:
    """Updates needed for the seed weight to fall below `target`."""
    alpha = 2.0 / (span + 1)
    return math.ceil(math.log(target) / math.log(1.0 - alpha))


def main() -> int:
    ap = argparse.ArgumentParser(description="EMA convergence analysis")
    ap.add_argument("--span", type=int, default=200)
    ap.add_argument("--warmup", type=int, default=215)
    args = ap.parse_args()

    span, warmup = args.span, args.warmup
    alpha = 2.0 / (span + 1)
    w = seed_weight(span, warmup)

    print(f"EMA({span}) via ewm(span={span}, adjust=False)")
    print(f"  alpha = 2/{span + 1} = {alpha:.6f}")
    print(f"  seed weight after {warmup} updates: (1-alpha)^{warmup} = {w:.4%}")
    print()
    print("  Convergence table (seed weight vs updates):")
    for target in (0.10, 0.05, 0.01, 0.001):
        n = updates_for_seed_below(span, target)
        print(f"    seed < {target:>6.1%} → {n:>4} updates "
              f"(≈ {n / 2:.0f} trading days at 2 bars/day)")
    print()
    print("  CONCLUSION (per ChatGPT 6037625281 blocker 2):")
    print(f"  WARMUP={warmup} leaves {w:.2%} weight on the first seed — the EMA200")
    print("  is NOT stabilized. Do not claim convergence from the warmup count.")
    print()
    print("  PILOT RULE (frozen):")
    print("  - Acquisition/session checks (C1 bar counts, labels, DST,")
    print("    early-close, closed-day) proceed with 215-bar 4H warmup.")
    print("  - Decision-impact checks (C2: BUY/NO re-runs through frozen")
    print("    pine_buy_signal) are INSUFFICIENT EVIDENCE unless a separately")
    print("    pinned initialization/sensitivity rule and enough")
    print("    decision-timeframe history support them.")
    print("  - No new performance experiment is authorized.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
