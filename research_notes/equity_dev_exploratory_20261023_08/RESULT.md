# EQUITY DEV EXPLORATORY DIAGNOSTIC — QF-EQUITY-DEV-EXPLORATORY-20261023-08 r1

**Labels: EXPLORATORY / 4-NAME CONVENIENCE SAMPLE / G4 UNADOPTED /
NOT VALIDATED EDGE.**

**States:** task SENT (Issue #1 comment 6373548773; Slack SENT TS
1792785447.545879, priority clarification TS 1792785628.548849) → ACK
(Slack TS 1792785844.209259; bridge `2cb0952`) → this RESULT.
Independent VERIFIED/PASS/HOLD is ChatGPT's/Claude's step, not claimed
here.

**Authorization:** Mike's direct equities-first decision relayed in
comment 6373548773. OFFLINE, DEV-ONLY, existing bytes only — **0 new
vendor calls, 0 new credits (program TD total stays 24), $0.** Sealed
holdout (HO) legs were never parsed for market content (integrity
hash-check against the archive manifest only). No SMCI, no crypto, no
250-symbol scan, no scope/production change, no shadow launch.

## Inputs (source pins)

- Bytes: qf-data-archive `captures/td_pilot_20261023/` at archive
  commit `45496f8` (pilot package `5d129fb`; adjudication -02
  `7823538`). Archive `SHA256SUMS` re-verified locally: **22/22 OK**.
- DEV raw bodies (sha256): NVDA `b1ecf7bf…`, TSLA `f6b1e64f…`,
  AAPL `97649d2f…`, SPY `2c6631dc…` — each equals its receipt
  `response.sha256`; receipts chain to manifest root `79ccdd12…`;
  request basis `adjust=splits`, interval `1h`, ET wall stamps.
- Frozen code (sha256, all on origin/main): `pine_backtest.py`
  `447a9a13…`, `scanner_rules.py` `62aa743a…`,
  `pine_stack/pine_stack.py` `839e4800…`, `pine_ranking/pine_ranking.py`
  `77afae0d…`, `pine_signal_quality/pine_signal_quality.py`
  `b1b39ee8…`, `pine_exposure/pine_exposure.py` `9f646161…`.
- Calendar: adopted pinned session table
  `research_notes/shadow_closeout_20261022/session_table.json`,
  sha256 `00c5555c…`, version `XNYS-751-UNION-20261021`; DEV segment =
  524 sessions, 2024-09-16 → 2026-10-16 (5 early closes at 13:00).
- Environment: stage venv python 3.12.3 / pandas 2.2.3 / numpy 1.26.4 /
  pandas_market_calendars 4.5.1; driver run under `unshare -n`
  (network namespace removed). Command:
  `unshare -n ./venv/bin/python run_diagnostic.py` (driver committed in
  this package). Two full executions produced byte-identical
  `results.json`.

## Phase 1 — DEV preflight (PASS, all four legs)

Admission = the generic -02 rule (bar-open instant ∈ expected starts
of its session under the pinned table; calendar only, no symbol/date
lists, no shape tests):

| Leg | Raw | Excluded | Admitted | Expected |
|---|---|---|---|---|
| NVDA/DEV | 3,654 | 1 | 3,653 | 3,653 |
| TSLA/DEV | 3,655 | 2 | 3,653 | 3,653 |
| AAPL/DEV | 3,655 | 2 | 3,653 | 3,653 |
| SPY/DEV | 3,655 | 2 | 3,653 | 3,653 |

Excluded rows are exactly the -02 enumeration (15:30 bar-opens on the
13:00 early-close dates 2024-11-29 ×4 legs, 2024-12-24 ×3 legs).
Admitted stamp sets equal the pinned-table expected set exactly (no
missing bars, no missing sessions, no duplicates, strictly
increasing). All OHLCV finite and positive; **zero zero-volume
admitted bars on any leg** (the SMCI provider-volume failure class is
absent here).

**VBASIS disclosure (carried, not waived):** all four legs remain
`CONVENTION_BREAK_SUSPECT` via VBASIS per -02 (checker candidate-2,
UNADOPTED — the candidate G4 checker is not treated as adopted).
Price-side convention evidence on the same bytes: STEP PASS, STEP-ALL
0 undeclared factor steps, `adjust=splits` in force. The data is an
exploratory candidate, NOT fully qualified; the diagnostic is
permissible as a labeled exploratory run precisely because it asserts
no G4 PASS and no validated edge.

## Phase 2 — real-input parity (PASS)

- 4H bars built ONLY by the frozen corrected constructor
  `scanner_rules.resample_closed_4h_session_anchored` (no legacy grid,
  no Yahoo fetch, no `backtest_cache`). Per leg: **1,043 bars**
  (519×2 + 5×1), grid equal to the pinned session table session by
  session (early-close days = exactly one 09:30→13:00 bar, by table
  comparison), first bar 2024-09-16 09:30 ET, last 2026-10-16 13:30 ET.
