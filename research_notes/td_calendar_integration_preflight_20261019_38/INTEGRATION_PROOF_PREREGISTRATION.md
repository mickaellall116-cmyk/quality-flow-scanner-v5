# -38 r1 — PREREGISTRATION: TD CALENDAR INTEGRATION PROOF v1 (separately versioned, synthetic-only)

**Status: PREREGISTERED ONLY — NOT EXECUTED, NOT AUTHORIZED BY THIS DOCUMENT.** Execution requires (a) resolution of blocker B1 (acquisition of the exact PMC 5.5.0 closure, itself a separately authorized network act) and (b) a separate explicit user GO naming this proof. This preregistration freezes the proof's shape so that any later run is judged against it, not tuned after the fact.

Proof identity: **TD-CALENDAR-INTEGRATION-PROOF v1**. It supersedes nothing; the -17 stub suite at `ab254c3` remains the standing offline evidence until this proof runs and is adjudicated.

## 1. Purpose and non-purpose

Purpose: prove, offline and synthetically, that the REAL pinned stack — `td_min_collector.py` classifier + `p2_spot_supplement_v2.json` pins + `validate_input.py::xnys_schedule` + a genuine `pandas_market_calendars==5.5.0` — classifies the EXPECTED_EMPTY_CLOSED_SESSION fixtures correctly with the calendar stubs removed, and fails closed under version/mechanism tampering.

Non-purpose: it qualifies no vendor data, no TD run, no manifest beyond the supplement's SPOT8 scope, no performance figure, and no production use. It does not adopt the classifier candidate.

## 2. Exact inputs (every byte hash-gated before any execution)

| Input | Source | sha256 |
|---|---|---|
| `td_min_collector.py` | commit `ab254c3458697dd450356146abcf4ad4f75ecef4` | `b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c` |
| `p2_spot_supplement_v2.json` | commit `ab254c3` | `cccd52260b2c80a7110559ed100111cf3634e7901daef2f883c6517b68255b31` |
| `validate_input.py` | commit `ab254c3` | `1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58` |
| `test_closed_session_classifier.py` (basis for the de-stubbed variant) | commit `ab254c3` | `3122bdfc5df432932395948216e4ec6cc50e438abe2518cd0a5984154c4d71d0` |
| De-stubbed test variant v1 (`test_calendar_integration_proof_v1.py`) | Created and hash-pinned **inside the future proof package before the run**; differs from the basis ONLY by removing the fake `pandas_market_calendars` module and the stub `xnys_schedule` (the `validate_input.__file__` pinning arrangement and all fixture bodies unchanged) | pinned in the proof package's manifest |
| `verify_sources.py`, `rate_limiter.py`, `construct_4h.py` | `pilot_harness` at the `ab254c3` tree | `a0bd2e4c…`, `06ad383d…`, `d47e8df1…` (full values in `integration_results.json` at `ab254c3`) |
| PMC 5.5.0 wheel + full transitive closure | **To be acquired under blocker B1's separate authorization** into a NEW wheelhouse; every wheel's sha256 recorded in a new lock file | lock file hash-pinned in the proof package before the run |
| Mechanism-probe expectation table (§4, family P) | This preregistration + committed primary-record evidence (-31/-32/-33 packages) | frozen below |

The existing 4.5.1 wheelhouse (`~/workspace/td_nl_wheelhouse_20261016`), the NL lock (`08b38cfa…`), and all committed bytes above are **inputs only** — none is modified by the proof.

## 3. Environment (built once, inside the proof's own authorization)

- Isolated venv built **only** from the new 5.5.0-closure wheelhouse, `--no-index`, every wheel hash verified against the new lock before install; network namespace disabled for the entire proof (the `unshare -n` pattern used by -35 r2), with deliberate network probes recorded as failed.
- Interpreter: CPython 3.12.3 (the standing NL-lock interpreter); its version string and executable sha256 recorded in the receipt. Any other interpreter = STOP.
- No other packages. The freeze output (`pip freeze` equivalent) is captured and hash-compared against the new lock; any extra/missing/differing member = STOP before any test runs.

## 4. Commands and check families (single attempt each; family accounting fixed here)

Run order is fixed: **hash gates → version probe → family P → families F/N/S (de-stubbed suite) → family V**. First failure anywhere stops the proof (§6).

