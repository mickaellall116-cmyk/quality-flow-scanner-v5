# Feed-Route Decision Memo — 2026-10-10 (QF-FEED-ROUTE-DECISION-MEMO-20261010-08 r1)

**Scope:** Read-only, one pass, zero vendor calls/credits/spend/performance. Planning only.
**Consolidates:** Issue #1 comments 6043456992 (bounded recovery-path brainstorm, Mike-requested 2026-10-07) and 6043557374 (addendum: constant repair time must be factored in).
**Supersedes directionally:** RECOVERY_PATH_DECISION_MEMO_20261007.md (its Route 1 bounded pilot has since run three repair rounds and stopped).

## 1. Where the Twelve Data lane stands (why this memo exists)

Three bounded repair rounds (r1/r2/r3, Oct 10) are exhausted. Final adjudication (Issue #1 comment 6099848127):
- Stage-0 acquisition: accepted as plumbing-only WORK RESULT (2 AAPL calls, HTTP 200, hashes verified). Interval semantics now **resolved**: official Twelve Data API reference states `datetime` is interval-START.
- r3 packet: FAIL/HOLD for P4. Seven execution-critical wrapper defects remain: non-persistent retry/429 state across resumes, out-of-order credit accounting, PAG schedule/depth mismatch, fail-open revision linkage, overclaimed driver enforcement, quarantined bodies not preserved, incomplete registry sync.
- **Verdict:** TD full pilot / API acquisition / feed qualification / recovery performance / CP2 all HOLD. No r4 and no disguised repeat on unchanged evidence. Reopen only for materially new load-bearing evidence under a new Mike decision.

What the TD lane actually proved: the API works, the credit math is now exact (expected 91 / max 171 + 2 spent, Basic 800/day), and interval-START is officially documented. What it did not prove: an execution-ready acquisition wrapper, free-tier retention qualification (still UNKNOWN/HOLD per Terms §§2.2/2.3/16.1/16.2), or decision-impact (C2) readiness — which was already gated INSUFFICIENT, and the corporate-action leg was already excluded. Even a perfect pilot would have qualified acquisition/session checks only, not the historical backtest it was originally meant to accelerate.

## 2. Route comparison (evidence vs assumption marked)

### Route A — Prospective capture (forward-collecting bars ourselves, free source)

**What it is:** the already-running V5.4 forward-test engine: hourly cycles download 4H bars, evaluate the frozen signal, advance the paper ledger fail-closed. This IS prospective capture in production. Tiingo degraded-mode observer fills Yahoo gaps on degraded cycles.

| Item | Estimate | Basis |
|---|---|---|
| Implementation remaining | ~0 | **Evidence:** running now; hardened wrapper deployed (94 checks) |
| Review/rework | 0 rounds | **Evidence:** pipeline already reviewed; no new code proposed |
| Maintenance | ~15 min/week operator attention | **Evidence:** existing cron ops; DEGRADED cycles handled fail-closed automatically |
| Calendar time to evidence | ~50-signal checkpoint late Oct 2026; ~100-signal verdict late Nov 2026 | **Evidence:** frozen forward-test spec rates (~10 signals/week design rate; actual rate observed, not assumed) |
| Budget | 0 credits, $0 | **Evidence:** Yahoo + Tiingo free tiers |
| Worst case | Capture outage loses forward time (no backfill per standing rule); single-regime 10-week window | **Evidence:** Oct-7 branch incident cost model; standing no-backfill rule |

**Prerequisites:** none outstanding — already running.
**Stop criteria:** forward test halted >48h unresolved → escalate; sustained signal rate <5/week → extend timeline, do not lower the bar.

### Route B — Fresh Yahoo (continuing Yahoo Finance downloads, hardened)

**What it is:** Yahoo remains the live-cycle vendor under the existing fail-closed guards. No new hardening proposed — the guards are deployed and proven.

| Item | Estimate | Basis |
|---|---|---|
| Implementation remaining | ~0 | **Evidence:** hardened wrapper deployed |
| Review/rework | 0 rounds | **Evidence:** already reviewed |
| Maintenance | **Highest vendor-driven triage of the three** | **Evidence:** daily DEGRADED cycles; Oct 9 evening 169/250 symbols refreshed, then 0/250; Oct-1 silent AAPL bar rewrite → V3.6 HALT; entries suppressed during degraded cycles |
| Budget | 0 credits, $0 | **Evidence:** free |
| Worst case | Silent revision → HALT → downtime; chronic slowness suppresses entries for days | **Evidence:** observed Oct 1–10 |

**Prerequisites:** none — this is the status quo.
**Stop criteria:** multi-day 0/250 refresh with no recovery → escalate to Mike for a vendor decision. Do NOT invest new hardening effort: the degradation is vendor-side (slowness, silent revisions) and no harness change fixes the vendor.

**Honest note:** Route B is not really a separate route from A in practice — prospective capture currently runs ON Yahoo. It is listed separately because the decision "invest more in Yahoo hardening" must be explicitly declined: the observed failure modes (slow cycles, partial refreshes, silent backfills) are not fixable from our side.

### Route C — Reopen the Twelve Data lane

**What it is:** a fourth repair round toward P4 clearance and the 20-symbol pilot.

| Item | Estimate | Basis |
|---|---|---|
| Implementation remaining | 1+ repair rounds (~1–2 hrs agent work + review each) | **Evidence:** 3 rounds closed 19 fixtures yet 7 execution-critical defects remain; defect discovery rate is not decaying |
| Review/rework | 1–3 rounds per repair round | **Evidence:** every prior round found real defects |
| Maintenance | Credit budgeting per pull; bar-revision re-verification | **Assumption:** same as Oct-7 memo; unchanged |
| Budget if reopened | Expected 91 / max 171 credits (+2 spent), $0 | **Evidence:** R3 machine-checked manifest; Basic 800/day |
| Worst case | Another round finds another 7 defects; C2 stays INSUFFICIENT and corporate-action stays excluded, so the pilot's ceiling remains acquisition/session qualification — the historical acceleration it was built for never materializes | **Evidence:** C2 gating and corporate-action exclusion are already frozen |

**Prerequisites to reopen (ALL required):** (1) a new Mike decision — the standing stop explicitly requires it; (2) materially new load-bearing evidence — e.g., official Twelve Data free-tier retention qualification, or a fresh wrapper implementation clearing all 7 defects presented as new evidence, not a re-run of r3.
**Stop criteria:** already stopped. No r4 on unchanged evidence per 6099848127.

## 3. Total-effort comparison (constant repair time included, per 6043557374)

| | A: Prospective capture | B: Yahoo (status quo) | C: TD reopen |
|---|---|---|---|
| Build remaining | ~0 (evidenced) | ~0 (evidenced) | 1+ rounds (evidenced defect rate) |
| Review/rework | 0 (evidenced) | 0 (evidenced) | 1–3 rounds/repair (evidenced) |
| Recurring maintenance | Low, automated (evidenced) | High, vendor-driven triage (evidenced) | Medium, credit/revision (assumption) |
| Time to evidence | Late Oct / late Nov (frozen spec) | Prospective only | Weeks IF reopens AND clears P4 (conditional ×2) |
| Meets evidence bar? | Yes — the only route currently producing evidence | Partially — vendor, not evidence path | Only if P4 clears; ceiling already capped below original goal |

## 4. Recommendation — ONE route

**Route A: prospective capture via the already-running forward test, Yahoo retained as the vendor under existing fail-closed guards, zero new hardening investment, Twelve Data lane stays stopped.**

Rationale:
1. It is the only route producing evidence today. The forward test accumulates real signals toward the frozen ~50-signal (late Oct) and ~100-signal (late Nov) checkpoints with zero incremental build.
2. Route B's failures are vendor-side and unfixable from our side; the correct action is to decline further hardening investment, not to treat Yahoo as a project.
3. Route C's expected value collapsed: three repair rounds bought plumbing proof and exact credit math, but the remaining 7 defects are execution-critical, the reopen bar (new evidence + new Mike decision) is intentionally high, and even success would no longer deliver the historical acceleration it was designed for (C2 INSUFFICIENT, corporate-action excluded).
4. Sunk-cost guard: the ~2.5 hours of agent work plus review cycles in the TD lane are context for the defect-discovery rate, not a reason to fund round four.

**Next eligible actions under this route:** none beyond current operations. Weekly forward-test health check continues; ~50-signal checkpoint arrives on the frozen schedule. Any new feed proposal enters as a fresh idea with its own bounded qualification — not as a TD reopen.

## 5. Preserved constraints (unchanged by this memo)

- V5.4 production freeze: no strategy/code changes to the frozen system.
- Sealed holdouts: 4H holdout sealed; 11-month holdout sealed and underpowered-by-design (not a failure).
- TOP-50 KILL (Mike 2026-10-04): no retuning cutoff/interval/weights/S4; revival needs new held-out/forward evidence.
- NQ/NDX quarantine stands.
- #18/#19 and FVG preregs: HELD, not executed.
- Authority: Mike decides — no vendor acquisition, spend, production change, or strategy change without his explicit word. Claude checkpoint runs at the next experiment's raw-evidence stage; no automatic Claude invocation.
- Adverse-evidence rule: verified losses are evidence (corrected-grid −15.23R preserved; never tuned away).

## 6. Effort log

- Memo pass: ~30 minutes (read-only; two Issue #1 comments, prior memo, R3 packet, final adjudication, memory log).
- Zero vendor calls, zero credits, zero spend, zero performance computations.

*Pins: 6043456992, 6043557374, 6099848127 (final r3 adjudication); RECOVERY_PATH_DECISION_MEMO_20261007.md; TD_PILOT_READINESS_R3_20261010.md (commit f22d030); forward-test degradation memory/2026-10-10.md (169/250 Oct 9, 0/250).*
