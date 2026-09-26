# Fundamental momentum beside Quality Flow — research proposal

**2026-09-26 | Status: proposal / data feasibility only. No score has been computed and no return has been inspected for this proposal.**

## Decision and scope

Mike authorized work on the Navellier-inspired idea after discussing a fundamental momentum score as a separate research/ranking layer. The video transcript describes themes, not the proprietary Stock Grader formula. The six weights floated in conversation (30/20/15/15/10/10) were illustrative, not an optimized or validated model. Do not call a reconstruction of Stock Grader authentic.

This proposal can produce an **observation-only sidecar** for Quality Flow candidates if trustworthy, historically as-seen fundamentals exist. It cannot change V5.4 BUY/EXIT, `rs_top2`, position sizing, slot/heat handling, alerts, or the frozen ERD v0.1 study. A sidecar score is never a trade recommendation or a passed edge. Do not display a numeric score without an auditable source and coverage status.

### Family and research history

The old `selection_edge/FACTOR_MENU.md` already listed F7 earnings/revisions momentum as **data permitting**. `research_notes/research_mandate.md` subsequently closed universe-factor mining and parked all other edge hunting. This fresh instruction authorizes examining the fundamental idea, but does **not** erase that family history. Record it under `FAM-UNIVERSE-FACTOR-MINING / F7` and preserve all earlier inspected results. Reusing 2023–2026 history may teach us about implementation and effect size; it cannot be relabeled untouched confirmatory evidence. Any confirmatory test needs genuinely uninspected forward/holdout decisions and a frozen, independently anchored manifest before returns are opened. If the economic mechanism or family assignment is changed, log and review that decision before testing; do not mint a new family ID to reset the ledger.

## First gate: data feasibility, before a formula is frozen

Inventory the candidate feed fields and raw vendor documentation. The following must be demonstrable **per historical version** and permanent security ID, including dead, renamed, and acquired firms:

| Field | Required evidence | Blocking failure |
| --- | --- | --- |
| Analyst consensus EPS | Fiscal period, estimate definition and currency, contributor/sample count where supplied, original value, revision history, vendor `available_at`/delivery timestamp | Current consensus retrospectively joined to old dates |
| Actual EPS / surprise | Fiscal period, comparable adjusted-versus-GAAP definition, event publication and vendor delivery timestamps, as-seen revisions | Final restated actual substituted for first known actual |
| Revenue, operating income and margin | Original filing/release and version, period end, fiscal-calendar changes, vendor delivery timestamp | Period end treated as publication date |
| Forward growth | PIT next-fiscal-period estimates and PIT comparable prior actual/estimate; negative or near-zero denominators handled by a frozen rule | Present-day forward estimate on a historic row |
| Price/volume (only if kept) | Completed adjusted bars available at the decision time; adjustment as-seen policy | Daily close from after a 13:30 ET decision |
| Identity and universe | Effective-dated permanent security ID, security type, corporate actions, delistings, PIT universe membership | Joins by ticker alone or survivor-only export |

Require feed receipt timestamps with timezone and an append-only revision history. `event_at` is not a substitute for `available_at`; date-only fields are unusable for intraday scoring. Missing or ambiguous history stays `UNKNOWN`, never becomes zero or a neutral default. No synthetic “publish at next open” replacement in the primary test. Keep vendor-native fields immutable and document access, coverage, licensing, and the same decision clock as the frozen candidate population. Do a mechanically selected raw-row integrity audit before calculating any returns. If the feed does not support this, verdict **UNTESTABLE**; do not use present-day APIs or price momentum as an undisclosed stand-in for fundamentals.

## Proposed score to finalize only after the data audit

For discussion, the six suggested components are EPS revisions (30), forward EPS growth (20), revenue growth (15), last earnings surprise (15), margin change (10), and price/volume pressure (10). These numbers sum to 100 but are **not yet a preregistration**. The first four are the distinctive fundamental hypothesis; price/volume overlaps the existing technical selector, so its marginal information must be reported separately. Define and freeze, before any returns:

1. Exact field IDs, fiscal-period matching, GAAP/adjusted policy, growth denominators and clipping, revision lookback, surprise measure, margin comparison, currency and corporate-action rules.
2. Cross-sectional cohort and transformations to a 0–100 score, ties, sector/size controls if any, component eligibility and minimum history. Do not renormalize available weights when a component is missing; mark the score `UNKNOWN` under a preregistered completeness rule.
3. A single primary formulation and quartile comparison, exact decision timestamps, coverage gate, sample size and calendar years, benchmark, costs, portfolio replay, holdout, and numeric PASS/MAYBE/FAIL criteria. Other variants and component ablations remain diagnostics in the **same family**.
4. Manifest hash and both pre-performance provenance anchors required by `research_notes/decision_time_availability_audit_amendment_5.md`; pass the framework implementation gate (T1–T16 and T2C) and candidate PIT audit. The framework is specification READY, **not implementation PASSED** as of this proposal.

The 4H decision clock must come from the frozen manifest. The first US equity bar closes 13:30 ET and the second closes 16:00 ET on a full session (half-days follow the frozen calendar). A fact version is eligible only if `available_at + frozen_latency_buffer < decision_at`, with strict inequality; select the latest eligible as-seen version, fail closed on same-time conflicting values, and never accept a caller-supplied decision-time override. An eligible 16:01 release cannot be scored for the 16:00 decision. Preserve both raw and selected versions in the decision packet.

