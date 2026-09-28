# HEMA Reconciliation After DST Fix — 2026-09-28

Research-only. Frozen/live Quality Flow remains unchanged.

## Verdict status
- 4H HEMA hard entry gate: **FAIL as a system change**.
- Small-green retest as an entry requirement: **FAIL**.
- HEMA as a slot-ranking input: **UNTESTED HYPOTHESIS**. Do not start ranking work until the reconciliation items below are closed.

## DST/session-bar correction
The first HEMA surrogate used a global pandas 4H resample across a DST boundary. Winter labels shifted to 08:30/12:30 ET. The research resampler was replaced with explicit per-session New York wall-time buckets:
- 09:30–13:30 ET
- 13:30–16:00 ET

The corrected trade log has entry labels only at 09:30 or 13:30 ET.

### Session edge cases
Synthetic session checks show:
- normal day: one 09:30 bucket with the 09:30/10:30/11:30/12:30 hourly bars and one 13:30 bucket with 13:30/14:30/15:30, ending at 16:00;
- historical half-day: one 09:30 bucket only; no phantom 13:30 bucket;
- holiday: no input bars, therefore no output bar.

One caveat remains for **same-day/live half-days**: the shared `bar_close_at` helper assumes the 09:30 bar closes at 13:30, whereas an NYSE early-close session ends at 13:00. This does not affect historical half-days in this backtest, but must be calendar-aware before this resampler is used for live/forward early-close execution.

## Why the baseline moved so much
Old baseline: 209 trades, +0.5210 gross R/trade.
DST-corrected baseline: 205 trades, +0.7939 gross R/trade, +0.5510 net R/trade at 50 bps.

Trade-by-trade reconciliation:
- 164 trades match on symbol + entry date;
- 45 old-only trades;
- 41 new-only trades;
- among the 164 matched trades, median R change = 0.0R and the summed R change is only +11.09R.

The biggest reason the corrected headline jumped is one newly admitted APLD trade:
- APLD entry 2024-01-03 09:30 ET;
- +57.94 gross R / +54.38 net R;
- 35.6% of the corrected baseline's total gross R;
- about 44.4% of recorded realized P&L.

Removing only that APLD outlier reduces the corrected baseline to approximately:
- +0.514 gross R/trade;
- +0.287 net R/trade.

Therefore the +153.8% corrected portfolio-return headline must not be treated as a stable baseline statistic until that trade's entry/stop geometry is audited.

## Corrected 50-bps comparison
- QF baseline: n=205, +0.551 net R/trade, net PF 1.72, +153.8% marked return.
- QF + 4H HEMA bull: n=73, +0.759 net R/trade, net PF 2.20, +67.2% marked return.
- QF + EMA20/40 bull: n=204, +0.519 net R/trade, net PF 1.68, +140.3% marked return.
- QF + SPY bull regime: n=196, +0.485 net R/trade, net PF 1.63, +116.0% marked return.

The HEMA gate improves per-trade quality in this surrogate but removes roughly 64% of trades, does not have a statistically secure advantage over the baseline after the correction, and was weaker than the baseline in 2026.

## Next step before ranking
Audit the APLD +57.94R trade by logging entry, stop, TP1, risk/share, shares and planned risk. Only after that reconciliation should the pre-registered HEMA slot-ranking test begin.
