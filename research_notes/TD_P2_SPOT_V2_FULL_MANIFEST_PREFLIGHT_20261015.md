# QF-TD-P2-SPOT-V2-FULL-MANIFEST-STATE-PREFLIGHT-20261015-05 r1

## Verdict

**P2_SPOT_V2_FULL_MANIFEST_PREFLIGHT_HOLD**

The unchanged candidate collector **cannot perform the copied-state
v1 → v2 transition** the spec asked to prove. Started from a byte-identical
copy of the actual SPOT8 acquisition state, a full-manifest run with the NL
supplement returns `HOLD (persistent): HTTP 400 for REQ-SPT-07` with zero
transport calls and zero writes. This is spec point 3's explicit branch —
"If the unchanged candidate cannot support this transition honestly, stop
and document the design gap" — not a malfunction: the candidate behaves
exactly as its code dictates, and every surrounding component (receipts,
classifier, calendar, restart machinery) is proven sound. The gap is one
missing step: **no entry point derives a closed-session classification from
durable rejected evidence, and a HOLD state has no re-entry path.**

This verdict authorizes **no vendor call**, adopts or merges nothing, and
changes no standing fact: **P2 v1 remains UNMET, SPT08 remains NOT
ATTEMPTED, TD feed qualification / corrected performance remain HOLD.**
Zero real/vendor/model calls, zero credits/spend, zero live state/limiter
writes occurred. The original SPOT8 state directory was read-only throughout
(all hashes identical before and after).

## 1. Frozen set and environment (spec point 1)

All -04 pins recomputed from bytes and matched: collector `ab254c3` /
`b683d277…`; NL supplement `9c712330…` binding canonical manifest
`748ca957…`; manifest file `ddff040f…` (exactly the frozen eight-request
SPOT8 manifest — no rewrite); REQ-SPT-07 digest `a259901e…`; REQ-SPT-08
digest `f547d8fe…`; mechanism `1b83cdcd…`; `pandas_market_calendars 4.5.1`;
`validate_manifest == []`.

Environment disclosure: `/tmp/tdqual/venv` was absent at start and was
rebuilt exactly by the qualified download-hash-then-`--no-index` procedure
(the accepted -01/-04 reproduction path): all 11 wheel hashes identical to
the qualified records, rebuilt `pip freeze` identical to the qualified
freeze, CPython 3.12.3, no substitution. Records in the evidence package.

## 2. Original state inventory (spec point 2)

`research_notes/twelve_data_stage0/snapshots/acquisition_state_spot8/`
(read-only): 11 files — `collector.lock` (empty), `lifecycle.jsonl` (34
events), `manifest_binding.json` (`{"sha256": "748ca957…"}`),
`pilot_state.json` (status HOLD, hold_reason "HTTP 400 for REQ-SPT-07",
attempts 7, credit_reservations 7, completed SPT01–06), receipts
SPT01–06 (`.json`), and `REQ-SPT-07.rejected.bin` (180 bytes, `3339c341…`).
Lifecycle: 7× CREDIT_RESERVED, 7× STARTED, 6× RECEIVED, 6×
CONSTRUCTION_HOLD, 6× COMPLETED, 1× ERROR_EVIDENCE (sha = preserved body
sha), 1× HOLD. No SPT07 receipt; no SPT08 artifact of any kind. Full
per-file hashes: `state_inventory_original.json` in the package.

## 3. The transition attempt (spec point 3) — GAP

Suite (9 cases, twice, byte-identical; `preflight_results_run{1,2}.json`):

