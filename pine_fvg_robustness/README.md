# FVG-as-entry challenger: robustness study (Mike's spec, 2026-09-24)

**Question:** is FVG-as-entry genuinely better than the 4H Hybrid baseline, or did
+0.285R vs +0.239R come only from changing *which* trades were taken?

**Answer up front: it's 100% trade selection — and the selection edge is real but
thin and concentrated. Verdict: MAYBE.** Details below.

## Setup

- Universe: 14-stock watchlist (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM,
  SPCX, ASTX, BBAI, NIO, HOOD, AMD), 4H bars, Oct 25 2023 – Sep 23 2026
  (cached pickles from `pine_entry_timing_backtest/cache`; 2022 NOT in sample —
  data starts Oct 2023, warmup kills 2023).
- Exits: frozen Mode B via `gen_pine_trades`, untouched. `pine_backtest.py`
  imported unmodified; only `pine_buy_signal` monkey-patched per variant.
- Variants: BASE (canonical), FVG (canonical OR FVG sub-signal = current sidecar),
  FVG_P1 (vol > 1.2×vol_ma), FVG_P2 (no HOT_ATR safe filter), FVG_P3
  (no close>e21 requirement). Perturbations pre-declared, no tuning.
- Costs stressed at 25/50/75/100 bps. Walk-forward split: train ≤2024-12-31,
  test ≥2025-01-01 (nothing tuned on test).
- Research only. V5.4, Mode B, alerts, grades, market gate, AI Observer untouched.

## 1. Matched-trade analysis — the central result

| | count |
|---|---|
| Shared setups (both variants took the same signal) | 203 |
| of which: byte-identical fills (entry/stop/exit) | **203** |
| BASE-only trades | 34 |
| FVG-only trades | 63 |

**Shared-setup ΔR = 0.0000R** (both 0.2536R). Same signal bar → same ATR-derived
stop/TP1 → same next-bar entry. There is NO entry-price, entry-timing, or
stop-geometry effect whatsoever. Mike's question is answered directly: **FVG is
not a better entry mechanism. It is a trade-selection mechanism.** The entire
+0.046R comes from taking different trades.

## 2. Attribution of the +0.046R gap

| Component | Contribution |
|---|---|
| Better entry price/timing (shared setups) | **+0.0000R** |
| Added FVG-only trades (63 @ +0.387R, 46% win, PF 1.71) | +0.0351R |
| Dropped BASE-only trades (34 @ +0.150R vs 0.239 baseline) | +0.0127R |
| Reweighting residual | −0.0014R |
| **Total** | **+0.0464R** |

~76% of the gain = added trades that run hot (+0.387R, PF 1.71 — genuinely
good, not a fluke of a few trades); ~27% = avoiding mediocre baseline trades.

## 3. Regime robustness — the big red flag

Regime = QQQ 4H close vs 200-bar SMA at signal bar.

| Regime | BASE | FVG |
|---|---|---|
| Bull (n=221/246) | +0.182R | +0.183R — **identical** |
| Bear/sideways (n=16/20) | +1.029R | +1.537R |

Year × regime cross-tab:

| Bucket | BASE | FVG |
|---|---|---|
| 2024 bear/side (n=3/4) | +1.705R | **+4.524R** |
| 2025 bear/side (n=7/9) | +1.223R | +1.166R (worse) |
| 2026 bear/side (n=6/7) | +0.465R | +0.306R (worse) |
| 2024 bull (n=72/76) | +0.291R | +0.241R (worse) |
| 2025 bull (n=95/103) | +0.384R | **+0.477R** |
| 2026 bull (n=54/67) | −0.321R | −0.333R (worse) |

**Four trades in the 2024 bear bucket averaging +4.5R contribute ≈+0.049R —
more than the entire +0.046R edge.** In bull regimes (93% of trades) FVG adds
nothing. The one genuinely broad win is 2025 bull (+0.09R, n≈100). 2026 YTD
both variants are underwater, FVG slightly worse.

## 4. Symbol / sector robustness — mixed, not broad

Improves: AMD (+0.53 vs +0.20), RKLB (+1.13 vs +0.80), NIO (+0.44 vs +0.13),
SOFI (+0.33 vs +0.16). Gets WORSE: BBAI, PLTR, ONDS, HOOD, and the whole
Software/AI theme (+0.30 vs +0.53) and Drones (+0.53 vs +0.66). Both negative
on AI Infra and QQQ. The edge is not a rising tide — it's concentrated.

## 5. Cost stress — survives

| Cost | BASE | FVG | FVG_P1 | FVG_P2 | FVG_P3 |
|---|---|---|---|---|---|
| 25bps | 0.239 | 0.285 | 0.279 | 0.333 | 0.265 |
| 50bps | 0.178 | 0.225 | 0.218 | 0.273 | 0.205 |
| 75bps | 0.117 | 0.164 | 0.156 | 0.212 | 0.146 |
| 100bps | 0.056 | 0.103 | 0.095 | 0.151 | 0.086 |

Gap persists at every cost level. Both variants stay positive through 100bps.

## 6. Perturbation — survives, with a warning

All three nearby definitions beat baseline (+0.265 to +0.333R). The edge is not
a knife-edge artifact of one exact threshold. **WARNING: FVG_P2 (dropping the
safe filter) jumps to +0.333R — do NOT adopt it.** That is exactly the
optimization trap this study was designed to avoid; it gets no validation
here and is reported only as a robustness data point.

## 7. Distribution (25bps)

| | BASE | FVG |
|---|---|---|
| Trades | 237 | 266 |
| Expectancy | +0.239R | +0.285R |
| Win rate | 50.6% | 50.4% |
| Profit factor | 1.38 | 1.48 |
| Median trade | +0.147R | +0.108R |
| Avg winner / avg loser | +1.71 / −1.27R | +1.75 / −1.20R |
| Max losing streak | 8 | 11 |
| MFE / MAE (mean) | +2.83 / −1.13R | +2.85 / −1.10R |
| Portfolio total return | (in JSON) | (in JSON) |

Same win rate, slightly longer losing streaks under FVG, no MFE/MAE advantage.

## 8. Walk-forward — edge decays out-of-sample

| | BASE | FVG | Δ |
|---|---|---|---|
| Train (≤2024, n=75/80) | +0.347R | +0.455R | +0.108 |
| Test (≥2025, n=162/186) | +0.188R | +0.212R | **+0.024** |

Edge survives the split but shrinks ~4.5×. Classic decay signature.

## Verdict: MAYBE

- **Not broad:** ~the whole +0.046R traces to 4 outsized 2024 bear-regime trades;
  bull-regime performance is identical; several symbols/themes get worse.
- **Explainable (now):** it's pure selection — FVG adds good pullback-into-gap
  setups (+0.387R, n=63) and drops mediocre ones. No entry-mechanism magic.
- **Partially robust:** survives costs and perturbations; walk-forward positive
  but decayed; 2026 YTD favors BASE slightly.

**Overfitting flags, stated plainly:** (1) FVG was the best of several tested
variants — cross-study selection bias inflates the headline; (2) the 4-trade
concentration in 2024 bear conditions is the definition of a thin bucket;
(3) P2's +0.333R is bait — reported, not adopted, not validated.

**Recommendation:** keep the live paper sidecar running (true out-of-sample
arbiter, uncontaminated) — do NOT promote FVG to production on this evidence.

## Files

- `run_fvg_robustness.py` — study script (`pine_backtest` unmodified)
- `fvg_robustness_results.json` — all variants, matched pairs, attribution,
  yearly/regime/symbol/theme splits, cost stress, walk-forward
- `README.md` — this file
