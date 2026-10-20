# PREP MEMO — QF-TD-ROUTE-ADOPTION-TRANSACTION-PREP-20261020-48 r1

**Terminal: `TD_ROUTE_ADOPTION_TRANSACTION_PREP_READY__AWAITING_OFFLINE_TRANSACTION_PROOF`**

Spec: Issue #1 adjudication comment 6286188915 (verdict
TD_POST_ACQUISITION_ROUTE_PROOF_ACCEPTED__RESEARCH_ADOPTION_TRANSACTION_HOLD).
Scope honored: research-only, one offline candidate-package build + one static
pin-closure linter run. No adoption, no overwrite, no merge, no runtime/vendor
execution, no repair loop. Elapsed and timing at the end.

## 1. Frozen pins — all re-verified byte-exact this pass
FRESH manifest 71aade8b…; existing FRESH supplement 3cbdbf63…; live driver
5fed4524…; gate r4 b5399645…; executor r4 e792b8b2…; adapter e8605669…;
TD lock 08b38cfa…; wheelhouse manifest 210b8273…; validator candidate
ca3bafd8…; entrypoint candidate 442e56cc…; constructor d47e8df1… (full hashes
in dag.json / SHA256_MANIFEST.txt; linter check C8 re-verifies the originals).

## 2. Candidate set (all new files in this package; status OFFLINE_CANDIDATE_NOT_ADOPTED)
| candidate | sha256 | change vs original |
|---|---|---|
| fresh_supplement_v2_candidate.json | 55ad6f40509ac77f… | calendar.mechanism/mechanism_module/mechanism_module_sha256 → validator candidate (ca3bafd8…, -44 path); calendar_proofs record re-keyed (mechanism field updated, basis appended, content digest recomputed 36bc3a89… → 6b030c62…); entries re-pointed; derived_from_supplement → current FRESH supplement. Base binding, request digests, classifier pins, safety binding, supplement_id, status carried by value. File is canonical bytes (canon == bytes, as the driver requires). |
| live_driver_r5_candidate.py | d11c6b587c028c26… | EXPECTED_SUPPLEMENT_SHA256 → 55ad6f40…; NL_MECHANISM_MODULE_SHA256 → ca3bafd8…; candidate banner. Nothing else. |
| dispatch_gate_r5_candidate.py | 94ef967ca832faea… | P_DRIVER/P_SUPPLEMENT/P_MECHANISM → candidate paths; PIN_DRIVER → d11c6b58…; PIN_SUPPLEMENT → 55ad6f40…; PIN_MECHANISM → ca3bafd8…; PIN_CALENDAR_PROOF → 6b030c62…; REVISION → r5-route48-candidate; banner. |
| live_dry_run_adapter_r5_candidate.py | 6980b5b3c887ea7e… | GATE_PATH → candidate gate; PIN_R4_GATE → 94ef967c…; banner. (Supplement value follows automatically: the adapter reads G.PIN_SUPPLEMENT from the loaded gate, :162.) |
| live_readiness_executor_r5_candidate.py | bbc23616b0b8c62f… | PIN_R4_GATE → 94ef967c…; PIN_SUPPLEMENT prefix → 55ad6f40; ADAPTER_PATH → candidate adapter; ADAPTER_SHA256 → 6980b5b3…; banner. |
| ROUTE_MANIFEST_CANDIDATE.json | (see SHA256_MANIFEST) | Pins route 442e56cc → ca3bafd8 → d47e8df1; records precedence sentence, split-exclusion placement, direct-CLI refusal + both open-requirement statuses; chain candidate hashes; unchanged pins; evidence commits. |

