# PIN DAG — TD route adoption transaction (task -48 r1)

Field-level pin graph of the post-adoption chain. `A -> B` means: file A carries a
pin (hash/path/digest field) whose target is B; the pin is enforced at the cited
location. Current values are the accepted chain (-41 matrix, commit 91604d0);
candidate values are this package's transaction candidates. Machine-readable
form: dag.json.

## Nodes

| node | artifact | current sha256 | candidate sha256 | disposition |
|---|---|---|---|---|
| manifest | FRESH manifest (51 requests) | `71aade8bfbb1f94b…` | — | UNCHANGED |
| supplement | FRESH supplement TD-FRESH-FM-SUPPLEMENT-NL-20261016 | `3cbdbf63fd49b021…` | `55ad6f40509ac77f…` | CANDIDATE_IN_48 |
| proof | calendar_proofs record (inside supplement; key = H(canon(record))) | `36bc3a89bd266b9d…` | `6b030c62fdaf3cd7…` | REKEYED_IN_CANDIDATE_SUPPLEMENT |
| validator | validator mechanism module (validate_input xnys_schedule) | `1b83cdcd4f6e2aaa…` | `ca3bafd87e7cb439…` | EXISTING_CANDIDATE_44 (no new file in -48) |
| driver | live driver (-04) | `5fed45242eb5ec46…` | `d11c6b587c028c26…` | CANDIDATE_IN_48 |
| gate | dispatch gate r4 | `b53996454650dafc…` | `94ef967ca832faea…` | CANDIDATE_IN_48 |
| adapter | live dry-run adapter (-19) | `e8605669db902c3e…` | `6980b5b3c887ea7e…` | CANDIDATE_IN_48 |
| executor | live readiness executor r4 | `e792b8b2b776adc7…` | `bbc23616b0b8c62f…` | CANDIDATE_IN_48 |
| entrypoint | route entrypoint (pilot_build) | `257d5bb99bcbae50…` | `442e56cc16bbbb7b…` | EXISTING_CANDIDATE_45 (no new file in -48) |
| constructor | construct_4h (authoritative for TD receipts) | `d47e8df14ec5f6f6…` | — | UNCHANGED |
| resampler | fetch_4h.resample_4h (convention reference ONLY, never a TD producer) | `2a4994a2 (prefix…` | — | REFERENCE_ONLY |
| collector | classifier collector @ab254c3 | `b683d277cc02a8d2…` | — | UNCHANGED (reads supplement fields at runtime) |
| lock | TD environment lock (NL-20261015) | `08b38cfa1880d328…` | — | UNCHANGED |
| wheelhouse | wheelhouse manifest (11 wheels, PMC 4.5.1) | `210b8273a15cc731…` | — | UNCHANGED |

## Edges (pin holder -> target, enforced at)

- **supplement -> manifest** — supplement fields base_manifest_canonical_digest / base_manifest_file_sha256 / base_manifest_id (fresh_supplement.json top level); driver reconcile live_driver.py:353
- **supplement -> validator** — supplement field calendar.mechanism_module_sha256 (+ calendar.mechanism / calendar.mechanism_module path strings)
- **supplement -> proof** — supplement entries.REQ-SPT-07/08.calendar_proof_digest -> calendar_proofs key
- **proof -> validator** — proof record field mechanism_module_sha256; verified equal to gate PIN_MECHANISM at dispatch_gate_r4.py:597 (Gate 7)
- **proof -> proof** — self-digest: key == H(canon(record)); checked at live_driver.py classify_closed (proof lookup) and dispatch_gate_r4.py:591
- **supplement -> collector** — supplement classifier_pins.collector_sha256 / collector_commit; driver reconcile live_driver.py:356-357
- **driver -> supplement** — live_driver.py:61 EXPECTED_SUPPLEMENT_SHA256 (byte pin enforced pre-parse :441)
- **driver -> manifest** — live_driver.py:60 EXPECTED_MANIFEST_DIGEST
- **driver -> validator** — live_driver.py:67 NL_MECHANISM_MODULE_SHA256 (declared integration pin; no operative comparison site inside the driver - operative mechanism enforcement sits in the gate)
- **gate -> driver** — dispatch_gate_r4.py:64 PIN_DRIVER + :51 P_DRIVER path; Gate 6 recompute :561-585
- **gate -> supplement** — dispatch_gate_r4.py:95 PIN_SUPPLEMENT + :53 P_SUPPLEMENT path; Gate 6
- **gate -> manifest** — dispatch_gate_r4.py:94 PIN_MANIFEST + Gate 6
- **gate -> validator** — dispatch_gate_r4.py:99 PIN_MECHANISM + :57 P_MECHANISM path; Gate 5 env check :529-543; Gate 7 derive_calendar :169 executes the file at P_MECHANISM in the pinned wheelhouse env
- **gate -> proof** — dispatch_gate_r4.py:103 PIN_CALENDAR_PROOF; Gate 7 :588-601
- **gate -> lock** — dispatch_gate_r4.py:100 PIN_LOCK + :540-551 (lock hash + PMC line == 4.5.1)
- **gate -> collector** — dispatch_gate_r4.py:96 PIN_COLLECTOR + P_COLLECTOR_GIT (git blob @ab254c3)
- **gate -> wheelhouse** — derive_calendar verifies all 11 wheel hashes vs wheelhouse SHA256_MANIFEST before use (:169-200)
- **adapter -> gate** — live_dry_run_adapter.py:65 PIN_R4_GATE + GATE_PATH (:63); loads gate by exact path+sha (_load_gate :88-99); reads gate pins G.PIN_SUPPLEMENT etc. from the loaded module (:162)
- **executor -> gate** — live_readiness_executor_r4.py:117 PIN_R4_GATE (recorded as gate_sha256 in the clearance record :461; operative gate loading flows through the adapter)
- **executor -> adapter** — live_readiness_executor_r4.py ADAPTER_PATH + :181 ADAPTER_SHA256; _load_live_adapter :184-200 (exact path+sha, origin check)
- **executor -> supplement** — live_readiness_executor_r4.py:125 PIN_SUPPLEMENT (8-hex prefix; declarative identity constant - no operative comparison site in the executor)
- **executor -> manifest** — live_readiness_executor_r4.py:124 PIN_MANIFEST (8-hex prefix; declarative)
- **entrypoint -> validator** — route binding: pilot_build_v6 loads the validator candidate as its validate_input (binding identity proven -46 Family A: the loaded candidate's validate/ValidationError ARE the -44 candidate's)
- **entrypoint -> constructor** — route binding: entrypoint hands validated ends to construct_4h (unchanged d47e8df1); F3 in -46 proves the pair end-to-end
- **collector -> validator** — td_min_collector.py @ab254c3 :527 version gate + :531 mechanism sha equality, both read FROM the supplement at runtime - the candidate supplement rebinds the collector dynamically; no collector candidate required
- **collector -> supplement** — td_min_collector.py @ab254c3 :507 base_manifest_digest equality (SPOT8 lineage supplement in the collector path; the FRESH driver builds the classifier view from the FRESH supplement - see -41 Edge 3)

