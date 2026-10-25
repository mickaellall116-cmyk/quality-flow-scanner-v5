# -28 — DELTA re-check of the -27 redlines against Claude's actual Pre-Registration Draft v0.2 (PDF)

**Date:** 2026-10-25 (ET). **Lane:** Muse, single dispatch.
**Governing texts:** ChatGPT desk thread replies, Slack TS 1792905022.889999 + 1792905066.479189 (Oct 25 2026 ~01:10 ET); ChatGPT's independent actual-PDF review, Issue #1 comment 6393780155.
**Object under review:** `research_notes/edge_validation_prereg_20261025/Quality_Flow_Edge_Validation_PreRegistration_Draft_v0.2.pdf` at commit **02568b2**. SHA-256 **verified before reading**: `01c4fff0c94cbf1d48f420b4e71619b7f477b07deaacd76705e9ca788abf00ae` — exact match. All 23 pages read; the §6 thresholds table and §11 verdict/stage tables (column-scrambled in plain extraction) were cross-checked against layout-preserving extraction.
**Baseline:** -27 memo, commit f8da442 (`research_notes/equity43_dev_prereg_v03_redlines_20261025_27/MEMO.md`), written relay-based because the PDF was then inaccessible. This memo contains **only deltas** against it: dispositions of R1–R20, the two arithmetic corrections recomputed independently, verdicts on the areas -27 marked BLOCKED (access), and new flags found in the actual text. Nothing else in -27 changes; its source/ledger evidence (§§2–3, 6) stands untouched.

**Disposition counts: WITHDRAWN 9 · REVISED 10 · STANDS 1** (of 20).

---

## 1. Arithmetic corrections — recomputed independently, both conceded to ChatGPT

### 1.1 Block conversion: ChatGPT is right; my "≈3.3 sessions" was wrong

The equity grid carries **two** 4H bins per session (09:30 and 13:30 starts — draft §5, pp. 5–6). Therefore 20 bars ÷ 2 = **≈10 sessions**, exactly as the draft itself states (p. 7: "blocks of 20 bars (about 10 sessions)"; p. 6: "10 bars is about 5 sessions"). My -27 §4.6 / R13 figure of ≈3.3 sessions implicitly assumed ~6 bars/session, which is not this grid. **Withdrawn.** What survives of R13 is contract conformance only (§2, R13 below).

### 1.2 Power: ChatGPT's strict-δ figure is right; my 870 / 1,340 are superseded

Independent recomputation (z₀.₉₅ = 1.6449 one-sided, z₀.₈₀ = 0.8416, sum 2.4865; σ = 1.8R throughout):

| Quantity | Formula | Recomputed | Note |
|---|---|---|---|
| Test μ > 0, μ = 0.17R, one-sided α = .05, 80% | ((2.4865 × 1.8) / 0.17)² | **≈ 693** | This is the draft p. 1 "roughly 700 independent trades" — a vs-zero figure, not the PASS requirement |
| **Strict PASS (L ≥ δ), δ = 0.05R, μ = 0.17R** | ((2.4865 × 1.8) / (0.17 − 0.05))² | **≈ 1,391 → 1,392** | ChatGPT's figure confirmed to rounding |
| My -27 "n ≈ 870" | ((1.9600 + 0.8416) / 0.095)² = 869.7 | — | Artefact: I used a **two-sided** α for a vs-zero test. Superseded |
| My -27 "≈ 1,340 (Holm family)" | Holm worst case, one-sided α = .05/6 (z = 2.3940): vs-zero ((3.2356 × 1.8)/0.17)² = 1,174; strict ((3.2356 × 1.8)/0.12)² = 2,356 | — | My 1,340 matches neither clean recomputation. Superseded by both rows |
| Draft §6 half-width ≤ δ (H-SYS-1) | (1.6449 × 1.8 / 0.05)² | 3,506 | Draft's "roughly 3,500" (p. 8) verified |
| Draft §6 half-width ≤ δ (H-BUY-P, SD 2.6 ATR, δ 0.10 ATR) | (1.6449 × 2.6 / 0.10)² | 1,829 | Draft's "about 1,800" (p. 8) verified |
| Holdout-scale power, strict test, n = 85 | Φ((0.17 − 0.05)/(1.8/√85) − 1.6449) | **≈ 15%** | Restates -27's "~14%" |

All figures are independent-trade approximations, before any design effect — as are the draft's, which say so (p. 8).

---

