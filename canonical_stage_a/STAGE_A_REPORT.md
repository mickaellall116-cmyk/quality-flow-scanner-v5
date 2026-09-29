# Stage A Report — candidate pool + daily PIT data

**Spec:** rev-6.1 (SHA-256 `53d3a5b8309fb3832e12bdf3ede24b55214919ec79f9c53f6096cddf7f371d9e`)
**Branch:** `research/canonical-stage-a` (from `9a6469a0`, branch `research/canonical-rev6-1-audit`)
**Run:** 2026-09-29 ~17:17–17:21 ET (fetch 21:17:29Z–21:19:48Z; analysis 21:21:06Z)
**Scope:** Stage A only — pool reconstruction, fresh daily cache, ADDV ranking, new-listing eval, Gate A. No portfolio simulation, no Phase-1 exposure rule, no production V5.4 changes.

## 1. Whitelisted input hashes (SHA-256, hashed before use)

| File | SHA-256 |
|---|---|
| `canonical_baseline/candidate_pool.json` | `bbd057eb08e7d2b606d7712d04bde9a27060a47191c2b65a0ba2499ca97c86de` |
| `canonical_baseline/addv_ranking_20230930.json` | `a1748bf63e2ca8e03092eb4afa72b0ea533aa3b9b5a626ffa6ec03f2b1ed0e0f` |
| `canonical_baseline/addv_unrankable.json` | `9c6457cced3f787facf8c1ff07161e713f9b97940bfa0b3b9e3fdb889062ada3` |
| `canonical_baseline/new_listings_eval.json` | `1ed4f6d35e7fcd16e0e48cb140b43b2667235d6b0c37884e824d9635cee95f56` |
| `canonical_baseline/universe.json` | `fa21ca55724993fab6709ab83fef7f2001e7d7672fa9e24f97beb24066893b16` |
| `canonical_baseline/universe_overlay_14.json` | `ecb124d717918ecffe453a47a5d69b9836f01b93cecf1e76a43829d09ea2c07c` |
| `canonical_baseline/coverage_report.json` | `fdb6e33a1b2edde231e607f9c5cd8f33f82f2d8b82caaac473fc551c26faed2b` |

All seven files are §1-whitelisted non-performance input artifacts, used as **check targets / frozen inputs only**, never as implementation sources.
The sealed comparator was not opened. No quarantined file (`simlib.py`, `modeb_engine.py`, `run_portfolio.py`, `analyze.py`, scripts, `data/*.pkl`, trade/result JSONs, fetch logs, `sectors_raw.json`, lonewolf files) was opened, read, or consulted.

## 2. Pinned-tree pool extraction — FINDING

Attempted the documented recipe: union of every symbol referenced in the repo at pinned tree
`de01ff70a13e680c5468ae5e6e81177c981832e0` (scanned all 7 `.py` files, `signal_log/watchlist.txt`, `signal_log/README.md`).

**Result: the pinned tree alone cannot reproduce the documented 272-name pool.**

- The tree contains only 7 `.py` files. The documented pool sources `v54_universe_x2.py` (199 names),
  `pine_backtest.py` (UNIVERSE_15/UNIVERSE_X, 51 names), and `rotation_watch.py` (21 names) **do not exist**
  at the pinned commit — they were never committed there. Neither do any `backtest_cache` / `pine_1h/cache` /
  `pine_2h3h_backtest/cache` filename sources.
- The extractable union (DEFAULT_WATCHLIST + DISCOVERY_THEMES + watchlist.txt) yields **129 names**, not 272.
- The pinned tree's `signal_log/watchlist.txt` holds only **4** names (QQQ, SMCI, PLTR, ANET), vs the 14 names
  the pool attributes to `signal_log/watchlist.txt` — the pool was built from a later repo state.
