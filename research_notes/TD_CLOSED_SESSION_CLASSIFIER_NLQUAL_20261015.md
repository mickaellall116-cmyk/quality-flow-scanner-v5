# TD closed-session classifier — NL-20261015 qualification (QF-TD-CLOSED-SESSION-CLASSIFIER-NLQUAL-20261015-02 r1)

**Verdict: NL_CLASSIFIER_PASS** (synthetic/offline qualification only — see scope).

Spec: GitHub Issue #1 comment `6183716994` (governs where it differs from
any summary). Candidate under test, byte-immutable throughout:
`ab254c3458697dd450356146abcf4ad4f75ecef4` (branch
`td-closed-session-classifier-20261014`), collector
`research_notes/td_lifecycle_repair_candidate/td_min_collector.py`
sha256 `b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c`.
Zero candidate bytes were modified; the -17 logic was not touched to make
any proof pass.

## Environment actually used

The qualified NL-20261015 disposable venv at `/tmp/tdqual/venv` was still
present and was used **as-is (not rebuilt)**. Verified in place before any
run: CPython 3.12.3; `pip freeze` byte-equal in content to the exact
`f64d12f` lock (11 packages, incl. `pandas_market_calendars==4.5.1`,
`pandas==2.2.3`, `tzdata==2026.5`); lock file sha256
`08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068`;
mechanism `research_notes/pilot_harness/validate_input.py` sha256
`1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58`
(cross-checked identical in the candidate worktree and the qual tree).
Freeze + baseline hashes: evidence `nl_env_freeze.txt`,
`baseline_hashes.txt`. Network was disabled in-process for every proof run
(socket connect/getaddrinfo patched to raise); transport was fake in all runs.

## Supplement candidate (the versioned re-pin)

`p2_spot_supplement_v2_nl20261015_candidate.json` (evidence dir) sha256
`9c71233003771d66cf81e99ae01a410ba8943aedfcce8a8c6411dfb51edacd32`.
Content-identical to the -17 shipped supplement
(`p2_spot_supplement_v2.json` @ ab254c3) in `entries`,
`base_manifest_digest` (`748ca957…`), class and lifecycle event; the
calendar block is re-pinned from the incorrect CP1-derived `5.5.0` to
NL-20261015 (`4.5.1`, f64d12f lock `08b38cfa…`, mechanism `1b83cdcd…`,
qualification commit `7de7950`). -11 remains UNKNOWN; P2 v1 remains UNMET.

## Results — real-calendar matrix (driver `run_nlqual_matrix.py`)

