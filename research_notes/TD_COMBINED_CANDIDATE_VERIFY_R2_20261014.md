# TD Combined Candidate — Verification Result R2 (Repair 1 of 1)

**Task:** QF-TD-COMBINED-CANDIDATE-VERIFY-20261014-08 r2 — repair of the
r1 gate failure (ChatGPT PARTIAL PASS on r1, 2026-10-14). Executed by
Muse (subagent), 2026-10-14.
**Scope honored:** local/synthetic only — zero vendor calls, zero
credits, zero spend, no live screen, no merge to `main`, PR #8 and its
branch untouched, no production/frozen code changes. The live credit
ledger `research_notes/pilot_harness/credit_ledger.json` is
byte-identical before and after (sha256
`ce515aa6fd53b297b693762e4236b2ea203874641ce745e482ba76daf1a67c59`).

## Verdict: GATE FAILURE REPAIRED — COMBINED CANDIDATE VERIFIED as a self-contained filesystem proof

The r1 candidate was a `/tmp` extraction assembled with `git show` and
carried a `.git` alternates pointer, so its runs did not prove the
combined tree stands on its own bytes. The r2 candidate is a **real
commit** on an isolated ref, exported with **`git archive`** (no
`.git`, no alternates), and **all three suites + the default-path
loader proof + the full-chain proof were executed inside that export
with `git` blocked** — a PATH shim that logs and exits 1 sat first in
PATH for every run, and its log is empty: **git was never invoked**.
Results reproduce r1 exactly: **41/41 + 16/16 + 19/19**, chain proof
passed, ledger untouched. **Landing is still NOT done** and the
one-credit live screen remains separately gated; nothing here is a
live-use authorization.

## 1. The isolated candidate commit

| Field | Value |
|---|---|
| Commit | `7ec0f0efce7d9ce668233bf8ee55d7503ec47c0a` |
| Tree | `51e5f90e9d1f50dd874bb6f0450e961747cb6962` |
| Parent | `f55b982a51ad683020099259c105841345b2f3e5` (single parent — a plain child of the Side B commit, no merge) |
| Ref | `refs/heads/td-combined-candidate-20261014` on origin (verified via `git ls-remote`) |
| Construction | Separate git worktree under `/tmp`; `git checkout f64d12f -- research_notes/td_lifecycle_repair_candidate/` onto `f55b982`; main worktree and the hourly harness never touched |
| Diff vs `f55b982` | **9 files changed, 1070 insertions(+), 0 deletions** — all additions under `research_notes/td_lifecycle_repair_candidate/` |

Added files — sha256 of each, byte-identical to its `f64d12f` blob
(verified in the worktree before commit; the collector re-verified in
the export):

| Path | sha256 |
|---|---|
| `research_notes/td_lifecycle_repair_candidate/td_min_collector.py` | `bd003c3cd5866172c04b0165d6ee60ec16be8487f28e90b4e6e1df046f8d489b` |
| `research_notes/td_lifecycle_repair_candidate/test_lifecycle_repair.py` | `1421f52ee5bfb11b5f53128c59269e1bf114228046aaf0b3676c1636652a03c4` |
| `research_notes/td_lifecycle_repair_candidate/test_pinned_integration.py` | `f1f195170edc1c070d5ca682fe48ad4cd32bc54f5053072f1b3511a396865386` |
| `research_notes/td_lifecycle_repair_candidate/integration_requirements.lock` | `08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068` |
| `research_notes/td_lifecycle_repair_candidate/integration_results.json` | `ba8000ec79354992882baf5bf346bb58d8af9da25bbb8993b9ddcd2c32d96f3c` |
| `research_notes/td_lifecycle_repair_candidate/integration_test_output.txt` | `1b6693859f10b44f5d6b9a0684e6a4c5bb7c9c138b2eb26af6deb208ff5b3836` |
| `research_notes/td_lifecycle_repair_candidate/test_output.txt` | `2ad14c15539015f607667753d973a904189977d59dc4ec385cb64bebe07bc370` |
| `research_notes/td_lifecycle_repair_candidate/README.md` | `f441a0387c58961a446fe7e6367f24fd67697aa23b183730abcfc717dc50dbcb` |
| `research_notes/td_lifecycle_repair_candidate/INTEGRATION_REVIEW_20261013.md` | `701809292a05151a36ca1f284de9ecaf982bfe14b0ff00e0eb4df2b277a34ce8` |

