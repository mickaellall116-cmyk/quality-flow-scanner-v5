# TD Fresh Live Dispatch Gate r2 — Owner Lease Ordering + Credential-Helper Import (2026-10-16)

Task: `QF-TD-FRESH-LIVE-DISPATCH-GATE-20261016-05` r2 (r1 review follow-up:
OFFLINE PARTIAL PASS / LIVE HOLD). Package:
`research_notes/td_fresh_live_dispatch_gate_evidence_20261016_r2/`.
Authoritative specification: Issue #1 comment `6229319362` (chatgpt
2026-10-16T22:30), fetched and read in full via the public API before
any work; verified against Issue #1 — not the Slack relay, not a local
handoff.

## VERDICT: `FRESH_LIVE_DISPATCH_GATE_R2_PASS_OFFLINE`

**32/32 trials and 234/234 recorded checks passed on the final matrix,
twice, under kernel network denial (`unshare -n`), and the two
normalized matrices are byte-identical (sha256 `24c6d730…`).** One
disclosed repair inside the allowance (below). This remains an
**OFFLINE** pass: armed transport construction existed only through
the -04 fake-transport factory seam and the spy wiring; the disarmed
default was never armed against the network. **The capped $0 live
screen did NOT run under this task**; it still requires the separate
adjudicated execution dispatch the spec names, and two confirmations
below are **LIVE-PROCESS-ONLY**.

## What r2 changed (and what it deliberately did not)

New candidate `dispatch_gate_r2.py` (sha256 `932fb2e8…`) beside, never
instead of, the r1 wrapper: every r1 file remains byte-identical
(runner-up pin rechecks below). Gates 1–7 and 10–12 are textually the
r1 logic; the changes are confined to gate 8/9 semantics, a new
phase-2 lease step in `dispatch()`, and receipt/result fields
(`gate_revision`, `owner_lease`, `lease_acquired`). **The pinned -04
driver itself was NOT modified** — its sha256 is still the pin
`5fed4524…` — because gate 6 and the r1 verdict bind that exact file.
The spec's alternative ("an equivalent single-owner handoff with no
unlock window") is what is implemented and proven, as follows.

### Gap 1 — owner lease ordering (spec point 1)

- When all 12 gates pass evaluation, the wrapper now acquires a
  nonblocking exclusive `flock` on an **owner-lease artifact** —
  `<namespace-abspath>.dispatch_lease`, a sibling file of the
  namespace, never inside it, so the pinned Runner's namespace census
  is untouched. The lease content binds run id + manifest digest +
  evidence digest + namespace absolute path; an existing lease whose
  identity binding disagrees refuses `OWNER_LEASE_BINDING_MISMATCH`
  and is never overwritten.
- Acquisition happens **before** the PASS receipt is written and
  before any transport is constructed. Contention amends gate 8 to
  `FAIL / OWNER_LEASE_HELD` on the receipt and the decision becomes
  HOLD — a competing owner can no longer pass gate 8 while another
  process holds the lease.
- Immediately after acquisition, gate 8's invariant is re-probed
  (clean namespace, zero prior attempts, own identity) while the
  lease is held; any change since evaluation amends gate 8 to FAIL
  and nothing arms.
