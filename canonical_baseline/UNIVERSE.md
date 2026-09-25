# Canonical Baseline Universe — point-in-time construction

Built 2026-09-24/25 (worker (a) of the canonical-baseline rebuild).
Research only. Nothing frozen was touched; all outputs live under
`canonical_baseline/`.

## The rule (one sentence)

The universe is the **top 120 US-listed common stocks and plain ETFs by
trailing-63-trading-day average daily dollar volume as of 2023-09-30**,
plus post-cutoff new listings admitted only from listing date + ~60 4H
bars subject to a $25M/day liquidity gate — 131 symbols total.

## Why this fixes the old baseline

The old research ran on Mike's 14-name live watchlist (assembled Sep 2026,
with full knowledge of the test window). On the 2023-09-30 dollar-volume
ranking, the four names carrying 102% of the old baseline's P&L rank
**#189 (HOOD), #207 (RKLB), #220 (BBAI), #227 (ONDS)** out of 229 rankable
names — i.e. the old universe was the 80th+ percentile of random draws by
construction. SOFI (#130) also misses the cut. The mechanical rule below
removes the hand-picking.

## Construction steps (all PIT)

1. **Candidate pool** (`candidate_pool.json`, 272 symbols): union of every
   symbol referenced anywhere in the repo — `v54_universe_x2.py` (199),
   `pine_backtest.py` UNIVERSE_15/UNIVERSE_X (51), `signal_log/watchlist.txt`
   (14), `backtest_cache` / `pine_1h/cache` / `pine_2h3h_backtest/cache`
   filenames, rotation-watch tickers, plus CYBR and SQ (named in the X2
   docstring as dropped/renamed). Build script: `scripts/build_pool.py`.
2. **Ranking metric**: for each pool symbol, average daily dollar volume =
   mean(adjusted Close × Volume) over the 63 trading days ending
   **2023-09-30** (window 2023-06-30 → 2023-09-30), from split/dividend-adjusted
   daily bars. Script: `scripts/select_universe.py`; full ranking in
   `addv_ranking_20230930.json`.
3. **Rankability**: ≥30 daily bars in the window; crypto pairs (`*-USD`)
   and leveraged/inverse ETFs (ASTX, 2x daily-reset) excluded from ranking
   (43 names unrankable — see `addv_unrankable.json`).
4. **Selection**: top 120 by ADDV. Cutoff: rank 120 = DVN at $375.7M/day;
   rank 121 = DAL at $373.2M/day (near-boundary names documented in the
   ranking file). Rank 1 = SPY at $32.2B/day.
5. **New listings**: pool names first trading after 2023-09-30 enter from
   listing + 30 trading days (≈60 4H bars) **only if** trailing-20-trading-day
   ADDV at eligibility ≥ $25M/day (mechanical, PIT-computable; evaluation in
   `new_listings_eval.json`). 11 admitted: ARM, BMNR, CRWV, DRAM, GEV, GLXY,
   NBIS, RDDT, SNDK, SPCX, TEM. 4 rejected: CORZ ($14.0M), NNE ($12.9M),
   RBRK ($24.5M — just under the gate), UMAC ($0.8M).
6. **Delisted/acquired**: kept through their last trading day. In practice
   none of the top-120 delisted during the window (all have last bar
   2026-09-24). The one known dead name in the pool, **CYBR** (acquired
   2025), returns no data from yfinance and is documented as missing below.

### PIT justification for the pool

The pool is hindsight-*influenced* (it is the union of Mike's 2026 lists)
but the *selection rule* is point-in-time: a symbol enters the universe
only if it was already among the most-traded US names on 2023-09-30, a
fact knowable on that date. Names that became famous later do not enter
unless they independently clear the dollar-volume bar (or the new-listing
rule). Residual risk: the pool may *miss* names that were liquid in Sep
2023 but that Mike never watched — the rule cannot select what the pool
doesn't contain. The pool (272 names) is a superset of every name the
research ever touched, so the plausible top-120 answer is covered; a
future vendor-sourced full-market ranking (e.g. all CRSP/Norgate names)
would close this residual.

## Data sources

- **Source: yfinance** (free). No API keys exist in this environment;
  Stooq is unreachable from this network (connection fails), and every
  vendor with pre-2024 intraday (Polygon, Alpaca, Tiingo, Norgate) needs
  a key. Documented as a limitation with a recommended upgrade path below.
- **Daily cache** (`data/d1_{SYM}.pkl`, 272 files): 2023-06-01 → 2026-09-24,
  `auto_adjust=False` then OHLC scaled by AdjClose/Close factor
  (split- **and** dividend-adjusted), Volume raw, America/New_York,
  regular session. Script: `scripts/fetch_daily.py` (batched download).
- **4H cache** (`data/h4_{SYM}.pkl`, 137 files = 131 universe + 6 overlay
  extras): 1H bars → resampled per-day, 4h bins anchored at 09:30 ET
  (bars at 09:30 / 13:30 ET, none spanning the overnight gap), agg
  first/max/min/last/sum — the same convention as the repo's
  `pine_entry_timing_backtest/fetch_resample_4h.py`. Script:
  `scripts/fetch_4h.py`.
  - **Intraday limit**: yfinance serves 1H only for the trailing 730 days,
    so 4H coverage is **2023-10-26 → 2026-09-24** (1451 bars for full-history
    names), not the aspirational 2023-09-01. The daily cache covers the
    full 2023-09-01+ window for warmup and daily-bar work.
  - Intraday bars are split-adjusted by Yahoo; dividends are *not*
    adjusted on intraday bars (immaterial at 4H horizon; daily cache is
    fully adjusted).
  - Per-symbol effective 4H start dates are in `coverage_report.json`
    (`effective_4h_from`); backtests should use
    `max(eligible_from, effective_4h_from)`.

## Corporate-action table

| Symbol | Event | Handling |
|---|---|---|
| SMCI | 10:1 split 2024-10-01 | Verified smooth in adjusted data ($41.64→$40.55 across the window; zero >40% single-day moves in full series). No action needed. |
| XYZ (ex-SQ) | Ticker rename SQ→XYZ | yfinance serves the full SQ-era history under XYZ (verified: 831 daily bars from 2023-06-01). Universe uses XYZ. |
| SPCX | Ticker **reuse**: old SPCX (SPAC ETF, liquidated Aug 2022) vs new SPCX (SpaceX, listed 2026-06-12) | Treated as distinct instruments keyed by listing date. yfinance "SPCX" returns only the SpaceX series (verified: starts 2026-06-12). Admitted via new-listing rule, eligible from ~2026-07-28. |
| CYBR | Acquired 2025 (Palo Alto Networks), delisted | **Missing**: yfinance returns "Quote not found" — no daily or intraday history retrievable. Not in universe (no data to rank). Needs a survivorship-inclusive vendor (Norgate/CRSP-style) to include. |
| BRK-B | Hyphenated ticker | Fetched as `BRK-B`; fine. |
| ARM | IPO 2023-09-14 (12 bars in ranking window) | Ranked unrankable (thin history); admitted via new-listing rule, eligible ~2023-10-26. |

## Coverage validation (`coverage_report.json`, script `scripts/validate_cache.py`)

- Expected 4H bars per symbol computed from its daily calendar inside the
  eligible window: 2 per full trading day, 1 per NYSE 13:00 early close
  (2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24, 2025-07-03, 2025-11-28,
  2025-12-24).
- **131/131 universe symbols: zero with >5% missing 4H bars — nothing flagged.**
  Missing%: mean −0.09%, median −0.14%, max +0.15% (≈±2 bars out of ~1450;
  small positive/negative deviations are calendar edge effects, not gaps).
- Data-quality sweep on all 131 4H frames: 0 NaN OHLC, 0 zero-volume bars,
  0 duplicated timestamps, 0 impossible wicks, timezone America/New_York
  everywhere, all bars stamped 09:30/13:30 ET.
- Two known Yahoo 1h gaps (single 4H bar on full trading days 2026-01-30
  and 2026-02-02, visible in AAPL and market-wide) — counted as missing
  bars; negligible (<0.15%).
- New listings with 4H starting after their rule eligibility
  (GEV/RDDT/TEM: Yahoo 1H hard-capped at 730d, first 4H bar 2026→
  actually 2024-09-26): effective 4H eligibility = 60th 4H bar
  (≈2024-11-07), recorded per-symbol in `coverage_report.json`.

## The 14-name overlay (`universe_overlay_14.json`)

Mike's 14 watchlist names are kept **only** as a reporting overlay — never
the universe. 8 of 14 are in the canonical universe
(QQQ, SMCI, PLTR, ANET, NIO, AMD, DRAM, SPCX); 6 are not
(SOFI rank #130 — just missed; RKLB #207, ONDS #227, BBAI #220,
HOOD #189 — the old baseline's P&L carriers; ASTX — leveraged-ETF
exclusion). The 6 outsiders have 4H cached (`data/h4_*.pkl`) so the
overlay subset can still be reported alongside the neutral baseline.

## File inventory

| Path | Contents |
|---|---|
| `canonical_baseline/universe.json` | **The universe**: 131 dicts — `symbol`, `eligible_from`, `eligible_to`, `reason`, `addv_rank_2023_09_30`, `addv_usd_per_day`, `sector`, `delisted`, plus listing/liquidity fields for new listings. Trivially loadable: `json.load(open(...))` → list of dicts. |
| `canonical_baseline/UNIVERSE.md` | This document. |
| `canonical_baseline/universe_overlay_14.json` | The 14-name reporting overlay with in/out-of-universe flags. |
| `canonical_baseline/data/d1_{SYM}.pkl` | Daily bars, 272 symbols, 2023-06-01 → 2026-09-24. |
| `canonical_baseline/data/h4_{SYM}.pkl` | 4H bars, 137 symbols (131 universe + 6 overlay extras), 2023-10-26 → 2026-09-24. |
| `canonical_baseline/candidate_pool.json` | 272-symbol pool with per-symbol repo sources. |
| `canonical_baseline/addv_ranking_20230930.json` | Full 229-name ADDV ranking. |
| `canonical_baseline/addv_unrankable.json` | 43 excluded-from-ranking names + reasons. |
| `canonical_baseline/new_listings_eval.json` | 15 post-cutoff listings, liquidity-gate evaluation. |
| `canonical_baseline/sectors_raw.json` | yfinance sector/industry pull (2026-09-25; current GICS — changes since 2023 are rare, treat as approximate PIT assignment). |
| `canonical_baseline/coverage_report.json` | Per-symbol expected/actual 4H, missing%, flags, quality checks, `effective_4h_from`. |
| `canonical_baseline/fetch_daily_log.json`, `fetch_4h_log.json` | Fetch provenance per symbol. |
| `canonical_baseline/scripts/` | `build_pool.py`, `fetch_daily.py`, `select_universe.py`, `pull_sectors.py`, `fetch_4h.py`, `validate_cache.py` — full rebuild recipe. |

## Known limitations (for workers (d) and (e))

1. **4H starts 2023-10-26, not 2023-09-01** — yfinance 1H hard limit (730d).
   Baseline backtest window on 4H is effectively Oct 2023 → Sep 2026
   (~2.9y, ~1450 bars/symbol — comparable trade count to the old study).
   A vendor backfill (Norgate/Polygon) would extend intraday to 2023-09-01.
2. **CYBR unrecoverable from yfinance** — the one documented delisted name
   is missing; survivorship handling is structurally ready (eligible_to /
   last-bar logic) but unpopulated.
3. **Sector labels are current-pull (2026-09-25)**, not 2023-vintage GICS.
   GICS reclassifications are rare; acceptable approximation, flagged.
4. **Pool-coverage residual** (see PIT justification): a full-market vendor
   ranking would remove the last hindsight-adjacent choice (the pool
   boundary itself).
5. Costs/execution/Mode B exits are **not** this worker's scope — the cache
   is raw material; workers (d)/(e) apply the exit stack and cost model.
