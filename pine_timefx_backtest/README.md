# P14 — Time effects (2026-09-24)

**Question:** do structural timing effects (day of week, month, earnings
proximity, quarter-end, opex week) affect baseline trade expectancy?

**Verdict: NO** — no calendar effect is strong, persistent across years, and
explainable. The null hypothesis (time effects are noise) stands.

## Setup

Measurement study on canonical 4H Hybrid baseline trades only. Baseline
sanity: **237 trades, +0.2388R @25bps** ✓ (`pine_backtest` imported
unmodified). Earnings dates from yfinance, actual reported dates only,
cached in `earnings_dates.json`. DRAM/ASTX (delisted per yfinance) and SPCX
(ETF, 1 date) have no usable earnings history — noted as a limitation; they
contribute 5 trades total, all in the "none" bucket.

## Bucket results (25bps)

| bucket | n | exp R | win% |
|---|---|---|---|
| Mon | 49 | +0.010 | 49.0 |
| Tue | 47 | +0.522 | 46.8 |
| Wed | 56 | +0.204 | 57.1 |
| Thu | 48 | +0.262 | 43.8 |
| Fri | 37 | +0.205 | 56.8 |
| earnings pre (±5d before) | 12 | −0.255 | 41.7 |
| earnings day | 2 | +1.772 | 50.0 |
| earnings post (±5d after) | 13 | +0.843 | 76.9 |
| earnings none | 210 | +0.215 | 49.5 |
| quarter-end (last 5 biz days) | 11 | +0.363 | 54.5 |
| opex week | 52 | +0.469 | 55.8 |
| opex rest | 185 | +0.174 | 49.2 |

## Persistence check (the part that kills every headline)

- **Tuesday (+0.522R pooled):** 2024 +1.25R, 2025 +0.45R, **2026 −0.73R**.
  Flips sign. Noise.
- **Opex week (+0.469R pooled):** 2024 +0.20R, 2025 +1.10R, **2026 −0.36R**.
  Flips sign. Noise.
- **Quarter-end (+0.363R):** n=11 total, 2026 flips to −1.44R (n=1). Thin + flips. Noise.
- **Months:** no month is positive in all three years. April looks best pooled
  (+1.228R) but was −1.25R in 2024. October/November/December positive in
  2024, negative in 2025. Noise.
- **Wednesday** is the only weekday positive all three years
  (+0.15/+0.22/+0.25) — persistent but small, and with 5 weekdays tested the
  multiple-comparison bar is not cleared. No mechanism. Not promoted.

## The one honest thread (watch-only, NOT a filter)

**Post-earnings entries: +0.843R, positive in every year with data**
(2024 +0.64R n=4, 2025 +1.20R n=6, 2026 +0.41R n=3), 76.9% win rate.
Mechanism is plausible (post-earnings drift: uncertainty resolved, trend
extends). But n=13 total across three years is far too thin to promote —
per the mandate, small samples are noise unless replicated. Pre-earnings
(−0.255R) flips sign by year. Recorded as watch-only; no filter.

## Bottom line

~20 buckets tested; every headline bucket either flips sign by year or sits
on a thin sample. Exactly what the null hypothesis predicts. **No time-based
filter. This priority is closed.**

## Files

- `run_timefx.py` — study script (`pine_backtest` unmodified)
- `timefx_results.json` — buckets, year persistence tables, earnings coverage
- `earnings_dates.json` — cached yfinance earnings dates per symbol
- `README.md` — this file

Guardrails respected: research only; no frozen files (V5.4, Mode B, alerts,
grades, exits, market gate, AI Observer) touched.
