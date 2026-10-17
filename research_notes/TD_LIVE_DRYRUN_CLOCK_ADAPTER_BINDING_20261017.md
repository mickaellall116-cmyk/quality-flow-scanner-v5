# TD LIVE DRY-RUN CLOCK + ADAPTER BINDING — 20261017-19 r1

**Verdict: `LIVE_DRYRUN_CLOCK_ADAPTER_BINDING_TARGETED_PASS_OFFLINE`**
(core proof + all four regression matrices, twice under kernel
network denial, byte-identical to their pins.)

Spec: Issue #1 comment 6241928840
(`QF-TD-LIVE-DRYRUN-CLOCK-ADAPTER-BINDING-20261017-19 r1`).
Offline only. No live clearance existed for this task and none was
used: zero helper invocations, zero vendor calls, zero credits,
zero real-ledger writes.

## 1. Reproduction of the -18 false stale (deliverable 1)

Against the ORIGINAL adapter (`r4_dry_run_adapter.py`, -17 package)
fed the committed -18 status evidence (`facts.api_usage`,
timestamp 2026-10-17 21:01:03Z) over a fixture copy of the adopted
candidate ledger: **11/12**, gate 3 FAIL `ACCOUNT_EVIDENCE_STALE`,
receipt `evaluated_at` **2026-10-17T08:00:00Z**, `clock_mode`
`injected_test`, decision HOLD. True epoch conversion, stated for
the record: **1792224000 == 2026-10-17T08:00:00Z** (the -11
runner's adjacent comment claims 14:00:00Z; it is wrong).

## 2. Dedicated live adapter (deliverable 2)

`live_dry_run_adapter.py` (`e8605669…`):

- Loads the accepted r4 gate **directly** by exact path + sha256
  pin (`b5399645…`), private module name. Never imports the trial
  harness; `base_evidence()`/`Trial` do not exist in its world
  (AST audit trial + runtime trials prove the boundary).
- **Anchor:** read from the immutable executor evidence file —
  `facts.evaluated_at`, the epoch the executor recorded at its own
  live gate-3 evaluation. Must be a finite number (bool/str/NaN/
  missing → `ANCHOR_MALFORMED`). Cross-checked against the vendor
  timestamp under Policy A's own bounds (age > 3600 s →
  `EVIDENCE_STALE_BEYOND_MAX_AGE`; age < −60 s →
  `VENDOR_FUTURE_SKEW_BEYOND_TOLERANCE`). The same anchor drives
  the gate clock (`AnchorClock`, `advance()` refused) and the
  dispatch window (derived `[anchor−3600, anchor+3600]`, or a
  packet-declared window after a containment/span check —
  `STALE_DISPATCH_WINDOW` otherwise).
- Evidence fields built explicitly: packet identity + GO record
  from the executor packet (cross-checked against the gate's own
  constants); adjudication/run/manifest/supplement/driver/policy
  pins from the pin-loaded gate module; environment from the
  pinned NL lock file (`lock_copy.txt` freeze hash +
  `pandas_market_calendars` line) and the running interpreter;
  account section verbatim from the executor's status facts;
  credential/stop-rule/retention sections restated as the standing
  attestations of the adjudicated -05 packet. No hidden fixture
  constants; no wall clock anywhere in the evaluation path.
- The gate runs in its own dry-run seam (mode `test`, token None →
  decision ceiling `PASS_DRY_RUN`; it cannot arm or run a screen),
  with the -11 helper stub as the gate-9 preflight override (path +
  sha pinned in the adapter). The executor verifies the real
  sanctioned helper in its own HELPER_OK phase, as before.
- Evidence txn/candidate bindings cross-checked against the packet
  before any gate runs (`EVIDENCE_TXN_MISMATCH`,
  `EVIDENCE_CANDIDATE_MISMATCH`).

Same -18 facts through the new adapter: **12/12**, decision
`PASS_DRY_RUN`, receipt `evaluated_at` **2026-10-17T21:01:02Z**
(the anchor). The old adapter on the same facts still fails
(§1) — the diagnosis is preserved, not overwritten.

## 3. Executor candidate with bound adapter (deliverable 3)

