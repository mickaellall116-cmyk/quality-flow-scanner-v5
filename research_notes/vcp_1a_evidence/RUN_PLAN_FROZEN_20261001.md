# VCP Probe v0.1 — Phase 1A FROZEN RUN PLAN (operationalization, NOT a spec amendment)

Frozen: 2026-10-01, before any performance result is computed.
Spec: vcp_probe_v01_SPEC_FREEZE_20260930.md (sha256 c8f103c5...2bc) — unchanged.
ChatGPT TYPE: GO (2026-10-01T03:22:16Z) execution requirements apply.

## 1. Universe (PIT, with delisted/acquired/bankrupt names)

- Source: fja05680/sp500 `sp500_ticker_start_end.csv`
  (sha256 b2f4fe2f2e4dce8eaf0eb4fbd3946a32a20c1ddfe69687dfca3b6b59a0b71f9f,
  saved as phase1a/sp500_ticker_start_end.csv).
  Wikipedia-derived; MIT license. Single-source limitation documented.
- Membership interval [start_date, end_date] per ticker; ticker is in-universe
  at month-end m iff an interval covers m. 831 unique tickers overlap 2010-01-01–2025-12-31.
- DOCUMENTED LIMITATION: candidate pool is S&P 500 historical constituents
  (large-cap tilt). $2B–$8B midcaps never in the S&P 500 are not covered.
  Delisted/acquired/bankrupt members ARE included via Tiingo dead-ticker EOD.
- Ticker-reuse guard (frozen, operationalized 2026-10-01 after pilot caught an
  over-quarantine bug): per membership interval [start, end], with s0/s1 the
  fetched series' first/last bar — closed interval: require end−9d <= s1 <= end+9d;
  open-ended: require s1 >= 2026-09-21. Start side is clamped to the observable
  overlap (no quarantine; pre-2009 membership months are unobservable given the
  2009-01-01 pull floor). Rationale: wrong-company series are detected at the
  END (reused ticker serving the new company runs past the old end; serving the
  old company stops before now). Quarantined intervals are logged with reason,
  never silently filled.

## 2. PIT market-cap filter $2B–$100B (at each decision date) — MECHANICAL

