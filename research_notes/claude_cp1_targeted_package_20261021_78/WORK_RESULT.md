# WORK RESULT — QF-CLAUDE-CP1-TARGETED-PACKAGE-20261021-78 r1

**Terminal: CLAUDE_CP1_TARGETED_PACKAGE_SENT__VERIFIED**

Assembled offline from existing immutable evidence only — nothing rerun, no vendor/model calls, no holdout access. Spec: ChatGPT's Slack message TS 1792624375.031749 (2026-10-21 19:12:55 EDT). Single-dispatch check passed (no prior -78 CP1 stage/package; the calendar backward-extension audit originally numbered -78 was renumbered -79 and its package, commit a08e08c, was sighted and left untouched — its outputs are included as coverage evidence).

## The bundle

- **ZIP:** `claude_cp1_targeted_package_20261021_78_r1.zip` — 5,145,070 bytes, **SHA-256 `96a3117f7b9114418f24bd6a32528c05c4ad226475178b78e26ee4431ff71d53`**, 177 entries (176 evidence files + BUNDLE_INVENTORY.json). Immutable once hashed; any correction ships as r2 with a new hash.
- **Retrieval route (Mike):** private repo `mickaellall116-cmyk/qf-data-archive`, commit **518915a**, path `captures/claude_cp1_targeted_package_20261021_78/` (ZIP + BUNDLE_INVENTORY.json + capture_manifest.json + SHA256SUMS). Verified after push by fresh re-fetch: SHA256SUMS pass 3/3 and the ZIP is byte-identical to the assembled artifact.
- **Inventory:** BUNDLE_INVENTORY.json (in this package and inside the ZIP) — per file: bundle path, byte length, SHA-256, Git blob SHA and commit pin for repo files. Every inventory hash was recomputed against the actual bundle bytes before handoff (176/176 OK).

## Contents by category

1. **Prior CP1 package** — the entire `recovery_4h_20261004` tree extracted at pin 84942a6929258a0c316a6e849a7480c286013d95 (cp1_bundle, cp1_followup, spec, fixtures, evidence, chart-review pilot), plus the later CP1 evidence closure (incl. archival_sources_v1) pinned at origin/main aa5bc666.
2. **Day-1 raw capture** — all 20 files from qf-data-archive@2f223cf `captures/td_probe_day1_20261021/` (manifest, SHA256SUMS, NVDA/TSLA/AAPL bars + receipts, usage body, credit ledger); every file re-verified against the archive SHA256SUMS.
3. **Pairing logic** — the accepted -74 candidate's analyzer/runner/manifest/preflight/temporal-gate code at result commit 71eee93 (all files cross-checked against the package's own SHA256_MANIFEST) and the full -75 execution package at ee7f71c.
4. **2023 coverage inventory** — the -77 readiness matrix (22b6903), the -79 calendar backward-extension audit (a08e08c), and the -31 NYSE official calendar capture records.
5. **Calendar classifier** — ab254c3's three files (collector cross-checked: b683d277… matches the -49 recorded pin), the -35 r2 XNYS_SESSION_SCHEDULE_V2 artifact (SHA-256 3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88), and dependency pins (-43 requirements/lock, -30 dependency map).
6. **Frozen universe/provenance** — canonical_baseline/UNIVERSE.md and the FROZEN X2 cohort definition.
7. **Pinned code** — the full construct_4h route chain (entrypoint v7 84ccd2c6…, CLI-guard constructor 3f432e7e…, original constructor d47e8df1…, validator ca3bafd8…, adapter/driver/gate/executor r5, supplement v2) — **every file's SHA-256 matches the ROUTE_MANIFEST_CANDIDATE_V2 recorded pin**; ROUTE_MANIFEST itself included; -25 fold materializer + inference layer; FRESH manifest (matches the recorded 71aade8b… digest). Entry/exit engine bytes are carried via category 01b (pine_backtest.py, c1_corrected_baseline_20261003.py, pine_stack.py, scanner_rules.py) and cross-referenced in the inventory.
8. **Preregistration + strategy-family ledger** — -25 PREREGISTRATION + amendments v2/v3/v4, research_mandate.md, TEST_LEDGER.md, family_ledger.json, killed_family_registry_export.json.
9. **Yahoo 10ae732** — candidate source at pin 10ae732 plus the retained ordinary observation evidence (FEED_RECOVERY_OBSERVATION_PIN_20261014; yahoo_r2_observation_closure_evidence_20261015).
- **reported/** — memos/interpretations kept separate from raw evidence: FORWARD_TEST_RECONCILIATION_20261021.md, FORWARD_TEST_COHORT_CLASSIFICATION_FREEZE_20261021.md.

Excluded per spec: credentials, private identifiers, sealed holdout payloads (metadata/inventory references only).

## Missing declarations (explicit — no substitutes, no re-creations)

- **M1 — PMC 5.5.0 dependency closure: MISSING.** Nothing of it exists in either repo or on this VM (the classifier-integration HOLD). Included instead: the PMC 4.5.1 wheelhouse digest as recorded in the route manifest, and the -43/-30 dependency pins that do exist.
- **M2 — D1 backtest_cache bytes (52 h4_*.pkl): DESTROYED** with a prior VM replacement; only the SHA-256 pins survive (included, category 01).
- **M3 — Benchmark loader executable bytes (SPY designation): MISSING as recorded** in the -21 matrix row 1.3 — prose-only in the committed tree; declared, not reconstructed.
- **M4 — Yahoo ordinary observation logs beyond the repo-retained set: NOT RETAINED** (category 09 is everything that exists).
- **M5 — Sealed holdout payloads: EXCLUDED BY SPEC** (see inventory for the NVDA-overlap note).

No required raw evidence was absent, so the spec's HOLD branch was not triggered: the anticipated gaps (M1–M4) are exactly the ones the spec instructs to mark missing.

## Disclosures

- The -74 pairing package was extracted at its result commit 71eee93 (package tip on origin/main); its BUILD_RESULT/SHA256_MANIFEST are included so Claude can re-derive every pin.
- One assembly repair, disclosed: the first archive push attempt failed before any file operation (credential helper not persisted in the temp clone's config); fixed the clone config and re-ran — no partial state resulted.
- The ZIP entry timestamps are fixed at the spec instant for determinism; file contents are byte-exact extractions at the recorded pins.
