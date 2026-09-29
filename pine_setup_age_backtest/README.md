# P7 — Setup Age Study

**Question:** do setups lose quality as they age? Report the actual expectancy curve; do not assume fresher is better.

**Verdict: NO** — no age filter justified. The curve is hump-shaped, not decaying, and the one bad-looking bucket fails the persistence check.

## Setup

- Canonical 4H Hybrid baseline, 14-stock watchlist, 4H bars, Oct 2023–Sep 2026
- Frozen Mode B exits, 25 bps costs. Baseline sanity check: **237 trades, +0.2388R** ✓
- For each taken trade, bars-since-event at the signal bar; buckets 0–1 / 2–5 / 6–10 / 11+ / never
- Event definitions (pre-declared): breakout10 = close > max(high, prior 10) — same window as the signal's breakout_buy; bos20 = same over 20 bars; choch = breakout10 after trading under e55 in the prior 10 bars; fvg_formed = low > high[−2] (V3.7 Pine formation rule); trend_align = bars since e21>e55 & close>e200 last flipped true
- Note: 2023 has n≈0 everywhere (sample starts Oct 25 2023; 215-bar warmup consumes the rest)

## Age curves (25 bps)

| bucket | breakout (n, exp) | bos (n, exp) | choch (n, exp) | fvg (n, exp) | trend_align (n, exp) |
|---|---|---|---|---|---|
| 0–1 | 47, +0.314R | 28, +0.184R | 25, +0.559R | 97, +0.123R | 36, +0.308R |
| 2–5 | 72, +0.530R | 61, +0.726R | 47, +0.082R | 82, +0.454R | 28, +0.016R |
| 6–10 | 52, −0.041R | 45, −0.177R | 32, +0.066R | 39, −0.081R | 22, +0.384R |
| 11+ | 66, +0.088R | 103, +0.147R | 133, +0.275R | 19, +0.557R | 149, +0.243R |
| never / not_aligned | 0 | 0 | 0 | 0 | 2, +0.174R |

## What the curve actually looks like

**Hump-shaped, not decaying.** Fresher is NOT better: the 2–5 bar bucket beats the 0–1 bucket on breakout (+0.530 vs +0.314), bos (+0.726 vs +0.184), and fvg (+0.454 vs +0.123). Mechanism guess: the signal often fires a few bars after the structural event (confirmed/ready entries following the breakout) — those "second-wave" entries are the sweet spot, while same-bar entries include more false starts.

**The 6–10 "dead zone" is a mirage.** Pooled it looks bad across breakout/bos/fvg, but by year it flips sign:

| dimension, 6–10 bucket | 2024 | 2025 | 2026 |
|---|---|---|---|
| breakout | n=18, +0.648R | n=19, −0.385R | n=15, −0.432R |
| bos | n=18, +0.648R | n=15, −0.795R | n=12, −0.641R |
| fvg | n=15, +0.329R | n=15, −0.293R | n=9, −0.410R |

Positive in 2024, negative in 2025/2026 → fails persistence. Not a filter.

**Fresh choch looks great pooled (+0.559R, n=25) but also fails persistence:** 2024 +0.401 (n=8), 2025 +1.060 (n=12), 2026 −0.388 (n=5).

**Trend alignment: flat.** 149 of 237 trades fire 11+ bars into an established trend (+0.243R) — the system is a ride-established-trends system. Fresh alignment (0–1, +0.308R, n=36) is fine but not the bulk. No curve to exploit.

## Signal composition (context, feeds P13)

| composition | n | exp | win | PF |
|---|---|---|---|---|
| pure_breakout | 9 | +0.716R | 66.7% | 3.74 |
| pure_ready | 19 | +0.463R | 47.4% | 1.89 |
| confirmed+breakout | 10 | +0.318R | 60.0% | 1.59 |
| pure_confirmed | 146 | +0.286R | 51.4% | 1.44 |
| confirmed+ready | 52 | **−0.053R** | 46.2% | 0.92 |
| breakout+ready | 1 | −0.822R | 0.0% | 0.0 |

Confirms the P6 flag: the confirmed+ready overlap (n=52) dilutes the edge vs pure confirmed (+0.286R) and pure ready (+0.463R). This is a P13 (signal sequencing) follow-up candidate, not a P7 filter.

## Verdict

**NO.** No age bucket is broadly and persistently worse across years, so no age filter is justified. Honest findings: (1) the curve humps at 2–5 bars — fresher is not better; (2) the 6–10 dead zone fails persistence; (3) most edge lives in established trends (11+ bars aligned), which is a description of the system, not a filter. One handoff: the confirmed+ready overlap dilution (−0.053R, n=52, flagged independently in P6) is the one MAYBE thread, for P13.

## Files

- `run_setup_age.py` — study script (`pine_backtest` imported unmodified; only adds measurement columns)
- `setup_age_results.json` — age curves, composition, persistence tables
- `README.md` — this file

Guardrails respected: research only. No frozen files touched.
