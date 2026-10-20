# INSPECTED FILES — exact identities (all read as text; nothing executed)

## Spec / adjudication sources
- Issue #1 comment `6280342431` — -41 verdict + this task's dispatch
  (canonical spec; fetched via the public GitHub API, paginated).
- Issue #1 comment `6278932260` — Option B adjudication (chain context).
- -41 package @ commit `91604d06952f7fe2000f902789b2778fd4b80514`:
  `research_notes/td_fresh_nl451_binding_reconciliation_20261019_41/`
  (RECONCILIATION_MEMO.md `d5d9020f…`, BINDING_MATRIX.md `118434f7…`,
  INSPECTED_FILES.md `e07337f7…` — prefixes as re-verified by the -41
  adjudication; F3 at RECONCILIATION_MEMO.md:56–60).

## Construction path (pilot_harness)
- `research_notes/pilot_harness/construct_4h.py` —
  `d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd` (263 lines;
  key lines: bins :44–45, session_close_et :49–61 [import :53, get_calendar
  :54], session_closes override :71, as_of :105–111, ends precedence
  :135–188, binning :193–199, bin-close rule :205–216, completed-bin filter
  :218–221, agg :223–227, CLI bypass :220–263, docstring warning :24–27).
- `research_notes/pilot_harness/pilot_build.py` —
  `257d5bb99bcbae50442491b71429abb6b37b8c5cbcd1e4bf93b6010ad9e5a508`
  (unconditional source verification :88–97; validate call :117–118;
  construct call WITHOUT session_closes :124–130; output :132).
- `research_notes/pilot_harness/validate_input.py` —
  `1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58`
  (xnys_schedule :47–56; expected_1h_starts :59–74; V10 :155–179; V11
  :196–233; V8/V6/V4 :238–371).
- `research_notes/pilot_harness/verify_sources.py` —
  `a0bd2e4cdce44be5d9fcc1d7c21046391d36c9bd366a959df03bf5d19c9a79e0`
  (PINNED = archival strategy sources only: pine_backtest.py `447a9a13…`,
  scanner_rules.py `7db282dd…`, :23–28).
- construct_4h hash also recorded in unadopted candidate evidence:
  `research_notes/td_combined_candidate_verify_evidence_20261014/
  candidate_manifest.json` (1 hit) and
  `research_notes/TD_COMBINED_CANDIDATE_VERIFY_20261014.md` (2 hits) —
  historical candidate records, NOT a chain pin (per -41 verdict).

## Canonical resampler / strategy lineage
- `canonical_baseline/scripts/fetch_4h.py` —
  `2a4994a26dbb98e244a14173a06697476835206c3d8d268ad21900dd43e0cbeb`
  (AGG :25; resample_4h :27–40 [per-day origin :31–33, resample :34,
  dropna :35, dedupe keep-last :38]; adjustment provenance note :8–11;
  fetch loop :43–85). Matches the -22 recovered-module pin exactly.
- Restored strategy sources (context): adopted at -23 (commit `b5af7da`);
  fetch_4h lineage per -22 (commit `8e0a187`).

## Calendar artifact + fold consumer
- `research_notes/xnys_isolated_calendar_generation_20261019_35_r2/
  XNYS_SESSION_SCHEDULE_V2.json` —
  `3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88`
  (524 sessions; coverage 2024-09-16 → 2026-10-16; package commit
  `9c62e255…`; receipt GENERATION_RECEIPT.md `cccfd541…`).
- `research_notes/validation_fold_coverage_boundary_20261018_28/
  fold_materializer_v3.py` —
  `e1b0dfed43c7c0817d2816f5398a1601a3886b107f7eb882e2e46a316f53d4c8`
  (docstring contract :1–51; ANCHOR_TIMES :69; accepted at commit
  `5dc8b2a…`).

## Validation contract
- `research_notes/validation_prereg_finalization_20261018_25/
  PREREGISTRATION.md` —
  `ccf1a988a93026a2032f5cb94f6c6d9e78705e5121ca049d60ec2a1272473c24`
  (timestamp-only input contract :24; holdout seal :50).
- `research_notes/VALIDATION_GOVERNANCE_CLOSURE_20261018_24.md` —
  Amendment v1 split handling (S1 :36, S2 :37, S3 :38; original protocol
  LOST, replaced :32).

## Readiness chain pins (recomputed this pass)
- `research_notes/td_fresh_full_manifest_preflight_evidence_20261016/
  fresh_manifest.json` —
  `71aade8bfbb1f94b25d780bdf68f08f7f127740fc745c1755432acc5f74044db`
- `research_notes/td_fresh_full_manifest_preflight_evidence_20261016/
  fresh_supplement.json` —
  `3cbdbf63fd49b021dc74f63727098551753949f8684967981c65f66101f95a86`
- TD lock `08b38cfa…` / wheelhouse manifest `210b8273…` — as pinned in the
  -41 reconciliation (not re-derived here; no env work in scope).

Elapsed: ~12 min of ≤35 (corrected from an initial ~15 min estimate in the first commit). Repair minutes: 0. Nothing executed, installed,
or edited outside this package.