- Aggregation parity recomputed independently for **every** bar
  (4,172 bars): OHLCV + SessionVWAP exact — **0 bad bars**.
- Candidate parity: all 61 candidates re-verified against the frozen
  formulas at their recorded indices (signal true, entry = next-bar
  open, stop = signal close − 1.5·ATR, TP1 = entry + 2·ATR,
  entry_time = signal bar + 1, exit ≥ entry) — **0 failures**.
- C0 fidelity invariant on these inputs: `pb.simulate_portfolio`
  final equity == `simulate_stack` (no ranking/caps/gate) final equity
  = 9894.345967222389 — **PASS** (the stack's own C1 fidelity check).

## Phase 3 — the one run (frozen C1 configuration)

Unchanged rules end to end: V3.6 hybrid signal (frozen
`pine_buy_signal`), frozen exits (TP1 +2·ATR at 50%, trail 2.5·ATR
after TP1, close-based stop/EMA55/bear exits at next-bar open, gap-
below-stop entries skipped), frozen portfolio construction
(R1 rs_top2 ranking + R2 sector cap, no R3; 1% risk/trade, max 5
concurrent, 5% portfolio-risk cap, $10k start), frozen cost pair
4bps / 25bps one-way via `pb._outcome`. Effective signal span
2025-02-21 → 2026-10-05 (frozen 215-bar warmup over bars from
2024-09-16). SPY rs benchmark derived from the same admitted SPY
bytes (daily bars). Determinism: identical re-invocation reproduced
the taken set and final equity exactly.

| Leg | Trades | Win% | Exp net R | Gross exp R | PF | Return | Max DD | Exposure |
|---|---|---|---|---|---|---|---|---|
| 4bps | 61 | 42.6 | **−0.005** | +0.015 | 0.99 | −1.05% | 12.43% | 68.1% |
| 25bps | 61 | 42.6 | **−0.106** | +0.015 | 0.83 | −7.05% | 14.47% | 68.1% |

Per-symbol (all candidates taken; see below):

| Symbol | Candidates | Taken | Mean net R @4bps | Sum net R @4bps | Mean net R @25bps | Win% @4bps |
|---|---|---|---|---|---|---|
| NVDA | 22 | 22 | −0.132 | −2.903 | −0.199 | 31.8 |
| TSLA | 11 | 11 | −0.184 | −2.024 | −0.233 | 45.5 |
| AAPL | 12 | 12 | +0.418 | +5.019 | +0.327 | 50.0 |
| SPY | 16 | 16 | −0.024 | −0.377 | −0.217 | 50.0 |

Exits: 42 stop / 19 ema55-break; TP1 hit rate 42.6%; avg winner
+1.359R / avg loser −1.018R @4bps; avg hold 17.8 bars; skipped
gap-below-stop 0. Full per-trade ledger: `trade_ledger.json`.

**Read, with the labels on:** gross expectancy is ≈ zero (+0.015R)
and the frozen cost legs push it negative. On this small convenience
sample the frozen rules show no edge. That is a statement about these
61 trades only — see non-comparability.

## Non-comparability (registered, verbatim intent of the task)

This diagnostic is **not comparable to the frozen UX51 baseline (C1)
or to any 44/51-name validation**, and no figure here updates,
confirms, or refutes the C1 verdict:

1. **Universe:** 4 of 51 names — the only names with receipted DEV
   bytes. 47 UX51 members are missing, so the frozen ranking/sector
   layer operates on a truncated cross-section; in this run it never
   bound (61/61 candidates taken; 0 rank, 0 sector-cap, 0 risk,
   0 max-position skips) — the portfolio layer is effectively
   unexercised and the original-universe portfolio is NOT replicated.
2. **Window:** DEV only (2024-09-16 → 2026-10-16). The sealed
   holdout was not touched; no reserved fold was used for
   performance, parameter choice, or signal inspection.
3. **Bars:** corrected session-anchored constructor on the pinned
   calendar — not C1's UTC-anchored study grid (13:30/17:30 UTC with
   documented EST drift). Candle bytes differ from C1's by design.
4. **Benchmark:** SPY rs benchmark derived from the same admitted TD
   bytes, not the destroyed Yahoo benchmark cache.
5. **Qualification grade:** candidate-grade bytes (VBASIS disclosure
   above; G4 unadopted). Exploratory candidate data, not the frozen
   baseline's qualified standard.
6. **Engine construction:** positions still open at the window's last
   bar produce no candidate (frozen `gen_candidates` construction,
   identical to C1's bull-window treatment).

## Bounds kept

PAUSED production pins identical before/after (harness
`ce7c902c…`, PAUSE_NEW_ENTRIES present, RESUME absent). No new bytes,
no vendor calls, no credits, no production or frozen-scope change,
no shadow/observer launch, prior packages byte-untouched.

— Muse
