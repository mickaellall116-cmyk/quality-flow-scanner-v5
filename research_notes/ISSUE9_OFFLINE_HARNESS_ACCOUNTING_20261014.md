# Issue #9 offline harness accounting repair — QF-ISSUE9-OFFLINE-HARNESS-ACCOUNTING-20261014-05 r1

**Verdict: OFFLINE_HARNESS_PASS** (synthetic enforcement only — see §4)

Spec: ChatGPT tasking, Slack `#qualityflowscaner` TS `1792024960.708879`,
pointing to GitHub Issue #1 comment `6181708698` (independent review of the
-04 candidate at commit `9a7e12e`: four enforcement gaps confirmed repaired,
verdict **HOLD** on complete post-dispatch resource accounting). The comment
governs where this memo and the tasking brief differ. Repair executed
2026-10-15 ~00:50–01:04 UTC, inside the ≤30-minute box. **No repair pass was
needed**: the amended suite passed in full on its first run (0 of the
≤10-minute repair allowance used; the suite was then run a second time for
byte-stability, §3).

**What this PASS means — and does not mean.** Identical in scope to -03/-04:
the enforcement code behaves correctly against a scripted fake transport
under adversarial fixtures. It does **NOT** authorize a first live model call
or the Arm A/B swarm comparison. Actual execution remains blocked pending
ChatGPT's acceptance of this corrected harness, a separate Mike GO, and
same-day $0 pin/quota evidence. Nothing here is wired into any live path;
`bin/or_chat.py` was not touched, per spec.

## 1. The HOLD items and their repairs

All repairs are in the isolated candidate only:
`research_notes/issue9_offline_harness_20261014/tools/offline_harness.py`.

**(1) Rejection consumed the response before usage was captured → capture
first, reject second.** `_validate_and_record` previously validated
HTTP/fallback/model/version/cost *before* parsing usage, so a response with
valid usage but a semantic defect stopped with no billed-token fields even
though the provider may have reported (and charged) them. The method is
restructured into a fixed order: **(i)** parse and validate the usage object
and compute billed tokens (input+output+reasoning); **(ii)** classify the
cost evidence (VERIFIED_ZERO / NONZERO / UNKNOWN with MISSING / NON_NUMERIC /
NON_FINITE); **(iii)** build the accounting field-set shared by *every*
outcome of the call; **(iv)** only then pick the first failing semantic check
— in the same order as -04 — as the rejection, with the rejection reason
preserved on the same record that carries the accounting. Consequences, all
fixture-proven: a rejected call's valid usage is counted **exactly once**
(it lands in `billed_total`, because the provider really consumed those
tokens); if usage is invalid/absent **or** cost is unverifiable, the record
additionally carries `usage_or_cost_status:
"UNKNOWN_INTERRUPTED_CALL_USAGE_OR_COST"` and `reconciliation_required:
true` — the unknown component is never silently dropped and never rewritten
as exact. The $0 and counted-usage values on the accepted / empty-content /
overrun / wall-quarantine records remain evidence-backed: those branches are
reachable only with valid usage and a verified exact-zero cost. *Proof:
F34 (version mismatch + valid usage), F36 (HTTP 500 + valid usage),
F37 (fallback + valid usage), F35 (missing cost + valid usage).*

**(2) Timeout was zero-filled → UNKNOWN, generalized to every interrupted
dispatch.** The `FAILED_TIMEOUT` outcome previously wrote `billed_tokens=0`,
asserting a provider consumption the harness cannot know. A timeout now
records `billed_tokens: null`, `cost_usd: null`,
`cost_evidence_status: "UNKNOWN"`,
`usage_or_cost_status: "UNKNOWN_INTERRUPTED_CALL_USAGE_OR_COST"`, and
`reconciliation_required: true`, exactly once, with no retry and no resend.
The same treatment covers the previously unhandled non-timeout transport
exception path: a `ConnectionError`/`OSError` after dispatch now produces a
`FAILED_TRANSPORT_EXCEPTION` outcome with identical UNKNOWN accounting
(exception type recorded) instead of propagating with no outcome at all.
`Ledger.billed_total` sums only authoritatively-known integer usage, so an
UNKNOWN record contributes nothing — not because it was zero, but because it
is unknowable locally. This generalizes the -04 F33 crash treatment
(`UNKNOWN_INTERRUPTED_CALL_COST` for a dispatch with no outcome) to every
post-dispatch path where accounting cannot be authoritatively determined.
*Proof: F38 (timeout), F39 (connection failure), F14 (gained the UNKNOWN
assertions; stop code, single dispatch, single outcome unchanged).*

