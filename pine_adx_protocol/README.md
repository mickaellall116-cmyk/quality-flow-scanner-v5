# TEST 3 — ADX crowded-signal ranking under Mike's exact validation protocol (2026-09-25)

**HYPOTHESIS.md frozen before running. `pine_backtest` and
`pine_ranking_confirm` helpers imported unmodified. Research only — V5.4,
Mode B, alerts, grades, market gate, AI Observer, the adopted rs_top2 rule,
and the live scoreboard untouched.**

## Hypothesis
When more valid signals exist than available portfolio slots, ADX identifies
better trades than the current RS ranking.

## Exact rule (fixed)
ADX(14) descending, take top min(2, free) at contested timestamps
(candidates > free slots, free > 0). Same 237-trade signal population for
A. take-all (arrival order, reference), B. current RS ranking (20-bar return
minus SPY), C. ADX. The RS+ADX combo was NOT run: RS does not beat take-all
(+0.160R vs +0.221R), so per the prompt and the mandate's "do not combine
weak discoveries" rule the combo is not justified.

## Primary metric: SELECTION EDGE (Mike's definition)
Per crowded bar: mean R of method-selected trades minus mean R of
method-rejected trades. 21 genuine crowded bars in 3 years.

| | ADX | RS |
|---|---|---|
| mean selection edge | **+0.651R** | −0.418R |
| median | +0.227R | −0.085R |
| bars positive | 57% | 48% |
| bootstrap (5000): frac of resample means > 0 | **95.1%** | 20.8% |
| bootstrap p5 / p50 / p95 | +0.002 / +0.630 / +1.296 | −1.221 / −0.398 / +0.371 |

Within crowded bars, ADX systematically picks the better trades and rejects
the worse ones; RS does the opposite. The ADX bootstrap 90% interval sits
entirely above zero.

Selection edge by year: ADX +0.322 (2024) / +0.731 (2025) / +0.790 (2026) —
positive in ALL three years. RS: +0.353 / −0.676 / −0.630.

## Per-method report (full sample, 237 eligible signals, 25bps)

| method | selected | exp R | PF | win% | maxDD% | avg winner | avg loser | mean MFE | mean MAE | total ret |
|---|---|---|---|---|---|---|---|---|---|---|
| take-all | 178 | +0.221 | 1.34 | 50.0 | 25.30 | +1.756 | −1.314 | +2.808 | −1.142 | 42.05% |
| RS (current) | 179 | +0.160 | 1.24 | 48.0 | 31.25 | +1.747 | −1.308 | +2.742 | −1.157 | 27.02% |
| ADX | 178 | **+0.314** | 1.50 | 50.6 | 26.78 | **+1.851** | −1.258 | **+3.006** | −1.118 | 68.01% |

Opportunity cost (rejected vs take-all reference): ADX rejected 14 trades @
**−0.650R** (dodged losers); RS rejected 11 trades @ **+0.311R** (skipped
winners). Two-sided skill confirmed for ADX, backwards for RS.

Crowded-bar subset (trades taken at the 21 genuine bars): take-all 25 @
−0.021R / RS 26 @ −0.278R / **ADX 26 @ +0.569R** (win 46.2%, avg winner
+2.528R, avg loser −1.111R).

## A. Year test (per-contest advantage, ADX vs take-all)
2024: +0.002 (n=5, flat) · 2025: **+0.956** (n=10) · 2026: −0.371 (n=6).
The vs-take-all differential is 2025-driven. (Selection edge, the within-bar
measure, is positive all three years — see above.)

## B. Cost test (full-sim Δ expectancy, ADX − take-all)
25bps: +0.093 · 50bps: +0.095 · 75bps: +0.098 · 100bps: +0.107.
Survives and is stable under friction. (RS collapses to +0.003R at 100bps.)

## C. Leave-one-symbol-out
Per-contest advantage and full-sim Δexp recomputed dropping one symbol:
no removal flips the differential negative (full-sim Δexp stays
+0.002…+0.107). Caveat: removing PLTR drops full-sim Δexp to +0.0022 —
effectively zero. Fragile at the margin, not robustly killed.

## D. Concentration
Differential (28 differing trades, +16.5R total): top-1 trade 25.7%, top-3
69.5%, top-5 96.8% of the differential. By year: 2025 supplies **112.7%**
(2024 +0.13R, 2026 −2.23R). By symbol: BBAI +8.14, SMCI +4.96, PLTR +3.51;
RKLB −2.59. The pooled edge is a 2025 phenomenon — pre-declared FAIL
condition for PASS is triggered on the concentration gate.

## E. Out-of-sample (dev ≤2024-12-31 / val ≥2025-01-01)
Per-contest advantage: dev +0.002 (n=5) · **val +0.458 (n=16)**.
Positive on validation; dev is 5 contests (uninformative, not negative).
HONEST CAVEAT: the ADX rule (period 14, descending top-2) was defined in
P2/confirmatory on the full sample, so this is a period-robustness check,
not a clean pre-registration.

