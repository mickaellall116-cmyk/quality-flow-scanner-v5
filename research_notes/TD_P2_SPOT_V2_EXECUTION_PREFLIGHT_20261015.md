# QF-TD-P2-SPOT-V2-EXECUTION-PREFLIGHT-20261015-04 r1

## Verdict

**P2_SPOT_V2_EXECUTION_PREFLIGHT_PASS**

This verdict is for the offline execution-preflight packet only. It authorizes **no vendor call**, does not adopt or merge the P2-SPOT v2 supplement or the classifier candidate, and does not change the standing facts: **P2 v1 remains UNMET, SPT08 remains NOT ATTEMPTED, TD feed qualification / corrected performance remain HOLD, and no edge claim is opened.** A live SPT08 attempt still requires separate ChatGPT adjudication and Mike's explicit bounded live-call decision.

All 22 main fake-transport cases and all 3 calendar-perturbation cases passed, each run twice with byte-identical normalized results. The candidate collector was not modified. One preflight-driver defect was repaired inside the allowance; see §6.

## 1. Frozen candidate set and drift detection

Every pin in spec §1 was recomputed from bytes before rehearsal:

| Item | Frozen identity | Result |
|---|---|---|
| Collector commit | `ab254c3458697dd450356146abcf4ad4f75ecef4` | exact worktree used |
| Collector bytes | `b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c` | match |
| NL supplement file | `9c71233003771d66cf81e99ae01a410ba8943aedfcce8a8c6411dfb51edacd32` | match |
| Environment lock | f64d12f lock, sha256 `08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068` | match |
| Calendar mechanism | `pilot_harness/validate_input.py`, sha256 `1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58` | match |
| NLQUAL result commit | `080a6ba82d8c286bdc7d07ff52a43eebcf6c6ccc` | referenced exactly |
| New-lineage qualification commit | `7de795032d17ca88bf49f3a2c1ca5185672bb088` | referenced exactly |
| Base manifest | file sha256 `ddff040fa654303cf4289f4c39c2a5b5af998bd4065ceddd4e4f5d52fcb8c28d`; canonical digest `748ca95789c6f16bab81fbc903fd0c60a890dd2f2e21a63d97ffdb962d70e4fb` | match |
| REQ-SPT-08 | canonical request digest `f547d8fec7882fa121feb966b33fde000b25c4ae0eb822a6b5a503f4a3651a97` | match |
| REQ-SPT-07 | canonical request digest `a259901ec57a8556228c2a6b95299c360102cc98edc62204ae539dc53a4c5edb` | match |
| Preserved SPT-07 vendor body | sha256 `3339c34154648c0ea4ddb9bd553e5274d390f953552518ad957d79704b7d5d50` | match |
| Rate limiter | sha256 `06ad383d856e62d126d1aae9edc7804e1b09471d87d9b280ec55a25aea0b8d64` | match |
| V2-bound adapter contract | sha256 `ec877a04d12e6b0c69378dba245be07ab60279a15c9eb78cc50e8b0c705e166b` at `b18db3ce...` | pinned in package |

Drift is not merely detected in a table: the tampered-manifest, tampered-supplement, version-drift, library-absent, mechanism-raise, and manifest-binding fixtures in §5 all fail closed.

### Environment reproduction disclosure

`/tmp/tdqual/venv` was absent when this task began. It was rebuilt exactly by the qualified package's download-hash-then-`--no-index` procedure. All 11 downloaded wheels are byte-identical to the qualification wheel hashes, the rebuilt `pip freeze` is identical to the qualified freeze, and the interpreter is CPython 3.12.3. No version was substituted. The rebuild reports and both freezes are in the evidence package.

## 2. Exact one-request SPT08 execution manifest

The evidence package contains `spt08_execution_manifest.json`. Its execution object is:

