# Claude audit bundle — rev 5 — provenance of the V5.4 wrapper/grader files

**Date:** 2026-09-28
**Purpose:** M5 of the rev-5 mandate (GitHub Issue #1, comment `5877927506`):
the exact local `v54_engine.py` / `v54_rules.py` bytes from which the §2
transcription was made, preserved byte-identical for Claude's independent
re-audit.

## Files

| File | SHA-256 (untouched bytes) | Lines | Local mtime |
|---|---|---|---|
| `v54_engine.py` | `bde3288307ac7b9bfbded29af89b056ae849f49d91b51c1151dad860224eb8fb` | 368 | 2026-09-15 12:31:22 -0400 |
| `v54_rules.py` | `1b55dedce3b17b1670ac7ee75bfcf4375a0162a1daa780a8abb4199c9ebb817a` | 196 | 2026-09-15 12:30:45 -0400 |

- Source paths (local, untracked): `~/workspace/quality-flow-scanner-v5/v54_engine.py`,
  `~/workspace/quality-flow-scanner-v5/v54_rules.py`.
- The copies in this directory were verified byte-identical to the sources
  (`sha256sum` match) on 2026-09-28 **before** any read beyond hashing.
  The sources have not been modified.
- Neither file is committed in the GitHub repo (no commit ref exists); the
  version pin is `V54_RULE_VERSION = "2026-09-15-v54"` (declared inside
  `v54_rules.py`).

## Role statement

- `v54_rules.py` — frozen V5.4 hard gates (`v54_hard_gates_pass`: structural
  contract + ADX ≥ 20) and the frozen A/B/C grader (`v54_grade`,
  `v54_annotate`). Docstring: "Frozen 2026-09-15 (see
  chatgpt_handoff_brief.md — the frozen source of truth)."
- `v54_engine.py` — V5.4 scan engine: pure setup triggers
  (`_pure_setup_triggers`, no score thresholds), V5.4 classification
  (`v54_classify`: state/entry/protection re-derived without scores;
  the V5.3 `classify_symbol` row is computed for LOGGED-ONLY control
  fields), MTF trend-state wrapper (`_v54_trend_state`), scan loop
  (`v54_scan_symbols`, default `period="180d"`), qualified-signal filter
  (`v54_qualified_signals`: every hard-gate-qualified signal kept,
  including C).

## What the auditor should check

For each frozen rule in
`research_notes/CANONICAL_RECONSTRUCTION_FROZEN_RULES_20260928_REV5.md`
§2, the basis note classifies it as **COPY** (verbatim from these bytes),
**DERIVABLE** (follows from these bytes or the pinned tracked code with no
material discretion), or **JUDGMENT** (frozen reconstruction choice, recorded
as such). The consolidated ledger is Appendix P of the rev-5 spec. In
particular, verify the R-1 reversal: the grade-precedence order frozen in
rev 5 (`v54_grade`: B-first incl. `or gate==CONFIRM`, then unknown→C) against
`v54_grade` in `v54_rules.py` and the handoff brief's "and/or market CONFIRM".

These bundle copies are **audit evidence**, not implementation sources for
the rebuild — the rebuild is specified solely by the rev-5 frozen spec.
