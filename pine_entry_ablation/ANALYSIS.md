# ENTRY ABLATION — ANALYSIS (2026-09-18)

## 1. Ablation table (exploratory: UX51 4H, 2024-09-16→2026-09-14, 4bps)

| Variant | Trades | Win% | Exp (R) | Δ vs base | PF | Ret% | MaxDD% | AvgWin R | AvgLoss R | TP1% | Hold | StopOut% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V0 baseline | 263 | 44.9 | +0.195 | — | 1.27 | +35.3 | 35.2 | +2.02 | −1.29 | 47.5 | 18.1 | 93.9 |
| V1 no_volume | 350 | 45.7 | +0.231 | +0.036 | 1.35 | +4.3 | 28.1 | +1.97 | −1.23 | 48.9 | 19.2 | 93.4 |
| V2 no_hot_guard | 566 | 48.4 | +0.318 | +0.123 | 1.48 | +110.6 | 36.0 | +2.02 | −1.28 | 51.4 | 19.1 | 96.1 |
| V3 no_trend_bull | 531 | 41.4 | +0.082 | −0.113 | 1.17 | +34.0 | 36.2 | +1.39 | −0.84 | 29.0 | 10.8 | 52.5 |
| V4 no_strong_trend | 512 | 45.7 | +0.145 | −0.050 | 1.21 | +92.9 | 32.5 | +1.84 | −1.28 | 48.4 | 17.5 | 90.6 |
| V5 no_score_gate | 1092 | 44.4 | +0.178 | −0.017 | 1.28 | +70.9 | 45.6 | +1.85 | −1.16 | 45.6 | 17.1 | 78.0 |
| V6 no_breakout | 1309 | 47.4 | +0.139 | −0.056 | 1.30 | +106.0 | 41.3 | +1.27 | −0.88 | 32.7 | 12.1 | 52.6 |
| V7 no_ready_prev | 263 | 44.9 | +0.195 | 0.000 | 1.27 | +35.3 | 35.2 | +2.02 | −1.29 | 47.5 | 18.1 | 93.9 |
| V8 confirmed_only | 0 | — | — | — | — | — | — | — | — | — | — | — |
| V9 breakout_only | 263 | 44.9 | +0.195 | 0.000 | 1.27 | +35.3 | 35.2 | +2.02 | −1.29 | 47.5 | 18.1 | 93.9 |
| V10 ready_only | 0 | — | — | — | — | — | — | — | — | — | — | — |
| V11 no_confirmed | 263 | 44.9 | +0.195 | 0.000 | 1.27 | +35.3 | 35.2 | +2.02 | −1.29 | 47.5 | 18.1 | 93.9 |
| V12 no_breakout_mode | 0 | — | — | — | — | — | — | — | — | — | — | — |
| V13 no_ready_mode | 263 | 44.9 | +0.195 | 0.000 | 1.27 | +35.3 | 35.2 | +2.02 | −1.29 | 47.5 | 18.1 | 93.9 |

Baseline fidelity: V0 cfg verified bar-for-bar identical to `pine_buy_signal`
on all 51 symbols; rerun reproduces +0.195R exactly. (25bps ordering identical;
see results JSON.)

## 2. Component classification (expectancy + robustness, not win rate)

**ADDITIVE — removal worsens the system:**
- `trend_bull` (Δ−0.113): avg winner collapses 2.02→1.39R, TP1 rate 47.5→29%.
  The trend filter is what makes winners big. Strongest keeper.
- `breakout` (Δ−0.056): avg winner 2.02→1.27R. The fresh-breakout requirement
  selects the explosive moves.
- `strong_trend` (Δ−0.050): adx>20 + atr_ratio>0.85 keeps entries in real trends.

**HARMFUL (in the bull window) — removal improves:**
- `hot_guard` (Δ+0.123 → +0.318R, PF 1.48): not buying extended stocks cost
  dearly in 2024–26 — momentum persisted, so "hot" entries kept winning.
