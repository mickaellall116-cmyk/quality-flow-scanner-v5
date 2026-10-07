# Recovery-Path Decision Memo — 2026-10-07

**Requested by:** Mike (confirmed 2026-10-07, "Yes brainstorm")
**Scope:** Planning/public-doc only. NO acquisition, spending, performance, or frozen-system authorization.
**Constraint (held):** A new feed cannot recreate the missing original Yahoo 1H inputs or validate the old performance retrospectively. Historical forensic conclusions stay intact.

---

## 1. What we already have (sunk, reusable by all routes)

| Artifact | Pin / path |
|---|---|
| Offline harness v6 (50/50 synthetic tests, fail-closed) | commit `fd03906`, `research_notes/pilot_harness/` — remote blobs verified byte-identical 2026-10-07 |
| Frozen execution plan v6 | `research_notes/PILOT_EXECUTION_PLAN.md` (blob `a87e19cb…`) |
| Frozen strategy semantics | `pine_buy_signal` (pine_backtest.py, SHA `447a9a13…`), `resample_closed_4h_session_anchored` (scanner_rules.py, SHA `7db282dd…`) |
| Hardened live-cycle wrapper (fail-closed, 94 checks) | commits `f0032aa`/`295726f`/`f216eaa`/`4c5c15e` |
| Tiingo degraded-mode observer (running, hourly) | `tiingo_observer/`, key in Secure Vault |

Six review rounds are complete (ChatGPT 6037625281 → 6043633584). Each round found real defects; each was repaired. **That repair history is the evidence base for maintenance estimates below — not invented failure rates.**

---

## 2. Route comparison

### Route 1 — Fresh Twelve Data (free tier)

**Reusable:** everything in §1, plus the frozen v2 pilot packet (20 symbols, 1H pulls from 2026-04-01, 5000 outputsize).

**Remaining blockers (specific):**
1. **Endpoint-credit entitlements MISSING** — v3's unverified 2-credit assumption was withdrawn per standing rule; exact endpoint weights must be named with entitlement evidence *before* execution.
2. **C4 retention MISSING** — Twelve Data Terms §2.2(a) permits internal-use storage; §2.3(g) caps at "permitted timeframes specified in the Documentation" (none specified); §16.1 limits to subscription duration; §16.2 requires deletion within 30 days of termination. Indefinite immutable retention: **not evidenced**. Pilot is scoped as a bounded prospective screen only.
3. **Free-tier history depth unknown** — if 1H history does not extend to the 2026-04-01 warmup start for a symbol, decision-impact checks for that symbol are marked INSUFFICIENT (per frozen plan §2). 15-min delay on free tier; 8 credits/min, 800/day caps.
4. **ChatGPT spec clearance still pending** — execution is HOLD until cleared.

**Next deliverable:** Entitlement evidence + C4 analysis → ChatGPT spec clearance → run frozen v6 pilot.

**Effort (evidence vs assumptions):**

| Leg | Estimate | Basis |
|---|---|---|
| Implementation remaining | ~0.5–1 day | Harness done; only entitlement lookup + pilot run config remain. **Evidence:** harness is 50/50, committed. |
| Independent review/rework | 1–3 rounds | **Evidence:** every prior round (v3→v6) found real defects requiring repair. Expect the same. |
| Recurring maintenance | Credit budgeting per pull; re-verification if Twelve Data revises bars | **Assumption:** free-tier limits force slow, batched pulls. **Evidence:** the plan already scopes to bounded prospective screen because C4 is missing — retained-history maintenance is off the table. |
| Failure mode cost | If history < 2026-04-01: decision-impact checks become INSUFFICIENT → route degrades to acquisition/session checks only, i.e. nearly Route 3 with extra vendor complexity | **Evidence:** frozen plan §2 states this explicitly. |

**Stop/go:** GO only if (a) entitlement evidence obtained, (b) free-tier history reaches 2026-04-01 for all 20 symbols, (c) ChatGPT clears spec. STOP if any of (a)–(c) fails — do not weaken checks to compensate.

### Route 2 — Fresh Yahoo through the repaired pipeline

**Reusable:** everything in §1. The v6 harness is feed-agnostic (validates any 1H input); the hardened wrapper already runs against Yahoo daily.

