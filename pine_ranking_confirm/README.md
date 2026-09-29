# ADX ranking — confirmatory study (mandate priority 3, 2026-09-25)

## Hypothesis (frozen BEFORE running — see HYPOTHESIS.md)
When portfolio slots are scarce, ranking contenders by ADX(14) selects better
trades than the adopted rs_top2 rule, consistently across years.

## Mechanism
A breakout bets that demand overwhelms supply. When slots are limited, prefer
the setup whose trend is already most established (highest ADX). On this
concentrated momentum watchlist, the highest 20-bar-return names tend to be
late/extended; trend strength at entry continues more reliably.

## Method (declared before running)
Same signal population as P2: 14-stock watchlist, 4H, 2023-10-25 → 2026-09-23,
canonical `pb.gen_pine_trades` (frozen Mode B exits), $10k / 1% risk / max 5
concurrent / 5% heat, next-bar-open, 25bps primary. Ranking engages ONLY at
contested timestamps (candidates > free slots): rank by score, take top
min(2, free). All features point-in-time at the signal bar.
`pine_backtest` imported unmodified. Fidelity check: score=None, n_cap=None
reproduces `pb.simulate_portfolio` exactly — PASS.

Frozen variants: `takeall` (arrival order, cap 2 — the do-nothing
counterfactual), `rs_spy_CONTROL` (adopted rule), `adx` (ADX(14), identical
definition to P2), `C_rs_adx` (ONE predeclared combo: mean cross-sectional
percentile rank of (rs_spy, adx) — run regardless, but EVALUATED/PROMOTED only
if BOTH components independently beat take-all). Secondary robustness:
`adx10`, `adx20`.

## Results @25bps

| variant | trades | exp R | win% | PF | maxDD% | total ret% |
|---|---|---|---|---|---|---|
| takeall | 178 | +0.221 | 50.0 | 1.34 | 25.3 | 42.05 |
| rs_spy CONTROL | 179 | +0.160 | 48.0 | 1.24 | 31.25 | 27.02 |
| **adx** | 178 | **+0.314** | 50.6 | 1.50 | 26.78 | 68.01 |
| adx10 | 177 | +0.272 | 50.3 | 1.42 | 26.78 | 55.66 |
| adx20 | 178 | +0.302 | 50.6 | 1.48 | 26.78 | 64.14 |
| C_rs_adx | 179 | +0.194 | 48.6 | 1.29 | 29.32 | 35.54 |

54 contested timestamps, **21 genuine** (real choice; 2024: 5, 2025: 10,
2026: 6). The differential sample is small by construction — everything below
must be read against that.

## The combo verdict (pre-declared discipline)
rs_spy (+0.160R) does NOT beat take-all (+0.221R), so per the frozen rule the
C_rs_adx combination (+0.194R) is NOT evaluated or promoted — reported for
completeness only. This is the mandate's "do not combine weak discoveries"
rule working as designed: anchoring on a bad factor drags the combo down.

## Opportunity cost (vs take-all)
- adx: ranked out 14 trades @ **−0.650R**; swapped in 14 @ **+0.530R**.
  Genuine two-sided skill — it both dodges losers and picks winners.
- adx10: out 11 @ −0.492R / in 10 @ +0.347R. adx20: out 17 @ −0.609R /
  in 17 @ +0.239R. Same two-sided pattern at nearby periods.
- rs_spy: ranked out 11 @ **+0.311R**; swapped in 12 @ **−0.606R**. The
  adopted rule does the opposite of what a ranker should: it skips winners
  and takes losers.

## Year-by-year expectancy

| variant | 2024 | 2025 | 2026 |
|---|---|---|---|
| takeall | +0.501 (56) | +0.219 (71) | −0.084 (51) |
| rs_spy CONTROL | +0.466 (56) | +0.195 (71) | −0.217 (52) |
| adx | +0.503 (56) | **+0.481 (71)** | −0.127 (51) |