- endpoint: `https://api.twelvedata.com/time_series`
- manifest ID: `TD-P2-SPOT-V2-SPT08-EXECUTION-20261015`
- exactly one request: the byte-identical JSON value of REQ-SPT-08 from the frozen SPOT8 manifest
- canonical one-request manifest digest: `c31c756ad1f06f51676f2bb3c90fc0b2b790a7f953c949a45f500077d888c3fb`
- canonical request bytes: the compact sorted JSON serialization in `spt08_canonical_request_bytes.json`, 513 bytes, sha256 = canonical request digest `f547d8fe...`
- HTTP construction: GET, fixed parameter order `symbol, interval, start_date, end_date, timezone, outputsize, order, adjust, format, apikey`, values copied verbatim from the manifest request, `format=JSON`, `order=asc`; see `spt08_http_params.json`. Venue fields are **not** sent as request filters; they are enforced on receipt meta. The API key is not part of the manifest or request digest.

Frozen SPT08 controls:

- `max_attempts=1`
- pagination disabled/absent
- `credit_weight=1`, `expected_credits=1`
- no retry and no fallback at collector or adapter layer
- deterministic immutable output path in the selected state directory: `receipts/REQ-SPT-08.json`
- raw closed/error evidence paths are likewise write-once: `receipts/REQ-SPT-08.closed_day.bin` or `receipts/REQ-SPT-08.rejected.bin`
- restart rule: a fresh invocation may reuse only fully revalidated receipts or durably evidenced closed-session requests under the **same manifest binding**; STARTED without durable completion is AMBIGUOUS and is never redispatched.

### Binding constraint found and proven

The NL supplement binds `base_manifest_digest=748ca957...`, i.e. the eight-request SPOT8 manifest, not the new one-request manifest digest `c31c756...`. Therefore:

1. Under the exact one-request manifest, the collector validates the request and permits the single fake dispatch, but a closed-session-shaped HTTP 400 **cannot classify**; it is preserved as rejected evidence and the run HOLDs. This was proven, not inferred.
2. Under the frozen eight-request SPOT8 manifest in an isolated copied state, REQ-SPT-01..06 complete from fake valid responses, REQ-SPT-07 classifies from the preserved live body, and REQ-SPT-08 classifies from the exact closed-session shape. Restart then makes zero transport calls.
3. A one-request collector pointed at state already bound to the SPOT8 manifest is refused before dispatch with a manifest-binding error.

Consequently, a future live packet must choose one explicitly in the adoption step: execute SPT08 in the SPOT8-bound state/manifest form, or separately issue/re-pin a supplement bound to the one-request manifest digest. This preflight does not make that adoption change.

## 3. Pre-dispatch gates and evidence pins

Every gate below must pass in the future live process before transport is constructed. Missing, expired, or ambiguous evidence stops before transport; the prerequisite fixtures prove the collector behavior for missing and nonconforming prerequisite evidence.

