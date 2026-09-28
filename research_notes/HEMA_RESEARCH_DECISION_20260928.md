# HEMA Research Decision — 2026-09-28

Research branch only. Frozen/live Quality Flow remains unchanged.

## Data / execution corrections
The HEMA surrogate was rebuilt with explicit New York session buckets:
- 09:30–13:30 ET
- 13:30–16:00 ET
to eliminate the DST-induced 08:30/12:30 winter labeling error.

Net R now includes entry and both exit-leg costs. Historical half-days produce only the available 09:30 bucket and holidays produce no bar. Same-day/live early-close awareness remains a separate production-calendar requirement.

## Baseline caveat
The 30-symbol surrogate's very large portfolio-return headline is distorted by very narrow structural stops and no capital-availability/notional cap in the documented portfolio model. One APLD trade alone used roughly 6.8x book notional and generated about +54R net. Therefore total/marked return from this surrogate is not a trustworthy live-return estimate. R-based paired comparisons are more informative.

## HEMA findings

### 1. Hard bullish entry gate
**FAIL as a system change.**
- It improved per-trade quality but removed roughly two-thirds of QF opportunities.
- Corrected random-subset evidence was not significant.
- Confidence interval versus baseline included zero.
- It was weaker than baseline in 2026.

### 2. Small-green retest entry
**FAIL.**
- Severe sample reduction.
- No robust incremental edge over generic bullish-trend context.
- Parameter instability.

### 3. Recent big-green crossover as mandatory entry
**FAIL as a gate.**
- Corrected result remained visually spectacular but only 8 trades.
- It discarded ~96% of QF opportunities.

### 4. Recent big-green crossover as slot-ranking preference
**NO INCREMENTAL EFFECT / UNDERPOWERED on the 30-name sample.**
- Only 9 true ranking-pressure decisions.
- HEMA changed zero accepted sets.
- Baseline, HEMA, EMA and matched-random preferences produced identical accepted trades.
- This question requires the canonical 131-symbol universe where slot pressure is materially greater.

### 5. HEMA post-TP1 runner exits
**NO EVIDENCE OF IMPROVEMENT.**
Fixed-entry paired test, 208 entries, 50 bps:
- Current: +0.5964 net R/trade.
- Daily HEMA bearish crossover: +0.5966 R/trade; changed 29 trades; paired mean +0.00027R; 95% CI roughly -0.040 to +0.043R.
- Current exit confirmed by Daily HEMA bear regime: +0.5908R; slightly worse.
- 4H HEMA bearish crossover: +0.5874R; slightly worse.
- Daily/4H plain EMA crossover control: +0.6065R, but those crossover rules never actually fired post-TP1 in this sample; the difference came from default stop/timeout behavior, so they are not informative controls.

Runner giveback remained large. Daily HEMA did not reduce it; 4H HEMA reduced average giveback modestly but also reduced net R. No candidate had statistically persuasive paired improvement.

### 6. HEMA pre-TP1 emergency exits
**FAIL.**
Fixed-entry paired test, 208 entries, 50 bps:
- Current: +0.5964 net R/trade.
- 4H HEMA emergency cross: +0.4841R; mean paired change -0.1123R; 95% bootstrap CI about -0.228 to -0.014R. It avoided 11 eventual stops but cut 13 baseline winners early.
- Daily HEMA emergency cross: +0.5728R; mean paired change -0.0236R; CI includes zero. It avoided 8 stops but cut 7 baseline winners early.
- Unarmed current scanner-exit control: +0.5904R; no improvement.
- 4H EMA20/40 emergency cross: +0.5908R; no improvement.

The 4H HEMA emergency rule was materially harmful in this sample.

## Current decision
No HEMA rule tested so far earns a change to frozen/live Quality Flow.

HEMA remains useful visually as descriptive trend context, but the tested attempts to convert that visual appeal into incremental system edge did not survive controlled comparison.

## What is still legitimately open
1. **Canonical 131-symbol slot-ranking test** using the frozen PIT universe/data, because the 30-name sample had too little slot competition.
2. **Forward observation only**: log HEMA states/crosses alongside future QF signals without letting HEMA affect execution. This creates genuinely out-of-sample evidence.
3. Do not continue searching HEMA parameter combinations on the same 30-name history; that would become optimization/fishing.

No live change should be made unless one of those future tests supplies new evidence.
