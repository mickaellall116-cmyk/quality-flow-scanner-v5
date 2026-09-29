# Scanner-to-Backtest Parity Spec — Locked Pine V3.6 Production Stack

**Status:** SPEC ONLY. No implementation, no code changes, no behavior changes.
**Written:** 2026-09-18. **Author:** engineering spec per Mike's directive
("research is closed; parity is next").

## The locked stack under test

1. **V3.6 entries/exits** — frozen. Reference implementation: `pine_backtest.py`
   (`pine_buy_signal`, `gen_pine_trades`, `add_pine_indicators`,
   `simulate_portfolio`). TradingView Pine script is the origin, NOT the parity
   reference.
2. **rs_top2 crowded-bar ranking** — frozen. Reference: `pine_ranking/pine_ranking.py`
   (`compute_features`, `simulate_portfolio_ranked`) and `pine_ranking/RANKING_SPEC.md`.
3. **E1 sector cap** — frozen. Reference: `pine_exposure/pine_exposure.py`
   (`SECTOR` dict, `pine_exposure_stacked.py`) and `pine_exposure/EXPOSURE_SPEC.md`.
4. Combined reference: `pine_stack/pine_stack.py` (`simulate_stack`, case C1).

## Critical context: no live V3.6 path exists

`pine_buy_signal` / `gen_pine_trades` are called only from research scripts
(`pine_backtest.py`, `tag_pine_mtf.py`, `pine_exit_ablation.py`,
`pine_expansion/study1_agreement.py`). There is **no automated live process that
generates V3.6 signals**. Today's live V3.6 path is Mike's TradingView script,
cross-checked manually.

The V5.4 forward-test harness (`v54_forward_harness.py`) is a **separate scanner
system** with its own frozen rules. It is NOT the V3.6 live path and must not be
modified for this work. It is useful only as (a) a proven data pipeline
(`masterscanner_api.download_data` → `scanner_rules.resample_closed_4h`) and
(b) a proven logging pattern (`v54_forward_log.ForwardLog`, append-only JSONL).

**Consequence:** Part A items marked **TODO** describe requirements for the
live V3.6 path when it is built. The non-negotiable architectural rule: the
live path must **call the same functions** (`pine_backtest.pine_buy_signal`,
`add_pine_indicators`, `resample_closed_4h`, `compute_features`,
`simulate_stack` portfolio logic), never reimplement them.

---

# PART A — Parity checklist

Each item: what must match, how to verify (exact procedure), pass criterion.
"Historical engine" = `pine_backtest.py` + `pine_stack.py` (C1) on the
`backtest_cache/v3/h4_*.pkl` bars. "Live path" = the future automated V3.6
signal process.

## A1. 4H session boundaries

**Must match:** 4H bars built by `scanner_rules.resample_closed_4h`:
- US equities: regular session only (09:30–16:00 ET), bins anchored
  `origin="start_day"`, `offset="9h30min"`, `label="left"`, `closed="left"` →
  09:30–13:30 and 13:30–16:00 ET bars (the latter a shortened 2.5h closing bar).
- Crypto (`-USD` suffix): 24/7, plain 4h bins from the same resample call
  (no session filter, no offset).
- The actively forming bar is excluded: last bin dropped when
  `now < bar_close_at(last_bar_start)` (`scanner_rules.py:86-87`).

**Verify:** take the live path's bar builder and the cached `h4_*.pkl` for 3
equity symbols + 1 crypto over one common week. Procedure: run
`masterscanner_api.download_data(sym, "4h", "5d")` today, compare bar
timestamps and OHLCV against a fresh resample of the same underlying 1h
download. Then compare the live builder's output for the historical week
against the cached pkl bars for that week (allowing for Yahoo revisions —
see A5).

**Pass:** identical bar start timestamps; OHLC equal to 1e-8; volume equal
to 1e-6; forming-bar exclusion agrees (live drops the bar the backtest
would drop at the same `now`).