## F. Walk-forward (12mo observe / 6mo test / 6mo roll)
Test windows: 2024-10→2025-03 +0.554 (n=4) · 2025-04→2025-09 +1.242 (n=6) ·
2025-10→2026-03 −0.531 (n=4) · 2026-04→2026-09 +0.006 (n=5).
Combined untouched test windows: **+0.399R/contest (n=19)**. 3 of 4 positive.

## G. Bootstrap (≥5000)
Per-contest advantage: 5000 resamples, median +0.335, **87.9% of resample
means > 0** (p5 −0.133, p95 +0.883). Selection edge: **95.1% > 0**.
Positive expectancy is typical, not a lucky tail — but the tail is wide
because n=21.

## Perturbation (not optimization)
Per-contest advantage: ADX(10) +0.200 · ADX(14) +0.350 · ADX(20) +0.313.
Directionally consistent — the general idea survives nearby periods.

## Regime splits
Uninformative: all 21 crowded bars fall in the P4 bull regime
(SPY>200EMA & rising), 20/21 at VIX<20. No regime variation exists in the
differential sample. Reported, not hidden.

## Economic effect summary (25bps)
Δexp +0.093R · ΔPF +0.16 · ΔDD +1.48pp (slightly worse vs take-all;
−4.47pp vs the RS rule) · 14 ranked out @ −0.650R / 14 swapped in @
+0.530R · return/DD: ADX 2.54 vs take-all 1.66 (at 100bps: 0.63 vs 0.01).

## Verdicts (pre-declared gates)

**Verdict A — ADX vs the adopted rs_top2 rule: PASS** (replace-bad-rule
decision). ADX beats RS pooled (+0.154R @25bps, +0.151/+0.148/+0.132 at
50/75/100bps), on validation (+0.773/contest), in 2 of 3 years (2024 flat
on 5 contests), at nearby ADX periods (confirmatory: +0.272/+0.302 vs
+0.160), with two-sided skill (selection edge +0.651 vs −0.418, bootstrap
95% vs 21% above zero), and no single-symbol dependency (LOSO all
positive, +0.037…+0.157). The production rule is confirmed harmful:
−0.061R vs take-all, +6pp drawdown, skips winners (+0.311R) and takes
losers (−0.606R). Caveat: dev sub-sample is 5 contests (uninformative);
production change still needs Mike's approval and forward evidence.

**Verdict B — ADX vs take-all (do nothing): MAYBE.** Pooled advantage is
positive with real two-sided skill, survives costs, survives perturbation,
bootstrap-typical (87.9%), positive on validation (+0.458) and combined
walk-forward (+0.399) — but it is 2025-concentrated (112.7% of the
differential; 2024 flat, 2026 negative), the differential sample is 21
contests, and PLTR removal nearly zeroes it. Blocked from PASS by the
pre-declared concentration and year-breadth gates; not FAIL because the
edge does not disappear on validation, survives friction/perturbation,
and the within-bar selection skill is positive in all three years.
The ADX shadow on the live scoreboard is the only arbiter for the
take-all question — currently vacuous (0 crowded bars on the forward
test so far; max 2 signals/bar).

## Research backlog (observed, NOT tested)
1. Crowded bars are bad for everyone on the ≥3-candidate cut (all methods
   negative) yet ADX-selected trades at genuine contested bars run +0.569R.
   Hypothesis: simultaneous breakouts across a concentrated momentum
   watchlist mark late-stage breadth thrusts / chop; ranking quality and
   bar crowdedness may interact. Mechanism: breadth-thrust exhaustion.
   Reason noticed: the two crowded-bar cuts disagree in sign.
2. Selection edge as a live metric: log per-bar selection edge on the ADX
   shadow's crowded bars as they occur forward — needs crowded bars first.
3. Universe transfer: the 14-name result may not transfer to the 250-symbol
   forward universe, where crowded bars actually occur. The live shadow is
   the test; do not backtest the 250 (different population, different
   question).

## Files
- `HYPOTHESIS.md` — frozen pre-registration (rule, baselines, windows, gates)
- `run_adx_protocol.py` — 12-step protocol (per-contest, dev/val, walk-forward,
  years, regimes, costs, perturbation, concentration, bootstrap, LOSO, economics)
- `run_addendum.py` — dev/val + yearly + LOSO for ADX vs RS (Verdict A gates)
- `run_selection_edge.py` — Mike's SELECTION EDGE metric, per-method reports
  (avg winner/loser, MFE/MAE, opportunity cost), combo justification check
- `adx_protocol_results.json`, `adx_protocol_addendum.json`,
  `adx_selection_edge.json` — full results
- `README.md` — this file

Guardrails respected: research only. V5.4, Mode B, production alerts, grades,
exits, market gate, AI Observer, the adopted rs_top2 rule, and the live
scoreboard untouched.
