# Shared Preconditions Checklist — Stage A / Stage B Execution Packages

**Assembled:** 2026-10-26 · **Basis:** Preregistration v0.3 draft (`PREREG_V03_DRAFT.md`, package `equity43_dev_prereg_v03_20261025`, commits `b65696a` state) as amended by the decisions of record below. **This checklist authorizes nothing.** It records what must be true before either stage may run. Document acceptance, a completed freeze, and these packages are each **not** a GO — every tier opening needs its own explicit GO from Mike (§15, gate G7).

**Standing labels (unchanged by anything here):** original C1 verdict **FAIL** · DEV **EXPLORATORY** (not a validated edge) · **G4 UNADOPTED** · **S1 LAUNCH_HOLD** · production **PAUSED** · holdout **SEALED** until Stage A's own access GO.

---

## 1. Decisions of record (Mike + ChatGPT, 2026-10-26)

| Fork | Decision | Effect on the protocol |
|---|---|---|
| **B1 (§9 holdout eligibility)** | **REDUCED.** The holdout confirmatory universe is the **19 defect-free names** (defect census: all 123 defective bars sit in one Twelve Data feed hole, Apr 4–22 2024, across 25 names; DEV has zero defective bars) **plus mechanically selected, outcome-blind Tier 3 additions**, gated on (i) a **Clean §9 contamination audit** and (ii) the **≥20-symbol validity floor**. | Stage A composition is fixed by this decision + the §9 audit outcome (§11 branch readings still govern Partly contaminated / Contaminated). Exclusion is by bar-quality metadata only, never by outcomes; the reduced universe is disclosed in every Stage A report. Results describe the tested sub-universe, never the full 43-name universe. |
| **B2 (§11 verdict contract)** | **ECONOMICS-FIRST.** PASS = all validity floors and gates met **+ point estimate θ̂ ≥ δ + the one-sided 95% interval excludes zero (L > 0)**. **CONFIRMED AT δ** (L ≥ δ) is retained as the stronger grade and is printed with every verdict. | Replaces v0.3 §11's strict PASS rule (L ≥ δ) as a logged pre-unblinding amendment (§15 permits amendments before any untouched data is opened). δ, α, floors, Holm/fixed-sequence structure, interval method, and the 25 bps gating cost are **unchanged**. FAIL is unchanged (U < δ → EXCLUDED). Sanity anchor: EXP-14B (+0.84%, interval crossing zero) still does **not** PASS under this contract. |
| Preserved as drafted | Statistical controls, costs, minimum effects (§6/§8); primary H-BUY horizon **10 bars** (checklist B3 designation preserved); per-fill cost convention (§8, checklist B6); A-then-B stage design (§11, checklist B5); Tier 3 expansion adopted (checklist B4, via B1). | Carried into the v1.0 assembly unchanged. |

## 2. Protocol preconditions P1–P11 (§3) — status

