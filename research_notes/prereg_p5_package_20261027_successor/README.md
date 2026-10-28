# P5 — Per-Fill Cost Configuration Package, SUCCESSOR (2026-10-27)

**Succession.** This package supersedes the original P5 package —
commit `bb90d72`, `research_notes/prereg_p5_package_20261027/`, config
SHA-256 `7690de07edc3af3eeb977e923c4d0b85e4576a01206705b4a2c30b8f443d69b9` —
as the current P5 staging deliverable. The predecessor is preserved on
record at that commit and remains the history of how P5 was first
produced; quote THIS package's manifest for the current validator and
fixture suite. The config hash is unchanged (see below), so the P5
completion evidence entering the freeze record is the same value under
both packages.

**Why this successor exists.** ChatGPT's preliminary review of the
original package (Slack #qualityflowscaner, thread on the P5 post TS
`1793147984.672939`, review posted 2026-10-27 20:45 ET) found one gap:
the validator enforced key sets at the top level, the parameter level,
and the predecessor block, but inside the nested **provenance** entries
it only checked for the presence of individual keys. A config whose
PINNED provenance entry carried extra keys, or whose PROPOSED entry
lacked its `derivation`, still validated — i.e. the block that records
which parameters are frozen-text-pinned and which are open proposals
was itself not schema-exact.

**Authorization.** Same scope as the original package: Mike approved
**P5 preparation only** (2026-10-27) — expressly no holdout access and
no performance run. This successor changes no parameter and authorizes
nothing by itself; the config cannot be used by any run until a future
per-tier G7 GO.

## What changed (validator + fixtures only)

1. `validate_p5_config.py` — provenance entries now carry **exact key
   sets**, enforced before any status/value check inside the entry:
   a PINNED entry is exactly `{status, citation}`; a PROPOSED entry is
   exactly `{status, requires_review, derivation}`. `citation` and
   `derivation` must be non-empty strings; `requires_review` must be
   exactly `true`. All other validation behavior (hash leg, top-level /
   parameter / predecessor key sets, PINNED values, PROPOSED
   consistency, cross-field arithmetic, fail-closed exits) is unchanged.
2. `test_p5_fixtures.py` — three new negative fixtures pin the
   tightening (12 → 15 checks): a PINNED entry with a spurious extra
   key; a PROPOSED entry missing `requires_review`; a PROPOSED entry
   missing `derivation`. Each tampered file is passed with its own
   correct hash, so rejection comes from schema validation, not the
   hash leg. The first and third **validate under the predecessor
   validator** — see the discrimination table in `FIXTURE_RESULTS.md`.
   All 12 predecessor fixtures pass with unchanged outcomes.

## What did NOT change

- **`per_fill_config.json` is byte-identical** to the predecessor:
  SHA-256 `7690de07edc3af3eeb977e923c4d0b85e4576a01206705b4a2c30b8f443d69b9`.
  No serialization change was forced — the committed config already
  carried exact provenance key sets; only the validator failed to
  enforce them. All 18 parameters, their values, and their
  PINNED (14) / PROPOSED (4) statuses are unchanged in substance and
  in bytes.
- **`generate_p5_config.py` is byte-identical** (SHA-256
  `bfb01ccccaa8c3c64f97fba06c72649c1eec3bba2c161ef1a7f125f119054f50`);
  generator output still reproduces the config hash exactly.

The four PROPOSED parameters remain open decisions for ChatGPT
adjudication and the G7 record, exactly as documented in the
predecessor README (sensitivity_per_fill_bps [2.0, 5.0],
adjustment_precedence, rounding_mode = none_full_precision,
min_cost_per_fill_applies = false). This successor proposes no change
to any of them.

## The artifact

| File | Role | SHA-256 |
|---|---|---|
| `per_fill_config.json` | The config (unchanged). The P5 completion-evidence hash. | `7690de07edc3af3eeb977e923c4d0b85e4576a01206705b4a2c30b8f443d69b9` |
| `generate_p5_config.py` | Deterministic generator (unchanged). Offline, stdlib only. | `bfb01ccccaa8c3c64f97fba06c72649c1eec3bba2c161ef1a7f125f119054f50` |
| `validate_p5_config.py` | Fail-closed validator/verifier (successor — exact nested provenance key sets). | see `SHA256_MANIFEST.txt` |
| `test_p5_fixtures.py` | Positive / negative / idempotence fixtures, 15 checks (successor — 3 new provenance key-set negatives). | see `SHA256_MANIFEST.txt` |
| `SHA256_MANIFEST.txt` | SHA-256 of every package file except the manifest itself. | — |

Verify: `python3 test_p5_fixtures.py` (expect `FIXTURES: 15/15 PASS`),
and `python3 validate_p5_config.py per_fill_config.json
--expected-sha256 7690de07edc3af3eeb977e923c4d0b85e4576a01206705b4a2c30b8f443d69b9`.