- `volume_ok` (Δ+0.036 → +0.231R, PF 1.35, DD improves 35.2→28.1%): the volume
  filter screened out good trades without adding quality.

**NEUTRAL-REDUNDANT:**
- `score_gate` (Δ−0.017, inside band): removal floods 829 extra confirmed trades
  and lifts DD +10.4pp. Its only function is suppressing confirmed mode. Keep.
- `ready_prev` (Δ=0): never binds; redundant given the other ready_buy conditions.
- `confirmed` mode: **ZERO signals in 2 years × 51 symbols** (score>=4 never
  satisfied alongside the other conditions). Dead code on this data.
- `ready_buy` mode: **ZERO signals.** Dead code on this data.
- Net: **the entire +0.195R edge comes from breakout_buy alone**
  (trend_bull + strong_trend + breakout + volume_ok + safe).

## 3. Frozen candidates (defined BEFORE 2022, see CANDIDATES_FROZEN.md)

Nested simplification ladder, component-removal only:
- **C1 "drop harmful"**: baseline − volume_ok − hot_guard.
- **C2 "drop harmful + neutral"**: C1 − score_gate.
- **C3 "breakout pure"**: C2 with modes={breakout_buy} only.

Research-window results (UX51 4H, 4bps):

| Candidate | Trades | Exp (R) | PF | MaxDD% | Bar (a) >0.195R | Bar (b) DD≤40% |
|---|---|---|---|---|---|---|
| C1 | 618 | +0.283 | 1.43 | 25.3 | PASS | PASS |
| C2 | 1372 | +0.164 | 1.27 | 50.0 | FAIL | FAIL |
| C3 | 618 | +0.283 | 1.43 | 25.3 | PASS | PASS |

(C3 ≡ C1 on the research window — confirmed/ready never fire with the score
gate on, so the mode prune is a no-op there. It differs from C1 only where
ungated confirmed/ready could fire.)

## 4. 2022 validation (32 symbols, 4H, signals ≥ 2022-01-01, EOD liquidation)

| Variant | Trades | Win% | Exp (R) | PF | Ret% | MaxDD% | Bar (c) > 0 |
|---|---|---|---|---|---|---|---|
| V0 baseline | 39 | 43.6 | **+0.287** | 1.35 | +11.2 | 20.4 | — |
| C1 | 122 | 47.5 | +0.007 | 1.01 | −1.2 | 28.5 | FAIL (noise) |
| C2 | 263 | 43.3 | −0.089 | 0.87 | −15.5 | 35.7 | FAIL |
| C3 | 122 | 47.5 | +0.007 | 1.01 | −1.2 | 28.5 | FAIL (noise) |

## 5. V3.7 verdict: KEEP V3.6. No candidate adopted.

C1/C3 passed the research-window bars and collapsed on unseen 2022 (+0.283R →
+0.007R, PF 1.01 = noise). C2 failed outright. Per the anti-overfit commitment,
no fourth candidate was built.

**Why it failed — the mechanism is coherent, not random:** the "harmful"
components were harmful only in a bull market. In 2024–26, buying extended
("hot") stocks worked because momentum persisted; skipping the volume filter
added winners. In the 2022 bear market, those same relaxed entries bought
overbought rips and dead-cat bounces — 122 trades at PF 1.01. The hot guard
and volume filter are **bear-market insurance**, the same species as the exit
study's finding: insurance that looks like a cost in good times and pays in
bad times.

**Bonus finding:** the V3.6 baseline itself is regime-robust — +0.287R on 2022
(39 trades, PF 1.35, DD 20.4%), stronger than its +0.195R bull-window result.

**Bottom line:** ~0.20R is the ceiling of this architecture. The edge lives in
one mode (breakout_buy) and three additive components (trend_bull,
strong_trend, breakout). Everything else is either bear-market insurance
(hot_guard, volume_ok, score_gate) or dead code (confirmed/ready modes,
ready_prev). There is nothing left to remove without breaking what the bear
market needs. V3.6 stands as-is.
