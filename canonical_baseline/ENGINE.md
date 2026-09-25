# ENGINE.md — Canonical Mode B Execution Engine

Fresh, exact rebuild of the frozen Mode B exit stack for research backtests.
Ground truth is the LIVE implementation (`v54_exit_tracker.py`, `ModeBTracker`),
driven by `v54_forward_harness.py`. Frozen spec: `v54_spec.md` §3.

**Nothing in this folder modifies the live system.** Guardrail files
(`v54_engine.py`, `v54_exit_tracker.py`, `v54_rules.py`, `scanner_rules.py`,
`v54_forward/`, `signal_log/`) were read, never written.

## 1. API

```python
from canonical_baseline.modeb_engine import run_trade

run_trade(entry_bar_idx, entry_price, stop, tp1, bars_df,
          scanner_states=None, realistic_gaps=False,
          entry_bar_label=None) -> TradeResult
```

- `entry_bar_idx`: positional index into `bars_df` of the ENTRY bar — the
  first completed 4H bar AFTER the signal bar. The caller passes the entry
  fill as `entry_price` (live paper fills at that bar's open —
  `v54_forward_harness.py:156`).
- `bars_df`: `Open`/`High`/`Low`/`Close` columns, rows in chronological
  order. The index supplies bar labels (used for `exit_bar`/events only).
- `scanner_states`: optional list aligned to `bars_df` rows (positional);
  only the value `"EXIT"` is read, and only when Profit Protect is armed —
  mirroring `v54_exit_tracker.py:165,171`. `None` = no EXIT signal.
- `realistic_gaps`: `False` (default) = byte-faithful to the live tracker;
  `True` = realistic gap variant (see §3).
- Returns `TradeResult` (`modeb_engine.py:104`): `exit_bar`, `exit_px`
  (for post-TP1 runner exits this is the RUNNER exit price; the TP1 fill is
  recorded separately in `tp1_fill_px`/`tp1_fill_bar`), `exit_reason`,
  `live_reason` (tracker vocabulary), `blended_r`, `partial_r`, `runner_r`,
  `mfe_r`, `mae_r`, `bars_held`, `tp1_taken`, `pp_armed`, `pp_arming_bar`,
  `reached_plus_1r`, `events`.

Exit reasons (`exit_reason`; `live_reason` in parentheses):
`STOP` (`stop`) · `TP1_THEN_STOP` (`runner-stop`) ·
`TP1_THEN_PP` (`runner-exit`) · `PP` (`scanner-exit`) ·
`TIMEOUT` (`time` / `runner-time`) · `GAP_ABOVE_TARGET`
(`gap-above-target`) · `OPEN` (bar data exhausted before any exit — live
never hits this; the forward test keeps feeding bars until close).

## 2. R-multiple convention (one sentence)

R is denominated in the planned risk unit `entry − stop`; full-position
exits report `blended_r = R(exit_px)` on the full position, while post-TP1
runner exits report `blended_r = 0.5·R(tp1_fill) + 0.5·R(runner_exit_px)`
because the 50% scale-out is real — half the position is gone at TP1, so the
runner's R applies only to the remaining half.

(`modeb_engine.py:94` `r_of`; live `_close`/`_close_runner` at
`v54_exit_tracker.py:199-232`.)

## 3. Every fill assumption, with code references

