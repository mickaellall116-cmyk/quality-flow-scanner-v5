# QF-TD-FRESH-FULL-MANIFEST-PREFLIGHT-20261016-03 r2 — targeted repair

**Verdict: `FRESH_FULL_MANIFEST_PREFLIGHT_PASS_R2`** (offline scope only; authorizes no live call)

Spec: GitHub Issue #1 comment `6225948851` (r1 source review / HOLD +
r2 dispatch), fetched via the public API and followed exactly.
r1 verdict repaired: `FRESH_FULL_MANIFEST_PREFLIGHT_HOLD_SOURCE_GAPS`.
r1 package (commit `7f5251f`) is preserved byte-identical — verified at
the end of this run: driver `a4dea1f1…`, manifest `71aade8b…`,
supplement `3cbdbf63…`, r1 matrices `b4aae1f9…` ×2.

## Gap 1 — account-shared locked limiter ledger (CLOSED)

The r1 `Limiter` was file-backed inside each run namespace and its
transaction had no ledger-level lock, so distinct runs/processes could
each spend against independent 8/min and 800/day budgets.

R2 contract (executable, in `preflight_driver_r2.py`):

- **Exactly one limiter ledger per account**, at an operator-pinned
  path **outside every run namespace**. `Runner` requires the path and
  refuses `SHARED_LEDGER_INSIDE_NAMESPACE` if it resolves inside the
  run namespace (proven by T29, zero calls, zero writes). The per-run
  owner flock remains separate and unchanged.
- **The complete transaction is locked**: load → check → reserve →
  atomic replace (tmp + fsync + `os.replace`) all run under an
  interprocess `flock` on the ledger's own lock file
  (`<ledger>.lock`), and the ledger is **re-read from disk inside the
  lock on every transaction**, so no process ever acts on a stale
  in-memory copy. Closing the fd (including on process death) releases
  the lock; the lock file is never deleted.
- **Corrupt/unreadable ⇒ HOLD, never reset**: any load failure raises
  `Refusal("LIMITER_LEDGER_CORRUPT")` at construction, at reserve time,
  and at count time; the corrupt bytes are never overwritten by the
  limiter (T22, T26, byte-compared before/after).
- A missing ledger is created empty inside the same locked
  transaction at first construction (r1 init semantics).

Real-process evidence (separate OS processes via `ledger_worker.py`,
two distinct run namespaces sharing the one account ledger, fixed
clock so all assertions are over totals, not timings):

- **T23 minute cap across processes**: two workers racing 8 attempts
  each ⇒ combined OK = **exactly 8**, the other 8 attempts WAIT,
  ledger holds exactly 8 reservations, rid set == union of both
  workers' OK rids, all unique — no lost or duplicated reservation.
- **T24 day cap across processes**: ledger preloaded to 795 for the
  day; two racing workers ⇒ combined new OK = **exactly 5**, combined
  REFUSED_DAY = 11, ledger stops at **exactly 800**, all 800 rids
  unique, new rids == union of workers' OK rids.
- **T25 crash persistence**: a worker reserves 3 credits then dies
  hard (`os._exit(42)`, no cleanup, no output file) ⇒ the 3
  reservations are intact in the shared ledger; a fresh process sees
  count 3 and can reserve a 4th — the lock and ledger survive the
  death.
- **T26 corrupt shared ledger**: garbage bytes before first use ⇒
  Refusal, bytes unchanged; after 2 live reservations, external
  corruption ⇒ the next reserve refuses `LIMITER_LEDGER_CORRUPT`,
  corrupted bytes unchanged (never reset).
- r1's T17 now preloads and spends against the **shared** account
  ledger (795 prior + this run): refuses at exactly 800 with only
  5 calls fitting — unchanged expectations, now against the shared
  path.

## Gap 2 — supplement exact pin enforced (CLOSED)

The r1 driver declared `EXPECTED_SUPPLEMENT_SHA256` but accepted an
already-parsed object and checked selected fields only. R2 changes the
interface: `Runner` receives the supplement as **canonical bytes** and,
**before any namespace creation or limiter access**, requires
(1) the bytes parse, (2) the bytes equal the canonical encoding of the
parsed object (`SUPPLEMENT_NOT_CANONICAL_BYTES`), and (3) SHA-256 of
the bytes equals `3cbdbf63fd49b021dc74f63727098551753949f8684967981c65f66101f95a86`
(`SUPPLEMENT_SHA_MISMATCH`). Only then is the supplement parsed and the
unchanged r1 semantic binding checks run.

Evidence:

