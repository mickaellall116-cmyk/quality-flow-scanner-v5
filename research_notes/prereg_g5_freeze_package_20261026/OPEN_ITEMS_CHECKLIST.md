# Open Items Checklist — at the G5 freeze candidate (2026-10-26)

State of every item that remains open when the G5 freeze package is
presented. Closed items are listed once, at the end, for orientation;
the operative content is the open list. Owners and closing conditions
are as recorded in `FREEZE_CHECKLIST_V10.md` (as amended by v1.0.1,
the v1.0.2 addendum, and the closure addendum).

## Open — signature gate

| # | Item | Owner | What closes it |
|---|---|---|---|
| G5 | **Signed freeze of v1.0** (tag + hash; document locked) | **Mike** | Mike adopts the decision text in `G5_DECISION_TEXT.md` (this package) against the manifest in `FREEZE_MANIFEST.md`; adoption logged in a freeze commit. **Not yet given.** C1 (independent review) and A5 both closed 2026-10-26, so G5 is the only remaining §15 freeze-path gate |

## Open — must close before any tier opens

| # | Item | Owner | Status / what closes it |
|---|---|---|---|
| O4 | 7A paired SDs (H-EXIT-1, H-EXIT-3) entered into the freeze record | Muse (execution); ChatGPT (review + replication) | **BLOCKED ON MIKE'S DIRECT GO.** The computation is not authorized by anything in the record (closure addendum). Procedure is prepared and ready to run: `O4_PROCEDURE.md` (this package) — variance-only, pooled arm-difference SDs on DEV, no group differences. Path: procedure review → Mike's direct GO → run → blind replication → entry into `POWER_REPORT.md` §4 (closes B9 with it) |
| O5 / P5 | Per-fill config hash produced and pinned | Muse | **BLOCKED — referent ambiguity, stated exactly in `MECHANICAL_CHECKS.md`.** The frozen C1 config (`EXPERIMENT_CONFIG` in the -13 driver; canonical pin `87b8285a…`, reproduced during this preparation) records the flat Stage-1 cost views, not the §8 per-fill conversion; the new per-fill config that §3 P5 names as the completion evidence does not exist in the record yet. Closes when the per-fill config artifact is produced under the P9 Stage-2 staging procedure and its SHA-256 is pinned in the freeze record |
| O6 | Per-tier §5 pool counts at staging | Muse | **Partly recorded; per-event sub-item BLOCKED on staging.** Recorded now from the frozen record (`MECHANICAL_CHECKS.md`): Tier 2 = 19 names, Tier 3 = 11 names, Stage-A universe = 30; DEV feasibility at frozen step (c): 311 events, 71 dropped (22.83%), 240 retained. The per-event pool counts for Tier 2 / Tier 3 require running the §5 matching code over the sealed holdout window and are produced at staging, outcome-blind, before that tier's G7 GO |

## Open — stage gates

| # | Item | Owner | What closes it |
|---|---|---|---|
| O7a | Stage B F2 — feed-qualification verdict (Twelve Data pilot) | Adjudication (ChatGPT checklist) | Pilot finalization Mon 2026-11-02 ~08:10 ET + independent review of the completed pilot; verdict recorded before any Stage B collection design is finalized |
| O7b | Stage B — ongoing-collection rights basis beyond Basic | Mike (decision) | A rights basis for ongoing collection (e.g. a higher Twelve Data tier or another qualified route), decided separately. Recorded condition: the pilot is strictly feed evaluation on Basic; a successful pilot does **not** authorize ongoing collection on Basic |
| O8 / G7 (Stage A) | Stage A access GO — the single two-person, logged session that opens the sealed holdout capture (receipt-chain re-verification, read-only mount, one frozen script run) | **Mike** | Mike's separate explicit G7 access GO for Stage A. **Not given.** Preconditions for the session are in `stage_packages/` (v1.0 package); O4 need not close for the session's non-verdict legs, but no verdict is read until the applicable freeze-procedure items close |
| O8 / G7 (Stage B) | Stage B Tier 4 GO — declares collection mode (signal-only is the default if the GO is silent) | **Mike** | Mike's separate explicit Tier 4 GO, after O7a and O7b close. **Not given** |
| O8 / G7 (per tier) | A separate explicit GO for **each** tier opening, in §11 stage order | **Mike** | Given per tier, never in bulk. **None given for any tier** |

## Standing (never closed by the freeze)

| # | Item | State |
|---|---|---|
| D1 | Holdout (2023-10-19 → 2024-09-15) | SEALED until its own access GO (G7) |
| D2 | Production / V5.4 entries | PAUSED (FAIL for promotion, 2026-10-03) |
| D3 | S1 shadow cohort | LAUNCH_HOLD (separate authority) |
| D4 | G4 / VBASIS | UNADOPTED |
| D5 | Original C1 (strategy) verdict | FAIL — closed, not reopened |
| D6 | DEV status | EXPLORATORY — no validated edge claimed |
| D7 | Tier 2 standing | SUPPLEMENTARY under the §9 Partly outcome |

## Closed, for orientation (2026-10-26)

C1 independent review — **CLOSED** (ChatGPT PASS on v1.0.2, Issue #1
comment `6430481827`). B1 (§9 audit + A5) — **CLOSED** (closure
addendum `c31c613`; A5 = Mike's NO, comment `6431596885`). O9 (Tier 3
12th slot) — **CLOSED** (APPROVE the 11-name list, comment
`6430214449`). B2 economics-first contract, calendar, E3 Mode A, S2
retirement, P10, P11, power report (subject to O4 residue) — closed
as recorded in the checklists of the frozen set.

**Nothing in this checklist is closed by the G5 freeze itself except
the document lock.** Acceptance is not authority to run.
