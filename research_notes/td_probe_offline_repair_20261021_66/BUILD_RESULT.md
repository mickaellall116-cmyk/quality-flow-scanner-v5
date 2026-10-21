# TD PROBE OFFLINE REPAIR — task -66 r1 RESULT

Task: QF-TD-PROBE-OFFLINE-REPAIR-20261021-66 r1
Spec: Issue #1 comment 6310607516 (independent adjudication of -65:
HOLD with three material fail-closed defects; one bounded successor
package, new files only, -65 preserved immutable, one
implementation/test attempt after precommit, ≤45 min).

## TERMINAL

TD_PROBE_OFFLINE_REPAIR_READY__INDEPENDENT_REVIEW_REQUIRED__USER_GO_STILL_REQUIRED

## The three repairs (file/line evidence)

1. **C2 mixed-basis false PASS — FIXED** (`probe_analyzer.py`).
   `check_c2` (L236) now classifies every pre-split bar's volume
   ratio as scaled / unscaled / other and requires a UNIFORM class:
   a mixture of factor-scaled and unscaled bars returns FAIL with
   convention INCONSISTENT (L273), as does any bar fitting neither
   convention or any post-split bar off ratio 1. Nonempty coverage
   is required: no pre-split bars -> EvidenceHold
   C2_PRE_COVERAGE_EMPTY (L250); no post-split bars ->
   C2_POST_COVERAGE_EMPTY. The -65 fixture that exposed the defect
   used factor 5 (an "other" bar); the new A01 fixture mixes
   factor-scaled and ratio-1 bars — the exact case -65 passed
   falsely — and now fails C2 while C1 (prices) still passes,
   isolating the repair.

2. **Receipt identity not verified — FIXED** (`probe_analyzer.py`).
   `verify_receipt` (L108) now takes an expected request_id and
   rejects any mismatch with RECEIPT_ID_MISMATCH (L132) before
   parsing; it also requires present, integral, ordered
   request/receipt timestamps (RECEIPT_TS_INSANE) and rejects
   future-dated receipts when now_ms is supplied
   (RECEIPT_TS_FUTURE). `analyze_revision` requires base and
   revision expected IDs to be distinct (RECEIPT_ID_AMBIGUOUS) and
   exact. `parse_bars` (L158) verifies snapshot meta symbol +
   interval (SNAPSHOT_META_MISMATCH, L174-183), unique strictly
   ascending datetimes (BARS_NOT_STRICTLY_ASCENDING, L198), and
   requested-window containment (BAR_OUT_OF_WINDOW, L205) — all
   before any C1-C6 check runs.

3. **Cached usage PASS not integrity-bound — FIXED**
   (`account_preflight.py`, wired in `probe_runner.py` L264-265).
   `AccountPreflight.check` persists a canonical sanitized response
   payload + its SHA-256 in the receipt (L81, L132).
   `DailyUsageSession._verify_cached` (L186) re-verifies a cached
   receipt before reuse: verdict/day/identity, manifest SHA-256
   binding (L202), store-marker digest binding (L205), required
   headroom binding — a cache written for weaker headroom is never
   reusable (L207) — payload digest + field re-derivation of
   current_usage/plan_limit (USAGE_CACHE_BODY_ALTERED, L216-223),
   headroom still holding, and timestamps neither stale (>1 day)
   nor future-dated (USAGE_CACHE_TIMESTAMP, L231-238). O_EXCL still
   protects creation; verification now protects reuse.

Unchanged from -65 (verified by regression): the 9-leg manifest
shape (task/manifest_id re-stamped for -66), max_attempts=2,
12 expected / 24 hard-max ceiling arithmetic incl. 3 usage
preflights, ≤2 usage attempts, temporal R7/R30 elapsed-time gate,
scope allowlist before transport construction, CLI exit-3 refusal
paths, sampled-window verdicts only (no global S2 verdict anywhere).

## Qualification — ONE attempt, 30/30 PASS

Harness: `tests_qualification.py` (td66_qualification_r1).
Exact command (run from this directory):
`python3 -W error tests_qualification.py`
(warnings are errors inside the harness as well). Run 1: exit 0,
stderr empty, all_pass=true. Permitted byte-identity repeat: exit 0,
stderr empty, stdout byte-identical to run 1 — stdout SHA-256
`0073f2d46a2c1894698ba5e4aaa9f2f242e75a73e69c09845eab6bed0ed3fcfb`
both runs. Full per-case output: QUALIFICATION_RESULTS.json.

