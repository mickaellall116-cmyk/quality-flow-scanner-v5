# Point-in-Time Feature Audit — Canonical Baseline Rebuild

**Date:** 2026-09-24 · **Worker (c)** · **Read-only audit; no code was modified.**

Companion to `research_audit/data_leakage/AUDIT_REPORT.md` (2026-09-24), which this
audit extends feature-by-feature against the LIVE signal path
(`scanner_rules.py`, `v54_rules.py`, `v54_engine.py`, `masterscanner_api.py`,
`v54_forward_harness.py`, `v54_lonewolf_overlay.py`, `v54_fvg_sidecar.py`) and
the canonical study engine (`pine_backtest.py`).

**Clock convention (applies everywhere):** all timestamps are
`America/New_York`. US-equity 4H bars are session-anchored at **09:30** and
**13:30** ET (`scanner_rules.py:70-73`). `bar_close_at` returns the bar's real
close: 13:30 for the first bar, and `min(start+4h, 16:00)` = **16:00** for the
second bar (`scanner_rules.py:30-36`) — i.e. the second 4H bar is a shortened
13:30–16:00 closing-session bar, NOT a full 4 hours. Half-days have a single
09:30 bar. The **signal bar** is the last *completed* 4H bar at signal time;
its close (`signal_bar_close_at`) is the timestamp every feature is joined at.

---

## Per-feature audit