- **T27 — mutations to formerly unchecked fields** (6 cases:
  `classifier_pins.collector_sha256`, `calendar.lineage_lock`
  (environment lock), `safety_design_binding.adapter_contract_sha256`,
  `class`, `lifecycle_event`, `status`): every case refuses
  `SUPPLEMENT_SHA_MISMATCH` pre-dispatch with **zero transport calls,
  zero namespace creation, zero ledger creation** (18/18 checks).
- **T28 — non-canonical bytes**: pretty-printed supplement ⇒
  `SUPPLEMENT_NOT_CANONICAL_BYTES`; unparseable bytes ⇒
  `SUPPLEMENT_UNPARSEABLE`; both with zero calls and zero writes.
- **T01** additionally asserts the enforcement pin itself
  (`H(supplement_bytes) == EXPECTED_SUPPLEMENT_SHA256`) and that no
  ledger file exists inside the run namespace.

Disclosed expectation deltas in the re-run r1 matrix (consequences of
the enforcement, not silent changes): T06/T07 supplement mutations now
refuse with `SUPPLEMENT_SHA_MISMATCH` instead of the r1 semantic codes
(the hash check fires first, by design); T13's proof-stripped
supplement is no longer classifiable at runtime — it is not the pinned
supplement, so it refuses pre-dispatch with zero calls (r1's
classification-disabled path is subsumed: with pinned bytes, the
calendar proofs are inside the pin). All other r1 trials keep their
r1 expectations verbatim.

## Full suite — twice under network denial

`unshare -n python3 run_trials_r2.py`, fake transport only:

- Run 1: **29/29 trials, 117/117 checks, all_passed = true**
- Run 2: **29/29 trials, 117/117 checks, all_passed = true**
- Normalized matrices **byte-identical** (both sha256 `5f53e3dd…`).
- Trial namespaces: 323 files per run; the only byte differences are
  the 6 race artifacts of T23/T24, where the *split* of wins between
  the two racing processes is genuinely nondeterministic (4/4 in
  run 1, 5/3 in run 2). Every check is over split-invariant totals,
  which held exactly in both runs. This is disclosed, not normalized
  away.
- Suite facts both runs: old SPOT8 state 11 files, byte-identical
  after; fresh digest distinct from the SPOT8 binding.

## Attempts and repair (all preserved)

- **Attempt 0** (`trial_matrix_attempt0_failed.json`): 17 trial
  errors — `Limiter.__init__` passed a non-tuple body to the locked
  transaction helper (`TypeError`). Preserved.
- **Repair (one episode, ≈4 minutes, inside the ≤10 allowance)**:
  (a) init body returns `(None, False)`; (b) a missing ledger is
  persisted empty inside the init transaction (r1 init semantics),
  found when attempt 1 failed T01/T17 on the not-yet-created ledger
  file. No trial, check, or evidence file was altered by the repair.
- **Attempt 1** (`trial_matrix_attempt1_failed.json`): 27/29 trials
  passed; T01/T17 failed on the missing-ledger-file defect above.
  Preserved.
- Attempts 2 and 3 are the definitive runs 1 and 2 above.

Total elapsed ≈21 minutes of the ≤25 cap (incl. the ≈4-minute repair
episode).

## Scope confirmation

Offline/fake transport/network-denied only. Zero vendor/Yahoo/model/
API calls beyond the public spec fetch; zero credits spent (the only
ledger ever written is the per-trial test ledger — the real live
credit ledger `research_notes/pilot_harness/credit_ledger.json` was
never opened for writing and still hashes to its r1 pin `7e5ccef0…`);
zero installs/downloads; zero live limiter/state writes; no
backtest/performance, tuning, holdout, production/trading, Issue #9,
merge/adoption, or PARKED-state use. No existing file was edited: the
r1 package and all prior evidence verified byte-identical; tracked
modifications in git status are the live harness's own runtime churn.
Deliverables are uncommitted in the worktree.

## Package (research_notes/)

- This memo: `TD_FRESH_FULL_MANIFEST_PREFLIGHT_20261016_R2.md`
- `td_fresh_full_manifest_preflight_evidence_20261016_r2/`:
  `preflight_driver_r2.py` (corrected driver, exact source),
  `ledger_worker.py`, `run_trials_r2.py`,
  `trial_matrix_run1.json`, `trial_matrix_run2.json` (byte-identical),
  `trial_matrix_attempt0_failed.json`, `trial_matrix_attempt1_failed.json`
  (the failed attempts' normalized matrices and failure records),
  `trials_run1/`, `trials_run2/`, `SHA256_MANIFEST.txt`.
