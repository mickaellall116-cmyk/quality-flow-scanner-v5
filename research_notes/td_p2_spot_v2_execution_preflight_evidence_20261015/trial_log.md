# Trial log — QF-TD-P2-SPOT-V2-EXECUTION-PREFLIGHT-20261015-04 r1

## Environment trial

- At task start, `/tmp/tdqual/venv` was absent.
- It was rebuilt from the exact f64d12f lock by download, hash verification, and `--no-index` installation.
- All 11 wheel hashes match the NL qualification package.
- The rebuilt pip freeze is identical to the qualified pip freeze.
- Interpreter: CPython 3.12.3.
- No package version was substituted.

## Initial main-driver trial

- The first main-mode execution stopped in the preflight driver at `write_once_collision_foreign_receipt`.
- Cause: the driver called `Collector.run()` without catching `CollectorError`.
- Collector behavior observed: refusal of unbound foreign evidence before dispatch (`legacy/unbound evidence requires review; no migration`), zero fake-transport calls, and the foreign receipt bytes untouched.
- Classification: preflight-driver defect, not a candidate failure.

## Repair

- One driver-only edit caught the `CollectorError` refusal path and recorded the refusal mechanism in the normalized result.
- No candidate, supplement, manifest, environment, or accepted-code bytes were changed.
- Repair time: approximately 3 minutes, within the single ≤10-minute allowance.

## Final trials

- Main mode: 22/22 cases PASS, run twice, byte-identical normalized result files.
- `vmismatch`: 1/1 PASS, run twice, byte-identical.
- `libabsent`: 1/1 PASS, run twice, byte-identical.
- `mechraise`: 1/1 PASS, run twice, byte-identical.
- Candidate failures in final trials: none.
