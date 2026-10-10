# Tiingo ToS Compliance Inventory — 2026-10-10

**Task:** QF-TIINGO-TERMS-COMPLIANCE-INVENTORY-20261010-10 r1 (inventory only — nothing executed, nothing deleted)
**Authority:** ChatGPT adjudication Issue #1 comment 6100626737 (all Tiingo observer/fill/parity work HELD effective immediately)
**ToS source:** `research_notes/FEED_ROUTE_OFFICIAL_EVIDENCE_20261010.md` (Tiingo ToS updated 2026-10-06)
**Method:** zero API calls, zero spend, key never touched. Read-only filesystem + git + memory inspection.

## 1. Plan determination: STARTER (free tier)

Established from non-secret metadata only:
- `~/workspace/skills/tiingo/SKILL.md`: "Free-tier budgets apply (50 req/hour, 1000 req/day, 500 unique symbols/month)"
- Appendix line 17: Tiingo **Starter $0** = 500 unique symbols/month, 50 requests/hour, 1,000 requests/day, 1 GB bandwidth/month — exact match
- Memory logs (2026-10-04/07/08) show active management of the "500-symbol monthly cap" and "453/500 used" — free-tier behavior
- No billing records, no paid-plan evidence, no dashboard screenshot found

**Verdict: PLAN = STARTER.** §1.6(a) applies: no writing, saving, archiving, backing up, or otherwise retaining Tiingo Data OR Derived Products in any persistent/durable storage. Processing only transiently in volatile memory; must be permanently removed before the process/job/session ends.

## 2. Persisted artifact inventory

Base dir: `~/workspace/goals/vcp-fundamental-momentum-probe-v0-1/hidden_files/phase1a/` (VCP Phase 1A October EOD pull)

| # | Path | Data class | Purpose / date | Size | SHA-256 (trunc) | ToS mapping | Proposed disposition |
|---|---|---|---|---|---|---|---|
| 1 | `raw/eod/` (444 files, `A.json`…`Z*.json`) | **Raw Tiingo EOD bars** (open/high/low/close/volume/adj*, 2009-01-02 → 2026-10) | VCP 1A October batch pull, early Oct 2026 | 365 MB | manifest `74681c8beab9d51c` | §1.6(a) — raw data persisted on Starter | **DELETE** (cease/delete) |
| 2 | `raw/fund/` (3 files: AAPL, MSFT, WMT) | **Raw Tiingo fundamentals** (statementData cashFlow etc.) | VCP 1A pilot, Oct 2026 | 152 KB | manifest `05e5e6f838b08181` | §1.6(a) — raw data persisted | **DELETE** |
| 3 | `panels/panel.jsonl` | **Derived bars** — 39,672-row panel constructed from Tiingo EOD | VCP 1A panel build, 2026-10-03 | 12.9 MB | `553e9442145b1f5f` | §1.6(a) — Derived Product on Starter | **DELETE** |
| 4 | `results_phase1a.json` | **Derived aggregates** — interim Oct-batch results (already invalid for inference) | VCP 1A analysis, Oct 2026 | 9.7 KB | `c6b0f98a4a5baaba` | §1.6(a) — Derived Product | **DELETE** |
| 5 | `cik_validated.json`, `cik_resolved.json`, `cik_dropped.json`, `ticker_cik_history.json` | **Derived validation outputs** of the Tiingo EFTS pull process | EFTS validation, Oct 2026 | ~40 KB | — | §1.6(a) — tainted derived outputs | **DELETE** |
| 6 | `ledger.json` | Pull ledger (symbol lists per month, not bars) | Pull bookkeeping, Oct 2026 | 92 KB | `cb90e2d47ced904a` | Metadata, not Tiingo Data — but evidences the pull | **DELETE** with dataset (Mike decides if kept as compliance record) |
| 7 | `research_notes/orb_15m_random_benchmark_20261007.md` (committed) | **Derived aggregates** — ORB test result numbers computed from Tiingo 15m QQQ/SPY bars | ORB experiment, 2026-10-07 | 3.5 KB | — | §1.6(a) — Derived Product retained in git | **DELETE numbers per strict terms** — FLAGGED: destroys adverse research record; Mike chooses delete / paid plan / written exception |
| 8 | `pull_oct.log`, `backfill_oct.log`, `efts_validation.log`, `cik_history.log` | Pull/validation logs (symbols, counts — no bars observed) | Oct 2026 | ~20 KB | — | Metadata; §1.6(b)-style log deletion applies to paid plans | Note; delete with dataset |

