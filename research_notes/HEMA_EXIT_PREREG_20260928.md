# HEMA Runner-Exit Test — Preregistration (2026-09-28)

Research-only. Frozen/live Quality Flow remains unchanged.

## Question
Can HEMA improve **runner management after TP1** without changing Quality Flow entries, structural stops, TP1, pre-TP1 Profit Protect, sizing, ranking, or portfolio limits?

## Fixed baseline
- QF entry logic unchanged.
- Next-bar-open entry.
- Structural stop always active.
- 50% at TP1.
- Pre-TP1 Profit Protect unchanged.
- No exit evaluation on the TP1 bar.
- 30-bar maximum hold unchanged.
- Costs remain leg-based.
- Headline cost = 50 bps, with 25/75/100 bps sensitivity.

## Pre-registered post-TP1 runner rules
1. **current** — existing scanner Profit Protect exit, baseline.
2. **daily_hema_cross** — replace the post-TP1 runner trigger with the first completed Daily HEMA20/40 bearish crossover; fill next available 4H open.
3. **current_and_daily_hema_bear** — current scanner exit only qualifies while the last completed Daily HEMA regime is bearish; fill next 4H open. This tests HEMA as confirmation rather than as a standalone exit.
4. **h4_hema_cross** — first completed 4H HEMA20/40 bearish crossover; next-bar-open fill. Reference rule already seen in earlier exploratory runs.
5. **daily_ema20_40_cross** — ordinary Daily EMA20/40 bearish crossover; next 4H open. Simple-control rule.
6. **h4_ema20_40_cross** — ordinary 4H EMA20/40 bearish crossover; next-bar-open fill. Simple-control rule.

No HEMA length search, no ATR tuning, no exit-weight search, and no choosing among variants by visual chart inspection.

## Two analyses
### A. Fixed-entry paired exit analysis
Use the exact baseline rs_top2 accepted entries. Hold entry, stop, TP1 and shares fixed across exit rules. This isolates exit quality from slot availability.

Report:
- blended net R/trade;
- runner R after TP1;
- post-TP1 MFE and giveback to exit in R;
- win rate / PF;
- holding bars;
- each year;
- cost ladder 25/50/75/100 bps;
- paired bootstrap and entry-month block bootstrap of candidate minus current;
- top-trade removal;
- number of trades actually changed by the exit rule.

### B. System-level portfolio confirmation
Only if a rule materially improves the paired fixed-entry test, rerun the full portfolio with that single rule, because different exit timing changes future slot availability.

## Interpretation standard
A candidate is not an improvement merely because portfolio return rises in this 30-name surrogate. It should:
- improve paired net R or reduce giveback on a meaningful number of TP1 runners;
- have a confidence interval that is not obviously dependent on one/few trades;
- avoid material deterioration in 2026;
- survive realistic costs;
- compare favorably with the plain EMA control.

This is a screening test only. Any positive result still requires canonical 131-symbol PIT confirmation before a live/frozen change.