**Status: PASS (shared code).** The backtest cache was built by the same
`download_data` → `resample_closed_4h` path (`backtest_v2.py:102`).

## A2. Timezone handling

**Must match:** bar timestamps end-to-end, tz-aware, no silent conversion:
- yfinance returns tz-aware index (equities `America/New_York`, crypto `UTC`
  — verified in cache: NVDA `America/New_York`, BTC-USD `UTC`).
- `resample_closed_4h` converts equity bars to `America/New_York` for the
  session filter; crypto bars keep the source tz (currently `UTC`).
- Ranking code converts to UTC for SPY alignment
  (`pine_ranking.py:104-105`: `tz_convert("UTC")`).
- Logs and alerts must store ISO-8601 with offset (never naive).

**Verify:** for 1 equity + 1 crypto symbol, assert `df.index.tz is not None`
after every pipeline stage (download → resample → indicators → signal log →
alert payload). Feed one deliberately naive-timestamp frame into the live
path and confirm it raises instead of silently localizing.

**Pass:** zero naive timestamps anywhere in the pipeline; mixed-tz (NY/UTC)
frames join correctly in ranking (no `TypeError`, no dropped symbols).

**Status: PASS (shared code) / TODO (live enforcement).** The tz behavior is
correct in the research code but nothing asserts it in a live path yet.

## A3. OHLCV adjustments

**Must match:** both sides use `yfinance` with `auto_adjust=True`
(`masterscanner_api.py:93`) — split- and dividend-adjusted OHLCV, no
separate `Adj Close` column. The backtest cache and the live download must
use the identical adjustment convention.

**Verify:** pick a symbol with a split or large dividend in-window
(e.g. NVDA 2024-06-10 split). Compare the cached `h4_NVDA.pkl` bars around
the ex-date against a fresh `download_data("NVDA","4h","2y")`: the ratio of
pre/post-split closes must match the split ratio on both sides, and the
absolute adjusted levels must agree to 1e-6 on overlapping bars.

**Pass:** adjustment convention pinned in one place (the shared
`download_data`); documented in the live path's README which convention is
used; a split/dividend regression check passes.

**Status: PASS (shared code).** Pin it: the live path must import
`download_data`, not call `yf.download` directly.

## A4. Premarket/after-hours treatment

**Must match:** excluded. `resample_closed_4h` filters equity 1h bars to
09:30–16:00 ET (`scanner_rules.py:60-63`, `minutes >= 570 & < 960`) before
resampling. The 1h download itself uses `prepost=False` (default) so
extended-hours prints never enter. Indicator inputs therefore contain
regular-session data only.

**Verify:** download 1h bars with `prepost=True` for one symbol on an
earnings day; run through `resample_closed_4h`; confirm the resulting 4H
bars are byte-identical to the `prepost=False` run.

**Pass:** extended-hours data cannot change any 4H bar, indicator value, or
signal.

**Status: PASS (shared code).**

## A5. Data-source differences, missing bars, revised bars

**Must match:** single source (Yahoo Finance via `yfinance`), single field
mapping (columns flattened from MultiIndex, `dropna()` on download —
`masterscanner_api.py:95-96`).

- **Missing bars:** a symbol with missing 1h bars produces fewer 4H bars;
  the engine must not forward-fill. `resample_closed_4h` drops bins with
  missing OHLC (`dropna(subset=["Open","High","Low","Close"])`).
- **Revised bars:** Yahoo revises recent 1h bars. The backtest ran on a
  static snapshot; the live path sees revisions. The live path must NEVER
  rewrite a bar it already used for a decision — instead it logs the data
  vintage (see Part B) and the reconciliation job classifies the resulting
  diffs as data mismatches, not logic bugs.

**Verify:** (1) delete 3 random 1h bars from a downloaded week, resample,
confirm no forward-fill (bar count drops, no NaN-filled OHLC). (2) Download
the same symbol twice 24h apart; diff the overlapping 4H bars; confirm the
live path's decision log for the first download is unchanged by the second
(the decision packet is immutable once written).