All nine match the r1 §2 Side A pins exactly. Side B production bytes
are inherited unchanged from `f55b982` (driver `671f4d0c…`, adapter
`ae8f4837…`, suite `b7fa2dc9…` in the commit). Machine-readable copy:
`td_combined_candidate_verify_r2_evidence_20261014/candidate_manifest.json`.

## 2. Export self-containment proof

- `git archive 7ec0f0e… | tar -x` into `/tmp/td_combined_candidate_r2_export`.
- Export file count **659** = commit tree entry count **659**.
- `find` for `.git` / `alternates` in the export: **0 hits**. No
  object store, no refs, no alternates pointer — the exact defect that
  failed r1 is structurally absent.
- Exported collector sha256 `bd003c3c…` ✓; exported ledger copy
  `ce515aa6…` ✓.
- Every run below executed with the git-blocking PATH shim described
  in the verdict; the shim's invocation log after all runs is **empty**
  (`export_verification.json`).

## 3. Suite results (exported tree only)

Environment: fresh venv built from the exported tree's own
`integration_requirements.lock` — pandas 2.2.3, numpy 1.26.4,
pandas_market_calendars 4.5.1, pytz 2024.2, python-dateutil 2.9.0,
exchange-calendars 4.13.2, tzdata 2026.5; Python 3.12.3 (identical pins
to r1). `PYTHONDONTWRITEBYTECODE=1` throughout; all suite outputs were
directed outside the export.

| Suite | Target | Result | Evidence |
|---|---|---|---|
| Adapter suite (`test_transport_adapter.py`, export copy w/ §5 patch) | 41/41 | **41/41 PASS** (exit 0) | `adapter_suite/results.json`, `adapter_suite/test_output.txt` |
| Pinned-integration suite (`test_pinned_integration.py`, pristine) | 16/16 | **16/16 PASS** (exit 0) | `pinned_integration_suite/results.json`, `test_output.txt` |
| Collector's own suite (`test_lifecycle_repair.py`, pristine) | 19/19 | **19/19 PASS** (`Ran 19 tests … OK`) | `collector_suite_stderr.txt` (full unittest output), `collector_suite_results.json` |

Reproducibility vs r1:

- Pinned suite's passed-test set is **identical** to r1's, and its
  self-computed source manifest pins the **exported** collector at
  `bd003c3c…` — the suite hashed the export's own files, not a repo's.
- Adapter suite production source hashes in its `results.json` are
  identical to r1 (adapter `ae8f4837…`, driver `671f4d0c…`); the only
  difference from r1's `results.json` is the test file's own hash,
  which is the disclosed §5 patch (`972fbb5c…` vs `b7fa2dc9…`).
- Probe (§4) output is **byte-identical** to r1/-07 (`3f8afbfd…`).
- Known suite noise, same as r1: the pandas keep-mask `UserWarning`
  at `construct_4h.py:171`. No result is affected.

## 4. Default-path + full-chain proof (exported tree, no git)

**Default path (C2, re-proven standalone):**
`driver.load_collector_module()` called with **no argument** in the
export resolved the default `COLLECTOR_PATH` to the export's own
`research_notes/td_lifecycle_repair_candidate/td_min_collector.py`,
verified its sha256 against `drv.COLLECTOR_SHA256` (`bd003c3c…`), and
loaded it cleanly through the loader's internal limiter pin check
(`default_path_proof.json`).

**Full chain (inside the 41/41 adapter suite, on the export):**

- `ProxyLevel.test_vault_surrogate_collector_round_trip_via_proxy_isolation`
  **PASS** — production vault binding (authd fetch stubbed to a fake
  surrogate, per suite design) → `driver.build_collector` → adapter →
  local CONNECT proxy → local TLS target → collector: outcome
  COMPLETE; exactly one CONNECT, one proxy upstream dial, one adapter
  dial (the proxy only); surrogate delivered as the LAST parameter;
  post-run byte-scan of every runtime artifact contains no surrogate,
  no fixture key, no `apikey` string.
- All ProxyLevel fail-closed negatives PASS: proxy absent →
  `proxy_unavailable`, zero dials; CONNECT refused → zero direct
  target connections; malformed/credentialed proxy → fail-closed,
  zero dials; blackhole → single CONNECT, no retry; TLS failure after
  tunnel surfaces correctly.
