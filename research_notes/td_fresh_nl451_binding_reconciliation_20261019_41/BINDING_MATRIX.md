# BINDING MATRIX — TD FRESH path under NL451 (task -41 r1)

Every hash below was recomputed from committed bytes during this pass
(origin/main @ e821eee; classifier branch commit ab254c3). "Enforced at"
names the exact field or source line that makes the binding operative.

## Edge 1 — FRESH manifest → governing supplement: BOUND
- Manifest: `research_notes/td_fresh_full_manifest_preflight_evidence_20261016/fresh_manifest.json`
  sha256 == canonical digest `71aade8b…` (file bytes hash to the digest);
  `manifest_id` = `TD-ACQUISITION-MANIFEST-V2-FRESH-20261016` (51 requests).
- Supplement: `…/fresh_supplement.json`, sha256 `3cbdbf63…`,
  `supplement_id` = `TD-FRESH-FM-SUPPLEMENT-NL-20261016`.
- Enforced at: supplement fields `base_manifest_canonical_digest` =
  `71aade8b…`, `base_manifest_file_sha256` = `71aade8b…`,
  `base_manifest_id` = the FRESH id (fresh_supplement.json, top-level keys).
- Answer to the standing question: a FRESH-bound supplement EXISTS. It is
  neither the original SPOT8 supplement (`cccd5226…`) nor the NL451 SPOT8
  candidate (`9c712330…`); it was derived from the NL451 candidate by value
  with ONLY the base binding changed (supplement field
  `derived_from_supplement`, sha `9c712330…`).

## Edge 2 — supplement → live driver: BOUND (byte pin, pre-parse)
- Driver: `research_notes/td_fresh_live_driver_integration_evidence_20261016/live_driver.py`,
  sha256 `5fed4524…` (the -04 driver; the latest accepted fresh chain).
- Enforced at: live_driver.py:60-61 `EXPECTED_MANIFEST_DIGEST = 71aade8b…`,
  `EXPECTED_SUPPLEMENT_SHA256 = 3cbdbf63…`; :431-441 canonical supplement
  BYTES are hash-checked BEFORE parsing/use (refusal on mismatch);
  :332 `reconcile_supplement()` semantic reconciliation, incl. :345
  `supplement_id` equality and :356-357 collector pin equality against the
  supplement's `classifier_pins` (collector commit `ab254c3…`, collector
  sha256 `b683d277…`).

## Edge 3 — driver → classifier/validator/calendar: BOUND (two-part)
- (a) Driver-side classification: live_driver.py:529 `classify_closed()`
  does NOT import any calendar library (no `pandas_market_calendars` /
  `validate_input` import exists in the driver). It verifies the
  supplement's PRE-COMPUTED `calendar_proofs` record (digest-checked,
  `closed is True`, date in `window_dates`) plus the response-shape
  conjuncts, returning the proof digest. Classification is disabled if the
  proof record is unavailable/mismatched (:536-538).
- (b) Live re-derivation sits in the gate: dispatch_gate_r4.py:169
  `derive_calendar()` executes the PINNED mechanism's `xnys_schedule`
  inside the pinned environment for 2026-07-03 / 2026-07-02 (:208-214),
  and Gate 7 (:584-585) matches the result against the supplement's pinned
  proof record (`calendar_proofs` digest `36bc3a89…`, closed 2026-07-03).
- The candidate collector's own mechanism path (NOT the live path):
  td_min_collector.py @ab254c3 :507 supplement `base_manifest_digest`
  equality; :527 exact version-string gate vs the supplement's
  `expected_library_version`; :531 mechanism module sha256 equality;
  then live `validate_input.xnys_schedule` calls.

## Edge 4 — supplement/collector → validator + calendar version: BOUND
- Validator: `research_notes/pilot_harness/validate_input.py`, sha256
  `1b83cdcd…` — byte-identical at origin/main AND at ab254c3.
  Its only calendar channel: validate_input.py:56-57
  `import pandas_market_calendars as mcal; mcal.get_calendar("XNYS")`.
