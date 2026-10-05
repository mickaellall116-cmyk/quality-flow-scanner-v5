# CP1 Follow-up: Findings and Unknowns
**Date:** 2026-10-05 | **Branch:** `recovery-4h-20261004`
**Responds to:** ChatGPT bounded assignment, Issue #1 comment 5986944792
**Scope:** FORENSIC EVIDENCE COLLECTION ONLY. No corrected performance computed or opened.

Evidence tags: COMPUTED (derived by audit code in this package), SOURCE/CODE VERIFIED
(confirmed against repo source), REPRODUCED (independently re-derived a prior claim),
UNRESOLVED (cannot be determined from retained evidence; no guessing).

---

## Task 1 — Cache provenance

| Finding | Tag |
|---|---|
| 52 h4 files created 2026-09-15 14:49–15:06 UTC, sequential mtimes (~1.5s/file, interleaved symbols — scripted loop, not batched by symbol group) | COMPUTED |
| Byte features (13:30/17:30 UTC grid, SessionVWAP column, `last_bar_*` attrs, forming-bar exclusion) match legacy `resample_closed_4h` (`scanner_rules.py`, `origin="start_day"`, `offset="9h30min"`) on every feature | SOURCE/CODE VERIFIED |
| No committed script writes to `backtest_cache/v3/`; cache files never committed to git; no build logs or shell history retained | COMPUTED |
| Searched: all `*.py` referencing `backtest_cache/v3` (14 files — all readers, no writers), git history (no record), filesystem for `*.log` (none) | COMPUTED |
| Exact invoking script/session: **UNRESOLVED** — permanent provenance gap (confirmed by deeper search; rev-2 conclusion stands) | UNRESOLVED |

## Task 2 — Full 52-symbol audit

| Finding | Tag |
|---|---|
| All 52 files: monotonic increasing indexes, zero duplicate timestamps | COMPUTED |
| Index tz: America/New_York (equities), UTC (crypto) | COMPUTED |
| Equities: 45 files; 23 with 995 bars, 22 with 993 bars | COMPUTED |
| The 22 with 993 bars are missing exactly 2026-01-30 12:30-05:00 and 2026-02-02 08:30-05:00 — both normal XNYS trading days (Fri/Mon), so these are unexplained data gaps, not scheduled closures | COMPUTED (calendar: XNYS via pandas_market_calendars 5.5.0) |
| 22-symbol mtimes interleaved with others — not a separate download batch; cause of the 2-bar gap is UNRESOLVED (underlying 1H data transient) | COMPUTED / UNRESOLVED |
| Crypto: 6 of 7 on 00/04/08/12/16/20 UTC grid with 12 missing (3 leading partial-day + 3 trailing partial-day + 6 mid-history Yahoo gaps on 2025-10-28 and 2025-11-29) | COMPUTED |
| SOL-USD: 40 missing / 2 extra vs BTC grid — REPRODUCED Claude's finding exactly. Missing in 4 clusters (Nov 2025: 31 bars ≈5 days; Dec 2025: 1; May 2026: 3; Jul 2026: 5). Extras at 2025-10-28 04:00/08:00 UTC (timestamps where BTC has the gap but SOL has bars) | REPRODUCED |
| Start dates: 45 equities 2024-09-16, 7 crypto 2024-09-15 (Sunday — crypto trades 24/7). Consistent; no anomaly | COMPUTED |
| QQQ is the 52nd file, created in the same Sep-15 batch (first alphabetically, 14:49:14) | COMPUTED |

## Task 3 — Trade intersection

| Finding | Tag |
|---|---|
| 82/240 trades entered during EST shifted-regime periods — matches prior finding | REPRODUCED |
| T145 PFE (2026-01-14 → 2026-02-03): holding interval contains BOTH gap timestamps | COMPUTED |
| T146 GOOGL (2026-01-21 → 2026-02-05): holding interval contains BOTH gap timestamps | COMPUTED |
| 12 SOL trades enumerated; only T192 (2026-05-07 → 2026-05-12) intersects a SOL outage window (SOL-GAP3) | COMPUTED |
| **Temporal overlap alone is NOT proof of performance impact** — stated plainly; causal effect on P&L is UNRESOLVED | UNRESOLVED |

## Task 4 — Price-window question (label-only vs different aggregation)

| Finding | Tag |
|---|---|
| Original Sep-15 1H inputs: NOT retained (transient Yahoo downloads). `pine_1h/cache/` holds 10 symbols from a Sep-18 study — a different retrospective snapshot, not the original inputs | COMPUTED |
| Per ChatGPT's correction: whether winter bars are label-shifted (same values) or value-shifted (different hourly windows aggregated) is **UNRESOLVED** without original 1H inputs | UNRESOLVED |
| No new data fetched for this task. No silent substitution performed | COMPUTED (process) |
| What would resolve it: original 1H bars for any EST date, re-aggregated under both candidate windows and compared to cached h4 OHLCV | UNRESOLVED (evidence requirement stated) |

## Task 5 — QQQ / coverage start / skip labels

| Finding | Tag |
|---|---|
| QQQ: 0 trades in the 240-trade ledger; not in the ledger's `cache_symbols` list (51 symbols). Cached in the same Sep-15 batch but excluded from the traded universe. Reason for its inclusion in the generator's list: UNRESOLVED. No QQQ trade/admission contamination: VERIFIED | COMPUTED / UNRESOLVED |
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
