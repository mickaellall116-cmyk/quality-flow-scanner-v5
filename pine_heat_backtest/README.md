# Priority 12 — Portfolio heat study

**Question:** Do later trades added to an already-loaded portfolio have worse expectancy?

**Verdict: NO** — the hypothesis is rejected. High-heat entries are not worse;
if anything they were better in good years, and heat is a regime proxy, not an
independent effect. No heat-based admission rule is justified.

## Setup

- 14-stock watchlist, 4H bars, Oct 2023–Sep 2026
- Canonical `pine_buy_signal` + `gen_pine_trades` (`pine_backtest` imported
  unmodified), frozen Mode B exits, 25bps costs
- Portfolio sim: line-for-line copy of `pine_backtest.simulate_portfolio` plus
  heat hooks. Heat at entry = sum(risk_dollars of open positions) / marked
  equity × 100, recorded BEFORE the new position is added.
- Baseline rerun in-study: 237 generated → 180 taken, 56.28% total return,
  21.63% max DD (matches known baseline exactly).

## Results — expectancy by heat at entry (25bps, taken trades)

| Heat at entry | n | Exp (R) | Win% | PF | Avg portfolio MAE |
|---|---|---|---|---|---|
| <2% (0–1 open) | 67 | +0.149 | 46.3 | 1.25 | −1.31% |
| 2–3% (2 open) | 47 | +0.425 | 57.4 | 1.66 | −2.62% |
| 3–4% (3 open) | 66 | +0.288 | 50.0 | 1.43 | −2.98% |
| 4–5% / 5% cap | 0 | — | — | — | — |

(The 4–5% and cap buckets are empty by construction: admission caps heat at
5%, so heat at entry tops out just under 4%.)

## Persistence — year × heat expectancy

| Year | <2% | 2–3% | 3–4% |
|---|---|---|---|
| 2024 | +0.153 (n=23) | +0.220 (n=13) | **+0.801** (n=23) |
| 2025 | −0.114 (n=20) | **+0.851** (n=21) | +0.494 (n=27) |
| 2026 | +0.365 (n=24) | −0.057 (n=13) | −0.798 (n=16) |

## Interpretation

1. **Hypothesis rejected.** Trades added to a loaded portfolio do NOT perform
   worse. In 2024 and 2025 the higher-heat buckets were clearly better.
2. **Heat is a regime proxy.** High heat means many signals fired at once,
   which happens in trending bull markets (P4: bull regime = most trades).
   In 2026 — the underwater year — the pattern flips: clustered signals meant
   correlated losers. Heat doesn't cause the outcome; the market regime does.
3. **A naive heat-based admission rule would have hurt.** Blocking high-heat
   entries would have skipped the best buckets of 2024–2025 and only helped
   in the one bad year — the classic overfit trap.
4. Portfolio MAE deepens with heat (−1.31% → −2.98%), but that's mechanical:
   more positions open = more simultaneous drawdown, not worse trade quality.

## Files

- `run_heat.py` — study script (`pine_backtest` imported unmodified)
- `heat_results.json` — bucket stats, year cross-tab, heat histogram
- `README.md` — this file

Research only. No frozen files touched (V5.4, Mode B, alerts, grades, exits,
market gate, AI Observer).