| Gate | Required evidence / rule | Preflight status |
|---|---|---|
| G1 — entitlement, endpoint, retention | Pinned prerequisites: Basic plan; `/time_series` = 1 credit/request with recorded evidence; retention `BOUNDED_RESOLVED` with the 30-day post-termination deletion condition; interval semantics explicitly SOURCED or INSUFFICIENT. Package pin: `prerequisites_pinned.json`, sha256 `038ccaf3...`. | **Specified and fixture-proven.** Wrong-plan and missing-file fixtures raise pre-dispatch with zero fake calls. The rehearsal used a synthetic fixture with the same gate fields; it did not contact the vendor to refresh entitlement. Live adjudication must confirm the pinned evidence is still current. |
| G2 — manifest and supplement integrity | Recompute file hashes, canonical base-manifest digest, per-request digests, supplement digest/binding, and `validate_manifest == []`. Any drift fails closed. | **Proven.** §1 freeze case and tamper fixtures pass. |
| G3 — accepted acquisition adapter contract | Use only the V2-bound contract pinned at `ec877a04...`: callable `(req) -> (status, body)`, GET, fixed parameter order, one attempt, no retries, HTTPS + certificate verification, sanitized exceptions, response cap, no adapter logging. Pinned implementation from the accepted lineage: adapter sha256 `ae8f4837...`, driver sha256 `671f4d0c...` at `b18db3ce...`. | **Specified; not executed.** Fake transport implements only the callable interface for rehearsal. No HTTP adapter was imported or run in this task. The adoption step must bind the exact adapter/driver bytes to the ab254c3 collector + NL supplement set and re-verify all hashes immediately before any live authority is considered. |
| G4 — credential-vault / proxy boundary | API key or vault surrogate comes only from Secure Vault `custom.twelvedata` in the separately authorized live driver, is held in memory only, is never written to disk/argv/logs/events/exceptions, and is sent last as `apikey`. A vault-surrogate request must use the sanctioned proxy substitution path; absent/malformed/credential-bearing proxy or failed CONNECT means fail closed with no direct fallback. | **Specified; untouched.** No credential was retrieved, no proxy was probed, and no vault call was made in this preflight. |
| G5 — shared live credit limiter and remaining credit | One shared persisted `RollingCreditLimiter(8, 800)` at `research_notes/pilot_harness/credit_ledger.json`; reserve weight 1 by non-blocking `try_acquire` before dispatch; corrupt ledger HOLDs; refusal ends run as REFUSED. Read-only snapshot taken for this packet: ledger day `2026-10-14`, `spent=8`, seven reservation timestamps. That historical day total is **not** remaining-credit evidence for a future date. | **Specified and behavior-proven in isolated state.** Limiter-exhaustion fixture makes zero calls. No live ledger/state write occurred. A live run must read the then-current ledger immediately before dispatch and reserve exactly 1. |
| G6 — environment reproduction | Disposable CPython 3.12.3 environment from the exact f64d12f lock; freeze and wheel hashes equal the qualified records; real `pandas_market_calendars==4.5.1`; mechanism sha `1b83cdcd...`. | **Proven after disclosed rebuild.** Version drift, absent library, or raising mechanism disables classification and HOLDs. |
| G7 — supplement / protocol adoption | NL supplement status in the frozen bytes is `OFFLINE_CANDIDATE_NOT_ADOPTED`; P2-SPOT v2 amendment is draft only. | **OPEN by design.** This preflight does not adopt it. Separate adjudication must adopt the exact supplement/manifest form (including the §2 binding choice) before live execution can be authorized. |
| G8 — output directory and write-once rules | Select a fresh, empty, isolated state directory (the live SPOT8 state and live pilot state are not to be overwritten). No foreign files/receipts. Receipt and evidence writes use exclusive-create semantics; an existing foreign receipt or unbound evidence refuses the run before dispatch. State and lifecycle writes occur only inside that copied/selected state. | **Proven in copied state.** Collision fixture preserves foreign bytes untouched and makes zero calls. |
| G9 — explicit live-call authority | A separate, bounded decision must name SPT08, the adopted manifest/supplement form, the state directory, the adapter/driver pins, the exact 1-credit ceiling, and the dispatch window. | **NOT GRANTED.** This PASS is not live authority. |
| G10 — calendar and closed-session pins | Real XNYS mechanism and library version must match the NL supplement exactly; expected SPT08 window is the fully closed 2026-07-03 session and the supplement entry must have `expected_bars=0` plus digest `f547d8fe...`. | **Proven.** Any calendar/version/mechanism anomaly falls through to HOLD. |

## 4. One-call outcome and lifecycle disposition matrix

Raw response bytes are preserved before interpretation on every HTTP response path. No blind retry exists in any disposition.