| ID | Precondition | Status | Gates |
|---|---|---|---|
| P1 | All-bar MTM drawdown basis | **PASS (bounded)** — -29 `c103540`, -29r `70ef367`; DEV all-bar DD 25.5756% gross / 26.1840% @4bps / 26.7035% @25bps | A, B |
| P2 | Ranking semantics pinned (live-count slots; gate order rank → cap → sector → heat) | **PASS (bounded)** — -30 `d077532`; census 191 / 326 / 45 / 28 reproduces | A, B |
| P3 | Benchmark as-of rule (D−1 completed SPY session) | **PASS (bounded)** — -30 `d077532` | A, B |
| P4 | Simulator documentation matches semantics | **PASS** — -29 `d06dfe3` (docstring erratum, zero behavior change) | A, B |
| P5 | Per-fill cost model (§8) converted and recorded in config | **OPEN — freeze-path.** Convention specified in §8; completion evidence is the new config hash at freeze. Stage-1/Stage-2 identity rule applies: no parity or P&L claim crosses between the frozen flat-convention ledgers and the per-fill restatement | A, B |
| P6 | Exposure as notional vs equity (full grid) | **PASS** — -31 `848f75d`: peak 2.7859x, mean 1.1203x, 964-sample grid | A, B |
| P7 | Unsuppressed all-fire ledger (2,892 = 590 + 2,301 + 1 + 0) | **PASS** — -29 `539e0a9` | A, B |
| P8 | Full-state as-of telemetry journal | **PASS (bounded; authorizes no launch)** — -29 `fa2f474`, -29r `70ef367`, -30 `d077532`; schema pinned in `qf_telemetry.py` (see §4 below) | A, B |
| P9 | Parity: pinned code reproduces the -13 ledger | **PASS, staged** — Stage 1 (frozen convention, identity fields, 26/26 checks, -30 `d077532`); Stage 2 restatement is a new version under §8 | A, B |
| P10 | Data-rights / session / adjustment audit | **OPEN — in production** (Mike's 2026-10-26 execute item 3). Rights position per data source (zero private vendor exposure in any report), session-table provenance, split/dividend adjustment handling | A, B |
| P11 | Immutable version pins (code, config, calendar, documents; numeric bootstrap seed) | **OPEN — in production** (execute item 3); lands in the freeze record | A, B |

## 3. Freeze chain G1–G7 (§15) and freeze-blocker items

| Gate | Content | Status at assembly |
|---|---|---|
| G1 | Independent review of v0.3 | On record (ChatGPT review; redlines comment `6401075123`; closure comment `6400814802` for the measurement layer) |
| G2 | Disagreements resolved / escalated to Mike | B1 and B2 **decided 2026-10-26** (see §1). Remaining B-items carried as drafted (B3 10 bars, B5 A-then-B, B6 per-fill) |
| G3 | P10 + P11 + §6 power report published | **OPEN — in production** (execute item 3). Power report is variance-only: per-endpoint strict-δ power, allocated α, paired SDs, design effects; **no group differences** |
| G4 | §9 contamination audit (A1–A5) run, outcome logged jointly (Mike + Muse) before any access | **OPEN — running** (execute item 1; metadata/access-history only, no holdout bars). Stage A cannot be staged until the outcome is logged |
| G5 | v1.0 committed with signed tag + hash; document locked | **OPEN — assembling** (execute item 5) |
| G6 | Feasibility decision logged (Tier 3 expansion vs accept UNDERPOWERED FOR PASS) | **Decided in substance by B1** (Tier 3 expansion adopted); formal log entry lands with the freeze record |
| G7 | Each tier opened only in §11 stage order, **each on its own explicit GO from Mike** | **NOT GIVEN for either stage.** This is the final gate for both packages |

Freeze-blocker checklist cross-reference: A1–A6 closed on evidence (measurement layer, R19 ledgers, P7 census, corrected power arithmetic 693 / 1,392 / 3,506 / 1,829 / 8,013 / 4,179, -28 dispositions, calendar union 1,054 sessions — base table sha `00c5555c…`). C5 (Tier 3 mechanical list rule) is **being finalized** under execute item 2 — source, cutoff, eligibility, reproducibility evidence — and must be CLOSED before either stage's universe is final.

## 4. Pinned references (both stages)

| Item | Pin |
|---|---|
| Frozen rule set under test | Config pin `87b8285a…8706`, source commit `555ebb1` (experiment QF-EQUITY43-DEV-ORDER-CENSOR-20261023-13). Any rule change = new version, fresh evidence; it cannot reuse any tier |
| Session calendar | Adopted 751-session table sha `00c5555c…`; union extension through 2027 = 1,054 sessions (-30 `d077532`) |
| Telemetry schema | `qf_telemetry.py` (-29 package `equity43_dev_measurement_fixes_20261025_29`, with -29r session-table binning and -30 repairs). Record types SIGNAL_FIRE / BAR_PATH / EXIT_DECISION / EXECUTION; strict schemas (unknown fields refused); hash-chained append-only JSONL; transactional append; fail-closed causality guards (bar_finalized; decision_time = signal_time + 4h; recorded_at ≥ decision_time; per-symbol monotonicity, no backfill) |
| Inference contract | Circular block bootstrap over calendar time, 20-session blocks, 10,000 reps, seed = first 8 bytes (big-endian) of the frozen preregistration's SHA-256, numeric value pinned in the freeze record (P11). Robustness: symbol-cluster bootstrap. **Verdict uses the wider interval.** Holm across H-EXIT-1/-3/-4 (ties broken in fixed order 1, 3, 4); H-BUY fixed sequence (10 bars primary; 5/20 inferential only if primary passes); H-SYS single test; one-sided α = 0.05; families never pooled |
| Minimum effects δ | H-BUY-P: 0.10 ATR · H-EXIT-1/-3/-4: 0.10 R · H-SYS-1: 0.05 R |
| Validity floors (below = INCONCLUSIVE regardless of estimate) | ≥200 de-clustered events (H-BUY) · ≥100 closed trades (H-EXIT, H-SYS) · ≥30 independent blocks · ≥20 symbols in every test |
| Costs | Gating: **25 bps round trip, per-fill** (12.5 bps × filled notional per fill, charged at each fill's own price). Descriptive/sensitivity only: 4 bps view; 10 bps (§12 cost-sensitivity point). DEV figures are restated under per-fill before any comparison, both versions shown once; no claim crosses stages (§8 two-stage rule) |
| Verdict computation (B2-amended §11) | **PASS** = floors + gates met, θ̂ ≥ δ, L > 0 → reported "PASS — economics-first" unless L ≥ δ, in which case grade **CONFIRMED AT δ**. **FAIL** = floors + gates met, U < δ → EXCLUDED. **INCONCLUSIVE** = everything else (floors/gates unmet, contamination, deviation, θ̂ < δ with a positive interval, or L ≤ 0 with U ≥ δ → INDETERMINATE), plus UNDERPOWERED FOR PASS where §6 applies. H-EXIT determinations use the Holm-adjusted bounds. §12 diagnostics annotate and never flip a verdict |
| Edge rule (§11) | "Edge supported" requires **Stage B PASS on H-SYS-1 AND Stage A not FAIL**. "Edge rejected" if **either** stage FAILs H-SYS-1. Anything else is INCONCLUSIVE and is reported as that |
| Deviation rule | Any deviation from the frozen protocol is logged; the affected verdict is **INCONCLUSIVE** unless Mike + Muse declared the deviation immaterial **before unblinding**. No post-hoc changes to δ, α, interval method, block length, or cost model after unblinding |

## 5. Per-stage gate matrix

| Requirement | Stage A (holdout replay) | Stage B (forward collection) |
|---|---|---|
| v1.0 frozen (G5, P11) | Required | Required (F1) |
| §9 audit outcome logged (G4) | Required — **Clean** for the B1 composition; Partly/Contaminated invoke §11 branch readings | Not required |
| B1 universe evidence (defect census + Tier 3 list pinned, pool ≥ 20) | Required | Tier 3 rule required for forward new symbols in the verdict pool |
| Power report published (G3/C4) | Required, with UNDERPOWERED determinations made before opening | Required before the verdict analysis (not before collection) |
| P10 audit (G3/C2) | Required | Required |
| Feed qualification (F2) | Not applicable (existing private capture, hash-verified) | **Required — OPEN dependency** (see stage_b_package.md) |
| Collector parity (F3) | P9 parity on the frozen code (replay form) | Zero decision mismatches on replayed inputs |
| Telemetry live (F4 / P8) | Journal written during the replay for every fire | Live from the first collection bar |
| Missed-signal discipline (F5) | n/a (historical window) | Required, verified before start |
| Separate tier GO (G7) | **Required — NOT GIVEN** | **Required — NOT GIVEN** |

## 6. What makes BOTH packages invalid to run

- v1.0 not frozen, or any pin in §4 mismatched at session start.
- Power report unpublished, or UNDERPOWERED determinations made after seeing any outcome.
- Any performance output viewed on an untouched tier before its frozen analysis (including "quick looks," partial runs, or a re-run to check a number).
- Any new strategy rule, parameter change, subset selection, or threshold adjustment introduced after the freeze — each is a new rule version and voids these packages for that version.
- Raw vendor bytes anywhere outside the private archive environment; any derived result computed from data the applicable rights position (P10) does not cover.