SOURCE CHANGE 2026-10-01 (operationalization, spec requirement unchanged):
Tiingo free-tier fundamentals are DOW-30-only with 3 years of history
(proven by pilot: AAPL/MSFT return 13–14 statements; ATVI/GE/F/BAC/T/KMI/…
all HTTP 400; Tiingo docs: "3 Years of the DOW 30 tickers are available for
free/evaluation"). Tiingo cannot supply the universe-wide PIT mcap filter.
Source switched to SEC EDGAR XBRL companyconcept
dei:EntityCommonStockSharesOutstanding (free, no key, 2009+ quarterly,
PIT via filed dates).

- shares(m) = val from the latest quarterly frame with filed <= (month-end m − 45d)
  and frame-end <= month-end m (filing-lag guard; PIT-conservative).
  One EDGAR request per ticker (companyconcept JSON); ticker→CIK via SEC
  company_tickers.json + browse-edgar resolution for delisted names.
- mcap(m) = close_unadj(month-end m) × shares(m). Unadjusted close is REQUIRED:
  adjClose is on today's split basis while EDGAR shares are on the historical
  split basis (pilot: AAPL Dec 2019 adjClose $70.66 × 4.38B pre-split shares
  = $310B vs true $1.29T — 4x error from the 4:1 split).
- Keep ticker-month iff $2B <= mcap(m) <= $100B.
- Ticker-months with no EDGAR shares coverage are excluded and logged
  (documented limitation; mostly pre-2010 XBRL gaps).
- Validation: EDGAR shares cross-checked against Tiingo shareswa for
  AAPL/MSFT over the 3 overlapping years (expect small timing differences:
  shareswa = quarterly weighted average vs EDGAR = quarter-end point).

## 3. Price and observation dates

- Price source: Tiingo EOD. `adjClose` (split- AND dividend-adjusted) for MAs,
  trend conditions, forward returns, downside excursion (ratio-based; split
  continuity required). UNADJUSTED `close` for the $10 filter and the mcap
  computation (both must be on the actual traded-price basis; adjClose would
  misstate both after splits — e.g. AAPL adjClose 2011-01-31 = $10.15 vs
  actual $339.32).
- Price > $10 on unadjusted close at observation.
- Observation dates: last trading day of each month per SPY Tiingo calendar,
  Jan 2010 – Dec 2025 (192 months). If month-end bar missing, use last
  available bar within 5 trading days before month-end, else drop stock-month.

## 4. Trend variants (frozen)

- Variant 1: adjClose > 150DMA AND adjClose > 200DMA.
- Variant 2: Variant 1 AND adjClose > 250DMA.
  (250 trading days ≈ 12 months: operationalization of the source video's
  "price above 12-month moving average". Documented as judgment call.)
- MAs computed on adjClose over windows ending ON the observation date
  (inclusive). Minimum valid bars: 140 / 185 / 230 respectively; otherwise
  insufficient-data → excluded from qualifier AND control that month.

## 5. Forward returns (frozen corporate-action/delist handling)

- Windows: 63 / 126 / 252 trading days after observation (≈3/6/12M),
  total return on adjClose: ret = adjClose(t+w)/adjClose(t) − 1.
- Splits/dividends: handled by Tiingo adjClose (verified on a known split
  in pilot).
- COMPLETE WINDOWS ONLY: 3M and 6M use all 192 months; 12M uses
  Jan 2010 – Sep 2025 (data ends ~2026-09-29; Dec 2025 + 12M is unobservable).
- Delisting/acquisition/bankruptcy inside the window (frozen): forward return
  is computed to the LAST available close, then held flat (cash-out at last
  close assumption). Bankruptcy resolves toward zero naturally via last closes.
  Documented limitation: cannot distinguish cash vs stock deals PIT-simply.
- Missing observation close → drop stock-month, log.

## 6. Controls

- Primary control (per variant, per month): stocks passing universe + price +
  market-cap filters but FAILING that variant's trend condition.
- Secondary reference: SPY total return (adjClose) over identical windows.
- Minimum 5 qualifiers and 5 controls per month, else drop the month (log).

## 7. Reported statistics (frozen)

- Excess return: qualifier mean − control mean (primary); qualifier − SPY (secondary).
- Estimation: Fama–MacBeth — per month m, d_m = mean(qual fwd ret) − mean(ctrl fwd ret),
  equal-weighted within month; headline = mean(d_m).
- Inference (frozen): block bootstrap on {d_m}, block length 12 (covers 12M
  window overlap), 9,999 resamples, seed 42. Two-sided 5%: report mean,
  95% CI, bootstrap p. The p is computed against the bootstrap distribution
  RECENTERED at 0 (H0: mean=0); the raw bootstrap is centered at the observed
  mean, so a p computed against it is degenerate (always ~1). Bug fixed
  2026-10-01; CI was already correct. Effect size annualized (×12) also
  reported.
- Persistence (frozen): 8 non-overlapping 2Y subperiods
  (2010–11 … 2024–25); PASS needs mean(d)>0 in ≥5 of 8 AND full-sample
  mean(d)>0 AND bootstrap p<0.05. All three horizons reported; no cherry-picking.
- Hit rate: fraction of qualifier stock-months with fwd total return > 0
  (control hit rate alongside).
- Downside: mean/median max adverse excursion per qualifier stock-month
  (min over window of close/obsClose − 1); plus drawdown of the diagnostic
  equal-weight qualifier portfolio (not a strategy).
- Breadth: qualifier count per month (mean/min/max).
- Turnover: 1 − |Q_m ∩ Q_{m+1}| / |Q_m|, averaged.

## 8. Data budget and quarantine

- Tiingo free tier: 50 req/hr, 1000 req/day, 500 unique symbols/month, 1 GB/month.
  Shared with the hourly Tiingo observer → pace at ≤40 req/hr (90s spacing),
  ≤500 NEW symbols per calendar month (ledger-enforced), stop at 900MB.
- STOP (hard) on repeated 429/403 per policy; checkpoint everything; resume cleanly.
- Quarantine: never touch V5.4, forward test, ERD, scanner repo, or production files.
  All code/data under goals/vcp-fundamental-momentum-probe-v0-1/hidden_files/phase1a/.
- STOP after Phase 1A. No Phase 1B, no fundamentals beyond the market-cap filter.