- Regression Q01-Q20 (the -65 set, re-run against the successor):
  20/20 PASS.
- Adversarial A01-A10: 10/10 PASS —
  A01 mixed factor/1 pre-split volume -> C2 FAIL/INCONSISTENT;
  A02 swapped request IDs (twin splits, twin none, revision base,
  revision leg — four sub-cases) -> HOLD RECEIPT_ID_MISMATCH;
  A03 duplicate / out-of-order / out-of-window bars -> HOLD;
  A04 meta symbol + interval mismatch -> HOLD;
  A05 edited usage PASS -> USAGE_CACHE_BODY_ALTERED;
  A06 cross-manifest cache -> USAGE_CACHE_BINDING;
  A07 weaker cached headroom (2 cached vs 10 required) ->
  USAGE_CACHE_BINDING; A08 stale (25h) and A09 future (+1h) cache
  timestamps -> USAGE_CACHE_TIMESTAMP; A10 post-only / pre-only
  windows -> HOLD C2_PRE/POST_COVERAGE_EMPTY.
  Every A05-A09 refusal is proven BEFORE data fetch: the seeded
  store aborts the day run with zero data-transport calls and zero
  usage-transport calls.

## Component SHA-256

- probe_analyzer.py    10ce932e031166bb4b3aeff623c0e798ddb5f0730cf8f5ee8adf877912f89851
- account_preflight.py a9b9e470bd069449bff2b9a3772473f49bb401e5140ccee5bb8d871ddc3a4cf2
- probe_runner.py      c43500cc1397194fa18563a9677eef2a1481019418d1ce7e1cc8ac716a26cc51
- temporal_gate.py     55625fd101ee1dcbabd8a17f5ae1c9ed0cfa42a3b3a0ed203ad2c8a445e7e0f5
- probe_manifest.json  1bb86e17ee7907bae67db9c22b0a74cc61027c495c1f1ed74d65df17585a53e1
- tests_qualification.py 0ed744024e6cd66191dbe732057901103108f1d2b607d39864c2ef3b465cef5a
- make_fixtures.py     58cb82e1e4e57caf3f3af23d50ca77608bd97618f362fa3e1f617d9ad0f88782
Full package manifest: SHA256_MANIFEST.txt (51 entries at precommit;
regenerated at result to cover this memo + QUALIFICATION_RESULTS).

## Commits

- Precommit (source/manifest/fixtures/SHA manifest BEFORE
  execution): 789629b258be17cb768636bcb8887c5c17aeb182
- Result: see the commit carrying this memo (hash reported in the
  bridge/Slack work-result post; both verified ancestors of
  origin/main).

## Elapsed / repair

Spec fetch 07:57:50Z -> result verified on origin/main 08:09:08Z:
≈11 minutes of the ≤45 cap (corrected from an initial ≈13 draft
figure in this memo's first committed version — the verified
remote-verification timestamp is 08:09:08Z). Repair minutes: 0
(first attempt
passed; no in-run repair; the byte-identity repeat is the permitted
post-pass repeat, not a repair).

## Attestation + disclosures

NO-CALL / NO-SECRET ATTESTATION: no vendor, network, API, or model
calls were made (the read-only public GitHub fetch of the spec
comment is the sole network use); no credentials were read,
resolved, or displayed; zero credits spent; synthetic fixtures
only; no real ADJ/S4/REV execution; no scheduling; no edits to -65,
frozen, or live paths; no adoption or integration; no S2
implementation, no -61 rerun, no performance computation, no
holdout/production/trading access. REQ-S2 remains HOLD; entries
remain PAUSED; the live probe remains USER-GO HOLD.

Disclosures:
- Elapsed clock started at the spec fetch (07:57:50Z) by the parent
  lane's dispatch; build work began immediately after.
- The successor package started as byte copies of the -65 files;
  only the three defect sites, the runner's session wiring, and
  provenance stamps were changed, plus additive fixtures/tests.
  temporal_gate.py is byte-identical to -65 apart from its header
  comment (its base-evidence verification already bound
  request_id/params/timestamps/SHA).
- /api_usage schema conformance, credential resolution,
  account/plan status, credit headroom, host clock, and network
  egress remain UNTESTED UNTIL USER GO — synthetic fakes only.
- Candidate only: NOT adopted, NOT integrated. Passing two sampled
  windows cannot globally retire S2 (governance correction
  preserved).
