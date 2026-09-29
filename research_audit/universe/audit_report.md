# Universe Integrity & Survivorship-Bias Audit — 14-stock research universe

Date: 2026-09-24. Auditor role: verify, don't research. Nothing modified outside this folder.
Reproduction script: `universe_bias_quant.py` (this folder). It imports `pine_backtest.py` unmodified
and reproduces the reported baseline exactly (237 trades, +0.2388R @25bps).

## Verdicts

| Check | Verdict |
|---|---|
| 1. Universe integrity (was the 14-name list knowable before the test period?) | **FAIL** |
| 2. Survivorship bias (dead/delisted names in or dropped from research) | **WARNING** (narrow question passes: no deaths, no drops; pipeline can't see dead names, latent bias remains) |

## 1. Universe integrity — FAIL

**How the 14 were chosen.** They are Mike's personal live-trading watchlist, assembled
September 2026 — i.e., with full knowledge of the Oct 2023–Sep 2026 test period — and then
reused verbatim as the backtest universe by all six study folders
(`pine_lonewolf_protocol`, `pine_adx_protocol`, `pine_fvg_protocol`,
`pine_ranking_confirm`, `pine_fvg_attribution`, `pine_lonewolf_confirm`).

File evidence:
- `signal_log/watchlist.txt` lines 1–5 (the file the studies copied): *"these are Mike's
  actively-watched tickers, NOT the paper engine's validation universe."* The studies used it
  as the validation universe anyway. Every study hardcodes the same list, e.g.
  `pine_lonewolf_protocol/run_protocol.py:29-30`,
  `pine_adx_protocol/run_selection_edge.py:21`,
  `pine_adx_protocol/run_addendum.py:15`; study HYPOTHESIS files say only
  "Symbols: the 14-name watchlist" with no construction rationale
  (`pine_lonewolf_protocol/HYPOTHESIS.md:37`, `pine_fvg_protocol/HYPOTHESIS.md:30`).
- The list changed *during* the research window: `git diff 2010819 HEAD --
  signal_log/watchlist.txt` shows it was created 2026-09-20 with 4 names
  (QQQ, SMCI, PLTR, ANET) and grew to 14 (added SOFI, RKLB, ONDS, DRAM, SPCX, ASTX,
  BBAI, NIO, HOOD, AMD) by 2026-09-24 — the exact days the studies ran.
- Selection mechanism is interest-after-momentum: names enter because Mike is watching
  them now — YouTube-discovered rotation names (IREN, Bloom Energy per research notes),
  his own positions (DRAM 26 sh @ $56.45; SMCI 87 sh @ $34.80), names he tapped "Watch"
  on after A-grade signals fired, and names added at his explicit request
  (HOOD/AMD 2026-09-20; MP/USAR; TSSI 2026-09-24). The rotation list itself
  (`~/workspace/.jarvis/idea-executions/9387c7ed-6b93-466b-be08-ae28794db796/scratch/rotation_watch.py:19-41`)
  is 21 hand-picked momentum names.
- **Picked because they ran:** the baseline's entire edge sits in four names —
  RKLB (+19.94R), PLTR (+14.13R), HOOD (+13.32R), ONDS (+10.56R) = +57.95R, i.e.
  **102.4% of the total +56.57R**; the other 10 names net −1.38R. All four are
  2024–2025 mega-runners (RKLB ~$4→$30s, PLTR's AI run, HOOD's 2024–25 run) that
  entered Mike's attention *after* those moves. Full per-symbol table in the appendix.

**Three of the 14 aren't even full-period instruments** (data from
`pine_entry_timing_backtest/cache/h4_*.pkl`, verified live via yfinance):
- DRAM = **Roundhill Memory ETF** (BATS), listed **2026-04-02** — 240 bars, 0 trades in baseline.
- SPCX = **Space Exploration Technologies Corp. (SpaceX)** (NMS), IPO **2026-06-12** — 142 bars, 0 trades. (Note: ticker *reuse* — the old SPCX SPAC ETF was liquidated Aug 2022.)
- ASTX = **Tradr 2X Long ASTS Daily ETF** (BATS), listed **2025-07-11** — 604 bars, 5 trades @ −0.69R. A 2x daily-reset leveraged ETF, not a stock.
- The other 11 have full 1453-bar history from 2023-10-25.

So the "+0.2388R over 237 trades" baseline is effectively an 11-name backtest whose
result is 100%+ carried by 4 hindsight-picked runners, plus 3 names that could not
have been known before 2025–2026.

## 2. Survivorship bias — WARNING

- **No dead names, no silent drops in the studies.** All 14 still trade. The six study
  folders reference only these 14 symbols (plus sector benchmark ETFs) — verified by
  ticker scan. Study code does `pd.read_pickle(...)` with no try/except
  (e.g. `pine_lonewolf_protocol/run_protocol.py:145-156`): a missing symbol would
  crash, not silently vanish. The broader historical lists (`UNIVERSE_15`/`UNIVERSE_X`
  in `pine_backtest.py:41-50`, identical in `backtest_v2.py:44`, `hybrid_exit_test.py:39`)
  show no removals; they were uploaded without git history so pre-upload edits can't
  be checked — stated as a limit, not a finding.
- **But the pipeline is structurally blind to failures.** Data is fetched by *current*
  ticker (`pine_entry_timing_backtest/fetch_resample_4h.py:19-43`); a name that died
  mid-period would simply never be fetched, and nothing in the research flow would flag
  it. The one place a dead name surfaced — `v54_universe_x2.py` docstring: CYBR
  (acquired/delisted 2025) was "dropped — no usable data" — was for the *forward*
  test, not historical research, so it doesn't bias the backtests; it does prove the
  failure mode exists and is handled by exclusion.
