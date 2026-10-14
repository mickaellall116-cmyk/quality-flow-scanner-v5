# TD V2-Bound Candidate + SPOT Batch Preflight — QF-TD-V2-SPOT-BATCH-PREFLIGHT-20261014-12 r1

**Verdict: PREFLIGHT COMPLETE — batch technically ready; execution
NOT authorized by this task.** Fully offline. STOP before any vendor
request: zero vendor/auth calls, zero credits, zero spend. Live
ledger, live HOLD state, and the live rejected receipt are
byte-identical before/after (§7). A PASS here only makes the 8-credit
batch technically ready for separate Mike authorization.

Canonical source: GitHub Issue #1 comment `6172067035` (ChatGPT,
2026-10-14T15:35:02Z), which also carries the -11 SCOPED PASS. This
report executes its six numbered steps in order.

## 1. -11 amendment (canonical step 1)

`research_notes/TD_MANIFEST_V2_OFFLINE_REPLAY_AMENDMENT_20261014.md`
— separate immutable file; the -11 report's bytes are untouched.
Reconstructed from existing evidence only (no test rerun): evidenced
artifact-producing span 15:01Z→15:14:54Z ≈ 14 min; 5 trials itemized,
all first-pass PASS; failures: none recorded; repair usage: none
recorded (0 min); total wall-clock beyond the evidenced span and
any artifact-free iteration marked **UNKNOWN**. Sanitized session
aggregates: 910 bars, 2026-04-01 09:30:00 → 2026-10-06 15:30:00,
session_1h validation PASS; derived aggregate (flagged derived):
130 sessions × 7 constituents, 0 incomplete sessions; per-session
missingness table was not persisted in -11 and is recorded
unavailable, not re-derived.

## 2. Isolated V2-bound candidate (canonical step 2)

| | |
|---|---|
| Commit | `b18db3ce25f3014d11847ba1ac92f488a994022e` |
| Tree | `06b12f82977447934921d82701763251f9373af1` |
| Parent | `7ec0f0efce7d9ce668233bf8ee55d7503ec47c0a` (single parent) |
| Ref | `refs/heads/td-v2-spot-candidate-20261014` (pushed; `git ls-remote` verified) |
| Diff vs `7ec0f0e` | 4 files changed, 1409 insertions, 6 deletions — nothing else |

Changed files (exact):

- **Added** `…/acquisition_manifest_v2.json` — byte-identical to the
  accepted V2 on main (sha256 `4a6e3a55…`).
- **Added** `…/acquisition_manifest_v2_spot8.json` — the §3 subset
  (sha256 `ddff040f…`).
- **Modified** `…/adapter_contract.json` (`db6c44a2…` → `ec877a04…`):
  `binds.manifest` only — path → V2 file, manifest_id →
  `TD-ACQUISITION-MANIFEST-V2-20261014`, canonical_sha256 →
  `4d5b7a56…` (V2 canonical digest; digest method first verified by
  reproducing V1's pinned `e1cb648d…` from V1's bytes).
- **Modified** `…/SHA256_MANIFEST.txt` (`d465ef78…` → `541ccf85…`):
  manifest pin V1 → V2, subset pin added, contract pin updated,
  bound canonical-digest pin V1 → V2.

Everything else is byte-identical to `7ec0f0e`, verified by the
full-tree diff and by pins inside the export: collector
`bd003c3c…`, adapter `ae8f4837…`, driver `671f4d0c…`, limiter
`06ad383d…`, adapter test file pristine `b7fa2dc9…`. V1's manifest
file remains present and byte-identical in the tree; only the
binding moved. Disclosure: the contract's pre-existing
`identity_semantics` prose still describes venue identity in V1-era
terms (e.g. "NASDAQ/XNAS") — it is descriptive text, not the
binding; the binding object (`binds.manifest`) is what the
candidate changes, and the prose was left byte-identical rather
than rewritten. Main and PR #8 untouched.

## 3. SPOT-only batch manifest (canonical step 3)

`TD-ACQUISITION-MANIFEST-V2-SPOT8-20261014` — exact subset of V2 by
the rule `leg == 'SPOT'` (8 of 51), V2 order preserved, every
request object copied byte-for-byte (proven three ways: deep
equality, identical per-request serialization, identical per-request
canonical digest). File sha256
`ddff040fa654303cf4289f4c39c2a5b5af998bd4065ceddd4e4f5d52fcb8c28d`,
canonical digest
`748ca95789c6f16bab81fbc903fd0c60a890dd2f2e21a63d97ffdb962d70e4fb`.
Budget: exactly 8 requests / 8 credits, `max_attempts = 1` each, no
retry, no pagination. The subset ships inside the candidate
(§2 path) and as a byte-identical copy in this task's evidence dir.

