# Priority 6 — Entry extension / chasing (2026-09-24)

## Hypothesis
Entries get worse when price is already extended — a measurable chase penalty,
because the move has already consumed its short-term momentum.

## Mechanism
Late entries buy exhaustion: price far above its EMAs or the breakout level
has less remaining thrust before mean-reversion or a pullback, so the same
setup taken "late" should underperform the same setup taken "early".

## Method (pre-registered)
Measurement study only — no filter built or proposed. 237 canonical 4H Hybrid
trades, 14-stock watchlist, 4H bars, Oct 2023–Sep 2026, frozen Mode B exits,
25bps costs. Engine (`pine_backtest`) imported unmodified.

Extension metrics at the SIGNAL bar (point-in-time), in ATR units:
- `d9` = (close − e9)/atr, `d21` = (close − e21)/atr → quartiles
- `dbrk` = (close − max(high of prior 10 bars))/atr → quartiles
- `gap` = (entry-bar open − signal close)/atr → down/flat/up-small/up-large
- `greens` = consecutive close>open bars into the signal → 0–1 / 2–3 / 4+

## Baseline
237 trades, +0.239R/trade, 50.6% win, PF 1.38 @25bps.

## Results

### Distance from 9 EMA (ATR) — no pattern
| bucket | n | exp R | win% | PF |
|---|---|---|---|---|
| Q1 (≤0.29) | 60 | +0.324 | 50.0 | 1.58 |
| Q2 | 59 | −0.021 | 44.1 | 0.97 |
| Q3 | 59 | +0.393 | 59.3 | 1.76 |
| Q4 (≥1.09) | 59 | +0.258 | 49.2 | 1.40 |
Non-monotonic; Q2 weak but Q3/Q4 fine. Noise, not a penalty.

### Distance from 20 EMA (ATR) — flat, most-extended best
| bucket | n | exp R | win% | PF |
|---|---|---|---|---|
| Q1 (≤0.53) | 60 | +0.105 | 46.7 | 1.18 |
| Q2 | 59 | +0.306 | 52.5 | 1.57 |
| Q3 | 59 | +0.249 | 52.5 | 1.34 |
| Q4 (≥1.76) | 59 | **+0.297** | 50.8 | 1.45 |
The most-extended quartile is the *best*. Dropping it would have lowered
expectancy to +0.219R. A chase filter here would hurt, not help.

### Distance above breakout level (ATR) — gradient, but confounded
| bucket | n | exp R | win% | PF |
|---|---|---|---|---|
| Q1 (≤−1.95, deep below 10-bar high) | 60 | +0.434 | 51.7 | 1.88 |
| Q2 | 59 | +0.157 | 50.8 | 1.23 |
| Q3 | 59 | +0.269 | 50.8 | 1.38 |
| Q4 (≥−0.41, at/above breakout) | 59 | +0.092 | 49.2 | 1.15 |

This looks like a chase penalty — until you check composition. Q4 contains
ALL pure breakout signals; Q1–Q3 are confirmed/ready mixes. It is a
**signal-type composition effect**, not the same setup taken late vs early:
entries far below the 10-bar high are confirmed/ready (pullback-style) entries,
which outperform as a group. Within-type extension (d9, d21) shows no penalty.
Directionally Q1 > Q4 in all three years (2024: 0.476 vs 0.275; 2025: 0.592
vs 0.260; 2026: 0.113 vs −0.465), so the gradient is persistent — but it
describes *which signal fired*, not *how chased the entry was*.

Signal-type split (context): confirmed n=146 +0.286R; ready n=19 +0.463R;
confirmed+ready overlap n=52 **−0.053R**; pure breakout n=9 +0.716R (thin).

### Entry-bar gap — thin buckets, ignore
| bucket | n | exp R |
|---|---|---|
| gap-down (<−0.2) | 4 | −1.283 |
| flat | 222 | +0.233 |
| gap-up small | 4 | +1.921 |
| gap-up large (>0.6) | 7 | +0.321 |
n=4/4/7 — no conclusions possible. Flat bucket = the baseline.

### Consecutive green bars — moderate momentum helps, no penalty
| bucket | n | exp R | win% | PF |
|---|---|---|---|---|
| 0–1 | 150 | +0.183 | 46.7 | 1.28 |
| 2–3 | 72 | **+0.367** | 58.3 | 1.66 |
| 4+ | 15 | +0.177 | 53.3 | 1.30 |
2–3 greens is the best bucket; 4+ falls back but n=15 is thin. If anything,
*some* momentum helps — the opposite of a chase penalty.

### Persistence check (d21 Q4 vs rest, by year)
2024: ext +0.359 vs rest +0.343 (same). 2025: ext +0.276 vs rest +0.496
(ext worse). 2026: ext +0.246 vs rest −0.391 (ext better). Mixed — no
persistent penalty.

## Why it failed
There is no measurable chase penalty *within* a signal type. The only
extension-like gradient (distance above the breakout level) is explained by
signal-type composition: pullback-style confirmed/ready entries outperform
breakout-level entries as groups. The cleanest extension metrics (distance
from the 9/20 EMA) are flat or favor the extended side.

## Verdict: FAIL (hypothesis rejected)
No chase penalty found. A "don't chase extended entries" filter is **not
justified** — on the d21 metric it would have reduced expectancy. The dbrk
gradient is real but is a statement about signal types, not entry timing.

## Recommended next experiment
The confirmed+ready overlap bucket (n=52, −0.053R, PF 0.92) underperforms
both pure confirmed (+0.286R) and pure ready (+0.463R). That belongs to P13
(signal sequencing): do overlapping/repeated signal conditions dilute the
edge? Test first-vs-repeat and signal-overlap splits.

## Files
- `run_chase.py` — study script (`pine_backtest` imported unmodified)
- `chase_results.json` — bucket tables, quartile edges, persistence, implied-filter effect
- `README.md` — this file

Guardrails respected: research only. No frozen files touched.
