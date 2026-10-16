# Rev3 Manifest Adoption Readiness — QF-YAHOO-REV3-MANIFEST-ADOPTION-READINESS-20261016-17 r1

**Terminal token: `REV3_MANIFEST_ADOPTION_READY`** (candidate only — this task adopts nothing)

Spec: Issue #1 comment 6208892272. Offline only. Elapsed ≈6 minutes of the ≤30 cap; no repair extension. Trials: one build pass, one checker refinement (see Failures), zero failed verification checks in the final run (35/35 PASS).

## Inputs (all pins verified before any work)

| Input | Pin | Verified |
|---|---|---|
| Frozen rev2 manifest `research_notes/yahoo_clean_capture_preflight_20261015/capture_manifest.json` | sha256 `634c4541…`, git blob `0d1bc602…` | yes, unchanged after the run |
| -13 rev3 candidate `research_notes/yahoo_qfar1_preflight_20261015/capture_manifest_rev3_candidate.json` | sha256 `617f8610…`, git blob `c62d4daa…` (spec pin) | yes |
| QFAR1 design r3 `research_notes/YAHOO_SINGLE_BLOB_ARCHIVE_DESIGN_20261015.md` | sha256 `cd9ef36d…` | yes |
| Accepted publisher (commit `53bdc672…`) `qfar1_publisher_h16.py` | sha256 `1d4c1923…` | yes |

## What the -13 candidate actually was (finding)

A full copy of the frozen rev2 manifest with **only** the ceilings block changed and a `revision` block appended (machine-proven, check IN-3). Every rev2 word outside those two places — including the stale local-VM durability narrative ("NOT DEMONSTRATED"), the per-file `os.link` publication narrative, and `execution_packet.later_command` pointing at the parked `execute_capture.py` — was inherited verbatim. Those inherited references were the normalization work of this task; no request, gate, or session content anywhere needed correction.

## Normalization applied (16 leaf changes, all classified in the semantic diff)

**Approved ceiling revision (5)** — values taken from the -13 candidate verbatim; this task introduced no ceiling number of its own:
- `bytes_total` 536,870,912 → **67,108,864** (`QF_SHARED_TOTAL_CEILING_BYTES`, scope = Σ of all **158 physical members**: 156 payloads + `manifest.json` + `SHA256SUMS`)
- added `bytes_total_definition`, `bookkeeping_reserve_bytes = 32,164`, `payload_budget_bytes = 67,076,700` (arithmetic verified: 67,108,864 − 32,164 = 67,076,700)
- added explicit `oversize_streaming_rule`: an oversized streaming response **consumes its single attempt** — cut off at the ceiling, symbol held, attempt never re-requested (the -13 adjudicated rule, previously present only in the candidate's revision note, now stated in the operative ceilings block)
- per-symbol (33,554,432), rows (20,000) and wall (1,800 s) ceilings unchanged

**Storage / publication / execution references (11)**:
- `archive.root`, `archive.durability`, `archive.publication` superseded: the local dir is staging only; durability is the designated **private** repo; publication is QFAR1 single-blob only — the per-file `os.link` narrative is named superseded and forbidden
- `archive.attempt_journal`: rule preserved word-for-word in substance (ATTEMPT_CONSUMED_AMBIGUOUS / SKIP_VERIFIED / HOLD:FINAL_MISMATCH); the -08 fixture proof clause replaced by a provenance note (the fixture is evidence, not the route)
- `execution_packet.later_command` **removed** (parked-executor route); explicit **handoff contract** added: clean capture executor (future, separately authorized, written fresh) → independent validation pins (G1–G11 validator output, never the capture process's own claims) → accepted QFAR1 publisher pin `53bdc672…`. No route passes through any parked executor
- new `publication_binding`: design pin, publisher commit + file hash, target `mickaellall116-cmyk/qf-data-archive` (private), ref `refs/heads/qf-archive`, path `captures/<capture_id>.qfar`, member accounting (156 + 2 = 158) with the acyclic binding graph, and **final verification** — resolve the exact commit by pinned SHA, recompute `CONTAINER_SHA256`, verify all 158 members against the independent validation pins; **no branch-tip-only trust** (a branch tip is never sufficient evidence; partial states are no-publication)
- `status` / `task` / `revision` provenance updated; candidate remains explicitly NOT ADOPTED

## Proven unchanged (canonical-JSON deep-equality, rev2 vs normalized rev3; hashes in the semantic diff)

`request_order` (all 52, frozen order, QQQ benchmark at i=52), `request_params` (1h, `auto_adjust=False`, `prepost=False`, `actions=True`, explicit start = execution − 729d, COVERAGE-LIMITED terms), `runtime_pins` (Python 3.12.3 / pandas 2.1.4 / numpy 1.26.4 / yfinance 1.7.0 + file hashes), `session_construction_freeze`, `qualification_gates_frozen` (G1–G11), `symbol_mapping`, `universe_source` (`44b0d8ba…`), `capture_id`, `purpose`, `schema`, `archive.layout`, `archive.restart`, `archive.rollback`, `execution_packet.abort_rules`, and `call_budget` outside the ceilings block (52 requests, 1 attempt/symbol, no retry/fallback, ≥1.0 s shared limiter). 14/14 preservation proofs PRESERVED; stale-token scan clean (`os.link` and the old total survive only inside supersession/provenance records).

## Trials / failures

- Build v1 verification: 34/36 — two scan false positives: my own supersession text names `os.link` and the revision record documents the old total `536870912` while removing them. The checker was refined to allow both tokens only inside supersession/provenance records; the manifest content was not changed to evade the scan. Final run: **35/35 PASS**, 16 leaf changes, 0 unclassified → token per spec item 5.

## Artifacts (uncommitted in the worktree)

Package `research_notes/yahoo_rev3_manifest_adoption_readiness_20261016/`:
- `capture_manifest_rev3_normalized_candidate.json` — sha256 `fe3611e78347806a19d9810a3c141bab5225f2b0785d38e1ba6f013c76d76c5e`
- `semantic_diff_rev2_to_rev3_normalized.json` — machine-readable diff: every change classified, every preserved section hash-proven
- `verification_results.json` — 35 checks, all PASS
- `build_rev3_normalized.py` — the builder/verifier (normalized manifest is derived from rev2 by construction, not hand-edited)
- `SHA256_MANIFEST.txt` — package hashes incl. this memo

## Scope confirmation

Offline only: the spec fetch was the sole network call. Zero authenticated GitHub operations, zero vendor/model/API calls, zero downloads, zero installs, zero spend, **zero adoption/merge** — the frozen rev2 manifest stays the live pin until a separate adoption act; zero capture/backtest/holdout/production changes. The -13, -14, -15, -16 packages and the frozen manifest are byte-identical after the run (hashes re-verified). U-1 remains HOLD and is not advanced by this result.
