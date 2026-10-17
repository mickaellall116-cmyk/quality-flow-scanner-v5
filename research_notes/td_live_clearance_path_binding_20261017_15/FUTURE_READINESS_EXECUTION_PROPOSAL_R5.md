# FUTURE READINESS EXECUTION PROPOSAL R5 — QF-TD-LIVE-CLEARANCE-PATH-BINDING-20261017-15

## STATUS: NOT AUTHORIZED

This proposal describes a future, separately cleared, one-use readiness
execution. It is **not authorized**. The first real `/api_usage` call
remains HOLD until these exact bytes are independently reviewed and a
distinct one-use readiness clearance is recorded. Nothing in this
document, in Mike's Policy A ceiling GO (Issue #1 comment 6234434220),
or in any prior package authorizes executing it.

**Explicitly excluded — not part of this proposal, not authorized by
it, and structurally impossible in the executor:** all 51 market-data
requests of the fresh full-manifest screen; token issuance or use for
the data screen; any armed `time_series` transport; the data screen
itself; any second status call; any retry.

## What the execution would do (and nothing else)

One run of the pinned executor below, in live mode, performing the
readiness transaction only:

1. Verify the one-use readiness clearance artifact (below) — before
   any marker, workdir, lock, vendor or ledger touch. (Immutable
   source/policy verification reads — the candidate bytes, the Policy
   A file — are permitted ahead of this check; nothing is created,
   locked or mutated before clearance passes.) The clearance is
   schema v2: in addition to the artifact hashes it binds the exact
   canonical live target path + realpath, the exact workdir, the
   candidate path, the dry-run root, and a digest of every live
   packet identity field, so a byte-identical ledger copy at any
   other path cannot satisfy it. Admission also rejects symlink or
   non-regular target / candidate, symlinked workdir ancestors, and
   symlink lease/lock paths.
2. Create the one-use transaction marker with exclusive-create
   semantics (a pre-existing marker refuses the run).
3. Acquire the owner lease, then the shared-ledger lock — **before
   reading or pinning any live ledger bytes**.
4. Under lock, read the live ledger; require the exact adjudicated
   legacy hash and legacy schema. Bind **those locked bytes** into
   the journal, the backup and any rollback. Mismatch → HOLD, ledger
   untouched, stale bytes never restored.
5. Resolve the sanctioned credential helper through the pinned -08
   resolver (path + sha256 pin, re-verified before use; never invoked
   at this step).
6. Revalidate the target pathname/inode/realpath identity captured
   under lock in the journal, immediately before the status boundary.
   Consume the single status slot — journaled **before** invocation —
   and place exactly one `GET /api_usage` (Twelve Data allowed host
   only, built through the verified helper handle; no retry, no
   redirect, no alternate endpoint). After the helper returns the
   credentialized URL, the executor independently parses it and
   requires HTTPS, exact host `api.twelvedata.com`, exact path
   `/api_usage`, no fragment, no userinfo, no alternate port, and
   only the expected credential query shape (no query, or exactly one
   `access_token` parameter) before transport is invoked.
7. Evaluate Policy A gate 3 from the response under the frozen
   contract (remaining ≥ 52 with the status credit conservatively not
   self-counted; 3600 s freshness; vendor-vs-ledger consistency
   fail-closed). Any non-PASS → HOLD before adoption; the ledger is
   never touched.
8. Back up the locked legacy bytes (fsynced, hash journaled),
   revalidate target/journal/path bindings **and the target
   pathname/inode/realpath identity** under lock, then adopt the
   pinned gate-schema ledger candidate atomically; post-write hash
   verification; exact rollback on any failure.
9. Refreeze the status evidence and the derived token card from the
   post-adoption bytes; run the exact r4 gate dry-run (12/12 required)
   inside the r3 transaction semantics as integrated by this
   executor; write the durable terminal record; release the locks
   only after the terminal journal state is durable.

Both locks are held continuously from step 3 through step 9. Any
crash or exception at any point leaves the write-ahead journal able
to classify the state cold — NOT_STARTED / PRE_REPLACE /
POST_REPLACE_UNVERIFIED / ADOPTED_VERIFIED / ROLLED_BACK /
HOLD_MANUAL — and recovery completes or rolls back **without any
second status call** (the recovery entry point accepts no
status/helper callable), revalidating all bindings again under lock
before touching the ledger.

## Exact pins