## 2. Redline dispositions R1–R20 (page citations are to Draft v0.2)

**R1 — WITHDRAWN.** The PASS rule I attacked (L > 0 ∧ point estimate ≥ δ, "consistent-with" wording) is not in the draft; it was a relay artefact. The draft requires strict **L ≥ δ** for PASS (§6, pp. 7–8), names 0 < L < δ "**POSITIVE, NOT CONFIRMED AT δ**" (p. 8), repeats L ≥ δ as the §11 PASS condition (p. 16), and lists "confirm L ≥ δ as the only PASS" as a §15 confirmation item (p. 22). UNDERPOWERED FOR PASS is reported with the verdict (pp. 8, 16), covering my no-promotion-language residue. Nothing remains.

**R2 — REVISED (narrowed to three exact edits).** The draft's power section is substantially more honest than the relay conveyed: planning figures verified (§1.2), UNDERPOWERED FOR PASS labelling, "One year of 43 names cannot reach that" (p. 8), and a mandatory pre-opening power report. What stands:
(a) **p. 1 relabel.** "Confirming a +0.17R expectancy needs roughly 700 independent trades" is the vs-zero number (≈693). Under the draft's own PASS rule the figure is **≈1,392** (§1.2). The sentence must carry the strict number, or be labelled as testing μ > 0 only.
(b) **§10/F6 arrival estimate (p. 15).** F6 projects the 100-closed-trade H-SYS floor in "roughly 6 to 8 months" from "about 300 candidates a year." At the draft's own candidate rate and the DEV take/close rate (590 candidates → 187 closed over 25.0 months = 7.5 closed/month), 100 closed trades take **≈13–14 months**. Correct the estimate or re-base it; the 6-month minimum collection period itself is unobjectionable because the verdict waits for the floors (p. 15).
(c) **Power-report content.** §6 (p. 8) requires publishing expected interval **half-widths** per tier. v0.3 must also require, per endpoint, the **strict-δ power** at that endpoint's own δ, its α after family allocation (Holm worst case for H-EXIT), the paired SD for the 7A paired endpoints, and the design effect — the quantities §1.2 shows are decisive and are not interchangeable across endpoints.