- **Version probe (gate, not counted):** import `pandas_market_calendars`; print `__version__`. Must equal exactly `"5.5.0"`, else STOP (`VERSION_PIN_MISMATCH`).
- **Family P — mechanism probe (8 assertions)** against `validate_input.xnys_schedule` (real library). Expectations are calendar-schedule facts from already-committed primary-record evidence (no market data, no vendor timestamps):
  - P1 regular session: 2025-01-08 (Wed) → `(09:30, 16:00)` America/New_York.
  - P2 dated closure: 2025-01-09 (Carter National Day of Mourning, -32 recovery) → `None`.
  - P3 early close: 2024-11-29 → close `13:00` ET, open `09:30` ET.
  - P4 early close: 2025-07-03 → close `13:00` ET.
  - P5 weekend: 2025-01-11 (Sat) → `None`.
  - P6 DST spring boundary: 2025-03-10 (first session after spring-forward) → `(09:30, 16:00)` ET.
  - P7 DST fall boundary: 2025-11-03 (first session after fall-back) → `(09:30, 16:00)` ET.
  - P8 key resolution record: the probe logs what `mcal.get_calendar("XNYS")` returns (class + calendar name) — recorded as evidence for blocker B2; the assertion is only that the call succeeds and P1–P7 hold through it.
- **Family F — positives (2):** F1 single closed day, F2 multi-day all-closed, from the -17 suite, run through the de-stubbed variant with the REAL mechanism (fixture windows re-pointed to genuinely closed dates under the real calendar: the -17 stub dates 2026-07-03/04/05 are also real XNYS closures/weekend, so the fixture bodies carry over unchanged — the variant's diff is stub removal only). Both must produce `CLOSED_DAY_EVIDENCED` with a proof record whose `library_version == "5.5.0"` and `mechanism_module_sha256 == 1b83cdcd…`.
- **Family N — negatives (12):** N1–N12 from the -17 suite, unchanged; every one must terminate in the pre-existing HOLD path with no classification.
- **Family S — supplement/restart (3):** S1–S3 from the -17 suite, unchanged; same expectations.
- **Family V — version/mechanism integrity negatives (4), all on disposable copies inside the isolated environment (committed bytes never touched):**
  - V1 version perturbation: environment rebuilt with PMC 4.5.1 substituted → version probe must STOP the proof before any suite runs (expected outcome recorded as a PASS of the gate, in a separate pre-suite invocation whose only job is to be refused).
  - V2 mechanism tamper: one byte flipped in a COPY of `validate_input.py` → classifier conjunct (3) refuses (no classification on F1's body).
  - V3 calendar absent: PMC uninstalled from a copy of the environment → classification disabled, HOLD path (real-environment analogue of N10's second half).
  - V4 supplement tamper: one byte flipped in a COPY of the supplement (digest change) → no classification.

**Total preregistered checks: 29 (P8 + F2 + N12 + S3 + V4). Any other total, in either direction, = HOLD.**

## 5. Expected outputs

A single proof package (new directory, separately versioned) containing: the receipt JSON (environment freeze hash, interpreter identity, version-probe result, `get_calendar("XNYS")` resolution record, per-check PASS/FAIL by family with the fixed 29-count, zero vendor calls, zero credits, elapsed and repair minutes), the de-stubbed test variant + its sha256, the new 5.5.0 lock file, full stdout/stderr logs, and a SHA-256 manifest — committed and remote-verified. Verdict vocabulary for the future run: `INTEGRATION_PROOF_PASS` (29/29, all gates green) or `INTEGRATION_PROOF_HOLD__<failure key>`; no partial-pass vocabulary exists.

## 6. Fail-closed / stop rules

- Any input hash mismatch, any freeze/lock mismatch, any network probe success, version probe ≠ `"5.5.0"`, or interpreter mismatch → STOP before tests; return HOLD with evidence.
- First failing check stops the run. **No repairs, no retries, no second invocations inside the authorization** (the -35 r2 rule). Repair minutes are recorded and must be 0 for a PASS.
- The proof environment is torn down or left inert; nothing it builds is installed into any standing environment, and the standing TD pins (executor r4, adapter, Policy A, ledgers, manifests) are never read for writing or altered in any way.
- Any need to change an input, a fixture, an expectation, or a count voids this preregistration; a v2 preregistration and a fresh GO are required.