28/28 cases PASS, run twice, **byte-identical machine outputs**
(`matrix_results_run1.json` = `matrix_results_run2.json`). The matrix
re-expresses the -17 F1/F2 + N1–N12 + supplementary fixtures against the
REAL `pandas_market_calendars` 4.5.1 and REAL
`validate_input.xnys_schedule` (no calendar stubbing anywhere on a positive
path; real `RollingCreditLimiter`; follow-request bodies generated from the
real calendar's expected 1H starts and accepted by the REAL validator):

- **Provenance**: the body under test is the actual preserved live evidence
  `research_notes/twelve_data_stage0/snapshots/acquisition_state_spot8/receipts/REQ-SPT-07.rejected.bin`
  — 180 bytes, sha256 `3339c34154648c0ea4ddb9bd553e5274d390f953552518ad957d79704b7d5d50` — loaded from disk, not reconstructed.
- **Calendar sanity**: real mechanism returns closed for 2026-07-03/04/05
  and open for 2026-07-06; library version reads exactly `4.5.1`.
- **F1 / F2**: classify as `EXPECTED_EMPTY_CLOSED_SESSION`, raw bytes
  preserved write-once (`.closed_day.bin` byte-equal, event sha = preserved
  sha), no receipt/completion events for the request, credit reservation
  stands spent, run **advances** to the following stubbed request.
- **N1–N9, N11, N12**: every negative HOLDs and terminates the batch
  (mixed window, one-char message mutation, code/status retype/alter/drop,
  HTTP-200 empty values, HTTP-200 exact body, auth message, 401/403/429/500,
  unparseable body, preregistration absent / expected_bars ≠ 0, values field
  present, manifest- and request-digest mismatch).
- **N10** (three separate throwaway-process controls, each run twice,
  deterministic): library version drifted to 9.9.9 → HOLD; library import
  blocked → HOLD; mechanism made to raise → HOLD.
- **S1 / S2 / S3**: meta-symbol mismatch HOLDs; no-supplement preserves the
  base HOLD behavior; restart never redispatches an evidenced request
  (0 calls, evidenced count reused).

## Results — real-process proofs (spec point 3)

- **REAL07**: the actual REQ-SPT-07 request object from the preserved V2
  SPOT8 manifest (file sha256 `ddff040f…`, matching the supplement's recorded
  binding) + the preserved 180-byte live body classify under the real
  calendar; its canonical digest equals the preregistered
  `a259901ec57a8556228c2a6b95299c360102cc98edc62204ae539dc53a4c5edb`;
  the run advances to the following stubbed request.
- **ELIG08 (SPT-08 eligibility, NO dispatch)**: full-manifest canonical
  digest equals the supplement's `748ca957…`; REQ-SPT-08 canonical digest
  equals the preregistered `f547d8fec7882fa121feb966b33fde000b25c4ae0eb822a6b5a503f4a3651a97`
  in both the shipped and candidate supplements; a direct
  `_classify_closed_session` precondition evaluation on preserved inputs
  (exact-schema QQQ body, synthetic) returns a calendar proof with
  `per_date {"2026-07-03": "closed"}` and `library_version "4.5.1"`, while
  the meta-mismatched control returns None. The transport was wired to raise
  on any invocation and recorded **zero calls**: SPT-08 was not dispatched
  and remains **NOT ATTEMPTED**.
- No receipt/completion/identity/construction claim is emitted for the
  closed-day class in any positive case (asserted per case); credits remain
  accounted (reservations stand at 2/2 in classified runs).

## Regressions (spec point 4), each run twice in the same environment

- Pinned integration suite (`test_pinned_integration.py`, the f64d12f
  suite): **16/16 PASS**, both runs (`integration_results_run1/2.json`).
- Base lifecycle suite (`test_lifecycle_repair.py`): **19/19 OK**, both runs.
- Original -17 classifier suite (`test_closed_session_classifier.py`,
  stubbed-calendar logic reference, unchanged): **OK**, both runs — recorded
  for continuity only; the NLQUAL matrix above is the real-calendar proof.

## Trials, failures, repair accounting

No case failed in any executed run. **Repair minutes used against the
candidate: 0** — no candidate or environment repair was needed or made. One
authoring correction was made to this task's own proof driver before its
first execution (the eligibility proof initially passed a reduced manifest
to the Collector; corrected to the full preserved manifest so the
supplement binding conjunct is exercised genuinely) — disclosed for the
record; it touched no candidate, supplement, or environment bytes.

## Adoption packet

`P2_SPOT_V2_ADOPTION_PACKET_DRAFT.md` (evidence dir) — DRAFT ONLY: the
supplement re-pin as the sole substantive delta, merge-as-is candidate
code, rollback (supplement drop/revert ⇒ classifier fails closed to the
pre-existing HOLD path), and the remaining gates. **Not adopted, not
merged** by this task.

## Scope confirmation

Zero vendor/model/API calls, zero credits, zero spend, zero backtests,
zero live changes. SPT-08 not dispatched (NOT ATTEMPTED stands). Live V5.4
harness/state untouched. P2 remains HOLD; P2 v1 remains UNMET; this result
does not qualify Twelve Data as a feed and opens no performance record.
