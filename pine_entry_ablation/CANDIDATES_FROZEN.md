# FROZEN CANDIDATES — written BEFORE 2022 validation (2026-09-18)

No changes after this point. A fourth candidate is prohibited.

## Ablation evidence (exploratory, UX51 4H 2024-09-16→2026-09-14, 4bps; baseline +0.195R)
- HARMFUL (removal improves): hot_guard Δ+0.123 (→+0.318R, PF 1.48, DD 36.0%);
  volume_ok Δ+0.036 (→+0.231R, PF 1.35, DD 28.1%).
- ADDITIVE (removal hurts): trend_bull Δ−0.113 (→+0.082R, avg winner collapses
  2.02→1.39R); strong_trend Δ−0.050 (→+0.145R); breakout Δ−0.056 (→+0.139R).
- NEUTRAL-REDUNDANT: score_gate Δ−0.017 but DD +10.4pp on removal (kept by default);
  ready_prev Δ=0 (never binds); confirmed mode: ZERO signals in 2y×51 symbols;
  ready_buy mode: ZERO signals. The entire baseline edge comes from breakout_buy alone.

## Candidates (nested simplification ladder, component-removal only)
- **C1 "drop harmful"**: baseline minus volume_ok, minus hot_guard.
  Entry = breakout_buy/confirmed/ready_buy with trend_bull + strong_trend +
  breakout (+ score gates where they apply) and NO volume filter, NO hot guard.
- **C2 "drop harmful + neutral"**: C1 minus score_gate.
  Confirmed/ready_buy may now fire without score>=4/>=3.
- **C3 "breakout pure"**: C2 with modes={breakout_buy} only.
  Entry = trend_bull AND strong_trend AND breakout; no volume, no hot guard,
  no score gate, no confirmed/ready modes.

Exact cfg dicts are written into pine_entry_validate.json at validation time.

## Adoption bar (per candidate, all three required)
(a) exploratory expectancy (4bps) > baseline +0.195R;
(b) exploratory maxDD ≤ 40%;
(c) positive expectancy on unseen 2022 4H (4bps).
If multiple pass: recommend the best expectancy/DD balance; all reported as
candidates for Mike to decide — NOT a recommendation to change his live script.
If none pass: verdict = "keep V3.6" (~0.20R is the ceiling of this architecture).
