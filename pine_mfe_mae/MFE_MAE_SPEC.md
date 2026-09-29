# MFE/MAE Diagnostic Study — Pre-registered Spec

**Status:** SPEC FROZEN before any analysis. Diagnostic only.

## Nature of this study

DIAGNOSTIC ONLY. V3.6 entries and exits are completely unchanged. We replay the
exact baseline trades and measure, for every trade, Maximum Favorable Excursion
(MFE) and Maximum Adverse Excursion (MAE) in R from entry until the actual exit.

**No optimization. No exit variants. No parameter changes.** If the diagnostics
look good, exit research stays closed, period. If a leak is found, it is reported
WITHOUT proposing a fix — fixes would be a separate pre-registered study that
Mike has not authorized.

## Trade universe (must BE the baseline trades)

- Bull window: UX51, 4H, 2024-09-16 → 2026-09-14. Engine copied (not modified)
  from `pine_backtest.py`. Fidelity check required: 263 trades, +0.195R @4bps.
  All 263 generated trades are measured (same population the baseline stats use).
- Bear window: 2022 4H, same framework as the exit-fix/entry-ablation studies:
  `v6_short_v2/cache/d4h_2022_*.pkl` + `pine_exit_fix/cache_2022/d4h_2022_*.pkl`,
  symbols ∩ UX51, signals with signal_time ≥ 2022-01-01, indicators warmed on
  earlier bars (WARMUP=215), end-of-data liquidation at last close.

## Excursion measurement (documented approximations)

- MFE_R = max over bars j ∈ [entry_idx, exit_trigger_idx] of
  ((High_j − entry) / entry) / risk_frac
- MAE_R = min over the same bars of ((Low_j − entry) / entry) / risk_frac
- risk_frac = (entry − stop0) / entry, the trade's own 1R definition.
- Excursion uses 4H bar high/low, NOT intrabar ticks: true intrabar excursion
  may be slightly larger. This biases MFE down a touch and MAE up a touch;
  it does not change the verdict logic.
- The window ends at the exit TRIGGER bar (the bar whose close triggered the
  exit). The next-bar-open fill is execution, not excursion. EOD-liquidated
  2022 trades measure through the last bar.
- Realized R for giveback/capture is the GROSS blended R (50% TP1 limit if hit
  + 50% final exit, no costs), because costs are a constant drag unrelated to
  exit mechanics. Winner/loser splits use NET R > 0 to stay consistent with the
  baseline's reported 44.9% win rate.

## Questions (the five)

1. How far do winners typically run (MFE) before the existing exit takes them out?
2. How much profit do winners give back — MFE minus realized R?
3. How deeply do eventual winners first go against us — MAE of winners?
4. Do stopped trades commonly recover — what MFE did stopped-out trades reach?
5. How do MFE/MAE distributions differ between winners and losers?

## Required output

- Median, p25/p75, p10/p90 of MFE and MAE, split by: winner/loser,
  bull window vs 2022 bear window, and exit type:
  `stop_no_tp1` (reason=stop, TP1 never hit), `stop_after_tp1` (reason=stop,
  TP1 hit — the runner), `ema55` (ema55-break / ema55-bear), `eod` (2022 only).
- Stopped trades: fraction that reached +1R, +1.5R, +2R MFE before stopping.
- Winners: median MAE; % touching −0.5R and −0.75R intra-trade.
- Giveback = MFE − realized gross R, winners only: median + percentiles.
- Capture = realized gross R / MFE, winners only: median + percentiles.

## Decision rule (pre-registered)

Exit research STAYS CLOSED if all three hold:
(a) exits capture most available excursion (median capture ≥ 0.5, i.e. winners
    give back less than half of MFE at the median);
(b) stops are not routinely clipping eventual winners: < 25% of stopped trades
    reached +2R MFE before stopping;
(c) winners rarely suffered deep adversity: < 25% of winners touched −0.75R MAE.

A LEAK is flagged if any of these fail by a clear margin — e.g. median giveback
> 50% of median MFE, or a large share of stopped trades later reached +2R, or
a large share of winners endured −0.75R+ MAE. A flagged leak is REPORTED ONLY.
No fix is designed, tested, or proposed in this study.

Small-sample caveat: the 2022 window has far fewer trades; its role is a
robustness read on the same questions, not a second optimization surface.
