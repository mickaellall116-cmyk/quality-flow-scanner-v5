# MFE/MAE Diagnostic — Analysis

**Verdict: LEAK FLAGGED — but it is runner-phase giveback, not premature stop-outs. No fix proposed (per spec).**

Fidelity: bull-window replay reproduces the baseline exactly (263 trades, +0.195R @4bps).
Excursion measured from 4H bar high/low over [entry bar, exit-trigger bar]; realized R is
gross blended (50% TP1 limit at +1.333R if hit + 50% final exit, no costs).

## Pre-registered decision rule vs results (bull window)

| Criterion | Bar | Observed | Result |
|---|---|---|---|
| (a) median capture (realized/MFE), winners | ≥ 0.50 | **0.335** | FAIL |
| (b) stopped trades reaching +2R MFE | < 25% | **41.7%** | FAIL |
| (c) winners touching −0.75R MAE | < 25% | **33.1%** | FAIL |

All three fail → leak flagged per spec. The decomposition below shows exactly
where the leak lives.

## The five questions

### 1. How far do winners run before the exit takes them out?
Median MFE 3.19R (p25 2.43, p75 6.18, p90 11.10, max 85.28). Every one of the
118 winners hit TP1 (+1.333R limit on half). The right tail is extreme: 20 winners
ran past +8R MFE.

### 2. How much profit do winners give back?
Median giveback (MFE − realized) **2.28R** (p25 1.66, p75 3.95, p90 6.92).
Median capture **0.335** — winners keep about one-third of peak excursion.
Capture improves with trade size: 0.22 for MFE<2R, 0.31 for 2–4R, 0.38 for 4–8R,
0.39 for >8R. The top-5 MFE trades (XRP 85R→31R, SOL 34R→13R, ETH 23R→10R,
LINK 20R→7R, CRWD 19R→8R) show the pattern: the system surrenders ~60% of
monster moves and still banks 7–31R on each. Those monsters fund the expectancy.

### 3. How deeply do eventual winners go against us first?
Median winner MAE −0.51R (p25 −0.88, p75 −0.21). 50.8% touched −0.5R;
33.1% touched −0.75R (stop sits at −1R). Winners routinely endure meaningful
heat — a third came within 0.25R of the stop and still won.

### 4. Do stopped trades commonly recover (reach large MFE before stopping)?
103 of 247 stopped trades (41.7%) reached +2R MFE. **All 103 had hit TP1 first**
— this is the runner trailing out after banking +0.667R on half, i.e. the
designed giveback, not the stop malfunctioning. The informative split:
- `stop_no_tp1` (123 trades, stopped before TP1): median MFE **0.43R**, max 1.51R,
  mean net −1.41R. These were dead trades — the initial stop is NOT clipping
  anything that was working.
- `stop_after_tp1` (124 trades): median MFE 3.15R, mean net **+1.90R**. The
  runner cohort is profitable on average despite the giveback.

### 5. Winner vs loser excursion
| | Winners (118) | Losers (145) |
|---|---|---|
| MFE median | 3.19R | 0.47R |
| MFE p90 | 11.10R | 1.23R |
| MAE median | −0.51R | −1.45R |

Clean separation: losers almost never showed real promise (p90 MFE 1.23R, only
29/145 ever reached +1R, only 7 hit TP1 and still lost). The −1R initial stop
discriminates well.

## 2022 bear window (30 trades, 25 symbols — robustness read)
Same structure: median winner MFE 2.89R, median capture 0.368, median giveback
2.04R; 28% of stopped reached +2R (n=25, small sample); winners' MAE shallower
(median −0.38R, 8.3% touched −0.75R). The giveback pattern is regime-independent:
it is structural to the TP1+trail design, not a bull-market artifact.

## Exit-type buckets (bull)
| Bucket | n | MFE med | MAE med | net R mean |
|---|---|---|---|---|
| stop, no TP1 | 123 | 0.43 | −1.46 | −1.41 |
| stop, after TP1 (runner) | 124 | 3.15 | −0.54 | +1.90 |
| ema55 / trend | 16 | 0.74 | −1.01 | −0.69 |

## Interpretation (diagnostic only — no fix proposed)

The flagged leak is **runner-phase profit giveback**, concentrated entirely in
trades that already banked TP1. It is NOT premature stop-outs: the initial −1R
stop shows excellent winner/loser separation, and no winner was ever stopped
before TP1.

Whether the giveback is a defect or the price of catching 85R monsters is a
design question this study cannot settle — but there is already direct evidence
on the obvious remedy: the exit-fix study's slower 3.5× ATR trail (fixC) had the
best bull-window numbers (+0.419R) with a 43% drawdown and **failed 2022**.
Reducing giveback by slowing the trail is exactly the kind of bull-window
improvement that breaks in a bear market.

Per the pre-registered spec: leak reported, no fix designed, tested, or proposed.
