# P11 — Cross-sectional breadth (2026-09-24)

**Question (pre-registered):** when many stocks signal simultaneously, is that
confirmation of a healthy market, or evidence of an overcrowded/late move?

## Method (declared before looking at results)

- Baseline: canonical 4H Hybrid trades, 14-stock watchlist, 4H bars,
  Oct 2023–Sep 2026, frozen Mode B exits, 25bps costs. `pine_backtest`
  imported unmodified. Measurement study — no filter built or proposed.
- For each of the 237 baseline trades, count how many **valid raw signals**
  (`pine_buy_signal == True`) fired on the same 4H bar across all 14 names.
  Raw signals are counted independently of whether that symbol already held
  an open position — breadth is about setups firing, not fills. All 237
  trades matched a raw-signal bar (0 misses).
- Buckets (mandate's, pre-declared): 1–2, 3–5, 6–10, 10+ simultaneous signals.
- Per bucket: n, expectancy @25bps, win rate, PF. Persistence: crowded (≥6)
  vs uncrowded by year.

## Results

Baseline sanity: 237 trades, +0.239R, 50.6% win, PF 1.38 — matches exactly.

Signal-count histogram (528 bars with ≥1 signal over ~3 years):
1:223, 2:120, 3:81, 4:52, 5:34, 6:12, 7:5, 9:1. Max observed = 9 —
the **10+ bucket is empty** on this universe/period.

| Bucket | n | Expectancy | Win rate | PF |
|---|---:|---:|---:|---:|
| 1–2 signals | 106 | +0.246R | 50.9% | 1.41 |
| 3–5 signals | 113 | +0.209R | 51.3% | 1.33 |
| 6–10 signals | 18 | +0.379R | 44.4% | 1.55 |
| 10+ signals | 0 | — | — | — |

Exact-count detail: 1:+0.257 (n=59), 2:+0.233 (n=47), 3:+0.141 (n=48),
4:+0.181 (n=28), 5:+0.319 (n=37), 6:+0.186 (n=14), 7:+1.054 (n=4).
No monotonic pattern; the count-7 reading is 4 trades.

### Persistence: crowded (≥6) vs uncrowded, by year

| Year | Crowded n | Crowded exp | Uncrowded n | Uncrowded exp |
|---|---:|---:|---:|---:|
| 2024 | 0 | — | 75 | +0.347R |
| 2025 | 15 | +0.738R | 87 | +0.391R |
| 2026 | 3 | −1.415R | 57 | −0.181R |

All crowded bars in the sample occurred in 2025–2026.

## Verdict: NO

Crowded signal bars do **not** produce worse trades. If anything the
direction leans toward confirmation (2025 crowded +0.738R vs +0.391R
uncrowded), but n=18 total crowded trades is too thin to claim a positive
effect either — and 2026's n=3 crowded sample is meaningless. The 1–2 vs 3–5
gap (+0.246R vs +0.209R) is noise-sized.

Implications:
- No "skip crowded bars" filter is justified.
- Crowded bars are when portfolio slots are scarcest — this mildly supports
  the P2 ranking direction (rank better when slots bind) rather than
  skipping. Consistent with P2's finding that ranking matters at contested
  timestamps.

## Files

- `run_breadth.py` — study script (`pine_backtest` imported unmodified)
- `breadth_results.json` — buckets, exact-count detail, year cross-tab,
  signal-count histogram
- `README.md` — this file

Guardrails respected: research only. V5.4, Mode B, production alerts,
grades, exits, market gate, AI Observer untouched.