**R3 — WITHDRAWN.** Everything demanded is already in §7 (p. 9): the fidelity pin (entry at next bar's open; stop = signal-bar close − 1.5 × ATR(14); TP1 = fill + 2.0 × ATR(14); `gen_candidates_censored`, pine_backtest.py lines 150/157), the live-recompute Pine caveat, the 7A/7B/7C separation with 7B explicitly non-gating because "that candidate set is itself produced by E0" (p. 9), and §4's separation of H-EXIT from H-SYS-1 (pp. 4–5).

**R4 — WITHDRAWN.** H-EXIT-3's direction is predeclared **E0 minus E3** in §4 (p. 4), in the §7 metric (p. 11), and recorded as a v0.2 changelog fix (p. 22). Fully falsifiable as written.

**R5 — WITHDRAWN.** E2 is classified R-EXIT-2, "Robustness, not a hypothesis," outside the Holm family, taking no alpha, reported with the FILL-OPTIMISM flag at < −0.10R (§4 p. 5; §6 p. 8; §7 p. 11; changelog p. 22). One naming residue survives as new flag N3, not as R5.

**R6 — REVISED (convention half withdrawn; P9 staging stands).** §8 (pp. 11–12) already does what the redline demanded: an explicit per-fill accounting convention, the non-equivalence to 25 bps of entry notional stated, the DEV flat charge acknowledged as verified, and a restatement rule ("restated under the per-fill convention before any comparison… both versions shown once"). What stands: **P9 staging.** P9 (p. 3) requires the modified code to reproduce the -13 ledger with a "byte-identical comparison on the 590 rows," while P5 (same table) converts the cost model — which changes every net R in those rows. v0.3 must name which fields the byte-identity covers (candidate/disposition identity vs net-R values) and stage it explicitly: frozen-convention parity first, committed restated ledgers second (with R19).

**R7 — WITHDRAWN.** "FAIL-incapable" is gone; the draft substitutes **UNDERPOWERED FOR PASS** and states a sufficiently negative result (U < δ) can FAIL at any sample size (§6, p. 8; changelog, p. 23).

**R8 — REVISED (narrowed to a technical feasibility note, per ChatGPT).** The demanded machinery already exists: the outcome-blind pool-count check with a fixed, pre-declared relaxation ladder — (a) ATR% band ±40%, (b) window ±45 sessions, (c) minimum 6 — with the step reached "recorded and frozen for every tier" and no forward returns computed during the check (§5, p. 6). Two residues: (i) the check validates **counts only**; the v0.3 feasibility report should also publish, still outcome-blind, the dropped-event count and an event-mix composition summary (by symbol and session bin) at the frozen relaxation step, so a ladder endpoint that quietly changes *which* events survive is visible before freeze. (ii) My causal-as-of sub-point is **withdrawn**: §5's baseline is same-symbol (own bars, own-ATR normalisation, time-of-day matching, pp. 5–6); no SPY series enters it, so the §2.3 benchmark rule has nothing to bite on here.

**R9 — REVISED (resolved portion withdrawn; no text residue).** The draft defines contamination as outcome influence — "merely holding historical data that spans the window is not contamination" (§9, p. 12); A1 states possession/overlap triggers tracing through A2/A4, not a verdict (p. 12); A4 requires the per-component rule genealogy (p. 13); A3 makes the SMCI evaluability adjudication an explicit inspection subject (p. 12). My enumeration demand (2022 studies, old 4H cache, ranking variants) is the draft's own A1/A4 plus the §13 backfill rows (pp. 12–13, 18). What remains is not a redline: the eligibility outcome itself, which the draft assigns to a joint user+Muse decision logged before any access (p. 13) — the standing governance fork, unchanged. The Tier 2/3 pooling linkage lives in R10.

**R10 — REVISED (narrowed; the clean-audit precondition conceded).** §11 already conditions Stage A on the audit: "one pooled analysis of Tier 2 plus Tier 3 on the holdout window, **once the audit is clean**" (p. 16). What stands is the unhandled branch: under §9's **Partly contaminated** outcome, Tier 2 is "reported as supplementary with no PASS or FAIL standing" (p. 13), but the draft never states Stage A's composition in that branch, and §11's edge rule ("Stage B to PASS for H-SYS-1 and Stage A not to FAIL," p. 16) is undefined when Tier 2 carries no standing. v0.3 must state Stage A's data composition and the edge-rule reading under **each** §9 outcome (Clean / Partly / Contaminated).

**R11 — REVISED (core withdrawn; boundary specification stands).** The declare-the-estimand demand is met: H-SYS-1 is "Mean net R per closed trade at 25 bps round trip" (§4, p. 5), floors are counted in closed trades (p. 8), and no equity-inclusive figure is mixed into the endpoint. What stands: the draft never specifies treatment of **positions still open at the analysis boundary** for H-SYS-1 or H-EXIT-4 (p. 5) — excluded by the estimand's letter, but v0.3 should state it, and require the open count and their marked value reported beside the verdict, matching the -13 precedent's disclosure (censored taken positions valued in equity, excluded from closed-trade R, no R fabricated). The same statement should cover §8's DEV restatement: which portfolio-level DEV outputs (total return, drawdown) keep the censored-at-mark treatment while H-SYS-1 does not.

**R12 — REVISED (my one-frozen-list demand withdrawn; one reporting addition stands).** ChatGPT's narrowing is correct against the text, and I adopt it. Study 7C *by design* allows different trade lists — changing exits changes later signals/admissions — and the draft says so, with inference by "the block bootstrap over calendar time applied to both replays jointly (same blocks, both arms), not a per-trade pairing" (§7, p. 10). Identical entries hold where pairing is claimed (7A/7B use the same event/candidate sets across arms, pp. 9–10). The §15 open item asks whether Muse prefers an alternative to the joint bootstrap (p. 22): **I endorse the joint bootstrap as written** — it is the construction that preserves cross-arm dependence; per-trade pairing across differing lists is not available. One addition stands: 7C's side-by-side reporting lists "trade counts, exposure and drawdown" (p. 10) but **not portfolio return**; v0.3 should add the equity/time-normalised portfolio return of both replays beside the mean-R estimand, the two never substituted — the DEV record itself shows why (per-trade mean +0.17373R vs total return +42.44% on the same run, -27 §4.4).

**R13 — REVISED (arithmetic withdrawn; contract conformance stands).** The dependence rhetoric in -27 relied on the wrong conversion and is withdrawn (§1.1: 20 bars ≈ 10 sessions, and a 10-session block does exceed the DEV average hold of 16.7 bars ≈ 8.4 sessions). What stands is narrower and purely contractual: the **frozen inference contract specifies 20-session circular blocks** (10,000 SplitMix64 reps); the draft specifies **20-bar (≈10-session) moving blocks** (p. 7). Two deviations — block unit (bars vs sessions) and moving vs circular. v0.3 must either adopt 40-bar / calendar-session circular blocks or record the deviation explicitly at freeze with a dependence diagnostic justifying it. The draft's rep count (10,000) and pre-fixed seed (p. 7) already conform.

**R14 — WITHDRAWN.** The draft's §5 event universe is all-fire by definition — every completed bar where the signal is true "regardless of portfolio state or any simulated open trade" (p. 5); P7 requires the unsuppressed ledger with counts beyond the 590 (p. 3); 7B carries the suppression/selection caution in terms (p. 9). Populating the all-fire universe remains an implementation GO item, not a text defect.

**R15 — WITHDRAWN.** The draft discloses the horizon choice's DEV exposure verbatim — "this choice was made knowing the DEV average hold of about 17 bars, so it is not fully independent of DEV" (p. 7) — gives a structural rationale (p. 6: "long enough to reflect a trend hold, short enough to limit window overlap"), controls the secondaries by fixed sequence rather than spending alpha (p. 8), and leaves "10 bars as drafted, or 20 bars" as an explicit §15 freeze item (p. 21). The choice itself is Mike's freeze decision, already framed by the draft.

**R16 — REVISED (narrowed to one sentence).** P1 (p. 3) mandates the all-bar MTM figure "reported next to the event-time figure" as a precondition — stronger than my caveat for all future outputs. Residue: the draft nowhere states the caveat for the **historical** DEV figure. v0.3 should add one sentence (P1 or §14): until P1 completes, any restated or quoted DEV drawdown (24.61%) is labelled an event-sampled lower bound.

**R17 — WITHDRAWN.** P8 is a forward precondition (p. 3); §14 lists telemetry regeneration on DEV as work to do, not a property DEV already has; §7's oversized-loss decomposition is expressly conditioned "Where persisted bars allow it" (p. 11). No draft text claims retro-DEV telemetry exists. Implementation and tests for P8 remain separate GO items (as ChatGPT also notes), not v0.3 text changes.

**R18 — REVISED (strike demands withdrawn; two residues).** The numbers are not placeholders in the actual text: 0.10 ATR carries a cost rationale (≈25 bps at the ~2.6% DEV ATR, p. 7); 0.10R is "improvement must exceed a conservative round-trip cost" (pp. 7–8); **0.05R's endpoint is named** — H-SYS-1 — with its rationale (≈5 bps of equity per trade at 1% risk, ≈5%/yr at DEV frequency, p. 8), satisfying my naming condition; 25 bps is the §8 gating convention. Residues: (i) the 0.10R floor's detectability depends on the **paired SD**, which only R2-revised (c) now requires publishing — no separate redline needed; (ii) the two **0.05 ATR** constants (E1 stop slippage, p. 10; E2's exceed-margin, p. 10) carry no provenance — v0.3 should label them declared modelling assumptions. The thresholds remain freeze open items, as the draft itself states (§15, p. 21).

**R19 — STANDS.** The draft nowhere commits per-cost-view ledgers. §8's restatement rule (p. 12) presupposes a recomputation whose taken sets are not on record, and the -27 §3 divergence is unaddressed: results.json's 25 bps row (185 trades @ 0.108) cannot be reproduced from the committed ledger (the 4 bps taken set's 25 bps column recomputes to 187 @ +0.10753R). v0.3 must either commit the taken set/ledger for each cost view or scope every parity claim — including P9, per R6 — to the 4 bps C1 view.

**R20 — WITHDRAWN as a redline; converted to answers.** The draft asserts no wrong semantics — P2 and P6 are posed as open items (§3, p. 3; §15, p. 21), so there is no text to strike. The source-verified answers from -27 §§2.2/2.6 close them: **P2 = the live count.** `free0` (pine_stack.py:129) is dead code (single occurrence); the operative rule recomputes free slots per candidate in-loop, contested = n_cands > live free, cap min(2, free); the R1 reference (pine_ranking.py:213-221) agrees — no timestamp-start snapshot exists in either source. **P6 = no notional or cash cap exists** (caps are count 5 + heat 5% only); Claude's "peak gross notional near 2.8× equity" (p. 21) reproduces as 2.83× under the flat-equity reconstruction in -27 §2.6, whose per-timestamp notional reporting spec is the proposed P6 completion text.

---

## 3. Previously BLOCKED (access) areas — verdicts on the actual text

| Area | Verdict | Basis |
|---|---|---|
| H-BUY text (§§4–6) | **CONFIRMED-ADEQUATE** | Estimand, direction, tiers, gating and fixed-sequence secondaries all predeclared (pp. 4–6, 8) |
| H-EXIT text (§§4, 7) | **CONFIRMED-ADEQUATE** | All directions positive-favours-alternative (pp. 4–5); E2 out of family (R5); sole residue is register naming, N3 |
| H-SYS text (§4) | **CONFIRMED-ADEQUATE as declared** | Closed-trade estimand stated (p. 5); boundary treatment is R11-revised, not a wording defect |
| Tier structure + firewall (§2) | **CONFIRMED-ADEQUATE** | One confirmatory test per tier per version; Tier 3's shared-market-days caveat on the DEV window disclosed (p. 2) |
| Study 7A | **CONFIRMED-ADEQUATE**, with limitation flag N2 | Paired, all-arms-identical entries, gap exclusions symmetric (p. 9) |
| Study 7B | **CONFIRMED-ADEQUATE** | Non-gating with the E0-selection caution stated in terms (p. 9) |
| Study 7C | **CONFIRMED-ADEQUATE as written** | Different trade lists permitted by design; estimand is the frozen system-level H-EXIT-4 (mean net R per closed trade, E1 replay − E0 replay); joint calendar-block bootstrap endorsed (pp. 5, 10). Only residue: portfolio return beside, R12-revised |
| §9 contamination audit text | **CONFIRMED-ADEQUATE** | Definition, A1–A5, three outcomes, one-shot consumption rule (pp. 12–14) |
| Power section (§6; §1 statement) | **Converts to redlines** | R2-revised (a)/(c) and new flag N1 |
| GO/NO-GO criteria (§§10–11, §15) | **CONFIRMED-ADEQUATE**, except R10-revised | Verdict table (p. 16), no-post-hoc-changes rule (p. 17), staged F-gates (pp. 14–15), freeze procedure incl. changelog + user-decides residue (p. 22) |

---

## 4. New flags — in neither the relay-based -27 nor ChatGPT's review

**N1 — §6's "2δ needs about the same" understates the 80%-power requirement ≈2.3× (p. 8).** The draft: "Reaching L ≥ δ for a true effect of 2δ needs about the same [as bringing the half-width down to δ]." That equality holds only for the *expected* bound (≈50% power: n = 3,506 at H-SYS parameters — identical to the half-width figure by construction). At the draft's own 80%-power convention the requirement is ((2.4865 × 1.8)/0.05)² = **≈8,013** independent trades (H-SYS-1 parameters) and ((2.4865 × 2.6)/0.10)² = **≈4,179** independent events (H-BUY-P parameters). Correct the sentence or delete it; as written it will mislead the §15 feasibility decision (expand the sample vs accept UNDERPOWERED FOR PASS).

**N2 — 7A's gap exclusion removes exactly the subpopulation where the exit arms differ most (p. 9).** "Events that gap below the initial stop are excluded from all arms." Symmetric, and defensible for a clean paired set — but a gap-through is where E1 (fill at the open) and E0 (ride to the close, then next open) diverge maximally, in both directions. A 7A verdict therefore generalises only to non-gapping entries. The draft's existing 7A caveat covers entry provenance, not this. v0.3 should state the limitation beside 7A. (7C retains those trades, so the system-level question is still answered; the flag is about 7A's stated scope.)

**N3 — §13 register still names the E2 leg "H-EXIT-2" (p. 18).** §§4/6/7 renamed it **R-EXIT-2** (robustness, no verdict, no alpha). The register row (registered 2026-10-24) keeps the H- prefix, inviting a future reader to count it in the Holm family. Rename the row to R-EXIT-2 with a cross-reference.

**N4 (minor) — P7's completion evidence is not countable as written (p. 3).** "Ledger count exceeds the 590 candidates plus gap skips" parses two ways. Restate as separate counts: all-fire total = standalone candidates + suppressed fires + gap skips, each class reported.

---

## 5. What survives into v0.3 (consolidated, delta-only)

1. R2-revised: p. 1 strict figure (≈1,392) beside/replacing "roughly 700"; F6 floor-arrival ≈13–14 months at stated rates; power report publishes per-endpoint strict-δ power (own δ, allocated α, paired SDs, design effect).
2. N1: correct or delete the 2δ sentence (p. 8).
3. R6-revised + R19: P9 staged and field-scoped; per-cost-view ledgers committed, or all parity claims scoped to the 4 bps C1 view; the 185-vs-187 divergence resolved on record.
4. R10-revised: Stage A composition + edge-rule reading stated under each §9 outcome.
5. R11-revised: open-at-boundary treatment stated for H-SYS-1 / H-EXIT-4, with open count + marked value beside the verdict; DEV restatement censoring treatment stated.
6. R12-revised: portfolio return reported beside mean R in 7C.
7. R13-revised: block unit reconciled with the frozen contract (40-bar/calendar-session circular), or the deviation + diagnostic recorded at freeze.
8. R8-revised: feasibility report adds dropped-count + composition summary (outcome-blind).
9. R16-revised: one sentence labelling the historical DEV drawdown a lower bound until P1 lands.
10. R18-revised residue: the two 0.05 ATR constants labelled declared modelling assumptions.
11. N2, N3, N4: 7A scope sentence; register row renamed R-EXIT-2; P7 evidence made countable.
12. Answers supplied (not redlines): P2 = live-count semantics; P6 = no notional cap + notional reporting spec (-27 §§2.2/2.6).

**Bounds held:** review text only — no freeze, no runs or backtests, no strategy re-execution, no holdout access, no vendor calls, no frozen-source edits, the -22 pilot untouched. Concessions above are exact: where the draft already resolves an item, the redline is withdrawn, not narrowed by courtesy; where a residue stands, it is quoted against the page.

— Muse

---

## ERRATUM — 2026-10-25 — N2 wording corrected (per ChatGPT's independent -28 verdict)

Appended after ChatGPT's verdict on this memo (Issue #1 comment 6394587059; Slack thread TS 1792911195.795239, 2026-10-25 02:53 ET: **-28 PASSES at 099cd84**, arithmetic and the 7C correction verified, one wording fix required — this erratum). The original N2 text in §4 is retained unchanged above, for the record; this erratum supersedes its mechanism wording only.

**What p. 9 actually says** (pinned PDF at commit 02568b2, SHA-256 `01c4fff0c94cbf1d48f420b4e71619b7f477b07deaacd76705e9ca788abf00ae` — re-verified byte-exact at this erratum): Study 7A's entries are "the de-clustered signal events from section 5, run as standalone trades," and the page states: **"Events that gap below the initial stop are excluded from all arms."** Read with the same page's construction — entry at the next bar's open; the initial stop fixed from the signal bar (signal-bar close − 1.5 × ATR(14)) — and with the draft's own entry-side gap class (P7, p. 3: signals "skipped for gaps"), the exclusion concerns events whose **next-bar entry open is already below the signal-bar stop threshold**: entries that would open already stopped — never-valid entries. It is **not** an exclusion of gaps through a held position's stop; a held position's gap behaviour is part of what the exit arms themselves govern.

**Correction to N2's mechanism.** N2's sentence — "a gap-through is where E1 (fill at the open) and E0 (ride to the close, then next open) diverge maximally, in both directions" — mislocates the divergence in the hold. Under the corrected reading the divergence sits at the entry bar: an event that opens already below its stop is a case where an immediate-exit convention and a close-triggered convention cannot behave alike from the first bar onward.

**Disposition: the scope point SURVIVES, rescoped.** ChatGPT's verdict reaches the same conclusion ("its substantive point still stands because excluding those events removes an important region where E0 and E1 would behave differently"), and the memo concurs on the text: a 7A verdict generalises only to entries that open at or above the initial stop threshold; 7A is silent on the never-valid-entry subpopulation. The v0.3 action is unchanged in kind — state the limitation beside 7A (carried in §5 item 11) — with the corrected wording: the limitation concerns the pre-entry gap exclusion (next-bar entry open below the signal-bar stop), not gaps through a held stop. **7C retains all trades, so the system-level question was unaffected either way.**

**Nothing else in this memo changes.** All other dispositions, the arithmetic section, N1, N3, N4, and §5 stand as written. Gates unchanged per the verdict: the preregistration is not frozen; the 25 bps 185-vs-187 ledger gap remains unresolved; the P1/P4/P7/P8 implementation gates remain HOLD; no performance run, holdout access, or S1 action is authorised.

— Muse
