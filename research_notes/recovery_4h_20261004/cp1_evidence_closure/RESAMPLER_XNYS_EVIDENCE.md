# Resampler + XNYS Session-Slot Logic — Evidence

**Date:** 2026-10-06
**Scope:** Omitted resampler/XNYS review from CP1; this document provides the
source/fixture evidence that was not re-examined, with precise citations.

## 1. Timezone / window origin

**Source:** `scanner_rules.py:87` (`resample_closed_4h`), lines 124–130:

```python
kwargs: dict[str, Any] = {"origin": "start_day", "label": "left", "closed": "left"}
if not is_crypto:
    kwargs["offset"] = "9h30min"
bars = data.resample("4h", **kwargs).agg(aggregations)...
```

- `origin="start_day"` anchors the 4h grid to **midnight America/New_York of
  the first 1H day** (pandas behavior for tz-aware index — corrected
  2026-10-07; not midnight UTC). The grid is UTC-fixed thereafter, not
  session-anchored, so DST moves the ET labels.
- `offset="9h30min"` shifts bins to 09:30/13:30/17:30/21:30 UTC label positions.
- `label="left", closed="left"`: bars are labeled by their left (start) edge;
  each bar covers [start, start+4h).
- For equities, input 1H rows are filtered to the 09:30–16:00 ET regular
  session before resampling (`scanner_rules.py:110-114`).

**Corrected replacement:** `resample_closed_4h_session_anchored`
(`scanner_rules.py:149`) — session-anchored, not UTC-anchored. New work must
use it; the legacy function is frozen for the affected cohort.

## 2. The two label sets — CRITICAL DISTINCTION (mechanism CORRECTED 2026-10-07)

The same `origin="start_day"` defect produced **two different label sets**.
**Neither may stand in for the other.**

