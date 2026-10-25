# Actual-dependency integration — October 13, 2026

Candidate: af49bf4a65acca08876a4bd9823a945ca8aa3d17 (draft PR #8).
No collector or accepted dependency code was changed in this pass. The missing calendar dependency was installed in an isolated venv using the existing harness requirements. Transitive versions are captured in integration_requirements.lock. Source bytes were retrieved from the candidate immutable tree and verified against Git blob hashes before testing.

## Result

16/16 actual-dependency integration tests PASS. The full driver, assertion output and machine-readable results are committed alongside this report. No dependency stubs are used. Transport is synthetic fixtures only: zero vendor requests, zero credits, no credential access, no market-data processing or performance computation.

Checks cover actual archival-source verification, 1H regular/early-close completion, spring/fall DST session offsets, missing constituent rejection, holiday empty-frame validator behavior, native-4H structural diagnostics, crash after RECEIVED, changed request binding, actual persisted limiter restart/refusal/corruption, prerequisite refusal, isolated source tampering, malformed payload, separate-process lock contention, and validator-to-constructor exact partial-bin OHLCV [10,41,9,40,10]. Receipt reuse dispatches once and revalidates with the actual validator. Exact test names and source hashes are in integration_results.json.

## Reproduce from this checkout

Use Python 3.12 (tested 3.12; exact patch in results), an isolated venv, and install this directory's integration_requirements.lock. Then:

    python3 research_notes/td_lifecycle_repair_candidate/test_pinned_integration.py --output-dir /absolute/path/to/NEW-private-results

The output directory must NOT already exist. The driver refuses reuse instead of deleting evidence. It writes test_output.txt and results.json there; there are no fixed /tmp paths. Synthetic state stays in fresh temporary directories, no live credit ledger is reset or touched.

## Scoped decision

The missing actual-calendar/dependency demonstration is now supplied. This is a scoped integration PASS for the enumerated synthetic cases, not full P4/live-execution clearance. Original failed artifacts, prior partial package and their adverse findings remain unchanged. Candidate code remains on an unmerged research branch; vendor transport remains disabled.

## Remaining concrete gates before a sample pull

- A reviewer must verify this pinned driver/output, rather than accepting the author's pass claim alone.
- Pin one acquisition adapter's actual account/retention, sanitized timeout/error handling, shared live limiter path and exact ascending request/venue identity. The candidate has no HTTP client and the revised manifest is not yet supplied.
- Interpret collector COMPLETE as validated receipt completion only. Native-4H diagnostic completion says nothing about session coverage. The 1H validation check uses a declared start-label convention; it is not proof of vendor interval semantics.
- Retain samples privately under the active-account retention condition. Do not use held Tiingo inputs as the comparator.
- Compare timestamps, date-end inclusion, venue coverage, missing bars, adjustment basis and available historical depth. No unchanged-strategy baseline until these checks pass and dataset/code/cost/fill/validation splits are fixed.

One runtime warning was observed in the accepted constructor: pandas reindexes the keep-mask Series to the DataFrame index. Exact synthetic output remained correct; this is disclosed, not silently repaired here.

Priorities: qualify the data route and corrected baseline first. The idea pipeline remains secondary; already-authorized Phase A work is not canceled or promoted into an experiment runner. No new collector rewrite or strategy search was performed.
