# -51 r1 — continuation memo (WORK RESULT)

Task: `QF-TD-ROUTE-TRANSACTION-GIT-AWARE-STAGING-CONTINUATION-20261020-51` r1
Spec: Issue #1 comment `6290393927` (2026-10-20T12:02:56Z), followed exactly.
Pre-execution commit: `265c32fe036452e4e9611fae0f9ce9f2e2957db8`
(driver v3 `65138541…` + `driver_v2_v3.diff` + `run_proof.sh` +
`STAGING_PLAN.md`, committed before execution per spec §B, remote-verified).

## Terminal verdict (verbatim)

**`TD_ROUTE_TRANSACTION_PROOF_HOLD__STAGING_WORKTREE_ADD`**

One continuation attempt was made. It stopped at its first material
failure — construction of the git-aware shadow — before the §B
preflight, before the collector-blob proof step, and before any suite.
No second attempt, no in-run repair. Repair minutes: **0**.

## What executed (all PASS, recorded in `proof_results.json`)

- **Environment:** one offline attempt inside `unshare -n`,
  2026-10-20T12:38:11Z → 12:38:35Z. Probes `NETWORK_DENIED`
  (connect Errno 101, DNS Errno -3; curl exit 7). Venv built
  `--no-index --require-hashes` from the pinned wheelhouse:
  CPython 3.12.3 / pandas 2.2.3 / PMC 4.5.1, `FREEZE_EQUALS_LOCK`
  (TD lock `08b38cfa…`).
- **Hash gates (§A freeze): ALL PASS, zero mismatches.** -48 package
  manifest 19/19; route pins 3/3; -49 candidates 2/2; frozen full-length
  pins (validator `ca3bafd8…`, CLI constructor `3f432e7e…`, entrypoint
  v7 `84ccd2c6…`); frozen checker driver v2 `68998a90…` byte-identical;
  -48 candidate pins (supplement `55ad6f40…`, driver `d11c6b58…`, gate
  `94ef967c…`, adapter `6980b5b3…`, executor `bbc23616…` — full hashes in
  `proof_results.json`); v3 manifest `9573118c…` canonical; -46 F1
  object `bd550433…` re-verified; wheelhouse manifest `210b8273…`.
  Pilot ledger before: `7e5ccef0…`.
- **P0 receipt verification (spec §C): PASS.** The accepted -50 record
  verified (task id, HOLD__P1_GATE_REGRESSION verdict, P0 + hash-gates
  sections present, driver-v2 hash match); v3 status read live =
  `IMPLEMENTED_BY_CANDIDATE__EXECUTION_PROOF_PENDING`. The P0
  semantic-delta proof was NOT repeated, per spec.

## First failure (verbatim, from `proof_results.json`)

Key: `STAGING_WORKTREE_ADD`. The orchestrator's
`git -C <repo> worktree add --detach /tmp/td51_stage/shadow` exited 128:

```
error: unable to write file tests/test_simulate_stack_20261004.py
error: unable to write file tests/test_top_broad_membership_20261004.py
error: unable to write file tests/test_v54_forward_harness.py
error: unable to write file top_broad_experiment.py
error: unable to write file top_broad_performance.py
error: unable to write file top_broad_run.py
error: unable to write file v54_forward_harness.py
Updating files: 100% (11601/11601)
fatal: Could not reset index file to revision 'HEAD'.
```

(stderr tail as recorded; the full recorded stderr is in
`proof_results.json` → `first_failure.detail`.)

**Characterization (post-hoc, labeled):** `/tmp` on this host is a
512 MB tmpfs. The scanner repo's working tree is 506 MB (11,601 files)
and the proof venv under `/tmp` occupies 174 MB, so a full git-worktree
checkout rooted under `/tmp` cannot fit alongside the venv — git's
checkout ran out of writable space partway and could not reset the
index. This is a stage-placement/environment failure of the
orchestrator's shadow location, NOT a candidate, checker, gate, or
spec defect, and it is not evidence about P1. The -51 prediction
(P1 = 46/46 in a git-aware stage) remains **untested**: the shadow was
never created, so the §B preflight checks (inside-work-tree,
derived-REPO equality) and the standalone collector-blob proof step did
not execute inside this attempt, and P1/P2/P3 never ran. (Out-of-band,
before the attempt and not part of it: the same blob read from the main
repository object store hashes to
`b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c` =
PIN_COLLECTOR — the object exists and is correct; only the shadow
placement failed.) Any successor attempt would need the shadow rooted
on a filesystem that can hold a full checkout (e.g. the workspace
disk); releasing one is adjudication's call, not this run's.

## Cleanup / repository state (recorded in `proof_results.json`)

The partial shadow was disposed of by the driver
(`staging_cleanup.shadow_removed: true`); `git worktree list` confirms
no lingering registration. Main working tree status hash UNCHANGED
pre/post (its pre-existing `UU forward_test/kama_shadow.json` merge
state untouched); the td51_wt repo HEAD remained at the pre-execution
commit `265c32f…` throughout; post-run rehash of pinned originals
(construct_4h `d47e8df1…`, validate_input `1b83cdcd…`, pilot_build
`257d5bb9…`, verify_sources `a0bd2e4c…`, ledger `7e5ccef0…`) matches
pre-run values (see `env_receipt.txt` tail).

## Timeline / elapsed

Spec issued 12:02:56Z; this execution session dispatched 12:30:05Z;
pre-execution commit remote-verified ~12:36Z; the one attempt ran
12:38:11Z → 12:38:35Z (24 s); results commit `789726b…` remote-verified
12:40:00Z. Elapsed: dispatch → remote-verified results = 9 min 55 s;
spec issuance → remote-verified results = 37 min 04 s — inside the
≤45-min cap on both conventions. (Correction: this paragraph's first
version estimated ≈16 / ≈43 min before the final timestamps existed;
the figures here are computed from the recorded timestamps.)

## Prohibitions — all honored

No candidate/checker/manifest/comparator file changed (driver v3's
staging-topology diff was committed pre-execution per spec §B; the
frozen v2 checker was hash-verified, not modified). Nothing adopted or
re-pinned. No live chain executed. E1 and the full A/D/B/NLQUAL
families not repeated. **REQ-S2 untouched, unimplemented, recorded as
the continuing hard HOLD.** No vendor/API/model calls during execution
(only the pre-run read-only public fetch of spec comment 6290393927);
0 credits; no real market data; no SPT-08; no backtests/performance;
no holdout; no state/ledger/production changes (V5.4 harness
untouched); no Issue #9; no Yahoo work; no second attempt or in-run
repair.
