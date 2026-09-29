# P13 — Signal sequencing (2026-09-24)

## Hypothesis
Repeated signals in the same move have diminishing edge; overlapping signal
conditions (confirmed+ready firing on the same bar) dilute the edge.

## Mechanism
Two independent studies (P6 chase, P7 setup age) flagged the confirmed+ready
overlap bucket at −0.053R (n=52) vs pure confirmed +0.286R / pure ready
+0.463R. Candidate mechanism (speculative): when the pullback-recovery
(ready) coincides with a maxed trend score (confirmed), the recovery bar is
already extended — the "buy the dip" component has less room. Stated plainly:
the mechanism is thin.

**Skepticism note:** the "two sightings" collapse to one dataset — P6, P7 and
this study count the same 52 trades three times. This is not three
replications. The year cross-tab below is the only genuinely new evidence.

## Setup
14-stock watchlist, 4H, Oct 2023–Sep 2026, canonical 4H Hybrid, frozen Mode B
exits, 25bps. `pine_backtest` imported unmodified. Baseline sanity: 237
trades, +0.2388R (matches benchmark).

## 1. Signal composition (25bps)

| bucket | n | exp R | win% | PF |
|---|---:|---:|---:|---:|
| pure_confirmed | 146 | +0.286 | 51.4 | 1.44 |
| confirmed+ready | 52 | **−0.053** | 46.2 | 0.92 |
| pure_ready | 19 | +0.463 | 47.4 | 1.89 |
| pure_breakout | 9 | +0.716 | 66.7 | 3.74 (thin — ignore) |
| breakout+confirmed | 10 | +0.318 | 60.0 | 1.59 (thin) |
| breakout+ready | 1 | −0.822 | — | — (ignore) |

Year cross-tab, overlap vs pure_confirmed:

| year | overlap n/exp | pure_conf n/exp | relative diff |
|---|---|---|---|
| 2024 | 15 / +0.272 | 47 / +0.445 | −0.17 |
| 2025 | 25 / +0.154 | 57 / +0.424 | −0.27 |
| 2026 | 12 / −0.892 | 42 / −0.079 | −0.81 |

**Reading:** the pooled −0.053R is driven by 2026 (−0.89 on n=12); overlap was
*positive* in 2024 and 2025. A skip filter would have blocked
positive-expectancy trades in 2 of 3 years. However, overlap underperforms
pure_confirmed in ALL three years, relatively.

Within-symbol (overlap vs pure_confirmed): underperforms in 8 of 12 symbols
(AMD −2.23, ONDS −2.08, PLTR −1.08, HOOD −0.93, NIO −0.53, ANET −0.29,
RKLB −0.15, SMCI −0.02); outperforms in 4 (BBAI +1.06, ASTX +0.95 on n=1,
SOFI +0.89, QQQ +0.31). Directionally persistent, magnitudes noisy.

## 2. Sequencing (prior signal bars in same symbol, trailing 20 bars)

| bucket | n | exp R | win% | PF |
|---|---:|---:|---:|---:|
| first | 103 | +0.159 | 47.6 | 1.24 |
| second | 23 | +0.521 | 56.5 | 2.10 |
| 3rd+ | 111 | +0.254 | 52.3 | 1.41 |

Year cross-tab flips for "second" (2024 +1.52 n=11, 2025 −0.00 n=8,
2026 −1.18 n=4) — not persistent. **No diminishing edge on repeats.**
Consistent with P7's hump: first signals are the weakest, not the best.

## 3. Re-entry (signal within 10 bars after a prior exit, same symbol)

| bucket | n | exp R | win% | PF |
|---|---:|---:|---:|---:|
| fresh | 130 | +0.204 | 48.5 | 1.32 |
| after_stop | 95 | +0.258 | 54.7 | 1.42 |
| after_tp1 | 0 | — | — | — |
| after_other_exit | 12 | +0.465 | 41.7 | 1.71 |

**No re-entry penalty.** Re-entering after a stop does fine (+0.258 vs +0.204
fresh, similar in 2024/2025). after_tp1 is n=0 — mechanically impossible while
the runner rides. The folk wisdom "never re-enter after a stop" is not
supported.

## The overfit trap, shown explicitly
Dropping all 52 overlap trades in-sample: remaining 185 trades @ +0.321R vs
baseline +0.239R. Tempting — and exactly the trap the mandate forbids: the
year split shows overlap was positive in 2024/2025, the mechanism is
speculative, and this is one dataset viewed three times. Adopting a skip
filter would be optimization, not research.

## Verdict
- **Signal sequencing: NO** — no diminishing edge on repeats; first signals
  weakest.
- **Re-entry: NO** — no penalty after stops.
- **Overlap relative-underperformance: MAYBE (weak)** — persistent in relative
  terms (all 3 years, 8/12 symbols, n=52, broad symbol mix) but the absolute
  negativity is a 2026 artifact, the mechanism is thin, and the "three
  sightings" are one dataset. Candidate input for future P2 ranking work
  (down-rank, never skip). Needs forward validation.

## Recommended next experiment
P2 follow-up: add overlap as a down-rank (not skip) input in the ranking
study and see if it survives. Separately, the dead-markets thread from P5
(pre-registered follow-up) is still queued.

## Files
- `run_sequencing.py` — study script (`pine_backtest` unmodified)
- `sequencing_results.json` — composition, sequencing, re-entry, yearly
  cross-tabs, within-symbol table, trap number
- `README.md` — this file

Guardrails: research only. V5.4, Mode B, production alerts, grades, exits,
market gate, AI Observer untouched.
