# VERDICT — corrected shadow parity probe (8339d1f): **HOLD**

Independent verification by Muse, 2026-10-22 (offline, `unshare -n`,
pinned venv CPython 3.12.3 / pandas 2.2.3 / PMC 4.5.1). Scope: ChatGPT's
corrected probe on branch `research/shadow-parity-probe-20261022` tip
`8339d1f19b75b1d9b4177489c5c39408e94b5cf5` (Issue #1 comments 6355735192
+ 6355785285), and the -80 successor candidate it gates (798de18).
Staged existing bytes only. No vendor/network, no holdout, no
performance, no production change, no launch. Legacy PAUSED production
untouched (V9).

## The one verdict: HOLD

The probe artifact itself is sound (V1–V4, V6, V7 pass). The gate
fails on two decisive checks in the successor the probe is meant to
qualify:

### FAILING CHECK 1 — market-frame failure does NOT exit before the cohort scan (V5)

`LiveAdapter.fetch()` (successor runner, sha256
`6b7584ac…`) computes `market_ok` and then calls
`eng.v54_scan_symbols(universe, …)` **unconditionally**. Spy proof
with a stubbed pinned engine, two failure modes:

| market frame | scan calls | symbols scanned | required |
|---|---|---|---|
| raises RuntimeError | 1 | **250** | 0 |
| returns None | 1 | **250** | 0 |

`market_ok` is honestly reported False and the core would record the
cycle DEGRADED — but the full 250-name cohort scan (the expensive,
data-pulling step) has already run. The fast-exit requirement is not
met. This is the same defect ChatGPT flagged as item 3 in 6355735192;
it is still present in the 798de18 bytes.

### FAILING CHECK 2 — no hash-chained provenance in the shadow log (V8)

Across a full dry-run + T0 test battery, the append-only shadow log
held 7 records (`shadow_signal` / `shadow_refusal` / `shadow_cycle`);
**0 of 7 carry any hash-chain field** (no `hash`, `prev_hash`,
`record_hash`, `chain_hash`, or `sha256` key). Provenance today =
stack-pin verification (V8 partial PASS: `verify_pins()` returns the
6 pinned digests, all matching) + fsync'd append-only log. A
hash chain / external first-cycle anchor does not exist in these
bytes.

### Supporting finding (not counted decisive)

The successor core's own `_validate_candidate` checks grid **opens**
only; it never verifies the bin close. A 09:30→10:30 row with
close > T0 and ≤ now would be recorded. The corrected probe does
check bin closure (09:30→13:30, 13:30→16:00) — the successor core
alone does not.

## What passed

- **V1 probe synthetic suite: 8/8 PASS** (exit 0), run from the exact
  8339d1f bytes (probe sha256 `b4c87a8d…`, test sha256 `606065cc…`).
- **V2a witness, ChatGPT's facts exact**: probe on the ba4276f blob
  of `forward_test/v54_ai_observer.json` (sha256 `d7e65070…`) →
  HOLD as designed; 37 rows; opens **06:30 ×15, 10:30 ×11,
  14:30 ×11**; durations **4.0h ×26, 1.5h ×11**; all
  `2026-09-15-v54`; 37/37 `off_frozen_0930_1330_grid`.
- **V2b/V2c/V2d true grid from stored bytes**: current observer
  export identical distribution (37). Full stored signal log
  `v54_forward/forward_test.jsonl`: **38** qualified rows, opens
  06:30 ×16 / 10:30 ×11 / 14:30 ×11, durations 4.0h ×27 / 1.5h ×11.
  Latest ordinary cycle output (`latest_v54_signals.json`,
  2026-10-22): 2 signals, both **14:30→16:00** legacy — the live
  pipeline still emits the legacy grid today.
- **V3 real adapter replay**: pinned `v54_engine.py` (sha256
  `bde32883…`, matches the successor's PINNED_STACK) —
  `v54_qualified_signals` passes all 38 stored rows and excludes 3
  fabricated ineligible rows (41 in → 38 out). Probe on the adapter
  output: HOLD, same legacy distribution. The adapter is a faithful
  filter; the grid defect is upstream in resampling, exactly as
  ChatGPT's root cause states (verified in source:
  `masterscanner_api.py:98` and `v54_forward_harness.py:708` call
  legacy `resample_closed_4h`; `scanner_rules.py:155` defines the
  session-anchored variant).
- **V4 corrected resampler parity**: `resample_closed_4h_session_anchored`
  on synthetic 1h bars gives exactly **09:30→13:30 and 13:30→16:00**
  on a normal day, invariant across the 2026-11-01 DST change. The
  legacy function on the same multi-week window drifts
  (09:30/13:30 in EDT → **08:30/12:30** in EST); the anchored one
  does not move. Early-close 2026-11-27: the anchored bin contains
  exactly the four hourly bars ending 13:00.
- **V6 cohort: 250 unique names** via the runner's own
  `frozen_universe()`: UX51 = 51 unique + X2 = 199 unique, union
  250, unique 250, overlap 0.
- **V7 T0 strictness (successor core)**: bar closing exactly at T0
  refused `PRELAUNCH_SIGNAL` (strict >); valid post-T0 bar recorded;
  unclosed bar refused `PARTIAL_BAR_NOT_CLOSED`; DEGRADED cycle
  records 0 signals; reopening with a different T0 raises
  `ShadowError`; same T0 reopens. Successor acceptance suite
  re-run: **24/24 PASS** — note its J2 fetch-count test exercises
  the FixtureAdapter path only, which is how the V5 defect survived
  a green suite.
- **V9 PAUSED production untouched**: 13 files (harness
  `ce7c902c…`, engine, rules, state, logs, exports) sha256-identical
  before/after this verification; `PAUSE_NEW_ENTRIES` sentinel
  present, `RESUME_NEW_ENTRIES` absent.

## Divergences from ChatGPT's stated facts (plain)

1. **38 stored signals, not 37.** The 37-row witness is the
   observer *export*; the stored forward log holds 38 qualified
   signals (one additional 06:30 4h row). ChatGPT's numbers are
   exact for the artifact they cited; the fuller stored record is
   one row larger, same grid, same verdict.
2. **The legacy defect is window-dependent.** On a single-day
   synthetic window the legacy resampler lands on the correct
   09:30 grid; drift appears on multi-day windows spanning a DST
   change (demonstrated 09:30→08:30). The production 06:30 grid is
   proven by the stored bytes themselves (V2), and the mechanism
   (UTC `origin='start_day'` anchor) is confirmed in source — but
   an exact synthetic 06:30 reproduction was not produced, and none
   is claimed.
3. **Early closes remain uncertified by the probe** (disclosed in
   the probe itself): a legitimate 09:30→13:00 early-close row is
   flagged `wrong_session_bin_close`. Pinning the adopted 751-session
   calendar for early closes is still required before any readiness
   claim. Not counted as a probe failure.

## What would flip this to GO

1. `LiveAdapter.fetch()` returns DEGRADED **before** any cohort scan
   when the market frame fails — proven by a spy test with
   scan_calls == 0 on both failure modes, added to the successor
   suite (the current suite's fetch-count test does not cover the
   live adapter's failure path).
2. Hash-chained provenance implemented in the shadow log (each
   record carrying the previous record's hash) or an equivalent
   external first-cycle anchor, demonstrated end to end.
3. (Supporting) successor core validates bin closure, not opens
   only — or formally delegates that check to the corrected probe
   in the cycle path.

Nothing here launches the shadow, touches the PAUSED legacy cohort,
or changes any gate. Adoptions remain HOLD.