**Remaining blockers (specific):**
1. **Silent bar revisions are structural.** 2026-10-01: Yahoo rewrote the already-snapshotted 2026-09-30 13:30 ET AAPL bar → V3.6 paper runner HALTed (fail-closed worked; root cause = vendor backfill, same as Stage C's 13 data_drifted). No harness fix prevents the vendor from rewriting history.
2. **Chronic slowness.** Multiple cycles DEGRADED — budget exhausted before staging, publish skipped. This is the vendor condition, not a harness bug.
3. **No retained 1H exists.** Retained cache is 4H on the defective grid (08:30/12:30 labels) — coarse session-structure reference only, not a 1H comparator. Any Yahoo historical backtest would be built on re-pulled data the vendor has already demonstrated it revises.

**Next deliverable:** Prospective Yahoo 1H capture through the hardened pipeline (fail-closed; never-rewrite guards stay on).

**Effort (evidence vs assumptions):**

| Leg | Estimate | Basis |
|---|---|---|
| Implementation remaining | ~0 (done) | Hardened wrapper deployed; v6 harness validates input. |
| Independent review/rework | 0–1 rounds | Pipeline already reviewed. |
| Recurring maintenance | **HIGHEST of the three routes** | **Evidence:** daily DEGRADED cycles requiring operator attention; Oct-1 HALT required manual triage; every silent revision needs never-rewrite guard verification. This burden is ongoing and vendor-driven — it does not decay with harness maturity. |
| Failure mode cost | A single undetected revision corrupts the evidence base; the never-rewrite guard converts corruption into HALTs, which convert into downtime | **Evidence:** Oct-1 HALT is the observed cost. |

**Stop/go:** GO for *prospective* capture (fail-closed handles Yahoo's flakiness). STOP for *historical* backtest — no retained 1H, and the vendor's demonstrated revision behavior makes re-pulled history untrustworthy as evidence.

### Route 3 — Narrow prospective capture (feed-agnostic)

**Reusable:** everything in §1. Capture starts now; data is clean by construction (every bar validated at ingest, never rewritten).

**Remaining blockers (specific):**
1. **Time to verdict.** No backtest — only forward-accumulated signals. At ~10 signals/week, a 50-signal interim read is ~5 weeks of clean capture; 100-signal verdict ~10 weeks. This is calendar time, not effort.
2. **Capture ops.** The pipeline must stay running; gaps are handled fail-closed (degraded, not invented).

**Next deliverable:** Start capture on the frozen signal universe this week.

**Effort (evidence vs assumptions):**

| Leg | Estimate | Basis |
|---|---|---|
| Implementation remaining | ~0–0.5 day | Harness + wrapper exist; only capture config. |
| Independent review/rework | 0–1 rounds | Same reviewed components. |
| Recurring maintenance | **LOWEST** — keep capture running; monitor DEGRADED flags | **Evidence:** the hardened wrapper's degraded-mode handling is proven (94 checks); no vendor-history qualification, no entitlement lookups, no retention-law analysis needed for data we generate ourselves. |
| Failure mode cost | A capture outage loses forward time (cannot backfill — missed bars stay missed per standing rule) | **Evidence:** Oct-7 branch incident showed the cost of state loss; the lesson is captured in AGENTS.md. |

**Stop/go:** GO as the primary evidence path. STOP only if capture cannot be kept running reliably.

---

## 3. Total-effort comparison (Mike's addendum: constant repair time included)

| | Route 1: Twelve Data | Route 2: Yahoo | Route 3: Prospective |
|---|---|---|---|
| Build remaining | 0.5–1 day | ~0 | 0–0.5 day |
| Review/rework | 1–3 rounds (evidenced) | 0–1 rounds | 0–1 rounds |
| Recurring maintenance | Medium (credit budgeting; C4-bounded) | **High (daily vendor-driven triage)** | **Low (keep capture alive)** |
| Calendar time to evidence | Weeks (if history qualifies) | Weeks (prospective only) | ~5 wks interim / ~10 wks verdict |
| Worst case | History insufficient → degrades to Route 3 with extra complexity | Silent revision → HALT → downtime | Outage → lost forward time |
| Meets evidence bar? | Only if (a)(b)(c) all clear | Prospective only; historical NO | Yes |

---

## 4. Recommendation

**Primary: Route 3 (narrow prospective capture).** It has the lowest credible total effort + maintenance burden that still meets the evidence requirements. The harness is done, the data is clean by construction, and there is no vendor-qualification repair loop.

**Parallel (bounded): Route 1 pilot.** The v6 pilot is already built and conditionally authorized; running it once ChatGPT clears the spec is cheap (0.5–1 day). If Twelve Data history qualifies, it *accelerates* the verdict with historical decision-impact checks. If it doesn't, we lose little and Route 3 continues unaffected.

**Not recommended as an evidence path: Route 2 historical.** Yahoo's revision behavior (Oct-1 AAPL rewrite, Stage C drift) disqualifies re-pulled history as trustworthy evidence. Yahoo remains the live-cycle vendor under fail-closed guards, but not the historical evidence vendor.

---

## 5. Bounded work budget + stop condition (Mike's addendum)

- **Route 1 pilot:** 2-week budget from today for entitlement evidence + ChatGPT spec clearance. If either is unresolved by 2026-10-21, **pause Route 1** — do not extend, do not weaken checks.
- **Route 3 capture:** start this week; weekly health check (capture alive, DEGRADED rate nominal).
- **Universal stop rule:** if any route fails the same acceptance check twice, simplify, choose a qualified alternative, or pause. No indefinite repair loop. Integrity checks are never removed to hit a deadline.
- **Sunk-cost guard:** the six completed repair rounds are context for estimating maintenance, not a reason to continue a route because of past investment.

---

*Evidence pins: harness v6 commit `fd03906` (50/50 tests, remote blobs verified 2026-10-07); plan v6 blob `a87e19cb…`; Oct-1 Yahoo AAPL rewrite → V3.6 HALT (memory/2026-10-01.md); Stage C vendor drift (research/canonical-stage-a). No vendor calls made. No spending.*
