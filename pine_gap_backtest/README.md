# P9 — Gap behavior (2026-09-24)

## Question (pre-registered)
Do large gaps create continuation (momentum) or chase risk (reversal) for
Quality Flow entries?

## Method
- Baseline: canonical 4H Hybrid, 14-stock watchlist, 4H bars, Oct 2023–Sep 2026,
  frozen Mode B exits, 25bps costs. `pine_backtest` imported unmodified.
- Gap measured at the ENTRY bar (i+1), since entries fill at next-bar open:
  gap = (Open[i+1] − Close[i]) / atr[i], in ATR units.
- Premarket gap is NOT separately measurable on 4H bars — the inter-bar gap
  IS the overnight/weekend gap.
- Baseline sanity: 237 trades, +0.2388R, 50.6% win — matches published baseline.

## Results (25bps)

### Gap-up size (pre-declared)
| bucket | n | exp R | win% | PF |
|---|---|---|---|---|
| no/neg gap | 223 | +0.216 | 49.8 | 1.33 |
| gap-up small (0.15–0.5 ATR) | 7 | +0.889 | 57.1 | 5.26 |
| gap-up large (≥0.5 ATR) | 7 | +0.321 | 71.4 | 2.01 |

Tempting, but n=7 per bucket. The persistence check kills it (below).

### Gap-down size (pre-declared)
| bucket | n | exp R | win% | PF |
|---|---|---|---|---|
| no/pos gap | 232 | +0.274 | 51.3 | 1.45 |
| gap-down small (−0.5..−0.15) | 2 | −0.609 | 50.0 | 0.32 |
| gap-down large (≤−0.5) | 3 | −1.904 | 0.0 | 0.00 |

Directionally consistent (all 5 gap-down entries negative — buying into
weakness on a long-only system), but n=5 cannot support a filter.
Watch-only, not evidence.

### Absolute gap quartiles
| bucket | n | exp R | win% | PF |
|---|---|---|---|---|
| Q1 (least) | 60 | +0.309 | 51.7 | 1.54 |
| Q2 | 59 | −0.073 | 39.0 | 0.91 |
| Q3 | 59 | +0.576 | 61.0 | 2.03 |
| Q4 (most) | 59 | +0.142 | 50.8 | 1.25 |

No pattern — Q3 best, Q2 worst, Q4 middling. Noise.

### Gap hold vs fade (pre-declared, |gap|≥0.15 only)
| bucket | n | exp R | win% | PF |
|---|---|---|---|---|
| no gap | 218 | +0.253 | 50.5 | 1.40 |
| gap-up held | 7 | +0.205 | 57.1 | 1.60 |
| gap-up faded | 7 | +1.004 | 71.4 | 6.50 |
| gap-down held | 2 | −2.202 | 0.0 | 0.00 |
| gap-down faded | 3 | −0.842 | 33.3 | 0.19 |

Same thin-bucket problem: the "gap-up faded" winners are essentially the
same 7 trades as "gap-up small". Cannot separate hold/fade from size.

### Opening location within prior 10-bar range (quartiles)
| bucket | n | exp R | win% | PF |
|---|---|---|---|---|
| Q1 (at the lows) | 60 | +0.102 | 46.7 | 1.16 |
| Q2 | 59 | +0.384 | 54.2 | 1.65 |
| Q3 | 59 | +0.178 | 52.5 | 1.26 |
| Q4 (at the highs) | 59 | +0.293 | 49.2 | 1.49 |

Flat. No gradient — where the entry bar opens inside the recent range
does not matter.

### Persistence: |gap|≥0.5 ATR vs rest, by year
| year | big-gap n | big-gap exp | rest n | rest exp |
|---|---|---|---|---|
| 2024 | 3 | −0.275R | 72 | +0.373R |
| 2025 | 5 | −0.250R | 97 | +0.478R |
| 2026 | 2 | −0.698R | 58 | −0.227R |

Big-gap trades are negative in ALL three years while the rest are positive
in 2024/2025. This undermines the headline "gap-up large +0.32R" — that
bucket (n=7) is a thin-bucket artifact sitting inside a consistently
negative big-gap population (n=10, dragged by the gap-downs).

## Verdict: NO

No broad gap bucket is clearly better or worse across years. The only
directional signals live in thin buckets (n=2–10): gap-down entries are
uniformly negative (n=5, watch-only), and big-gap trades are negative in
every year (n=10, confounded by gap-downs). Nothing here justifies a
filter. This joins the tested-and-parked list.

## Files
- `run_gap.py` — study script (`pine_backtest` imported unmodified)
- `gap_results.json` — bucket tables, definitions, persistence cross-tab
- `README.md` — this file

Guardrails respected: research only. V5.4, Mode B, alerts, grades, exits,
market gate, AI Observer untouched.
