# Errata — QF-TD-V2-SPOT-BATCH-PREFLIGHT-20261014-12 r1

**Task:** QF-TD-V2-SPOT-PREFLIGHT-ERRATA-20261014-13 r1 (ChatGPT, with the
-12 SCOPED PASS; permanent adjudication: Issue #1 comment 6173739464)
**Date:** 2026-10-14
**Scope:** Documentation only. One immutable errata note; no rerun; no
candidate / manifest / contract / code / pin change; no live-state access;
no vendor/auth call; no credit/spend; no candidate merge; no
baseline/performance content.

**Record under correction:**

- Candidate: `b18db3ce25f3014d11847ba1ac92f488a994022e`
  (branch `refs/heads/td-v2-spot-candidate-20261014`)
- Report commit: `b5c30fdb1633592c4b6ee9b157b5b1209b22d428`
  (`research_notes/TD_V2_SPOT_BATCH_PREFLIGHT_20261014.md` + evidence dir
  `research_notes/td_v2_spot_batch_preflight_evidence_20261014/`, integrated
  to main via merge `07f24d7`)

---

## Erratum 1 — Fall-case label (date and year)

In `research_notes/td_v2_spot_batch_preflight_evidence_20261014/subset_proof.json`,
the `case` field for **REQ-SPT-03** and **REQ-SPT-04** reads:

> "DST-fall week (EST resumes 2026-11-01)"

That label is wrong on both year and date. The corrected label is:

> **"EST resumed 2025-11-02"**

The request window itself — 2025-11-03 → 2025-11-07, the first full week
after EST resumed — was and remains correct and is unchanged. (The -12
report's own table says only "DST-fall week" and carries no wrong date.)
The proof file is immutable evidence and is **not** modified; this note is
the correction of record.

## Erratum 2 — Inherited v1-era non-executable prose in `adapter_contract.json`

The candidate's contract
(`research_notes/td_acquisition_adapter_preflight_evidence_20261013/adapter_contract.json`
in candidate `b18db3ce`) carries three prose fields inherited from the v1
era. They are descriptive text only — **non-executable** — and where they
differ from the candidate's bindings and code, the bindings and code govern:

1. **`adapter.status`** — "DESIGN ONLY — not implemented. No HTTP client
   exists in the candidate. Implementation is a separate,
   separately-authorized step; this contract is the pinned spec it must be
   built and reviewed against." Inherited from the pre-implementation v1
   contract. Not true of this candidate: it contains the implemented
   adapter/driver, pin-verified and exercised by the suites recorded in
   -12 (adapter 41/41, pinned-integration 16/16, collector 19/19).
2. **`identity_semantics.venue_identity`** — the parenthetical example
   "(NASDAQ/XNAS, NYSE/XNYS, Cboe BZX/BATS)" uses the v1-era operating MIC
   `XNAS`. Executable venue truth is each request's manifest-pinned
   `{exchange, mic_code, currency}` under Manifest V2 — for Nasdaq listings
   the segment MICs adjudicated in the -10/-11 record (XNGS / XNMS / XNCM) —
   enforced by the collector against receipt meta, fail-closed.
3. **`limiter_binding.state_path`** — the note "…the SAME persisted ledger
   the integration tests exercised and Stage-0 used (2 credits spent
   2026-10-10). One ledger for every Twelve Data run; no per-run or
   per-adapter ledgers." A Stage-0-era historical note, retained as
   description; it is not an executable statement about this candidate's
   run state.

**Executable truth:** the contract's `binds` object — manifest →
`TD-ACQUISITION-MANIFEST-V2-20261014` (canonical_sha256
`4d5b7a560d9d222d8012cd674fc065de3ef014c2adeb4034e39f8efb99aed646`),
collector pin `bd003c3cd5866172c04b0165d6ee60ec16be8487f28e90b4e6e1df046f8d489b`
— together with the pinned implemented driver/adapter code in the
candidate tree. No contract bytes were changed by this note.

## Erratum 3 — Merge status clarification

The **candidate `b18db3ce` is NOT merged.** It exists only on
`refs/heads/td-v2-spot-candidate-20261014` and is not an ancestor of
`main` or `origin/main` (verified 2026-10-14 for this note). What **was**
integrated to main is the -12 **report and evidence** (commit `b5c30fd`,
merged `07f24d7`). Any wording in the -12 record that could be read as the
candidate itself landing on main should be read as: report/evidence on
main; candidate on its branch, unmerged.

---

## Effort and stop

Elapsed effort: ~2 minutes (13:28–13:30 EDT, VM clock), inside the
15-minute budget; no repair extension used. Zero vendor/auth calls, zero credits,
zero spend, no live-state access, no rerun.

**Status after errata: HOLD.** REQ-SPT-01..08 are not dispatched.
Dispatch requires Mike's direct authorization for exactly 8 free-quota
credits max, one attempt each, no retry/pagination.

— Muse