**Pass:** missing-bar policy = drop, never fill; revised bars never mutate
history; every decision packet records its data vintage.

**Status: PASS (shared code) / TODO (live vintage logging).**

## A6. Indicator warmup

**Must match:** the backtest starts signal evaluation at bar index
`WARMUP = 215` (`pine_backtest.py:47`) and additionally requires non-NaN
`e200`, `atr_base` (50-bar rolling mean), `adx`. The binding constraint is
the 200-bar EMA plus the 50-bar ATR-base rolling window.

**Verify:** start the live path with a fresh download; assert it emits no
signal until ≥215 completed 4H bars are present. Then replay: feed the live
indicator function the first 300 bars of a cached symbol and compare
`e9/e21/e55/e200/atr/adx/vol_ma/atr_ratio` at bars 215–300 against the
cached research values to 1e-10.

**Pass:** zero signals before bar 215; indicator values match the research
engine to 1e-10 from bar 215 onward.

**Status: PASS (reference defined) / TODO (live gate).** The live path must
implement the 215-bar gate explicitly — a fresh live deployment with only
"180d" of 1h history gives ~360 equity bars (OK) but this must be asserted,
not assumed.

## A7. Signal determinism

**Must match:** `pine_buy_signal(df, i)` is a pure function of the
indicator-augmented frame and bar index — same input bars → same boolean,
including the three sub-conditions (confirmed / breakout_buy / ready_buy)
and the NaN guard.

**Verify (the core parity test):** replay procedure —
1. Take the cached `h4_*.pkl` for all 51 UX51 symbols.
2. Run the historical engine's `pine_buy_signal` over every bar ≥ WARMUP;
   record `(symbol, signal_bar_start_iso)` for every True.
3. Run the LIVE path's signal function over the IDENTICAL frames;
   record the same.
4. Diff the two signal sets.

**Pass:** the two sets are identical — zero missing, zero extra, zero
timestamp-shifted signals across all 51 symbols and the full window
(2024-09-16 → 2026-09-14). Any single diff = logic mismatch = bug (Part B
taxonomy).

**Status: TODO (no live path).** The historical side is fully specified;
the live side must call `pine_backtest.pine_buy_signal` directly.

## A8. Ranking calculation

**Must match:** rs_top2 exactly as specified in `RANKING_SPEC.md`:
- `score = (Close[i]/Close[i-20] − 1) − SPY_ret`
  (`pine_ranking.py:103-107`).
- `SPY_ret = bench_ret(spy_daily, t0, t1)` where `t0/t1` are the symbol's
  own bar-`i` and bar-`i-20` timestamps converted to UTC, and `bench_ret`
  uses the last daily bar ≤ each timestamp
  (`pine_signal_quality.py:49-61`). No lookahead.
- SPY daily series: same adjustment convention as the research cache
  (`pine_signal_quality/cache/bench_1d_SPY.pkl`, daily, adjusted).
- Contested-bar arbitration: ranking engages ONLY when candidate entries at
  timestamp `t` exceed free slots (after exits at `t` are processed);
  take top `min(2, free_slots)`; ties broken by deterministic candidate
  order (UNIVERSE_X order, then entry time — Amendment A); uncontested
  timestamps take all.

**Verify:** (1) replay: recompute `rs` for every candidate trade in
`pine_stack` C1 using the live path's ranking function on identical inputs;
all scores match to 1e-10, and the contested-timestamp take/skip decisions
match exactly (C1 = 143 trades; the replay must select the same 143).
(2) SPY freshness: the live SPY daily series must contain the last
completed daily bar ≤ each signal timestamp; assert `bench_ret` returns
non-None for every live signal (a None → `-inf` score silently deprioritizes
— must be logged, never silent).

**Pass:** score-for-score and decision-for-decision match on the full
research window; SPY series provenance (source, adjustment, download time)
logged per decision packet.

