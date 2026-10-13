# Tiingo Disposition Proposal — 2026-10-12 (PROPOSAL ONLY — nothing executed)

**Task:** bounded disposition-plan build from existing inventory + applicability evidence + filesystem metadata.
**Authority:** Mike, main chat 2026-10-12 22:07 EDT ("Yes do whatever chat got says"), approving ChatGPT's Tiingo package (Issue #1 comment 6129566895: cease Tiingo as prospective route; prepare a precise disposition plan for Mike's review).
**Sources (only):** `research_notes/TIINGO_TERMS_COMPLIANCE_INVENTORY_20261010.md` (incl. amendment 6101353568), `research_notes/TIINGO_APPLICABILITY_EVIDENCE_NOTE_20261012.md`, and filesystem metadata (paths, names, sizes, counts via `ls`/`du`, git log metadata). **No retained Tiingo data file contents were opened, parsed, or processed. No deletion. No vendor contact. No API calls. No purchase.**
**Governing facts (from the evidence note):** plan UNKNOWN — TREAT AS STARTER; account created ~2026-09-30 (pre-Oct-6 update); §1.6(a) retention prohibition on Starter likely predates the Oct 6 update (secondary evidence, two third-party audits of the "updated 2026-08-05" text); no amendment-notice email found in the registered inbox; paid plan is NOT proven to cure earlier retention; §1.6(b) written-agreement exception is NOT available for Starter or Power.

Base directory for items 1–3 and 6: `~/workspace/goals/vcp-fundamental-momentum-probe-v0-1/hidden_files/phase1a/` (total tree: **381 MB**, metadata-verified 2026-10-12).

---

## 1. Raw Tiingo data files — deletion candidates (highest confidence)

| Item | Path | Count | Size (metadata-verified) | Provenance |
|---|---|---|---|---|
| Raw EOD bars | `phase1a/raw/eod/` (`A.json` … `Z*.json`) | **444 files** | **365 MB** | Tiingo EOD pull, VCP Phase 1A October batch, complete 2026-10-03 04:04 UTC (453/453 ledger; 444 OK + 9 fail-closed 404s) |
| Raw fundamentals | `phase1a/raw/fund/` (`AAPL.json` 46,331 B; `MSFT.json` 49,967 B; `WMT.json` 52,578 B) | **3 files** | **152 KB** | Tiingo fundamentals pilot, Oct 2026 |

**Proposed disposition:** DELETE, under the cessation route. These are the clearest §1.6(a) items — raw vendor data persisted on a treated-as-Starter account. No research record depends on the raw files themselves (results derived from them are handled in §2/§5).

## 2. Derived artifacts — deletion candidates (lineage per inventory)

| Item | Path | Size | Derives from | Notes |
|---|---|---|---|---|
| Derived panel | `phase1a/panels/panel.jsonl` | 12,888,079 B (~12.9 MB) | Raw Tiingo EOD (`raw/eod/`) — constructed 2026-10-03, 39,672 rows per inventory | §1.6(a) Derived Product; reconstructible to underlying bars — does NOT qualify as a §1.6(c)-style non-reconstructible aggregate |
| Derived aggregates | `phase1a/results_phase1a.json` | 9,701 B | The panel / October batch analysis | Interim October-batch results; already invalid for inference (October result must not be cited). §1.6(a) Derived Product |
| Panel process log | `phase1a/panels/quarantine.log` | 24,699 B | Panel build process | **Not in the 2026-10-10 inventory** — surfaced by metadata. Proposed: delete with the panel, subject to Mike's call on log retention (§6) |

**Proposed disposition:** DELETE with §1. Deleting the panel and results also permanently forecloses any re-analysis of the October VCP dataset — that dataset is already invalid and must not be rerun, so no scientific loss is incurred beyond the record-keeping question in §5.

## 3. Independent / mixed-provenance items — NOT deletion candidates pending provenance clarity

Flagged separately per adjudication 6101353568 (field-level provenance unresolved). **None of these should be deleted under a Tiingo disposition without a separate provenance determination.**

