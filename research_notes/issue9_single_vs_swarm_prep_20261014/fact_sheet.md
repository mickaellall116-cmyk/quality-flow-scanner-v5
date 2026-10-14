# FACT SHEET — Issue #9 comparison input (identical for both arms, all seeds)

Frozen at prep 2026-10-14. This sheet is the ONLY factual input either arm may use.
Anything not stated here is UNKNOWN to the arms. Both arms receive this file verbatim.

## The system under study
- Quality Flow: a 4H US-equities signal system (scanner + TradingView indicator share one logic).
- Primary timeframe: 4H bars anchored to the 09:30 America/New_York session open; 1H and 1D
  contexts exist. Every proposal must name its timeframe and decision time explicitly.
- Standing verdict: the frozen V5.4 strategy FAILED its promotion review (2026-10-03);
  entries are paused. Its corrected-grid replay produced −15.23R at zero cost; that adverse
  evidence is preserved and must not be tuned away. No proposal may assume V5.4 has an edge.
- Universes: UX51 (51 frozen symbols) and a frozen 199-symbol cohort; SPY is the benchmark.
  Indices/ETFs and large-cap equities; no options, no futures, no crypto in this study.

## Data that exists today (design may target ONLY this as "available")
- Yahoo OHLCV: 1H bars (4H is resampled from 1H with the 09:30 ET anchor), 1D, 1W.
  Practical history used in prior preregistered work: ~180 days of 1H, ~2 years of 1D, ~5 years of 1W.
- The Yahoo feed is currently DEGRADED (hourly refreshes exhaust their time budget before
  covering all 250 symbols); a repair candidate exists but is not yet adopted. Proposals must
  remain feasible on the history depths above, not on assumed real-time completeness.
- Twelve Data: a qualification effort is in progress (1H pilot receipts exist for a small
  symbol set; a 51-request V2 acquisition manifest is preregistered). It is NOT yet a
  qualified feed. Designs that need it must be marked DATA_BLOCKED (future), not available.

## Data that does NOT exist (designs needing it are DATA_BLOCKED, not failed)
- Point-in-time earnings announcement timestamps (a dedicated study of this is on HOLD;
  no qualified free source exists). Reported-EPS values are not point-in-time safe here.
- Intraday options flow, level-2 / order-book data, tick data, short interest (PIT),
  analyst revisions, fundamentals as originally reported (as-seen snapshots).
- A retained Tiingo dataset exists but its disposition is on HOLD; it is not usable input.

## Standing research rules (proposals are screened against these)
- Every hypothesis must survive a point-in-time (PIT) access audit: each input must have
  been knowable at the stated decision time. Same-bar-close decisions on the signal bar
  are leakage unless the fill model is explicitly next-bar.
- Costs: prior preregistered work used 4 bps baseline and a 25 bps stress bar.
  Proposals must state execution and cost assumptions, with unambiguous timestamps.
- Goalposts never move after outcomes are seen. Verified losses are evidence.
- Multiple-testing discipline applies to any downstream test; this study generates
  candidate specifications only — it runs no backtest and makes no return claims.

## Already-decided families (proposing these again = duplication, screened out)
- The killed-family registry export accompanies this sheet
  (`killed_family_registry_export.json`): composite ranking filters (TOP-50 etc.),
  laggard veto, MA-variant probes (DEMA/TEMA/ALMA/VIDYA/FRAMA), short-side daily systems,
  path-signature features, CRT sweep-and-return, ML price forecasting as a claim,
  plain trend/momentum reparameterization; ORB and VCP-selection claims beyond their
  existing HOLD records.
- Also standing, per the research record: BOSWaves long-only daily is a provisional FAIL
  held for a November re-run (not a new idea); SA-VWAP long-only daily was weak/secondary.
- Already in the live idea backlog (presenting these as new = duplication): overnight vs
  intraday return decomposition; MAX-effect exclusion (daily); high-volume return premium.

## Forbidden inputs
- Holdout data of any kind (sealed), strategy or portfolio returns, forward-test outcomes
  beyond the standing verdicts stated above, and any outcome/performance figure for the
  seed topics. Seeds were chosen without consulting outcome data; keep it that way.
