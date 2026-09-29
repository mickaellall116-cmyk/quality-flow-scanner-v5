# P5 follow-up (pre-registered): NO-DEAD-MARKET filter

**Hypothesis (pre-registered):** skipping new entries when the market is in a
bottom-tercile realized-volatility regime improves expectancy, because
breakouts need movement and dead markets starve them.

**Definition (exact P5 definition, no re-tuning):** per-symbol 20-bar
log-return std, percentile-ranked within trailing 500 4H bars
(min_periods 250); skip entry if `rv_pctile < 33` at the signal bar.
P5 evidence: low tercile −0.034R overall / −1.15R in 2026 (n=39);
high tercile +0.402R (n=107), best bucket every year.

NOTE: the dispatch text said "SPY ... trailing 1 year", but P5's actual
pre-registered definition is per-symbol / trailing 500 bars. This study
follows P5's definition exactly — that is the evidence being confirmed.

**Setup:** 14-stock watchlist, 4H, Oct 2023–Sep 2026, canonical 4H Hybrid
entries via `pb.gen_pine_trades` (unmodified), frozen Mode B exits,
25 bps, portfolio sim = copy of `pb.simulate_portfolio` with an admission
hook (same pattern as `pine_correlation_backtest`). CONTROL reproduces the
known baseline exactly (180 taken, +0.272R, 56.28% return, 21.63% DD),
so the apparatus is faithful. Note: 237 generated signals → 180 taken
after slot/heat caps; all variants compared on the taken basis.

## Results (25 bps)

| Variant | Taken | Exp (R) | Win% | PF | Total ret | Max DD |
|---|---|---|---|---|---|---|
| CONTROL | 180 | +0.272 | 50.6 | 1.43 | 56.28% | 21.63% |
| NO_DEAD_MARKET | 163 | **+0.298** | 50.9 | 1.48 | 56.71% | 20.90% |

- Blocked: 27 trades (of 39 dead-market signals; the other 12 were
  cap/heat-skipped before reaching admission). **Blocked expectancy:
  +0.1168R** (51.9% win, PF 1.19) — mildly *positive*.
- Dead-market signals span 11 symbols (QQQ 6, SOFI 6, PLTR 5, others ≤4):
  no concentration.
- Full 39-signal dead bucket (pre-cap): −0.034R — matches P5 exactly,
  confirming the definition.

## Year cross-tab (taken basis)

| Year | CONTROL | NO_DEAD_MARKET |
|---|---|---|
| 2024 | (59, +0.420R) | (52, +0.389R) — filter *worse* |
| 2025 | (68, +0.425R) | (60, +0.533R) — filter better |
| 2026 | (53, −0.089R) | (51, −0.071R) — slightly less bad |

## Walk-forward (pre-declared split: test = entries ≥ 2025)

| Period | CONTROL | NO_DEAD_MARKET |
|---|---|---|
| train (≤2024) | (59, +0.420R) | (52, +0.389R) |
| test (≥2025) | (121, +0.200R) | (111, +0.256R) |

## Verdict: MAYBE (weak)

The filter adds +0.026R with drawdown flat-to-slightly-better, broad
symbol spread, and the walk-forward test period favors it (+0.056R).
But three honest problems:

1. **The mechanism check failed.** The hypothesis said dead markets
   produce losers; the 27 blocked trades ran **+0.1168R**. The gain is
   reweighting (trimming mediocre trades raises the average), not
   dodging losers.
2. **Not persistent.** The filter hurts in 2024 (−0.032R) and helps in
   2025 (+0.108R). Two of three years positive is not a pattern.
3. **Small.** +0.026R is within noise per the mandate's own rule
   ("small improvements are noise unless they replicate").

Recommendation: keep the "avoid dead markets" thread on the watch list;
do NOT forward-validate as a paper overlay yet. Revisit only if more
data accumulates or the mechanism is sharpened (e.g. a stricter
percentile with a pre-registered rationale — no tuning now).

## Files
- `run_deadmarket.py` — study script (`pine_backtest` imported unmodified)
- `deadmarket_results.json` — per-variant stats, blocked-trade analysis,
  year cross-tabs, walk-forward
- `README.md` — this file

Guardrails respected: research only. V5.4, Mode B, production alerts,
grades, exits, market gate, AI Observer untouched.
