# TD ledger compatibility + token-card binding (-07 r1)

**Task:** `QF-TD-LEDGER-COMPAT-AND-CARD-BINDING-20261017-07 r1`
(spec: GitHub Issue #1 comment `6230110894`, fetched via the public API
first and followed exactly; bases: gate base `a82d720`, evidence commit
`3403e7f`).
**Verdict: `LEDGER_COMPAT_AND_CARD_BINDING_PASS_OFFLINE`** — the
candidate is conservative, separate-output, and source-preserving, and
both repeated matrices match. This authorizes **no** live execution.

**TD live remains HOLD regardless of this result.** Two of the three
-06 blockers are untouched by this round, by design: the credential
helper `dynamic_credentials` is absent from this execution environment
(gate 9), and no fresh Basic / good-standing / ≥51-credit account
evidence exists (gate 3). TD live unblocks only on an execution
environment that actually provides the helper plus fresh account
evidence, per the adjudication. This round cured the third blocker
(gate 4's ledger schema generation) as an offline candidate and the
independently found token-card defect — nothing more.

## 1. Ledger compatibility candidate (defect: LEDGER_SCHEMA_GENERATION_MISMATCH)

Source (preserved, read-only throughout): `pilot_harness/credit_ledger.json`,
SHA-256 `7e5ccef0…`, legacy schema `{"day":"2026-10-14","spent":8,
"window":[[ts,1]×7]}`. Consumers pin the reservation schema
`{"reservations":[{"rid","ts","day","weight"}]}` — gate 4's assertions
in `dispatch_gate_r2.py` and `Limiter._load_locked` in `live_driver.py`
are byte-for-byte the same four field checks; the converter targets
exactly that schema.

`ledger_compat.py` (separate output only; refuses an output path equal
to the source path) maps:

- each window entry `[ts, w]` → one reservation
  `{rid: "legacy-<srcsha12>-<index>", ts, day: UTC day of ts, weight: w}`
  — rolling-window content carried record-for-record;
- the day residual `spent − (same-day window sum)` (= 1 for the real
  ledger: spent 8 vs window sum 7) → unit-weight residual reservations
  on the ledger day, so the candidate's day sum equals
  `max(spent, same-day window sum)` exactly — never undercounted;
- conversion is a pure deterministic function of (source bytes, source
  path, target instant): the receipt binds source path + source SHA +
  target instant + candidate SHA (`conversion_receipt.json`, which also
  carries the full per-record mapping table and the before/after source
  hash proof).

Accounting at the pinned target instant 1792213267
(2026-10-17T05:01:07Z, the -06 frozen window start): candidate
`candidate_credit_ledger.json` (SHA-256 `79ff4844…`) holds 8 records;
day sum on the source day 2026-10-14 = 8 (= spent); day sum on the
target day = 0 and active rolling-window weight = 0 — **proven from
timestamps** in the receipt's staleness block (source day ≠ target day;
max source ts 1792001518.58 is ~2.45 days before the target), not by
silently resetting anything. All 8 legacy credits remain in the
candidate under their own day.

Fail-closed validation (suite L08–L14): malformed JSON, wrong schema,
negative/zero weights, negative spent, duplicate window records, future
timestamps, spent below the same-day window sum, and window entries on
an unrelated day all refuse with named codes; replaying the candidate
as a source refuses (`SOURCE_ALREADY_RESERVATION_SCHEMA`, L04);
conversion is idempotent byte-for-byte (L03). Focused cases also cover
same-day residual spent after window expiry (L05), a cross-midnight
active window retained from the previous UTC day (L06 — active weight
3 vs source 2: the residual record conservatively overcounts, never
undercounts), and a stale prior day with contents preserved (L07). The
candidate loads through the real `live_driver.Limiter` on a temp copy
(count 8; a probe reservation at the target instant succeeds) while the
driver refuses the legacy source with `LIMITER_LEDGER_CORRUPT` (L02) —
the mismatch was real, and the candidate is the schema both consumers
read.

## 2. Token-card binding (defect: TOKEN_CARD_WINDOW_DRIFT)

The -06 card (`bcda33d7…`, preserved untouched as a test fixture) is
**marked REJECTED** and was not repaired into a usable token.

`token_card.py` defines the canonical card as derived from the frozen
evidence bytes: run, manifest, evidence digest (= SHA-256 of the bytes
themselves), ledger path, and window are all read from the same bytes;
ISO labels are computed from the epochs they label; the token preview
recomputes the gate's `make_dispatch_token` formula (cross-checked
against the real `dispatch_gate_r2` module in C01). Verification
regenerates the card from the bytes and demands exact equality, naming
the first differing field. Suite C02 reproduces the exact -06 failure —
a card carrying the stale window (both ends −1,200 s) HOLDs at
`make_dispatch_token_inputs.window` — and the raw -06 card document
HOLDs as well. Per-field mutations (run, manifest, evidence digest,
ledger path, window start, window end, token preview, card digest) each
HOLD (C03); a card presented against different frozen bytes HOLDs (C04);
derivation is deterministic (C05). The derived card for the -06 frozen
bytes is published as `derived_token_card.json` for binding proof only
and is stamped NOT token-eligible while gates 3/9 remain blocked.

## 3. Suite, attempts, budget

Focused suite `run_compat_suite.py`: 20 cases / 63 checks. Attempt 0:
19/20 (61/62 checks) — one harness assertion defect in C04 (it demanded
`evidence_digest` as the first differing field; the binding check
correctly reported `card_digest`, which sorts first). The failed matrix
is preserved as `suite_matrix_attempt0_failed.json`; the assertion was
corrected to check the HOLD plus the digest difference directly. This
was the single allowed repair (≈2 min). Final runs, twice under
`unshare -n`: **20/20 cases, 63/63 checks, matrices byte-identical**
(SHA-256 `9b97e653…`). Total elapsed ≈8 min of the ≤30 cap.

## 4. Failure memory

`FAILURE_MEMORY_20261017_07.md` records both failure classes with root
cause, cure, and the standing rule: `TOKEN_CARD_WINDOW_DRIFT` (never
copy a bound field — derive it) and `LEDGER_SCHEMA_GENERATION_MISMATCH`
(a schema mismatch is a migration task with a conservation proof, never
an in-place rewrite or silent reset).

## 5. Scope

Offline / network-denied throughout (suite under `unshare -n`). Zero
credentials in any form; zero account/vendor/model/API calls beyond the
spec fetch; zero installs/downloads/spend; zero writes to the shared or
pilot ledger (source SHA-256 `7e5ccef0…` before and after — L15); no
backtest/performance/holdout/production/trading; no Issue #9; no live
execution; no merge/adoption; no parked-lane reuse. All prior packages
byte-identical; the -06 rejected card preserved as a fixture. Deliverables
in `research_notes/td_ledger_compat_card_binding_20261017_07/`, left
UNCOMMITTED for independent review.
