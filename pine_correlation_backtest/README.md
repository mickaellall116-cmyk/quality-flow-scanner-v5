# P3 — Correlation & concentration study (2026-09-24)

**Question:** does avoiding highly correlated simultaneous positions improve
portfolio performance?

**Hypothesis:** correlated positions concentrate drawdown without adding
expectancy, because they win and lose together.

**Answer up front: partially — expectancy improves (+0.049R, +5.4pp total
return), drawdown does NOT fall, and the existing theme-cap rule does nothing.
Verdict: MAYBE.**

## Setup

- Universe: 14-stock watchlist, 4H bars, Oct 25 2023 – Sep 23 2026 (cached
  pickles from `pine_entry_timing_backtest/cache`).
- Entries: canonical 4H Hybrid via `gen_pine_trades` — IDENTICAL for all
  variants (237 generated trades). Exits: frozen Mode B. `pine_backtest.py`
  imported unmodified; only the portfolio admission rule varies.
- Custom sim is a line-for-line copy of `pb.simulate_portfolio` plus admission
  hooks and blocked-trade recording. CONTROL reproduces the known baseline
  exactly (total return 56.28%, DD 21.63% — matches `pine_pullback_backtest`).
- Costs: 25 bps. Pre-declared variants (thresholds set before running):
  - **CONTROL** — max 5 concurrent + 5% heat, no theme/corr control
  - **THEME_CAP2** — CONTROL + max 2 open per theme (existing production rule)
  - **CORR_07** — CONTROL + block new entry if 60-bar return correlation with
    ANY open position > 0.7 (raw positive correlation)
  - **CORR_06 / CORR_08** — robustness points only, not proposals
  - **CLUSTER1** — CONTROL + max 1 open per merged cluster
    (Semis+AI Infra: AMD/DRAM/SMCI/ANET; Software/AI: PLTR/BBAI;
    Fintech: SOFI/HOOD; Space: RKLB/SPCX/ASTX; Other: ONDS/NIO/QQQ)
- Research only. V5.4, Mode B, alerts, grades, market gate, AI Observer untouched.

## Results (taken-trade basis; 25 bps)

| Variant | Taken | Exp (R) | Win% | PF | Total ret | Max DD | Blocked | Blocked exp |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CONTROL | 180 | **+0.272** | 50.6 | 1.43 | 56.28% | 21.63% | 0 | — |
| THEME_CAP2 | 180 | +0.272 | 50.6 | 1.43 | 56.28% | 21.63% | 0 | — |
| CORR_07 | 165 | **+0.321** | 51.5 | 1.54 | **61.70%** | 21.99% | 28 | **−0.133R** |
| CORR_06 | 149 | +0.328 | 51.7 | 1.55 | 56.39% | 21.31% | 51 | −0.110R |
| CORR_08 | 179 | +0.261 | 52.0 | 1.42 | 52.63% | 22.36% | 6 | +0.916R |
| CLUSTER1 | 152 | +0.344 | 52.0 | 1.62 | 62.98% | **27.02%** | 67 | −0.110R |

Note: CONTROL taken-expectancy (+0.272R/180) differs from the published
+0.239R/237 baseline because the baseline averages over all *generated*
trades while the sim can only *take* 180 (44 cap + 13 heat skips). Variant
comparisons use the taken basis consistently.

## Key findings

1. **The existing max-2-per-theme rule never binds.** THEME_CAP2 blocked zero
   trades — bit-identical to CONTROL. The 5-slot cap and 5% heat cap already
   constrain concentration, so the theme rule is decorative in backtest. It
   costs nothing but also buys nothing.

2. **CORR_07 earns its keep on expectancy, not on drawdown.** Blocked 28
   trades averaging −0.133R (39% win) → taken expectancy +0.321R vs +0.272R
   (+0.049R), total return +5.4pp. But max DD is flat (21.99% vs 21.63%) —
   the hypothesized drawdown reduction did NOT materialize. The gain comes
   from dodging losers, not from smoother equity.

3. **Blocked trades are broad, not concentrated.** 28 blocks span 9 symbols
   (AMD 7, QQQ 6, SMCI 3, ANET/ASTX/HOOD/PLTR/RKLB/SOFI 2 each) across
   2024-05 to 2026-07. No single name or month drives the effect.

4. **Walk-forward holds.** Test period (entries ≥ 2025-01-01, equity reset):
   CORR_07 +0.241R vs CONTROL +0.200R (+0.041R). Yearly: 2024 +0.477 vs
   +0.420, 2025 +0.521 vs +0.425, 2026 −0.159 vs −0.089 (2026 is negative
   for everything; the filter underperforms there).

5. **Perturbation: 0.6 agrees, 0.8 flips on a thin bucket.** CORR_06 blocks 51
   @ −0.110R and matches (+0.328R). CORR_08 blocks only 6 trades — which
   averaged +0.916R — and underperforms slightly. n=6 is noise, but it shows
   the effect lives in the 0.6–0.7 zone, not at the extreme.

6. **Real opportunity cost exists.** The filter blocked a +8.67R HOOD winner
   (2025-04-29, maxcorr 0.857) and a +2.74R SMCI winner. It also blocked a
   −5.05R ANET loser. Fat-tail trades get blocked in both directions; the
   average favors the filter, but single-trade variance is high.

7. **CLUSTER1: FAIL as specified.** Highest taken expectancy (+0.344R) but max
   DD jumps to 27.02% (+5.4pp vs control) — materially worse drawdown, which
   fails the mandate's gates. Cap-1-per-cluster is too restrictive (67 blocks).

## Why it worked (mechanism)

When a new signal fires while a highly correlated position is already open,
it is usually the same bet twice — same sector move, same market impulse.
Blocking the second entry avoids doubling down on shared losers. The blocked
set's −0.133R expectancy (vs +0.272R baseline) is the mechanism made visible.
The drawdown half of the hypothesis failed: fewer, less-correlated positions
did not smooth the equity curve — likely because 1%-risk sizing already
caps per-trade damage, so concentration shows up in expectancy, not DD.

## Overfitting flags (stated plainly)

1. 28 blocked trades is a modest sample; the +0.049R rides on their −0.133R
   average. One fewer HOOD-style winner blocked and the story weakens.
2. The 0.8 threshold flips sign (n=6) — the effect is not threshold-invariant,
   though the pre-declared main threshold and its neighbor agree.
3. 2026 (out-of-sample, live regime) favors CONTROL — the filter's edge is
   historical, and the live paper sidecar era is exactly when it underperforms.
4. Only tested at 25 bps; costs hit all variants equally, but the filter takes
   fewer trades, so cost stress would likely flatter it — not tested.

## Verdict: MAYBE

CORR_07 is a genuine, pre-declared, mechanism-plausible improvement that
survives walk-forward (+0.041R out-of-sample) and is broad across symbols and
years. But: the blocked sample is small (28), the drawdown benefit never
appeared, 2026 favors control, and it once blocked a +8.7R winner. Interesting
enough to keep on the candidate board; not proven enough for production.
Recommended next: forward-validate as a paper overlay (like the FVG sidecar),
then revisit with more blocked-trade data.

## Files

- `run_correlation.py` — study script (`pine_backtest` imported unmodified;
  sim copied with admission hooks)
- `correlation_results.json` — per-variant stats, blocked-trade analysis,
  yearly splits, walk-forward
- `README.md` — this file