- `BindingLevel.test_vault_sourced_round_trip_and_secret_isolation`
  and `CollectorLevel.test_full_synthetic_round_trip_success` PASS.
- Raw-key negatives (DispatchGateLevel) PASS: `api_key=` kwarg →
  `TypeError` before transport construction; raw-string `key_source`
  → `DriverError`; invocation order pinned
  `[vault_fetch, adapter_construct, collector_construct]`.

**Probe (export):** `sentinel_probe.py` —
`surrogate_requests_route_via_connect_proxy: true`,
`fixture_key_requests_stay_direct: true`,
`direct_path_receives_substitution: false`; output byte-identical to
-07/r1 (`sentinel_probe/sentinel_probe_results.json`, sha256
`3f8afbfd…`).

## 5. Test-only patch disclosure (the one deviation, export copy only)

The adapter suite's pristine bytes resolve the pinned collector via
`git show f64d12f:…` at four sites — impossible in a self-contained
export, and exactly the dependency this repair exists to eliminate.
Per the task spec, **only the export copy** of
`test_transport_adapter.py` was patched:

- sha256 before: `b7fa2dc922ac0395171bb25a033d2c78d1a53ea0d962f169eee142bf0cf8e1c9`
  (the `f55b982` pin — the candidate commit carries these exact bytes)
- sha256 after: `972fbb5c04e9694096b9465eb63efaae832a7c19b0d43eb70f6604337c4e7a9d`
- Change: at the 4 fetch sites (CollectorLevel.setUp, BindingLevel
  vault round-trip, DispatchGateLevel.setUp, ProxyLevel vault
  round-trip), `raw = subprocess.run(["git", "-C", str(REPO), "show",
  f"{COLLECTOR_COMMIT}:{COLLECTOR_GIT_PATH}"], …).stdout` →
  `raw = drv.COLLECTOR_PATH.read_bytes()`. Each site is followed by
  the **unchanged** assert `hashlib.sha256(raw).hexdigest() ==
  drv.COLLECTOR_SHA256`, so the pin check still gates every use — the
  patch changes where the bytes come from (the export's own default
  collector path), never what is accepted.
- Full unified diff: `test_only_patch.diff`; machine record:
  `test_only_patch.json`.
- **No production file was modified anywhere** — not in the candidate
  commit, not in the export (driver `671f4d0c…`, adapter `ae8f4837…`,
  collector `bd003c3c…` all at pin, confirmed by the suites' own
  source manifests and the post-run hash check).

## 6. Post-run verification

- Export immutability: `sha256sum -c` against the 659-file pre-run
  baseline shows **exactly one** mismatch — the §5-patched test file
  (baseline was snapshotted before patching). All other 658 files
  byte-identical; export file count unchanged; zero new files in the
  export (`post_run_verification.json`; baseline in
  `export_pre_run_hashes.txt`).
- Live ledger: `ce515aa6…` before **and** after (spent 0).
- `main` untouched: HEAD `60cc5f7` before and after; the candidate
  exists only on `refs/heads/td-combined-candidate-20261014`.
- PR #8 untouched; no vendor calls, credits, or spend.

## 7. Conflict register (unchanged from r1, C2 re-proven)

- **C1** (PR #8 `mergeable=false` vs clean local simulation):
  unchanged, out of scope — the candidate is a standalone commit on
  its own ref; the landing step (cherry-pick per -06/-07, or this
  candidate commit itself as the landing source) remains separate.
- **C2** (dangling default collector path on `main`): **resolved in
  the candidate and now proven from a self-contained export** — §4.
  On `main` the path remains absent by design until landing.
- **C3 / C4**: no action, as registered — exactly one collector in
  the candidate, at the canonical path; V1 manifest bound.
- **C5** (ledger singularity): verified — live ledger byte-identical,
  all suites ran against scratch ledgers.

## 8. What remains (unchanged gates)

1. **Landing** of the combined tree — separate, separately-authorized
   step; candidate commit `7ec0f0e` on
   `td-combined-candidate-20261014` is now the verified,
   self-contained source for it.
2. **The one-credit live screen** (-06 §4) — still the decisive
   on-the-wire substitution check; still gated.
3. Everything downstream (P4, acquisition, any strategy use) remains
   exactly as gated before this task.

**Status: combined candidate VERIFIED (self-contained); live dispatch HOLD.**
