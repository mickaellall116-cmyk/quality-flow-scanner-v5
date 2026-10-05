# CP1 Follow-up: Findings and Unknowns — REV 2 (targeted corrections)
**Date:** 2026-10-05 | **Branch:** `recovery-4h-20261004`
**Responds to:** ChatGPT bounded assignment (Issue #1 comment 5986944792) +
targeted corrections (Issue #1 comment 5994294209)
**Scope:** FORENSIC EVIDENCE COLLECTION ONLY. No corrected performance computed or opened.

Evidence tags: COMPUTED (derived by audit code in this package), SOURCE/CODE VERIFIED
(confirmed against repo source), REPRODUCED (independently re-derived a prior claim),
UNRESOLVED (cannot be determined from retained evidence; no guessing).

---

## Correction delta (rev2 vs rev1)

| # | What changed | What was preserved | What remains UNRESOLVED |
|---|---|---|---|
| A | 82-count split: **51 equity** shifted-regime entries (defect exposure) + **31 crypto** EST-calendar entries (calendar membership only, NOT a defect) | Superseded 82-count preserved with correction note in `trade_intersection.json` | Whether any individual trade's P&L was affected |
| A | Crypto trades no longer flagged as DST-defect exposure | The 31 crypto entries still enumerated (calendar membership) | — |
| B | Grid comparator rewritten: per-day session-slot analysis using `market_open`/`market_close`; missing classified as scheduled_closure / scheduled_truncation / coverage / label_mapping / true_absent | 22-symbol gap evidence preserved exactly (44 absent slots) | Cause of the 44 absent slots |
| B | 225 early-close truncations now properly classified (were conflated into "missing") | 14,986 shifted-slot count matches prior off-grid count exactly | — |
| C | Gap tables derived from pinned audit (`audit_52symbol.json`), not hard-coded; signal-regime flags added; all 240 rows validated | T145 PFE / T146 GOOGL gap intersections preserved | — |
| C | **T192 SOL intersection WITHDRAWN**: prior claim used hard-coded May 11–12 envelope; derived exact timestamps show May gaps on 2026-05-05, outside T192's interval. **Zero SOL trades intersect exact derived gaps.** | The 40 SOL-specific missing timestamps (Claude's finding reproduced) | — |
| D | Full SHA-256 manifest added (`FULL_MANIFEST.json`): package files, source files, inputs | Cache hashes (unchanged, pinned before inspection) | — |
| D | Provenance search evidence added (`PROVENANCE_SEARCH.md`): 13 scripts classified, zero writers found, git/filesystem searches documented | — | Exact invoking script (permanent gap) |
| D | Builder claim qualified: feature-signature compatibility, NOT byte-equality reproduction | Mechanism identification (legacy `resample_closed_4h`) | Byte-equality proof (needs original 1H inputs) |
| D | **QQQ upgraded to SOURCE/CODE VERIFIED**: `load_bull()` iterates `pb.UNIVERSE_X` (51 symbols); QQQ not in the list, so its cache file is never loaded — cannot influence ranking/admission | QQQ has 0 trades (still true) | Reason QQQ's file was generated in the batch |

---

## Task 1 — Cache provenance (REV 2 qualified)

| Finding | Tag |
|---|---|
| 52 h4 files created 2026-09-15 14:49–15:06 UTC, sequential mtimes (~1.5s/file, interleaved symbols — scripted loop, not batched by symbol group) | COMPUTED |
| Byte features (13:30/17:30 UTC grid, SessionVWAP column, `last_bar_*` attrs, forming-bar exclusion) match legacy `resample_closed_4h` (`scanner_rules.py`, `origin="start_day"`, `offset="9h30min"`) on every feature — **feature-signature compatibility** | SOURCE/CODE VERIFIED |
| **Qualification:** signature compatibility is NOT byte-equality reproduction. Original 1H inputs not retained; the legacy function has not been re-run and compared byte-for-byte. Builder = identified mechanism, exact builder unproven. | UNRESOLVED (byte equality) |
| 13 scripts reference `backtest_cache/v3`; zero write h4 files to that path (all readers/documenters). Git has no cache-file history. No build logs retained. Full search evidence: `PROVENANCE_SEARCH.md` | COMPUTED |
| Exact invoking script/session: **UNRESOLVED** — permanent provenance gap | UNRESOLVED |

## Task 2 — Full 52-symbol audit (REV 2 corrected comparator)

| Finding | Tag |
|---|---|
| All 52 files: monotonic increasing indexes, zero duplicate timestamps | COMPUTED |
| Index tz: America/New_York (equities), UTC (crypto) | COMPUTED |
| Equity slot analysis (45 files): 29,745 present_correct + 14,986 present_shifted + 44 absent_true + 225 scheduled_trunc | COMPUTED (calendar: XNYS via pandas_market_calendars 5.5.0, market_open/market_close consulted) |
| 14,986 shifted slots = the DST fixed-UTC-grid defect scope (matches prior off-grid count exactly) | COMPUTED |
| 44 absent_true slots across exactly 22 symbols (2 each: 2026-01-30 afternoon + 2026-02-02 morning) — the preserved gap evidence; both normal XNYS full trading days | COMPUTED |
| 225 scheduled_trunc slots (early closes) — now properly classified, not conflated with gaps | COMPUTED |
| Crypto: 6 of 7 on 00/04/08/12/16/20 UTC grid | COMPUTED |
| SOL-USD: 40 SOL-specific missing timestamps (vs BTC grid) — REPRODUCED Claude's finding exactly. Exact clusters from raw cache: Nov 17–21 2025 (24 bars), Nov 29–Dec 1 2025 (12 bars), May 5 2026 (3 bars), Jul 13 2026 (5 bars), plus 3 leading-coverage bars Sep 15 2024. Nov 17–21 confirmed SOL-specific (BTC/ETH have all 30 bars) | REPRODUCED / COMPUTED |
| Start dates: 45 equities 2024-09-16, 7 crypto 2024-09-15. Consistent; no anomaly | COMPUTED |
| QQQ is the 52nd file, created in the same Sep-15 batch | COMPUTED |

## Task 3 — Trade intersection (REV 2 corrected)

| Finding | Tag |
|---|---|
| **51 equity** trades entered during EST shifted-regime periods (defect exposure) | COMPUTED |
| **31 crypto** trades entered during EST calendar periods (calendar membership only — crypto UTC grid has no DST shift; NOT defect exposure) | COMPUTED |
| Superseded rev1 82-count preserved with correction note in `trade_intersection.json` | COMPUTED (process) |
| T145 PFE (2026-01-14 → 2026-02-03): holding interval contains BOTH derived gap slots | COMPUTED |
| T146 GOOGL (2026-01-21 → 2026-02-05): holding interval contains BOTH derived gap slots | COMPUTED |
| 12 SOL trades enumerated against derived exact gap timestamps; **zero intersect**. Prior T192 claim WITHDRAWN (was based on hard-coded May 11–12 envelope; exact gaps are May 5, outside T192's interval) | COMPUTED |
| Gap tables derived from pinned `audit_52symbol.json`, not hard-coded; signal-regime flags added; all 240 rows validated against pinned ledger | COMPUTED (process) |
| **Temporal overlap alone is NOT proof of performance impact** — stated plainly; causal effect on P&L is UNRESOLVED | UNRESOLVED |

## Task 4 — Price-window question (label-only vs different aggregation)

| Finding | Tag |
|---|---|
| Original Sep-15 1H inputs: NOT retained (transient Yahoo downloads). `pine_1h/cache/` holds 10 symbols from a Sep-18 study — a different retrospective snapshot, not the original inputs | COMPUTED |
| Per ChatGPT's correction: whether winter bars are label-shifted (same values) or value-shifted (different hourly windows aggregated) is **UNRESOLVED** without original 1H inputs | UNRESOLVED |
| No new data fetched for this task. No silent substitution performed | COMPUTED (process) |
| What would resolve it: original 1H bars for any EST date, re-aggregated under both candidate windows and compared to cached h4 OHLCV | UNRESOLVED (evidence requirement stated) |

## Task 5 — QQQ / coverage start / skip labels (REV 2)

| Finding | Tag |
|---|---|
| **QQQ loader-path exclusion: SOURCE/CODE VERIFIED.** `load_bull()` in `pine_stack/pine_stack.py` iterates `pb.UNIVERSE_X` (51 symbols) and loads `h4_{sym}.pkl` per symbol. QQQ is NOT in `UNIVERSE_X`; its cache file is never loaded. QQQ cannot influence ranking, admission, or any portfolio decision — demonstrated via the loader code path, not merely inferred from zero trades. | SOURCE/CODE VERIFIED |
| QQQ: 0 trades in the 240-trade ledger; not in the ledger's `cache_symbols` list (51 symbols). Cached in the same Sep-15 batch but excluded from the traded universe. Reason for its inclusion in the generator's list: UNRESOLVED. | COMPUTED / UNRESOLVED |
| Coverage start Sep-2024 vs "intended 2023": the baseline's own provenance declares "UX51 4H 2024-09-16 -> 2026-09-14" as the universe window — observed start matches the declared window. The 2023 intention (if from an earlier spec) is not documented in the baseline's provenance | SOURCE/CODE VERIFIED |
| Skip tallies (`rank_cap: 528, max_positions: 0, sector_cap: 74, portfolio_risk: 35, gap_below_stop: 2`): documented in ledger provenance; exact code-path mapping requires the original generation code | COMPUTED (as stated) |
| Baseline provenance explicitly documents the UTC grid as "a documented property of the study data (caveat, not re-cut)" — the builders knew about the grid at baseline build time | SOURCE/CODE VERIFIED |

## Task 6 — Decision traces

| Finding | Tag |
|---|---|
| Every trade in the ledger carries a full `decision_trace` (entry_bar, contenders, contested flag, RS rank, slots, sector, portfolio risk, sizing) — preserved verbatim in the CP1 bundle | SOURCE/CODE VERIFIED |
| No price/exit effect claims are made in this package; therefore no effect traces are required. Any future effect claim must cite these traces | COMPUTED (process) |

---

## Superseded inference (per ChatGPT correction)

The prior bridge statement that the grid issue is "not merely a label issue" is **preserved in history and marked SUPERSEDED** on this specific inference. The CP1 evidence establishes shifted timestamp regimes; without original input/value evidence and actual builder provenance, label-only versus different price-window aggregation remains UNRESOLVED (Task 4).