## Graph cycles

One intentional cycle exists in the accepted pin graph: **supplement <-> collector**
(the supplement's classifier_pins name the collector hash; the collector checks the
supplement's manifest digest at runtime; both directions are enforced — see the edges
above and the -41 matrix). It is a consistency cycle, not an ordering problem: the
collector is UNCHANGED by this transaction, so it anchors the SCC as a fixed point,
and the ordering graph over the nodes this transaction changes is acyclic (verified
by the linter, checks C7).

## Substitution order and atomicity

**Atomic set A (must be designated together): supplement (+proof record) -> driver ->
gate -> adapter -> executor.** Each member hash-pins the next, so any partial state is
detectably inconsistent. Crucially, every inconsistent intermediate state FAILS CLOSED
at a hash check before any dispatch can occur (driver: SUPPLEMENT_SHA_MISMATCH;
gate Gate 6: PIN_MISMATCH; adapter: GATE_PIN_MISMATCH; executor: ADAPTER_PIN_MISMATCH).
Named inconsistent intermediate states (chain unusable, never silently runnable):
A1 candidate gate + original driver (Gate 6 driver check fails); A2 candidate driver +
original supplement (driver byte-pin refusal); A3 candidate adapter + original gate
(adapter gate-pin refusal); A4 candidate executor + original adapter (executor adapter-pin
refusal); A5 candidate supplement + original gate (Gate 6 supplement check fails);
A6 candidate gate + candidate supplement but original proof semantics (impossible by
construction here: the proof record lives INSIDE the supplement file).

**Independent legs:** the route leg (entrypoint candidate 442e56cc -> validator candidate
ca3bafd8 -> constructor d47e8df1) consists of already-committed candidate files; it has
no hash edge INTO the readiness chain except through the supplement/gate mechanism pins
in set A. The two legs must BOTH be complete before any live use, but neither leg's
internal order interacts with the other.

**Residual by-name binding (recorded, out of transaction scope):** modules that import
`validate_input` BY NAME from research_notes/pilot_harness (e.g. the original
pilot_build.py) still resolve the ORIGINAL validator 1b83cdcd. The adopted route binds
the candidate by exact path (gate P_MECHANISM; entrypoint candidate's proven binding),
never by name, so this does not create a mixed chain - but any future by-name consumer
must be treated as bound to the original mechanism until separately re-pinned.

## Governance requirements carried in the DAG

- PRECEDENCE: construct_4h is authoritative for TD receipts; fetch_4h.resample_4h is a
  historical-convention reference only (node `resampler`, no production edge).
- REQ-S2 (split exclusion at 4H assembly): adjudicated placement is the future 4H
  dataset-assembly component downstream of the constructor - validate/construct the
  complete receipt set first, then exclude bars AND candidate entries D-1..D+1 around
  each split effective session, recompute with no imputation. NOT implemented by any
  candidate in this package; it is a requirement on the assembly component + its proof.
- REQ-CLI (direct construct_4h CLI must fail closed): the constructor is UNCHANGED in
  this transaction and still ships a standalone CLI (the -42 preflight recorded the
  bypass as shipped). No candidate here satisfies REQ-CLI; the adoption transaction
  must either bind a CLI-refusing constructor variant (new candidate + proof) or carry
  deployment terms exposing only the entrypoint path. OPEN requirement - see
  NEXT_TRANSACTION_PROOF_SPEC.md.
