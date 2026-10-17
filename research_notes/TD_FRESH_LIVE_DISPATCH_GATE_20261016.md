# TD fresh live dispatch gate (-05 r1) — FRESH_LIVE_DISPATCH_GATE_PASS_OFFLINE

Task: `QF-TD-FRESH-LIVE-DISPATCH-GATE-20261016-05 r1` (Issue #1 comment 6227935189).
Verdict: **`FRESH_LIVE_DISPATCH_GATE_PASS_OFFLINE`** — offline readiness only.
This PASS authorizes no live call: the one capped $0 live screen still
requires independent review of this package and its own adjudicated
execution dispatch. No authenticated request was made; no credit was used.

## What was built

`dispatch_gate.py` — a fail-closed executable wrapper around the exact
-04 driver (`live_driver.py` sha256 `5fed4524…`, verified byte-identical
before and after). It closes the boundary gap named in the -04 review:
the -04 `Runner` accepted caller-supplied `account_mode`, a
caller-supplied clock, and an already-constructed armed transport, so
the 12-gate checklist was a document, not an enforcement. The wrapper:

1. **Clock.** Live mode uses the actual UTC system clock
   (`SystemUtcClock`). Any injected clock/factory/path override in live
   mode raises `TEST_SEAM_IN_LIVE_MODE` **before any file access**
   (trial F21). Fake clocks exist only behind `mode="test"`.
2. **One immutable evidence object.** The wrapper consumes one
   canonical-JSON pre-dispatch evidence object (non-canonical bytes
   refuse) and evaluates **all 12 gates independently** (no
   short-circuit), each against a recomputed pin or a read-only probe.
   Any FAIL or UNKNOWN → HOLD.
3. **Receipt before arming.** A canonical gate receipt (per-gate
   verdicts with evidence hashes, derived account mode, token check,
   decision) is written durably (fsync, exclusive-create) **before**
   any transport construction. Exclusive-create doubles as a replay
   guard (`RECEIPT_ALREADY_ISSUED`).
4. **Arming.** `LiveHttpsTransport(armed=True)` is constructed only by
   the wrapper's own factory, only after a PASS receipt is durable, and
   only with a `--dispatch` token = SHA-256 over (task, run_id,
   manifest digest, evidence digest, ledger path, dispatch window).
   Default/dry-run never arms (G01). `account_mode` is **derived** from
   the verified receipt (`"known"` iff gate 3 passed); `dispatch()`
   has no `account_mode` parameter (F22: passing one is a TypeError).
5. **Zero mutating access on failure.** On any HOLD the wrapper never
   constructs the Runner (no namespace created/written), never
   constructs a transport, and never writes the shared ledger (gate 4
   reads ledger bytes only — byte-identical before/after in every
   refusal trial). The real pilot ledger was hash-read only and is
   unchanged (`7e5ccef0…`); the old SPOT8 state tree is byte-identical.

## The 12 gates — enforcement and offline satisfiability

| # | Gate | Executable enforcement | Offline |
|---|------|------------------------|---------|
| 1 | Adjudicated execution packet | Packet fields vs pinned identity (run/manifest/supplement/entrypoint), ceiling == 51 == manifest budget, dispatch window contains evaluation instant | PASS on fixture packet |
| 2 | Authority recorded | Basis == Mike's standing 2026-10-14 capped-authority record, `re_requested == false`, ceiling/spend consistency | PASS on fixture record |
| 3 | Account plan/status/capacity | Timestamped evidence: plan Basic, standing good, age ≤ packet max (3600 s) vs the real/injected clock, remaining ≥ 51, minute cap == 8; stale/insufficient/partial → HOLD | Fixture evidence (live account state remains UNKNOWN until a live observation is recorded — no authenticated call was made) |
| 4 | Shared limiter state | Exact packet ledger path, outside the namespace; read-only structural validation; dispatch-day reservations + 51 ≤ 800; corrupt → HOLD, never reset | PASS on fixture ledgers |
| 5 | Environment reproduction | Lock + mechanism pins recomputed; all 11 wheelhouse wheels hash-verified vs the wheelhouse manifest; evidence freeze digest == H(lock bytes); interpreter `CPython 3.12.3`; pmc == 4.5.1 in lock | PASS by pin recomputation (no live venv exists in this sandbox; a live dispatch additionally requires the rebuilt env present — the recorded freeze is bound to the recomputed lock) |
| 6 | Source hashes | Manifest, supplement, driver, pilot_acquire, rate_limiter, prerequisites recomputed; collector recomputed from the pinned git commit blob `ab254c3:…/td_min_collector.py` | PASS |
| 7 | Calendar re-derivation | The 11 hash-verified wheels are extracted to a throwaway temp dir (no pip, no site-packages mutation, nothing persisted, temp deleted) and the pinned mechanism's `xnys_schedule` is executed there: 2026-07-03 must derive closed, 2026-07-02 open (control), pmc == 4.5.1; facts must match the supplement's pinned proof `36bc3a89…` | PASS — real derivation, derived closed=true / open-control=false / pmc 4.5.1 |
| 8 | Clean namespace / zero attempts / sole owner | State dir absent → PASS; else contents ⊆ runner-known files, binding identity match, recorded attempts == 0; state dir == old SPOT8 dir refuses outright. The Runner's own flock arbitrates a live second owner at construction (which happens only after PASS) | PASS |
| 9 | Credential / proxy boundary | Driver constants recomputed from the pinned module (endpoint, credential ref `custom.twelvedata`, allowed hosts), evidence declaration consistent, no `apikey=` in driver source | PASS on binding recomputation. Disclosure: `dynamic_credentials` is **not importable in the sandbox interpreter**, so helper presence in the live platform process is attested by the evidence record, not probed here |
| 10 | Adapter contract | Contract pin recomputed; driver's `build_url` query-key order == the contract's fixed order prefix; method GET | PASS |
| 11 | Stop rules armed | The wrapper constructs only the Runner of the hash-verified pinned module; evidence stop-rule declaration must be fully armed | PASS |
| 12 | Retention acknowledged | Evidence record: acknowledged, private-screen-evidence scope, no indefinite-retention claim, no redistribution | PASS on fixture record |

## Proof (offline, kernel network denial)

25 trials, **170/170 checks**, run twice; matrices byte-identical
(sha256 `0ba1b817…` both runs).

- **G01 green dry-run:** 12/12 PASS → `PASS_DRY_RUN`, receipt written,
  factory never called, ledger unchanged, namespace never created.
- **G02 green fake dispatch:** token valid → factory called once,
  **after** the PASS receipt existed (factory read it) → full ordered
  51-request lifecycle through the wrapper: COMPLETE, 49 COMPLETED +
  2 CLOSED_DAY_EVIDENCED, exactly 51 reservations. **Replay** of the
  same evidence+token → HOLD (gate 8 `PRIOR_ATTEMPTS_PRESENT` +
  `RECEIPT_ALREADY_ISSUED`), zero transport.
- **G03 default-factory wiring:** with the default factory, a spy
  `LiveHttpsTransport` installed on a spy copy of the pinned module was
  constructed exactly once, `armed=True`, **with the PASS receipt
  already durable**; its dead-network refusal stopped the batch at
  exactly 1 attempted call (`HOLD_TRANSPORT_TIMEOUT`) — the -04 stop
  rules firing through the wrapper.
- **Per-gate refusals** (each: HOLD + zero namespace creation + ledger
  byte-identical + zero transport construction): packet digest (1),
  authority (2), account capacity / stale / partial-UNKNOWN (3),
  ledger corrupt / day-capacity / inside-namespace (4), env freeze
  record (5), manifest tamper (6), namespace foreign files / SPOT8
  path (8), credential ref (9), adapter tamper (10), stop rules (11),
  retention (12). Calendar fault-injection trips gates 5+7 together
  (wheelhouse tamper: `WHEELHOUSE_HASH_MISMATCH` +
  `DERIVATION_WHEEL_HASH_MISMATCH`; patched mechanism:
  `ENV_MECHANISM_PIN_MISMATCH` + `DERIVATION_CALENDAR_DERIVATION_FAILED`)
  — gates 5 and 7 share evidence sources by design; gate 7's
  independent content (derivation vs pinned proof) is exercised in
  every green run.
- **Token:** window-shifted token → all gates PASS, token invalid,
  HOLD, zero construction (F19). Evidence edited after issuance
  (capacity inflated, re-canonicalized) → token no longer binds →
  HOLD (F20).
- **Boundary:** live mode + injected clock refuses pre-access (F21);
  caller `account_mode` is a TypeError and the disarmed candidate alone
  still refuses `TRANSPORT_NOT_ARMED` (F22). Language-level note: a
  caller who imports `live_driver` directly bypasses any wrapper by
  construction; the enforcement boundary is the adjudicated live
  process running this wrapper as its entrypoint — the same boundary
  the -04 review specified.

## Attempts and repair (all preserved, disclosed)

- **Attempt 0** (`dispatch_matrix_attempt0_failed.json`, 20/25): a
  wrapper defect — the calendar memo key concatenated bytes + str
  (TypeError), so gate 7 read `DERIVATION_UNAVAILABLE` in the 5 trials
  that needed a PASS or a token check. Fixed in one line.
- **Attempt 1** (`dispatch_matrix_attempt1_failed.json`, 24/25): a
  trial-harness defect — the spy transport raised the harness module's
  `TransportTimeout` class while the Runner catches its own module
  instance's class; the spy now raises the installed module's class.
- Both fixes were inside one repair window of ≈3 minutes (allowance
  ≤10). No trial, check, gate, or evidence was altered by the repairs;
  the final matrices are from the repaired code, run twice.
- Total elapsed ≈25 minutes of the ≤30 cap.

## Scope confirmation

Offline only, both final runs under `unshare -n`. Zero
vendor/Yahoo/model/API calls beyond the public spec fetch; no
credentials used or read (the vault surrogate was never invoked; the
armed transport's network path was never executed — G03's spy refuses
before any call); zero credits/spend; zero installs/downloads (gate 7
extracts already-held, hash-verified wheels to a temp dir and deletes
it — disclosed above); zero live writes (real pilot ledger hash-read
only, unchanged; ledger writes occurred only in trial temp namespaces);
no backtest/performance/holdout/production/trading/Issue #9;
no merge/adoption; no PARKED reuse (the parked derivation candidate
`ce9c02a` was never read or touched). Prior packages verified
byte-identical before/after: -04 driver `5fed4524…`, -04 matrices
`1c3c76c2…`, r2 driver `50463ce9…`, supplement `3cbdbf63…`. Deliverables
left **uncommitted** in
`research_notes/td_fresh_live_dispatch_gate_evidence_20261016/`.