**Status: TODO (no live path).** Note the research SPY cache is a static
artifact — the live path needs a maintained daily-SPY feed with the same
convention, not a copy of the pkl.

## A9. Sector labels and cap logic

**Must match:** the frozen sector map in `pine_exposure/EXPOSURE_SPEC.md`
(UX51: 9 sectors; SEMIS 9, AI_INFRA 1, AI_SOFTWARE 11, SPACE 3, CRYPTO 9,
FINTECH 5, CONSUMER 6, HEALTHCARE 2, ETF 5), implemented as the `SECTOR`
dict (`pine_exposure/pine_exposure.py:21`). Cap rule: at each entry event
(after same-timestamp exits), skip the candidate if ≥2 positions in its
sector are already open.

**Verify:** (1) the live path imports the `SECTOR` dict (or a JSON export of
it) — assert the live map's SHA-256 equals the frozen map's SHA-256 at
startup; any new symbol without a sector label blocks signal generation
(fail-closed) rather than defaulting. (2) Replay the C1 portfolio sim's
sector-skip decisions against the live cap function on identical open-
position state; all 23 documented sector skips (research window) reproduce.

**Pass:** single source of truth for the map; fail-closed on unknown
symbols; skip decisions replay exactly.

**Status: TODO (no live path).** The map exists and is frozen; nothing
consumes it live.

## A10. Position-slot accounting

**Must match:** `simulate_stack` event ordering —
- Max 5 concurrent positions (`pb.MAX_CONCURRENT`).
- At each timestamp: exits processed before entries (kind=0 before kind=1).
- 5% max portfolio risk gate (`open_risk + risk_pct > 0.05` → skip).
- One position per symbol (a new signal for a symbol with an open/pending
  position is skipped, never double-traded — same convention as
  `v54_forward_harness._busy`).
- Duplicate suppression: `signal_id` = `v36:{SYMBOL}:4h:{signal_bar_start_iso}`
  (tz-aware ISO). The same signal_id is never counted twice; idempotent
  reruns are safe (processed-bar sets, seen-signal-id sets).

**Verify:** replay the full C1 event sequence (entries/exits/skips with
timestamps) through the live path's portfolio accountant on identical
inputs; the taken/skipped sets and the final equity must match
`stack_results.json` C1 to the cent.

**Pass:** bit-identical portfolio accounting on the replay; duplicate
signal_ids rejected; rerun of the same cycle changes nothing.

**Status: TODO (no live path).** Reference logic exists in
`pine_stack.simulate_stack`; the live path must reuse its ordering rules.

## A11. Alert timing / no lookahead

**Must match:** a signal is computed on completed bar `i` and becomes
actionable at the NEXT bar's open (`gen_pine_trades`: entry =
`df["Open"].iloc[i+1]`). The live path must not use any information with
timestamp > the signal bar's close:
- Only bars with `bar_start < now` AND `now >= bar_close_at(bar_start)`
  (the forming-bar rule, A1) may enter the signal computation.
