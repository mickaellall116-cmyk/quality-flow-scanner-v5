# QF-TD-FRESH-FULL-MANIFEST-PREFLIGHT-20261016-03 r1

Canonical spec: GitHub Issue #1 comment `6225325757` (governs where it
differs from any summary). Mode: one immutable **offline execution packet
only** — fake transport, network denied (`unshare -n`), zero vendor /
Yahoo / model / API calls, zero credits, zero spend, zero downloads or
installs, zero live limiter/state writes, zero backtest/performance,
zero tuning, zero holdout, zero production/trading, zero Issue #9
execution, zero merge/adoption, and **no use of the PARKED derivation
candidate** (`ce9c02a`, untouched). The old SPOT8 state and receipts are
preserved byte-for-byte (proven in §5).

## Verdict

**FRESH_FULL_MANIFEST_PREFLIGHT_PASS** — ready for independent review
before a separately dispatched live screen under standing capped
authority. This PASS authorizes no call by itself.

## 1. Fresh identity (spec point 1)

Derived from `TD-ACQUISITION-MANIFEST-V2-20261014` (file sha256
`4a6e3a55…`, canonical digest `4d5b7a56…`; both recomputed and matched):

| Item | Value |
|---|---|
| Manifest ID | `TD-ACQUISITION-MANIFEST-V2-FRESH-20261016` |
| Run ID | `TD-FRESH-FM-20261016-03-R1` |
| Canonical bytes | 27,691 bytes, written in canonical form (compact sorted JSON) |
| Canonical digest == file sha256 | `71aade8bfbb1f94b25d780bdf68f08f7f127740fc745c1755432acc5f74044db` |
| Requests | exactly 51, frozen V2 order: P1H×20, P4H×20, ADJ×3, SPT×8 |
| Symbols | 20 |
| Terms | one attempt each, no retry/pagination, `adjust=splits`, expected == max == 51 credits |
| Output namespace | `research_notes/td_fresh_full_manifest_preflight_evidence_20261016/runs/TD-FRESH-FM-20261016-03-R1/` (scheme proven by the trial namespaces in this package) |

The request table, endpoint, and budget are the V2 values verbatim;
identity, run id, binding digest, and namespace are new. Canonicalization
(compact sorted JSON + sha256) was proven against three lineage pins
before freezing: it reproduces the V2 canonical digest `4d5b7a56…`, the
SPOT8 canonical digest `748ca957…`, and the REQ-SPT-08 request digest
`f547d8fe…` exactly. **No evidence or state was copied into the new
run** — no receipts, lifecycle, limiter data, or the old supplement;
the fresh pilot state starts empty and the fresh binding digest
(`71aade8b…`) differs from the SPOT8 binding (`748ca957…`).

## 2. Bindings (spec point 2)

A fresh supplement (`fresh_supplement.json`, sha256 `3cbdbf63…`, status
`OFFLINE_CANDIDATE_NOT_ADOPTED`) re-binds the adjudicated semantics to
the full 51-request identity. It carries the NL candidate supplement's
schema, calendar block, and entries **by value**; the only change is the
base binding, from the SPOT8 manifest to the fresh manifest:

- Entries: `REQ-SPT-07` / `REQ-SPT-08`, `expected_bars = 0`, request
  digests `a259901e…` / `f547d8fe…` (recomputed from the fresh manifest;
  identical to the lineage pins because the request values are V2's).
- Calendar proof record (digest `36bc3a89…`): 2026-07-03 exchange-closed,
  provenance = the -12 subset-proof preregistration (derived from the
  pinned XNYS mechanism before any dispatch), the civil-calendar fact
  (2026-07-04 is a Saturday; NYSE observes the holiday Friday
  2026-07-03), and the NL lineage qualification chain.
- NL environment bound by pin (installs are out of scope for -03):
  rebuild `0923db7` (`NL_ENV_REBUILD_PASS`), lock `08b38cfa…`
  (11 packages), `pandas_market_calendars` 4.5.1, lineage NL-20261015,
  mechanism `validate_input.py` sha256 `1b83cdcd…`, CPython 3.12.3.
  Disclosure: the rebuilt venv was absent from /tmp at this session's
  start (the known VM-replacement loss class); the retained wheelhouse
  persists. The live checklist (gate 5) requires the environment present
  and re-verified immediately before dispatch.
- Classifier pins: collector commit `ab254c3…`, collector bytes
  `b683d277…`, NLQUAL result `080a6ba…`, new-lineage qualification
  `7de7950…`.
- Closed-session requests classify **only from their own fresh
  responses** in this run (proven T08). Nothing is derived from
  REQ-SPT-07's preserved v1 evidence; the v1 HOLD is not rewritten
  (the -05 design gap — no derivation entry point in a terminal HOLD
  state — does not arise: this is a fresh run, and classification fires
  in-run from fresh transport responses only).

## 3. Safety design re-scoped to 51 (spec point 3)

The accepted -04 design
(`P2_SPOT_V2_EXECUTION_PREFLIGHT_PASS`) is re-scoped unchanged in
substance from the 8-request SPOT8 identity to all 51 requests:
endpoint/entitlement expectations (prerequisites pin `038ccaf3…`),
venue identity per request (exchange + segment MIC + currency enforced
on receipt meta), expected credit maximum 51, shared persistent limiter
(`RollingCreditLimiter(8, 800)`, module sha256 `06ad383d…`; the live
ledger was read for its pin only — sha256 `7e5ccef0…`, unchanged — and
never written), reservation-before-dispatch lifecycle, write-once
raw/error/closed evidence, crash/restart/idempotency (STARTED without
durable completion = AMBIGUOUS, never redispatched), and fail-closed
batch stop: any first HTTP / identity / hash / budget / unknown-credit
failure stops the run; later requests remain NOT ATTEMPTED.

## 4. Offline proofs (spec point 4)

Driver: `preflight_driver.py` (packet-owned implementation of §§2–3).
Harness: `run_trials.py`. Executed **twice** under `unshare -n`; the two
normalized trial matrices are **byte-identical**
(`trial_matrix_run1.json` == `trial_matrix_run2.json`).

**22/22 trials, 67/67 checks PASS, both runs:**

| Trial | Result |
|---|---|
| T01 freeze & pin verification | fresh identity verifies against all pins |
| T02–T05 manifest tamper (symbol / order swap / budget / dropped request) | refused pre-dispatch, 0 calls each |
| T06–T07 supplement tamper (binding digest / `expected_bars` 0→7) | refused pre-dispatch, 0 calls each |
| T08 full run, fake transport | **COMPLETE**; exactly the 51 calls in frozen order; exactly 51 reservations; ≤8 reservations in any rolling 60 s (max observed 8, 6 pacing waits); 49 COMPLETED; REQ-SPT-07/08 classified `EXPECTED_EMPTY_CLOSED_SESSION` from their own fresh responses → `CLOSED_DAY_EVIDENCED`, **no receipt files, no COMPLETED events** for them; closed bodies preserved write-once as `.closed_day.bin`; response/request/manifest hash binding verified for representative 1h (P1H-01), native-4h (P4H-01), adjustment (ADJ-01), and spot (SPT-01) successes |
| T09 mutated closed message (1 char) | HOLD at REQ-SPT-07, 50 calls, SPT-08 NOT ATTEMPTED |
| T10 HTTP 200 + ok + empty values on closed window | HOLD (silent-acceptance exclusion), 50 calls |
| T11 400 body carrying a `values` field | HOLD, 50 calls |
| T12 exact closed shape on a non-preregistered request | HOLD at first request, 1 call |
| T13 calendar proof removed | classification disabled → HOLD, 50 calls |
| T14 HTTP 500 at request 5 | fail-closed stop, 5 calls, rest NOT ATTEMPTED |
| T15 venue (MIC) mismatch at request 3 | stop, 3 calls |
| T16 unknown credit state | HOLD before dispatch, 0 calls, 0 reservations |
| T17 shared limiter, 795 credits already reserved today | day cap binds across runs: 5 calls fit, then REFUSED at exactly 800 |
| T18 crash after STARTED (request 11) + restart | restart makes 0 calls; 1–10 stay COMPLETED (never redispatched); 11 marked AMBIGUOUS → terminal HOLD; 12–51 NOT ATTEMPTED |
| T19 restart after full completion | 0 calls, receipts revalidated, COMPLETE (idempotent) |
| T20 duplicate live owner | refused (flock), 0 calls |
| T21 foreign file in namespace | refused pre-dispatch, 0 calls, foreign bytes untouched |
| T22 corrupt limiter ledger | HOLD, 0 calls, ledger never reset |

Transport accounting: real/vendor calls **0**; fake dispatches per full
run exactly as asserted per trial. Note the honest scope of T08's
classification proof: the calendar conjunct is satisfied from the pinned
preregistered proof record bound in the supplement (digest-verified at
load and at classification); live re-derivation from the real mechanism
is checklist gate 7, not a preflight claim.

## 5. Preservation (spec point 1, cont.)

The old SPOT8 state directory
(`research_notes/twelve_data_stage0/snapshots/acquisition_state_spot8/`,
11 files) was hashed before and after the whole suite: **byte-identical**.
Nothing in any trial namespace references the old binding; the parked
derivation candidate was not read, copied, or modified.

## 6. Retention limits (spec point 6) — recorded explicitly

TD bytes from any future run of this packet are **private screen
evidence only, retained only while permitted**: Twelve Data's terms as
read 2026-10-07 specify no retention durations and §16.1 contemplates
deletion within 30 days of termination; **indefinite immutable retention
is NOT granted**; redistribution is prohibited without an add-on. No
claim of indefinite retention is made, and this packet supports **no
dataset-scale adoption** of TD bytes.

## 7. Live pre-dispatch checklist (spec point 5)

Published in the package: `live_pre_dispatch_checklist.md` — **12
gates**: adjudicated execution packet; standing-authority basis (already
granted — **not to be re-requested**; the old 8-credit grant is not this
task's ceiling); live account plan/status and remaining daily/minute
capacity re-verification (unknown/insufficient → HOLD); shared limiter
state; environment reproduction (freeze == lock, wheel hashes, library
and mechanism pins); manifest/supplement/source hashes; calendar-proof
re-derivation; clean namespace + zero prior attempts + sole owner;
credential/proxy boundary; adapter contract; stop rules armed; retention
limits acknowledged.

## 8. Attempts and repair accounting

- Suite run 1: 22/22 PASS (67 checks). Suite run 2: 22/22 PASS,
  byte-identical matrix. **No failed trial, no repair used** (0 of the
  ≤10-minute allowance). One driver design adjustment was made *before*
  any trial ran (owner lock = OS flock instead of an existence flag, so
  crash-restart is honest); it is part of the delivered driver, not a
  repair of a failed attempt.
- Total elapsed ≈29 minutes of the ≤45 cap, including spec fetch,
  grounding reads, build, both suite runs, and this memo.

## 9. Package and scope confirmation

Evidence package: `research_notes/td_fresh_full_manifest_preflight_evidence_20261016/`
— `fresh_manifest.json`, `fresh_supplement.json`, `preflight_driver.py`,
`run_trials.py`, `trial_matrix_run1.json`, `trial_matrix_run2.json`,
per-run trial-namespace hash lists, `live_pre_dispatch_checklist.md`,
and `SHA256_MANIFEST.txt`. Trial namespaces (`trials_run1/`,
`trials_run2/`) are preserved in place. All deliverables are left
**UNCOMMITTED**, exactly as specified.

Scope confirmation: fake transport only; network denied at kernel level
for both suite runs; zero vendor/Yahoo/model/API calls beyond the one
unauthenticated public GitHub spec fetch at intake; zero credits/spend;
zero downloads/installs; zero live limiter/state writes (the live credit
ledger was hash-read only); zero backtest/performance/holdout access;
no adoption or merge; no production or live V5.4 changes; candidate,
supplement-of-record, manifests of record, and the original SPOT8 state
all unmodified.

**Final verdict: FRESH_FULL_MANIFEST_PREFLIGHT_PASS — packet only; ready
for independent review before a separately dispatched live screen under
standing capped authority.**