- Composition note: 2 of the 14 are ETFs (DRAM, ASTX — ASTX 2x leveraged) and 1 is an
  index ETF (QQQ); calling it a "14-stock" universe overstates its stock content.

## 3. Quantified impact on the +0.2388R baseline

**Selection bias (the big one).** Apples-to-apples comparison, same window
(2024-09-16→2026-09-14) and cost (4bps), canonical backtester unmodified:
- 14-stock hand-picked universe: **+0.3523R** (195 trades).
- Median of 20,000 random 14-name draws from the 51-symbol UX51 universe: **+0.1640R**
  (p90 +0.545, p95 +0.649).
- Implied selection lift: **≈ +0.19R** — the hand-picked list sits near the 80th
  percentile of random draws, and UX51 is itself a Mike-selected list, so this is a
  *lower bound* on the true hindsight lift.
- Translating to the reported cost (25bps ≈ −0.05R vs 4bps on this universe):
  reported **+0.2388R** → selection-neutral estimate **≈ +0.05R to +0.12R**.
  Sanity anchor: the full 51-symbol UX51 run at 25bps is +0.115R
  (`pine_backtest_results.json`), right in that band.

**Survivorship bias (classic).** Direct effect ≈ 0 (no deaths in the 14). Latent
effect: literature (Brown–Goetzmann–Ross and follow-ups) puts survivorship inflation
for US equity samples at roughly 1–2%/yr of return; mapped loosely onto this
expectancy that is **≈ +0.01 to +0.03R, and this is an estimate, not a measurement** —
the honest statement is that the pipeline cannot observe the names it would have
excluded.

**Bottom line:** roughly **half of the +0.2388R baseline (≈ +0.12 to +0.19R) is
universe-selection artifact**, not strategy edge. The defensible baseline for the
strategy on a neutral universe is on the order of **+0.05 to +0.12R @25bps**.
Every study delta computed against +0.2388R (lone-wolf +0.108R, ADX +0.154R vs rs_top2,
FVG attributions, etc.) inherits this inflated denominator — the *deltas* are less
affected than the baseline level, but any "expectancy > X" gate calibrated to 0.2388R
is miscalibrated.

## 4. Point-in-time universe proposal (concrete)

1. **Fix the universe on 2023-09-30** (one month before the 2023-10-25 test start),
   by rule not by hand: all NASDAQ-100 constituents on that date, or top-300 names by
   trailing-90-day median dollar volume as of 2023-09-30. Write the rule and the
   resulting list to `research_notes/UNIVERSE.md` with the construction date.
2. **Keep the dead.** Names delisted/acquired mid-period stay in the data through
   their last trading day; their trades count. Fetch delisted histories once from a
   survivorship-inclusive source (e.g. Norgate, CRSP-style vendor, or Stooq
   delisted archives) — yfinance-by-current-ticker is not acceptable for the
   historical universe.
3. **New listings enter only from their listing date**, require ≥60 4H bars before
   generating signals, and are never backfilled.
4. **Corporate-action table**: ticker changes mapped (e.g. SQ→XYZ); ticker *reuse*
   (old SPCX vs SpaceX SPCX) treated as distinct instruments keyed by listing date.
5. **Separate the live watchlist.** Mike's 14-name list stays as a reporting *overlay*:
   always report the neutral-universe baseline first, then the watchlist subset —
   never the watchlist alone. A study whose verdict depends on the watchlist-only
   number does not pass.
6. **Recompute the baseline once** on the point-in-time universe before the
   ~50-signal checkpoint (late Oct 2026); keep V5.4 frozen — this changes the
   measuring stick, not the system.

## Appendix — per-symbol baseline reconstruction (@25bps, canonical `pine_backtest`, unmodified)

| sym | n | mean R | sum R | history start |
|---|---|---|---|---|
| RKLB | 25 | +0.7974 | +19.94 | 2023-10-25 |
| PLTR | 20 | +0.7065 | +14.13 | 2023-10-25 |
| HOOD | 22 | +0.6056 | +13.32 | 2023-10-25 |
| ONDS | 16 | +0.6600 | +10.56 | 2023-10-25 |
| BBAI | 17 | +0.3173 | +5.39 | 2023-10-25 |
| SOFI | 24 | +0.1597 | +3.83 | 2023-10-25 |
| AMD | 23 | +0.1970 | +4.53 | 2023-10-25 |
| NIO | 12 | +0.1346 | +1.61 | 2023-10-25 |
| ANET | 25 | −0.1057 | −2.64 | 2023-10-25 |
| QQQ | 29 | −0.1633 | −4.74 | 2023-10-25 |
| SMCI | 19 | −0.3109 | −5.91 | 2023-10-25 |
| ASTX | 5 | −0.6892 | −3.45 | **2025-07-11** (2x ASTS ETF) |
| DRAM | 0 | — | 0.00 | **2026-04-02** (Memory ETF) |
| SPCX | 0 | — | 0.00 | **2026-06-12** (SpaceX IPO) |
| **total** | **237** | **+0.2388** | **+56.57** | |

Excluding the 3 truncated names: 232 trades, +0.2588R (ASTX was a small drag; DRAM/SPCX
contribute nothing — their inclusion flatters the *narrative* of a 14-name universe,
not the number).
