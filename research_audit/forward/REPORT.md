# Forward-Test Contamination Audit — REPORT

**Date:** 2026-09-24 (audit run ~21:35–21:45 ET)
**Scope (read-only):** `v54_forward_harness.py`, `v54_fvg_sidecar.py`, `v54_lonewolf_overlay.py`,
`forward_scoreboard.py`, `lonewolf_report.py`, and forward state/logs in `v54_forward/`
**Method:** static code comparison against the research definitions, file birth/mod times
(filesystem crtime), schema-drift check of the live signal log, and empirical spot-checks of
live overlay/sidecar records. Nothing was modified; nothing was run live (`--verify` modes
not executed, live cycles not triggered).

---

## Check 1 — FROZEN RULES match research (line-by-line)

### 1a. FVG sidecar vs research FVG definition — PASS (one inert cosmetic difference noted)

Research canonical definition is shared by both studies:
- `pine_fvg_attribution/run_fvg_attribution.py:33` imports `add_fvg_columns` from
  `pine_stalefvg_backtest/run_stalefvg.py` (used unmodified); it also imports `fvg_sub` from
  `pine_fvg_robustness/run_fvg_robustness.py:59-71`.
- `pine_fvg_protocol/run_fvg_protocol.py:24-26` imports the same two functions; the canonical
  variant is `make_signal(PERTURB["FVG"])` with `PERTURB["FVG"] = {vol_mult: 1.0, use_safe: True, use_e21: True}`
  (`pine_fvg_robustness/run_fvg_robustness.py:74-79`).

Line-by-line comparison:

| Research (`run_stalefvg.py`) | Live sidecar (`v54_fvg_sidecar.py`) | Match |
|---|---|---|
| `add_fvg_columns`, lines 49–77: formation `if i >= 2 and low[i] > high[i-2]: last_lo,last_hi = high[i-2], low[i]` (66–68) | `add_entry_timing_columns`, lines 69–115: same formation (95–96) | ✅ identical |
| `in_fvg[i] = bool(low[i] <= last_hi and c >= last_lo)` (73) | `in_fvg[i] = bool(low[i] <= last_hi and c >= last_lo)` (111) | ✅ identical |
| `if np.isnan(a): continue` (69–71, atr only) | `if np.isnan(a) or np.isnan(e): continue` (97–98, atr AND e21) | ⚠️ differs, **inert** |
| `fvg_sub` guard: skip if e200/atr_base/adx NaN (`run_fvg_robustness.py:62-63`) | `fvg_sub_signal` guard: same (117–120) | ✅ identical |
| `trend_bull = e21>e55 and close>e200` (68); fired = `trend_bull and inBullFvgSupport and close>e21 and vol>vol_ma and not hot`, with canonical PERTURB (70–71) | `trend_bull = r["e21"] > r["e55"] and close > r["e200"]`; returns `trend_bull and inBullFvgSupport and close>e21 and vol>vol_ma and safe` (124–128) | ✅ identical |
| Variant signal = `_orig_signal OR fvg_sub` (`run_fvg_robustness.py:82-87`; protocol `run_fvg_protocol.py:102`) | `scan_signals`: `base = pb.pine_buy_signal(df, i)`; `fvg = fvg_sub_signal(df, i)`; fire if `base or fvg` (134–144) | ✅ identical |
| FVG-only bucket = FVG signals minus BASE signals (`run_fvg_protocol.py:116`) | `fvg_marginal = bool(fvg and not base)` (`make_signal_record`, ~170) | ✅ same concept |

Notes:
- The ⚠️ NaN-guard difference can never bind: the sidecar scans from `max(start_pos, pb.WARMUP)`
  (line 139), and `pb.WARMUP = 215` (`pine_backtest.py:54`), at which point e21 (21 bars) and
  ATR (14 bars) are both non-NaN. The research scans post-warmup too. Zero behavioral impact.
- The sidecar computes `bullSweep`, `useFvg`, `nearBuyZone` columns (lines 84–113) that are
  **never read** by `fvg_sub_signal` or `scan_signals` — dead columns, harmless, but they are
  not part of the fired signal path.