## Evaluation, in required order

1. **Integrity before performance:** prove field provenance, historical coverage by year/industry/size/survivorship, release timing and revision replay, permanent-ID mapping, conflict behavior, manifest/dual-anchor validation, and independent timing fixtures. A missingness placebo must use the frozen framework statistic and seed. Stop on a failed gate.
2. **Same-population diagnostic:** attach as-seen scores to *all canonical PIT candidates*, including busy/slot/heat skips, without changing any decisions. Report coverage and missingness by outcome and cohort. Among the unchanged 374 taken trades, compare predeclared score quartiles and within-bar rank versus realized R; account for overlapping episodes. This is descriptive, not an edge claim, because the historical sample has been inspected and trade selection is conditional.
3. **Selection test:** if diagnostics justify it and untouched holdout exists, predeclare exactly one way a score would compete for existing slots and rerun the **entire** $75k, 1%-risk, 6-slot, 5%-heat portfolio at the canonical realistic 50-bp round-trip cost and the 25/75/100-bp stress levels. Compare against unchanged `rs_top2` on the same universe and decision dates. Log baseline displacements, newly admitted replacements, losses from missing coverage, costs, drawdown, expectancy, PF, and return. Never infer portfolio improvement by removing low-score trades from a static trade list.
4. **Falsification:** year/regime splits, untouched forward/holdout, episode-block uncertainty, concentration by stock/sector/earnings season, leave-one-stock-out, low/high coverage strata, placebo/permuted scores, and adjacent predeclared parameter values without selecting a winner. Report the whole family ledger, including failures. A positive bucket chart alone is not PASS.

The canonical reference is `canonical_baseline/REBASELINE.md`: PIT 131-name universe, 374 trades, approximately **−0.0013R/trade at 50 bps**, PF 1.00, and 39.8% maximum drawdown, with only about seven effective overlap episodes. The earlier +0.239R estimate and 14 hindsight names are not the control. Current V5.4 remains paper-only at its precommitted checkpoints. ERD v0.1 keeps its separate vendor/timing integrity gate.

## Immediate implementation boundary

**Ready now:** vendor-field inventory, coverage query, raw-row audit design, manifest draft, sidecar packet schema (`security_id`, `decision_at`, `component_value`, `available_at`, `source_version`, `status`, `score_status`). Synthetic boundary fixtures may test clock and version-selection code without opening returns.

**Blocked now:** historical score computation, numeric live labels, performance replay, or production ranking. Those require a qualifying as-seen feed, complete anchored manifest, implementation-audit PASS, and a genuinely untouched confirmatory sample. Record `UNTESTABLE` rather than filling a gap with a lower-quality substitute.

## Independent Claude audit handoff

Claude is the independent replication and code auditor in the existing research workflow. Before any performance read, provide Claude with the immutable raw-field dictionary, data coverage report (with no returns), proposed manifest and hash, sidecar source and fixtures, decision-clock trace, and the first mechanically selected timestamp/version audit rows. Ask Claude to independently derive the expected eligibility and score inputs for boundary examples, check treatment of missing/conflicting revisions and dead securities, and verify that no score can affect V5.4 production outputs. File Claude's unedited findings in the research record. If Claude finds a material defect, freeze a dated amendment **before** inspecting returns and rerun the audit; do not rewrite or erase the original finding.

Claude cannot directly join the project mailbox or commit to this repository under the established communication constraints. Mike relays the exact audit back through ChatGPT to Muse at the audit gate. This proposal is a concrete review packet, not a claim that Claude has already reviewed it.

## Preliminary public-documentation check (2026-09-26; no vendor data accessed)

- Intrinio's [Zacks EPS Estimates endpoint](https://data.intrinio.com/documentation/web_api/get_zacks_eps_estimates_v2) documents consensus `mean`, estimate `count`, and `mean_7_days_ago` / `mean_30_days_ago` / `mean_60_days_ago` / `mean_90_days_ago`. Its listed `date` is **period end**. The published output-field list does not show a feed-delivery `available_at` or an append-only historical version ID. This is a documentation gap, **not proof** that a separately licensed delivery feed lacks those fields.
- Intrinio's [Zacks EPS Surprises endpoint](https://data.intrinio.com/documentation/web_api/get_zacks_eps_surprises_v2) documents the earnings date, reported-time bucket, non-GAAP EPS actual, and pre-release mean estimate. It does not itself prove when any particular historical record or correction first became available to a subscriber.
- Intrinio's [EPS Surprises product page](https://intrinio.com/products/eps-surprises) currently labels the feed Enterprise-only and says historical access requires a separate payment. The product-page FAQ says GAAP, while the API endpoint describes `eps_actual` as non-GAAP. Resolve the exact package/field definitions in a vendor data dictionary before combining surprise, estimate, and filing fields.

**Vendor question to resolve before purchase or replay:** Can the licensed feed deliver archived as-seen consensus snapshots and corrections, with original subscriber delivery timestamps, stable security/period identifiers, delisted coverage, and the historical records themselves for the intended test years? Obtain an actual sample and contractual field dictionary; a current API response or marketing claim is insufficient for this gate.
