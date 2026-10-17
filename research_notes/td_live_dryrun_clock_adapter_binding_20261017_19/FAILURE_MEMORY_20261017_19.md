# FAILURE MEMORY — 20261017-19 (clock + adapter binding)

## LIVE_DRYRUN_TEST_CLOCK_LEAK

The live readiness dry-run inherited the -11 TRIAL harness's frozen
clock. `run_dispatch_gate_trials_r4.py` sets `NOW = 1792224000` —
true conversion **2026-10-17T08:00:00Z** (the adjacent source
comment claims 14:00:00Z; it is wrong) — and `Trial.dispatch()`
injects `FakeClock(NOW)`. The -14 adapter wired the executor's live
dry-run through that harness, so in live run -18 the vendor
evidence (timestamp 2026-10-17 21:01:03Z, ~1 s old, executor gate 3
PASS at real UTC) was judged ~13 h stale by the dry-run's gate 3
(`ACCOUNT_EVIDENCE_STALE`), the dry-run scored 11/12, and the
transaction rolled back a sound, verified adoption.

Lesson: any component that evaluates LIVE evidence must derive its
evaluation instant from the evidence itself (here:
`facts.evaluated_at`, recorded by the executor at its own live
gate-3 evaluation), never from a harness default and never from an
unbound wall clock. Fixture clocks stay inside fixture runners;
a live path must have no import route to them. Proven by -19 trial
`repro_old` (original adapter + committed -18 facts → 11/12,
`ACCOUNT_EVIDENCE_STALE`, receipt `evaluated_at`
2026-10-17T08:00:00Z) vs `new_12of12` (dedicated adapter + same
facts → 12/12, receipt `evaluated_at` 2026-10-17T21:01:02Z, the
anchor).

## UNBOUND_DRYRUN_ADAPTER

The -14/-15/-17 executors loaded `r4_dry_run_adapter` by module
NAME through `sys.path` (`from r4_dry_run_adapter import ...`). Its
identity was recomputed and reported by hand in run memos but was
NOT enforced by the executor or bound by the clearance: different
adapter bytes at the same module name would have run silently.

Lesson: every code artifact in a live path is loaded by exact path
+ sha256 pin, verified before the run can reach a marker, a status
boundary, or a mutation, and the pin lives in the already-pinned
executor source so the clearance covers it transitively. The -19
executor candidate (`live_readiness_executor_r4.py`) verifies the
dedicated adapter during `validate_live_admission()` (pre-marker)
and again at `_dry_run()` load; tamper → `ADAPTER_PIN_MISMATCH`,
symlink → `ADAPTER_PATH_REFUSED`, shadow module → ignored (load is
by pinned path under a private module name, origin re-checked).
Proven by -19 trials `binding_ok`, `binding_tamper`,
`binding_symlink`, `binding_shadow`.
