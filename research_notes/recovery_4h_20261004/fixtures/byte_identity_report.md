# Phase A — 4H Fixtures & Byte-Identity Report

**Date:** 2026-10-04 | **Branch:** `recovery-4h-20261004`
**Target:** `scanner_rules.resample_closed_4h_session_anchored` (candidate canonical 4H constructor)
**Fixture module:** `research_notes/recovery_4h_20261004/fixtures/test_4h_fixtures.py`
**Raw results:** `research_notes/recovery_4h_20261004/fixtures/phase_a_results.json`

Constraints honored: synthetic data only (no network); the only real data read
was the existing local `backtest_cache/v3/h4_*.pkl` for comparison (b). No
production code modified — test-only files. No performance data.

---

## Task 1 — DST/session fixtures: 11/11 PASS

All fixtures build synthetic tz-aware 1H OHLCV (deterministic: Open=base+i,
High=Open+0.6, Low=Open−0.4, Close=Open+0.2, Volume=1000+i·10 int64) and assert
exact bar-start timestamps, OHLCV values, bar counts, and (where applicable)
`last_bar_*` attrs.

| # | Fixture | Result |
|---|---------|--------|
| 1 | Spring-forward DST (2026-03-08): Fri 2026-03-06 (EST) + Mon 2026-03-09 (EDT) → bars at 09:30/13:30 wall-clock both days | PASS |
| 2 | Fall-back DST (2026-11-01): Fri 2026-10-30 (EDT) + Mon 2026-11-02 (EST) → same | PASS |
| 3 | Normal day → exactly 2 bars (09:30, 13:30), OHLCV = first/max/min/last/sum; SessionVWAP spot-checked; attrs `last_bar_close_at=2026-10-02T16:00:00-04:00` | PASS |
| 4 | Half-day 2026-11-27 (13:00 XNYS close) → exactly 1 bar; `last_bar_close_at=2026-11-27T13:00:00-05:00` | PASS |
| 5 | Holiday 2026-12-25 (Friday, closed) → zero bars, empty frame | PASS |
| 6 | 5-day week (2026-10-05…09) → 10 bars; both slots present every day | PASS |
| 7 | Missing 11:30/12:30 rows → bars correct from present rows only, no forward-fill | PASS |
| 8 | `now`=15:00 ET (inside afternoon bar) → only morning bar returned | PASS |
| 9 | Future-row truncation: `anchored(full, now) == anchored(truncated@now, now)` | PASS |
| 10 | Row stamped exactly 13:30 → afternoon bar (closed-left) | PASS |
| 11 | Crypto `BTC-USD` → 00/04/08/12/16/20 UTC bins; no SessionVWAP column | PASS |

Fixture 9 note (documented in the fixture docstring): with the forming-bar
exclusion in place, the causal cutoff can never change a *returned closed* bar
(any bin holding a post-`now` row is forming and dropped regardless), so the
fixture asserts the truncation code path as an equivalence invariant —
defense-in-depth, verified, not observable in outputs by design.

---

## Task 2 — byte-identity proofs

### (a) Session-anchored vs per-day-origin `resample_4h` (fetch_4h.py) — IDENTICAL OHLCV + index