- The sidecar never monkey-patches `pb.pine_buy_signal` (only reads it at line 140), so the
  shared `pine_backtest` module used by the harness is untouched.

### 1b. Lone-wolf overlay block rule vs research — PASS (one documented, more-conservative adaptation)

Research: `pine_lonewolf_backtest/run_lonewolf.py:208` → `"lone_wolf": bool(srs > 0 and secrs <= 0)`;
also `pine_lonewolf_protocol/run_protocol.py:196` → `bool(srs > 0 and secrs <= 0)`;
lookback `LOOKBACK = 20` in both; sector map at `run_lonewolf.py:43-48`, `run_sector_rs.py:54-63`,
`run_protocol.py:31-36`.

Live overlay (`v54_lonewolf_overlay.py`):
- `LOOKBACK = 20` (line 75); `SECTOR` map (77–81) — compared entry by entry against all three
  research maps: **identical** (14 names, same ETFs).
- `would_block = bool(srs > 0 and secrs <= 0)` (~line 280) — **identical** to research.
- `_ret20` (~lines 245–255) vs research `ret20` (`run_lonewolf.py:64-70`): same math
  (`searchsorted(asof, right)-1`, `pos < 20 → NaN`, `series[pos]/series[pos-20] - 1`). The overlay
  adds a `if not base or pd.isna(base)` guard — inert (a price base of exactly 0.0 cannot occur).
- **Documented adaptation:** the research used the signal date's daily close; for a signal fired
  intraday today, the overlay uses the last *completed* trading day
  (`asof = min(sig_date, today-1d)`, ~lines 264–270). This is *more* conservative than the study
  (strictly less information, never more). Verified empirically: signal
  `v54:ANET:4h:2026-09-24T10:30:00-04:00` (fired today) was classified with `rs_asof_date=2026-09-23`
  in `v54_forward/lonewolf_overlay.jsonl`.

### 1c. ADX shadow vs research ADX definition — PASS

- Research canonical feature: `("adx", 14, "adx")` — period-14 Wilder ADX on 4H bars
  (`pine_ranking_confirm/run_ranking_confirm.py:42-53`; protocol computes `pb.adx(df, 14)` at
  `run_adx_protocol.py:53`).
- The shadow does not recompute ADX: it reads the per-signal `"adx"` the frozen harness logs
  (`forward_scoreboard.py:237, 251`). That value comes from the engine (`v54_engine.py:173, 246`),
  whose `ADX` column is built by `masterscanner_api.adx(out, ADX_LEN)` with `ADX_LEN = 14`
  (`masterscanner_api.py:68, 147-155, 168`) — the same Wilder-RMA formulation as
  `pine_backtest.adx(df, l=14)` (`pine_backtest.py:81-88`; both `atr()` use Wilder RMA,
  `masterscanner_api.py:142-145` vs `pine_backtest.py:75-76`). Same period, same timeframe (4H),
  same math, point-in-time at the signal bar.
- Shadow selection (top `SLOT_CAP` by ADX desc on crowded bars, `forward_scoreboard.py:248-252`)
  matches the research's crowded-bar ranking direction (`-feats[i]["adx"]`, `run_adx_protocol.py:135`).
  `SLOT_CAP = 5` (line 34) reconstructs the research's 5-slot crowded-bar notion; the frozen
  forward harness itself applies no slot cap (admits every qualified signal — verified in
  `v54_forward_harness.py:185-213`), so the shadow is a like-for-like what-if, not a production
  rule. Currently vacuous (0 crowded bars, `sample_warning` states this explicitly at lines 282–283).

**Check 1 verdict: PASS.** No rule drift. The only code differences found are provably inert
(NaN guard behind warmup; dead columns) or a documented stricter point-in-time adaptation.

---

## Check 2 — NO RETUNING after forward results arrived

Git provides no history here: none of the five live files are tracked (`git ls-files` shows only
`scanner_rules.py`/`tests/test_scanner_rules.py`), so birth/mod times are the evidence.

