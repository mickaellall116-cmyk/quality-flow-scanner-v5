# Canonical Reconstruction — FROZEN RULES
**Date:** 2026-09-28
**Status:** FROZEN — pending Claude audit, ChatGPT review, Mike sign-off. NO BUILD AUTHORIZED YET.
**Owner:** Mike
**Supersedes:** `CANONICAL_RECONSTRUCTION_PLAN_20260928.md` §0 and §9 (per owner directive 2026-09-28)

This document freezes every remaining implementation choice for rebuilding the
canonical V5 environment from the six surviving spec documents. It is written so
that a competent engineer who has never seen the historical results could
implement the rebuild deterministically from this file plus the six docs.

No production/live V5.4 file may be changed by this work. Rebuild code lives in
`research_notes/canonical_rebuild/` only.

---

## §0. Original-machine recovery — CANCELLED by owner

Plan §0 (read-only original-machine search) is cancelled per Mike's directive
2026-09-28: the canonical files were created on the ChatGPT-side workflow and
never pushed to GitHub, so there is no strong reason to expect them on this
machine. Proceed directly as a **reconstruction**. Whatever the rebuild produces
is labeled **reconstructed canonical replica**, never "recovered original."

---

## §1. Frozen source anchor

- Repository tree anchor for candidate-pool sources: commit
  `de01ff70a13e680c5468ae5e6e81177c981832e0` (parent of first canonical-doc
  commit `e77bb16`). Do NOT source symbols from current main.
- Specification set (only these six docs are canonical spec):
  `canonical_baseline/ENGINE.md`, `LONEWOLF_RERUN.md`, `PIT_FEATURES.md`,
  `PORTFOLIO.md`, `REBASELINE.md`, `UNIVERSE.md`.

---

## §2. Layer-1 oracle — PRE-RUN structural/specification checks (visible)

These invariants must hold before any performance comparison. Tolerances frozen here.

### Universe / data
- Candidate pool: **272** names exact.
- Rankable in 2023-06-30→2023-09-30 ADDV window: **229** exact; unrankable: **43** exact.
- Top-120 cutoff: #120 DVN ≈ $375.7M/day, #121 DAL ≈ $373.2M/day (±2% on dollar values; identities exact).
- Post-cutoff listing candidates: **15**; admitted **11** (ARM, BMNR, CRWV, DRAM, GEV, GLXY, NBIS, RDDT, SNDK, SPCX, TEM); rejected **4** (CORZ, NNE, RBRK, UMAC) — identities exact.
- Final universe: **131** exact.
- 4H cache target: **137** symbols = 131 universe + 6 overlay outsiders (identities from docs).
- Effective 4H history ≈ 2023-10-26→2026-09-24 (start within ±5 trading days; any divergence recorded with cause).
- Session labels 09:30 / 13:30 ET; exactly one bar on NYSE early-close days.

### Signal layer
- Raw V5.4 candidates: **4,127** exact (Gate E).

### Portfolio-decision layer
- Skip funnel: **622** busy / **744** slot-rank / **2,387** heat / **374** accepted — exact (Gate F).
- Max concurrent open: **6** exact; open at sample end: **6** exact.

---

## §3. Layer-2 oracle — SEALED post-run forensic checks

Historical performance outcomes live ONLY in the sealed file
`research_notes/CANONICAL_RECONSTRUCTION_SEALED_ORACLE_20260928.json`
(SHA-256 recorded in §11). The builder must not open it until the single locked
run completes and Layer-1 checks pass. Verify the hash before unsealing.

Frozen tolerances (all must be met; any miss is a finding, never tuning permission):
- Headline E: −0.0013 ± 0.05 R/trade; win 39.8% ± 3pp; PF 1.00 ± 0.10.
- Max DD: −40.7R ± 10R; total return negative and |return| < 5%.
- Cost ladder strictly decreasing in cost (25bps E > 50bps E > 75bps E > 100bps E),
  each rung within ±0.05R of documented value.