| Feature | Bars used vs signal bar (index `i`) | Code ref | Verdict | Canonical convention for the rebuild |
|---|---|---|---|---|
| Stock RS vs benchmark (live) | 20 **closed 4H bars**: `df["Close"].iloc[i]` vs `iloc[i-20]` | `masterscanner_api.py:236` (`rs_qqq=...iloc[-1]...iloc[-RS_LOOKBACK]`); `RS_LOOKBACK=20`, `MARKET_SYMBOL="QQQ"` at :48, :68 | **CLEAN** | Keep native: 20 closed 4H bars (≈10 trading days), benchmark = QQQ, evaluated at signal bar `i`. Note this is **not** the study's "20 trading days vs SPY" — do not mix the two definitions. (Score use only; logged, not V5.4-gating.) |
| SPY RS itself (studies) | Benchmark leg = **last completed daily bar ≤ signal-bar close timestamp** (`searchsorted(t1, right)-1`) | `pine_ranking/pine_ranking.py:95-114`; `pine_signal_quality/pine_signal_quality.py:49-60` (`bench_ret`) | **CLEAN** | SPY leg endpoint = last daily bar with timestamp ≤ signal-bar close. For a first-bar signal (13:30 close) that is **yesterday's** daily bar. This is the reference-safe pattern. |
| Sector ETF RS (20-bar, studies) | Endpoint = **signal date's daily close** (`searchsorted(date, right)-1` on `resample("1D").last()` — the *forming* daily bar) | `pine_sector_rs_backtest/run_sector_rs.py:95-100` (`ret20`), called at **:138-139** with `sig_date`; `pine_lonewolf_backtest/run_lonewolf.py:64-70`, called at **:201-202** | **LEAK** — the one genuine finding (see Impact below) | Strict: 20-trading-day returns with endpoint = last completed daily bar as of signal time. For live/intraday signals: `asof = signal date − 1 trading day` if the signal date is today; for past dates, the signal date's (completed) close is exact and safe. Reference impl: `v54_lonewolf_overlay.py:180-215` (`classify`, `asof` logic). |
| ADX (Wilder) | Value at signal bar only; Wilder EWM `alpha=1/14`, causal (`adjust=False`), computed on closed 4H bars; cross/trigger reads use `iloc[i]` and `iloc[i-1]` only | `masterscanner_api.py:147-155` (`adx(df,l=14)`), `ADX_LEN=14` at :68; study: `pine_backtest.py:105-114`; hard gate `ADX>=20`: `scanner_rules.py:17`, `v54_rules.py:38` | **CLEAN** | Wilder ADX(14) on closed 4H bars only; signal uses `ADX[i]`. V5.4 hard gate `ADX >= 20` evaluated at signal bar `i`, never revised with later bars. |
| FVG detection/state | State machine reads `low[i] > high[i-2]` and `close[i]` at index `i` only; vars persist forward but are never revised with future bars | `pine_entry_timing_backtest/run_entry_timing.py:40-78` (`add_entry_timing_columns` loop); live sidecar scans positional bars `[start, len(df)-1)` on the closed-bar feed: `v54_fvg_sidecar.py:128-143` | **CLEAN** | Detection may use bars `≤ i` only. Paper fills at the next **completed** bar's open after the signal bar (mirror of entry convention). FVG is **not** in the live V5.3/V5.4 signal path (`"FVG OFF"` in `classify_symbol`'s `mode_setup`, `masterscanner_api.py:282`). |
| BOS/CHOCH | `high.shift(1).rolling(10/20).max()`, `low > high.shift(2)`; `last_event_age` slices `ev[:pos+1]` — all reads `≤ i` | `pine_setup_age_backtest/run_setup_age.py:60-79` (`last_event_age`, `add_event_columns`) | **CLEAN** | Bars `≤ signal bar` only. Research-only (setup-age study); not in the live signal path. |
| Market gate / regime (live) | Computed from **closed 4H bars** at cycle time: QQQ EMA200/21/55 levels, `_session_return` = last closed bar's close vs the prior date's last closed bar's close | `masterscanner_api.py:185-219` (`get_market_regime`), `_session_return` at :174-183; feed from `download_data` → `resample_closed_4h` (:91-100) | **CLEAN** | Compute on closed bars at cycle time and log `signal_bar_close_at` of the last closed bar. Staleness is accepted: in a morning cycle the "session return" is yesterday's full-day return (last closed bar = yesterday's 13:30 bar) — do NOT backfill with later intraday data. |
| Market regime (studies) | Backward indicators joined at the signal **date** | `pine_regime_backtest/run_regime.py:113-130`; `pine_adx_protocol/run_adx_protocol.py:96-104` | WARNING — same mild same-day leak as sector RS | Descriptive bucketing only; no filter was adopted from it. Rebuild must join regime at the last completed bar, not the signal date. |
| Ranking inputs (rs_top2) | Ranked at signal bar `i` (one bar before entry at `i+1`); symbol leg = 4H `Close[i]/Close[i-20]`; SPY leg = `bench_ret` (last completed daily bar) | `pine_ranking/pine_ranking.py:95-114` | **CLEAN** | Rank at signal bar `i`; ETF benchmark leg = last completed daily bar ≤ signal-bar close timestamp. Entry unaffected (still next-bar open). |
| Entry trigger evaluation | Signal evaluated on completed bar `i` (`pine_buy_signal(df, i)` reads `iloc[i]`, `iloc[i-1]` only); **entry = Open of bar `i+1`**; skipped if `entry <= stop` (gap-through-stop) | `pine_backtest.py` signal fn ~:107-130, fill at ~:140-150 (`entry = df["Open"].iloc[i+1]`, `if entry <= stop0: skip`); forward harness `v54_forward_harness.py:145-158` (fills pending entry at first completed bar after the signal bar, at its open; skip `entry <= structural stop`) | **CLEAN** | Signal complete at **signal-bar close**; paper/live entry filled at **next completed 4H bar's open**; skip if entry ≤ stop. Signal price on the record = signal-bar close (unknown fill price at signal time). |
| Forming-bar truncation | Last 4H bar dropped when `now < bar_close_at(last bar)` | `scanner_rules.py:86-88` (`if current < bar_close_at(...): bars = bars.iloc[:-1]`); also `closed_higher_timeframe` (:220-245) drops today's daily bar before 16:00 ET and the unfinished weekly bar; `completed_15m_confirmation` (:183-217) drops 15m bars with `index+15min > now` | **CLEAN — confirmed** | The reference implementation. Every feature feed must pass through it (or its daily/weekly/15m equivalents) before scoring. |
| 15m confirmation / MTF trend | Completed 15m bars only; daily/weekly trimmed by `closed_higher_timeframe` before `timeframe_trend_confirmed` (needs 205 completed bars for EMAs) | `scanner_rules.py:183-217`, :248-256; engine wiring `v54_engine.py:96-109` | **CLEAN** | 15m confirmation is observational for V5.4 (not gating/grading); MTF trends feed grading as `confirmed/not_confirmed/unknown`. |
| Earnings/event data | **Zero references** in the signal path: no "earn" matches in `masterscanner_api.py`, `scanner_rules.py`, `v54_rules.py`, `v54_engine.py`, `v54_exit_tracker.py`, `v54_forward_harness.py` | Research-side only: `pine_timefx_backtest/run_timefx.py:47-80` (actual yfinance dates, ±5d bucketing, **descriptive** — the post-earnings thread is watch-only, no filter adopted) | **CLEAN (absent)** | Keep out of the canonical signal path. No earnings/event inputs in the rebuild. |

---

## The one genuine LEAK: signal-date daily close in the RS studies

`run_sector_rs.py:138-139` and `run_lonewolf.py:201-202` pass `sig_date`
(the signal **date**, tz-naive midnight ET) into `ret20`, which resolves the
endpoint with `searchsorted(date, side="right") - 1` on `resample("1D").last()`.
For a signal fired on the **first** 4H bar (09:30–13:30 ET — **91.1% of the
237 baseline signals**), the signal date's daily bar is still forming; the
endpoint therefore contains the 13:30–16:00 session — up to ~6.5 hours of data
not knowable at signal time. For second-bar signals (close 16:00) the
signal-date daily close IS point-in-time, so they are unaffected.

Quantified impact (from the audit report §3, strict = live-overlay
convention):
- Lone-wolf blocked set: **83 @ −0.0183R (study) → 93 @ +0.0616R (strict)** —
  the published "blocked = genuinely dead money" claim does not survive.
- Filter edge over control shrinks **+0.1076R → +0.0925R** (~14%).
- 18/83 lone-wolf classifications flip; 24/237 P10 sector-RS bucket
  assignments flip. Under strict PIT the filter would have blocked the
  sample's biggest winner (HOOD 2025-04-29, +8.67R).
- The canonical 237-trade baseline (+0.2388R), the engine, exits, grades, and
  all live forward-test logging are **unaffected** — none of them consume RS.

Note the live overlay's convention (`v54_lonewolf_overlay.py:208-212`) is
even stricter than the audit's "strict" sim: for a signal fired *today* it
uses `asof = today − 1d` for **both** legs (last completed daily bar), while
backfilled past signals reuse the study's signal-date endpoint (completed bar
then — safe, but a different convention; the overlay log mixes both, logged
as `rs_asof_date`).