- Subset check **failed**: 30 of the 129 tree-extracted names are **not** in `candidate_pool.json`:
  ACHR, ARQQ, BKSY, DNN, FLR, GFAI, GSAT, HIMS, HWM, IRDM, JOBY, MCHP, NTAP, NVTS, PL, QUBT, RDW,
  RIVN, RPD, SATL, SOXX, SPIR, SUI-USD, TDY, TENB, TER, UEC, URNM, VOO, XLV
  (all from the pinned commit's DISCOVERY_THEMES; they never entered the documented pool).
- Per-symbol provenance as far as the tree allows is recorded in `canonical_stage_a/tree_pool_extraction.json`.

Per the frozen plan, the whitelisted `candidate_pool.json` (272 names, hash above) is therefore the frozen
Stage-A pool input. Its per-symbol `sources` fields corroborate the documented provenance:
v54_universe_x2:UNIVERSE_X2 (199), data-cache-filename (58), pine_backtest:UNIVERSE_X (51),
rotation_watch.py:TICKERS (21), pine_backtest:UNIVERSE_15 (15), signal_log/watchlist.txt (14),
plus the CYBR (acquired 2025) and SQ (renamed XYZ) docstring entries.

## 3. Daily cache rebuild (fresh — no reuse of `data/*.pkl`)

- Source: yfinance 1.7.0. Window 2023-06-01 → 2026-09-24 (end-exclusive 2026-09-25).
- `auto_adjust=False`; OHLC scaled by AdjClose/Close factor (split- **and** dividend-adjusted); raw Volume;
  America/New_York; regular session only (`prepost=False`); NaN-OHLC calendar-padding rows dropped
  (batch downloads align tickers on the union of dates — crypto's 24/7 calendar pads stock symbols with
  weekend rows; first run kept them, caught in review, fixed with `dropna` and re-fetched clean).
- Batching: ~20 symbols/request, single-threaded, ~4s between batches; no 429s encountered;
  the live forward-test harness shares this vendor and was not disturbed.
- **270/272 symbols fetched.** 2 missing, both expected and documented:
  - `CYBR` — no daily data (acquired 2025, delisted; yfinance 'Quote not found'). Matches UNIVERSE.md.
  - `SQ` — no data under the old ticker (renamed XYZ; full SQ-era history served under `XYZ`: 832 bars
    from 2023-06-01). Matches UNIVERSE.md corporate-action table ('Universe uses XYZ').
- One deterministic JSON cache per symbol: `canonical_stage_a/data/d1_{SYMBOL}.json`
  (270 files), each with per-row [date, open_adj, high_adj, low_adj, close_adj, adj_close, volume_raw].
- Full-history names: 832 trading-day bars (2023-06-01 → 2026-09-24). Crypto pairs: 1212 calendar-day bars (24/7).
- Spot checks: SPCX returns only the SpaceX series (72 bars from 2026-06-12; ticker-reuse handled);
  ARM 760 bars from 2023-09-14; BRK-B hyphenated ticker fine.

### 3.1 Per-symbol cache manifest (SHA-256 + fetch timestamps, UTC)

| Symbol | Bars | First | Last | Fetched (UTC) | SHA-256 |
|---|---|---|---|---|---|
| AAPL | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:29Z | `987a2b66cacd229e…` |
| AAVE-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:29Z | `ce331bb93f98bb58…` |
| ABBV | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:29Z | `dcfe8fe4347d448f…` |
| ABNB | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:29Z | `ff0940b03e010d64…` |
| ADA-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:29Z | `e799ddb8ad1c8255…` |
| ADBE | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:29Z | `d53a07930a55af43…` |
| AFRM | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:29Z | `24c9523a45bbb57c…` |
| AI | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:29Z | `79b5aa2c5d5db98a…` |
| ALB | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:29Z | `2312ae21758d7a8c…` |
| AMAT | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:29Z | `993f3da2614ad3d3…` |
| AMC | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:29Z | `e9c7a42405fb3917…` |
| AMD | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:30Z | `13aa45fa4a8f5ef3…` |
| AMGN | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:30Z | `8689738bad564e9d…` |
| AMT | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:30Z | `83482a19d8d9fe91…` |
| AMZN | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:30Z | `644946a3dd71816e…` |
| ANET | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:30Z | `a880b996b72ec19f…` |
| APLD | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:30Z | `5af5177442f77436…` |
| APP | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:30Z | `de555706e586827d…` |
| ARB-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:30Z | `9a9577959f04c694…` |
| ARKK | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:30Z | `e61c511afc5ab15f…` |
| ARM | 760 | 2023-09-14 | 2026-09-24 | 2026-09-29T21:17:39Z | `32d574e6504a01bd…` |
| ASML | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:39Z | `cf4d2a5c97e4fe6c…` |
| ASTS | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:39Z | `94333bfea5903729…` |
| ASTX | 304 | 2025-07-11 | 2026-09-24 | 2026-09-29T21:17:39Z | `bf86b50aaccf7236…` |
| ATOM-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:39Z | `a1fa7dd69bc3d76d…` |
| AVAX-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:39Z | `79a42931921d4190…` |
| AVGO | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:39Z | `3b21be7078a71ac0…` |
| BA | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:40Z | `a2405dc80b11e855…` |
| BAC | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:40Z | `8072ad9f4a394bda…` |
| BBAI | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:40Z | `08f6931f18547a32…` |
| BE | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:40Z | `e4433a087ad5d4b0…` |
| BIIB | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:40Z | `15874e45a6c827e8…` |
| BKNG | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:40Z | `4035ab73bdb032c8…` |
| BKR | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:40Z | `0fb16874cb1e36df…` |
| BMNR | 328 | 2025-06-05 | 2026-09-24 | 2026-09-29T21:17:40Z | `5fd5633231c1c863…` |
| BNB-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:40Z | `ec5407bf0c51b18f…` |
| BONK-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:40Z | `31a93453bf2c8b4d…` |
| BP | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:40Z | `6197a405ab8ad63b…` |
| BRK-B | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:40Z | `4e9a57859d74ee94…` |
| BTC-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:40Z | `448fd1a9b0388ed3…` |
| BTDR | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:49Z | `9262e40d8e02f16b…` |
| BWXT | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:49Z | `dd9af36b845be424…` |
| CAT | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:49Z | `41005dcbd17dc35f…` |
| CCJ | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:49Z | `443a4d450772ef4d…` |
| CDNS | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:49Z | `2e13256314af45df…` |
| CEG | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:50Z | `e4df5cc18e25db4d…` |
| CIEN | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:50Z | `1bc0748a1edf1e29…` |
| CIFR | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:50Z | `eca9aefa40667817…` |
| CLS | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:50Z | `6e40be457f671385…` |
| CLSK | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:50Z | `aaa9c485aaa9bb26…` |
| CMG | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:50Z | `84a4ecd1b702d911…` |
| COHR | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:50Z | `9372bab0289afe84…` |
| COIN | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:50Z | `ac447d340e10e351…` |
| COP | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:50Z | `a808355ee4e6cc5c…` |
| CORZ | 670 | 2024-01-24 | 2026-09-24 | 2026-09-29T21:17:50Z | `696bb08f7ecaa419…` |
| COST | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:50Z | `0cfe8e5fe31b1aad…` |
| CPER | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:50Z | `7fdf12df87271e33…` |
| CRM | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:50Z | `3b034b1415243f13…` |
| CRSP | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:51Z | `b526c2a71005866e…` |
| CRWD | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:17:51Z | `2f091e3df67d760e…` |
| CRWV | 375 | 2025-03-28 | 2026-09-24 | 2026-09-29T21:18:02Z | `fcf4350eea31bbc1…` |
| CSCO | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:02Z | `d510f76d16237d1f…` |
| CVX | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:02Z | `2821a691bec72f90…` |
| CYBR | MISSING | — | — | 2026-09-29T21:21:01Z | yfinance returned no daily bars after retries |
| DAL | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:02Z | `bffb9bde7119f2e5…` |
| DASH | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:02Z | `6f97c929cbe0c5cc…` |
| DDOG | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:02Z | `e74ed994631dbfb0…` |
| DE | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:02Z | `281de325bb29ff0c…` |
| DELL | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:02Z | `361ac2da27076fcf…` |
| DHR | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:03Z | `f77eaed34fce1315…` |
| DIA | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:03Z | `1c29096c9d62c235…` |
| DIS | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:03Z | `70ec779e83813598…` |
| DJT | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:03Z | `1287ddca3a067cef…` |
| DKNG | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:03Z | `a36dbe3416dfd38b…` |
| DLR | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:03Z | `77fef354db481dd1…` |
| DOCU | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:03Z | `b19e1aae14c94392…` |
| DOGE-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:03Z | `59e1fb2f47a2c4f4…` |
| DOT-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:03Z | `ad0544c33132d7a9…` |
| DRAM | 121 | 2026-04-02 | 2026-09-24 | 2026-09-29T21:18:03Z | `7960060c8f0707a9…` |
| DVN | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:03Z | `b6f3cf8e674d2b02…` |
| EBAY | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:12Z | `0cf08745c69713db…` |
| EME | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:12Z | `011568b60b9c91b8…` |
| ENPH | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:12Z | `bb50cfacfbaafbfd…` |
| EOG | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:13Z | `fc3b7c6f55f14078…` |
| EPD | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:13Z | `33d570d7a859003b…` |
| EQIX | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:13Z | `f896a42374a0af69…` |
| EQT | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:13Z | `ab365dbf6a490859…` |
| ET | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:13Z | `9dcebfd07b4b70fe…` |
| ETH-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:13Z | `067b0dc0df8ffb3b…` |
| ETN | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:13Z | `bc1851ba63f5f870…` |
| EXPE | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:13Z | `0e5a5bf03e571941…` |
| F | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:13Z | `ce65ffeff21f56c6…` |
| FANG | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:13Z | `b0c08b725f90bb8e…` |
| FCX | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:13Z | `7e7cbb2d66b2dcb8…` |
| FDX | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:13Z | `5c9fb3e21d1db8c6…` |
| FET-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:13Z | `b0ac06d3e30d6f2d…` |
| FIL-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:14Z | `60deb9f9d806d8a8…` |
| FIS | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:14Z | `0c00f6a462626c9d…` |
| FSLR | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:14Z | `0bd36d918544cbba…` |
| FTNT | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:14Z | `6128e3dceece9e28…` |
| GD | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:23Z | `1e22f085b7321a09…` |
| GE | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:23Z | `0f6dca1a94677946…` |
| GEV | 626 | 2024-03-27 | 2026-09-24 | 2026-09-29T21:18:23Z | `0e375c23fd695c4d…` |
| GILD | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:23Z | `7e843ee398feb274…` |
| GLD | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:23Z | `c8af4a843d22aece…` |
| GLXY | 341 | 2025-05-16 | 2026-09-24 | 2026-09-29T21:18:24Z | `20f8a1d1ea7e57b8…` |
| GM | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:24Z | `2f1500d96196d45b…` |
| GME | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:24Z | `220161b2a92334b6…` |
| GOOGL | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:24Z | `8d62f513440a1a0b…` |
| GPN | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:24Z | `4cb08dcba401d572…` |
| GS | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:24Z | `0371aed0bb12f4d4…` |
| HAL | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:24Z | `37249b8a9b76ffbb…` |
| HBAR-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:24Z | `25eabcdf6e910c0f…` |
| HD | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:24Z | `eecf296cb162f6ef…` |
| HON | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:24Z | `1df453db53d294bf…` |
| HOOD | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:24Z | `ae12a6f4df3401ac…` |
| HPE | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:24Z | `3cfcc75f8e1e21d7…` |
| HUBS | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:24Z | `ea7a00b09b19c2d9…` |
| HUT | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:25Z | `4444f39a22e85b9a…` |
| IBM | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:25Z | `643e251b53d37e31…` |
| ICP-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:34Z | `1f0b45aa5439c735…` |
| ILMN | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:34Z | `2a1e51ef225866db…` |
| INJ-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:34Z | `348a94d7e7c0f610…` |
| INTC | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:34Z | `530087e5757f69d4…` |
| INTU | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:34Z | `ccb64c201e7aefd5…` |
| IONQ | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:34Z | `9eacfc7084cc3163…` |
| IREN | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:34Z | `f3e22d309670c979…` |
| ISRG | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:34Z | `d8045d909ddaa249…` |
| IWM | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:34Z | `cad1dea931f62d62…` |
| JBL | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:34Z | `83ff5531cede5859…` |
| JNJ | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:34Z | `6ba75698ed561be8…` |
| JPM | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:35Z | `ecfc30bebc28e8cc…` |
| KLAC | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:35Z | `cf3bf5c9ab33b9d8…` |
| KMI | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:35Z | `54c41f037e8f88fb…` |
| KO | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:35Z | `769d094fcd7459fc…` |
| LCID | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:35Z | `7e5bb93b9b12044a…` |
| LEU | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:35Z | `b2b0a8e37c7bc3ba…` |
| LIN | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:35Z | `8a1ccf633f733e8b…` |
| LINK-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:35Z | `f207027b54ad89b4…` |
| LITE | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:35Z | `e0efce2b8acb7fc1…` |
| LLY | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:44Z | `5bf1740a9943ebb7…` |
| LMT | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:44Z | `22b79ef061ca4b71…` |
| LRCX | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:44Z | `e400fc29b05dcd12…` |
| LUNR | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:44Z | `79e9e8405a761df7…` |
| LYFT | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:44Z | `db58c81475aaed21…` |
| MA | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:44Z | `133e535b96d31858…` |
| MARA | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:45Z | `bf46fa3aa814dc35…` |
| MCD | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:45Z | `7160e702a8feaf98…` |
| MDB | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:45Z | `1ab80e415dc3be93…` |
| MELI | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:45Z | `979e23813297a983…` |
| META | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:45Z | `568797df9c619187…` |
| MP | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:45Z | `4a5cf463868529a8…` |
| MPC | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:45Z | `611666c6db4befe8…` |
| MRNA | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:45Z | `b77aada21ec88401…` |
| MRVL | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:45Z | `5703499a44bb26f5…` |
| MS | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:45Z | `06b549fa067930a1…` |
| MSFT | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:45Z | `765795d25616ca28…` |
| MSTR | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:45Z | `4ece6b5203a33305…` |
| MU | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:45Z | `13b415de6df65ccc…` |
| NBIS | 483 | 2024-10-21 | 2026-09-24 | 2026-09-29T21:18:45Z | `7d626affe590a3d0…` |
| NEAR-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:55Z | `d19fa3e7acc61bd3…` |
| NEE | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:55Z | `a9373c120e1579a6…` |
| NEM | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:55Z | `16402010f0ff01eb…` |
| NET | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:55Z | `28194c3f74d93a8b…` |
| NFLX | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:55Z | `e26391b1cc427814…` |
| NIO | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:55Z | `4aefb4ff5d59fc1d…` |
| NKE | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:55Z | `d37fcbad7e488e46…` |
| NNE | 597 | 2024-05-08 | 2026-09-24 | 2026-09-29T21:18:55Z | `f366b55c8f18b8bb…` |
| NOC | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:55Z | `f8ca82a20285798a…` |
| NOW | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:55Z | `f7e20f637ff750e1…` |
| NU | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:55Z | `88f252d5ab1a3c02…` |
| NVDA | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:55Z | `2f550ed346c37449…` |
| NXPI | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:55Z | `ff9fa6e9aaf70625…` |
| OKE | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:56Z | `ed0b40f3e786eb42…` |
| OKLO | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:56Z | `c74a46dcc69965f6…` |
| OKTA | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:56Z | `29dc0e1d83b55ad9…` |
| ON | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:56Z | `90fdef25263c8a13…` |
| ONDO-USD | 981 | 2024-01-18 | 2026-09-24 | 2026-09-29T21:18:56Z | `c9ac2a0da9de9a72…` |
| ONDS | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:56Z | `a2c12f069470c96f…` |
| OPEN | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:18:56Z | `9839648cbb94fe30…` |
| ORCL | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:06Z | `ecc1f775ccd74d5d…` |
| OXY | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:06Z | `12f516e41b0d1036…` |
| PANW | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:06Z | `f64a911a5d8fc0f1…` |
| PATH | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:07Z | `0ccc0c90f034647c…` |
| PEP | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:07Z | `90503753839d92fa…` |
| PFE | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:07Z | `dfd0862a842a3b2c…` |
| PG | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:07Z | `a1fdcc5273d922d5…` |
| PLTR | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:07Z | `9509ae02afa59bc1…` |
| POWL | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:07Z | `6d1cd1123e96fa75…` |
| PPLT | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:07Z | `723e1819758bbb1e…` |
| PSX | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:07Z | `bb9d1bc7f08e22a9…` |
| PWR | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:07Z | `e9ab8a56413bafb9…` |
| PYPL | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:07Z | `dafad8ea5888b47e…` |
| QBTS | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:07Z | `312d24f6270277a9…` |
| QCOM | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:07Z | `4bb6401277ca010d…` |
| QQQ | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:08Z | `124fcf44f6dd3e37…` |
| RBLX | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:08Z | `8ad56b2358c8baa3…` |
| RBRK | 606 | 2024-04-25 | 2026-09-24 | 2026-09-29T21:19:08Z | `d835ecb96ebc4fa6…` |
| RDDT | 630 | 2024-03-21 | 2026-09-24 | 2026-09-29T21:19:08Z | `d6551da506de8bf8…` |
| REGN | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:08Z | `6f7c4601c8b64ae1…` |
| RENDER-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:16Z | `c7b3b705a2458e99…` |
| RGTI | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:17Z | `4d9589d60815f98a…` |
| RIOT | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:17Z | `d20258dd8ce34b32…` |
| RKLB | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:17Z | `0ad25fcc12b151a9…` |
| RTX | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:17Z | `fd4553d029c74684…` |
| S | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:17Z | `70d029ceb45e9aae…` |
| SBET | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:17Z | `bf6745a9fb1f4766…` |
| SBUX | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:17Z | `08a1204ea47685f4…` |
| SCHW | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:17Z | `4fd94790245b768a…` |
| SHEL | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:17Z | `c23d3d9c739989fb…` |
| SHIB-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:17Z | `a7c7374e8d5c526e…` |
| SHOP | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:17Z | `f9f6ce2af329b32b…` |
| SLB | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:18Z | `61d3c04309139bc8…` |
| SLV | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:18Z | `5ce55cb22f264d47…` |
| SMCI | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:18Z | `50ecac8930d1cf48…` |
| SMH | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:18Z | `32b3c7d50e5247eb…` |
| SMR | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:18Z | `700903f0b53fa551…` |
| SNAP | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:18Z | `842842c8f748cad5…` |
| SNDK | 405 | 2025-02-13 | 2026-09-24 | 2026-09-29T21:19:18Z | `cc7a4990716535c8…` |
| SNOW | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:18Z | `1e928f179cb582c6…` |
| SNPS | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:28Z | `a79b56d21eadbb1c…` |
| SOFI | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:28Z | `4a7aee312bf91a1e…` |
| SOL-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:29Z | `e8eb7775fc0a6b09…` |
| SOUN | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:29Z | `d43d8f857780195e…` |
| SPCX | 72 | 2026-06-12 | 2026-09-24 | 2026-09-29T21:19:29Z | `e8df8086e3598bf4…` |
| SPY | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:29Z | `7ad7a4d43bad1c55…` |
| SQ | MISSING | — | — | 2026-09-29T21:21:01Z | yfinance returned no daily bars after retries |
| STX | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:29Z | `e94750383439125e…` |
| T | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:29Z | `3e7d98c93e7e0e26…` |
| TEAM | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:29Z | `61f35674ae4d42de…` |
| TEM | 571 | 2024-06-14 | 2026-09-24 | 2026-09-29T21:19:29Z | `63cdd361bf43023f…` |
| TLN | 831 | 2023-06-02 | 2026-09-24 | 2026-09-29T21:19:29Z | `a1d8d7ddacfa9971…` |
| TLT | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:29Z | `6ae940741f7510a0…` |
| TMO | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:29Z | `fd4e3ca27f3ab344…` |
| TRX-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:29Z | `e442e48ee3de82c5…` |
| TSLA | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:29Z | `49bcfbc408e1ab8f…` |
| TSM | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:30Z | `b71fa5663cfa3a66…` |
| TSSI | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:30Z | `3e92eea192c62b25…` |
| TTE | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:30Z | `1ebcc9746f49dec9…` |
| TXN | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:30Z | `c9c5f5577a5a115b…` |
| UAL | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:39Z | `60fba51e4364cde7…` |
| UBER | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:39Z | `07d93d1c22836fc1…` |
| UMAC | 655 | 2024-02-14 | 2026-09-24 | 2026-09-29T21:19:39Z | `40cc80b30ea6b722…` |
| UNG | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:39Z | `7afc0a3091988ac6…` |
| UNH | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:39Z | `71fbf8fd7e020099…` |
| UNP | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:39Z | `52fa864364347665…` |
| UPST | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:40Z | `27bd6797a94848f0…` |
| USAR | 802 | 2023-07-17 | 2026-09-24 | 2026-09-29T21:19:40Z | `fefbaf588b38e073…` |
| USO | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:40Z | `100e95e1155baa81…` |
| UUUU | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:40Z | `ef8eca784b033a27…` |
| V | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:40Z | `89cc5214dc8d03c6…` |
| VEEV | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:40Z | `98f193e3976ad34d…` |
| VLO | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:40Z | `50ada1d24b66884e…` |
| VRT | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:40Z | `0b00f5c23026be3f…` |
| VRTX | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:40Z | `236c646ef68ddf1d…` |
| VST | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:40Z | `9e09cadc40efa8d1…` |
| VZ | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:40Z | `99c5129dfc4d24a2…` |
| WDAY | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:40Z | `aa29778b4860136d…` |
| WDC | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:40Z | `eb0c9265cfcda772…` |
| WFC | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:40Z | `8dbf058d932bb32d…` |
| WIF-USD | 1011 | 2023-12-19 | 2026-09-24 | 2026-09-29T21:19:47Z | `33db51327bc59550…` |
| WMB | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:48Z | `2aca0d99bf9ee83a…` |
| WMT | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:48Z | `faee35e692b13aa0…` |
| WULF | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:48Z | `17e09d2fbd980069…` |
| XLE | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:48Z | `a12ea80d322842f0…` |
| XLF | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:48Z | `30f86281922c105d…` |
| XLK | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:48Z | `4c8a4718cb2b185d…` |
| XOM | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:48Z | `9fc0108518728432…` |
| XRP-USD | 1212 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:48Z | `ae0c240d013ace19…` |
| XYZ | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:48Z | `b79c589ec19b517b…` |
| ZM | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:48Z | `46f58fafe371218d…` |
| ZS | 832 | 2023-06-01 | 2026-09-24 | 2026-09-29T21:19:48Z | `cfbb396683dbbd88…` |

(Full 64-hex digests in `canonical_stage_a/fetch_manifest.json`.)

## 4. ADDV ranking (recomputed from the fresh cache)

- Metric: mean(adjusted Close × Volume) over the 63-trading-day window ending 2023-09-30,
  implemented as the inclusive date range 2023-06-30 → 2023-09-30 (64 trading bars for full-history names;
  the '63' is nominal — the mean is insensitive to the one-bar difference).
- Rankable requires ≥30 daily bars in the window. Excluded from ranking: crypto pairs (`*-USD`, 25),
  leveraged/inverse ETFs (ASTX — documented 2x daily-reset in UNIVERSE.md; yfinance quoteType confirms 'ETF'),
  post-cutoff listings (14), thin-history ARM (12 bars), CYBR (no data), SQ (renamed alias of XYZ, ranked instead).
- **Unrankable identity + reason sets match the check target exactly (43/43).**
- **Ranking identity order matches the check target exactly (229/229); worst relative ADDV deviation 4.5e-08
  (floating-point noise) — the independent recomputation reproduces the documented ranking.**

### 4.1 Full ranking table (ADDV in $M/day)

| Rank | Symbol | ADDV $M/day | Win bars |
|---|---|---|---|
| 1 | SPY | 32,168.91 | 64 |
| 2 | TSLA | 29,950.10 | 64 |
| 3 | NVDA | 22,017.53 | 64 |
| 4 | QQQ | 18,163.73 | 64 |
| 5 | AAPL | 10,537.43 | 64 |
| 6 | MSFT | 8,064.79 | 64 |
| 7 | AMZN | 7,212.46 | 64 |
| 8 | META | 6,883.08 | 64 |
| 9 | AMD | 6,484.41 | 64 |
| 10 | IWM | 4,654.64 | 64 |
| 11 | GOOGL | 3,600.36 | 64 |
| 12 | JNJ | 3,457.42 | 64 |
| 13 | NFLX | 2,566.95 | 64 |
| 14 | TLT | 2,456.86 | 64 |
| 15 | AVGO | 1,957.75 | 64 |
| 16 | XOM | 1,545.06 | 64 |
| 17 | XLE | 1,505.38 | 64 |
| 18 | UNH | 1,474.54 | 64 |
| 19 | ADBE | 1,463.20 | 64 |
| 20 | LLY | 1,422.80 | 64 |
| 21 | DIS | 1,337.21 | 64 |
| 22 | JPM | 1,286.88 | 64 |
| 23 | INTC | 1,281.54 | 64 |
| 24 | XLF | 1,278.89 | 64 |
| 25 | V | 1,229.19 | 64 |
| 26 | ORCL | 1,126.70 | 64 |
| 27 | BAC | 1,117.58 | 64 |
| 28 | BA | 1,105.14 | 64 |
| 29 | SMH | 1,099.40 | 64 |
| 30 | BRK-B | 1,085.66 | 64 |
| 31 | CRM | 1,064.97 | 64 |
| 32 | DIA | 1,046.75 | 64 |
| 33 | XLK | 1,032.09 | 64 |
| 34 | GLD | 1,030.23 | 64 |
| 35 | CVX | 1,025.23 | 64 |
| 36 | PANW | 1,002.04 | 64 |
| 37 | COIN | 994.63 | 64 |
| 38 | PLTR | 990.48 | 64 |
| 39 | PYPL | 976.05 | 64 |
| 40 | ABNB | 931.46 | 64 |
| 41 | MU | 928.05 | 64 |
| 42 | MA | 911.78 | 64 |
| 43 | CSCO | 907.47 | 64 |
| 44 | UBER | 897.01 | 64 |
| 45 | QCOM | 894.76 | 64 |
| 46 | SMCI | 893.10 | 64 |
| 47 | COST | 872.77 | 64 |
| 48 | HD | 867.11 | 64 |
| 49 | BKNG | 832.43 | 64 |
| 50 | WMT | 816.13 | 64 |
| 51 | TSM | 800.47 | 64 |
| 52 | SNOW | 796.19 | 64 |
| 53 | AMAT | 786.73 | 64 |
| 54 | PG | 782.65 | 64 |
| 55 | PEP | 777.25 | 64 |
| 56 | TMO | 768.56 | 64 |
| 57 | TXN | 764.52 | 64 |
| 58 | NKE | 751.14 | 64 |
| 59 | LRCX | 718.20 | 64 |
| 60 | PFE | 708.41 | 64 |
| 61 | NIO | 704.93 | 64 |
| 62 | ASML | 702.82 | 64 |
| 63 | INTU | 692.34 | 64 |
| 64 | VZ | 688.76 | 64 |
| 65 | SHOP | 683.37 | 64 |
| 66 | KO | 673.32 | 64 |
| 67 | MELI | 672.31 | 64 |
| 68 | CAT | 659.65 | 64 |
| 69 | ARKK | 653.47 | 64 |
| 70 | DHR | 651.82 | 64 |
| 71 | GS | 629.08 | 64 |
| 72 | MCD | 627.82 | 64 |
| 73 | ABBV | 623.21 | 64 |
| 74 | RTX | 621.76 | 64 |
| 75 | NOW | 619.63 | 64 |
| 76 | XYZ | 616.47 | 64 |
| 77 | WFC | 612.81 | 64 |
| 78 | MRVL | 603.03 | 64 |
| 79 | DE | 575.52 | 64 |
| 80 | SCHW | 566.01 | 64 |
| 81 | NEE | 564.40 | 64 |
| 82 | ISRG | 562.56 | 64 |
| 83 | AMGN | 561.21 | 64 |
| 84 | T | 552.38 | 64 |
| 85 | MS | 550.63 | 64 |
| 86 | ENPH | 543.93 | 64 |
| 87 | F | 539.59 | 64 |
| 88 | UNP | 537.70 | 64 |
| 89 | SBUX | 536.72 | 64 |
| 90 | OXY | 534.50 | 64 |
| 91 | AI | 523.19 | 64 |
| 92 | CRWD | 522.55 | 64 |
| 93 | MDB | 521.59 | 64 |
| 94 | IBM | 518.64 | 64 |
| 95 | ON | 516.72 | 64 |
| 96 | HON | 510.94 | 64 |
| 97 | CMG | 508.98 | 64 |
| 98 | SLB | 488.34 | 64 |
| 99 | COP | 486.39 | 64 |
| 100 | GE | 483.22 | 64 |
| 101 | LIN | 466.29 | 64 |
| 102 | KLAC | 458.99 | 64 |
| 103 | FDX | 456.43 | 64 |
| 104 | VLO | 453.14 | 64 |
| 105 | MPC | 447.53 | 64 |
| 106 | MARA | 439.69 | 64 |
| 107 | ANET | 437.97 | 64 |
| 108 | GM | 435.40 | 64 |
| 109 | LMT | 432.70 | 64 |
| 110 | MRNA | 427.36 | 64 |
| 111 | ETN | 420.44 | 64 |
| 112 | DDOG | 417.57 | 64 |
| 113 | NXPI | 416.24 | 64 |
| 114 | WDAY | 413.35 | 64 |
| 115 | REGN | 408.44 | 64 |
| 116 | UPST | 406.62 | 64 |
| 117 | FCX | 397.14 | 64 |
| 118 | FTNT | 383.25 | 64 |
| 119 | GILD | 378.82 | 64 |
| 120 | DVN | 375.73 | 64 |
| 121 | DAL | 373.22 | 64 |
| 122 | FSLR | 367.78 | 64 |
| 123 | SNPS | 355.93 | 64 |
| 124 | AMT | 349.59 | 64 |
| 125 | RBLX | 345.54 | 64 |
| 126 | DKNG | 345.30 | 64 |
| 127 | VRTX | 343.09 | 64 |
| 128 | ALB | 334.45 | 64 |
| 129 | CDNS | 328.77 | 64 |
| 130 | SOFI | 322.68 | 64 |
| 131 | ZS | 316.09 | 64 |
| 132 | EOG | 314.06 | 64 |
| 133 | SLV | 312.78 | 64 |
| 134 | PSX | 312.57 | 64 |
| 135 | UAL | 302.36 | 64 |
| 136 | RIOT | 302.31 | 64 |
| 137 | NOC | 297.92 | 64 |
| 138 | NEM | 281.67 | 64 |
| 139 | AFRM | 276.86 | 64 |
| 140 | HAL | 272.95 | 64 |
| 141 | SNAP | 272.10 | 64 |
| 142 | BIIB | 270.64 | 64 |
| 143 | TEAM | 268.60 | 64 |
| 144 | DELL | 265.37 | 64 |
| 145 | EQIX | 264.14 | 64 |
| 146 | ILMN | 261.87 | 64 |
| 147 | LCID | 260.24 | 64 |
| 148 | EXPE | 259.09 | 64 |
| 149 | DLR | 258.11 | 64 |
| 150 | MSTR | 257.42 | 64 |
| 151 | DASH | 255.37 | 64 |
| 152 | FANG | 250.59 | 64 |
| 153 | SHEL | 250.56 | 64 |
| 154 | HUBS | 249.74 | 64 |
| 155 | OKE | 243.04 | 64 |
| 156 | FIS | 241.09 | 64 |
| 157 | NET | 238.68 | 64 |
| 158 | ZM | 237.90 | 64 |
| 159 | BP | 235.66 | 64 |
| 160 | BKR | 232.69 | 64 |
| 161 | AMC | 230.14 | 64 |
| 162 | EBAY | 226.78 | 64 |
| 163 | GD | 223.47 | 64 |
| 164 | EQT | 213.92 | 64 |
| 165 | USO | 213.52 | 64 |
| 166 | GPN | 211.33 | 64 |
| 167 | VRT | 203.48 | 64 |
| 168 | IONQ | 199.54 | 64 |
| 169 | WMB | 184.76 | 64 |
| 170 | KMI | 184.62 | 64 |
| 171 | CEG | 177.14 | 64 |
| 172 | NU | 176.17 | 64 |
| 173 | VEEV | 175.68 | 64 |
| 174 | OKTA | 172.76 | 64 |
| 175 | HPE | 172.15 | 64 |
| 176 | LYFT | 163.20 | 64 |
| 177 | DOCU | 160.55 | 64 |
| 178 | STX | 158.65 | 64 |
| 179 | CCJ | 152.76 | 64 |
| 180 | JBL | 146.92 | 64 |
| 181 | PWR | 142.92 | 64 |
| 182 | VST | 141.82 | 64 |
| 183 | WDC | 140.19 | 64 |
| 184 | ET | 129.94 | 64 |
| 185 | COHR | 128.19 | 64 |
| 186 | PATH | 126.56 | 64 |
| 187 | UNG | 124.99 | 64 |
| 188 | S | 116.53 | 64 |
| 189 | HOOD | 104.08 | 64 |
| 190 | APP | 97.50 | 64 |
| 191 | EPD | 90.67 | 64 |
| 192 | LITE | 76.70 | 64 |
| 193 | CIEN | 73.63 | 64 |
| 194 | OPEN | 72.90 | 64 |
| 195 | EME | 65.34 | 64 |
| 196 | MP | 64.16 | 64 |
| 197 | TTE | 63.19 | 64 |
| 198 | CLSK | 60.18 | 64 |
| 199 | GME | 55.88 | 64 |
| 200 | CRSP | 48.64 | 64 |
| 201 | BE | 48.25 | 64 |
| 202 | BWXT | 40.98 | 64 |
| 203 | SOUN | 40.43 | 64 |
| 204 | APLD | 37.08 | 64 |
| 205 | CLS | 34.47 | 64 |
| 206 | HUT | 33.21 | 64 |
| 207 | RKLB | 29.15 | 64 |
| 208 | UUUU | 17.87 | 64 |
| 209 | DJT | 17.81 | 64 |
| 210 | RGTI | 17.45 | 64 |
| 211 | WULF | 15.79 | 64 |
| 212 | QBTS | 10.37 | 64 |
| 213 | POWL | 9.17 | 64 |
| 214 | OKLO | 8.88 | 64 |
| 215 | IREN | 7.80 | 64 |
| 216 | ASTS | 7.71 | 64 |
| 217 | SMR | 7.33 | 64 |
| 218 | LEU | 7.31 | 64 |
| 219 | PPLT | 7.11 | 64 |
| 220 | BBAI | 5.88 | 64 |
| 221 | CIFR | 5.42 | 64 |
| 222 | TLN | 3.97 | 64 |
| 223 | LUNR | 2.66 | 64 |
| 224 | CPER | 2.20 | 64 |
| 225 | BTDR | 1.19 | 64 |
| 226 | USAR | 0.99 | 54 |
| 227 | ONDS | 0.93 | 64 |
| 228 | SBET | 0.02 | 64 |
| 229 | TSSI | 0.00 | 64 |

### 4.2 Unrankable names (43)

| Symbol | Reason |
|---|---|
| AAVE-USD | crypto_pair |
| ADA-USD | crypto_pair |
| ARB-USD | crypto_pair |
| ARM | thin_history_12bars |
| ASTX | leveraged_etf |
| ATOM-USD | crypto_pair |
| AVAX-USD | crypto_pair |
| BMNR | listed_after_cutoff |
| BNB-USD | crypto_pair |
| BONK-USD | crypto_pair |
| BTC-USD | crypto_pair |
| CORZ | listed_after_cutoff |
| CRWV | listed_after_cutoff |
| CYBR | no_daily_data |
| DOGE-USD | crypto_pair |
| DOT-USD | crypto_pair |
| DRAM | listed_after_cutoff |
| ETH-USD | crypto_pair |
| FET-USD | crypto_pair |
| FIL-USD | crypto_pair |
| GEV | listed_after_cutoff |
| GLXY | listed_after_cutoff |
| HBAR-USD | crypto_pair |
| ICP-USD | crypto_pair |
| INJ-USD | crypto_pair |
| LINK-USD | crypto_pair |
| NBIS | listed_after_cutoff |
| NEAR-USD | crypto_pair |
| NNE | listed_after_cutoff |
| ONDO-USD | crypto_pair |
| RBRK | listed_after_cutoff |
| RDDT | listed_after_cutoff |
| RENDER-USD | crypto_pair |
| SHIB-USD | crypto_pair |
| SNDK | listed_after_cutoff |
| SOL-USD | crypto_pair |
| SPCX | listed_after_cutoff |
| SQ | renamed_XYZ_alias |
| TEM | listed_after_cutoff |
| TRX-USD | crypto_pair |
| UMAC | listed_after_cutoff |
| WIF-USD | crypto_pair |
| XRP-USD | crypto_pair |

## 5. New-listing evaluation (recomputed from the fresh cache)

- Candidates: 15 pool names with first trading day after 2023-09-30, plus ARM (IPO 2023-09-14, 12 window bars).
- Rule: eligible from listing + 30 trading days (31st bar); admitted iff trailing-20-trading-day ADDV
  at eligibility ≥ $25M/day (20 bars ending on the eligibility date; strict PIT).
- **All 15 recomputed trail-20d values match the check target to its 1-decimal rounding;
  admitted/rejected identity sets match exactly.**

| Symbol | First bar | Eligible | Trail-20d ADDV $M/day | Verdict |
|---|---|---|---|---|
| ARM | 2023-09-14 | 2023-10-26 | 288.69 | ADMIT |
| BMNR | 2025-06-05 | 2025-07-21 | 1320.42 | ADMIT |
| CORZ | 2024-01-24 | 2024-03-07 | 14.05 | REJECT |
| CRWV | 2025-03-28 | 2025-05-12 | 360.88 | ADMIT |
| DRAM | 2026-04-02 | 2026-05-15 | 1313.69 | ADMIT |
| GEV | 2024-03-27 | 2024-05-09 | 629.92 | ADMIT |
| GLXY | 2025-05-16 | 2025-07-01 | 132.90 | ADMIT |
| NBIS | 2024-10-21 | 2024-12-03 | 121.87 | ADMIT |
| NNE | 2024-05-08 | 2024-06-21 | 12.86 | REJECT |
| RBRK | 2024-04-25 | 2024-06-07 | 24.55 | REJECT |
| RDDT | 2024-03-21 | 2024-05-03 | 100.65 | ADMIT |
| SNDK | 2025-02-13 | 2025-03-28 | 200.37 | ADMIT |
| SPCX | 2026-06-12 | 2026-07-28 | 10439.81 | ADMIT |
| TEM | 2024-06-14 | 2024-07-30 | 34.93 | ADMIT |
| UMAC | 2024-02-14 | 2024-03-28 | 0.78 | REJECT |

## 6. Gate A verdict

| Invariant | Observed | Verdict |
|---|---|---|
| pool_272_exact | pool=272 | **PASS** |
| rankable_229 | rankable=229 | **PASS** |
| unrankable_43 | unrankable=43 | **PASS** |
| rankable_plus_unrankable_272 | 229+43=272 | **PASS** |
| cutoff_120_identity | #120=DVN $375.7M/day | **PASS** |
| cutoff_120_value | #120 DVN observed $375.73M vs target $375.7M | **PASS** |
| cutoff_121_identity | #121=DAL $373.2M/day | **PASS** |
| cutoff_121_value | #121 DAL observed $373.22M vs target $373.2M | **PASS** |
| listing_candidates_15 | candidates=15: ['ARM', 'BMNR', 'CORZ', 'CRWV', 'DRAM', 'GEV', 'GLXY', 'NBIS', 'NNE', 'RBRK', 'RDDT', 'SNDK', 'SPCX', 'TEM', 'UMAC'] | **PASS** |
| admitted_11_identities_exact | admitted=['ARM', 'BMNR', 'CRWV', 'DRAM', 'GEV', 'GLXY', 'NBIS', 'RDDT', 'SNDK', 'SPCX', 'TEM'] | **PASS** |
| rejected_4_identities_exact | rejected=['CORZ', 'NNE', 'RBRK', 'UMAC'] | **PASS** |

**GATE A: PASS** — all 11 invariant checks pass. No miss; no tuning was performed or needed.

*(Correction, 2026-09-29: an earlier revision of this report said "12 invariant checks."
`gate_a_verdict.json` contains 11 named checks; the ASTX quote-type result is stored
separately in the same JSON, not as a named check. The count is corrected to 11 here.
Substance unchanged — all checks pass.)*

Key corroborating values (independent recomputation vs documented):
- #120 DVN $375.73M/day (doc $375.7M), #121 DAL $373.22M/day (doc $373.2M)
- RBRK trail-20d $24.55M — just under the $25M gate (doc $24.5M); CORZ $14.05M; NNE $12.86M; UMAC $0.78M
- ARM admitted at $288.69M trail-20d (doc $288.7M)

## 7. Data-availability / drift findings

1. **CYBR permanently missing** from yfinance (acquired 2025) — documented in UNIVERSE.md; reproduced.
   Not in the universe (no data to rank). Needs a survivorship-inclusive vendor to include.
2. **SQ serves no data under the old ticker**; XYZ serves the full SQ-era history (832 bars from 2023-06-01).
   Handled per the UNIVERSE.md corporate-action table.
3. **Yahoo daily path healthy** at fetch time (2026-09-29 ~17:18–17:20 ET): 270/272 symbols on first clean
   pass, no 429s, no throttling. (The ~16:41 ET incident was the 1H/intraday path; the daily path tested fine
   at ~17:15 ET and again here.)
4. **Batch-union calendar padding** (methodology note): yfinance batch downloads align all tickers on the union
   of dates, so crypto pairs' 24/7 calendar pads stock symbols in the same batch with NaN-OHLC weekend rows.
   The first fetch kept them (1212-row frames); caught in review, fixed with a `dropna` on OHLC, and the full
   cache was re-fetched clean. No padded rows exist in the committed cache.
5. **No data drift vs the documented baseline**: the independent ADDV recomputation matches the documented
   ranking to 4.5e-08 relative and all 15 listing-eval values to the documented rounding — Yahoo's current
   daily history for this window is consistent with the 2026-09-24/25 baseline build.

## 8. Reproducibility

- `canonical_stage_a/fetch_daily.py` — daily cache rebuild (own code, §11 recipe).
- `canonical_stage_a/analyze_stage_a.py` — ranking, listing eval, Gate A (own code).
- `canonical_stage_a/tree_pool_extraction.json` — pinned-tree extraction record (`/tmp/tree_pool.json` copy).
- `canonical_stage_a/data/d1_*.json` — 270 deterministic per-symbol caches.
- `canonical_stage_a/fetch_manifest.json` — per-symbol SHA-256 + fetch timestamps.
- `canonical_stage_a/addv_ranking_recomputed.json`, `addv_unrankable_recomputed.json`,
  `canonical_stage_a/new_listings_eval_recomputed.json`, `canonical_stage_a/gate_a_verdict.json`.

Stage A is complete. Stage B (regenerate `universe.json`: top-120 + 11 admitted listings) is unblocked
but NOT started — it awaits the parent's go-ahead per the staged plan.