- **Input:** identical synthetic 1H, 10 business days 2026-08-24…2026-09-04,
  7 rows/day, tz-aware America/New_York, `now=2026-09-05T12:00-04:00` (all bars
  closed, so the anchored path's forming-bar exclusion is a no-op).
- **Input hash (sha256):** `1c21972945071ce57c75db62f7e727670bf903c57527e262ac0efe9755c9c49b`
- **Result:** 20 bars vs 20 bars; `pd.testing.assert_frame_equal` on
  Open/High/Low/Close/Volume + index with `check_exact=True` → **byte-identical**.
- **Documented deltas (schema/metadata only, zero OHLCV/index impact):**
  1. `SessionVWAP` column exists only on the session-anchored side
     (fetch_4h never computes it).
  2. `last_bar_start_at` / `last_bar_close_at` attrs set only by
     session-anchored (`2026-09-04T13:30:00-04:00` / `2026-09-04T16:00:00-04:00`);
     fetch_4h sets no attrs.
  3. Known non-firing semantic deltas on this complete input: fetch_4h drops
     only NaN-Close rows (anchored requires all of OHLC — no NaNs here);
     fetch_4h has no forming-bar exclusion and no causal cutoff (all bars
     closed here).
- The fetch_4h `resample_4h` was loaded via AST extraction (test-only) to avoid
  importing the script's module-level fetch/network code.

### (b) Session-anchored grid vs `backtest_cache/v3/h4_*.pkl` — DELTA FOUND (grid defect in cache)

**Verdict: NOT on the session-anchored grid.** The cached AAPL bars sit on a
**fixed-UTC grid (13:30 / 17:30 UTC)** — the legacy `origin='start_day'` defect
class — not on the per-day session grid. This also contradicts the premise that
the cache was built by `fetch_4h.py`'s `resample_4h`: that function groups
per-day with a per-day 09:30 origin (DST-invariant wall-clock labels) and
produces **no** SessionVWAP column and **no** attrs, whereas the cache **has**
both. The cache's grid is consistent with the legacy `resample_closed_4h`
(origin='start_day', offset 9h30min) construction.

Evidence (`h4_AAPL.pkl`, 993 bars, 2024-09-16 → 2026-09-14):

| Regime (NY wall-clock labels) | Dates | Bars |
|---|---|---|
| 09:30 / 13:30 (EDT) | 2024-09-16…2024-11-01, 2025-03-10…2025-10-31, 2026-03-09…2026-09-14 | 661 |
| 08:30 / 12:30 (EST, **−1h wall-clock shift**) | 2024-11-04…2025-03-07, 2025-11-03…2026-03-06 | 332 |

- Every one of the 993 bars is at exactly 13:30 or 17:30 UTC — bins are UTC-fixed.
- During EDT the labels coincide with the session grid (09:30/13:30) and the
  bins coincide in content with the session-anchored bins; during EST the
  wall-clock labels shift to 08:30/12:30 and the "morning" bin
  ([13:30,17:30) UTC = [08:30,12:30) EST) covers a different hour set than the
  session morning bin ([09:30,13:30) EST).
- Early-close days correctly show a single morning bar (2024-11-29, 2024-12-24,
  2025-07-03, 2025-11-28, 2025-12-24).
- Two single-bar anomalies consistent with missing upstream 1H rows (not grid
  defects): 2026-01-30 has only the morning-labeled bar; 2026-02-02 has only
  the afternoon-labeled bar (volumes normal, ~19–20M).
- `h4_BTC-USD.pkl` (4374 bars): all bars on exactly 00/04/08/12/16/20 UTC —
  **crypto grid aligned**, no delta (25-hour/23-hour UTC days at DST
  transitions handled correctly).

**Implication:** any replay that needs bar-for-bar parity with
`backtest_cache/v3/h4_*.pkl` during EST periods must account for the −1h
wall-clock label shift and the shifted morning bin. The cache is **not** a
valid reference for the session-anchored grid in EST months.

### (c) Window-invariance: 30d vs 180d through session-anchored — BYTE-IDENTICAL

- **Input:** synthetic 1H business days; 180d window ending 2026-09-30 vs the
  last 30d of the same window (identical rows on overlapping dates by
  construction), `now=2026-10-01T12:00-04:00`.
- **Input hashes (sha256):** 180d
  `e24120804e57c8fe03d2a2ae75d2bf4c6d3098d3aa8dd209355ab669e6f3245b`;
  30d `d09f592bd136d2f68a4528c9226342c30232530d40c814abc2b5fa49e75aeba5`
  (hashes differ because the inputs differ in length — the overlapping
  *dates* carry identical rows).
- **Result:** all 60 overlapping bars **byte-identical** (OHLCV + index +
  SessionVWAP + attrs), `check_exact=True`. **Window-invariance proven** — the
  legacy `origin='start_day'` window-length defect does not exist in the
  session-anchored path.

---

## Summary

- Fixtures: **11/11 PASS** (also `pytest`: 11 passed).
- (a) Session-anchored ≡ fetch_4h per-day-origin on OHLCV+index; deltas are
  SessionVWAP column + `last_bar_*` attrs only.
- (b) `backtest_cache/v3/h4_AAPL.pkl` is on a **fixed-UTC legacy grid**
  (13:30/17:30 UTC; 332 bars mislabeled 08:30/12:30 during EST) — **not**
  session-anchored-grid-compatible in EST months. Crypto cache aligned.
- (c) 30d vs 180d windows → byte-identical bars; window-invariance holds.

## Files

- [test_4h_fixtures.py](sandbox://workspace/quality-flow-scanner-v5/research_notes/recovery_4h_20261004/fixtures/test_4h_fixtures.py) — fixtures + proofs (runnable: `python3 test_4h_fixtures.py` or `pytest`)
- [phase_a_results.json](sandbox://workspace/quality-flow-scanner-v5/research_notes/recovery_4h_20261004/fixtures/phase_a_results.json) — machine-readable results
- [byte_identity_report.md](sandbox://workspace/quality-flow-scanner-v5/research_notes/recovery_4h_20261004/fixtures/byte_identity_report.md) — this report

No production code was modified. No network calls were made.