- The lease fd is held **continuously** through receipt fsync,
  transport construction, Runner construction (which takes the
  Runner's own `owner.lock` flock inside that window), the whole
  run, and `runner.close()`; it is released only afterwards (and on
  every non-PASS return and exception path). From lease acquisition
  to Runner close there is **no unlocked interval**: a competing
  flow is refused by the lease before the Runner exists, and by the
  lease and the Runner flock afterwards.
- Replay protection is unchanged and additive: the fsync'd exclusive
  PASS receipt is still written before arming and still doubles as
  the replay guard; account mode is still derived from that receipt.

### Gap 2 — credential-helper existence (spec point 2)

Gate 9 no longer treats the helper as attested evidence. After the
r1 credential-boundary checks (exact ref `custom.twelvedata`, exact
helper name, exact allowed hosts, no material read, pilot pin,
no-key-material scan), it now performs a **preflight import** of the
exact module `dynamic_credentials`, verifies
`url_with_surrogate_query_param` exists and is callable, and
verifies the allowed-host binding surface (at least two positional
parameters and an `allowed_hosts` parameter or `**kwargs`) via
signature inspection — **without invoking the helper, without
resolving/reading/logging any credential material, and without
network**. Failures are distinct pre-arm refusals:
`CREDENTIAL_HELPER_UNAVAILABLE` (import fails),
`CREDENTIAL_HELPER_CALLABLE_MISSING` (missing or non-callable),
`CREDENTIAL_HELPER_BINDING_MISMATCH` (wrong signature/binding).

**Plainly stated (spec point 4):** in this sandbox
`dynamic_credentials` does not exist as an importable module, so
against the real import path gate 9 now returns
`CREDENTIAL_HELPER_UNAVAILABLE` and the wrapper HOLDs — the trial
`H05_helper_real_import_absent` proves exactly that fail-closed
behavior on the genuine path. The positive preflight path is proven
offline against a **stubbed module surface** (in-process seam and a
real importable stub package used by the contention processes), with
an invocation counter proving the gate never calls the helper. The
helper's presence and identity in the future **live execution
process** — where the platform injects it — remains
**LIVE-PROCESS-ONLY to confirm**; if it is absent or different there,
this gate will refuse, by design.

### Point 3 — real-process contention (trial C01)

Two genuine OS processes, not one: a holder process runs the full
wrapper (stub helper importable) and blocks inside its transport
factory — lease held, PASS receipt durable, Runner not yet
constructed. A contender process then runs the full wrapper for the
same namespace identity. Proven facts: holder's independent probe fd
was refused the flock at the construction instant
(`lease_held_at_construction = true`); the contender's receipt reads
`HOLD`, gate 8 `FAIL / OWNER_LEASE_HELD`, the other 11 gates PASS,
**zero** factory calls, zero transports constructed, no lease
acquired, namespace never created, ledger hash unchanged. The holder
then completes: `COMPLETE`, 51 calls, 51 reservations, helper
invocation count 0, and the lease is re-acquirable after it exits
(released, not leaked). A second process can therefore never obtain
PASS or construct an armed transport while the lease is held.

### Point 4 — helper negatives

`H01` import failure via seam → `CREDENTIAL_HELPER_UNAVAILABLE`;
`H02` wrong module (no attribute) and `H03` wrong callable
(non-callable) → `CREDENTIAL_HELPER_CALLABLE_MISSING`; `H04` callable
with no allowed-host binding → `CREDENTIAL_HELPER_BINDING_MISMATCH`;
`H05` genuine import absence (see above). Each is the **only** failed
gate, with zero transport construction, zero namespace creation, zero
ledger change, and zero lease artifact. The positive fake-helper
wiring case (green trials G01/G02/G04) runs under the same network
denial with the helper's invocation counter at zero.

## Trials (32 = r1's 25, verbatim, + G04 + H01–H05 + C01)

- G01 green dry-run; G02 green fake dispatch (51 calls in manifest
  order, 49 `COMPLETED` + 2 `CLOSED_DAY_EVIDENCED`, 51 reservations)
  + replay refusal; G03 default-factory spy wiring (exactly one armed
  construction, after PASS durable); G04 lease lifecycle (artifact is
  a sibling, binding matches identity, released after dispatch).
- F01–F22: the r1 single-gate failures, token mismatch, evidence
  tamper, live-mode seam refusal, and direct-arm boundary — unchanged.
- Per-run safety flags: the real pilot ledger and the old SPOT8 state
  tree are reported unchanged by both final matrices, and their
  hashes were independently re-verified for this memo (below).

Failed attempts, preserved verbatim: the first post-build run 2
failed exactly one trial (`G04`, 31/32, matrix sha256 `38d8ba41…`)
on a **harness** defect — a check compared the lease's absolute path
against the trial root's relative prefix (run 1 had used an absolute
/tmp root, which is why it passed there). One-line harness repair
inside the repair allowance; the failed matrix and its full trial
tree are preserved as `dispatch_matrix_attempt0_failed.json` /
`trials_attempt0_failed/`, and both final runs were then executed
fresh. A service restart then interrupted the first post-repair
run-2 mid-flight; its partial tree was deleted as an incomplete
artifact of the interruption (the completed attempt-0 failure above
is the preserved failed attempt of record) and run 2 was re-executed
in full.

Tree hash lists (`trials_run1_hashes.txt`, `trials_run2_hashes.txt`,
267 files each) are per-run records: 41 files differ across runs,
all in the path/digest-embedding class — receipts (which embed the
evidence digest binding run-root absolute paths), the C01 evidence
files, lease artifacts (binding embeds the namespace absolute path),
and one stray `.pyc`. No lifecycle, state, or ledger content differs;
the normalized matrices are the byte-identical determinism object.

## What remains LIVE-PROCESS-ONLY (plainly)

1. The platform credential helper's presence in the live execution
   process (above): gate 9 will refuse there until it imports.
2. The real account figures, the independently applied dispatch
   token, and the same-day $0 terminal evidence — unchanged from the
   live dispatch checklist; the r2 addendum beside this memo records
   the two amended steps (lease-first ordering, helper preflight).

## Scope confirmation

Offline only: no vendor, Yahoo, model or API call beyond the spec
fetch; no credential resolution (the helper was imported for surface
inspection only in stub form, and never invoked); no spend/credits;
no installs/downloads; no live writes (the real pilot ledger and old
SPOT8 state were hash-read only and are unchanged); the armed
candidate was constructed only against fake transports in fixtures,
exactly as in -04/r1; no backtest, performance, holdout, production,
trading or Issue #9 work; no merge/adoption; no parked-lane reuse;
r1 and all prior packages byte-identical (r1 gate `77c686ca…`,
-04 driver `5fed4524…`, supplement `3cbdbf63…`, real pilot ledger
`7e5ccef0…` — all re-verified at close).

Entry decision remains: **no direct arming entrypoint exists**. The
only arming path is `dispatch_gate_r2.dispatch()` with all 12 gates
green including the helper preflight, a valid adjudicator token, the
owner lease held, and the PASS receipt durable first — and even then
the run is the driver's one-attempt, stop-on-first-error flow.
