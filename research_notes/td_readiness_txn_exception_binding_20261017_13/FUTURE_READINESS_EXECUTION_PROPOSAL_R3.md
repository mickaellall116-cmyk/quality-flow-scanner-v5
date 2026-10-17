# FUTURE READINESS EXECUTION PROPOSAL — r3 (revised for exception capture and recovery binding)

## STATUS: NOT AUTHORIZED

This proposal is a source-pinned packet for a FUTURE, separately accepted
step. It authorizes nothing. It excludes the 51 market-data requests and
token issuance, exactly as the r1 proposal did. Mike's GO remains a
52-credit ceiling decision only (1 status credit + the unchanged
51-request manifest), not an execution GO.

## What changed vs the r2 proposal (the -12 PARTIAL PASS grounds)

The -12 review accepted explicit crash recovery but held live readiness
on three source-level gaps. The r3 candidate
(`readiness_transaction_r3.py`, sha256
db93f07ee057b731528a231e836e67c791a01ab779c6893fe1bda6c258a5c79a)
closes all three; everything below it in this proposal is unchanged:

1. **Real exceptions, not only Refusal** — run() now catches every
   Exception while locks remain held. Real OSError/RuntimeError
   failures at evidence write/fsync, card write/fsync, receipt
   write/fsync, the dry-run hook, terminal-record write/fsync and the
   terminal journal advance each restore the exact legacy bytes and a
   durable TERMINAL_ROLLED_BACK journal state before locks release
   (trials x01-x07). If the rollback itself cannot be verified, the
   journal records TERMINAL_HOLD_MANUAL and the outcome is HOLD_MANUAL
   / manual-recovery-required: ROLLED_BACK is never claimed falsely
   (trial x08).
2. **Terminal COMPLETE is fully validated** — recovery parses and
   verifies the terminal record (exact txn id, outcome COMPLETE,
   status-call count equal to the journal), the dry-run receipt
   (txn-bound, gates exactly 12 x PASS, 12/12 counts), and the
   evidence/token-card cross-digests (card evidence_sha == sha256 of
   the evidence bytes; candidate_sha bound to the journal), plus the
   candidate target hash and journal phase/history consistency.
   Existence alone is never sufficient; any terminal-artifact tamper
   is HOLD_MANUAL with no ledger touch (trials b01-b07).
3. **Recovery paths are exactly bound** — the journal binds canonical
   absolute target and backup paths, the target realpath and the
   workdir. Recovery validates the caller path, marker txn id,
   journal txn id, path bindings, hash formats and phase/history
   BEFORE acquiring locks or touching the ledger. Symlink
   substitution, a relocated or path-edited journal, a wrong
   workdir/target, a marker/journal mismatch, nonmonotonic history
   and an ambiguous second journal for the same target all fail
   closed as HOLD_MANUAL (trials b08-b15).

Offline proof: recovery matrix 45/45 trials, 193/193 checks, twice
under kernel network denial, byte-identical (sha256
56084b752a74a8f394f2beae2eae9357d8a35b636a414279fc455587c5c5e748);
the unchanged r4 gate regression remains 46/46 trials, 332/332
checks, byte-identical to the pinned matrix (sha256
aafd4e1b13b444600eb4d13481525aac54e840416b25d73ad84db514c16e2de3).

## What changed vs the r1 proposal (the -11 HOLD ground)

The r1 transaction could strand an adopted candidate after a post-replace
failure or crash, with no cold-start recovery path short of a second
status call. The r2 candidate (`readiness_transaction_r2.py`, pin in the
-12 memo) closes that gap:

1. **Write-ahead journal before replace** — fsynced at every phase,
   binding txn id, target path, original hash, candidate hash, and the
   backup path + backup hash (journaled at BACKED_UP, before REPLACED).
2. **Locks held to terminal commit** — owner lease then ledger lock are
   held through refreeze, the 12/12 dry-run, and the durable terminal
   journal write. Any ordinary failure after replace (evidence/card
   write or fsync, dry-run exception or non-12/12, terminal-record
   write/fsync, post-write verification) atomically restores the exact
   legacy bytes, fsyncs, verifies the original hash, and records a
   terminal HOLD/ROLLED_BACK journal state before locks release.
3. **Cold-start recovery, zero status calls** — recovery takes no
   status/helper callable at all. Under the same locks it classifies
   from journal + filesystem bytes alone: NOT_STARTED / PRE_REPLACE
   (finalize, ledger untouched) / POST_REPLACE_UNVERIFIED (backup
   verified, legacy restored exactly) / ADOPTED_VERIFIED /
   ROLLED_BACK / HOLD_MANUAL (corrupt journal, unknown target bytes,
   or backup mismatch — ledger never touched). A consumed transaction
   can never place a second status call.

## The future step this proposal asks adjudication to clear (unchanged
in scope from r1)

- Exactly ONE authenticated `GET /api_usage` status request through the
  -08-verified resolver/helper, inside the r2 transaction, under the
  Policy A gate-3 contract (remaining >= 52 at check time, status credit
  conservatively not self-counted, 3600 s freshness).
- Conditional adoption of the -07 conservative ledger candidate ONLY on
  gate-3 PASS, via the journaled backup/replace/verify sequence above.
- Refreeze + derived token card + r4-gate dry-run to 12/12.
- Abort conditions: any pin drift, GO-record drift, helper surface
  failure, gate-3 shortfall, journal/backup anomaly, or post-replace
  fault → rollback to exact legacy bytes and a terminal HOLD record.
- Crash at any point → cold-start recovery per §3 before any new
  transaction may be proposed; recovery never spends a credit.

## Explicitly excluded (unchanged)

The 51 market-data `time_series` requests, dispatch-token issuance/use,
armed transport, corrected performance, production/trading, holdouts,
Issue #9 execution.
