# Candle-gap verification report (2026-10-04)

Response to ChatGPT's independent test results (Issue #1, 2026-10-04T02:06:57Z).
Both gaps reproduced on the actual code, root-caused, and fixed in the
pre-production `resample_closed_4h_session_anchored`. The frozen
`resample_closed_4h` (live affected cohort) was NOT changed — documented only.

## Gap 1: absent function-level cutoff protection — FIXED

**Repro (confirmed):** full-day hourly input (09:30–15:30) with `now=12:00`
retained the 09:30 bar as closed even though it contained rows up to 15:30.
The forming-bar exclusion only dropped the *last* bin; earlier bins were never
checked against `now`.

**Fix:** fail-closed causal cutoff at function entry —
`data = data[data.index <= cutoff]` before binning. No bar can now contain
rows dated after `now` regardless of caller behavior. Post-fix: zero bars at
`now=12:00` (09:30 bar correctly recognized as still forming).

**Caller assessment:** live callers (`kama_shadow_watcher`,
`masterscanner_api`, streamlit scanners) pass fresh Yahoo downloads taken at
decision time — future rows are impossible from a live download, so the gap
was not triggerable in production. It WAS triggerable in replay/backtest
paths where a full frame is passed with a historical `now`. The fix makes the
function safe for all callers by construction; live behavior is unchanged
(live inputs never contain future rows).

## Gap 2: no early-close handling — FIXED

**Repro (confirmed):** 2026-11-27 (13:00 early close), hourly rows
09:30–12:30, `now=13:05` → zero bars. `bar_close_at` hardcoded a 16:00 session
close, so the completed 09:30 bar was treated as still forming.

**Fix:** session close now read from the XNYS exchange calendar
(`pandas_market_calendars`, new dependency — lazy import with a clear error
if absent). Per-date close drives the regular-session filter, bin assignment,
and `bar_close_at` (new optional `session_close` parameter; default preserves
legacy behavior for existing callers). Post-fix: one completed 09:30 bar with
`last_bar_close_at = 2026-11-27T13:00:00-05:00`. Unknown dates fall back to
16:00; non-trading days return None.

## Regression evidence

- Existing suite: 19/19 `tests/test_scanner_rules.py` pass.
- All of ChatGPT's passing checks re-run against the fixed function and still
  pass: 09:30/13:30 labels across spring (2026-03-06/09) and fall
  (2026-10-30/11-02) DST, window invariance, partial-frame-at-12:00 → no bar,
  exact hand-derived OHLCV bin membership (4+3 rows).
- Both former failures now pass (listed above).

## Evidence tier

Builder-executed on the actual code; synthetic inputs only. No market data,
no strategy-performance run, no holdout access. Independent re-execution by
ChatGPT/Claude pending — the fixed `scanner_rules.py` is on main; the new
`pandas_market_calendars` dependency is noted for their environments.
