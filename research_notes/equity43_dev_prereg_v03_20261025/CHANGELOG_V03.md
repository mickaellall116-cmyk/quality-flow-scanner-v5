# Changelog — Preregistration Draft v0.2 → v0.3

**Base:** Claude preregistration draft v0.2, commit `02568b2`, PDF SHA-256 `01c4fff0c94cbf1d48f420b4e71619b7f477b07deaacd76705e9ca788abf00ae`.
**Product:** `PREREG_V03_DRAFT.md` in this package.
**Governing instruction:** Issue #1 comment `6401075123` (ChatGPT, 2026-10-25) + Slack desk TS `1792950736.364589`.
**Adjudication inputs:** -27 redlines (commit `f8da442`); -28 delta dispositions (commit `099cd84`, reviewed PASS in Issue #1 comment `6394587059`); N2 erratum (commit `f625921`); measurement closure (Issue #1 comment `6400814802`); -25 frozen inference contract (commit `fc17041`).

**Rule of construction:** v0.3 incorporates **only adjudicated material**. Withdrawn -28 items stay exactly as v0.2 wrote them (rows W01–W09: no text change). Revised items take the revised wording (rows C02–C03, C06, C08–C10, C14–C18, C20–C21). R19, the one STANDS item, is recorded **closed-by-delivery** on the -29 evidence (row C07). Unresolved forks are carried as OPEN items in the user's name (rows C17, C19; checklist), never resolved by the draft. No new hypotheses, no new thresholds, no design freelancing.

Disposition accounting (auditable against -28 §2/§5): **WITHDRAWN 9 · REVISED 10 · STANDS 1** (of R1–R20), plus new flags **N1–N4**, plus governing-comment items (1)–(8).

---

## Change register — text changes (C)

| ID | Where in v0.3 | Change | Primary source | Evidence |
|---|---|---|---|---|
| C01 | §3, Historical evidence schema | Machine-checkable schema separating ALL_SIGNAL_FIRE (2,892) from STANDALONE_CANDIDATE (590) and PORTFOLIO_TAKEN by view (191/191/189); 7A/7B/7C strata and availability rules defined | Governing (1) | Comment `6401075123` item (1); -29 all-fire artifact (commit `539e0a9`) |
| C02 | §1 power limit; §10 F6 | "Roughly 700" relabelled as the vs-zero figure (≈693); strict PASS figure ≈1,392 stated; F6 floor arrival corrected from "roughly 6 to 8 months" to ≈13–14 months at the DEV realized rate (590 → 187 closed over 25.0 months = ≈7.5 closed/month) | -28 R2-revised (a),(b) | -28 §1.2/§2 R2 (commit `f625921` state); governing (5) |
| C03 | §6 Power report | Power report must publish, per endpoint: strict-δ power at the endpoint's own δ, α after family allocation (Holm worst case for H-EXIT), paired SDs for 7A endpoints, design effect; dependence-aware power required | -28 R2-revised (c) | -28 §2 R2; governing (5) |
| C04 | §6 Power report | **N1 correction:** v0.2's "Reaching L ≥ δ for a true effect of 2δ needs about the same" replaced — at 80% power the requirement is ≈8,013 H-SYS trades / ≈4,179 H-BUY events (≈2.3× the half-width figure); the ≈50%-power equality (≈3,506) stated as such | N1 | -28 §4 N1; confirmed in comment `6394587059`; governing (5) |
| C05 | §8 Two-stage identity rule | Stage 1 byte-identity scoped to the original per-view frozen fields under the frozen convention; Stage 2 per-fill restatement is a new version that may alter net P&L; claiming unchanged P&L while changing costs is prohibited | Governing (2) | Comment `6401075123` item (2); -28 R6 context |
| C06 | §3 P9; §8 | P9 staged and field-scoped (identity fields first under the frozen convention; restated ledgers second), resolving the P5/P9 contradiction in v0.2 §3 | -28 R6-revised | -28 §2 R6; -30 parity artifact (commit `d077532`, 26/26) |
| C07 | §3, R19 block | **R19 CLOSED-BY-DELIVERY:** per-cost-view ledgers committed (gross 191/188/+28.1812R; 4 bps 191/187/+32.4873R; 25 bps 189/185/+19.8892R, each matching results.json); the 185-vs-187 divergence resolved on record as a wrong-subset figure, preserved as a labelled diagnostic; R19 not carried as an open requirement | -28 R19 (STANDS) + delivery | -29 reconciliation commit `2cf06fc`; resolution accepted in comment `6398111535`; governing instruction not to carry the resolved redline |
| C08 | §7 Study 7C | 7C reports the equity/time-normalised portfolio return of both replays beside the mean-R estimand, never substituted; joint calendar-block bootstrap endorsed as written | -28 R12-revised | -28 §2 R12 (DEV illustration: mean +0.17373R vs total return +42.44% on the same run) |
| C09 | §4 censoring; §14 | Analysis-boundary treatment stated for H-SYS-1 / H-EXIT-4: open positions excluded from the closed-trade mean, open count + marked equity reported beside the verdict, no R fabricated; portfolio return/drawdown keep censored-at-mark treatment; DEV restatement treatment stated | -28 R11-revised | -28 §2 R11; governing (3); -13 precedent (4 censored taken positions) |
| C10 | §6 Inference | Interval method reconciled: v0.2's 20-bar moving blocks superseded by the frozen contract — circular block bootstrap, 20-session blocks, 10,000 reps, seed from the frozen preregistration's SHA-256; wider-of-two rule retained; deviation and its resolution recorded | -28 R13-revised | -28 §2 R13 (§1.1 arithmetic withdrawn); frozen contract commit `fc17041`; governing (5) |
| C11 | §7 Study 7A | **N2 as errata'd:** scope sentence added with the corrected never-valid-entry wording — the exclusion is the pre-entry gap case (next-bar entry open already below the signal-bar stop); a 7A verdict generalises only to entries opening at or above the initial stop; 7A is silent on the never-valid-entry subpopulation; held-position gaps are not excluded | N2 (erratum) | Erratum commit `f625921`; ChatGPT verdict comment `6394587059` |
| C12 | §13 register; §4 | **N3 rename:** register row "H-EXIT-2" renamed **R-EXIT-2** with cross-reference; H-EXIT-4 register row added for completeness (§4 hypothesis previously unregistered) | N3 | -28 §4 N3; governing (7) "Retain E2 as R-EXIT-2 only"; v0.2 §4 p.5 vs §13 pp.18–19 |
| C13 | §3 P7 | **N4:** P7 completion evidence made countable — all-fire total stated as separate class counts: 2,892 = 590 standalone candidates + 2,301 suppressed-overlap + 1 gap-ineligible + 0 unclassified | N4 | -28 §4 N4; -29 `allfire_summary.json` (commit `539e0a9`); governing (1) |
| C14 | §5 Feasibility check | Feasibility report additionally publishes, outcome-blind, the dropped-event count and an event-mix composition summary (by symbol and session bin) at the frozen relaxation step; causal-as-of sub-point withdrawn (same-symbol baseline, no SPY series) | -28 R8-revised | -28 §2 R8; governing (6) |
| C15 | §7 Declared modelling assumptions | The two 0.05 ATR constants (E1 stop slippage; E2 TP1 exceed-margin) labelled **declared modelling assumptions** with no empirical provenance | -28 R18-revised (residue) | -28 §2 R18; governing (7) "flag 0.05 ATR assumptions" |
| C16 | §3 P1; §14 | One-sentence label: until the all-bar basis is quoted, any restated or quoted DEV drawdown (24.61%) is an **event-sampled lower bound**; all-bar figures cited (4 bps 26.1840%) | -28 R16-revised | -28 §2 R16; -29/-29r artifacts (commits `c103540`, `70ef367`) |
| C17 | §9 Status | §9 text stands (confirmed adequate); the audit **outcome** is carried as an OPEN joint user+Muse governance item, not resolved by the draft | -28 R9-revised (residue) | -28 §2 R9 ("the standing governance fork, unchanged"); v0.2 §9 p.13 |
| C18 | §11 Stage A branches | Stage A composition and edge-rule reading stated under **each** §9 outcome (Clean / Partly contaminated / Contaminated): Tier 2 included / excluded-from-pool / excluded-entirely; Tier 3 eligibility unchanged; shared-market-days covariance handled inside the calendar-block design | -28 R10-revised | -28 §2 R10; governing (4) |
| C19 | §11 Adoption status; §15 O2 | The §11 contract is stated as the single PASS/FAIL/INCONCLUSIVE contract; its **adoption at freeze is carried OPEN in the user's name** — the draft states semantics, it does not adopt them | Governing (8) + freeze governance | Comment `6401075123` item (8); -28 R1 withdrawal (semantics themselves stand as v0.2 wrote them) |
| C20 | §3 P2 | R20 converted answer written in: ranking is the **live count** (`free0` dead code; in-loop free → contested → `min(2, free)`; gate order rank → cap → sector → heat) | -28 R20 (answers) | -27 §§2.2 (source-verified); -30 semantic pins (commit `d077532`) |
| C21 | §3 P6 | R20 converted answer written in (no notional/cash cap; caps are count 5 + heat 5%) with the **corrected** full-grid figures (peak 2.7859x, mean 1.1203x, max single 1.6453x; -30 entry-only figures superseded); upper-bound caveat retained | -28 R20 (answers) + measurement delivery | -27 §2.6; -31 commit `848f75d`; closure comment `6400814802` |
| C22 | §15 Freeze path | Per-stage gate owners named (G1–G7); P10/P11 carried as freeze-path preconditions; **document acceptance explicitly distinguished from authority to run** | Governing (8) | Comment `6401075123` item (8) |
| C23 | §6 Multiple testing | Holm procedure made deterministic: family {H-EXIT-1, H-EXIT-3, H-EXIT-4}, familywise one-sided 0.05, ties in step-down ordering broken by fixed hypothesis order (1, 3, 4); R-EXIT-2 takes no alpha | Governing (5) | Comment `6401075123` item (5) (Holm multiplicity and tie-breaking) |
| C24 | §2 Measurement basis | The closed measurement layer (P1–P4, P6–P9 PASS) cited as the qualified basis, with the standing disclaimer that measurement readiness is not edge validation, freeze, or run authority | Measurement closure | Comment `6400814802` (-31 verdict: P6 PASS; package closed); comment `6401075123` preamble |
| C25 | Companion file | `OUTCOME_BLIND_FEASIBILITY.md` delivered with the draft: outcome-blind feasibility/readiness from committed metadata/census only (accrual, corrected required-n, measurement readiness, calendar coverage, pool-check runnability) | Governing (readiness deliverable) | Comment `6401075123` closing instruction; Slack TS `1792950736.364589` |
| C26 | Companion file §6 + bottom line (**post-delivery amendment A1**) | §6 "RUNNABLE from committed metadata" verdict **corrected to BLOCKED/UNPROVEN as cited**: the all-fire journal carries only BUY-fire rows and cannot enumerate non-signal bars or their ATR%/EMA fields (HOLD 1). Closure recorded: P7b every-observed-bar inventory built from the committed DEV capture bytes and hash-pinned; pool-count check executed outcome-blind under the pinned EXP-14 script. No rule, threshold, or design element changed | ChatGPT review HOLD 1; Claude Final-Gate M1 | Comment `6401471382` (HOLD 1); comment `6405097569` (Claude verdict relay, M1/M2); companion package `research_notes/equity43_dev_buy_prep_m1m2_20261025/` |

## Change register — no-change dispositions (W)

Withdrawn items stay exactly as v0.2 wrote them. Recorded here so the -28 disposition count is auditable from this package alone.

| ID | -28 item | Disposition | Why no text change (evidence) |
|---|---|---|---|
| W01 | R1 — §11 PASS semantics attacked as "L > 0 ∧ estimate ≥ δ, consistent-with" | WITHDRAWN | The attacked rule is not in the draft (relay artefact); v0.2 already requires strict L ≥ δ (§6 pp.7–8, §11 p.16, §15 p.22). -28 §2 R1 |
| W02 | R3 — §7 E0 fidelity pin demanded | WITHDRAWN | Everything demanded is already in v0.2 §7 p.9 (fidelity pin, 7A/7B/7C separation, 7B non-gating). -28 §2 R3 |
| W03 | R4 — H-EXIT-3 direction predeclared | WITHDRAWN | Direction E0 minus E3 already predeclared (§4 p.4, §7 p.11, changelog p.22). -28 §2 R4 |
| W04 | R5 — E2 classification / Holm family | WITHDRAWN | E2 already R-EXIT-2, outside Holm, no alpha, FILL-OPTIMISM flag (§4 p.5, §6 p.8, §7 p.11). Sole residue was register naming → C12. -28 §2 R5 |
| W05 | R7 — "FAIL-incapable" language | WITHDRAWN | Already replaced by UNDERPOWERED FOR PASS with FAIL possible at any n (§6 p.8). -28 §2 R7 |
| W06 | R14 — two-universe honesty (590 vs all-fire) | WITHDRAWN | v0.2 §5 event universe is all-fire by definition; P7 already requires the unsuppressed ledger. Populating it was an implementation item → delivered by -29 (C13). -28 §2 R14 |
| W07 | R15 — 10-bar horizon primacy | WITHDRAWN | v0.2 already discloses the DEV-informed choice and leaves 10-vs-20 as a §15 freeze item for the user (carried as checklist O3). -28 §2 R15 |
| W08 | R17 — telemetry retro-DEV claims | WITHDRAWN | No v0.2 text claims retro-DEV telemetry exists; P8 is a forward precondition. -28 §2 R17 |
| W09 | R20 — rank + exposure semantics as a redline | WITHDRAWN as a redline; converted to answers | v0.2 asserts no wrong semantics (P2/P6 posed as open items). The source-verified answers are written into §3 as C20/C21. -28 §2 R20 |

## Carried OPEN (not changes, not resolutions)

| Item | Where carried | Owner |
|---|---|---|
| §9 eligibility audit outcome | Draft §9 status; §15 O1; checklist B1 | Joint: the user (Mike) and Muse |
| §11 PASS-semantics adoption at freeze | Draft §11 adoption status; §15 O2; checklist B2 | The user (Mike) |
| Horizon 10 vs 20; feasibility expand-vs-accept; stage design; cost-convention confirmation | Draft §15 O3/O4/O8/O9; checklist | The user (Mike) |
| P10 / P11 completion evidence | Draft §3, §15 O5/O6; checklist | Muse (produce), ChatGPT (review) |

## Not in v0.3 (by instruction)

No new hypotheses; no new thresholds or δ/α values; no re-estimated planning constants (μ, σ carried from v0.2 as its stated planning figures); no holdout content (the §9 audit is specified on metadata/history only); no performance results of any new run (none was run); no change to the frozen strategy, the pilot, or S1.