---

## PIT CONTRACT — rules worker (d) must obey in the portfolio sim

1. **Forming-bar exclusion.** No 4H bar with `bar_close_at > cycle time` may be
   read by any feature, indicator, or exit rule. Reference implementation:
   `scanner_rules.py:86-88`. Signal bars are always *completed* 4H bars.
2. **No daily-bar data with timestamp > signal-bar close.** Daily-resolution
   feature endpoints (RS, sector RS, any new daily feature) resolve to the
   last **completed** daily bar ≤ signal-bar close (`searchsorted(..., side="right")-1`
   on a completed-only series). The signal date's daily close is usable only
   when the signal date is strictly in the past.
3. **RS endpoints = last completed daily bar.** For both the stock leg and
   the ETF legs: 20-trading-day return ending at the endpoint from rule 2.
   Intraday signals today → endpoint = yesterday's close. Never the forming
   daily bar.
4. **Entry evaluated at signal-bar close, filled at next-bar open.** The
   signal is complete when the signal bar closes; the fill price (next
   completed 4H bar's open) is unknowable at signal time. If entry ≤
   structural stop, skip the fill (gap-through-stop rule).
5. **Frozen exits from signal-bar values only.** Stop/TP1 are computed from
   the **signal-bar** close and ATR and never revised. Runner trails on
   completed-bar closes only; close-evaluated exits fill at next-bar open
   (Pine semantics, `pine_backtest.py` exit block).
6. **Indicators are causal and signal-bar-indexed.** ADX/ATR/EMA/VWAP/RVOL
   use Wilder/EMA/rolling math on closed bars only; triggers read index `i`
   (and `i-1` for crosses), never `i+1`. Warmup bars before the sample are
   for indicator seeding only, never for signal evaluation.
7. **Market gate is timestamped, not backfilled.** Compute the gate from the
   closed-bar feed available at cycle time; log `signal_bar_close_at` of the
   last closed bar. Morning-cycle staleness (yesterday's session return) is
   correct behavior — do not "repair" it with data that arrived after the
   cycle.
8. **Higher-timeframe trimming.** Drop today's daily bar before 16:00 ET and
   the unfinished weekly bar before MTF trend reads
   (`closed_higher_timeframe`, `scanner_rules.py:220-245`); EMA200-class
   indicators require ≥205 completed bars.
9. **No earnings/event inputs.** The canonical signal path consumes no
   earnings or event data; research-side descriptive bucketing
   (`pine_timefx_backtest`) stays out of the sim.
10. **Timezone discipline.** All joins in `America/New_York`. Signal identity
    keys to `signal_bar_close_at` (ISO); 4H bar labels 09:30/13:30 with closes
    13:30/16:00 (second bar is the shortened 13:30–16:00 session bar).
11. **No mixing RS definitions.** The live path's RS = 20 closed 4H bars vs
    QQQ (log-only); the research protocol's RS = 20 trading days vs SPY with
    strict daily endpoints (rules 2–3). A feature is either one or the other;
    document which before use.
