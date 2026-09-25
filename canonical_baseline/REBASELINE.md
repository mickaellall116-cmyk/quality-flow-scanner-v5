# Canonical Re-Baseline — frozen V5.4 Mode B under honest conditions

_2026-09-24/25. Research only; nothing frozen was modified. All artifacts under `canonical_baseline/`._

## What was built

One canonical research backtest of the exact frozen V5.4 system currently being forward-tested:

- **Universe:** top-120 by trailing-63-day dollar volume as of 2023-09-30 + gated new listings = 131 symbols (`UNIVERSE.md`, `universe.json`). Mike's 14 kept as reporting overlay only. The four names that carried 102% of the old baseline's P&L rank #189–#227 on the 2023-09-30 ranking — the old universe is confirmed hand-picked.
- **Exits:** fresh Mode B engine, 31/31 unit tests passing, 122/122 decision-packet matches against the live forward-test tracker (`ENGINE.md`, `modeb_engine.py`). Live-faithful gap handling primary (stop filled AT the stop on gap-through — optimistic, quantified separately at −0.038R).
- **Features:** strict point-in-time contract, 11 rules (`PIT_FEATURES.md`). One genuine leak found and fixed: sector-RS studies used the signal-day daily close.
- **Portfolio:** $75k book, 1% risk, max 6 open, 5% heat cap, slot competition with production rs_top2 ranking, busy-symbol rule — all matching live.
- **Costs:** round-trip, leg-based, at 25/50/75/100bps.

## A. Honest V5.4 baseline (V5 @ 50bps round-trip — the headline)

| Metric | Value |
|---|---|
| Expectancy | **−0.0013R / trade** |
| Win rate | 39.8% |
| Profit factor | 1.00 |
| Max drawdown | −39.8% (−$30,504 / −40.7R) |
| Trades | 374 (effective n = 7 overlap episodes) |
| Annualized / total return | −0.4% / −0.9% |
| Median trade | −1.08R |
| Average winner / loser | +1.76R / −1.17R |
| Max losing streak | 11 |
| Avg MFE / MAE | +2.12R / −1.15R |
| Cost sensitivity | +0.103R @25bps → −0.001R @50bps → −0.106R @75bps → −0.210R @100bps |
| Concentration | Top 10 trades = +58.5R vs total −0.5R; ex-top-10 = −0.162R; best year 2026, ex-2026 = −0.089R |
| Years | 2024 −0.254R / 2025 +0.061R / 2026 +0.166R |
| Signal funnel | 4127 candidates → 622 busy-skipped → 744 slot-skipped → 2387 heat-skipped → 374 taken |

The 14-name watchlist under identical machinery: **+0.449R @50bps** (n=151, PF 1.77) — the watchlist is a selected universe, not evidence for the system.

## B. Exact difference vs the old +0.239R estimate

**−0.240R.** The old +0.2388R (V0 reproduction: +0.2704R, n=236) does not survive honest conditions. The corrected baseline is indistinguishable from zero.

## C. Why the difference occurred (ablation decomposition, R/trade)

| Step | Delta | Meaning |
|---|---|---|
| V0→V1 universe (14 hindsight names → 131 PIT names) | **−0.351R** | Dominant effect. The old edge does not exist outside the hand-picked universe |
| V1→V2 Mode B exits (old exits → live Mode B stack) | +0.054R | Real exit stack helps slightly |
| V2→V3 v54 entries + strict PIT | +0.041R | Bundles the V3.6→v54 entry-definition change; not a pure PIT effect |
| Gap realism (live-faithful vs realistic fills) | −0.038R | Live fills gap-through-stop at the stop price — optimistic |
| V3→V4 costs (25bps once → 50bps round-trip leg-based) | −0.131R | Real friction on tight-stop trades (notionals up to 2.6× equity, no notional cap specified) |
| V4→V5 portfolio (1645 independent → 374 with slots/heat/ranking) | +0.116R | Slot/heat/rs_top2 competition selects better trades |

## D. Corrected lone-wolf result (strict PIT, frozen rule, candidate-stage block)

**The overlay hurts the corrected baseline. Do not adopt it.**

| Metric @50bps | Canonical V5 | V5 + lone-wolf | Delta |
|---|---|---|---|
| Expectancy | −0.0013R | −0.1746R | **−0.173R/trade** |
| Max drawdown | −39.8% | −63.8% | −24.0pp |
| Total return | −0.9% | −47.8% | −46.9pp |

1109/4127 candidates blocked (26.9%). The 114 blocked trades that made the baseline book were mildly negative dead money (−0.019R) — removing them alone would have helped. But candidate-stage filtering reshuffles slot/heat competition: only 142/374 baseline trades survive, and 132 newly admitted replacements lost −0.389R on average. The damage holds at every cost level, is broad-based across symbols/years (worst in 2025), and survives top-contributor removal. This overturns the earlier PASS — which was measured on the inflated baseline, with a leaky RS endpoint, and without portfolio competition. Full detail: `LONEWOLF_RERUN.md`.

## E. Confidence: HIGH

HIGH that the honest historical expectancy of the frozen system is ~zero and not +0.24R: PIT universe by mechanical rule, engine proven against live decisions (122/122), strict PIT contract, round-trip costs, full portfolio replay, replicated end-to-end. Caveats (none change the verdict): 4H data starts 2023-10-26 (yfinance 1H 730-day limit); CYBR's delisted history unrecoverable without a survivorship-inclusive vendor; lone-wolf sector labels are current-pull GICS (no mid-window structural GICS change, result broad-based); effective n = 7 chained episodes means the point estimate is noisy — the honest statement is "indistinguishable from zero," not "precisely −0.0013R."

## F. Should the live forward test continue? Yes — with reset expectations

- **Continue paper to the pre-committed ~50-signal checkpoint.** It costs nothing, it is the only uncontaminated measurement of the actual frozen system, and 19 signals is no sample at all.
- **Reset the bar:** the checkpoint must be judged against ~0R, not +0.239R. Every gate calibrated to the old number is miscalibrated.
- **No real-money go-live** on the baseline alone — forward data must show a positive edge over a meaningful sample first.
- **Remove lone-wolf from the checkpoint candidate list.** The corrected rerun says the overlay destroys value under portfolio competition. (The live overlay is logging-only, so nothing to unwind in production.)
- **Recommended production fix for Mike's approval:** the live gap-through-stop fill credits the stop price on gap-through bars (optimistic ~+0.04R on expectancy, +0.41–0.46R per event). Filling at the open beyond the stop matches reality. This is a production change — his call, not made here.

## Files

- `REBASELINE.md` (this file) · `UNIVERSE.md` + `universe.json` · `ENGINE.md` + `modeb_engine.py` + `tests/test_modeb.py` + `compare_live.py` · `PIT_FEATURES.md` · `PORTFOLIO.md` + `portfolio_results.json` + `canonical_trades.json` · `LONEWOLF_RERUN.md` + `lonewolf_rerun.json` + `lonewolf_trades.json` · scripts: `simlib.py`, `run_ablation.py`, `run_portfolio.py`, `analyze.py`, `lonewolf_rerun.py`, `scripts/`
