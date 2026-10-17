# QF-TD-FRESH-LIVE-DRIVER-INTEGRATION-20261016-04 r1 — integrated live-capable candidate

**Verdict: `FRESH_LIVE_DRIVER_INTEGRATION_PASS_OFFLINE`** (spec: Issue #1 comment
6227025232). This pass authorizes **no live call**; independent review comes next.
Offline only: injected fake transport + kernel network denial (`unshare -n`)
throughout. No vendor/Yahoo/model/API calls beyond the public spec fetch, no
credits/spend, no downloads/installs, no live writes, no backtest/performance,
no holdout, no production/trading, no Issue #9, no merge/adoption, no
PARKED-state reuse. The real pilot credit ledger was never touched (hash-read
only in prior rounds; not read at all in this one). The r1/r2 preflight packages
(commit `7f5251f`, `a56c449`) and all prior evidence are byte-identical, unedited.

## The candidate

One integrated entrypoint:
`research_notes/td_fresh_live_driver_integration_evidence_20261016/live_driver.py`
(sha256 `5fed45242eb5ec465266c4d4c4258485f01a8c5bfdfdda2fb81295d3cf6d9c00`),
derived from the accepted r2 driver with the four integration gaps closed in
executable code. It binds: the fresh manifest canonical bytes/digest
`71aade8b…`; the fresh supplement canonical bytes/SHA `3cbdbf63…` verified
**before parsing/use and before any namespace/ledger access**; the NL
environment/mechanism pins; one operator-pinned account-shared limiter ledger
outside all run namespaces (interprocess-flocked, re-read under lock,
atomic-replaced, corrupt → refusal, never reset); the pinned collector
implementation; and the live HTTPS/vault-proxy transport design as immutable
constants plus a candidate `LiveHttpsTransport` implementation.

## How each integration gap was closed

1. **Transport.** `live_driver.py` binds the -14 pilot `UrllibTransport`
   design (`pilot_harness/pilot_acquire.py`, sha256 `acf39bbd…`) as constants
   — endpoint `https://api.twelvedata.com/time_series` (== the manifest's own
   endpoint pin), credential ref `custom.twelvedata`, allowed hosts
   `["api.twelvedata.com"]`, response cap 33,554,432 B, timeout 30 s — and
   ships `LiveHttpsTransport` implementing its semantics (surrogate attached
   at the last moment via `dynamic_credentials.url_with_surrogate_query_param`,
   sanitized exceptions, capped read) plus `build_url()` (the pilot parameter
   set, deterministic, credential-free). The transport is **DISARMED**: the
   `Runner` refuses `TRANSPORT_NOT_ARMED` before any namespace/ledger access
   unless the transport was constructed `armed=True`; nothing in this package
   arms or connects it (I18). The armed code path was never executed.