| Item | Path | Size | What metadata/inventory shows |
|---|---|---|---|
| SEC EDGAR raw data | `phase1a/raw/edgar/` | 685 files, 6.9 MB | EDGAR-sourced (inventory: "Not Tiingo data — no action") |
| EDGAR outputs | `phase1a/edgar_shares.json` (1,527,034 B), `edgar_concepts.json` (34,120 B), `_tmp_edgar_shares.json` (376,403 B) | ~1.9 MB | SEC-sourced per filenames/pipeline; inventory lists `edgar_shares.json` as EDGAR-sourced |
| CIK / EFTS validation outputs — **PROVENANCE-PENDING** | `phase1a/cik_validated.json` (551 B), `cik_resolved.json` (5,021 B), `cik_dropped.json` (15,664 B), `ticker_cik_history.json` (**623,828 B**) | **~645 KB total** | Inventory row 5 called these "derived validation outputs of the Tiingo EFTS pull process"; the amendment **withdrew** that classification pending field-level provenance. EFTS is an SEC system; whether these files embed any Tiingo-sourced fields is UNKNOWN from metadata |
| SEC ticker map | `phase1a/sec_ticker_map.json` | 230,735 B | SEC-sourced by name; not in inventory — unclassified |
| Universe / calendar metadata | `phase1a/universe.json` (51,774 B), `month_ends.json` (2,882 B), `sp500_ticker_start_end.csv` | ~55 KB | Inventory lists `month_ends.json` and the CSV as calendar/ticker metadata, not Tiingo data; `universe.json` unclassified |
| Pull ledger — **PROVENANCE-PENDING** | `phase1a/ledger.json` | 92,454 B | Symbol lists per month, not bars (inventory). Metadata about the pull, not Tiingo Data — but it is also the primary compliance record that the pull happened, its scope, and its dates |
| Pull/validation logs — **PROVENANCE-PENDING** | `pull_oct.log` (13,695 B), `backfill_oct.log` (2,432 B), `efts_validation.log` (11,351 B), `cik_history.log` (3,537 B), `cik_validation.log` (32 B), `backfill_validated_efts.log` (1,361 B) | ~32 KB | Symbols/counts per inventory; no bars observed. §1.6(b) log-deletion language applies to paid plans; applicability on Starter UNKNOWN |
| Disposition manifest — **UNCLASSIFIED** | `phase1a/interval_disposition_manifest.json` | 49,182 B (modified Oct 8) | **Not in the inventory.** Created during the interval-repair chain; content not inspected (would require opening). Must be classified before any deletion pass touches the directory |
| Working documents — **UNEXAMINED** | `phase1a/CHECKPOINT.md`, `PIPELINE_STATE.md`, `RUN_PLAN_FROZEN_20261001.md` | — | Not in inventory. Whether they embed Tiingo-derived numbers is UNKNOWN; not inspected under this task's metadata-only limit |
| Observer code | `~/workspace/quality-flow-scanner-v5/tiingo_observer/__pycache__/*.pyc` | 24 KB | Compiled observer **code**, not data (inventory). No action |

**Proposed disposition:** RETAIN all §3 items until (a) field-level provenance is established for the PROVENANCE-PENDING group by a separately authorized inspection, or (b) the vendor inquiry answers what the terms require for process metadata/logs. EDGAR/SEC items are presumptively KEEP (independent source). The ledger/logs question — delete as tainted process artifacts vs keep as the compliance record of what was pulled and when — is Mike's explicit call (see §7).

## 4. Copies / backups

Metadata findings (2026-10-12):

- **The phase1a tree is NOT inside any git repository** (`git rev-parse` fails at the goals directory and at `~/workspace`). The raw files, panel, and §3 items therefore exist **only** as local filesystem copies — no git-history copies of the raw/derived data exist. Deletion of §1–§2 items, if approved, is a single-location operation with no history rewrite required.
- **No archives or backups found** in the VCP goal directory: filename search for `*.zip`, `*.tar*`, `*.bak`, `*backup*` returned nothing.
- **No second copy of `panel.jsonl`** anywhere under `~/workspace` (filename search).
- **ORB raw 15m files** (`/tmp/qqq_15m*.json`, `/tmp/spy_15m*.json`) are already gone (ephemeral `/tmp`); only hash pins in a manifest remain (inventory).
- **Git-retained copy — one item only:** the ORB report (§5) is committed in the scanner repo's git history (commits `e360a94`, `838bb89`). Any disposition of that report must account for history, not just the working-tree file.
- **NOT verified (open gap):** off-machine backups (cloud sync, Time Machine-style snapshots, VM snapshots) were not inspected — metadata checks covered this machine's workspace only. Whether any copy exists off-box is UNKNOWN.

## 5. Report containing Tiingo-derived numbers — the preservation tension (NOT decided here)

| Item | Location | Size | Content |
|---|---|---|---|
| ORB 15m random-benchmark report | `~/workspace/quality-flow-scanner-v5/research_notes/orb_15m_random_benchmark_20261007.md` | 7,368 B; committed (git history: `e360a94`, `838bb89`) | Aggregate result numbers computed from Tiingo 15m QQQ/SPY bars pulled 2026-10-07. ORB verdict is exploratory/HOLD; timing-edge and robustness claims already withdrawn |

**The tension, stated plainly:** a strict reading of §1.6(a) treats these numbers as a retained Derived Product on Starter → delete. But the standing research rule (adverse-evidence rule, 2026-10-03) says verified results — especially adverse/withdrawn ones — are evidence and must never be silently erased; the inventory amendment (6101353568, point 6) likewise keeps this row flagged for Mike's explicit decision rather than a blanket deletion. Deleting the numbers from the working tree also does not remove them from git history without a history rewrite, which carries its own record-integrity cost.

