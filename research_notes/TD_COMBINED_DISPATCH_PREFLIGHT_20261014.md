# TD Combined-Dispatch Preflight — Result

**Task:** QF-TD-COMBINED-DISPATCH-PREFLIGHT-20261014-06 r1 (ChatGPT assignment,
Issue #1 comment in the 2026-10-14 00:23 EDT review; auto-approved under
Mike's standing rule). Executed by Muse (subagent), 2026-10-14.
**Cap:** 45 minutes incl. one ≤10-min repair pass — used: one repair pass
(~4 min, a stub-seam defect in my own new test, no production-code repair).
**Scope honored:** no merge, no push to the PR branch, no vendor calls, no
credits, no spend. The live credit ledger
`research_notes/pilot_harness/credit_ledger.json` is byte-identical before
and after (sha256 `ce515aa6fd53b297b693762e4236b2ea203874641ce745e482ba76daf1a67c59`).

## Blocker dispositions (summary)

| # | Blocker | Disposition |
|---|---|---|
| 1 | Raw-key bypass in `build_collector` | **CLOSED** — parameter removed; 5 new gate proofs; all 27 prior proofs still pass (suite 32/32). |
| 2 | Sentinel compatibility of the direct http.client path | **EXACT BLOCKER** (below) — proven offline that the direct path does NOT receive substitution in this environment; not fixable within this task's no-live scope; one-step check defined for first live use. |
| 3 | Combined tree (collector + adapter/driver/manifest) unlanded; PR #8 `mergeable=false` | **PLAN PRODUCED** (below) — merge simulation is textually clean; the `mergeable=false` state is not reproduced and is attributable to GitHub-side state; semantic conflicts enumerated with resolutions. Live dispatch remains HOLD until blockers 2 and 3 land and the §4 screen is separately authorized. |

---

## 1. Raw-key bypass — CLOSED

**The path:** `driver.build_collector(..., api_key=None, ...)` — its own
docstring stated the resolution order "an explicit api_key wins". Any caller
could hand the combined dispatch path a raw key and it would be placed,
verbatim, into the adapter — bypassing the vault surrogate binding entirely.

**The correction** (`research_notes/td_transport_adapter/driver.py`,
sha256 `671f4d0ce25a76bc4967f1ca8cbb16fcda037f0e0ce71529c2aa385dce33fed1`,
was `be8c0bb7…`):

- The `api_key` parameter is **deleted**. There is no raw-key parameter.
- The only remaining key paths are (a) the production default — the vault
  surrogate binding `get_api_key()` — whose result `build_collector` now
  **re-asserts** is an `hsurr:*` surrogate before any adapter exists
  (defense in depth behind `get_api_key`'s own checks), and (b) an explicit
  `key_source` callable, the seam through which the proof suite injects the
  named test-fixture source (`get_test_fixture_key`).
- A non-callable `key_source` (e.g. a raw key string passed positionally)
  raises `DriverError("key_source_not_callable")` at function entry.

**Proofs** (new class `DispatchGateLevel`, suite now **32/32 PASS** —
all 27 pre-existing proofs intact; evidence:
`td_transport_adapter/test_evidence_combined_preflight_20261014/`):

1. `test_raw_key_kwarg_refused_before_transport` — `api_key="RAW-KEY-…"`
   raises `TypeError` (no such parameter); counting fakes over the adapter
   class and both `http.client` connection classes record **zero**
   constructions.
2. `test_raw_key_as_key_source_refused_before_transport` — raw string as
   `key_source` → `DriverError("key_source_not_callable")`, zero
   constructions.
3. `test_vault_failure_refused_before_transport` — helper failure (fake
   `dynamic_credentials` raising with key material in its text) surfaces
   only as `vault_credential_unavailable`; no transcript of the raw text;
   zero constructions.
4. `test_non_surrogate_refused_at_build_level` — a vault entry whose value
   is not an `hsurr:*` surrogate → `DriverError("vault_non_surrogate_value")`
   at the build level; zero constructions.
5. `test_invocation_order_vault_adapter_collector` — with instrumented
   components, the recorded invocation order is exactly
   `["vault_fetch", "adapter_construct", "collector_construct"]`, and the
   key the adapter receives is the surrogate.

Every refusal is therefore proven to occur **before any transport object is
created** — no adapter instance, no `http.client` connection, no socket.

The one call-site that passed `api_key=None` explicitly (the suite's
`CollectorLevel.build` helper) was updated to drop the dead argument; no
assertion in the 27 prior proofs changed.

---

## 2. Sentinel compatibility — EXACT BLOCKER

**Verdict: the adapter's direct `http.client` path does NOT receive the
Sentinel surrogate→real-key substitution in this environment.** This is
proven offline (`td_transport_adapter/sentinel_probe.py`, sha256
`59468511…`; results `test_evidence_combined_preflight_20261014/sentinel_probe_results.json`,
sha256 `6edc539e…`):

**How substitution is delivered here.** This sandbox's approved egress is an
explicit proxy: `http_proxy` / `https_proxy` / `HTTP_PROXY` / `HTTPS_PROXY` /
`ALL_PROXY` all point at `http://hatch-egress-proxy:3128`, and TLS trust for
that interception is the platform bundle `/run/hatch/egress-tls/ca-bundle.pem`
(`SSL_CERT_FILE`, `NODE_EXTRA_CA_CERTS`, `REQUESTS_CA_BUNDLE`,
`GIT_SSL_CAINFO` all reference it). A proxy-aware stdlib client discovers
exactly this channel: `urllib.request.getproxies()` returns
`https → http://hatch-egress-proxy:3128`. The helper's own documentation
states Sentinel replaces surrogates "on approved outbound requests"
(`dynamic_credentials.py`, module docstring) — i.e., on traffic that goes
through the approved egress path.

**The adapter never touches that channel.**
- Static: `td_http_transport_adapter.py` contains zero occurrences of
  "proxy", never calls `set_tunnel()`, and has no `os` import / no
  environment access of any kind (its sole "environ" substring is the
  docstring word "environment"). Python's `http.client` has no env-proxy
  behavior — tunneling happens only via an explicit `set_tunnel()` call.
- Dynamic (loopback only): with `http_proxy` pointed at a recording
  loopback proxy, the adapter delivered its request **directly** to a
  loopback target — proxy hits delta **0**, target hits delta **1** —
  while a proxy-aware control client using the same configuration was
  routed via the proxy (control reached: proxy, 1 hit).
- Dynamic (vendor construction, intercepted before any socket exists):
  for the vendor base URL the adapter constructs
  `HTTPSConnection(host="api.twelvedata.com", port=443, context=<TLS>)`
  directly; `set_tunnel` is never called. There is no proxy hop at which
  substitution could occur.
- TLS is **not** the blocker: `ssl.get_default_verify_paths().cafile` in
  this environment is `/run/hatch/egress-tls/ca-bundle.pem` (via
  `SSL_CERT_FILE`) and the adapter's default context has
  `CERT_REQUIRED` + hostname checking — i.e., if the traffic were routed
  through the proxy, the adapter would already trust the interception CA.
  The single missing piece is proxy routing (CONNECT tunneling).

**Consequence if dispatched as-is:** the request either fails closed
(`connection_error`, if direct egress is unavailable from the runner) or
reaches Twelve Data with `apikey=hsurr:…` verbatim and is rejected as an
invalid key. Neither outcome is a substitution. (Whether direct egress
succeeds was deliberately NOT tested — any attempt would itself be a
vendor contact, which this task forbids.)

**What resolves it** (any one, separately reviewed — none done here):
(a) teach the adapter environment-proxy support: honor the standard
`*_proxy` configuration with an HTTPS CONNECT tunnel to the configured
proxy (stdlib `http.client` supports this via `set_tunnel`), preserving
the contract's one-attempt / sanitized-failure / apikey-LAST properties;
or (b) run the eventual dispatch from an environment whose egress is
transparently intercepted rather than explicitly proxied; or (c) a
platform ruling that direct connections from the live runner are
substituted by another mechanism — to be evidenced, not assumed.

**One-step check at first live use:** the §4 screen IS the check. A `200`
with a `{"status":"ok", "values":[…]}` payload proves end-to-end
substitution on the production path. An auth-class rejection
(`401`/`403`, or a `200`-wrapped error payload naming the apikey) proves
the surrogate arrived unsubstituted. A `connection_error` /
`tls_failure` TransportError proves the direct path cannot egress. Each
outcome is decisive on its own; none requires a second request.

---

## 3. Combined-tree / patch plan (PLAN ONLY — nothing merged)

### 3.1 Source inventories (pinned)

**Side A — collector, from PR #8 branch `research/td-lifecycle-repair-20261012`
at `f64d12f885339e9e2ab4fa38b4a55df78db39b9f`** (2 commits over merge-base
`411457d`: `411457d` collector, `f64d12f` integration evidence):

| File | sha256 |
|---|---|
| `td_lifecycle_repair_candidate/td_min_collector.py` | `bd003c3cd5866172c04b0165d6ee60ec16be8487f28e90b4e6e1df046f8d489b` |
| `td_lifecycle_repair_candidate/test_pinned_integration.py` | `f1f195170edc1c070d5ca682fe48ad4cd32bc54f5053072f1b3511a396865386` |
| `td_lifecycle_repair_candidate/test_lifecycle_repair.py` | `1421f52ee5bfb11b5f53128c59269e1bf114228046aaf0b3676c1636652a03c4` |
| `td_lifecycle_repair_candidate/integration_requirements.lock` | `08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068` |
| `td_lifecycle_repair_candidate/integration_results.json` | `ba8000ec79354992882baf5bf346bb58d8af9da25bbb8993b9ddcd2c32d96f3c` |
| `td_lifecycle_repair_candidate/integration_test_output.txt` | `1b6693859f10b44f5d6b9a0684e6a4c5bb7c9c138b2eb26af6deb208ff5b3836` |
| `td_lifecycle_repair_candidate/test_output.txt` | `2ad14c15539015f607667753d973a904189977d59dc4ec385cb64bebe07bc370` |
| `td_lifecycle_repair_candidate/README.md` | `f441a0387c58961a446fe7e6367f24fd67697aa23b183730abcfc717dc50dbcb` |
| `td_lifecycle_repair_candidate/INTEGRATION_REVIEW_20261013.md` | `701809292a05151a36ca1f284de9ecaf982bfe14b0ff00e0eb4df2b277a34ce8` |

(All paths under `research_notes/`.)

**Side B — adapter/driver/manifest, on `main`** (post-this-task working tree
for driver/tests; everything else committed):

| File | sha256 |
|---|---|
| `td_transport_adapter/driver.py` (corrected, this task) | `671f4d0ce25a76bc4967f1ca8cbb16fcda037f0e0ce71529c2aa385dce33fed1` |
| `td_transport_adapter/td_http_transport_adapter.py` (unchanged) | `85c67977d176e36135751e588cc81d1bb1f21e56821189796cf87bdaab389d31` |
| `td_transport_adapter/test_transport_adapter.py` (updated, this task) | `b758d5e5c4a16a3e54c293e5e5587fd91c7372ebc97f28779bc45f1b3023638a` |
| `td_transport_adapter/sentinel_probe.py` (new, this task) | `59468511bd185ab3050b5f389f10644984afff8af45fc1d3e2064dad15073496` |
| `pilot_harness/rate_limiter.py` | `06ad383d856e62d126d1aae9edc7804e1b09471d87d9b280ec55a25aea0b8d64` |
| `pilot_harness/validate_input.py` | `1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58` |
| `pilot_harness/verify_sources.py` | `a0bd2e4cdce44be5d9fcc1d7c21046391d36c9bd366a959df03bf5d19c9a79e0` |
| `pilot_harness/credit_ledger.json` (live; spent must stay 0 until §4) | `ce515aa6fd53b297b693762e4236b2ea203874641ce745e482ba76daf1a67c59` |
| `td_acquisition_adapter_preflight_evidence_20261013/acquisition_manifest_v1.json` | `66a31e10aca1ca5f8af66139c4ff30a68cfef1c1138156eae103d8cf77e44f12` |
| `td_acquisition_adapter_preflight_evidence_20261013/adapter_contract.json` | `db6c44a2c95254fcc46d3c2717b682e00b33aa70fc563f8e86557dbca852a1f5` |

### 3.2 Order of operations (when separately authorized)

1. **Land Side B first:** commit this task's driver correction + test
   update + probe + this preflight on `main` (central commit; the parent
   agent owns commits).
2. **Re-run the merge simulation** against the new `main`:
   `git merge-tree --write-tree main origin/research/td-lifecycle-repair-20261012`
   must exit 0 with no conflicted-files section. (Against pre-correction
   `main` it already does — tree `0bfa0dc909c19ad53b928ea87b009a83145b4f83` —
   and the two sides' path sets are disjoint: the branch touches only
   `research_notes/td_lifecycle_repair_candidate/*`; this task touches only
   `research_notes/td_transport_adapter/*` + this note. Cleanliness is
   therefore expected to carry over; the re-run is the verification, not
   a hope.)
3. **Land Side A:** merge PR #8 if GitHub's state clears (see 3.3-C1), or —
   equivalently and deterministically — cherry-pick `411457d` and `f64d12f`
   onto `main` and close PR #8 as superseded-by-cherry-pick, recording
   both commit IDs and this plan in the bridge thread. Cherry-pick is the
   recommended path: it makes the landed tree independent of the PR's
   stale mergeability state, and the resulting tree is byte-identical to
   the simulated merge for every Side-A path.
4. **Post-land verification in the combined tree** (all offline):
   - `driver.load_collector_module()` succeeds against the landed
     `td_lifecycle_repair_candidate/td_min_collector.py` and its bytes
     hash to the accepted pin `bd003c3c…` (verified in simulation: the
     merged tree's collector hashes to exactly the pin the driver
     enforces).
   - Adapter suite: 32/32 (this task's suite extracts the collector from
     `f64d12f`; after landing, re-run with the collector taken from the
     working tree to prove the landed bytes, not the commit, satisfy the
     pin — same sha either way).
   - Pinned-integration suite from the branch (`test_pinned_integration.py`,
     16/16 at `f64d12f`) re-run in the combined tree with the pinned venv
     (`integration_requirements.lock`: pandas 2.2.3,
     pandas_market_calendars 4.5.1).
   - Live ledger sha256 unchanged (`ce515aa6…`).
5. **Documentation supersession:** append a bridge note that the branch's
   `INTEGRATION_REVIEW_20261013.md` / `README.md` describe the pre-merge
   PR state; do not edit the landed evidence files (they are records).

### 3.3 Conflict register

- **C1 — PR #8 `mergeable=false` (reviewer-observed) vs clean local
  simulation.** `git merge-tree` (git's own merge machinery, base
  `411457d`, branch 2 ahead / main 52 ahead) produces a clean tree with
  zero conflicted paths; the sides modify **disjoint path sets**, so no
  textual conflict exists to resolve. The `mergeable=false` state is
  therefore NOT a content conflict: it is attributable to GitHub-side
  mergeability state (stale computation against an older `main`, or a
  base other than current `main`). **Resolution:** step 3's cherry-pick
  path removes the dependency on that state entirely; if the merge path
  is preferred, first re-sync GitHub's computation (e.g. update the
  branch) and re-check — do not hand-resolve phantom conflicts.
- **C2 — Dangling default path on `main` today.** `driver.COLLECTOR_PATH`
  points at `research_notes/td_lifecycle_repair_candidate/td_min_collector.py`,
  which does not exist on `main` — the production construction path is
  currently unsatisfiable from `main` alone (the suites pass only because
  they extract the pinned bytes from `f64d12f`). **Resolution:** landing
  Side A (step 3) is precisely the fix; until then, `main`'s driver is
  evidence-complete but not dispatch-constructible, which is consistent
  with LIVE HOLD.
- **C3 — Duplicate collector copies in evidence trees.** `main` carries
  byte-copies of the collector under
  `td_integration_review_evidence_20261012/{cand,run,run_h}/…` and the
  superseded original under `…/orig/td_minimal_collector/`. Path-confusion
  risk only. **Resolution:** none required — the driver binds exactly one
  canonical path (Side A's) and pin-checks its bytes; the evidence copies
  are never on a load path. Recorded here so no future step "helpfully"
  re-points the driver at a copy.
- **C4 — Manifest generations.** The combined tree binds the preflight
  manifest `TD-ACQUISITION-MANIFEST-V1-20261013` (51 requests, sha
  `66a31e10…`), which supersedes `pilot_harness/request_manifest.json`
  (R3). The collector's fixture manifests in the suites are test-only.
  **Resolution:** the §4 screen and any future acquisition name the V1
  manifest by ID + sha256; R3 stays as a superseded record, untouched.
- **C5 — Ledger singularity.** Both sides reference the same persisted
  limiter state (`pilot_harness/credit_ledger.json`); branch scenario
  runs used scratch ledgers, as do the adapter suites. **Resolution:**
  no merge action; the invariant to verify at step 4 is the live
  ledger's sha256 (`ce515aa6…`, spent 0) before and after landing.

---

## 4. First-live screen — PROPOSAL ONLY (not executed, not an authorization claim)

**Purpose:** spend exactly one credit to settle the Sentinel question
(§2) end-to-end on the real production path, and produce the first
real receipt through the combined dispatch stack. Proposed for
adjudication; execution requires its own separate authorization after
blocker 3 lands and a §2 resolution (or an explicit decision to run it
as the §2 one-step check on the unresolved path, accepting the
`connection_error`/auth-rejection outcomes as the answer).

**Exact request** — request #1 of the pinned manifest
`TD-ACQUISITION-MANIFEST-V1-20261013` (sha256 `66a31e10…`), identity
`AAPL|/time_series|1h|2026-04-01T00:00:00|2026-10-06T23:59:59|America/New_York|adjust=splits`:

- Endpoint: `GET https://api.twelvedata.com/time_series`
- Parameters, in the adapter contract's fixed order (apikey LAST):
  `symbol=AAPL`, `interval=1h`, `start_date=2026-04-01T00:00:00`,
  `end_date=2026-10-06T23:59:59`, `timezone=America/New_York`,
  `outputsize=5000`, `order=asc`, `adjust=splits`, `format=JSON`,
  `apikey=<hsurr surrogate from the vault binding>` — the surrogate is
  fetched fresh in-process by `driver.get_api_key()`; the raw key is
  never in the process.
- Path: combined tree only — `driver.build_collector` (default vault
  source, default live ledger) → collector dispatch of `REQ-P1H-01`
  only, `max_attempts=1`, `semantics_status` unchanged. Expected
  credits: **1** (manifest `expected_credits=1`, `credit_weight=1`).
  Expected response bound: 1,323 one-hour bars (≤ outputsize, no
  pagination).

**Expected evidence produced:**
- The collector's lifecycle record for `REQ-P1H-01`
  (`CREDIT_RESERVED → STARTED → RECEIVED → COMPLETED`, or HOLD with the
  preserved response), the raw response body as the receipt file
  (`REQ-P1H-01.json`), and the live ledger transitioning `spent 0 → 1`
  — nothing else in the ledger changes.
- The HTTP status and payload class, which settle §2 in one step:
  - `200` + `{"status":"ok", …values…}` → substitution works end-to-end;
    §2 blocker clears for this path; data then flows into the frozen
    comparison protocol (P1–P7) — no strategy conclusion from one pull.
  - `401`/`403` or an error payload naming the apikey → the surrogate
    reached the vendor unsubstituted; §2 stands, resolution (a)/(b)/(c)
    required before any further live attempt.
  - Sanitized `TransportError` (`connection_error` / `tls_failure`) →
    direct egress unavailable from the runner; same consequence.
- A run note pinned to the manifest ID + sha256, the driver/adapter/
  collector pins in §3.1, and the ledger hashes before/after.

**Stop rule:**
- Exactly ONE attempt. No retry on any outcome — not on 429, not on
  5xx, not on timeout, not on auth rejection. The adapter already
  enforces one attempt; the run authorizes nothing beyond it.
- Any non-COMPLETE outcome = HOLD: preserve the receipt/lifecycle/ledger
  evidence untouched and stop. A failure means the dispatch path (not
  the strategy, not the data) failed its screen; it is evidence about
  §2/§3, never a reason to re-run, re-key, fall back to a raw key, or
  widen the request set.
- If the limiter refuses (ledger state inconsistent with `spent=0`
  before the run), abort BEFORE dispatch — that refusal is the screen
  failing its own precondition, at zero credits.
- Success authorizes nothing by itself: the remaining 50 manifest
  requests stay gated behind their own adjudication.

---

## Pins (this task)

| Artifact | sha256 |
|---|---|
| `td_transport_adapter/driver.py` (corrected) | `671f4d0ce25a76bc4967f1ca8cbb16fcda037f0e0ce71529c2aa385dce33fed1` |
| `td_transport_adapter/td_http_transport_adapter.py` (unchanged) | `85c67977d176e36135751e588cc81d1bb1f21e56821189796cf87bdaab389d31` |
| `td_transport_adapter/test_transport_adapter.py` (updated) | `b758d5e5c4a16a3e54c293e5e5587fd91c7372ebc97f28779bc45f1b3023638a` |
| `td_transport_adapter/sentinel_probe.py` (new) | `59468511bd185ab3050b5f389f10644984afff8af45fc1d3e2064dad15073496` |
| `test_evidence_combined_preflight_20261014/results.json` (32/32) | `a4ada3d1ccf85a7d5aaadb630d63dd74dac9ac4eae70ef88aca217f4fc6c2342` |
| `test_evidence_combined_preflight_20261014/test_output.txt` | `6c2cb20d8384ce77acb311513b5828ae45ded8b97df5ecda6f991322f5c42837` |
| `test_evidence_combined_preflight_20261014/sentinel_probe_results.json` | `6edc539ef786c2fddae50a0fd99c82d79bd23af658d1c1beb51d75670edffe69` |
| Live credit ledger (unchanged) | `ce515aa6fd53b297b693762e4236b2ea203874641ce745e482ba76daf1a67c59` |
| Collector pin (unchanged) | `bd003c3cd5866172c04b0165d6ee60ec16be8487f28e90b4e6e1df046f8d489b` |
| Limiter pin (unchanged) | `06ad383d856e62d126d1aae9edc7804e1b09471d87d9b280ec55a25aea0b8d64` |

**Environment:** Python 3.12.3; pinned-dependency venv rebuilt from
`integration_requirements.lock` (pandas 2.2.3, pandas_market_calendars
4.5.1, exchange_calendars 4.13.2). `vendor_calls: 0, credits: 0, spend: 0`.
Suite ran twice: first pass 31/32 (my new vault-failure test stubbed the
wrong seam — it replaced `_vault_entry` instead of the helper module, so
the stub's exception bypassed the driver's sanitizer by construction);
repair pass fixed the test seam only, second run 32/32. Prior-round
evidence directories are preserved untouched.

**Status after this preflight:** raw-key bypass CLOSED; combined-tree
plan pinned and ready; Sentinel = exact blocker on the current adapter
(no proxy routing). **Live dispatch remains HOLD.** Nothing here is a
live-use authorization, a merge, or a feed/performance claim.