Exact diffs: diffs/*.diff (supplement diff rendered over pretty-printed
canonical content; byte identity is over the canonical form). No
business/classification/construction logic change anywhere — every changed
line is a pin, a path, a revision string, a provenance record, or the
candidate banner. No consumer required a semantic code change, so the
spec §3 stop condition was not triggered: the one place that could have
forced it — the supplement's calendar_proofs digest — is a pure content
digest (driver/gate verify key == H(canon(record)), reproduced from the
drivers' own canon/H definitions read as text), so the re-key is data
propagation, verified statically (linter C2.proof_self_digest).

**Why no collector candidate:** the collector (b683d277 @ab254c3) reads the
supplement's calendar version + mechanism sha FROM the supplement at runtime
(:527/:531), so the candidate supplement rebinds it dynamically; its own
bytes carry no mechanism pin to propagate.

## 3. Static linter (spec §4) — 43/43 PASS (CONSISTENCY_CHECK.md)
- All referenced paths/hashes resolve (C1–C5), incl. gate P_ paths vs PINs
  and the supplement's mechanism_module path vs ca3bafd8….
- No authoritative candidate-chain pin remains on original validator
  1b83cdcd…, existing supplement 3cbdbf63…, or old proof 36bc3a89… (C6).
  Stale-pin sweep, full-hash literals remaining in candidate files: exactly
  ONE — the candidate supplement's derived_from_supplement.sha256
  provenance pointer to 3cbdbf63… (intentional, classified). Prefix-form
  historical mentions remain only in the originals' docstrings carried into
  the candidates (driver :8/:48, gate :4, executor header) — non-authoritative
  prose describing the ORIGINAL integrations, superseded by each candidate's
  banner; enumerated here so the sweep is complete.
- No orphan candidates (C7); rollback complete (C7); originals unchanged (C8).
- Cycles: the pin graph's single SCC {supplement, collector} is the accepted
  chain's intentional mutual binding, anchored by the unchanged collector;
  the graph over transaction-changed nodes is acyclic (C7; PIN_DAG.md
  "Graph cycles"). Disclosure: the linter's first draft required full
  acyclicity and flagged this SCC; the rule was corrected to the SCC form
  BEFORE commit and the correction is recorded in CONSISTENCY_CHECK.md.
  No candidate byte changed after the single build.

## 4. Pin DAG / rollback
PIN_DAG.md (+ dag.json): 14 nodes, 27 field-level edges with enforcement
citations; atomic set A (supplement→driver→gate→adapter→executor) with six
named inconsistent intermediate states — every one fails CLOSED at a hash
check before any dispatch; the route leg is independent but both legs must
complete before live use; the by-name validate_input residual is recorded.
ROLLBACK_MAP.md (+ rollback.json): adoption designates the candidate
executor as chain head and overwrites nothing, so rollback = withdraw the
designation; per-node restore set + post-rollback verification included.

## 5. Open requirements carried for the transaction (NOT closed here)
- REQ-CLI: the unchanged constructor still ships a standalone CLI
  (recorded as shipped in the -42 preflight). No candidate in this package
  satisfies the adjudicated fail-closed requirement; the transaction must
  bind a CLI-refusing constructor variant (new candidate + proof) or carry
  adjudicated deployment terms exposing only the entrypoint path.
- REQ-S2: split exclusion (D-1..D+1, bars AND candidate entries, recompute,
  no imputation) belongs to a future 4H assembly component + its own proof;
  recorded in the route manifest and DAG; not implemented here.

## 6. Next step (returned, not executed)
NEXT_TRANSACTION_PROOF_SPEC.md — P0 static re-verification, P1 gate/adapter/
executor offline regression vs candidates, P2 driver classification
regression, P3 route-leg binding confirmation, P4 the two open requirements.

## 7. Prohibitions — confirmations
No vendor/model/API calls (the only network use was the read-only public
GitHub API fetch of the spec comments); no credits/spend; no real market
data; no SPT-08; no holdout access; no performance/backtest work; no
production/live/state/ledger changes; no trading restart; NO route
adoption or re-pin in any live position; no live/existing file modified
(linter C8 re-verified all originals byte-identical at the end of the run,
and this package was built and committed from a temp worktree off
origin/main — the main tree's pre-existing UU forward_test/kama_shadow.json
merge state was never touched); no Yahoo scan; no Issue #9 execution;
no gate/executor/collector/acquisition/construction code executed (the
linter and builders are static text/hash tooling that import no chain
module).

## 8. Timing
Build start 2026-10-20T08:04:13Z (after spec read + chain inspection from
~07:57Z). Single candidate build, single linter pass after the documented
C7 rule correction (package tooling only; repair minutes on candidates: 0).
Remote-verified commit recorded in the bridge/work-result post.
