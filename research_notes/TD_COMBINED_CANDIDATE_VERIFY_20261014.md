# TD Combined Candidate — Verification Result

**Task:** QF-TD-COMBINED-CANDIDATE-VERIFY-20261014-08 r1 (ChatGPT assignment
from its 2026-10-14 02:13 EDT adjudication; auto-approved under Mike's
standing rule). Executed by Muse (subagent), 2026-10-14.
**Cap:** 45 minutes incl. at most one ≤10-min repair pass — used: ~25 min,
**no repair pass needed** (no failures to repair).
**Scope honored:** local/synthetic only — zero vendor calls, zero credits,
zero spend, no live screen, no merge to `main`, PR #8 and its branch
untouched, no production/frozen code changes. The live credit ledger
`research_notes/pilot_harness/credit_ledger.json` is byte-identical before
and after (sha256 `ce515aa6fd53b297b693762e4236b2ea203874641ce745e482ba76daf1a67c59`).

## Verdict: COMBINED CANDIDATE VERIFIED (offline)

The combined tree — Side B adapter/driver/manifest bytes from `f55b982`
(main) + Side A collector bytes from `f64d12f` (PR #8), byte-identical —
passes **all three suites (41/41 + 16/16 + 19/19)** and the full-chain
proof. No byte drift, no path conflicts requiring resolution in the
candidate. **Landing is NOT done here** and the one-credit live screen
remains separately gated; nothing in this result is a live-use
authorization or a feed/performance claim.

## 1. Candidate construction (immutable, isolated)

- Root: `/tmp/td_combined_candidate_20261014/` — outside the repo's
  tracked paths; `main`'s working tree was never modified.
- 33 files extracted byte-for-byte via `git show <commit>:<path>`:
  Side B = the -07 corrected adapter set (adapter, driver, suite, probe),
  the shared `pilot_harness` modules + live-ledger copy + R3 manifest,
  the V1 acquisition manifest/contract/prerequisites, and the pinned
  archival sources the collector verifies against. Side A = the complete
  `f64d12f` candidate directory (9 files).
- Every file's sha256 was checked twice: against its source commit blob
  and, where a pin exists in the -06/-07 records, against the expected
  pin. **Drift: 0.** Files were then set read-only (0444) and all runs
  executed with bytecode-writing disabled; a post-run re-hash of all 33
  files shows **zero drift and zero unexpected new files**
  (`post_run_verification.json`).
- One disclosure: the adapter suite's own tests resolve the pinned
  collector via `git show f64d12f:…` against the tree they run in. The
  candidate therefore carries a `.git` whose object store is an
  *alternates* pointer (read-only) to the source repo's objects — no
  refs copied, no candidate commits. The driver's default-path tests
  and the direct loader check below exercise the candidate's own
  extracted collector file, so the landed-bytes claim does not rest on
  the alternates mechanism.
- Overlap check: the shared `pilot_harness` files are byte-identical
  between `f55b982` and `f64d12f` (limiter `06ad383d…`, validate
  `1b83cdcd…`, verify `a0bd2e4c…`, construct_4h `d47e8df1…`, ledger
  `ce515aa6…`), so no Side A/Side B byte conflict exists on shared
  paths; Side A's directory is disjoint from Side B's, as -06 found.

## 2. Candidate manifest (full sha256 inventory)

| Side | Path | sha256 | Bytes |
|---|---|---|---|
| B (f55b982, main) | `research_notes/td_transport_adapter/driver.py` | `671f4d0ce25a76bc4967f1ca8cbb16fcda037f0e0ce71529c2aa385dce33fed1` | 9308 |
| B (f55b982, main) | `research_notes/td_transport_adapter/td_http_transport_adapter.py` | `ae8f4837b3d11a53990cfd56f207d5ec96c40b8fe4c1280f15fb08452cc43343` | 14226 |
| B (f55b982, main) | `research_notes/td_transport_adapter/test_transport_adapter.py` | `b7fa2dc922ac0395171bb25a033d2c78d1a53ea0d962f169eee142bf0cf8e1c9` | 56672 |
| B (f55b982, main) | `research_notes/td_transport_adapter/sentinel_probe.py` | `8464124554662ad14860c8d540dd3d04d0024456ba6f965dc1b98701f4a24d02` | 13614 |
| B (f55b982, main) | `research_notes/pilot_harness/construct_4h.py` | `d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd` | 11316 |
| B (f55b982, main) | `research_notes/pilot_harness/pilot_acquire.py` | `acf39bbd98f7174a4205019e754fc714ca420b4a7df43c815ea158a6fad67c59` | 27636 |
| B (f55b982, main) | `research_notes/pilot_harness/pilot_build.py` | `257d5bb99bcbae50442491b71429abb6b37b8c5cbcd1e4bf93b6010ad9e5a508` | 6312 |
| B (f55b982, main) | `research_notes/pilot_harness/rate_limiter.py` | `06ad383d856e62d126d1aae9edc7804e1b09471d87d9b280ec55a25aea0b8d64` | 14459 |
| B (f55b982, main) | `research_notes/pilot_harness/synthetic_data.py` | `b269db87fa444f343ec4ac09041540e5171ba3d330b53f422bcc5b84af2b15a7` | 7633 |
| B (f55b982, main) | `research_notes/pilot_harness/validate_input.py` | `1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58` | 20217 |
| B (f55b982, main) | `research_notes/pilot_harness/verify_sources.py` | `a0bd2e4cdce44be5d9fcc1d7c21046391d36c9bd366a959df03bf5d19c9a79e0` | 2670 |
| B (f55b982, main) | `research_notes/pilot_harness/warmup_math.py` | `df2219df8256ee859600d7bd34596caa55cfe0e925b8b2569bdd04adad38bf3e` | 2822 |
| B (f55b982, main) | `research_notes/pilot_harness/credit_ledger.json` | `ce515aa6fd53b297b693762e4236b2ea203874641ce745e482ba76daf1a67c59` | 95 |
| B (f55b982, main) | `research_notes/pilot_harness/request_manifest.json` | `a0a001b7458993ffb21c33a92a0fa9aec7a7126691e749a1a3dfb06afbb8b9f0` | 40632 |
| B (f55b982, main) | `research_notes/pilot_harness/requirements.txt` | `812c526fc0392dd81a4c6224e004eab169e973ec48a3103939f2f61b2ff85066` | 212 |
| B (f55b982, main) | `research_notes/td_acquisition_adapter_preflight_evidence_20261013/acquisition_manifest_v1.json` | `66a31e10aca1ca5f8af66139c4ff30a68cfef1c1138156eae103d8cf77e44f12` | 34013 |
| B (f55b982, main) | `research_notes/td_acquisition_adapter_preflight_evidence_20261013/adapter_contract.json` | `db6c44a2c95254fcc46d3c2717b682e00b33aa70fc563f8e86557dbca852a1f5` | 5683 |
| B (f55b982, main) | `research_notes/td_acquisition_adapter_preflight_evidence_20261013/prerequisites.json` | `038ccaf33547d6dae1f12ace073726300d92333184a0ba5de0dbab94cc0b5349` | 2533 |
| B (f55b982, main) | `research_notes/td_acquisition_adapter_preflight_evidence_20261013/SHA256_MANIFEST.txt` | `d465ef78bf02e2411f82d48a7467ffe292d8f9cf3bb86ad501faf1895bb773be` | 1330 |
| B (f55b982, main) | `research_notes/recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1/ARCHIVAL_INDEX.md` | `5d47c3a57e2cfaf1061c2c3bee184e9f47e0b4a46feb1db24a4036f68ad4f60f` | 2900 |
| B (f55b982, main) | `research_notes/recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1/pine_backtest.py` | `447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5` | 16996 |
| B (f55b982, main) | `research_notes/recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1/scanner_rules.py` | `7db282ddfc150c9e9aec7d8f1f10f439ce7e296da2d69da38f97ed8cbec70cac` | 22892 |
| B (f55b982, main) | `research_notes/recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1/pine_execution/c1_corrected_baseline_20261003.py` | `4568823cb8fe645a820c64bb4fac112fa7c90ac860bf626611467f7d94ea8f2b` | 16548 |
| B (f55b982, main) | `research_notes/recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1/pine_stack/pine_stack.py` | `839e4800624de253514095b5c007e8088afc0ab6c6ef45c86fb29a5956dfcefa` | 19161 |
| A (f64d12f, PR #8) | `research_notes/td_lifecycle_repair_candidate/td_min_collector.py` | `bd003c3cd5866172c04b0165d6ee60ec16be8487f28e90b4e6e1df046f8d489b` | 26443 |
| A (f64d12f, PR #8) | `research_notes/td_lifecycle_repair_candidate/test_lifecycle_repair.py` | `1421f52ee5bfb11b5f53128c59269e1bf114228046aaf0b3676c1636652a03c4` | 9788 |
| A (f64d12f, PR #8) | `research_notes/td_lifecycle_repair_candidate/test_pinned_integration.py` | `f1f195170edc1c070d5ca682fe48ad4cd32bc54f5053072f1b3511a396865386` | 10724 |
| A (f64d12f, PR #8) | `research_notes/td_lifecycle_repair_candidate/integration_requirements.lock` | `08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068` | 206 |
| A (f64d12f, PR #8) | `research_notes/td_lifecycle_repair_candidate/integration_results.json` | `ba8000ec79354992882baf5bf346bb58d8af9da25bbb8993b9ddcd2c32d96f3c` | 2661 |
| A (f64d12f, PR #8) | `research_notes/td_lifecycle_repair_candidate/integration_test_output.txt` | `1b6693859f10b44f5d6b9a0684e6a4c5bb7c9c138b2eb26af6deb208ff5b3836` | 1841 |
| A (f64d12f, PR #8) | `research_notes/td_lifecycle_repair_candidate/test_output.txt` | `2ad14c15539015f607667753d973a904189977d59dc4ec385cb64bebe07bc370` | 2091 |
| A (f64d12f, PR #8) | `research_notes/td_lifecycle_repair_candidate/README.md` | `f441a0387c58961a446fe7e6367f24fd67697aa23b183730abcfc717dc50dbcb` | 4027 |
| A (f64d12f, PR #8) | `research_notes/td_lifecycle_repair_candidate/INTEGRATION_REVIEW_20261013.md` | `701809292a05151a36ca1f284de9ecaf982bfe14b0ff00e0eb4df2b277a34ce8` | 3885 |

Machine-readable copy: `td_combined_candidate_verify_evidence_20261014/candidate_manifest.json`
(sha256 `b3dcde39b93af26566f30a8e091ef959308ea6504b29033d52ffe691ed9462d8`).

## 3. Suite results (all run against the candidate tree)

Environment: isolated venv built from the candidate's own
`integration_requirements.lock` — pandas 2.2.3, numpy 1.26.4,
pandas_market_calendars 4.5.1, pytz 2024.2, python-dateutil 2.9.0,
exchange-calendars 4.13.2, tzdata 2026.5; Python 3.12.3.

| Suite | Target | Result | Evidence |
|---|---|---|---|
| Adapter suite (`test_transport_adapter.py`, f55b982 bytes) | 41/41 | **41/41 PASS** | `adapter_suite/results.json` sha256 `2731b191…`, `test_output.txt` sha256 `60792a5f…` |
| Pinned-integration suite (`test_pinned_integration.py`, f64d12f bytes) | 16/16 | **16/16 PASS** | `pinned_integration_suite/results.json` sha256 `8a093a43…`, `test_output.txt` sha256 `7789e80f…` |
| Collector's own suite (`test_lifecycle_repair.py`, f64d12f bytes) | 19/19 | **19/19 PASS** (`Ran 19 tests … OK`) | `collector_suite_stderr.txt` sha256 `fe1367d7…` (full unittest output); wrapper summary `collector_suite_results.json` sha256 `4fd8dbd9…` |

Reproducibility notes:

- The adapter suite's `results.json` is **byte-identical** to the -07
  accepted evidence (`2731b191…`), the pinned suite's `results.json` is
  byte-identical to the 2026-10-13 independent rerun (`8a093a43…`), and
  the probe output (§4) is byte-identical to -07's (`3f8afbfd…`) — the
  result formats carry no run-specific fields, so the combined tree
  reproduces the accepted evidence exactly, not approximately.
- The pinned suite's passed-test set is set-identical to the `f64d12f`
  author's, and its self-computed source manifest pins the candidate
  collector at `bd003c3c…`.
- The collector's own suite stubs its dependencies by design (lifecycle
  isolation, per its header); it is counted as the third suite exactly
  as tasked, not as integration proof — that role belongs to the other
  two suites.
- Suite stderr noise, disclosed: two `BrokenPipeError` traces from the
  adapter suite's own loopback servers (body-cap tests disconnect
  mid-response) and the known pandas keep-mask `UserWarning` at
  `construct_4h.py:171`. Both pre-date this task and appear in the
  accepted evidence pattern; neither affects any result.

## 4. Full-chain proof (vault surrogate → CONNECT proxy → collector)

**Dynamic (on the candidate, inside the 41/41 adapter suite):**

- `ProxyLevel.test_vault_surrogate_collector_round_trip_via_proxy_isolation`
  — the production vault binding (authd fetch stubbed to a fake
  surrogate, per the suite's design) drives `driver.build_collector` →
  adapter → local CONNECT proxy → local TLS target → collector:
  outcome COMPLETE; exactly one CONNECT, one proxy upstream dial, one
  adapter dial (the proxy only); the target saw the surrogate as the
  LAST parameter; the post-run byte-scan of every runtime artifact
  (state, receipts, lifecycle, ledger) contains no surrogate, no
  fixture key, and no `apikey` string.
- Dial-tripwire negatives, all PASS: proxy absent → `proxy_unavailable`
  with **zero dials of any kind**; proxy CONNECT refused (403) →
  `proxy_connect_failed`, adapter dialed only the proxy, target accepts
  unchanged; malformed/credentialed proxy configs → fail-closed, zero
  dials. There is no code path in the run that dialed the target
  directly with a surrogate.
- Raw-key path negatives, all PASS: `api_key=` kwarg → `TypeError`
  before any transport construction; raw string as `key_source` →
  `DriverError` before construction; vault failure → sanitized token
  only; non-surrogate vault value → refused at build level; invocation
  order pinned as `[vault_fetch, adapter_construct, collector_construct]`.

**Probe (on the candidate):** `sentinel_probe.py` re-run —
`surrogate_requests_route_via_connect_proxy: true`,
`fixture_key_requests_stay_direct: true`,
`direct_path_receives_substitution: false` (the -06 finding, historical
for the pre-correction path). Output byte-identical to -07's
(`sentinel_probe/sentinel_probe_results.json`, sha256 `3f8afbfd…`).

**Static byte-scan (candidate production sources; full output in
`post_run_verification.json`):**

- `driver.py`: the ONLY environment access in the file is
  `os.environ.get(TEST_FIXTURE_KEY_ENV)` inside the explicitly
  test-only `get_test_fixture_key`; the raw name `TWELVEDATA_API_KEY`
  never occurs; `build_collector` has no `api_key` parameter (regex
  over the signature: 0 hits); the `hsurr:` surrogate guard occurs at
  every key-acceptance point (5 hits).
- `td_http_transport_adapter.py`: no `socket.create_connection`, no
  `socket.socket` construction anywhere — the `socket` module appears
  only as an import and a `socket.timeout` exception class; all dialing
  is `http.client` (12 hits), with the surrogate branch constructing
  `HTTPSConnection` addressed to the proxy + `set_tunnel` (1 hit) after
  `getproxies` resolution (4 hits incl. docstring).
- `td_min_collector.py` and the harness modules: zero socket / http /
  environment hits — the collector's only built-in transport is the
  disabled one; every real request flows through the injected adapter
  transport.

## 5. Conflict register (C1–C5) — disposition on the candidate

- **C1 (PR #8 `mergeable=false` vs clean local simulation):**
  unchanged and out of scope here — the candidate was built from
  commit bytes, not from the PR, so its verification does not depend
  on GitHub's mergeability state. The -06/-07 recommendation
  (cherry-pick `411457d` + `f64d12f`, or merge if the state clears)
  stands for the separately-authorized landing step.
- **C2 (dangling default collector path on `main`):** **RESOLVED in
  the candidate.** `driver.COLLECTOR_PATH` exists in the candidate
  tree and hashes to the pin `bd003c3c…`; a direct check —
  `driver.load_collector_module()` at its default path — loads the
  collector and passes the loader's internal limiter pin check with no
  `DriverError`. On `main` today the path remains absent (by design —
  nothing was landed), so `main`'s driver remains non-constructible
  until the landing step; the candidate proves the landed state works.
- **C3 (duplicate collector copies in evidence trees):** no action,
  as registered — the candidate contains exactly one collector (Side
  A's canonical path); the driver binds only that path and pin-checks
  its bytes. The evidence-tree copies were not imported into the
  candidate and are never on a load path.
- **C4 (manifest generations):** the candidate binds the V1 manifest
  (`TD-ACQUISITION-MANIFEST-V1-20261013`, sha256 `66a31e10…`) and the
  pinned adapter contract (`db6c44a2…`); the superseded R3
  `request_manifest.json` (`a0a001b7…`) is present only as the harness
  record it is on both source commits — identical bytes on both sides,
  no conflict.
- **C5 (ledger singularity):** verified — both sides reference the
  same persisted limiter state; all suites ran against scratch ledgers;
  the candidate's ledger copy and the live ledger both hash to
  `ce515aa6…` before and after (spent 0).

## 6. Hard stops honored

No vendor call, no credits, no spend, no live screen, no merge, no
PR #8/branch modification, no production or frozen-code change. All
network activity in the suites is loopback (127.0.0.1) servers the
suites start and stop themselves. The only writes outside `/tmp` are
this report and its evidence folder.

## 7. What remains (unchanged gates)

1. **Landing** of the combined tree (cherry-pick per C1, or PR merge)
   — a separate, separately-authorized step; this candidate is the
   verified source for it.
2. **The one-credit live screen** (-06 §4) — still the decisive
   on-the-wire substitution check; still gated.
3. Everything downstream (P4, acquisition, any strategy use) remains
   exactly as gated before this task.

**Status: combined candidate VERIFIED offline; live dispatch HOLD.**
