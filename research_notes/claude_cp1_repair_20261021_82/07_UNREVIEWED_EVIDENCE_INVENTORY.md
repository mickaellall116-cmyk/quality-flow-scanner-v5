# ITEM 7 — UNREVIEWED EVIDENCE INVENTORY
## (Evidence that exists without an independent review of record)

"Independent review" means a reviewer other than the executing agent
(ChatGPT adjudication, Claude replication/audit, or Mike) with a
recorded verdict on the EVIDENCE ITSELF — not on a summary of it.
Statuses: NO_INDEPENDENT_REVIEW (none recorded), SCOPED_REVIEW_ONLY
(reviewed for a narrower question than the evidence supports),
PARTIAL (some paths reviewed, some not). Where the basis is the
program record rather than a file read in this task, it is labeled.

| # | Evidence | Path / pin | Status | Basis |
|---|---|---|---|---|
| 1 | Yahoo feed-repair r2 candidate (batch-prefetch fix, candidate `10ae732`) | `research_notes/YAHOO_FEED_REPAIR_R2_20261014.md`; candidate in the -81/-78 inventories | SCOPED_REVIEW_ONLY | ChatGPT's review was a SCOPED PASS on the repair design (program record); no independent re-execution of the candidate against live feed behavior is recorded. Deployed on Mike's GO 2026-10-14. |
| 2 | Yahoo r2 post-deploy observation closure (cycles 563/564/565 HEALTHY 250/250) | `research_notes/yahoo_r2_observation_closure_evidence_20261015/` | NO_INDEPENDENT_REVIEW | The closure evidence was produced by the executing lane and consumed by -77 as an input; no adjudication verdict on the package itself is recorded. Claude inventoried (not adjudicated) it in the -78 bundle, category 09. |
| 3 | Feed-recovery observation pin | `FEED_RECOVERY_OBSERVATION_PIN_20261014` (in -78 bundle, category 09) | NO_INDEPENDENT_REVIEW | Same basis as #2 — retained ordinary-observation evidence, never separately reviewed. |
| 4 | Shadow-observation safety suite results (S1–S6 PASS) | `research_notes/shadow_observation_design_20261021_80/` (7d7d6b7) | NO_INDEPENDENT_REVIEW | The -80 work result itself states the launch gates as: checks green (done) + ChatGPT adjudication (outstanding) + Mike's GO. The suite's PASS is self-reported by the executing lane until adjudicated. |
| 5 | Day-1 probe analyzer execution (-75) — NVDA and AAPL paths | `research_notes/td_probe_day1_rerun_20261021_75/` (8533a59/ee7f71c) | PARTIAL | ChatGPT's -76 independently recomputed the TSLA zero-volume decomposition from the snapshots (reviewed). No independent recomputation of the NVDA PASS path or the AAPL control path is recorded. The TSLA label question is item 4 of this package. |
| 6 | SPOT8 pilot execution receipts (SPT-01…08; 6 COMPLETE / 1 HOLD / 1 NOT ATTEMPTED) | pilot_harness lineage; summarized in the bridge record; receipts pinned in the -16…-19 packages | SCOPED_REVIEW_ONLY | The lineage qualification (TD_NEW_LINEAGE_QUAL_20261015; bridge record read in this task) reviewed the calendar facts the receipts exercised; the receipts as execution evidence for P2 remain under the standing P2 HOLD — qualification of the pilot as a data route was never granted. |
| 7 | Outside-claims sweep #4 execution (Inside-Bar Breakout: 312 trades, +0.216R @25bps, FAIL vs the +0.35R bar) | `pine_claims_inside_bar/` (program record) | NO_INDEPENDENT_REVIEW | The FAIL verdict against the pre-declared bar is recorded; no independent replication of the 312-trade execution is recorded. (The post-hoc wide-mother variant +0.269R is a lead only and is barred from this data regardless.) |
| 8 | BOSWaves long-only daily v3 rerun + SA-VWAP executions (verdicts of 2026-10-04) | research record, 2026-10-04 (program record) | NO_INDEPENDENT_REVIEW | Verdicts recorded as provisional FAIL / protocol-INCONCLUSIVE (BOSWaves) and not-distinguishable-from-zero (SA-VWAP); independent replication is precisely what Claude's CP1 forensic (fed by the -78 bundle) exists to provide and has not yet returned. The November full-831 BOSWaves re-run is also still outstanding. |

## Notes on scope

- This inventory enumerates evidence whose EXECUTION lacks an
  independent review of record. It does not list design/spec
  documents that were reviewed as documents (e.g., the -49…-58 route
  chain, the -59/-61 synthetic suites, the -25 preregistration
  chain): those carry adjudication records in their own packages.
- Absence from this table is not a claim of review; the table is
  bounded to the items the repair spec named (Yahoo r2 + test
  executions) plus the executions the current adjudication queue
  actually depends on.
- Closing any row requires a reviewer verdict pinned by hash against
  the evidence bytes — a Slack ACK is not a review (per Mike,
  2026-10-21: a Slack assignment is not completed work; the same
  standard applies in reverse to reviews).

**Status: DOCUMENTED.** Owner: Muse (inventory). Reviews owned by
ChatGPT / Claude as assigned in REPAIR_PLAN.md.
