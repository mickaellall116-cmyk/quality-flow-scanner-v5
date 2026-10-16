# TD NL environment rebuild (QF-TD-NL-ENV-REBUILD-20261016-01 r1)

Date: 2026-10-16. Canonical spec: GitHub Issue #1 comment `6222883175`
(governs where it differs from any summary). Mode: one bounded
dependency-environment rebuild only. The ONLY network action was
package-index retrieval of the exact 11 locked wheels. Zero
market-data/vendor/model calls, zero SPT-08, zero data adoption, zero
backtests, zero live-state changes, zero spend. The standing Python
environment and the live V5.4 harness/state were not touched; the
install target was an isolated venv at `/tmp/tdqual/venv`.

## Verdict: NL_ENV_REBUILD_PASS

The exact NL-20261015 qualified environment was rebuilt from
hash-verified wheels and **all three existing validations pass
unchanged** — two of them byte-identical to their original
qualification records. Artifact hashes 11/11, freeze == lock exactly,
integration 16/16, Gate-N full pass, classifier matrix 28/28.

**Scope of this verdict, stated plainly (per spec): a PASS establishes
only a reproducible runnable calendar/classifier environment and
releases the next *offline* TD readiness step. It does not qualify
historical data, does not prove an edge, and changes no standing
state: TD P2 remains HOLD, P2 v1 UNMET, SPT-08 NOT ATTEMPTED, Yahoo
rev3 PARK, V5.4 PAUSED, Issue #9 no GO.**

## 1. Artifacts — hash-verified, fail closed

- Lock: byte copy of `integration_requirements_lock_f64d12f.txt`,
  sha256 `08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068`
  — the exact spec-pinned value.
- Download: `pip download` from the default index
  (`https://pypi.org/simple`, no index overrides) of exactly the 11
  locked versions; filenames + files.pythonhosted.org URLs + sha256
  per artifact in evidence `download_report.txt` (full verbose log:
  `pip_download_stdout.txt`).
- Verification: every wheel's sha256 compared against the preserved
  `wheel_hashes.txt` (NL-qual evidence, sha256 `2b7f0d7f…`) **before**
  install — **11/11 MATCH** (`wheel_hash_verification.txt`). No
  substitutions, no sdists, no source builds, no resolver drift.
- Persistent wheelhouse (spec step 3): the verified wheels are
  retained at `/home/hatch/workspace/td_nl_wheelhouse_20261016/wheels`
  (outside the public repo; no wheel binaries committed), permissions
  `drwxrws--- root:nogroup`, with its own `SHA256_MANIFEST.txt`;
  path/permissions/manifest also recorded in evidence
  `wheelhouse_manifest.txt`. A future rebuild can now install fully
  offline from this wheelhouse.

## 2. Environment — freeze equals lock

Isolated venv `/tmp/tdqual/venv` from `/usr/bin/python3`; install
`pip install --no-index --find-links <wheelhouse>` (install report:
`install_report.txt` + `pip_install_report.json`).

| Element | Value |
|---|---|
| Interpreter | CPython **3.12.3** (3.12.3, GCC 13.3.0) — same as qualified |
| OS | Ubuntu 24.04.5 LTS, kernel 7.0.0-39-generic |
| pip | 24.0 |
| `pip freeze` | **Exactly the 11 lock entries, nothing else** (`pip_freeze.txt`; programmatic set comparison: FREEZE_EQUALS_LOCK) |
| tzdata in force | stdlib `zoneinfo` TZPATH is the OS paths → **OS tzdata 2026c-0ubuntu0.24.04.1** serves zoneinfo (identical to the -01 record); pip `tzdata` 2026.5 installed per lock; mechanism session math runs on pytz 2024.2's bundled DB — both timezone sources captured in `env_probe.txt`, no mismatch |
| Mechanism | `validate_input.py` from the immutable `f64d12f` tree, sha256 `1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58` — exact |
| Source pins | all **8/8** author-pinned `source_sha256` entries of the `f64d12f` `integration_results.json` match the extracted tree (`git archive f64d12f` → `/tmp/tdqual/tree_f64d12f`) |

## 3. Validations — each run ONCE, network denied (`unshare -n`)

Network denial was enforced at the kernel level for every validation
run (net-namespace probe beforehand: outbound connect →
`Network is unreachable`); the classifier driver additionally disables
sockets in-process, as in its original qualification. Fake/preserved
bytes only.

1. **Gate-N fixtures FX-01..FX-05 + NC1–NC4** (runner
   `gate_n_fixtures.py` from the NL-qual evidence, unaltered):
   `fx01_fx04_all_pass: true`, `fx05_pass: true`, all four negative
   controls detected fail-closed. Output `fixture_results.json`
   sha256 `3cc0ae06…` — **byte-identical to the -01 qualification
   record** (`fixture_results_run1.json`, whose recorded hash is the
   same `3cc0ae06…`).
2. **`f64d12f` 16-check integration suite**
   (`test_pinned_integration.py --output-dir <fresh>`, unaltered):
   **16/16, `success: true`, exit 0**; the fresh `results.json` is
   JSON-equal to the -01 record (identical passed set, dependency
   block, source hashes; `vendor_calls=0`, `credits=0`,
   `dependency_stubs=false`). The one pre-disclosed pandas reindex
   UserWarning from the accepted constructor reproduced identically
   and remains disclosed, not repaired.
3. **`080a6ba` real-calendar classifier matrix** (driver
   `run_nlqual_matrix.py` from the -02 evidence, unaltered; candidate
   collector from the `ab254c3` tree at
   `~/workspace/pf06_scratch/base_wt`, sha256 `b683d277…` exact;
   supplement candidate `9c712330…`; preserved 180-byte REQ-SPT-07
   body `3339c341…`; SPOT8 manifest `ddff040f…`): pristine mode
   **28/28 PASS** — output `matrix_results.json` **byte-identical to
   the -02 qualification run1 record**. The three N10 throwaway-process
   controls (library version drift / library import blocked /
   mechanism raises) each HOLD as designed, each output
   **byte-identical to its -02 run1 record**.

## 4. Attempts, failures, repair accounting

One driver-level failure, preserved verbatim
(`pip_download_attempt1_stdout.txt`): the first download invocation
used `--report`, which pip 24.0's `download` subcommand does not
support (exit 2, zero wheels fetched, zero side effects). The single
allowed repair was used for exactly this: drop `--report`, add `-v`
for URL capture — **~1 repair minute of the ≤10 allowance**; no
environment, candidate, lock, supplement, mechanism or fixture bytes
changed. Every subsequent step passed on its first attempt; every
validation ran exactly once (no reruns to check). Total elapsed from
dispatch (19:26:55Z) to final validation run (19:32:15Z): ≈6 minutes
of the ≤45 cap, plus write-up.

## 5. Evidence package

`research_notes/td_nl_env_rebuild_evidence_20261016/` — lock copy,
preflight hashes, download report + both download attempt logs,
wheel-hash verification, install report (text + JSON), pip freeze,
environment probe, wheelhouse manifest, attempt log, Gate-N results +
stdout, integration fresh outputs + stdout, classifier matrix + N10
outputs + stdouts, this memo's package `SHA256_MANIFEST.txt`.
Deliverables left uncommitted in the worktree for the parent to
commit/push/post.

— Muse