- The SPY daily bar used in ranking must satisfy `daily_bar_end <=
  signal_bar_close` (guaranteed by `bench_ret`'s `searchsorted(right)-1`).
- An alert emitted for signal bar `i` must carry `actionable_at` =
  next bar's open time, and must not be emitted before the signal bar
  actually closed.

**Verify:** (1) run the live cycle at 5-minute offsets across one full
session; assert no signal is ever emitted for a bar that hasn't closed.
(2) For 20 historical signals, assert every input value in the decision
packet has `as_of <= signal_bar_close`.

**Pass:** zero lookahead violations in the timing sweep; every alert
carries `actionable_at` ≥ signal bar close.

**Status: TODO (no live path).**

## A12. Cost/fee modeling

**Must match:** documented assumption, applied consistently. Research legs:
4bps modeled, 25bps realistic-retail; break-even friction ~108bps
(`pine_execution/`). Any live P&L reporting must state which cost leg it
uses and must never mix legs within one reported number.

**Verify:** the live P&L reporter takes `cost_bps` as an explicit parameter;
a report without it is rejected. Recompute reported live P&L from the
decision packets with the stated cost leg; matches to the cent.

**Pass:** every P&L number carries its cost assumption; recomputation from
packets reproduces it.

**Status: TODO (no live reporting yet).**

---

# PART B — Reconciliation layer design

## B1. The decision packet

For **every live signal** (including signals skipped by ranking/cap —
skipped signals get a packet too, with the skip reason), append one
immutable JSON record to an append-only log (same pattern as
`v54_forward_log.ForwardLog`: `{"type":"signal", ...}`, never rewritten).
Schema (all fields required unless marked optional):

**Identity & timing**
- `signal_id`: `v36:{SYMBOL}:4h:{signal_bar_start_iso}` (tz-aware ISO).
- `symbol`, `timeframe`: `"4h"`.
- `signal_bar_start`, `signal_bar_close`: ISO with offset.
- `computed_at`: ISO UTC when the live engine evaluated the bar.
- `actionable_at`: next bar's open (ISO with offset).

**Raw inputs (the exact values the decision used)**
- Signal bar OHLCV: `open, high, low, close, volume`.
- Indicator values at bar `i`: `e9, e21, e55, e200, atr, atr_base,
  atr_ratio, adx, vol_ma`.
- Sub-condition booleans: `confirmed, breakout_buy, ready_buy`
  (which of the three fired), plus the raw components a human would need:
  `volume_ok, hot, trend_bull, strong_trend, trend_score`.
- Entry plan: `entry_px_rule` = `"next_bar_open"`, `stop_rule` =
  `"signal_close - 1.5*ATR"`, `stop_px`, `tp1_px` (computed from
  signal-bar ATR), `risk_frac`.

**Ranking (always computed; used only if contested)**
- `sym_20bar_ret`, `spy_ret`, `rs_score` (or `"unavailable"` with reason —
  never silent `-inf`).
- `contested`: true/false; `free_slots_at_t`; `n_candidates_at_t`;
  `rank_among_candidates` (optional when uncontested); `rank_taken`:
  true/false.

**Portfolio state at decision time**
- `open_positions`: list of `{symbol, sector, entry_time}`.
- `sector_counts`: `{sector: n_open}` at decision time.
- `sector_cap_skip`: true/false + `sector` when skipped.
- `risk_cap_skip`: true/false (5% portfolio-risk gate).
- `duplicate_skip`: true/false (symbol already open/pending).

**Data vintage**
- Per symbol: `bars_source` (`"yfinance"`), `bars_downloaded_at` (UTC),
  `n_bars_used`, `first_bar_start`, `last_bar_start` (the last bar the
  decision used — must be ≤ signal bar).
- SPY daily: `spy_source`, `spy_downloaded_at`, `spy_last_daily_bar`.
- `engine_version`: git SHA (or content hash) of the signal code that ran.

## B2. The reconciliation job

**Cadence:** daily (after the US close) plus on-demand. It re-runs the
**historical reference engine** (`pine_backtest.pine_buy_signal` +
`add_pine_indicators` + `compute_features` + `simulate_stack` C1 logic) on
the bars recorded in each decision packet's data vintage, then diffs
live-vs-reference field by field:

1. Signal set: `{signal_id}` live vs reference → missing/extra/shifted.
2. Indicator values: all B1 raw inputs → tolerance 1e-10.
3. Ranking: `rs_score`, contested flag, take/skip → exact match.
4. Portfolio: sector skips, slot accounting → exact match on the replayed
   event sequence.

**Mismatch taxonomy** (seven categories, classified by pipeline layer — the
layer tells you where the bug lives):

1. **Data mismatch** — same code path, different input bars. Causes: Yahoo
   revision of a closed bar, missing bar filled differently, download raced
   a bar close. **Vendor/data cause, not strategy drift.** Counted,
   classified by cause, daily digest; a data mismatch that flips a decision
   gets its own line in the digest and the packet is annotated (append-only
   event, history never rewritten).
2. **Bar-construction mismatch** — 4H session boundaries, timezone
   attribution, or premarket/after-hours handling differ between live and
   reference on the same raw vendor data. **= logic bug.**
3. **Indicator-value mismatch** — same bars, different indicator values
   (warmup shortfall, reimplemented instead of imported indicator,
   lookback misalignment). Tolerance 1e-10; anything beyond it **= logic
   bug.**
4. **Ranking mismatch** — `rs_score`, contested-bar flag, or take/skip
   decision differs (SPY series/alignment drift, rank-cap ordering bug).
   **= logic bug.**
5. **Sector-cap mismatch** — sector label, concurrent-sector count, or
   skip decision differs (stale sector map, cap checked against wrong
   state). **= logic bug.**
6. **State/slot mismatch** — position-slot accounting differs (exits not
   processed before entries at the same timestamp, duplicate signal_id
   admitted, rerun not idempotent). **= logic bug.**
7. **Alert-delivery mismatch** — decision was correct but the alert was
   wrong, late, duplicated, or missing (`actionable_at` violated, payload
   disagrees with the packet). **= delivery bug.**

**Classification rule:** categories 2–7 are logic/delivery bugs regardless
of cause — the reference implementation is the definition of correct.
Category 1 is the ONLY non-bug category, and only when the live path can
prove it ran the reference code on different input bars (decision packet
vintage must show it).

**Alerting rule:** any category 2–7 mismatch → immediate alert (page the
operator) and the live path stops emitting new signals until the mismatch
is root-caused. Category 1 → daily digest with counts by cause; a
category-1 mismatch that flips a decision gets its own line in the digest.

## B3. Retention

- Decision packets: **immutable, retained indefinitely** (append-only JSONL;
  cheap). They are the audit trail that makes reconciliation possible.
- Raw 4H bar snapshots used per decision: retain the exact frames (or their
  content hashes + the download they came from) for **≥ 2 years**, so any
  historical decision can be replayed.
- Reconciliation diff reports: retained indefinitely alongside the packets
  they cover.

---

# PART C — Acceptance gate

All checks must pass, in order, before the locked stack is production-ready.
"Production-ready" here means: **cleared for paper-only live signal logging
with reconciliation** — NOT cleared for real money. Real money is a separate
Mike decision after the paper phase.

## Non-negotiable exit criteria

The gate is not passed until ALL of the following hold simultaneously —
they are invariants, not aspirations:

1. **Zero unresolved logic mismatches.** Every category 2–7 mismatch ever
   observed has a root cause and a fix; none are open, waived, or
   "explained away."
2. **No session/timezone ambiguity.** Every bar timestamp in every packet
   is unambiguous (exchange session + tz-attributed close); the
   reconciliation job has never observed a bar attributed to two different
   sessions.
3. **Ranking and sector-cap decisions reproducible from stored inputs.**
   Given only a decision packet, the reference engine re-derives the same
   `rs_score`, contested take/skip, sector count, and skip decision —
   bit-for-bit, with no access to live state.
4. **No duplicate-signal path.** The same `signal_id` can never produce two
   live signals; the dedup mechanism has been demonstrated under rerun,
   retry, and overlapping-cycle conditions (see C9).
5. **Packets sufficient for deterministic replay.** A third party with the
   packets, the raw bar snapshots, and the reference code reproduces every
   live decision exactly — no missing fields, no "live-only" state.

## Ordered checks

1. **C1 — Shared-code wiring.** The live path imports (not reimplements):
   `resample_closed_4h`, `download_data`, `add_pine_indicators`,
   `pine_buy_signal`, `compute_features`/`bench_ret`, the `SECTOR` map, and
   the `simulate_stack` event-ordering rules. Grep the live codebase for
   duplicate implementations of any of these; zero allowed.
2. **C2 — Historical replay (A7).** Live signal function vs reference on
   identical cached frames, all 51 symbols, full window: signal sets
   identical, zero diffs.
3. **C3 — Indicator fidelity (A6).** Indicator values match reference to
   1e-10 from bar 215; zero signals before 215 completed bars.
4. **C4 — Ranking replay (A8).** `rs_score` match to 1e-10; contested-bar
   take/skip decisions reproduce the 143 C1 trades exactly.
5. **C5 — Portfolio replay (A9/A10).** Sector-skip decisions and full event
   sequence reproduce `stack_results.json` C1 to the cent; duplicate
   signal_ids rejected; reruns idempotent.
6. **C6 — Timing sweep (A11).** Live cycle run at 5-minute offsets across a
   full session: zero signals on unclosed bars; every alert carries
   `actionable_at` ≥ signal bar close.
7. **C7 — Vintage & cost discipline (A5/A12).** Every decision packet has
   complete data vintage; every P&L number carries its cost leg;
   recomputation from packets matches.
8. **C8 — Reconciliation dry run.** The Part B job runs against 4 weeks of
   paper signals: zero logic/timing mismatches; data mismatches (if any)
   classified and understood.
9. **C9 — Failure drills.** Kill the data download mid-cycle; feed a symbol
   with a missing sector label; deliver a Yahoo 429 burst. The live path
   must fail closed (no signal rather than a wrong signal) in all three
   cases, and each failure must appear in the logs.

## Paper phase

After C1–C9 pass: run the live path **paper-only for 8 weeks** — signals
logged, decision packets written, reconciliation job running daily, no
orders, no money. Rationale for 8 weeks: at the research pace (~263 trades
/ 104 weeks ≈ 2.5 signals/week across 51 symbols) 8 weeks yields ~20 live
signals — enough to exercise contested bars, sector-cap skips, and at
least one Yahoo revision event, but short enough to keep momentum. Fewer
than 10 live signals in the window extends the phase.

**Sign-off:** Mike signs off on (a) the C1–C9 evidence bundle and
(b) closing the paper phase. No real-money use before both.

## What "production-ready" does NOT mean

- It does not re-open strategy research (entries, exits, ranking, sector
  cap, sizing — all closed).
- It does not authorize real money (separate decision, separate checklist).
- It does not retire the V5.4 forward test (separate system, separate gates).

---

## Appendix: file/line reference for the parity anchors

| Anchor | Location |
|---|---|
| Signal logic | `pine_backtest.py:129-153` (`pine_buy_signal`) |
| Indicators | `pine_backtest.py:104-127` (`add_pine_indicators`), params `pine_backtest.py:50-57` |
| Warmup | `pine_backtest.py:47` (`WARMUP = 215`) |
| Trade management | `pine_backtest.py:157-243` (`gen_pine_trades`) |
| Portfolio sim | `pine_backtest.py:247-315` (`simulate_portfolio`), `MAX_CONCURRENT=5`, `MAX_PORTFOLIO_RISK=0.05` |
| Bar construction | `scanner_rules.py:41-90` (`resample_closed_4h`), `bar_close_at` `scanner_rules.py:33-38` |
| Download | `masterscanner_api.py:91-99` (`download_data`, `auto_adjust=True`) |
| Cache builder (proof of shared path) | `backtest_v2.py:102` |
| Ranking spec | `pine_ranking/RANKING_SPEC.md`; `compute_features` `pine_ranking/pine_ranking.py:95-114` |
| SPY alignment | `pine_signal_quality/pine_signal_quality.py:49-61` (`bench_ret`) |
| Sector map | `pine_exposure/pine_exposure.py:21` (`SECTOR`); frozen in `pine_exposure/EXPOSURE_SPEC.md` |
| Stack engine | `pine_stack/pine_stack.py:32-140` (`simulate_stack`); C1 results `pine_stack/stack_results.json` |
| Log pattern | `v54_forward_log.py` (`ForwardLog`, append-only JSONL) |
| V5.4 harness (separate system — do not touch) | `v54_forward_harness.py` |