ADX beats the adopted control in ALL three years (+0.037, +0.286, +0.090).
Vs take-all the edge is 2025-concentrated: 2024 flat (+0.002 — only 5 genuine
contests that year, variants nearly identical by construction), 2025 +0.262,
2026 −0.044 (both negative; ~6 genuine contests — noise territory).

## Walk-forward (train ≤2024 / test ≥2025; no parameters fit — period check)
- train: takeall +0.501 / rs_spy +0.466 / adx +0.503 (n=56 each; tiny
  differential sample, near-identical as expected)
- test (OOS): takeall +0.144 / rs_spy +0.072 / **adx +0.209** (n≈122)
  → OOS delta +0.066R vs take-all, +0.138R vs control. The edge does NOT
  disappear out-of-sample.

## Crowded-bars-only (≥3 candidates; 8 timestamps, 24 candidates)
Ranking cap binds at 2 — this is where the factor actually decides.
- takeall: 13 taken @ −0.964R
- rs_spy: 13 taken @ −1.075R
- **adx: 12 taken @ −0.317R**
- C_rs_adx: 13 taken @ −1.164R

Crowded bars are bad for everyone (all negative — crowded signal bars coincide
with choppy, market-wide conditions), but ADX loses least. Differential picks
at crowded bars: ADX-only 6 trades @ **+0.284R** (BBAI, HOOD, QQQ) vs
RS-only 7 trades @ **−1.210R** (AMD, ANET, PLTR, RKLB, SMCI, SOFI). Stark.

## Symbol concentration
ADX selected trades span 12 symbols (QQQ 23, RKLB 20, AMD 18, SOFI 18, ANET 17,
PLTR 17, HOOD 16, ONDS 12, BBAI 12, SMCI 11, NIO 10, ASTX 4) — no 2–3 name
dominance. Swapped-in set spans 7 symbols; ranked-out (dodged) losers span 6.
The control's selected set is similarly broad — the difference is selection
quality, not ticker concentration.

## Cost sensitivity
| costs | takeall | rs_spy | adx |
|---|---|---|---|
| 25bps | +0.221 | +0.160 | **+0.314** |
| 50bps | +0.157 | +0.101 | **+0.252** |
| 100bps | +0.028 | +0.003 | **+0.135** |
ADX survives and stays best at every cost level; the control collapses to
~zero at 100bps.

## Why it worked
Two-sided selection skill on the differential trades (dodges −0.65R losers,
picks +0.53R winners), visible at crowded bars where the ranking actually
binds. The adopted RS rule does the reverse — on this concentrated momentum
watchlist, highest 20-bar return = most extended = latest.

## Why it's not PASS
The vs-take-all edge is a 2025 story (2024 flat on 5 genuine contests, 2026
slightly negative on 6). The mandate's PASS gate requires breadth across
periods; vs the do-nothing baseline, ADX has not cleared that bar. The
differential sample (21 genuine contests in 3 years) is too thin for PASS on
any reading.

## Verdict: MAYBE
ADX is unambiguously better than the adopted rs_top2 rule — every year, every
period, every nearby ADX period, every cost level, crowded bars included, with
two-sided skill. Whether it beats doing nothing (take-all) is 2025-dependent
and needs forward validation. The adopted ranking rule, meanwhile, is
confirmed harmful on this watchlist: −0.061R vs take-all, +6pp drawdown, and
its swaps are backwards (skips +0.311R winners, takes −0.606R losers).

## Recommended next experiment
Forward-validate via an ADX shadow on the live scoreboard (mandate item 5):
at each crowded forward-test bar, log what ADX ranking would have picked vs
what the adopted rule picked. Revisit at the ~50-signal checkpoint. No
production change — rs_top2 stays untouched.

## Files
- `HYPOTHESIS.md` — frozen hypothesis, variants, analyses, win gate
- `run_ranking_confirm.py` — study script (`pine_backtest` imported unmodified)
- `ranking_confirm_results.json` — full results

Guardrails respected: research only. V5.4, Mode B, production alerts, grades,
exits, market gate, AI Observer untouched; the adopted rs_top2 ranking was not
changed anywhere in production.