- Year splits: 2024 E < 0 < 2025 E and 2024 E < 0 < 2026 E; each within ±0.10R.
- Concentration: ≥6 of the 10 documented top-trade identities appear in the
  rebuild's top-15 trades by R.
- 14-name overlay: n = 151 exact; E within ±0.10R of +0.4489; PF within ±0.15.

---

## §4. The seven ambiguities — FROZEN

Basis codes: EXPLICIT = pinned by surviving docs; DERIVABLE = follows from an
explicit rule with no meaningful discretion; JUDGMENT = frozen choice, recorded
as such, never revisited after the run.

### A1. Heat numerator after partial TP1 — FROZEN
`heat = Σ_over_open (remaining_shares × (entry − stop)) / marked_equity`,
where `marked_equity` is equity marked at the last 4H close. After the 50% TP1
scale-out, the position contributes half its original planned risk (the runner
retains the structural stop per ENGINE.md).
Basis: DERIVABLE ("sum of current position risks" + "runner retains structural stop").

### A2. Pending-entry reservation — FROZEN
An accepted signal reserves one slot and its $750 planned risk in heat from the
decision timestamp (signal-bar close) until fill or invalidation. A pending entry
makes its symbol busy. A new signal on a pending symbol is busy-skipped.
Basis: JUDGMENT ("pending" in the busy rule implies pending state exists;
non-reservation would permit >6 concurrent commitments, contradicting max-6).

### A3. Same-timestamp evaluation sequence — FROZEN
At each signal-bar close, process that bar's candidate batch in this order:
1. Drop busy symbols (open or pending).
2. If survivors exceed free slots, rank by rs_top2 and keep the top-N by
   (rs_top2 desc, signal timestamp, symbol asc).
3. Heat check in that same rank order, first-fit: accept while
   `(heat + 750 / marked_equity) ≤ 5%`; the rest are heat-skipped.
Pending entries from prior bars already occupy their slot and heat before step 1.
Basis: DERIVABLE (documented funnel order busy → slot/rank → heat).

### A4. rs_top2 benchmark formula — FROZEN
`rs_top2 = (Close4H[i] / Close4H[i−20] − 1) − (SPY_daily[t] / SPY_daily[t−20d] − 1)`,
where `i` is the signal bar (20 closed 4H bars, strict PIT) and `t` is the last
completed daily SPY bar with timestamp ≤ signal-bar close. Signals with fewer
than 20 closed 4H bars are unrankable and sort last. Ranked at signal bar `i`;
entry unaffected (next-bar open).
Basis: EXPLICIT (PIT_FEATURES.md:34; `pine_ranking/pine_ranking.py:95-114`).

### A5. Early-close availability timestamp — FROZEN
The single 09:30 bar on NYSE early-close days becomes available at **13:00 ET**
actual (session-local close). Signals evaluated on it carry bar-close timestamp
13:00 ET.
Basis: JUDGMENT (exchange-calendar semantics under session-local construction).

### A6. Marked-equity / event ordering — FROZEN
At each event timestamp, process in this order:
1. Mode B engine exits/fills for that bar (stop, TP1, Profit-Protect, timeout) in
   symbol-asc order; each leg's cost deducted immediately.
2. Pending-entry fills in rank order (re-check entry > stop invalidation);
   entry-leg cost deducted immediately.
