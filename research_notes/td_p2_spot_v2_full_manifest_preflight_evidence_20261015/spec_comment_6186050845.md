## REVIEW / DECISION — TD P2-SPOT v2 execution preflight `0e3a260`

I reviewed the immutable preflight memo, source pins, environment rebuild records, exact request/HTTP construction, trial log, normalized result sets and driver at `0e3a260ae16e0f0664ec088055270409c4e22319`.

### Verdict: scoped preflight PASS accepted; live readiness remains HOLD

Accepted:
- All frozen collector/supplement/environment/mechanism/manifest/request/limiter/adapter-contract pins recompute from bytes.
- The exact 11-wheel NL environment was rebuilt without substitution.
- Main matrix 22/22 and three calendar perturbation modes pass twice with byte-identical normalized outputs.
- Socket/DNS denial and injected fake transports support zero real/vendor/model calls, zero credits/spend, zero live limiter/state writes.
- Failure, crash, unknown-credit, write-once, tamper, restart and lifecycle dispositions are fail-closed.
- The disclosed ~3-minute driver-only correction is within budget and did not alter candidate/supplement/manifest/environment bytes.

The discovered binding constraint is load-bearing and correctly prevents live authorization:
- Supplement `9c712330…` binds canonical manifest `748ca957…`, the frozen eight-request SPOT8 manifest.
- The proposed one-request manifest digest is `c31c756a…`.
- Under that one-request manifest, the single dispatch may occur, but the expected closed-session HTTP 400 cannot classify and the run HOLDs.
- Therefore `P2_SPOT_V2_EXECUTION_PREFLIGHT_PASS` is accepted only as a safety/design result. It is **not** an executable live packet.

Do not re-pin the supplement merely to make the standalone form pass. The least-assumptive eligible route is the already-bound full SPOT8 manifest, but only if immutable prior evidence/state can be transitioned without re-calling SPT01–07 or rewriting P2 v1.

### NEXT — QF-TD-P2-SPOT-V2-FULL-MANIFEST-STATE-PREFLIGHT-20261015-05 r1

Muse: perform a final **offline copied-state transition preflight**. Budget <=40 minutes including one <=10-minute repair. Fake transport and socket/network denial only; zero vendor/API/model calls, credits/spend, live state/limiter writes, installs, merges, protocol adoption, backtests or production changes.

1. Use exactly the frozen eight-request SPOT8 manifest (file `ddff040f…`, canonical `748ca957…`) and NL supplement `9c712330…`; no manifest or request rewrite. Recompute all -04 pins.
2. Start from a clean immutable copy of the actual SPOT8 acquisition evidence/state. Inventory and hash every SPT01–07 receipt, rejected body, lifecycle/state record and credit reservation. The original directory and P2 v1 record are read-only.
3. Prove—or return HOLD—that a separately versioned v2 state can be derived deterministically:
   - SPT01–06 reuse only their already-validated, manifest-bound durable receipts, with zero transport.
   - SPT07 is derived from its preserved 180-byte rejected evidence under accepted NL classifier rules, with zero transport, while retaining the original v1 HOLD record unchanged and emitting explicit provenance linking source hash, classifier/supplement/environment pins and derivation.
   - No hand-edited/fabricated completion, receipt, identity or construction claim. If the unchanged candidate cannot support this transition honestly, stop and document the design gap rather than patching state around it.
4. In that copied v2 state, run the full manifest with a fake transport wired to allow **only REQ-SPT-08**. Assert exact call list `[REQ-SPT-08]`, one reservation, no retry/fallback/pagination. A call to SPT01–07 is an automatic FAIL.
5. Exercise SPT08 outcomes: exact closed-session 400 → distinct evidenced class only; valid 200 → receipt validation path; auth/rate/server/timeout/schema/meta/calendar/digest drift → terminal HOLD. Preserve raw bytes and unknown-credit semantics.
6. Restart each durable outcome and require zero redispatch. Include crash after STARTED and foreign/write-once collision controls.
7. Run complete normalized suite twice byte-identically. Publish all trials/failures, repair minutes, source/evidence pins, original-vs-derived state mapping, fake-call ledger, SHA256 manifest and verdict `P2_SPOT_V2_FULL_MANIFEST_PREFLIGHT_PASS | HOLD`.

A PASS still authorizes no vendor call, adoption or merge. It only resolves the manifest/state execution shape for a subsequent explicit decision. P2 v1 remains UNMET, SPT08 NOT ATTEMPTED, TD feed qualification and corrected performance remain HOLD.

Tracking:
- -04 ACK + WORK RESULT received and independently reviewed.
- -04 scoped offline preflight PASS accepted; live readiness HOLD on manifest/state binding.
- -05 SENT by this comment; ACK and WORK RESULT remain separate.
- Yahoo feed-health acceptance / pause-safety HOLD unchanged; pause restoration remains Mike-only.
- Issue #9 live execution remains unauthorized.