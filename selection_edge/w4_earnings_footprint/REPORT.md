# Selection-Edge Worker W4 — F7 (earnings/revisions momentum) + F8 (institutional-footprint proxy)

## Status

- **F7: TESTABLE via post-earnings drift** — data audit complete (see "F7 data audit" below).
  The EPS-revision candidate is UNTESTABLE (no timestamped revision history exists in any
  available source — evidence below). Exact construction pre-registered below BEFORE any
  F7 results were computed.
- **F8: pre-registered construction** (disambiguations frozen before computing results).

## Blinding

The 14 masked names (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM, SPCX, ASTX, BBAI,
NIO, HOOD, AMD) are excluded from ALL construction, threshold-setting, and evaluation.
8 of the 14 sit inside the canonical 131-name universe (QQQ, AMD, PLTR, SMCI, NIO, ANET,
DRAM, SPCX) → **working set = 123 names**. 5 of the 14 appear in canonical_trades.json
(AMD×8, SMCI×5, PLTR×4, NIO×2, ANET×2 = 21 trades) → masked out, leaving **353 trades**.
AMD was the single most-traded symbol in the unmasked set — masking is load-bearing.

## F7 data audit (2026-09-24, before pre-registration)

**Revision candidate — UNTESTABLE.** yfinance exposes per-quarter `EPS Estimate`,
`Reported EPS`, `Surprise(%)` (single final-consensus snapshot per quarter) and NO
timestamped estimate-revision history. No other free source available to this worker
provides revision timestamps (Zacks/FactSet revision histories are paid). Constructing
"positive EPS revision in trailing 63 days" is therefore impossible without lookahead
or fabrication. NOT proxied with price action — dropped per the do-not-force rule.

**Drift candidate — TESTABLE.** `yfinance.Ticker.get_earnings_dates` returns actual
announcement dates (verified against known MSFT/JPM report dates; timestamps carry the
announcement time, e.g. 16:00 ET post-close / 08:00 ET pre-open). Probe 2026-09-24:
12/12 working-set equities returned full histories (~25 dates each, past actuals +
future scheduled), ~2.4s/symbol, zero failures. PIT rule: use ONLY rows with non-null
`Reported EPS` (actual announcements) and index date ≤ signal time — future/scheduled
dates are never touched. Rescheduling lookahead: nil in practice — we only use dates
whose announcement already happened (reported EPS exists), so the date used is the
date the market actually saw the announcement. Earnings dates fetched once for the
113 equity names, cached to `earnings_dates_w4.json`.

**F7 test population:** equity names only (113 of 123). The 10 ETFs (SPY, IWM, TLT,
XLE, XLF, SMH, DIA, XLK, GLD, ARKK) have no earnings by construction — including them
as "unselected" would contaminate the comparison with a structurally different asset
class. This is a pre-registered design decision, not data-driven.

## F7 pre-registered construction (frozen before computing any F7 result)

- **Factor:** 5-trading-day post-earnings drift of the most recent earnings announcement.
- At signal time T (4H signal-bar close): let D = most recent actual earnings date with
  `D.date() < T.date()`. Drift window: `drift = close(D+5) / close(D) − 1` on daily bars
  (close(D) = announcement-day close; note D's bar does NOT contain the news).
- Strict PIT: all of D…D+5 trading days must be ≤ last completed daily bar as of T
  (latest trading day whose 16:00 ET close is strictly before T). If the window is
  incomplete at T → no value → unselected.
- Staleness: D must be within the trailing 63 trading days of T (≈ one quarter back);
  older → unselected.
- **Select: drift > 0** (positive post-earnings drift = business momentum under the tape).
- Perturbations (robustness only): threshold > +0.02; window 10 trading days instead of 5.

## F8 pre-registered construction (frozen before computing any F8 result)

Disambiguations of the FACTOR_MENU spec, frozen here:
- **Up-day** = daily close > previous daily close; **down-day** = close < previous close
  (day-over-day; flat days count in neither group).
- **Volume median** = median of daily volume over the SAME trailing window (strict PIT).
- **Daily endpoint** = last completed daily bar as of the 4H signal-bar close: latest
  trading day whose 16:00 ET close is strictly before the signal timestamp (so 16:00
  signals use the prior day's bar — conservative, unambiguous).
- `balance = (# up-days with vol > median − # down-days with vol > median) / N`
- **Select: balance > 0.15** (pre-registered). Perturb: thresholds 0.10 / 0.20, windows
  20 / 40 trading days.

## Test protocol (both factors, from FACTOR_MENU)

Signal population: canonical_trades.json (taken trades, post slot/heat competition),
masked to the working set (353 trades). Relative test = selected vs unselected
expectancy on the same population; absolute test = does selected clear zero?
Periods: full / dev 2023-10-01–2024-12-31 / val 2025-01-01–2026-09-30 / years
2024, 2025, 2026 / walk-forward 6-month test windows (2024H2, 2025H1, 2025H2, 2026H1,
2026H2+). Thresholds frozen — dev/val is a pure out-of-time check, nothing is fit.
Costs: per-trade net R at 25/50/75/100bps round-trip (precomputed leg-based in the
trade records; headline = 50bps). Bootstrap ≥5,000 on the selected−unselected delta
(resample each group separately, report P(delta>0) and 95% CI). LOSO over symbols.
Concentration: per-symbol contribution to the delta; delta ex-top-1/3/5 contributors.
Economic check: full portfolio replay (simlib v54 signals + rs_top2 slot competition +
Mode B engine, imported from canonical_baseline) on working-set symbols, full vs
selected-signals-only, $75k / 1% risk / 6 slots / 5% heat.

## Results

### F8 — institutional-footprint proxy

(Tables filled after computation.)

### F7 — post-earnings drift

(Tables filled after computation.)

## Verdicts

- **F8:** TBD
- **F7:** TBD
