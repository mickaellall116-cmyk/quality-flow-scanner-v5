# CANONICAL 4H CONSTRUCTOR SPECIFICATION
**Recovery pre-run package — Phase A**
**Date:** 2026-10-04 | **Branch:** `recovery-4h-20261004`
**Source:** `scanner_rules.resample_closed_4h_session_anchored` (scanner_rules.py @ `7db282ddfc150c9e`)
**Status:** SPECIFICATION ONLY — no performance data opened.

---

## 1. Designation

The candidate research canonical 4H path is
`scanner_rules.resample_closed_4h_session_anchored(df, symbol, now=None)`.

It is explicitly anchored to the **US equity session clock in America/New_York**,
DST-safe by construction (bins assigned from local session time, never via
pandas `origin=` anchoring).

## 2. Exact bar boundaries (US equities)

| Bar | Session window (America/New_York) | Label (bar start) | Bar close |
|-----|-----------------------------------|-------------------|-----------|
| Morning | [09:30, 13:30) | 09:30 | 13:30 |
| Afternoon | [13:30, session_close) | 13:30 | min(17:30, session_close) |

- `session_close` is read per-date from the XNYS exchange calendar
  (`pandas_market_calendars`): 16:00 regular days, 13:00 early-close days
  (e.g. day after Thanksgiving, July 3rd when applicable).
- Unknown dates fall back to 16:00.
- On early-close days the afternoon bin [13:30, 13:00) has no rows by
  construction → only the morning bar is emitted.
- Input rows are filtered to `[09:30, session_close)` in local time before binning.
- Crypto (`-USD` suffix): bins at 00/04/08/12/16/20 UTC, UTC-anchored, no session logic.

## 3. Labeling / closed semantics

- **Label:** left (bar start timestamp). Index is tz-aware `America/New_York`.
- **Closed:** left — a 1H row stamped exactly at 13:30 belongs to the afternoon bar.
- **OHLCV aggregation:** Open=first, High=max, Low=min, Close=last, Volume=sum.
- **SessionVWAP:** cumulative regular-session VWAP (`last` per bar); computed from
  typical price × volume grouped by session date.
- **Forming-bar exclusion:** the last bar is dropped when `now < bar_close_at(bar_start)`.
  `bar_close_at` = `min(bar_start + 4h, session_close)`.
- **Causal cutoff (fail-closed):** rows with index `> now` are dropped BEFORE binning.
  No bar can contain future data regardless of caller input.

## 4. Partial-session handling

| Case | Behavior |
|------|----------|
| Early close (13:00) | Morning bar [09:30,13:30) emitted normally; afternoon bin empty → dropped. `last_bar_close_at` = 13:00 ET. |
| Half data (late start) | Bars built from available rows; empty bins dropped via `dropna`. |
| Holiday (no rows) | Empty frame returned. |
| Missing bars mid-session | Aggregation over present rows only; no forward-fill. |
| `now` inside forming bar | Forming bar excluded; `last_bar_*` attrs reflect last CLOSED bar. |
| `now` before session start | Zero bars returned. |
| Future rows in input | Truncated at `now` before binning. |

## 5. Execution timing

- Signal bar = the most recently CLOSED 4H bar per `last_bar_close_at`.
- Entry executes at next bar open (backtest convention: `pine_backtest`,
  "entry at next 4h bar open").
- `now` parameter: when None, defaults to wall-clock in the index timezone.
  Callers MUST pass explicit `now` for reproducibility; wall-clock default is
  for live use only.

## 6. Timezone conversions

- Input MUST be tz-aware for US equities (TypeError otherwise).
- All binning done in `America/New_York` local time.
- Output index: tz-aware `America/New_York`.
- `bar_close_at` returns tz-aware timestamps.
- Attrs `last_bar_start_at` / `last_bar_close_at` are ISO-8601 with offset.

## 7. DST invariance (by construction)

Bins are assigned from `local.hour * 60 + local.minute` (wall-clock minutes),
so:
- Spring forward (2026-03-08): 09:30 ET still labels the morning bar; the
  session has the same wall-clock structure.
- Fall back (2026-11-01): same.
- No UTC-midnight anchor exists anywhere in the path → grid cannot shift with
  DST or download-window length (the defect in the legacy constructor).

## 8. Schema

Output columns: `Open, High, Low, Close, Volume[, SessionVWAP]`.
Output attrs: `last_bar_start_at`, `last_bar_close_at` (ISO strings).
Index name: None (cleared).
