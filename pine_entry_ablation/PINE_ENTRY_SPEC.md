# PINE_ENTRY_SPEC.md — Entry ablation, pre-specified BEFORE any test (2026-09-18)

FROZEN. No definitions change after results. Any deviation must be documented as a
protocol violation, not a silent edit.

## AMENDMENT A (2026-09-18 ~01:35 EDT, from Mike via parent — applied before candidate freeze)
1. Up to THREE frozen candidates allowed (was one). Build max 3 from the ablation
   evidence, all frozen before 2022 validation. No fourth after seeing validation.
2. Per-variant metrics extended: average winner (R), average loser (R), TP1 hit rate,
   average holding period (bars), stop-out percentage — in addition to trades, win%,
   expectancy R, PF, return%, maxDD%.
3. Component classification in the writeup: ADDITIVE (removal worsens expectancy/DD) /
   NEUTRAL-REDUNDANT (removal changes little) / HARMFUL (removal improves).
   Judge on expectancy and robustness, not win rate.
4. Final report to Mike: full ablation table, which components carry the edge, frozen
   candidate definitions, research-window results, 2022 validation results, V3.7 verdict
   (adopt one / keep V3.6). If none survives validation: "keep V3.6", plainly.
5. Hard constraints: Pine V3.6 entries only; exits byte-identical; 4H only; no shorts;
   no hedges; no continuous parameter search — component removal only. V5.4 forward
   test untouched.
6. Candidate rule (replaces old §Candidate construction): up to 3 candidates,
   constructed ONLY from component-removal evidence (harmful/neutral-redundant drops,
   optional mode pruning). Each candidate frozen with exact definition before 2022.
   Adoption bar per candidate: (a) exploratory expectancy (4bps) > +0.195R;
   (b) exploratory maxDD ≤ 40%; (c) positive expectancy on unseen 2022 (4bps).
   If multiple pass, recommend the one with the best expectancy/DD balance;
   report all as candidates for Mike to decide — NOT a recommendation to change
   his live TradingView script.

## Baseline
`pine_backtest.py::pine_buy_signal` (Hybrid), UX51 4H, 2024-09-16→2026-09-14,
4bps/25bps, $10k, 1% risk/trade, max 5 positions, next-bar-open entries,
stop-first ties, gap-below-stop skip. Exits byte-identical to baseline Pine exits
(validated — NOT ablated). Sanity: baseline rerun must reproduce ~+0.195R @4bps.

## Components under test (computed per signal bar i; r=current, rp=prior)
1. `volume_ok`: r.Volume > r.vol_ma (SMA20)
2. `hot_guard` (safe): hot = close > e9 + atr*1.5; safe = not hot
3. `trend_bull`: e21 > e55 and close > e200
4. `strong_trend`: adx > 20 and atr_ratio > 0.85
5. `score_gate`: score=(e9>e21)+(e21>e55)+(close>e200)+(adx>25)+(atr_ratio>1);
   confirmed requires score>=4, ready_buy requires score>=3
6. `breakout`: close > max High of prior 10 bars
7. `ready_prev`: rp.Close < rp.e21 and rp.Close > rp.e55 and rp.e21 > rp.e55
   and rp.atr_ratio > 0.85
8. Entry modes as units: `confirmed`, `breakout_buy`, `ready_buy`

## Removal variants (exactly one change per variant)
| ID | Change |
|---|---|
| V0 baseline | full entry |
| V1 no_volume | volume_ok forced True |
| V2 no_hot_guard | safe forced True |
| V3 no_trend_bull | trend_bull dropped from breakout_buy |
| V4 no_strong_trend | strong_trend dropped from breakout_buy |
| V5 no_score_gate | score>=4 and score>=3 dropped |
| V6 no_breakout | breakout condition dropped from breakout_buy |
| V7 no_ready_prev | ready_prev dropped from ready_buy |
| V8 confirmed_only | only confirmed fires |
| V9 breakout_only | only breakout_buy fires |
| V10 ready_only | only ready_buy fires |
| V11 no_confirmed | breakout_buy OR ready_buy |
| V12 no_breakout_mode | confirmed OR ready_buy |
| V13 no_ready_mode | confirmed OR breakout_buy |

## Interpretation rule (ablation)
Removal metric: Δ = expectancy_variant − expectancy_baseline, at 4bps.
- Δ < −0.03R → component HELPS (removal hurt). Keeper.
- Δ > +0.02R → component is DEAD WEIGHT (removal helped).
- |Δ| ≤ band → neutral; default KEEP (conservative).

## Candidate construction rule (mechanical, no judgment)
1. Compute Δ for V1–V7 at 4bps.
2. Candidate C1 = baseline with every DEAD WEIGHT component (Δ > +0.02R) removed.
3. If no component qualifies → C1 = baseline (report: no simpler entry found).
4. Mode check (V8–V13): if a single mode standalone beats baseline by > +0.03R
   with ≥ 60 trades, document it but do NOT build a second candidate —
   one candidate only (anti-overfit).
5. C1 requires ≥ 100 trades on the exploratory window for stability;
   otherwise verdict = inconclusive, no adoption.
6. C1 is frozen (definition written to results JSON) BEFORE touching 2022.

## Validation (2022-01-01→2022-12-31, 4H)
- Data: union of v6_short_v2/cache/d4h_2022_*.pkl and pine_exit_fix/cache_2022/d4h_2022_*.pkl
  (dedupe by symbol; document final symbol list and count honestly).
- Run V0 baseline AND C1 only. Same conventions, same exits.
- Adoption bar (ALL THREE required):
  (a) C1 exploratory expectancy (4bps) > baseline +0.195R;
  (b) C1 exploratory maxDD ≤ 40%;
  (c) C1 positive expectancy on unseen 2022 (4bps).
- If adopted: report as a CANDIDATE for Mike to decide on — NOT a recommendation
  to change his live TradingView script.
- If not adopted: verdict = ~0.20R is the ceiling of this architecture.
- NO second candidate fitted on 2022. Ever.