| File | Created (birth) | Modified | Assessment |
|---|---|---|---|
| `v54_forward_harness.py` | 2026-09-15 16:39 UTC | **2026-09-24 03:23 UTC** (= Sep 23 23:23 ET) | modified once, mid-test |
| `v54_fvg_sidecar.py` | 2026-09-24 03:23 UTC (= Sep 23 23:23 ET) | same | created with first live run Sep 24 03:55 UTC |
| `v54_lonewolf_overlay.py` | 2026-09-25 01:14 UTC (= tonight) | same | new tonight |
| `forward_scoreboard.py` | 2026-09-25 01:19 UTC (= tonight) | same | new tonight |
| `lonewolf_report.py` | 2026-09-25 01:14 UTC (= tonight) | same | new tonight |
| Frozen: `v54_engine.py`, `v54_rules.py`, `v54_exit_tracker.py`, `v54_ai_observer_prompt_v1.md` | Sep 15 | **unchanged since Sep 15** | frozen ✅ |

Findings:
- The harness's single mid-test modification (Sep 23 23:23 ET) is the **additive FVG-sidecar hook**:
  the sidecar file was born one second earlier (03:23:26 vs harness mtime 03:23:28) and the call
  `run_sidecar_cycle(ctx, regime)` sits at the end of `run_once` **after** all frozen outputs are
  written, wrapped in try/except (`v54_forward_harness.py` ~lines 700–706). No evidence of a
  frozen-rule change: the live signal schema is byte-identical from the first signal
  (2026-09-15) to the latest (2026-09-24) — no schema drift — and every one of the 19 signals
  is stamped `v54_rule_version = 2026-09-15-v54`.
- Sidecar parameters match research exactly (`SWEEP_LB=20, BZ_W=0.35, NEAR_ATR=0.50` =
  `pine_entry_timing_backtest/run_entry_timing.py:33-35`). Overlay parameters match research
  exactly (LOOKBACK=20, sector map, block rule). No parameter differs from the pre-registered
  research values, so there is nothing to attribute to post-hoc tuning.
- The overlay/scoreboard/report were created tonight, *after* 9 days of forward results — but
  they are read-only shadow/overlay systems with verbatim research parameters, and the live
  sample is tiny (19 forward signals, 4 closed trades; only 1 in-map lone-wolf classification so
  far, `would_block=False`) — there was effectively no outcome data to tune *to*.

**Check 2 verdict: PASS.** One harness edit mid-test, but it is additive (sidecar hook) and the
frozen signal schema/rule version are unchanged; no parameter in any shadow system differs from
the pre-registered research values.

---

## Check 3 — NO FUTURE LEAKAGE in live evaluation

### 3a. Lone-wolf overlay "last completed daily bar" — PASS
- `classify()` (~lines 258–283): `asof = min(sig_date, today - 1d)` when the signal date is today,
  else the signal date itself; `_ret20` then uses `searchsorted(asof, side="right") - 1` — the
  last daily bar at or before `asof`. An intraday signal can never see today's incomplete bar.
- Empirically confirmed on the live log (ANET signal fired 2026-09-24 → `rs_asof_date=2026-09-23`).
- The daily cache (`_get_daily`, ~lines 195–240) merges cached + fresh yfinance bars into
  `v54_forward/lonewolf_cache/` — own files only; cached bars are historical closes, not future data.

### 3b. Forward harness signal generation — PASS
- `eng.v54_scan_symbols` (~`v54_engine.py:278-289`) states its contract: "`download_data` already
  returns closed 4H bars". Verified: `masterscanner_api.download_data` → `resample_closed_4h`
  drops the actively-forming bar (`scanner_rules.py:41-92`: `if current < bar_close_at(bars.index[-1], symbol): bars = bars.iloc[:-1]`).
  Every bar the harness evaluates is complete.

### 3c. FVG sidecar signal generation — PASS (doubly conservative)
- Scans `scan_signals(df, start_pos, len(df) - 1)` with `range(lo, end_pos)` — the last bar of the
  (already closed-bar) dataframe never generates a signal (`v54_fvg_sidecar.py` ~line 285).
  First run seeds `last_scan_bar` forward-only; historical bars never generate sidecar signals
  (lines ~272–279). No backfill contamination.

