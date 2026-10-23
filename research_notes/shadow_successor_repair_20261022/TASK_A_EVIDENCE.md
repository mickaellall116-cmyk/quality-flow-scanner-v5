# TASK A — read-only inspection of the ordinary-cycle output (2026-10-22)

Requested by ChatGPT (Slack 22:36 ET + Issue #1 comment 6356026005;
verdict context comment 6356126182). READ-ONLY: nothing inspected
was written. All reads taken 2026-10-23 02:49–02:59Z on this VM.
No provider calls of any kind.

## 1. `latest_v54_signals.json` — EXISTS, fresh, healthy, PAUSED

- Path: `~/workspace/quality-flow-scanner-v5/latest_v54_signals.json`
- sha256 (cycle-759 bytes): `aa45f03d83d5774ae11b92d3995f68d015c7b46e00bf49c01e4f61df161a4aa9`
- Size 5,815 bytes; `generated_at` 2026-10-23T02:49:25Z (file is
  rewritten every hourly cycle; this hash pins the cycle-759 bytes).
- Envelope schema (15 keys): scanner "Quality Flow Scanner V5.4",
  scanner_version 5.4, rule_version `2026-09-15-v54`, interval 4h,
  period 180d, source `v54-engine-local`,
  uses_closed_4h_candles true, signal_id
  `v54:4h:2026-10-22T16:00:00+00:00:2026-09-15-v54`,
  market_regime block (RISK-OFF, gate BLOCK, QQQ −2.843%,
  SPY −1.182% session returns), count, grades, results,
  forward_test block.
- Result rows: 48 keys each (full V5.4 row: symbol, theme,
  timeframe, signal_id, bar stamps, state, entry, protection,
  price/stop/tp1, buy_zone, EMAs, ADX, rel_vol, risk_reward,
  market_gate/regime, daily/weekly trend, 15m confirmation,
  premarket block, v53 block, v54_eligible/grade/label/reasons).
- Current cycle results: count = 2 — ABBV (grade B) and AMT
  (grade A), both `signal_bar_start_at` **2026-10-22T14:30:00-04:00**
  → close 16:00 ET. That is the legacy 1.5h final bin: the live
  envelope itself confirms **LEGACY / OFF_GRID** production output
  (06:30/10:30/14:30 starts), exactly as the witness showed. NOT
  relabeled, NOT counted as corrected-grid evidence.

## 2. Cohort / health (from the envelope's forward_test block)

- universe "UX51+X2", universe_size **250**; cohort_sizes
  UX51 **51** + X2 **199** (disjoint per verify V6: union 250,
  overlap 0).
- cycles_run **759**; cycle_status **HEALTHY**; errors [];
  coverage: expected 250 / fresh 250 (all via prefetch),
  benchmarks 2/2, degraded_symbols [], unresolved_security_events
  [], global_provider_status "ok", market_data_gap "",
  cycle_duration_s 489.
- signals_logged (cumulative) **38**; grade_counts A 9 / B 26 / C 3.
- Open positions: SHOP (2026-10-15), TEAM (2026-10-16).
  Pending: MSFT (2026-10-19T10:30 bar).

## 3. Heartbeat artifacts

- `v54_forward/last_cycle.json`: finished_at
  2026-10-23T02:49:27Z, cycle_status HEALTHY, new_signals 0,
  opened 0, errors [], publish {ok: true, pushed: false,
  note: "up to date"}.
- `v54_forward/last_cycle_summary.json`: same health/coverage;
  names this file as its output target and the three
  forward_test snapshot files.

## 4. Pause state — mechanically ENFORCED and visible in the output

- `forward_test/PAUSE_NEW_ENTRIES` present (533 bytes, Oct 19);
  `forward_test/RESUME_NEW_ENTRIES` absent.
- Envelope + heartbeat agree: entries_paused true,
  entries_suppressed true, pause_control "sentinel",
  suppression_reason "entries paused: PAUSE_NEW_ENTRIES sentinel
  present", fills_blocked_by_pause = [MSFT 2026-10-19 signal].
  The MSFT fill has now been blocked for 28+ cycles past the
  earlier 53-block count — the gate is still doing its job.

