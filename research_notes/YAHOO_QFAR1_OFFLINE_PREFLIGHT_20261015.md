# Yahoo QFAR1 Offline Preflight (-13 r1)

- Task: `QF-YAHOO-QFAR1-OFFLINE-PREFLIGHT-20261015-13 r1`; spec: GitHub Issue #1 comment `6205968339` (the -12 r3 final design adjudication).
- Governing design: `research_notes/YAHOO_SINGLE_BLOB_ARCHIVE_DESIGN_20261015.md` r3 (commit `d7dc58b`, sha256 `cd9ef36d…`), **as corrected by the adjudication in the spec comment** — the adjudicated arithmetic (§ below) supersedes r3 §0 wherever they conflict.
- Scope: isolated offline implementation + no-socket fake Git Data remote only. No reuse/import/edit of the parked -11 publisher or the parked executor. No network (spec fetch excepted), no authenticated GitHub calls, no archive writes to any real repo, no Yahoo/vendor/model calls, no downloads, no installs, no spend, no capture, no backtest, no holdout, no production/live changes. U-1 (live ~64 MiB blob probe) NOT in scope — remains HOLD.

## Verdict: `QFAR1_OFFLINE_PREFLIGHT_PASS`

Elapsed: spec fetched 2026-10-16T01:57:23Z; work completed inside the ≤60-minute cap. Repair minutes used: ~5 of the ≤10 allowance (three fixes after first failing runs: a pins-shape mismatch at the build self-check; the §7 re-fetch comparison corrected to the trailer semantics of `CONTAINER_SHA256`; the A-10 exact-ceiling fixture redistributed under the 32 MiB per-member guard). This PASS leaves U-1, rev.3 adoption, acquisition authority, data qualification and corrected performance on HOLD, exactly as the spec states.

## Adjudicated constants (asserted programmatically — hardcoding forbidden, drift = fail)

Derived from the internally pinned frozen rel set (frozen capture manifest sha256 `634c4541…`, 52 symbols → 156 payload rels + 2 bookkeeping = 158):

| Quantity | Adjudicated value | Programmatic derivation |
|---|---|---|
| Σ rel byte lengths (158) | 3,057 | computed |
| QFAR1 index | 9,693 | 158×42 + 3,057 |
| Fixed header / trailer | 16 / 32 | format constants |
| Non-member overhead | 9,741 | 16 + 9,693 + 32 |
| Shared ceiling (Σ 158 physical members) | 67,108,864 | design constant |
| Max container at ceiling | 67,118,605 | ceiling + 9,741 |
| Max base64 length | 89,491,476 | 4·⌈67,118,605/3⌉ |
| SHA256SUMS canonical length | 13,566 | 157×67 + 3,047 |
| Manifest template max (64-char ID, 8-digit lengths) | 18,598 | computed from template |
| Bookkeeping reserve | 32,164 | 18,598 + 13,566 |
| Capture-side payload budget | 67,076,700 | 67,108,864 − 32,164 |

Semantic correction (binding): the reserve guarantees a **completed** 156-payload capture cannot overflow when bookkeeping is added. It cannot refuse an oversized streaming response *before* the request is consumed — the attempt is consumed, the stream is cut off and held. The A-10 streaming case records attempt consumption honestly.

## Implementation

- Module: `research_notes/yahoo_qfar1_preflight_20261015/qfar1_publisher.py` (new, isolated; public surface: `publish`, `HoldError`).
- Driver: `research_notes/yahoo_qfar1_preflight_20261015/run_qfar1_fixture.py`.
- Read discipline: component-wise directory-fd walk (R-3 fallback — the spec-accepted U-2 implementation) with `O_NOFOLLOW` on **every** component + census `(dev, ino, size)` binding before/after each read and a final re-census; no path-string payload re-open after seal (upload reads the sealed container fd).
- Fake remote: in-process, no sockets; blob/tree/commit/ref Git Data semantics incl. fast-forward-only ref update, visibility gate, fault injection (substitution, response loss, ref movement, encoding lies).

## Results

