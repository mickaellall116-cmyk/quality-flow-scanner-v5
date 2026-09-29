# Ranking-factor study (P2) — results 2026-09-24

**Question:** when crowded signal bars produce more signals than portfolio
slots, does any ranking factor beat the adopted rs_top2 control (20-bar return
minus SPY, take top 2)?

**Setup:** 14-stock watchlist, 4H, 2023-10-25 → 2026-09-23. Canonical
`gen_pine_trades` (frozen Mode B). Portfolio: $10k, 1% risk/trade, max 5
concurrent, 5% heat, next-bar-open, 25bps primary. Factors pre-declared in
`CANDIDATES.md` (frozen before running). Research only — nothing frozen touched.

## Step 0 — clustering
237 candidate trades → 54 contested timestamps, **21 genuine** (a real choice;
the rest were a lone signal with zero free slots). Histogram of candidates per
contested bar: {1: 31, 2: 15, 3: 8}. Genuine contests by year: 2024: 5,
2025: 10, 2026: 6. Ranking gets to act ~21 times in 3 years — the differential
sample is small by construction.

## Per-factor results @25bps (n_cap=2)

| factor | trades | exp R | win% | PF | maxDD% | vs control |
|---|---|---|---|---|---|---|
| take-all (ref) | 178 | +0.221 | 50.0 | 1.34 | 25.3 | +0.061 |
| **rs_spy CONTROL** | 179 | **+0.160** | 48.0 | 1.24 | 31.3 | — |
| **adx** | 178 | **+0.314** | 50.6 | 1.50 | 26.8 | **+0.154** |
| trend_score | 178 | +0.289 | 50.6 | 1.46 | 26.8 | +0.129 |
| dollar_liq | 176 | +0.287 | 51.1 | 1.46 | 26.5 | +0.127 |
| vol_expansion | 180 | +0.254 | 50.0 | 1.40 | 29.2 | +0.094 |
| breakout_dist | 178 | +0.232 | 49.4 | 1.36 | 29.5 | +0.072 |
| mom50 | 180 | +0.204 | 48.9 | 1.31 | 31.2 | +0.044 |
| rr | 180 | +0.231 | 50.0 | 1.37 | 29.8 | +0.071 |
| dist_200ema | 178 | +0.225 | 49.4 | 1.35 | 26.5 | +0.065 |
| atr_mom | 179 | +0.212 | 49.7 | 1.32 | 27.6 | +0.052 |
| dist_high | 180 | +0.183 | 48.9 | 1.28 | 29.5 | +0.023 |
| rs_sector | 179 | +0.174 | 48.6 | 1.26 | 29.5 | +0.014 |
| mom20 | 179 | +0.160 | 48.0 | 1.24 | 31.3 | +0.000 |

## The two big findings

**1. The control loses to doing nothing.** rs_top2 (+0.160R) underperforms
take-all (+0.221R) on this 14-stock universe — and raises max DD (31.3% vs
25.3%). The rs_top2 benefit found on UX51 (+0.324R vs +0.195R) does **not**
transfer to the 14-name momentum watchlist. On these names, taking the earliest
signals beats taking the highest-RS signals when slots are scarce. Note:
mom20 is mathematically identical to rs_spy (SPY return is a constant shift
per timestamp) — a redundant duplicate, not an independent test.

**2. ADX is the best ranker, with genuine two-sided skill.** adx (+0.314R)
beats control by +0.154R and take-all by +0.093R. Swap analysis vs control:
17 swapped in @ +0.954R, 18 swapped out @ −0.611R — it both picks winners and
dodges losers, across 7 symbols (QQQ 5, HOOD 3, BBAI 3, AMD 2, NIO 2, RKLB 1,
ONDS 1). Mechanism: when slots are scarce, prefer the signal with the
strongest established trend. Survives costs: +0.252R @50bps, +0.135R @100bps
(control collapses to +0.003R @100bps).

## Caveats (why this is MAYBE, not PASS)
- The skill is demonstrated on ~35 differential trades, and 10 of the 21 genuine
  contests fall in 2025 — the edge is a 2025 story (+0.481R vs control +0.195R
  that year). 2024 had only 5 genuine contests (variants nearly identical);
  2026 everything was negative (adx −0.127R, control −0.217R).
- trend_score is partially redundant with adx by construction (shares adx≥20).
- dollar_liq's swapped-in set concentrates in QQQ+HOOD (11/16) — flag.
- vol_expansion shows skill here but the prior UX51 study found none — conflict.
- Pre-declared combos (rs_spy+adx/vol/rr) all failed because rs_spy is a bad
  anchor here. Follow-up adx-anchored combos: C_adx_vol +0.318R, C_adx_rr
  +0.294R vs adx alone +0.314R — the +0.004R combo delta is noise. No combo
  earns its keep.

## Verdicts
- **adx: MAYBE** — best single factor, two-sided skill, survives costs, but
  thin differential sample concentrated in 2025. Needs forward validation
  before any production discussion.
- **trend_score / vol_expansion: MAYBE-weak** (redundancy / prior-study conflict).
- **dollar_liq: MAYBE-weak** (symbol concentration flag).
- **Everything else: FAIL** — rs_sector, dist_high, atr_mom, dist_200ema, rr,
  breakout_dist, mom50 show no material edge over control.
- **Context flag for Mike:** the adopted rs_top2 ranking costs ~0.06R vs
  take-all on the 14-stock watchlist. Worth revisiting whether the production
  ranking rule should apply to this universe — but that is his call, not
  research's.

## Files
- `CANDIDATES.md` — frozen pre-declared factor definitions
- `run_ranking_factors.py` — study script (`pine_backtest` imported unmodified)
- `ranking_factor_results.json` — full results incl. yearly, cost stress, swaps
- `README.md` — this file