| One-call outcome | Collector disposition | Evidence / state consequence |
|---|---|---|
| Valid HTTP 200, API `status=ok`, exact meta/venue binding, rows within bound, real validation passes | Receipt path: write raw body write-once to `receipts/<id>.json`; emit RECEIVED; run accepted validation; emit COMPLETED; mark request completed. | Durable completion binds request digest + manifest digest + receipt sha/bytes. Restart revalidates and reuses it with zero dispatch. |
| Exact closed-session HTTP 400 and every supplement/calendar/wire conjunct matches | Distinct `EXPECTED_EMPTY_CLOSED_SESSION` path: preserve raw body write-once as `.closed_day.bin`; emit CLOSED_DAY_EVIDENCED with calendar proof digest; mark only `closed_day_evidenced`; run may continue. | **Never** a receipt, **never** COMPLETED, **never** identity or construction evidence. Credit reservation stands spent. Restart recognizes the durable event and never redispatches. |
| HTTP 401/403 (auth) | Preserve raw body as `.rejected.bin`; emit ERROR_EVIDENCE; terminal HOLD. | No completion, no retry. Credential/authority must be resolved outside the run; the same run does not resume. |
| HTTP 429 (rate limit) | Preserve raw body as `.rejected.bin`; terminal HOLD. A 429 is not retried or special-cased. | Recorded divergence between reservation and vendor response; reconciliation outside the run required. |
| HTTP 5xx / other non-200 | Preserve raw body as `.rejected.bin`; terminal HOLD. | No completion or classification unless the exact closed-session conjuncts independently match (they require HTTP 400). |
| Transport timeout or other transport exception | Terminal HOLD with sanitized exception type only. | Credit billing is **unknown**: the advance reservation stands in state; restart remains HOLD and makes no redispatch. Manual/out-of-band reconciliation is required before any future authority. |
| HTTP 200 but unparseable body | Preserve raw bytes as `.rejected.bin`; terminal HOLD. | No receipt and no interpretation from malformed bytes. |
| HTTP 200 but API `status != ok` | Preserve raw bytes as `.rejected.bin`; terminal HOLD. | API error payload is evidence only. |
| HTTP 200 schema/meta/venue mismatch | Preserve raw bytes as `.rejected.bin`; terminal HOLD. | Symbol/interval/venue binding failure; no identity claim. |
| HTTP 200 values missing/empty, over output cap, or over one-response bar bound | Preserve raw bytes as `.rejected.bin`; terminal HOLD. | Possible truncation is never resolved by pagination in this scope. |
| Receipt validation failure after raw receipt write | RECEIVED remains in lifecycle, validation failure returns a terminal HOLD reason; no COMPLETED event. | Restart does not silently reuse it: durable completion is absent/mismatched, so receipt verification fails and the run HOLDs. |
| Digest/manifest/supplement mismatch before dispatch | Preflight or manifest-binding failure; CollectorError/HOLD before transport. | Zero dispatch. A changed manifest cannot reuse state bound to another digest. |
| Calendar unavailable, library version drift, or mechanism hash/version mismatch | Classification returns no proof; any closed-shaped response falls through to rejected-evidence HOLD. | Fail-closed. Calendar facts are not guessed. |
| Limiter refusal | Emit LIMITER_REFUSED; outcome REFUSED; save state. | Zero transport calls for that request. |
| Limiter ledger corrupt | Terminal HOLD. | Ledger is never reset by the collector. |
| Crash before STARTED is durable | No dispatch record exists; a later invocation starts from the bound state normally, subject to all gates. | No request is marked attempted or billed by the collector. |
| Crash after STARTED but before durable RECEIVED/COMPLETED or CLOSED_DAY_EVIDENCED | On restart, reconciliation marks it AMBIGUOUS and terminal-HOLDs. | Never auto-recalled or redispatched. Credit outcome remains unknown and requires reconciliation. |
| Crash after response raw preservation but before terminal completion | The preserved evidence/lifecycle is inspected on restart; absent a matching durable validated completion, receipt verification or AMBIGUOUS reconciliation HOLDs. | No silent completion and no redispatch. |
| Closed-session evidence offered for a later claim | Rejected as a basis for receipt/completion/identity/construction claims by construction: distinct event class, distinct filename, no RECEIVED/COMPLETED events, and 1H semantics remain INSUFFICIENT / CONSTRUCTION_HOLD. | Classification only proves the preregistered closed-session disposition. |