## 5. Independent passive audit (ChatGPT's auditor, 655345b)

- `passive_cycle_audit.py` + its test file extracted read-only
  from branch tip 655345b (core blob 8c6820…). Its suite:
  **11/11 PASS** locally.
- CLI run read-only against the actual file at 02:58Z: exit 2,
  verdict **HOLD** (the tool exits 2/HOLD by design until a
  corrected producer + independent attestation exist). sha256
  reported by the auditor = aa45f03d… — identical to §1.
  qualified_count 2, no bad rows. Named reasons:
  - `COMPLETE_COHORT_AND_MARKET_NOT_PROVEN` — the envelope's
    coverage.market_data_gap is the empty string "", where the
    auditor accepts only False/None. A schema-representation
    mismatch worth naming: the harness's "no gap" encoding is
    not the auditor's.
  - `NO_INDEPENDENT_CORRECT_GRID_ATTESTATION` — expected: the
    producer is legacy-grid (§1) and no corrected-grid pins have
    been adopted.

## 6. Raw 1h availability — RAW_1H_NOT_AVAILABLE (for this purpose)

Question: do staged raw 1h frames exist locally from which the
corrected 09:30 grid could be built for the 250 cohort, fully
offline? **No.** What actually exists:

| Store | What it is | Why it does not qualify |
|---|---|---|
| `backtest_cache/` (D1) | ABSENT — directory does not exist | Destroyed with the prior VM; only 52 SHA256 pins survive |
| `pine_1h/` | only `__pycache__/fetch_1h.cpython-312.pyc` | a fetch script, zero data files |
| TD Day-1 probe store (`~/workspace/qf_td_probe_d1_20261021/store/`) | real raw 1h payloads, 3 symbols only: NVDA 917 bars 2023-12-13→2024-06-21; TSLA 911 bars 2022-03-07→2022-09-09; AAPL 903 bars 2026-02-19→2026-08-24 (as stored) | 3 of 250 symbols; split-qualification probe windows, not 180d scan frames; the NVDA window overlaps the SEALED holdout (2023-10-19→2024-09-15) — using it for signal generation would breach the holdout firewall |
| `research_notes/twelve_data_stage0/snapshots/aapl_1h_2026-09-08_2026-10-06.json` | 1 symbol, ~1 month | smoke-test snapshot, not cohort data |
| `pine_entry_timing_backtest/cache/h4_*.pkl` | 14 watchlist symbols | already-aggregated 4H (legacy construction), NOT raw 1h |
| `v54_forward/lonewolf_cache/` | daily pickles (ANET/SPY/XLK) | wrong timeframe, wrong purpose |
| live harness itself | downloads 1h via prefetch each cycle | persists NO 1h frames — in-memory only; nothing staged to reuse |

Determination: **RAW_1H_NOT_AVAILABLE** for offline corrected-grid
construction over the cohort.

Smallest gated route (NOT authorized here, stated for the
record): the already-specified TD capture under the -88 manifest
(146 credits expected / 289 worst; ceiling 300 vs ~320 and the
pilot GO are Mike's decisions), or a separately authorized
one-time Yahoo 1h capture written to the private qf-data-archive.
Either produces immutable staged 1h frames the session-anchored
resampler can consume offline. Until one is authorized, the
passive intake of §1–§5 is diagnosis only: legacy-grid output
cannot be promoted to corrected-grid shadow signals by any
relabeling.

## 7. Production integrity during this inspection

The 7 production code modules hash-identical to their pins
before AND after this whole task (harness ce7c902c…, engine
bde32883…, rules 1b55dedc…, scanner_rules 62aa743a…,
masterscanner_api c3e95b25…, universe 44b0d8ba…, hybrid
9140504f… — full table in REPAIR_NOTES.md). Live artifacts
(latest_v54_signals.json, state.json, forward_test.jsonl,
snapshots) rotate hourly by the harness's own cycles; they were
only read.