| Artifact | Pin |
|---|---|
| Executor candidate (-15) | `live_readiness_executor_r2.py` sha256 `e93e88a53410f1c5e8ef5ff399da0c1fe73964a9a9ea864eb0761b76f1e2e22b` (package td_live_clearance_path_binding_20261017_15) |
| r4 dry-run adapter (-14) | `r4_dry_run_adapter.py` sha256 `7a56d86ab6d3318bb67988b270101b21f5236f949e63df91dbd598d66c876e3f` |
| Transaction semantics base (-13, unchanged) | `readiness_transaction_r3.py` sha256 `db93f07ee057b731528a231e836e67c791a01ab779c6893fe1bda6c258a5c79a` (commit a95639d) |
| r4 gate (-11, unchanged) | `dispatch_gate_r4.py` sha256 `b53996454650dafc77e647a8497eba91beb3785fb52c13d70fa81768fd370117` (commit dbecf03) |
| Credential resolver (-08, unchanged) | `credential_resolver.py` sha256 `c8271193c97713f72b59af2377989362750142eda36940fa0be71cf6de8a911c` (commit 9474400) |
| Sanctioned helper | `/opt/hatch/skills/skill-creator/bin/dynamic_credentials.py` sha256 `8b1f42e80a76710edf0ff2abf8a51b0cde35b06474af865de108a7ca27d6728d` |
| Policy A (canonical digest) | `5d9d82ca3e1c867e3f38dcb7f50cd7f372c793048d21232608f7835467d26cde` (file sha256 `728c3defc13d88c27e37d176c560aa708fc93a99730893c9d097c2ca5e9a57e5`) |
| Gate-3 contract (-10) | `gate3_policy_candidate.py` sha256 `7e44a2e0d0a3b32dfd6fb7f93f04a224f935310a6e71dfe06ea83008595eb3f9` |
| Legacy ledger (live, must match under lock) | `research_notes/pilot_harness/credit_ledger.json` sha256 `7e5ccef0e5fd7e2faa744c8fe7ee646c3162fa4f72fc4a9a85317d52b5d890ed` |
| Ledger candidate (-07, adoption target) | sha256 `79ff48444d9f05c1272bfbeec2376b8065f4c22dc97b86f657e2ad15495e846b` (commit 2f312a1) |
| Manifest (context only; NOT executed) | digest `71aade8bfbb1f94b25d780bdf68f08f7f127740fc745c1755432acc5f74044db`; supplement `3cbdbf63…` |
| Authority record | Mike Policy A GO, Issue #1 comment 6234434220, record `QF-TD-POLICY-A-52-CREDIT-CEILING-GO-20261017` (ceiling in principle: 52 credits total on the screen day; this readiness step spends at most 1) |

## The one-use readiness clearance (the arming artifact)

Before any live run, a distinct clearance must be recorded as a JSON
artifact binding: the transaction id; this executor's source sha256;
the r4 gate sha256; the Policy A digest; the ledger candidate sha256;
the legacy ledger sha256; `ceiling_credits: 52`; and
`scope: "READINESS_ONLY_ONE_API_USAGE"`. The live packet pins the
clearance file's sha256. The executor verifies the pin and every
binding before creating the marker; an absent, malformed, or
mismatched clearance refuses the run with zero side effects. The
clearance is consumed by the transaction's one-use marker: it can
never authorize a second run, a second status call, or any
market-data request.

## Abort conditions (any one → HOLD, no adoption)

Clearance missing/mismatched (including any path or packet-digest
binding) · symlink/non-regular target, candidate, workdir ancestor,
lease or lock path at admission · target pathname/inode/realpath
drift before the status boundary or before mutation · helper-returned
URL failing the executor-side boundary (scheme/host/path/fragment/
userinfo/port/query shape) · marker already present · lock
contention · locked ledger hash or schema differs from the
adjudicated pin · helper path/hash/origin/signature mismatch ·
status transport error, redirect, or non-JSON body · gate-3 non-PASS
(including remaining < 52, stale evidence, plan-limit mismatch,
vendor-vs-ledger inconsistency) · binding revalidation failure
before mutation · post-write hash mismatch (→ rollback) · dry-run
not 12/12 (→ rollback) · rollback unverifiable (→ HOLD_MANUAL,
manual recovery, never a false ROLLED_BACK claim).

## Required return evidence for the future run

Terminal record + journal (full phase history) · the status evidence
file and derived token card · the 12/12 dry-run receipt · pre/post
ledger hashes · the count of authenticated requests placed (must be
exactly 1) and credits consumed (must be ≤ 1 for this step) · the
clearance artifact and its pin · a scope attestation (no token, no
`time_series`, no market-data request).

— Muse (proposal only; NOT AUTHORIZED)