## 5. Deterministic fake-transport rehearsal

The driver is `run_preflight.py` in the evidence package. Its normalized result files contain every check. All cases were run twice; corresponding run 1/run 2 files are byte-identical.

### Main mode — 22/22 PASS twice

1. `freeze_candidate_set`
2. `spt08_one_request_manifest`
3. `spt08_single_manifest_supplement_unbound_fails_closed`
4. `full_spot8_end_to_end`
5. `restart_idempotent_zero_redispatch`
6. `single_manifest_against_bound_state_refused`
7. `prereq_wrong_plan`
8. `prereq_missing`
9. `limiter_exhaustion`
10. `resp_valid_200`
11. `resp_auth_401`
12. `resp_rate_429`
13. `resp_server_500`
14. `resp_transport_timeout`
15. `resp_unparseable_200`
16. `resp_meta_mismatch_200`
17. `resp_api_status_error_200`
18. `unknown_billed_credit_no_redispatch`
19. `crash_after_started_ambiguous`
20. `write_once_collision_foreign_receipt`
21. `tampered_supplement_expected_bars`
22. `tampered_manifest_request_drift`

### Calendar perturbation modes — 1/1 PASS twice each

- `N10_vmismatch`: real library version attribute drifted to `9.9.9` in a throwaway process → HOLD, no classification.
- `N10_libabsent`: library import blocked in a throwaway process → HOLD, no classification.
- `N10_mechraise`: real mechanism made to raise in a throwaway process → HOLD, no classification.

### Transport-call accounting

- Real/vendor transport calls: **0**.
- Twelve Data calls: **0**. No authenticated vendor/API/model call was made by the rehearsal.
- Injected fake-transport dispatches in each main run: **34**, every one asserted against an exact per-case call list. Each perturbation-mode run made exactly **1** fake dispatch to the closed-day fixture and then HOLDed.
- The collector's built-in transport was never used. The driver additionally disabled socket connect/DNS operations in-process before loading the collector.
- The shared live limiter ledger and live V5.4 harness/state were not written. Limiter rehearsal used isolated temporary ledgers only; the live ledger was read only for the §3 snapshot.

## 6. Trials, failures, and repair

- **Environment trial:** the qualified venv was absent at start. Rebuild succeeded from the exact lock; all 11 wheel hashes and the final freeze match the qualification records.
- **Initial main-driver trial:** the first main execution stopped in the preflight driver at the write-once collision case because the driver had not caught the collector's `CollectorError`. The collector's actual behavior was the stronger fail-closed path: it refused unbound foreign evidence before dispatch, with zero fake calls and foreign bytes untouched. This was a driver defect, not a candidate failure.
- **Repair:** one driver-only edit caught that refusal path and recorded which refusal mechanism fired. No candidate, supplement, manifest, environment, or accepted-code bytes were changed. **Repair time: approximately 3 minutes**, within the single ≤10-minute allowance.
- **Final trials:** after the repair, main mode passed 22/22 twice byte-identically; all three perturbation modes passed twice byte-identically.
- **Candidate failures in final trials:** none.

## 7. Package and scope confirmation

Evidence package: `research_notes/td_p2_spot_v2_execution_preflight_evidence_20261015/`

It contains the verbatim spec, frozen manifest and supplement, the one-request execution manifest, canonical request bytes and HTTP parameter specification, the adapter contract and pinned prerequisites, the environment lock/rebuild records, the driver, all run outputs, the transport accounting, and `SHA256_MANIFEST.txt`.

Scope confirmation:

- fake transport only
- zero live TD execution
- zero vendor/model/authenticated API calls in the rehearsal
- zero credits or spend
- zero live limiter/state writes
- zero backtests or holdout access
- no adoption or merge
- no production or live V5.4 changes
- candidate and accepted code unmodified

**Final verdict: P2_SPOT_V2_EXECUTION_PREFLIGHT_PASS — packet only; no live call authorized.**