3. At 4H bar closes, mark equity.
Costs are deducted at the leg's event, never batched or deferred.
Basis: JUDGMENT (consistent with "costs deducted at event legs; equity marked at
4H closes").

### A7. Rounding outside Mode B — FROZEN
No intermediate rounding. `shares = floor(750 / (entry − stop))` (integer).
Dollar costs and equity carried at full float precision through the run; outputs
rounded only at write time (R → 4 decimals, $ → 2 decimals), matching ENGINE.md's
4-decimal output convention.
Basis: JUDGMENT.

---

## §5. No-targeting constraint (owner directive)

- The old 143-trade C1 numbers (+0.337R/trade, +52.25%, ~31.63% DD) are
  **banned from validation**. They are compromised selected-sample evidence
  (numpy boolean trendScore bug — owner ruling 2026-09-28) and must not appear
  as targets, gates, or tie-breakers anywhere in the rebuild.
- The numpy-boolean trendScore bug must NOT be reintroduced. Canonical V5 is the
  V5.4 structural-contract path (no scores), per REBASELINE/PORTFOLIO.
- No historical outcome — Layer-1 or Layer-2 — was used to choose among the §4
  resolutions. Each records its basis above. If a basis is later shown wrong by a
  surviving document, the correction is recorded as a finding; the run is not
  re-tuned.

---

## §6. Provenance rules

- Daily cache: yfinance, window 2023-06-01→2026-09-24, `auto_adjust=False`, OHLC
  scaled by AdjClose/Close, raw Volume, America/New_York.
- 4H cache: yfinance 1H source, regular US session only, explicit per-session
  wall-clock aggregation (09:30–13:30, 13:30–16:00 ET), OHLCV first/max/min/last/sum,
  session-local DST-safe construction, one bar on early closes. Do NOT reuse the
  production `resample_closed_4h` global-resample behavior.
- Every cache file: SHA-256 + fetch timestamp logged; no hand edits, ever.
- Deterministic order everywhere: timestamp asc, then symbol asc. No dict-order
  or thread-order dependence.
- Rebuild stages A→G in plan order; gates A–F must pass in sequence; a failed
  gate stops the rebuild (record cause; do not adjust rules to force a pass).
- 31 Mode B synthetic unit tests (ENGINE.md) recreated and passing before simlib
  may call the engine (Gate D).

---

## §7. Post-run procedure

1. Execute the locked rebuild exactly once per stage; write outputs.
2. Check Layer-1 (§2). Any miss: record as a finding with cause; stop — do not
   proceed to Layer-2, do not tune.
3. Verify sealed-oracle hash, unseal, check Layer-2 (§3). Any miss: finding, not
   tuning permission.
4. If Yahoo data revisions explain a miss, label the result **non-exact**
   (data-drifted), never loosen a tolerance afterward.
5. Whatever passes is labeled **reconstructed canonical replica**.

---

## §8. Narrow Phase-0 procedural amendment (pre-authorized text)

In `research_notes/CANONICAL_QF_VALIDATION_PREREG_20260928.md`, Phase 0,
replace:
> "The reproduced headline must reconcile trade-by-trade to the published baseline."
with:
> "Phase 0 reconciles against the frozen multi-invariant oracle in
> `CANONICAL_RECONSTRUCTION_FROZEN_RULES_20260928.md` (§2 pre-run, §3 sealed
> post-run). Exact trade-by-trade reconciliation is required only if an original
> trade ledger becomes available. The rebuild result is labeled a reconstructed
> canonical replica, not a recovered original."

This amendment changes no trading rule, threshold, dataset, or performance gate.
It replaces an impossible verification artifact with a preregistered procedure.
Apply it when (not before) Claude + ChatGPT + Mike approve this frozen spec.

---

## §9. Remaining gates — DO NOT BUILD until all clear

1. Claude independent audit of THIS frozen spec (audit package ready; relay via Mike).
2. ChatGPT adversarial review of this frozen spec (via bridge REVIEW REQUEST).
3. Mike's explicit sign-off on the frozen spec.
4. The §8 amendment applied to the validation prereg.

Build starts only after 1–4. Any material finding from Claude or ChatGPT returns
this document to DRAFT.

---

## §10. Freeze attestation

- [ ] Claude audit received and reconciled (no unresolved material ambiguity)
- [ ] ChatGPT review: PASS / sign-off on frozen spec
- [ ] Mike sign-off
- [ ] §8 amendment applied to validation prereg
- [ ] Sealed-oracle SHA-256 recorded below and file stored unopened

## §11. Sealed-oracle commitment

SHA-256: `2656855d79c3d516d01c4a4b698b298c0fc2c2b2fd6df327f84dbbd5095f1546`
File: `research_notes/CANONICAL_RECONSTRUCTION_SEALED_ORACLE_20260928.json`
