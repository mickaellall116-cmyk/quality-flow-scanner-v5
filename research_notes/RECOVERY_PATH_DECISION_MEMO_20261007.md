# Recovery-Path Decision Memo — 2026-10-07 (v2, corrected per ChatGPT 6047556037)

**Requested by:** Mike (confirmed 2026-10-07, "Yes brainstorm")
**Scope:** Planning/public-doc only. NO acquisition, spending, performance, or frozen-system authorization.
**Constraint (held):** A new feed cannot recreate the missing original Yahoo 1H inputs or validate the old performance retrospectively. Historical forensic conclusions stay intact.
**Adjudication:** ChatGPT 6047556037 — ACCEPTED as planning input; route ranking and pilot clearance HOLD.

---

## 1. What we already have (sunk, reusable by all routes)

| Artifact | Pin / path |
|---|---|
| Offline harness v6 (50/50 synthetic tests, fail-closed) | commit `fd03906`, `research_notes/pilot_harness/` — remote blobs verified byte-identical 2026-10-07 |
| Frozen execution plan v6 | `research_notes/PILOT_EXECUTION_PLAN.md` (blob `a87e19cb…`) |
| Frozen strategy semantics (partial map — see §1b) | `pine_buy_signal` (pine_backtest.py, SHA `447a9a13…`), `resample_closed_4h_session_anchored` (scanner_rules.py, SHA `7db282dd…`) |
| Hardened live-cycle wrapper (fail-closed, 94 checks) | commits `f0032aa`/`295726f`/`f216eaa`/`4c5c15e` |
| Tiingo degraded-mode observer (running, hourly) | `tiingo_observer/`, key in Secure Vault |

Six review rounds are complete (ChatGPT 6037625281 → 6043633584). Each round found real defects; each was repaired. **That repair history informs maintenance estimates below as evidence of review burden — it is not a forecast of future failure rates.**

### 1b. Complete C1 stack prerequisite map (ChatGPT 6047556037 §6)

A claim of "reusable complete-system backtest" requires ALL of the following mapped with source pins — not only the two functions above:

| C1 component | Pin status |
|---|---|
| Entry: `pine_buy_signal` (structural + ADX≥20 + SAFE/VWAP + completed-bar) | PINNED (`447a9a13…`) |
| Candle construction: `resample_closed_4h_session_anchored` (09:30 ET anchor, DST handling) | PINNED (`7db282dd…`) |
| Ranking: C1 rank (rs_top2 cross-sectional tie-break overlay) | NEEDS MAPPING — pin not recorded in this memo |
| Sector caps / risk gate (C1 portfolio-construction) | NEEDS MAPPING — pin not recorded in this memo |
| Exits: structural stop; 50% at TP1; +1R arms Profit Protect (next-bar open); 30-bar max hold; stop wins ties | NEEDS MAPPING — described in forward-test spec, pins not recorded here |
| Sizing: 1% risk ($750), max 6 positions, max 2/theme, ~5% heat cap | NEEDS MAPPING — standing rule, code pin not recorded here |
| Market gate (logged per signal; Stage 1 frozen) | NEEDS MAPPING |

**No route may claim a reusable complete-system backtest until every NEEDS MAPPING row is pinned.** The two pinned functions are necessary but not sufficient.

**C1 reconciliation (ChatGPT 6048657174 §2; short, no remapping):** The existing sourced map at commit `aa77ee4`, `research_notes/system_map_sourced_20261004.md` (blob `ea747e66fa12932c4eee2c4c834c38945dbd8364`) already documents the as-studied C1: `gen_candidates` + `compute_features` + `simulate_stack`; rs top-2 when candidates contest free slots; five concurrent slots; sector cap two; 5% portfolio heat; 1% marked-equity risk per trade; S4 drawdown gate (equity ≤90% of peak → risk halves; ≥95% → restores). This is the **C1 backtest lineage only**. It does not describe the forward-test Mode B system (per-symbol busy control, intrabar stops, 30-bar max hold — separate lineage, Claude-reviewed 2026-10-04) and it does not revive the killed TOP-50 experiment. No forward-system settings are substituted for C1 here; no full remapping performed. Any complete-system backtest claim on a new feed must re-pin this map against the new feed's data before asserting reuse.

---

## 2. Route comparison

### Route 1 — Fresh Twelve Data (free tier)

**Reusable:** everything in §1, plus the frozen v2 pilot packet (20 symbols, 1H pulls from 2026-04-01, 5000 outputsize).