**(3) Resume stayed blocked only for crash orphans → blocked for any
unreconciled call, cleared only by evidence.** `run()` now refuses any new
dispatch while `Ledger.reconciliation_outstanding()` is nonempty (stop code
`RECONCILIATION_REQUIRED`), and `resume_state()` classifies such a ledger
`RECONCILIATION_REQUIRED` (after CORRUPT and ORPHANED, whose meanings are
unchanged). The block clears **only** via a new explicit ledger record type,
`reconciliation`, appended through `Ledger.append_reconciliation(...)`:
it requires an `evidence_ref` (absent → `RECONCILIATION_EVIDENCE_MISSING`,
nothing recorded), verifies the chain before appending, resolves exactly one
(arm, seed, call_index), and stores any resolved figures on the
reconciliation record itself — the original outcome is immutable and is
never rewritten or zero-filled retroactively. *Proof: F35 — resume refused
with zero dispatches while unresolved; a no-evidence reconciliation is
refused; a reconciliation naming the wrong call does not clear the block;
the correct evidence-backed record clears it and the resumed run completes,
with each call's tokens counted exactly once (total 2,500 = 1,250 rejected
+ 1,250 resumed).*

## 2. Path audit (every outcome path in `offline_harness.py`)

Post-dispatch paths — all now carry the shared accounting field-set:

| Path | Stop code | Usage handling after -05 |
|---|---|---|
| HTTP != 200 / non-dict body | `HTTP_NOT_200` | valid usage counted once; invalid/absent → UNKNOWN + reconciliation |
| `fallback_used` | `FALLBACK_DETECTED` | same |
| Response model != pin | `MODEL_MISMATCH` | same |
| Version absent / pin version absent | `MODEL_VERSION_UNVERIFIABLE` | same |
| Version substituted | `MODEL_VERSION_MISMATCH` | same; both versions recorded |
| Cost missing / non-numeric / non-finite | `COST_EVIDENCE_MISSING` / `COST_EVIDENCE_INVALID` | valid usage counted once; cost UNKNOWN + reconciliation |
| Cost numeric nonzero | `NONZERO_COST` | usage counted; cost recorded at its reported value |
| Usage absent / unmetered / negative / inconsistent | `MISSING_USAGE` / `UNMETERED_REASONING` / `NEGATIVE_USAGE` / `INCONSISTENT_USAGE` | usage UNKNOWN + reconciliation (cost still recorded as classified) |
| Empty content | `EMPTY_CONTENT` | usage counted (reasoning counted, never substituted); cost verified $0 |
| Overrun vs reservation/cap | `OVERRUN` | usage counted; content quarantined |
| Wall overrun at acceptance | `CEILING_WALL` | usage counted; content quarantined |
| Accepted | — (`RECORDED`) | usage counted; cost verified $0 |
| Timeout | `TIMEOUT` | usage + cost UNKNOWN (null) + reconciliation; one record, no retry |
| Transport exception (new outcome) | `TRANSPORT_EXCEPTION` | identical UNKNOWN treatment |
| Crash after response (no outcome) | `ORPHANED_LEDGER` on resume | unchanged from -04: `UNKNOWN_INTERRUPTED_CALL_COST` + reconciliation-required preserved in the stop record |

Pre-dispatch stops (`LEDGER_CORRUPT`, `ORPHANED_LEDGER`,
`RECONCILIATION_REQUIRED`, price-evidence stops, `LEDGER_DISCONTINUITY`,
`CEILING_CALLS`, pre-dispatch `CEILING_WALL`, `QUOTA_EXHAUSTED`,
`QUOTA_RESET_UNVERIFIED`, `PROMPT_CONTAMINATION`, `ROLE_INVALID`,
`CEILING_TOKENS`) fire before any transport invocation, so no provider
consumption exists to account for; they are unchanged.

## 3. Fixture results — 42/42 matched, twice, byte-identical

Complete suite = the 36 -04 fixtures (expectations preserved; F14's checks
strengthened as noted in §1) + 6 new -05 adversarial fixtures (F34–F39),
covering the spec's fixtures (a)–(d) one-for-one, with (c) split into its
HTTP and fallback halves and (d) into timeout and connection failure. Run
twice end to end; both runs exit 0 with **42/42 matched**, and the outputs
are byte-identical across runs:

| Output | sha256 (both runs) |
|---|---|
| `fixtures/fixture_results.json` | `2fb1a568221d67847cf7ace68d56b2802e07ec9af28064f2fcb3f1150bde1fa1` |
| `evidence/f01_clean_control_ledger.jsonl` | `82a7497ded34cb28dfd36aea9a78b8b07715a0050ae6a1639e7318fa4badff37` |
| `evidence/f01_clean_control_summary.json` | `c129547de4b646f478a66372c0a8a7bee290827bb383900fe16f5e0300072e1b` |

The F01 clean-control hashes are **unchanged from -03 and -04** — the
compliant path's behavior did not move across any of the three repairs.
Per-fixture proof, one line each: F34 version substitution + valid usage →
`MODEL_VERSION_MISMATCH`, billed 1,250 counted once, cost $0 known, no
reconciliation owed; F35 missing cost + valid usage →
`COST_EVIDENCE_MISSING`, billed 1,250 counted, cost UNKNOWN +
reconciliation-required, resume blocked until the evidence-backed
reconciliation record, then completes; F36 HTTP 500 + valid usage →
`HTTP_NOT_200`, billed 1,250 counted once; F37 fallback + valid usage →
`FALLBACK_DETECTED`, billed 1,250 counted once; F38 timeout → `TIMEOUT`,
usage/cost UNKNOWN (null, never 0), reconciliation-required, 1 invocation,
0 resends, resume `RECONCILIATION_REQUIRED` with 0 dispatches; F39
`ConnectionError` → `TRANSPORT_EXCEPTION`, identical UNKNOWN treatment.

## 4. What did NOT change; scope confirmations

- The frozen protocol, the prep package, and the -02 preflight guard are
  untouched. All -03/-04 enforcement semantics not named in the HOLD are
  preserved: preflight-first, empty-content stop with reasoning counted and
  never substituted, reservation + overrun quarantine, exact version
  equality, strict cost evidence for *acceptance*, acceptance-time wall
  cap, pre-dispatch chain verification, crash-orphan accounting, no
  retries, quota/reset evidence rules, seed order, prompt registration.
  The only existing expectation set amended is F14's, and only by *adding*
  the UNKNOWN-accounting assertions the -05 spec requires (its `billed_0`
  check still passes — now because an UNKNOWN record contributes nothing
  known, not because a zero was written).
- Fake transport only; **zero** provider/model/API calls, **zero** spend,
  **zero** installs, **zero** live/production changes. The fixture runner
  patches the socket layer to raise before anything runs (F00 proves it).
- Files changed, all inside the isolated package plus this memo:
  `tools/offline_harness.py` (capture-before-reject restructure, UNKNOWN
  timeout/transport-exception accounting, reconciliation gate + record
  type, `billed_total` hardening), `tools/run_fixtures.py` (F34–F39, F14
  checks, task label), `fixtures/fixture_results.json` (regenerated),
  `SHA256_MANIFEST.txt` (regenerated). F01 evidence files regenerated
  byte-identical.
- Not touched, per spec: `bin/or_chat.py`, the live V5.4 harness, Yahoo /
  production anything, Issue #9 treatment outputs, any provider. The live
  `v54_forward_harness.py` was hash-checked only, before and after:
  `dc3ee392c808aa2e52d468cad0020d8fe85b6f2bda0adc656304193563cba0c8`
  (the deployed feed-repair r2 candidate) — unchanged.

## 5. Defects, repair effort, open items

- No open defect from the HOLD remains: both load-bearing items (usage
  capture ordering; timeout zero-fill) are repaired and fixture-proven,
  and the brief's generalization requirements (all rejection/timeout paths
  consistent with the F33 pattern; resume blocked while any
  interrupted/unreconciled call is outstanding; reconciliation clearing
  only via an explicit evidence-backed record) are implemented and proven
  by F35/F38/F39.
- Repair minutes: ~14 minutes total task time (~00:50–01:04 UTC) including
  spec fetch (Slack + Issue #1 comment), source audit of every outcome
  path, the code restructure, fixture authoring, and two full suite runs.
  The ≤10-minute repair-pass allowance is unused — the amended suite
  passed on its first run.
- Known synthetic-only limits (carried from -03/-04, unchanged): quota
  fixtures inject small caps on the same code path as the 50/day default;
  wall time comes from the injected clock; a real provider's timeout may
  in practice arrive with a partial response or a later usage report —
  the harness's contract for that case is exactly what F35/F38 prove:
  UNKNOWN + reconciliation-required until authoritative evidence lands in
  a reconciliation record.

— Muse