`live_readiness_executor_r4.py` (`e792b8b2…`) = r3 (`8b01c6f5…`)
plus exactly the -19 deltas (exact diff:
`executor_r3_to_r4.diff`, 85 lines):

- `ADAPTER_PATH`/`ADAPTER_SHA256` constants in-source (adapter
  identity transitively covered by the executor source pin; any
  future clearance must pin the executor, hence the adapter).
- `_load_live_adapter()`: exact path, symlink refused
  (`ADAPTER_PATH_REFUSED`), sha mismatch refused
  (`ADAPTER_PIN_MISMATCH`), private-name load, `__file__` origin
  re-checked (`ADAPTER_ORIGIN_MISMATCH`).
- `validate_live_admission()` verifies the adapter BEFORE marker
  creation, the status boundary, or any mutation.
- `_dry_run()` live branch uses the pinned dedicated adapter; the
  trial-harness import is gone.
- All r3 URL-boundary, clearance/path-binding, lock-first,
  one-slot, journal/rollback/recovery and prohibited-scope
  behavior is byte-preserved (diff shows no other changes).

Binding trials: tampered adapter byte → `ADAPTER_PIN_MISMATCH`;
symlink at the adapter path → `ADAPTER_PATH_REFUSED`; a decoy
`live_dry_run_adapter.py` shadow on `sys.path` → ignored, pinned
origin loads.

## 4. Tests (deliverable 4)

`run_clock_adapter_trials.py`, run **twice under `unshare -n`**,
matrices **byte-identical** (sha256 `9d8d0eff…`):
**20 trials, 31/31 checks** — reproduction (§1), corrected 12/12
(§2), stale age 7200 HOLD, future-skew −61 s and −3600 s HOLD,
boundary age exactly 3600 s PASS, boundary skew exactly −60 s
PASS, malformed anchors (string / NaN / missing) HOLD, txn and
candidate mismatch HOLD, stale declared dispatch window HOLD,
adapter binding ok/tamper/symlink/shadow, AST no-harness audit,
and the real pilot ledger byte-identical (`7e5ccef0…`) after all
trials. Zero real ledger/helper/network/credit operations
(fixture ledger copies only; `unshare -n` throughout).

**Regression re-runs — GREEN, twice each, byte-identical to
pins** (copies in this package): r4 gate matrix `aafd4e1b…`
(46/46 trials, 332/332 checks); -13 transaction/exception/
recovery matrix `56084b75…` (45/45, 193/193); -15 path-binding
matrix `946baa91…`; -17 URL/placement matrix `e68ba5af…`. The
gate and -13 runners were executed from scratch copies/outputs
under /tmp so no prior package was written; the -15/-17 runners
resolve bases NOTES-relatively and were run in place with all
trial roots and matrix outputs under /tmp.

## 5. Scope confirmation

Offline/network-denied throughout; the sanctioned helper was never
invoked or imported (the gate-9 preflight override is the pinned
-11 stub, as in every prior dry-run); vendor/authenticated calls
0; credits 0; real ledger writes 0 (pilot ledger re-verified
`7e5ccef0…`); -16/-18 trees and commits `1ee6d39`/`4820437`
untouched; bases re-verified after all work: r3 executor
`8b01c6f5…`, r4 gate `b5399645…`, r4 runner `93b911e0…`, adapter
base `7a56d86a…`. No token, no `time_series`, no backtest/
performance/holdout, no production/trading, no Issue #9, no
merge/adoption. Deliverables uncommitted.

Failure memories `LIVE_DRYRUN_TEST_CLOCK_LEAK` and
`UNBOUND_DRYRUN_ADAPTER`: see `FAILURE_MEMORY_20261017_19.md`.
Proposal R7 (NOT AUTHORIZED, new txn
QF-TD-READINESS-LIVE-20261017-20) states plainly that any further
`/api_usage` call before the screen totals 53 against Mike's
52-credit ceiling and needs his separate decision.

## Cap disclosure

Wall: ≈23 min of the ≤25 cap (18:27:27 spawn → ~18:50 ET docs
final); **zero repairs** used — the -19 suite and every regression
passed first-run. One process note: the first background launch
of the -13 regression runner was started without its required
argv and died instantly with no side effects; it was relaunched
correctly (operator error in the test harness invocation, not in
any candidate code).