**Remaining blockers (specific):**
1. **Endpoint-credit entitlements MISSING** — v3's unverified 2-credit assumption was withdrawn per standing rule; exact endpoint weights must be named with entitlement evidence *before* execution.
2. **C4 retention: UNKNOWN/HOLD** — Official source: Twelve Data Terms (https://twelvedata.com/terms, updated Jan 1 2026). §2.2(a) permits internal-use storage; §2.3(g) caps at "permitted timeframes specified in the Documentation" (none specified in the public terms); §16.1 limits to subscription duration; §16.2 requires deletion within 30 days of termination. **What the terms do NOT establish:** tier-specific retention qualification for the free tier. Neither the memo nor ChatGPT's review establishes it. Recorded as **UNKNOWN/HOLD** — indefinite immutable retention is not evidenced. Pilot is scoped as a bounded prospective screen only.
3. **Free-tier history depth unknown** — if 1H history does not extend to the 2026-04-01 warmup start for a symbol, decision-impact checks for that symbol are marked INSUFFICIENT (per frozen plan §2). 15-min delay on free tier; 8 credits/min, 800/day caps.
4. **ChatGPT spec clearance still pending** — execution is HOLD until cleared.

**Next deliverable:** Entitlement evidence + retention analysis → ChatGPT spec clearance → run frozen v6 pilot.

**Effort (evidence vs assumptions separated):**

| Leg | Estimate | Basis |
|---|---|---|
| Implementation remaining | ~0.5–1 day | **Evidence:** harness is 50/50, committed. Only entitlement lookup + pilot run config remain. |
| Independent review/rework | 1–3 rounds | **Estimate informed by past repairs** (every prior round v3→v6 found real defects). Not a forecast — bounded scenarios: 0 rounds (clean pass) to 3+ rounds (if entitlement/retention evidence is contested). |
| Recurring maintenance | Credit budgeting per pull; re-verification if Twelve Data revises bars | **Assumption:** free-tier limits force slow, batched pulls. **Evidence:** plan already scopes to bounded prospective screen because C4 is missing — retained-history maintenance is off the table. |
| Failure mode cost | If history < 2026-04-01: decision-impact checks become INSUFFICIENT → route degrades to acquisition/session checks only, i.e. nearly Route 3 with extra vendor complexity | **Evidence:** frozen plan §2 states this explicitly. |

**Stop/go:** GO only if (a) entitlement evidence obtained, (b) free-tier history reaches 2026-04-01 for all 20 symbols, (c) ChatGPT clears spec, (d) retention qualification resolved (currently UNKNOWN/HOLD). STOP if any of (a)–(d) fails — do not weaken checks to compensate. **The 2-week deadline (§5) is a proposed ceiling on evidence-gathering, not permission for indefinite storage or acquisition.**

### Route 2 — Fresh Yahoo through the repaired pipeline

**Reusable:** everything in §1. The v6 harness is feed-agnostic (validates any 1H input); the hardened wrapper already runs against Yahoo daily.

**Remaining blockers (specific):**
1. **Silent bar revisions are structural.** 2026-10-01: Yahoo rewrote the already-snapshotted 2026-09-30 13:30 ET AAPL bar → V3.6 paper runner HALTed (fail-closed worked; root cause = vendor backfill, same as Stage C's 13 data_drifted). No harness fix prevents the vendor from rewriting history.
2. **Chronic slowness.** Multiple cycles DEGRADED — budget exhausted before staging, publish skipped. This is the vendor condition, not a harness bug.
3. **No retained 1H exists.** Retained cache is 4H on the defective grid (08:30/12:30 labels) — coarse session-structure reference only, not a 1H comparator.

**On new Yahoo historical studies (corrected per ChatGPT):** The inability to reconstruct missing old inputs does not categorically disqualify every newly snapshotted retrospective study. Each proposed study must be assessed separately on: reproducibility (can the pull be reproduced byte-identical?), revision policy (does the vendor document revision behavior?), adjustment policy (splits/dividends handling), universe/PIT integrity, and study purpose (what claim would the study support?). **Prospective records do not cure earlier evidence gaps.** No such study is currently proposed or authorized.

**Next deliverable:** Prospective Yahoo 1H capture through the hardened pipeline (fail-closed; never-rewrite guards stay on).

**Effort (evidence vs assumptions separated):**

| Leg | Estimate | Basis |
|---|---|---|
| Implementation remaining | ~0 (done) | **Evidence:** hardened wrapper deployed; v6 harness validates input. |
| Independent review/rework | 0–1 rounds | **Estimate:** pipeline already reviewed. |
| Recurring maintenance | **Highest of the three routes (conditional on continued Yahoo use)** | **Evidence:** daily DEGRADED cycles requiring operator attention; Oct-1 HALT required manual triage; every silent revision needs never-rewrite guard verification. This burden is ongoing and vendor-driven — it does not decay with harness maturity. |
| Failure mode cost | A single undetected revision corrupts the evidence base; the never-rewrite guard converts corruption into HALTs, which convert into downtime | **Evidence:** Oct-1 HALT is the observed cost. |

**Stop/go:** GO for *prospective* capture (fail-closed handles Yahoo's flakiness). Historical backtest: not proposed; any future proposal assessed per the five criteria above.

### Route 3 — Narrow prospective capture (feed-agnostic acquisition timing)

**Scope correction (ChatGPT 6047556037):** Route 3 is an *acquisition-timing approach*, not a separate data vendor. It **inherits the selected vendor's** outages, coverage gaps, rights/retention constraints, and revision risks. Ingest checks + immutable snapshots establish what was seen and detect specified defects — they do **not** make data "clean by construction." The phrase "data we generate ourselves" is withdrawn: derived bars remain subject to the underlying vendor's terms.

**Reusable:** everything in §1. Capture starts now on the selected vendor.

**Remaining blockers (specific):**
1. **Time to verdict (ASSUMPTIONS, not guarantees).** No backtest — only forward-accumulated signals. *Assuming* ~10 signals/week (the V5.4 forward-test design rate — **not an established cadence for a new study**), a 50-signal interim read is ~5 weeks; 100-signal verdict ~10 weeks. **Caveats:** signals may be correlated (reducing effective sample); sample power depends on the realized signal count, not the calendar; regime exposure of a 10-week window is narrow (a single regime, not a cycle). The existing forward-test 50/100 checkpoints do not automatically confer statistical clearance on a new study.
2. **Vendor-terms prerequisites (conditional).** Before capture begins on a vendor: confirm the vendor's terms permit the intended retention scope and duration; confirm coverage includes the signal universe; confirm outage/degradation behavior is acceptable under fail-closed handling. **If any prerequisite is unresolvable → UNKNOWN/HOLD, do not start another indefinite qualification cycle.**
3. **Capture ops.** The pipeline must stay running; gaps are handled fail-closed (degraded, not invented).

**Next deliverable:** Vendor-terms prerequisite check → start capture on the frozen signal universe.

**Effort (evidence vs assumptions separated):**

| Leg | Estimate | Basis |
|---|---|---|
| Implementation remaining | ~0–0.5 day | **Evidence:** harness + wrapper exist; only capture config. **Assumption:** vendor-terms check resolves without extended legal review. |
| Independent review/rework | 0–1 rounds | **Estimate:** same reviewed components. |
| Recurring maintenance | **Conditional: lower than Route 2's vendor-driven triage IF the selected vendor is more reliable than Yahoo; not "lowest" as a blanket claim.** Keep capture running; monitor DEGRADED flags. | **Evidence:** hardened wrapper's degraded-mode handling is proven (94 checks). **Assumption:** the selected vendor's outage rate is acceptable — not yet evidenced for any specific vendor. |
| Failure mode cost | A capture outage loses forward time (cannot backfill — missed bars stay missed per standing rule) | **Evidence:** Oct-7 branch incident showed the cost of state loss; lesson captured in AGENTS.md. |

**Stop/go:** GO as the primary evidence path **conditional on vendor-terms prerequisites resolving**. STOP if capture cannot be kept running reliably, or if a prerequisite is unresolvable (→ UNKNOWN/HOLD).

---

## 3. Total-effort comparison (Mike's addendum: constant repair time included)

**All estimates below are conditional; evidence vs assumption is marked per cell.**

| | Route 1: Twelve Data | Route 2: Yahoo | Route 3: Prospective |
|---|---|---|---|
| Build remaining | 0.5–1 day (evidenced) | ~0 (evidenced) | 0–0.5 day (evidenced + assumption) |
| Review/rework | 1–3 rounds (**estimate** informed by past repairs; scenarios: 0 to 3+) | 0–1 rounds (estimate) | 0–1 rounds (estimate) |
| Recurring maintenance | Medium, C4-bounded (assumption: credit budgeting dominates) | High, vendor-driven triage (evidenced: daily DEGRADED, Oct-1 HALT) | Conditional — lower than Route 2 IF vendor reliable (assumption, not evidenced) |
| Calendar time to evidence | Weeks, IF history qualifies (conditional) | Weeks, prospective only | ~5 wks interim / ~10 wks verdict (**assumptions**: ~10 sig/wk cadence, uncorrelated signals, single-regime exposure noted) |
| Worst case | History insufficient → degrades to Route 3 with extra complexity | Silent revision → HALT → downtime | Outage → lost forward time; vendor terms block retention |
| Meets evidence bar? | Only if (a)(b)(c)(d) all clear — currently (a),(d) UNKNOWN/HOLD | Prospective only; historical per five-criteria assessment | **Conditional** on vendor-terms prerequisites + realized signal rate |

---

## 4. Recommendation (unchanged in direction, corrected in justification)

**Primary: Route 3 (narrow prospective capture), conditional on vendor-terms prerequisites.** Among the routes, it has the lowest *evidenced* maintenance burden that can meet the evidence requirements — no vendor-history qualification loop, no entitlement lookups. The "lowest maintenance" claim is conditional on the selected vendor being more reliable than Yahoo's demonstrated behavior; it is not a blanket property of prospective capture.

**Parallel (bounded): Route 1 pilot.** The v6 pilot is already built and conditionally authorized; running it once ChatGPT clears the spec is cheap (0.5–1 day). If Twelve Data history qualifies AND retention is resolved, it *accelerates* the verdict with historical decision-impact checks. If either fails, we lose little and Route 3 continues unaffected. **The 2-week budget is a ceiling on evidence-gathering, not acquisition permission.**

**Route 2 historical:** not proposed. Any future retrospective study assessed on reproducibility, revision policy, adjustment policy, universe/PIT, and study purpose — not categorically ruled in or out. Yahoo remains the live-cycle vendor under fail-closed guards.

---

## 5. Prerequisite / stop table (explicit)

| # | Prerequisite | Route | Status | Stop action if unresolvable |
|---|---|---|---|---|
| P1 | Endpoint-credit entitlements with evidence | 1 | UNKNOWN/HOLD | Pause Route 1 |
| P2 | Free-tier 1H history reaches 2026-04-01 (all 20 symbols) | 1 | UNKNOWN (no vendor calls made) | Degrade to acquisition/session checks |
| P3 | Retention qualification under Twelve Data Terms §§2.2/2.3/16.1/16.2 | 1 | UNKNOWN/HOLD | Bounded prospective screen only; no indefinite retention |
| P4 | ChatGPT pilot-packet spec clearance | 1 | HOLD (pending) | No execution |
| P5 | C1 stack fully pinned (§1b — all NEEDS MAPPING rows) | 1, 2-hist | NOT STARTED | No "complete-system backtest" claim |
| P6 | Vendor-terms check: retention scope, coverage, outage behavior | 3 | NOT STARTED | UNKNOWN/HOLD — do not start indefinite qualification |
| P7 | Realized signal rate supports interim/verdict timeline | 3 | ASSUMPTION (~10/wk) | Extend timeline; do not lower bar |
| P8 | Retrospective study five-criteria assessment (reproducibility, revisions, adjustments, universe/PIT, purpose) | 2-hist | NOT PROPOSED | No historical study |

**Universal stop rule:** if any route fails the same acceptance check twice, simplify, choose a qualified alternative, or pause. No indefinite repair loop. Integrity checks are never removed to hit a deadline.
**Sunk-cost guard:** the six completed repair rounds are context for estimating maintenance, not a reason to continue a route because of past investment.

## 6. Bounded work budget (Mike's addendum)

- **Route 1 pilot:** 2-week ceiling from 2026-10-07 for entitlement evidence (P1) + retention analysis (P3) + ChatGPT spec clearance (P4). If any is unresolved by 2026-10-21, **pause Route 1** — do not extend, do not weaken checks. This ceiling covers evidence-gathering only; it does not authorize acquisition or storage beyond the terms.
- **Route 3 capture:** vendor-terms check (P6) first, then start; weekly health check (capture alive, DEGRADED rate nominal).
- **Effort logging:** log actual hours in three buckets — initial work, review/rework, maintenance — per experiment. Estimates above are replaced by measured hours as work proceeds.

---

*Evidence pins: harness v6 commit `fd03906` (50/50 tests, remote blobs verified 2026-10-07); plan v6 blob `a87e19cb…`; Oct-1 Yahoo AAPL rewrite → V3.6 HALT (memory/2026-10-01.md); Stage C vendor drift (research/canonical-stage-a). Official terms: Twelve Data Terms https://twelvedata.com/terms (updated Jan 1 2026), §§2.2(a), 2.3(g), 16.1, 16.2 — tier-specific retention qualification NOT established. No vendor calls made. No spending.*
