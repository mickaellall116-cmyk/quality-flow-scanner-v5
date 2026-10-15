# QF-YAHOO-CAPTURE-EXECUTOR-PREFLIGHT-20261015-09 r2 — FINAL AMENDMENT

**Verdict: `CAPTURE_EXECUTOR_PREFLIGHT_PASS`** (preflight scope only;
authorizes no Yahoo call, no capture execution, no publication).

Spec: GitHub Issue #1 comment `6199809645` (final in-revision amendment
to r2; not r3). ChatGPT closed r2's three defects but held the route
because a post-completion mutation could bypass publication: the
`ALREADY_COMPLETE` branch did not reject extra/unlisted files, and
`publish_capture()` enumerated directories without validating the
archive manifest or the exact completed object set.

## The delta (only what the amendment authorized)

`execute_capture.py` gains one strict gate,
`validate_complete_archive(cap_dir, capture_id, entries)`, now used by
BOTH the `ALREADY_COMPLETE` restart branch and `publish_capture()`:

- `INCOMPLETE_HOLD.json` present → `HOLD:INCOMPLETE_MARKER`.
- Exact filesystem object set via `verify_object_set`: 52 raw + 52
  actions + 52 metadata files, no extra/temp/unlisted object anywhere
  in the capture directory → `HOLD:OBJECT_SET`.
- Strict `SHA256SUMS`: every line must be `<64 lowercase hex>  <rel>`;
  exactly the 156 expected unique paths, no duplicate, conflicting or
  malformed lines; the parsed map must equal the byte-verified file
  hashes → `HOLD:SUMS_INVALID`.
- Strict `manifest.json`: status `COMPLETE`, exact capture ID, 52
  symbols, `capture_manifest_sha256` equal to the frozen
  `EXPECTED_MANIFEST_SHA256`, and `files` mapping exactly equal to the
  validated sums → `HOLD:ARCHIVE_MANIFEST_INVALID`.
- `publish_capture()` resolves the frozen entries and calls the
  validator BEFORE the first remote operation (before
  `full_name()`/`visibility()`/`has_prefix()`), then uploads exactly
  the validated 156 objects plus `SHA256SUMS` and `manifest.json` —
  directory enumeration is gone.

## Adversarial fixtures (new file `run_executor_fixture_r2_amendment.py`)

15/15 checks, run twice, byte-identical result files:

- A-prior: the r2 suite re-run twice as a subprocess — 32/32 prior
  checks preserved and passing, result files byte-identical.
- A1/A2: extra object / temp leftover added AFTER completion →
  restart returns `INCOMPLETE_HOLD` (`HOLD:OBJECT_SET`), zero
  transport calls. (This is the exact bypass that held r2.)
- A3: publication attempted on an extra-object archive →
  `HOLD:OBJECT_SET`, zero uploads.
- A4/A4b: duplicate `SHA256SUMS` line → publish `HOLD:SUMS_INVALID`
  (zero uploads) and restart `INCOMPLETE_HOLD` with the same code.
- A5: conflicting sums line (same path, different valid hash) →
  `HOLD:SUMS_INVALID`, zero uploads.
- A6: malformed sums line (non-hex hash) → `HOLD:SUMS_INVALID`, zero
  uploads.
- A7/A8/A9: manifest capture-ID drift / files-mapping drift /
  frozen-hash drift → `HOLD:ARCHIVE_MANIFEST_INVALID`, zero uploads.
- A10/A10b: retained `INCOMPLETE_HOLD.json` on a completed archive →
  publish `HOLD:INCOMPLETE_MARKER` (zero uploads); restart
  `INCOMPLETE_HOLD` with the same code.
- A11: untouched completed archive → restart `ALREADY_COMPLETE`
  (156 files verified); publish `PUBLISHED_FAKE`, 158 objects, and the
  uploaded path set is EXACTLY the validated 156 + `SHA256SUMS` +
  `manifest.json`.

## Minutes (stated precisely)

- Spec fetched: 2026-10-15T18:57:42Z (VM clock).
- Code repair (the three surgical edits: validator added,
  `ALREADY_COMPLETE` rewired, `publish_capture` rewired): complete by
  ~19:00:10Z — **≈2.5 repair minutes**, inside the remaining 3-minute
  cumulative repair allowance.
- Verification (fixture written, run twice, twins byte-identical):
  complete 19:02:27Z; package manifest regenerated and verified
  18/18 at 19:03:22Z. Total elapsed spec-fetch → final verification
  ≈5.7 minutes. No earlier repair in
  this revision exceeded its allowance; cumulative r2 repair report
  stands as previously accepted, plus ≈2.5 minutes here.

## Hashes

- `execute_capture.py`: `8fe97abd0c081bf0c4269c412eb8f4e7e9f767b29a1ada362b36e4d2da16b22c`
- `run_executor_fixture_r2_amendment.py`: `189b2859075d63fa54aac6df8eaf0f3973c22473b7faa90333632d2cdaf64f95`
- `executor_fixture_results_r2_amendment.json` (+ byte-identical
  `_run1` twin): `99143581788827329e648472bb34e56cc8a8784efe7a00120df157b35a860b83`
- `executor_fixture_results_r2.json` (regenerated against the amended
  executor; + byte-identical `_run1` twin): `d80fda7793191eb4610920961a4e9ba35d03fd33622924d0fbae2ba8da44974d`
- Full package: `yahoo_clean_capture_preflight_20261015/SHA256_MANIFEST.txt`
  (regenerated over the whole package, verified after generation).

## Scope confirmation

Offline/local only. Zero Yahoo/vendor/API/model calls (the only
network fetch was the spec comment itself), zero downloads, zero
installs, zero spend, zero capture execution, zero publication (fake
local remote only), zero GitHub writes, zero holdout access, zero
live-state or production changes. Sockets were denied before any code
ran in both fixtures. Deliverables are uncommitted in the worktree.