**Not Tiingo data (no action):** `tiingo_observer/__pycache__/*.pyc` (compiled observer *code*, not data — 24 KB); `raw/edgar/`, `edgar_shares.json` (EDGAR-sourced); `month_ends.json`, `sp500_ticker_start_end.csv` (calendar/ticker metadata); observer gap-fills (transient in-memory only — no persisted fill artifacts found in `forward_test/` or `v54_forward/`; labels `TIINGO/IEX/OBSERVER` never written to disk); ORB raw `/tmp/qqq_15m*.json`, `/tmp/spy_15m*.json` (ephemeral — already gone; manifest pins hashes only).

**Totals:** 7 artifact groups requiring deletion under Starter terms (444 raw EOD files + 3 raw fundamentals files + 5 derived/metadata files). ~378 MB.

## 3. Immediate hold (recorded, effective immediately per 6100626737)

- Tiingo degraded-mode observer cron: CEASED — no further fills, no parity comparisons
- No new Tiingo API calls for any purpose (VCP November batch, ORB reruns, parity work)
- No use of retained Tiingo data to validate/reconcile any other dataset (§1.6(c) substitute-use prohibition — the validated dataset would also require deletion)

## 4. Mike's decision (pending — nothing executed)

Per the adjudication, Mike chooses among:
- **(a) Deletion/cessation** — delete all 7 artifact groups above, keep observer code only
- **(b) Paid plan** — upgrade Tiingo; retention permitted while active (with 30-day-style deletion on termination per §1.6(b))
- **(c) Written permission** — separate written agreement with Tiingo (not available for Starter/Power plans per §1.6(b))

## 5. Task state

- QF-TIINGO-TERMS-COMPLIANCE-INVENTORY-20261010-10 r1: COMPLETE (inventory only)
- Actual effort: ~15 min of 20-min budget
- Nothing deleted, no code changed, no API calls, no sealed-validation access

## 6. Amendment — adjudication 6101353568 (remaining 5-min budget, metadata only)

**Verdict on this report:** PASS as preliminary inventory report; HOLD for entitlement proof, completeness, classification, disposition.

**Corrections (supersede §1/§2/§4 wording above; original preserved as evidence):**

1. **PLAN UNKNOWN — TREAT AS STARTER.** The §1 "Verdict: PLAN = STARTER" overstates: free-tier budgets + 453/500 usage do not prove actual account entitlement. No billing/dashboard/account evidence exists. Treat as Starter for compliance purposes; do not assert it as fact.
2. **No blanket deletion verdict.** This inventory is NOT deletion-ready: 8 table rows vs 7 groups, incomplete full hashes/manifests, no enumerated git history, remote copies, backups, or cross-dataset lineage. Do not delete or rewrite git/history based on this report.
3. **Field-level provenance unresolved.** CIK/EFTS validation outputs, pull ledgers, and logs require field-level provenance before being called Tiingo-derived. Rows 5, 6, 8 above are marked PROVENANCE-PENDING, not confirmed Tiingo-derived.
4. **Prompt deletion, no grace period.** §1.6(b) requires *prompt* permanent deletion on paid-plan end/downgrade — there is no "30-day-style" grace. Do not import Twelve Data's 30-day rule. (§4's parenthetical is withdrawn.)
5. **Paid plan is not a retrospective cure.** A paid plan has not been demonstrated to cure existing Starter storage, nor is it blanket permission for prohibited validation/substitute use (§1.6(c)). Written exceptions are limited to eligible Start-up/Enterprise/Institutional accounts; no vendor contact or spend is authorized.
6. **Adverse-evidence preservation.** No adverse result may be silently reversed or promoted merely because its source is on hold. The ORB report row stays flagged for Mike's explicit decision.

**Mike's decision (concrete but not deletion-ready):** pursue account/permission clarification and a permitted paid route, OR cessation with a separately reviewed exact deletion plan. Neither purchase nor destructive disposition is inferred from this report.

**Amendment effort:** ~4 min (total ~19/20). Metadata only; no Tiingo data values inspected, no analyses run.