| Case | Result |
|---|---|
| `freeze_candidate_set` | PASS 11/11 |
| `original_state_inventory` | PASS 12/12 |
| `copy_fidelity` | PASS — copy hashes == original hashes |
| `receipts_revalidate_in_copy` | PASS 5/5 — SPT01–06 `_verify_receipt` all `(True, "ok")` in a copy; side effect recorded (below) |
| `transition_attempt_full_manifest` | PASS 10/10 — outcome `HOLD (persistent)`, **0 transport calls**, 0 dispatched/reused/evidenced, lifecycle + pilot-state bytes unchanged, no SPT08 artifacts |
| `transition_restart_again` | PASS 3/3 — second run on the copy: same persistent HOLD, 0 calls, bytes still unchanged |
| `classifier_direct_proof_on_preserved_evidence` | PASS 9/9 — pure `_classify_closed_session` on the preserved body + actual REQ-SPT-07 returns the full calendar proof (`2026-07-03: closed`, lib 4.5.1, mechanism pin, digest recomputes); tampered-body / wrong-status / no-supplement controls all return None; classifier wrote nothing |
| `synthetic_control_downstream_machinery` | PASS 5/5 — synthetic fresh state (clearly not the copied v1 state): in-run classification, then restart reuses 6 + evidences 2 with 0 calls |
| `original_state_untouched_final` | PASS — original hashes unchanged |

**Why the transition cannot happen (empirical + code):**
`_run_locked()` returns the persistent-HOLD summary before receipt reuse,
the evidenced-reuse branch, or any dispatch; `_reconcile_…` early-returns
on HOLD; `_classify_closed_session`'s only caller is `_handle_response`
(fresh transport responses only); the CLI exposes no derivation mode; the
state carries no version field. Deriving anyway would require hand-writing
a `CLOSED_DAY_EVIDENCED` event and flipping HOLD → ACTIVE — the fabricated
state transition the spec forbids. It was not done. Full analysis, plus
what a future candidate change would need (derivation entry point,
provenance emission, credit integrity at reservations 7 → 8, fail-closed
preservation of the v1 HOLD record): `design_gap_analysis.md`.

**Secondary finding:** receipt verification is not read-only —
`_verify_receipt` → `_validate_bars` emits one `CONSTRUCTION_HOLD`
lifecycle event per 1h receipt (6 appends observed in a probe copy; pilot
state and receipts untouched). A pre-repair driver run surfaced this when
the probe shared the transition copy; the repair (driver-only, ~4 min,
within the single ≤10-min allowance) isolated the probe and now asserts
the side effect exactly. No candidate bytes were changed at any point.

## 4. Spec points 4–6 — not run, by the spec's own rule

With no honestly derivable v2 state, the SPT08-only full-manifest run
(point 4), the SPT08 outcome matrix in the derived state (point 5), and
derived-state restart/crash/collision controls (point 6) **cannot be
executed without fabricating state** and were not run. What stands instead:
the restart control executed against the copied v1 state itself (§3), and
the SPT08 outcome/lifecycle matrix remains proven at -04 scope in fresh
state. The fake-call ledger for this preflight: transition attempts 0
calls; synthetic control 8 fake dispatches (exact in-order list asserted);
real transport calls 0 (`transport_call_accounting.json`).

## 5. Original-vs-derived mapping

No derived state exists. `original_vs_derived_mapping.json` records every
original file with original == copied == post-attempt sha256 and
disposition "unchanged", and states this explicitly. The v1 HOLD record is
retained byte-for-byte — in the original (untouched) and in the copy
(untransitioned).

## 6. Scope confirmation

Fake transport + in-process socket/DNS denial only; zero vendor/API/model
calls; zero credits/spend; zero live state/limiter writes (isolated temp
ledgers only); no installs beyond the disclosed exact-lock disposable
environment rebuild; no merges, no protocol adoption, no backtests, no
production or live V5.4 changes; candidate, supplement, manifest, and the
original SPOT8 state all unmodified. Deliverables left uncommitted in the
worktree.

**Final verdict: P2_SPOT_V2_FULL_MANIFEST_PREFLIGHT_HOLD — the full-manifest
execution shape is blocked on a precisely documented design gap (missing
derivation entry point + terminal HOLD), pending a separately designed,
reviewed, and adopted candidate change. A PASS was not available honestly,
and none was manufactured.**
