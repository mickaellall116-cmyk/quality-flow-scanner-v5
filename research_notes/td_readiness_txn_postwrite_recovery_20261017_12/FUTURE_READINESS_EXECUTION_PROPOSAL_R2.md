# FUTURE READINESS EXECUTION PROPOSAL — r2 (revised for post-write recovery)

## STATUS: NOT AUTHORIZED

This proposal is a source-pinned packet for a FUTURE, separately accepted
step. It authorizes nothing. It excludes the 51 market-data requests and
token issuance, exactly as the r1 proposal did. Mike's GO remains a
52-credit ceiling decision only (1 status credit + the unchanged
51-request manifest), not an execution GO.

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