> **Correction (2026-10-07, ChatGPT amendment 6028744990):** the mechanism
> stated here in rev 1 ("different first-download date → different
> UTC-midnight anchor phase") was wrong. `origin='start_day'` anchors to
> midnight **in the index timezone** (`America/New_York`), not midnight UTC,
> and a date change within one DST regime does not shift the grid at all.
> The real mechanism — first day's DST *regime* moves the ET-midnight anchor
> by 1h in UTC (05:00 vs 04:00), shifting the UTC-fixed grid — is derived
> with a passing synthetic fixture in **`RESAMPLER_MECHANISM_FIXTURE.md`**
> (`resampler_grid_fixture.py`). What follows is the corrected summary;
> the fixture document is authoritative.

### Set A — Historical cache labels: 08:30 / 12:30 ET

- **Artifact:** `backtest_cache/v3/h4_*.pkl` (52 files, created 2026-09-15
  via an uncommitted process using Path 1).
- **Evidence:** `research_notes/recovery_4h_20261004/fixtures/byte_identity_report.md:82`
- **Observation:** 332 bars labeled 08:30/12:30 EST during EST regimes
  (2024-11-04…2025-03-07, 2025-11-03…2026-03-06). Underlying UTC bins are
  fixed at 13:30/17:30 UTC; during EDT the same bins label 09:30/13:30.
- **Mechanism (corrected):** EDT-anchored 13:30/17:30 UTC grid (first 1H day
  in EDT). `[13:30,17:30)` UTC = `[08:30,12:30)` EST — the "morning" bin
  covers a different hour set than the intended `[09:30,13:30)` EST session
  bin. Full derivation: `RESAMPLER_MECHANISM_FIXTURE.md`.
- **Used by:** the 240-trade C1 baseline (+0.178R @4bps); the 51 equity
  shifted-regime entries were evaluated on these bars.

### Set B — Live forward-test labels: 06:30 / 10:30 / 14:30 ET

- **Artifact:** live forward-test signals, 2026-09-15 through 2026-10-03.
- **Evidence:** `research_notes/recovery_4h_20261004/spec/call_site_map.md:13`
  ("live forward test produced 06:30/10:30/14:30 ET bars instead of 09:30/13:30").
- **Mechanism (corrected):** EST-anchored 14:30 UTC grid (first 1H day in EST —
  live window pinned to `start="2026-01-15"`, verified bar-for-bar identical
  to the live `period="180d"` construction in `build_affected_cohort_archive.py`).
  In EDT the bins fall at 06:30/10:30/14:30/18:30 local → three session bars
  per day. Full derivation: `RESAMPLER_MECHANISM_FIXTURE.md`.
- **Used by:** the frozen forward-test cohort (4 open paper positions:
  VEEV, SHEL, ANET, VLO) — pinned, entries paused.

### Why they differ (corrected)

`origin="start_day"` = midnight **America/New_York** of the first 1H day —
not midnight UTC. Midnight EST (05:00 UTC) vs midnight EDT (04:00 UTC)
shifts the UTC-fixed grid by 1h. Cache build: first day in EDT → 13:30 UTC
grid → 08:30/12:30 EST labels. Live: first day in EST → 14:30 UTC grid →
06:30/10:30/14:30 EDT labels. Same defect class, different manifestation —
via the DST-regime anchor, not the calendar date.

## 3. Early-close behavior

- **Resampler:** `bar_close_at` (`scanner_rules.py:32-52`) caps the bar close
  at `min(start + 4h, session_close)`, where `session_close` defaults to
  16:00 ET but accepts the exchange calendar's early-close time (e.g. 13:00 ET).
- **Audit comparator:** `cp1_followup/audit_52symbol.py:7,34,53-61` uses
  `pandas_market_calendars` XNYS v5.5.0, consulting `market_open`/`market_close`
  per day; early closes (day after Thanksgiving, Christmas Eve) are classified
  as `scheduled_truncation` (225 slots), not gaps.
- **Cache evidence:** `byte_identity_report.md:90` — early-close days
  (2024-11-29, 2024-12-24, 2025-07-03, 2025-11-28, 2025-12-24) correctly show
  a single morning bar in the cache.

## 4. Completed-bar causality

**Source:** `scanner_rules.py:132-136` (inside `resample_closed_4h`):

```python
current = _now_for_index(bars.index, now)
if current < bar_close_at(bars.index[-1], symbol):
    bars = bars.iloc[:-1]
```

The actively forming bar is excluded: if "now" precedes the last bar's close,
the last bar is dropped. Signals are therefore computed only on completed bars.
(`bars.attrs["last_bar_start_at"/"last_bar_close_at"]` record the boundary.)

## 5. Deterministic chart selection (pilot)

**Source:** `research_notes/recovery_4h_20261004/trade_chart_review_pilot/pilot_selection.json`
- Six trades selected by deterministic rules (exact gap intersection; earliest
  shifted equity entry; earliest unshifted equity entry; earliest crypto
  calendar entry; earliest SOL trade) — no P&L-based selection.
- Chronology is self-reported (no pre-render timestamped commit anchor).

## 6. Preservation of original caches

- SHA-256 of all 52 `backtest_cache/v3/h4_*.pkl` files pinned **before**
  inspection in `cp1_followup/cache_hashes_pinned.txt` (52 entries, verified
  2026-10-06 present).
- The CP1 audit (`audit_52symbol.py`) is read-only; no cache file was modified.
- Constraint honored throughout: no corrected performance, no holdout access,
  no production changes.

## 7. What was NOT re-examined (omitted review boundary)

- The resampler source itself was not re-audited line-by-line in CP1; the
  defect characterization above rests on the function's docstring
  (`scanner_rules.py:87-108`, which explicitly documents the UTC-anchor
  defect), the byte-identity fixture report, and the call-site map.
- The XNYS comparator logic (`audit_52symbol.py`) was reviewed as a
  forensic instrument, not as a production component.
- Any claim requiring the *live* 06:30/10:30/14:30 bars' byte content is
  **UNVERIFIABLE** from the cache evidence — the cache contains only the
  08:30/12:30-label manifestation. Live-bar bytes were not retained.