| ID | Symbol | Window (ET) | Case | Bound |
|---|---|---|---|---|
| REQ-SPT-01 | AAPL | 2026-03-09 → 2026-03-13 | DST-spring week | 35 |
| REQ-SPT-02 | QQQ | 2026-03-09 → 2026-03-13 | DST-spring week | 35 |
| REQ-SPT-03 | AAPL | 2025-11-03 → 2025-11-07 | DST-fall week | 35 |
| REQ-SPT-04 | QQQ | 2025-11-03 → 2025-11-07 | DST-fall week | 35 |
| REQ-SPT-05 | AAPL | 2025-11-28 | early close | 7 |
| REQ-SPT-06 | QQQ | 2025-11-28 | early close | 7 |
| REQ-SPT-07 | AAPL | 2026-07-03 | closed day | 7 |
| REQ-SPT-08 | QQQ | 2026-07-03 | closed day | 7 |

No parameter was invented: every field (1h, America/New_York,
outputsize 5000, asc, adjust=splits, per-symbol segment-MIC venue
pins XNGS/XNMS) is V2's own, copied — so no derivation flags apply.

## 4. P1–P7 qualification ledger (canonical step 4)

New persistent artifact:
`td_v2_spot_batch_preflight_evidence_20261014/qualification_ledger_p1_p7.json`
(frozen protocol of preflight §5; designed to be appended to by
future tasks). Current state — nothing promoted beyond its class:

| Check | Status |
|---|---|
| P1 Timestamps | SAMPLE evidence (AAPL): session_1h PASS, 130 complete sessions, labels on the frozen grid |
| P2 Bar-boundary/semantics | **HOLD** — pending all eight SPOT receipts; semantics INSUFFICIENT, CONSTRUCTION_HOLD in force |
| P3 Date-end inclusion | SAMPLE evidence (AAPL): final session fully present, COMPLETE |
| P4 Venue coverage | IDENTITY evidence (AAPL: NASDAQ/XNGS/USD recorded, binds under V2); volume/comparator PENDING |
| P5 Missing bars | SAMPLE evidence (AAPL): 910/910 constituents, 0 missing |
| P6 Revision stability | PENDING (needs authorized PAR baseline + T+7/T+30) |
| P7 Adjustment basis | PENDING (ADJ legs not acquired) |

Overall qualification: NOT PASSED.

## 5. Suites + export + pre-dispatch proof (canonical step 5)

Self-contained export: `git archive b18db3c` → 661 files = 661
tree entries; no `.git`, no alternates. All runs executed from the
export only, under a git-blocking PATH shim (**zero git
invocations logged**), a loopback-only socket guard, and
`PYTHONDONTWRITEBYTECODE=1`; venv built from the candidate's own
lock (pandas 2.2.3, pandas_market_calendars 4.5.1, Python 3.12.3).

| Suite | Result |
|---|---|
| Adapter (`test_transport_adapter.py`) | **41/41 PASS**, exit 0 |
| Pinned integration (`test_pinned_integration.py`) | **16/16 PASS**, exit 0 |
| Collector (`test_lifecycle_repair.py`) | **19/19 PASS** (`Ran 19 tests … OK`) |