| # | Assumption | This engine | Live tracker |
|---|---|---|---|
| 1 | Entry fill | Caller-supplied `entry_price`; docstring `modeb_engine.py:135-188` | Next 4H bar's open after the signal bar — `v54_forward_harness.py:156` (`open_position(snap, float(newbars.iloc[0]["Open"]), …)`, `newbars = df[df.index > signal_bar_start]`) |
| 2 | Entry ≤ stop | `ValueError` — `modeb_engine.py:190` | `open_position` returns `None` (invalid) — `v54_exit_tracker.py:87-88` |
| 3 | Entry bar opened at/above TP1 | Immediate close at entry price, `blended_r = 0.0`, `bars_held = 0`, reason `GAP_ABOVE_TARGET` — `modeb_engine.py:209-226` | `open_position` closes immediately at entry — `v54_exit_tracker.py:92-95` |
| 4 | Entry bar is processed | Yes, as bar #1 of the 30-bar clock — `modeb_engine.py:257` | `v54_forward_harness.py:173` (`df[df.index >= entry_bar]` for newly opened); `v54_exit_tracker.py:127` (`bars_held += 1` at top of `process_bar`) |
| 5 | Resting stop fill (primary) | **At the exact stop price — even when the bar gaps through it** — `modeb_engine.py:236-241` | `v54_exit_tracker.py:151-152` (full), `:169-170` (runner). **Optimistic** vs a real stop-market |
| 6 | Resting stop fill (realistic variant) | Gap-through (open ≤ stop): fills at the **open**. Intrabar touch (open > stop, low ≤ stop): fills at the **stop** — `modeb_engine.py:236-241` (`realistic_gaps=True`) | N/A — live has no realistic variant (this is the audit's recommended fix: `EXECUTION_AUDIT_REPORT.md` §4) |
| 7 | TP1 fill (primary) | **At the exact TP1 price — even when the bar opens above it** (price improvement ignored) — `modeb_engine.py:243-248` | `v54_exit_tracker.py:157-162` (`tp1_r = _r_of(tp1, …)` always at the tp1 level). **Conservative** vs a real limit |
| 8 | TP1 fill (realistic variant) | Gap-through (open ≥ TP1): fills at the **open** — `modeb_engine.py:243-248` (`realistic_gaps=True`) | N/A |
| 9 | Profit Protect fill | At the NEXT bar's open, exact price; the pending fill takes precedence over all stop/TP1/EXIT evaluation on the fill bar — `modeb_engine.py:272-298` | `v54_exit_tracker.py:141-147` (fills at `float(bar["open"])` and returns) |
| 10 | Same-bar stop/TP1 conflict | **STOP WINS** — `modeb_engine.py:301` checked before `:314` | `v54_exit_tracker.py:150` before `:153` |
| 11 | TP1 bar | TP1 taken; NO stop/EXIT evaluation on the TP1 bar itself (falls through to the timeout check only) — `modeb_engine.py:314-326` | `v54_exit_tracker.py:157-164` ("Research: continue") |
| 12 | PP arming | Bar high reaching +1R (unrealized, full position) arms permanently; sticky; evaluated BEFORE the pending-exit fill and before the TP1 check on the same bar — `modeb_engine.py:263-269` | `v54_exit_tracker.py:189-197` (called at `:134`, before the pending-exit check at `:141`) |
| 13 | Scanner EXIT gating | EXIT sets a pending exit ONLY if PP is already armed; pending fills at next bar's open — `modeb_engine.py:327-330,349-352` | `v54_exit_tracker.py:165-167` (full), `:171-174` (runner) |
| 14 | Runner stop | Runner keeps the STRUCTURAL stop — never breakeven, never trailed — `modeb_engine.py:332-348` | `v54_exit_tracker.py:169-170`; frozen in `v54_spec.md` §3 |
| 15 | 30-bar timeout | Fires when `bars_held` reaches 30 — i.e. on the **30th processed bar** (entry bar = #1) — at that bar's **close**. Evaluated after stop/TP1/EXIT on the same bar, so stop wins a bar-30 tie. Reason `TIMEOUT` (`time` full / `runner-time` runner) — `modeb_engine.py:356-383` | `v54_exit_tracker.py:178-183` |
| 16 | MFE/MAE | Tracked on every processed bar INCLUDING the entry bar, from bar high/low vs entry; MAE is ≤ 0 by construction (low ≤ open = entry) — `modeb_engine.py:258-259` | `v54_exit_tracker.py:130-131` |
| 17 | Rounding | `blended_r`/`partial_r`/`runner_r`/`mfe_r`/`mae_r` rounded to 4dp — `modeb_engine.py:381-383` (`_round4`) | `v54_exit_tracker.py:215-225` (rounded in the exit record; stored raw while open) |
| 18 | Slippage | Zero everywhere (matches live) | Zero everywhere |

## 4. Live-vs-realistic gap handling — quantified on real data

Primary (`realistic_gaps=False`) is byte-faithful to live, including live's
optimistic gap-through-stop fill at the stop price. The realistic variant
(`realistic_gaps=True`) fills gap-through-stop at the bar open beyond the
stop and gap-through-TP1 at the open. Both variants were run over the exact
live bar sequences of all 15 forward-test positions
(`compare_live.py`, `comparison_report.json`):

- **Gap-through-stop events (3): CRM, BP, USO** — all three were live
  "stop" exits credited at **−1.00R** (fill at stop). Realistic fills at the
  gap open: CRM −1.4305R (open 244.18 vs stop 246.82), BP −1.4552R (open
  44.69 vs stop 45.00), USO −1.4122R (open 148.88 vs stop 151.21).
  **Live's convention flatters each such exit by ≈ +0.41–0.46R** (mean
  +0.43R). Sample is tiny (n=3) but the direction is structural: any
  gap-through-stop is credited −1.00R by live regardless of gap size.
- **Gap-through-TP1 (1): RBLX** — live TP1 level 50.734; realistic limit
  fill at the gap open 50.90 (+0.166 price improvement on the 50% partial).
  Position still open (runner riding), so no blended-R delta yet; the
  improvement would add ≈ +0.02R to blended R if the runner exited at the
  same price.
- Net on the 15 live positions: 4/15 (27%) differ under realistic gaps.

## 5. Unit tests — 31/31 passing

`tests/test_modeb.py` (run: `python3 -m pytest tests/ -q` from
`canonical_baseline/`). Synthetic bar sequences proving each rule:

- Stop always active: `test_stop_active_on_entry_bar`,
  `test_full_position_stop_before_tp1` (stop at exact price, blended −1.0)
- 50% at TP1 with R math: `test_tp1_takes_half_with_correct_r_math`
  (blended 0.5 = 1.0 + 0.5·(−1.0)), `test_tp1_runner_rides_to_timeout_math`
  (blended 1.75 on runner-time)
- +1R arms PP, sticky: `test_plus_1r_arms_pp_and_is_sticky`,
  `test_no_arm_below_1r`, `test_arm_on_tp1_bar_counts`
- PP fills next-bar open, not the signalling bar:
  `test_pp_full_position_fills_next_bar_open` (exit at b2's open, blended
  R(109) = 0.9 full-position), `test_pp_runner_fills_next_bar_open`
  (blended 2.0), `test_exit_ignored_before_arming`,
  `test_pending_pp_fill_takes_precedence_over_stop_on_fill_bar`
  (gap-through-stop on the fill bar still fills PP at open: −2.0R, not −1.0R)
- Runner keeps structural stop: `test_runner_keeps_structural_stop`
  (survives a dip below entry, stops at 90 not breakeven),
  `test_no_evaluation_on_tp1_bar_itself`
- 30-bar timeout on the 30th bar: `test_timeout_fires_on_30th_bar_at_close`
  (exit at b29's close, bars_held=30), `test_no_timeout_before_30_bars`,
  `test_timeout_binds_on_winners_too`, `test_stop_beats_timeout_on_bar_30`
- Stop wins ties: `test_stop_wins_tie_full_position`,
  `test_stop_wins_tie_on_entry_bar`
- Gaps: `test_gap_through_stop_live_fills_at_stop` (−1.0R not −1.5R),
  `test_gap_through_stop_realistic_fills_at_open`,
  `test_gap_through_stop_realistic_runner`,
  `test_intrabar_stop_touch_realistic_fills_at_stop`,
  `test_gap_through_tp1_live_fills_at_tp1`,
  `test_gap_through_tp1_realistic_fills_at_open`,
  `test_gap_above_target_at_entry`
- Conventions: `test_entry_bar_counts_as_bar_1_and_mfe_mae_include_it`,
  `test_entry_at_or_below_stop_is_invalid`,
  `test_stop_never_moves_except_pp_or_timeout`,
  `test_entry_bar_idx_offsets_into_larger_frame`,
  `test_r_convention_full_position_pp`

## 6. Decision-packet comparison vs the live tracker — 122/122 (100%)

`compare_live.py` replays, for each of the 15 live forward-test positions
(4 closed, 11 open), the EXACT bar sequence the live tracker processed
(`v54_forward/state.json` → `processed_bars`, read-only) with the EXACT
per-bar `scanner_state` the harness fed it (`v53_state_for_bar` imported
read-only from `v54_forward_harness`; the EXIT trigger is pure
price-structure — `masterscanner_api.py` `exit_signal = price < e55 or
EMA21/55 bear cross` — hence regime-independent and faithfully
reconstructable). 4H bars re-downloaded with the harness's own call
(`eng.m53.download_data(symbol, "4h", "180d")`).

Compared per position: `bars_held`, `tp1_taken`, `plus_1r_armed`,
`plus_1r_bar`, `mfe_r`, `mae_r`; plus for closed trades `exit_reason`,
`exit_px`, `exit_bar`, `blended_r`, `partial_r`, `runner_r`,
`reached_plus_1r`. Also verified the entry-fill convention: live recorded
entry == entry bar's open for all 15/15 positions.

**Result: 122/122 checks matched, 0 mismatches — 100% decision reproduction.**
All 4 closed trades (CRM/VEEV/BP/USO "stop" exits) reproduce exit price, bar,
and blended R exactly; all 11 open positions reproduce bars held, TP1 state,
arming state and bar, and MFE/MAE (within half a rounding unit — live stores
in-flight MFE/MAE raw and rounds only at close; the engine rounds to 4dp
always). Full per-position detail: `comparison_report.json`.

Caveats: (a) the live tracker's last-processed bar for open positions may
have been a still-forming bar at the time — completed bars are immutable in
yfinance, so replay is exact for closed trades and for all completed bars;
(b) 15 positions is a small sample — the comparison proves implementation
fidelity, not statistical coverage of every path (the unit tests cover the
paths live hasn't exercised yet: PP fills, timeouts, ties).

## 7. Deliverables

- `canonical_baseline/modeb_engine.py` — the engine
- `canonical_baseline/tests/test_modeb.py` — 31 unit tests (passing)
- `canonical_baseline/compare_live.py` — decision-packet comparison script
- `canonical_baseline/comparison_report.json` — per-position comparison detail
- `canonical_baseline/ENGINE.md` — this file