2. **Supplement schema reconciliation.** No new supplement bytes: the pinned
   artifact remains exactly `3cbdbf63…` (the r2 pin is unchanged, not edited).
   The change is a code layer, `reconcile_supplement()`: after the r2
   exact-byte SHA gate, it validates the fresh schema field-by-field —
   `supplement_id == TD-FRESH-FM-SUPPLEMENT-NL-20261016`,
   `class == EXPECTED_EMPTY_CLOSED_SESSION`,
   `lifecycle_event == CLOSED_DAY_EVIDENCED`,
   `status == OFFLINE_CANDIDATE_NOT_ADOPTED`,
   `base_manifest_canonical_digest == manifest digest` (the fresh-schema
   counterpart of the collector's `base_manifest_digest` conjunct),
   `classifier_pins` == the ab254c3 collector commit/bytes, the adapter
   contract pin in `safety_design_binding`, the calendar `environment_binding`,
   and per-entry `expected_bars == 0`, exact request digests, and
   digest-verified pinned `calendar_proofs` (the NL-qualified mechanism's
   recorded proof — the fresh schema's counterpart of the collector's
   live-mechanism conjunct; live re-derivation remains checklist gate 7).
   It returns the classifier view the lifecycle consumes. Any anomaly →
   `SUPPLEMENT_SCHEMA_MISMATCH` (or the r1 semantic codes) pre-dispatch,
   zero calls/writes (I04, incl. mutations to fields the r1 driver never
   examined: `classifier_pins`, `notes`, `status`, calendar proof body).
3. **Real closed-response schema.** `classify_closed()` now implements the
   preserved vendor contract (REQ-SPT-07 observation, sha `3339c341…`):
   HTTP 400; keys exactly `{code, message, status, meta}`; `code` the integer
   400; `status == "error"`; message byte-equal; **no `values`**; `meta`
   exactly `{symbol, interval, exchange}` with symbol/interval bound to the
   request and `exchange == ""`. The fake three-key body is removed;
   `FakeTransport` emits the real four-key body via `build_closed_body(req)`.
   I03 proves the exact positive and 11 negatives (three-key body, missing/
   wrong `meta` fields, `exchange != ""`, extra `values` key, string code,
   mutated message, wrong status, closed body on an unregistered request,
   closed body under HTTP 200) — none classify; all fall through to HOLD.
4. **Executable binding.** Pins for the collector (commit `ab254c3…`, bytes
   `b683d277…`), NL mechanism module (`1b83cdcd…`), NL env lock (`08b38cfa…`),
   adapter contract (`ec877a04…`), and the pilot transport/rate-limiter
   sources (`acf39bbd…`, `06ad383d…`) are constants in the entrypoint, and
   trial I01 recomputes the on-disk sources against them before any
   lifecycle proof runs.

## Proof (integrated entrypoint, fake transport, `unshare -n`)

**18/18 trials, 133/133 checks, run twice; normalized matrices byte-identical**
(sha256 `1c3c76c2a0d219187e85776826aa177002632d06f9af74d3487a1ccc2341e894`).
Trial-namespace hash lists (950 files each) differ only in the 6 I14
race-artifact files (worker win splits / resulting ledger bytes); every check
is over split-invariant totals, as in r2.

- I01 source/artifact pins (above) all recompute equal; driver source contains
  no `apikey=` assignment.
- I02 full ordered lifecycle: 51 calls in frozen manifest order, outcome
  COMPLETE, **49 COMPLETED + 2 CLOSED_DAY_EVIDENCED** (REQ-SPT-07/08, real
  schema), 51 reservations, 49 receipts + 2 `.closed_day.bin`, old SPOT8 state
  tree byte-identical before/after.
- I03 real-schema closed positives/negatives (above).
- I04 manifest/supplement tamper: all mutations refuse pre-dispatch, zero
  calls, namespace and ledger never created.
- I05/I06/I07 HTTP 500 stops at request 5; venue mismatch stops at request 21;
  unknown credit state HOLDs pre-dispatch with zero calls.
- I08 shared-ledger day cap: preloaded 795 → exactly 5 calls fit, refusal at
  exactly 800 reservations.
- I09 crash after STARTED (request 11): restart makes 0 calls, AMBIGUOUS →
  terminal HOLD, prior 10 receipts intact. I10 restart-after-completion
  idempotent (0 calls, 51 reservations). I11 tampered receipt →
  HOLD_RECEIPT_REVALIDATION_FAILED. I12 duplicate live owner refused; owner
  admitted after release. I13 foreign namespace file / foreign identity
  binding refused.
- I14 two real processes, one ledger: minute cap — combined OK exactly 8, all
  rids unique; day cap — preloaded 795 → combined new OK exactly 5, ledger
  stops at exactly 800. I15 crash (`os._exit(42)`) reservations persist;
  corrupt ledger → `LIMITER_LEDGER_CORRUPT`, bytes never reset. I16 ledger
  path inside a namespace refused pre-dispatch.
- I17 credential hygiene: no `apikey` substring in any namespace artifact
  (receipts, lifecycle, state), argv, or the timeout path's outcome/exception
  surface. I18 disarmed live transport refused before namespace/ledger
  creation; `build_url` deterministic and credential-free.

## Attempts, repair, minutes

Elapsed ≈ 00:28Z→00:51Z ≈ **23 min of the ≤35 cap**, incl. **one repair episode
≈ 9 min (≤10 allowance)**. The integrated **driver source was never repaired**;
all failures were trial-harness defects, and both failed matrices are preserved
(`integration_matrix_attempt0_failed.json` sha256 `adab8393…`;
`integration_matrix_attempt1_failed.json` sha256 `ed5a2150…`):

- Attempt 0 (14 PASS): I06 FAIL + I18 ERROR (harness: instance-level
  `__call__` monkeypatch is bypassed by type lookup; `expect_refusal`
  transport kwarg collision), I14 ERROR + I15 FAIL (harness:
  `ledger_worker_i.py` missing — a shell `&&` chain in package prep
  short-circuited before the file was created).
- Attempt 1 (17/18, 132 checks): I14 `day_cap_new_5` FAIL — the harness
  preload spread fake timestamps across two calendar days; fixed by adopting
  r2 T24's direct-construction preload (all reservations on the runner's day,
  >1 h old). One further I08/I14 preload function is shared.
- Disclosure: attempt 0's per-trial artifact directory was deleted before the
  repaired run (its normalized matrix and failure record above are preserved;
  the raw attempt-0 trial trees are not). Attempt 1's trees are preserved
  (`trials_attempt1_failed/`).

## Deliverables (this package, UNCOMMITTED)

- `TD_FRESH_LIVE_DRIVER_INTEGRATION_20261016.md` (this memo)
- `td_fresh_live_driver_integration_evidence_20261016/live_driver.py` — `5fed4524…`
- `…/run_integration_trials.py` — `a5697ccb…`; `…/ledger_worker_i.py` — `81f4fbea…`
- `…/integration_matrix_run1.json` / `…/integration_matrix_run2.json` — both `1c3c76c2…`
- `…/integration_matrix_attempt0_failed.json` — `adab8393…`; `…/integration_matrix_attempt1_failed.json` — `ed5a2150…`
- `…/live_pre_dispatch_checklist.md` (updated with exact -04 pins)
- `…/trials_run1_hashes.txt`, `…/trials_run2_hashes.txt`, `…/SHA256_MANIFEST.txt`

Scope restated: this package is a candidate + offline proof only. It creates
no live packet, arms no transport, and authorizes no authenticated TD request.