Guard record across all runs: exactly one non-loopback connect
attempt — the adapter suite's own blackhole test dialing RFC-5737
`192.0.2.1:8443` — blocked by the guard and handled fail-closed by
the suite (41/41 stands); zero non-localhost DNS lookups; all other
traffic loopback (the suites' synthetic proxy/collector fixtures).
Disclosure, same as -08 r2: the export copy of the adapter test
file carries the r2 test-only patch (`git show f64d12f:…` →
`drv.COLLECTOR_PATH.read_bytes()`, 4 sites; patched sha256
`972fbb5c…`, byte-identical to r2's patched file). The candidate
commit carries pristine bytes. No fixture or raw key appears in any
deliverable — this lane has no raw key (vault surrogate only), and
no vault fetch was performed offline; the vault→proxy→collector
route is proven by the synthetic round-trip inside the 41/41
adapter suite plus the driver pin load below.

Pre-dispatch proof for the batch (`pre_dispatch_proof.json`):

- Collector CLI on the subset: `validate-manifest` → **0 errors, 8
  requests**; `preflight` → **0 prerequisite failures, dispatch
  BLOCKED** (zero-call build). Same on full V2: 0 errors / 51
  requests, BLOCKED.
- Contract binding verified from export bytes: bound file exists,
  sha256 `4a6e3a55…`, canonical digest == contract pin `4d5b7a56…`;
  pin file carries the V2 + subset lines.
- Driver default path loads the export's own collector at pin
  `bd003c3c…` (loader-verified).
- **Fresh state directory** (`/tmp/td12_state/state_a`, created by
  this run; the -09 HOLD state was never opened): Collector bound
  the subset manifest digest (`748ca957…`); run with the build's
  default transport → **`HOLD: transport disabled (zero-call
  build)`**, 0 completed — fail-closed before any dispatch.
- Shared limiter path: the same pinned `RollingCreditLimiter` on a
  disposable ledger accepted exactly 8 weight-1 reservations and
  refused a 9th inside the minute (8/min cap); disposable ledger
  spent = 8. The live ledger was never the limiter's state file in
  any run.
- Venue fail-closed spot check: single-request reduction of the
  subset + local stub returning mic_code XNYS against the XNGS pin
  → **`HOLD: venue binding mismatch for REQ-SPT-01`** — the -09
  behavior reproduced offline against the batch manifest.
- Retention path: all state/receipts artifacts of these runs live
  under the disposable `/tmp/td12_state` tree (private, git-ignored
  by location); nothing was written into the repo's live store.

## 6. Immutable evidence (canonical step 6)

This report + `research_notes/td_v2_spot_batch_preflight_evidence_20261014/`:
`candidate_manifest.json` (commit/tree/parents/ref, changed + pin
hashes), `acquisition_manifest_v2_spot8.json` (byte-identical
subset), `subset_proof.json` (per-request digests), 
`qualification_ledger_p1_p7.json`, suite outputs
(`adapter_suite/`, `pinned_integration_suite/`,
`collector_suite_stderr.txt`), `cli_validate_preflight.txt`,
`pre_dispatch_proof.json` + the proof script itself,
`netguard_log.txt`, `test_only_patch.diff`. Secret scan over all
deliverables: no credential-shaped strings (the only key-shaped
material is `hsurr:` surrogate references inside the suites' own
synthetic outputs, as in every prior package).

## 7. Safety accounting

Byte-identical before/after (full sha256 measured both times):
live credit ledger `4ba4cf6f…` (spent 1, unchanged); live HOLD
state — `pilot_state.json` `8c59a56c…`, `lifecycle.jsonl`
`fbdbd1c3…`, `manifest_binding.json` `324a69ba…`; live rejected
receipt `c47bf899…`; V1 `66a31e10…`; V2 `4a6e3a55…`. No
reconciliation of the HOLD was attempted. No merge, no PR #8
change, no production/frozen change, no collector/adapter/driver
byte changes anywhere. Vendor/auth calls: 0. Credits: 0. Spend: 0.

## 8. Trials, failures, effort (this task)

- Trials: canonical fetch (1); digest-method verification (PASS);
  subset build + 3-way exactness proof (PASS first attempt);
  candidate build/commit/push (PASS first attempt; ls-remote
  verified); export + venv (PASS); suites — adapter 41/41,
  integration 16/16, collector 19/19 (PASS); CLI validate/preflight
  ×4 (PASS); pre-dispatch proof script (PASS first run).
- Invocation misfires (corrected in seconds, no artifact impact):
  adapter and integration suites each first launched without their
  required `--output-dir`; the integration suite was then launched
  against a pre-created output dir it insists on creating itself
  (`FileExistsError`). All three were re-run correctly; outputs in
  evidence are from the successful runs only.
- Repair usage: 0 of the 1 allowed repair pass was needed for the
  deliverables themselves. Total elapsed ≈ 40 min of the 60-min
  budget (canonical fetch ~15:41Z → deliverables complete ~16:20Z).

**STOP.** The batch is preflighted and technically ready. Any
dispatch of REQ-SPT-01..08 (8 credits) requires Mike's separate,
direct authorization; nothing in this package executes, schedules,
or pre-approves it.