**Options proposed (Mike chooses; this proposal does not):**
- **(a) Redact in place:** replace the Tiingo-derived numbers in the report with a dated disposition note ("figures removed 2026-10-XX under Tiingo §1.6(a) disposition; methodology, verdict, and withdrawal record retained"), preserving the experiment's existence, method, and adverse verdict while removing the derived values. Git history would still contain the original — a complete cure requires (b) or vendor guidance.
- **(b) Delete file + history rewrite:** full removal including git history. Maximum terms-strictness; destroys the adverse record and sets a precedent of rewriting research history.
- **(c) Retain pending vendor answer:** hold the report unchanged until the vendor inquiry (question 4 — research aggregates) is answered; the numbers are aggregate backtest statistics, and whether §1.6(c)-style aggregate treatment can apply is one of the inquiry's explicit questions. Risk: continued retention in the interim.
- **(d) Retain with annotation:** keep the report, add a compliance annotation noting its disputed status. Weakest terms position; strongest record position.

## 6. Retention uncertainties and named gaps

1. **Plan entitlement UNKNOWN.** No billing/dashboard/account evidence; TREAT AS STARTER is a compliance posture, not a proven fact. (Vendor inquiry Q1.)
2. **Accepted terms version/date UNKNOWN.** Account created ~2026-09-30; accepted text presumed pre-Oct-6 ("updated 2026-08-05" per secondary audits) — not confirmed from account records; official prior text not recovered (Wayback step never completed). (Vendor inquiry Q1.)
3. **Notice dispatch unproven either way.** No amendment-notice email in the registered inbox; absence in the inbox does not prove non-dispatch (ChatGPT's caveat, 6129566895). (Vendor inquiry Q1.)
4. **Retrospective cure unproven.** Terms do not state that a Power upgrade covers pre-upgrade retention; §1.6(b) exception is unavailable for Starter/Power. (Vendor inquiry Q3.)
5. **Aggregate treatment unresolved.** Whether aggregate, non-reconstructible research statistics get different disposition treatment than raw/derived datasets — directly affects §5. (Vendor inquiry Q4.)
6. **Inventory size discrepancy.** The inventory grouped the four CIK files at "~40 KB"; metadata shows `ticker_cik_history.json` alone is 623,828 B and the group totals ~645 KB. The inventory's size accounting for row 5 is understated; classification, not size, is the blocker, but the record should be corrected if the plan proceeds.
7. **Unclassified files in the phase1a tree.** `interval_disposition_manifest.json` (49 KB), `sec_ticker_map.json` (231 KB), `universe.json` (52 KB), `panels/quarantine.log` (25 KB), and three working documents (CHECKPOINT / PIPELINE_STATE / RUN_PLAN) were not covered by the 2026-10-10 inventory. Any deletion pass scoped to the whole directory would sweep them unexamined.
8. **Field-level provenance of CIK/EFTS outputs, ledger, and logs** (adjudication 6101353568, point 3) — requires opening file contents, which no authorized task has done under the HOLD.
9. **Off-machine copies unverified** — cloud/VM/system backups outside `~/workspace` were not inspected (§4).
10. **Cross-feed validation status.** §1.6(c) prohibits using Tiingo data to validate another dataset (substitute use); no such validation was run on the retained files per the HOLD, but whether any pre-HOLD observer parity comparison constitutes substitute use is unadjudicated. (Vendor inquiry Q5.)

## 7. The decision Mike must make — and what execution would look like

**Decision (one of):**
- **A. Approve this plan as-is** — §1 + §2 deleted; §3 retained pending provenance; §5 handled per the option Mike names (a/b/c/d); §6 gaps accepted as recorded.
- **B. Approve with amendments** — e.g., different §5 option, ledger/logs kept as compliance record (or deleted), §3 provenance inspection authorized first.
- **C. Send the vendor inquiry first** (draft pinned in the evidence note, commit `f87b836`) and defer disposition until account-specific answers arrive — requires Mike's explicit send authorization; nothing is deleted in the interim and all HOLDs continue.
- **D. Neither now** — HOLD continues unchanged; data remains frozen, unused, and undeleted.

**Execution, if A or B is chosen, is a SEPARATE, separately-approved step — this proposal authorizes nothing:**
1. Pre-execution verification pass: enumerate the exact file list (full paths + full SHA-256 manifest) for §1–§2 items only, read back to Mike or posted to the bridge before anything is removed.
2. Execute deletion of exactly that list (filesystem delete; no git operations needed for §1–§2 since the tree is not version-controlled). §5 option (a) or (b), if chosen, is executed in the same pass as a separate, explicitly listed action.
3. Post-execution verification: re-run the metadata inventory on the phase1a tree; confirm §1–§2 paths absent, §3 items untouched; record sizes/counts removed in the bridge thread and Issue #1.
4. Record the disposition in memory + the compliance inventory (amended, not overwritten), including Mike's §5 choice and the §6 gaps that remain open.
5. The Tiingo observer code stays; all API holds lift only by Mike's separate word; the November VCP data question is unaffected (it needs a feed regardless).

---

*Prepared 2026-10-12, metadata + existing documents only. Proposal only — no deletion, no vendor contact, no API calls, no processing of retained data.*
— Muse