- **63 case records, 63 PASS in run 1 and 63 PASS in run 2** (`fixture_results_run1.json` / `fixture_results_run2.json`, sha256 `e5a5c0a4…` each). The two runs materialized their trees independently (different creation order and mtimes) and the two results files are **byte-identical** (`cmp` clean; identical sha256).
- Per-case summary (full records in the results JSONs):
  - **A-01** determinism twin: identical container bytes, `CONTAINER_SHA256`, and blob id across independently materialized trees. Container length asserted byte-exact against the adjudicated formula (Σ + 9,741).
  - **A-02** (7 variants): symlink `raw/` before census, after census, leaf symlink swap, capture-root symlink, magic-link component → `HOLD:PATH_TYPE`; legitimate-directory swap → `HOLD:READ_DRIFT`; **real-process churn** (external swapper process replaced `raw/` with a symlink mid-read of a 6 MiB member) → HOLD. Zero remote writes in all variants. The mechanism exercised is the component-wise fd walk — every component opened `O_NOFOLLOW` from the pinned root fd, directory inodes census-pinned.
  - **A-03**: uppercase positives (`raw/NVDA.csv`, `raw/BTC-USD.csv`) build as members in every baseline; extra file, missing file, case-variant rel, frozen+variant pair → `HOLD:MEMBERSHIP`; capture IDs (lowercase, `--`, `/`, length 7, length 65) → `HOLD:ID_INVALID`.
  - **A-04**: member flip vs validation pins → `HOLD:MEMBER_DRIFT`; sealed-container payload/index/trailer flips → HOLD (trailer flip `HOLD:CONTAINER_FORMAT`; payload/index flips surface as trailer-first `HOLD:CONTAINER_FORMAT` in the parser — recorded as observed).
  - **A-05**: truncation at header/index/payload/trailer, one trailing garbage byte, overstated index length → `HOLD:CONTAINER_FORMAT`.
  - **A-06**: baseline publish establishes the parent; descendant-without-blob advance, ref deletion mid-protocol, first-publication creation race → `HOLD:REF_RACE`, winner state never overwritten.
  - **A-07**: crash after blob/tree/commit creation → restart `HOLD:ID_CONSUMED` (never a second commit); ref update applied with response lost → `HOLD:API`, restart completes by recording (`PUBLISHED_BY_RECORDING`, exactly one commit for the ID).
  - **A-08**: wrong blob id → `HOLD:BLOB_SUBSTITUTION`; tree entry naming another blob → `HOLD:TREE_MISMATCH`; altered commit message / extra parent → `HOLD:COMMIT_MISMATCH`; altered blob bytes on re-fetch (raw and JSON routes) → `HOLD:REFETCH_CONTAINER_HASH`.
  - **A-09**: public repo and wrong repo name → `HOLD:VISIBILITY` with zero objects created.
  - **A-10**: Σ physical == 67,108,864 seals with container length exactly 67,118,605; ceiling+1 → `HOLD:CEILING`; a single member at exactly the 32 MiB guard with total in range seals; streaming case records `attempts_consumed=1, cut_off=True` and HOLDs mid-stream (the adjudicated honest-consumption semantics); `derive_constants` asserts every adjudicated constant from the derived rel set on every invocation.
  - **A-11**: newline-wrapped base64 JSON verifies; encoding lie, raw-route JSON error body, invalid padding → `HOLD:ENCODING`.
  - **A-12**: duplicate `publish()` after success → verification-only `ALREADY_PUBLISHED_VERIFIED`, still exactly one commit for the ID.
  - **A-13**: manifest self-entry, manifest SHA256SUMS-entry, manifest omitting a payload → `HOLD:MANIFEST_SCOPE`; SHA256SUMS self-line (158) and missing manifest line (156) → `HOLD:SUMS_SCOPE`; scope-violating on-disk manifest at build → `HOLD:MANIFEST_SCOPE`. Scope checks run before hash comparisons in verification (§7 order).
  - **A-14**: W1 (preflight→intent) and W2 (intent→confirm) ref movement → `HOLD:PARENT_DRIFT` with **zero** publisher-created objects; W3 (post-confirm) → `HOLD:REF_RACE`, moved state intact.
- **Peak RSS**: suite driver process 156.92 MiB (run 1) / 157.06 MiB (run 2) — that figure is harness-dominated (the driver materializes payload bytes in memory and holds full container bytes for the tamper fixtures). Measured separately in an isolated process, the **publisher's own streaming build of a ceiling-size container (67,118,605 bytes) peaked at 19.19 MiB**, well under the -11 baseline of 121.73 MiB: construction streams spool→container in 1 MiB chunks and never holds the container in memory.
- **Unimplemented branch (disclosed)**: the step-4 upload assembles the base64 body in memory (bounded by the adjudicated maximum base64 length 89,491,476 at ceiling; exercised at ~350 KB in the protocol fixtures). A streaming base64 upload is not implemented. `openat2` is likewise not used — the shipped mechanism is the R-3 fd-walk fallback, which the spec accepts as the U-2 implementation.

## Candidate rev.3 capture-manifest amendment (candidate only — NOT adopted)

- `research_notes/yahoo_qfar1_preflight_20261015/capture_manifest_rev3_candidate.json`, sha256 `617f8610…`. Derived from the frozen manifest (`634c4541…`): `bytes_total` 536,870,912 → **67,108,864** with the definition string "sum of byte lengths of all 158 physical members (156 payloads + manifest.json + SHA256SUMS)", plus `bookkeeping_reserve_bytes = 32164` and `payload_budget_bytes = 67076700`. Parity with the publisher is by construction and by assertion: the publisher derives the same three numbers from the pinned rel set and fails on drift (A-10). The candidate is NOT adopted and authorizes no acquisition.

## Scope confirmation

Offline only. Zero Yahoo/vendor/model/API calls, zero downloads beyond the spec-comment fetch, zero installs, zero spend, zero authenticated GitHub operations, zero real publication (the only remote is the in-process fake), zero capture execution, zero backtests/holdout/production changes. Parked files verified byte-identical at completion: `execute_capture.py` sha256 `8fe97abd…` (never edited/imported/run), -11 `publish_snapshot.py` `1b50db56…` and `run_publish_fixture.py` `a89460d5…` (never edited or reused — the QFAR1 module is fresh code). U-1 was not probed and remains HOLD.
