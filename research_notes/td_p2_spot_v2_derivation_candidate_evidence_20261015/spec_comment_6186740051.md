## REVIEW / HOLD — TD full-manifest copied-state preflight `7723f07`

Independent review of the immutable memo, state inventory, direct classifier proof, trial log, driver and manifests at `7723f07ca9b98dd824752e83e753c77fafc17c16` supports the reported result.

### Verdict: `P2_SPOT_V2_FULL_MANIFEST_PREFLIGHT_HOLD` accepted

The evidence isolates two real, load-bearing design gaps:

1. **No provenance-safe v1→v2 derivation entry point.** The actual copied SPOT8 state is terminal HOLD at SPT07. `_run_locked()` short-circuits before reuse/dispatch and the classifier is callable only from a fresh response handler. Direct classification of the preserved 180-byte body succeeds under the accepted calendar pins, but there is no legitimate path to append that derived evidence and resume. Hand-writing state/events would be fabrication and was correctly refused.
2. **Receipt verification is not read-only.** `_verify_receipt → _validate_bars` appends a `CONSTRUCTION_HOLD` event for each verified 1h receipt. Six such appends occurred in the isolated probe. A verifier must not mutate lifecycle history merely by checking reusable evidence.

The original SPOT8 state remained byte-identical and no live/vendor/model calls, credits, state writes, merge or adoption occurred. SPT08 remains NOT ATTEMPTED; P2 v1 remains UNMET.

This is new load-bearing evidence, so one bounded isolated repair candidate is eligible. Do not continue iterative repair beyond the task below.

### FINAL ELIGIBLE OFFLINE REPAIR — QF-TD-P2-SPOT-V2-DERIVATION-CANDIDATE-20261015-06 r1

Muse: build an **isolated candidate only** from `ab254c3`; no merge/adoption/live state change. Budget <=50 minutes including one <=10-minute repair. Socket/network denied and fake transport only; zero vendor/API/model calls, credits/spend, installs, backtests, holdout access or production changes. If the design cannot meet all invariants inside the bound, return HOLD and PARK for revised architecture.

1. Add an explicit, opt-in derivation entry point separate from normal `run()`. It may operate only on an isolated copy whose manifest binding is exactly `748ca957…`, supplement is exactly `9c712330…`, environment/mechanism pins match NL-20261015, and terminal HOLD is exactly the preserved SPT07 HTTP-400 state.
2. Derivation prerequisites must all match: REQ-SPT-07 digest `a259901e…`; preserved rejected body 180 bytes / `3339c341…`; matching prior STARTED, ERROR_EVIDENCE and HOLD records; seven attempts/reservations; SPT01–06 durable completions; no SPT07 receipt/completion/closed-day event; no SPT08 attempt/artifact; no foreign/unbound files. Any mismatch refuses with zero writes/transport.
3. On success, append a distinct versioned **DERIVED_CLOSED_DAY_EVIDENCED** transition with source event/body hashes, classifier/supplement/environment/manifest/request pins and calendar proof digest. Retain all v1 events and the v1 HOLD record unchanged in history. Never create a receipt, RECEIVED/COMPLETED/identity/construction claim for SPT07.
4. Update derived state through a crash-reconcilable atomic protocol. The candidate must survive injected interruption before append, after derivation event but before state publication, and after state publication. Restart must yield exactly one derivation, never duplicate, never unlock on partial/unbound evidence, and never dispatch SPT07.
5. Credit accounting: derivation consumes no new credit; reservations remain 7. Only a later SPT08 fake dispatch may reserve credit 8. Never decrement or rewrite historical reservations.
6. Refactor receipt reuse verification to be **observationally read-only**: validation returns structured findings without lifecycle append. Construction eligibility/HOLD emission must be an explicit separate action. Rechecking SPT01–06 must leave every state/lifecycle/receipt byte unchanged.
7. Against the copied actual state, prove exact transition then full-manifest fake execution with call list exactly `[REQ-SPT-08]`. Exercise SPT08 closed-session, valid-200, auth/rate/server/timeout/schema/meta/calendar/digest drift, crash and write-once outcomes; restart durable outcomes with zero redispatch.
8. Adversarial derivation fixtures: wrong HOLD reason/status; missing/altered prior event; altered body/request/manifest/supplement/env/calendar; missing or invalid receipt; already-derived duplicate; SPT08 already attempted; credit count drift; concurrent second process. Every negative must make zero writes and zero calls.
9. Run the complete new suite and all applicable -05/-04/NLQUAL/base/`f64d12f` regressions twice. Require deterministic machine outputs; publish every trial/failure, exact repair minutes, candidate diff/hash, crash-state mapping, call/credit ledger and SHA256 manifest. Verdict `DERIVATION_CANDIDATE_PASS | HOLD`.

Even PASS is an isolated candidate result only. It authorizes no adoption, merge or live SPT08 call. If HOLD, PARK this route for revised design; do not disguise another repair revision as the same task.

Tracking:
- -05 ACK + WORK RESULT received and independently reviewed; HOLD accepted.
- -06 SENT by this comment; ACK and WORK RESULT remain separate.
- Yahoo pause restoration remains blocked on Mike's explicit production GO.
- Issue #9 live execution remains unauthorized; no duplicate task is created.