- Fresh supplement calendar block: `expected_library_version` = `4.5.1`,
  `mechanism_module_sha256` = `1b83cdcd…`, `mechanism` =
  `pandas_market_calendars:XNYS via pilot_harness/validate_input.py::xnys_schedule`,
  `lineage` = `NL-20261015`, `lineage_lock.lockfile_sha256` = `08b38cfa…`.
- Field-by-field comparison vs the -40-accepted NL451 candidate
  supplement (`9c712330…`): ALL operative calendar fields IDENTICAL
  (library, version 4.5.1, lineage, lock sha, mechanism string, mechanism
  module, mechanism sha). Differences are provenance text only
  (NL451 carries `expected_library_version_basis` + `lineage_environment`;
  FRESH carries `calendar.environment_binding` instead) — no operative
  difference. Closed-day entries: both supplements carry REQ-SPT-07/08
  with the SAME request digests (`a259901e…`, `f547d8fe…`); FRESH adds the
  window/proof linkage to the single proof record `36bc3a89…`
  (2026-07-03, closed, 4.5.1, mechanism `1b83cdcd…`).

## Edge 5 — calendar → lock / environment: BOUND
- TD lock sha256 `08b38cfa…`; wheelhouse `~/workspace/td_nl_wheelhouse_20261016/SHA256_MANIFEST.txt`
  sha256 `210b8273…` (11 wheels; PMC 4.5.1 wheel `7b4f3478…`) — the pin the
  -40 package cited by reference (this pass records it explicitly, per the
  -40 review's minor limitation note).
- Enforced at: dispatch_gate_r4.py:100 `PIN_LOCK = 08b38cfa…`, :541 lock
  hash check; :540-551 the lock's PMC line must equal exactly
  `pandas_market_calendars==4.5.1` and the environment record must report
  `4.5.1`; live_dry_run_adapter.py:135-143 parses the same PMC line from
  the pinned lock for its evidence record.

## Edge 6 — gate → readiness executor: BOUND; executor → classifier/calendar: DECOUPLED (by design)
- Gate: `research_notes/td_policy_a_live_readiness_packet_20261017_11/dispatch_gate_r4.py`,
  sha256 `b5399645…`. Its pins: :64 `PIN_DRIVER = 5fed4524…`, :94
  `PIN_MANIFEST = 71aade8b…`, :95 `PIN_SUPPLEMENT = 3cbdbf63…`, :96
  `PIN_COLLECTOR = b683d277…`, :99 `PIN_MECHANISM = 1b83cdcd…`, :100
  `PIN_LOCK = 08b38cfa…`, :90 `PIN_POLICY_A = 5d9d82ca…`; paths :50-60
  (P_DRIVER/P_MANIFEST/P_SUPPLEMENT/P_COLLECTOR_GIT @ab254c3/P_MECHANISM/
  P_LOCK). Gate 6 (:561-565) recomputes manifest/supplement/source hashes;
  Gate 7 re-derives the calendar proof (Edge 3b).
- Executor: `research_notes/td_live_dryrun_clock_adapter_binding_20261017_19/live_readiness_executor_r4.py`,
  sha256 `e792b8b2…` (chain head at commit `3932903`, ancestor of
  origin/main — verified). Pins: :117 `PIN_R4_GATE = b5399645…`, :119
  `PIN_RESOLVER = c8271193…`, :120 `PIN_HELPER = 8b1f42e8…`, :122
  `PIN_POLICY_A_DIGEST = 5d9d82ca…`, :124 `PIN_MANIFEST = 71aade8b` (prefix
  form). It contains ZERO references to the supplement, validator,
  classifier, or any calendar mechanism (full-text search, 0 hits) — the
  executor binds the GATE, and the gate binds the calendar chain.
- Adapter: `…/live_dry_run_adapter.py`, sha256 `e8605669…`; :162 records
  `supplement_sha256` from the gate module's `PIN_SUPPLEMENT`; :52 imports
  stdlib `calendar` (timegm only) — NOT pandas_market_calendars.
- Resolver: `research_notes/td_credential_helper_path_binding_20261017_08/credential_resolver.py`,
  sha256 `c8271193…`; sanctioned helper
  `/opt/hatch/skills/skill-creator/bin/dynamic_credentials.py` sha256
  `8b1f42e8…` (recomputed live this pass).
- Ledgers (for completeness of the chain record): source
  `research_notes/pilot_harness/credit_ledger.json` `7e5ccef0…`;
  candidate `research_notes/td_ledger_compat_card_binding_20261017_07/candidate_credit_ledger.json`
  `79ff4844…` — both match their pins; neither was touched.
- Driver revision note: a `live_driver_r3.py` (sha256 `b83b97d7…`) exists
  in the -08 package as trial scaffolding; the gate/executor chain pins
  the -04 driver `5fed4524…` (PIN_DRIVER), which is therefore the bound
  live driver. No conflict: the r3 copy is not referenced by any pin in
  the accepted chain.

## RESIDUAL SWEEP (main + classifier branch @ab254c3 + recovery branch refs)
1. `5.5.0` in pin-bearing positions:
   - origin/main, all `*.py`/`*.json`: ONLY
     `research_notes/recovery_4h_20261004/cp1_followup/audit_52symbol.json`
     (the CP1 audit record — historical, expected; it is the conflation's
     source document, not a binding).
   - @ab254c3: the candidate's own supplement `p2_spot_supplement_v2.json`
     (`expected_library_version: "5.5.0"` — the unmerged candidate's own
     superseded pin, operative ONLY inside that candidate) and its fixture
     suite `test_closed_session_classifier.py` :58/:104/:127/:304 (stub
     version strings for that supplement — candidate-internal).
   - NO occurrence of 5.5.0 anywhere in the FRESH chain (manifest,
     supplement, driver, gate, adapter, executor, resolver).
2. `cccd5226…` (original SPOT8 supplement): ZERO references in `*.py` code
   on origin/main; 14 files total, all memos/manifests/records
   (historical). It binds nothing in the live chain; the gate's
   P_OLD_SPOT8 path points at the old SPOT8 acquisition STATE directory,
   not at the supplement.
3. `9c712330…` (NL451 SPOT8 candidate): cited on main only in NLQUAL-era
   memos/manifests, the adoption-packet draft, the -40 package, and the
   FRESH supplement's `derived_from_supplement` provenance field. It is
   NOT in any operative pin position in the fresh chain (gate/driver pins
   name `3cbdbf63…`). Its SPOT8-only scope caveat IS carried with it
   where it matters: -40 `ADOPTION_CANDIDATE_RECORD.md`:27 states the
   SPOT8-only scope and that FRESH use needs a new supplement version —
   which the FRESH supplement is.
4. Stale hashes: NONE. Every pin in the tasking brief and every internal
   pin in the driver/gate/executor/adapter was recomputed against the
   committed bytes and matched (see INSPECTED_FILES.md for the full list).
   Labeling clarification, not a mismatch: the brief's "manifest file
   ef82fb37" is the sha256 of the r2 preflight package's
   `SHA256_MANIFEST.txt`
   (`td_fresh_full_manifest_preflight_evidence_20261016_r2/SHA256_MANIFEST.txt`,
   verified `ef82fb37…`); the manifest FILE itself hashes to its canonical
   digest `71aade8b…`.
5. Unbound calendar imports: `research_notes/pilot_harness/construct_4h.py`
   :49-50 imports `pandas_market_calendars` and calls
   `get_calendar("XNYS")` directly. It is NOT referenced by any pin in the
   readiness chain (gate P_ paths do not include it) — it is the pilot
   harness's post-acquisition 4H construction component, outside the
   readiness binding chain swept here. Recorded as an observation for
   adjudication awareness, not a chain defect. (The -40 P8 probe verified
   the registered-XNYS semantics this import relies on under 4.5.1.)