### 3d. Outcome joining (signal ID → closed trade) — PASS
- Harness: positions walk `df[df.index > last_processed_bar]` in order and close only via the
  frozen Mode B tracker (`v54_forward_harness.py:169-183`); closes are logged in step 3
  (~lines 225–232) strictly after the tracker marks them closed. The V5.3 EXIT probe is
  point-in-time: `v53_state_for_bar` truncates to `df_full[df_full.index <= bar_ts]` (lines ~130-136).
- Sidecar: its own `ModeBTracker` instance (created fresh in `run_sidecar_cycle`, line ~379) —
  it does **not** share the harness's tracker, so paper positions cannot contaminate frozen positions.
- Overlay close-join: reads the harness's `forward_test/v54_closed_trades.json` and joins by
  `signal_id`, copying only already-realized fields (`blended_r`, `exit_reason`) into its own log
  (`v54_lonewolf_overlay.py` ~lines 315–335). Joining happens only for closes the harness already
  recorded — no lookahead, no information available after close is injected back into anything.

**Check 3 verdict: PASS.** Signal detection uses only completed bars; outcome joining uses only
post-close information; the intraday adaptation in the overlay is strictly point-in-time.

---

## Check 4 — SCOREBOARD HONESTY

- `forward_scoreboard.py` is read-only: the only file I/O is `with open(path) as f:` reads of the
  three jsonl logs plus `v54_forward/v54_closed_trades.json`; output is `print()` to stdout
  (plain text or `--json`). No writes, no state mutation — verified by grep for
  `open(` with write/append modes, `json.dump`, `to_csv`, `to_pickle`, `os.replace` (none found).
  `lonewolf_report.py` similarly reads only (`open(LOG)` at line 25).
- Mandatory sample-size warnings: `size_warning()` (`forward_scoreboard.py:83-90`) is attached to
  every board ("n=0 closed trades — no outcomes yet, do not judge", "n<5 — noise, do not judge",
  etc.), rendered as `SAMPLE WARNING:` in text output (line 347). The ADX board additionally warns
  when it is vacuous ("n=0 crowded bars — shadow is vacuous until a bar exceeds the slot cap",
  lines 282–283). It is not currently feasible to declare any winner, and the board says so.

**Check 4 verdict: PASS.** Read-only; warnings present on every board.

---

## Overall verdict: **PASS** — clean bill of health, no forward-test contamination found

1. **Frozen rules match research:** PASS (FVG, lone-wolf, and ADX shadow all verbatim; inert
   cosmetic differences and one documented stricter point-in-time adaptation only).
2. **No retuning:** PASS (one mid-test harness edit = additive sidecar hook; frozen files
   untouched since Sep 15; shadow parameters verbatim from research).
3. **No future leakage:** PASS (completed bars only; intraday-today overlay uses last completed
   daily bar; outcome joining strictly post-close; separate tracker instance for the sidecar).
4. **Scoreboard honesty:** PASS (read-only; mandatory sample-size warnings on every board).

### Discrepancies / caveats (all non-blocking)
1. Sidecar NaN guard checks e21 too, research checks ATR only — provably inert behind
   `pb.WARMUP = 215` (`v54_fvg_sidecar.py:97-98` vs `run_stalefvg.py:69-71`).
2. Sidecar computes `bullSweep`/`useFvg`/`nearBuyZone` columns never used in the signal path —
   dead code, no behavioral effect.
3. Lone-wolf overlay's intraday adaptation (last-completed-day asof) differs slightly from the
   study's signal-date-close convention — documented in the overlay's docstring, strictly more
   conservative, and logged per record as `rs_asof_date`.
4. Scoreboard `SLOT_CAP = 5` is a reconstruction of the research's crowded-bar notion; the frozen
   forward harness itself has no slot cap (admits all qualified signals) — the shadow is honest
   about this and currently vacuous.
5. The overlay covers only the 14 mapped watchlist symbols; the other 236 forward-test symbols
   log `no_sector_mapping` (by design — P10 was a 14-stock study).
6. No git history exists for the live files (all untracked), so Check 2 rests on filesystem
   birth/mod times plus schema-drift analysis rather than diffs. Consider committing these
   files so future audits have a diffable trail.

### Files
- This report: `~/workspace/quality-flow-scanner-v5/research_audit/forward/REPORT.md`
