# Test Report: Long→Short Flip Test

Date: 2026-09-25. Ordered by Mike. Pre-registered BEFORE execution
(`selection_edge/flip_short_prereg.md`, commit `e709875`) — frozen, no
tuning after results. **Result: FAIL** (all three pre-set criteria failed).

## What ran

Question: buy the validated buy signals, then flip to SHORT at the long
leg's exit — is the combo more profitable than long-only? Tested on all
three timeframes on the 13-stock watchlist (QQQ, SMCI, PLTR, ANET, SOFI,
RKLB, ONDS, DRAM, SPCX, BBAI, NIO, HOOD, AMD; ASTX excluded per prereg — no
validated data, leveraged ETF).

- Entry: `pine_buy_signal` (imported unmodified from `pine_backtest.py`),
  applied per timeframe; entry at next bar open; stop = signal close −
  ATR×1.5; TP1 = entry + ATR×2.0.
- Arm A: long-only, Mode B exit stack (`canonical_baseline/modeb_engine`,
  imported unmodified, realistic gaps).
- Arm B: identical long leg, then SHORT at the next open after the long's
  exit bar, with mirrored geometry (same risk distance, flipped side),
  executed by the unmodified Mode B engine on price-negated bars (exact
  mirror — verified: median short STOP −1.175R vs median long STOP −1.18R).
- Costs: 50 bps round-trip per leg, deducted in R. Arm B pays twice.
- 4,779 paired trades (identical signal population both arms). Eligibility:
  ≥61 bars after the signal bar so both legs complete in-data.

## Post-prereg methodology correction (one, documented)

The first run produced −100R "trades": when the entry gapped down to
microscopically above the stop, the planned risk ($0.0017/share in the worst
case) was smaller than the round-trip friction itself, and the prereg's
R-denominated cost formula exploded. Those signals are untradeable by
construction — no one can trade a stop tighter than the spread. Correction:
skip signals where planned risk < round-trip cost (120 signals, 2.4%),
applied symmetrically to both arms so the paired comparison is intact. This
is a bug fix for nonsense values, not tuning: it cannot favor either arm.

## Results

Expectancy in R/trade (net of costs), win rate, profit factor, max drawdown:

| Timeframe | Arm A long-only | Arm B combo (long+flip) | Short leg alone |
|---|---|---|---|
| 1H (n=3,275) | −0.160R, 36.4% wr, PF 0.80, DD 554R | −0.504R, 36.5% wr, PF 0.59, DD 1,655R | −0.344R, 32.8% wr, PF 0.59 |
| 4H (n=683) | **+0.254R**, 44.8% wr, PF 1.40, DD 50R | −0.180R, 41.4% wr, PF 0.83, DD 156R | −0.434R, 29.0% wr, PF 0.45 |
| Daily (n=821) | **+0.329R**, 47.0% wr, PF 1.61, DD 38R | −0.030R, 43.2% wr, PF 0.97, DD 113R | −0.359R, 30.8% wr, PF 0.51 |
| Pooled (n=4,779) | −0.017R, PF 0.98 | −0.376R, PF 0.67 | −0.360R |

## Decision vs the pre-set rule

1. Arm B beats Arm A on ≥2 of 3 timeframes: **NO** — 0 of 3.
2. Pooled Arm B expectancy > 0: **NO** (−0.376R).
3. Pooled Arm B drawdown ≤ 1.2× Arm A: **NO** (1,807R vs 325R).

**FAIL.** No partial credit, no re-tuning — per the prereg, the flip idea
is closed alongside the 2026-09-17/18 short-side closure.

## Plain-words interpretation

Flipping to short after the long exits does not harvest post-exit drift —
it just adds a second losing system. The short leg loses on every timeframe
(−0.34 to −0.43R, ~30% win rate, profit factor ~0.5), which is the same
no-short-edge result the closed short-signal research found, now confirmed
from the other direction. The damage is worst on 1H, where the long baseline
itself is already ~zero (−0.16R): the flip turns a flat system into −0.50R.
On 4H and daily the long-only baseline is genuinely positive (+0.25R /
+0.33R on this watchlist with Mode B exits) — and the flip destroys it in
both cases. Drawdowns roughly triple. There is no timeframe, and no leg of
the combo, where the short side earns its keep.

Caveats (from the prereg): shorting modeled frictionless (no borrow fees —
real economics are worse, especially SMCI/ONDS/BBAI); trade-level replay, no
portfolio constraints; entry logic tuned on 4H, 1H/daily are unmodified
transfers; ASTX excluded.

## Files

- `selection_edge/flip_short_prereg.md` (commit `e709875`)
- `selection_edge/flip_short_run.py`, `flip_fetch.py`, `flip_fetch_log.json`,
  `flip_short_trades.json`, `flip_short_results.json` (local working files)
- This report: `selection_edge/flip_short_report.md`

Nothing frozen was modified. No forward-test interference. No live path.
