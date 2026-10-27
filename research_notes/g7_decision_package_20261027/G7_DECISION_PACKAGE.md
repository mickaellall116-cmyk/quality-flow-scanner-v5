# G7 Decision Package — Tier Openings for BUY Validation (prepared 2026-10-27)

**PREPARATION ONLY. This package decides nothing and authorizes nothing.**
G7 is **not** given for any tier. No tier opens, no holdout data is
accessed, no computation is run, and no vendor call is made by the
preparation, acceptance, or reading of this package. It assembles, for
Mike's separate G7 decisions, exactly what each GO would and would not
authorize, the precondition state of record, the protocol ambiguities
that the frozen texts leave open (flagged in §5, **not** resolved
here), signable decision texts (§6), and a recommended sequencing
(§7).

**Basis.** The frozen protocol set, as adopted at G5: preregistration
v1.0 (`research_notes/prereg_v10_20261026/`, commit `4ffb8fb`;
`PREREG_V10.md` SHA-256
`29a0477a13e52ff4467193f69df7ef107048a8801f64c61f43de28d40d2850c6`;
bootstrap seed `2999475941474119668`), as amended by v1.0.1 (commit
`247a1c7`) and v1.0.2 (commit `4b45a3e`), closed out by the closure
addendum (commit `c31c613`), and frozen by Mike's G5 adoption
2026-10-27 (Issue #1 comment `6440943528`; G5 package commit
`503731183b4d9385059b83e1996b5bc3989ebe8d`, package manifest SHA-256
`81b881b3574fba5156107bcac0e53e27472dfc9c8fa8217e7f6de17f91b8975e`;
addendum commit `92aaa0a`, corrected at `4988f15`). Every protocol
claim below was checked against those committed documents (cited as
§n of `PREREG_V10.md`, or by file), not against chat summaries.

**State in one paragraph.** G5 is adopted: the methodology is locked,
including the B2 economics-first verdict contract (§11) and the §9
PARTLY CONTAMINATED outcome (Tier 2 supplementary, no PASS/FAIL
standing; Stage A verdict legs Tier-3-only). What remains before any
tier can open is a short, named list: the **O4** paired-SD estimate
(procedure and cost basis pinned; computation gated on Mike's direct
GO), the **P5** per-fill config hash (the artifact does not exist
yet), and the **per-tier §5 pool counts** (staging step over the
sealed window). Stage B additionally waits on the **F2** feed verdict
(Twelve Data pilot finalization, Mon 2026-11-02) and a separate
**rights-basis decision** for ongoing collection. Standing labels are
unchanged: holdout **SEALED**, production **PAUSED**, S1
**LAUNCH_HOLD**, original C1 verdict **FAIL**, DEV **EXPLORATORY**.

---

## 1. The decisions in front of Mike

Under §15, gate G7 is "a separate explicit GO for each tier opening"
(owner: Mike), with tiers opened "only in the stage order of §11."
Four separable decisions are assembled here:

| # | Decision | Text | Decision-ready when |
|---|---|---|---|
| 0 | Pre-G7 staging access for the per-tier §5 pool counts (resolves AMB-1 by ruling) | §6, Text 0 | Now — nothing else gates it |
| 1 | Stage A — the single holdout access session and run (Tier 3 verdict legs) | §6, Text 1 | When O4, P5, and the pool counts are in the freeze record |
| 2 | Stage A — Tier 2 supplementary legs (include / exclude within that same session) | §6, Text 2 | With Text 1 |
| 3 | Stage B — Tier 4 forward collection start (mode declared in the GO) | §6, Text 3 | When F2 (both legs) has closed and F3 parity evidence exists |

The O4 computation GO is **not** a G7 decision and is not bundled into
any text here: it remains Mike's separate direct GO, as recorded in
the closure addendum and `O4_PROCEDURE.md`. It is listed in §4
because it gates Text 1.

---

## 2. What a G7 GO would authorize

### 2.1 Stage A / Tier 3 — the verdict-bearing opening

A Stage A GO (Text 1) authorizes exactly the Stage A execution
package's single session and run:

- **The access session itself** (§2 firewall rule 3; Stage A package
  §4): two people present, session logged end-to-end, frozen code
  hash verified against the freeze record before any data access
  (any pin mismatch → STOP before access).
- **Seal verification and read-only access:** re-verification of the
  holdout capture files against their committed SHA-256 receipt
  chains (A3 discipline), read-only mount inside the private archive
  environment; raw bytes never leave that environment.
- **One run of the frozen orchestrating script, once, in its frozen
  order** (Stage A package §4, step 3): (a) all-fire census and
  de-clustering; (b) §5 matching (B-A primary baseline; B-T
  diagnostic) at the frozen ladder step (c); (c) the 7A paired legs —
  H-BUY-P (primary, 10 bars), H-BUY-S5/S20 (fixed sequence),
  H-EXIT-1 (E1−E0), H-EXIT-3 (E0−E3), R-EXIT-2 (robustness only, no
  verdict); (d) the 7B descriptive legs (non-gating); (e) the 7C
  full-system replays under E0 and E1 (see AMB-2, §5); (f) the P8
  telemetry journal written throughout the replay.
- **Verdict computation by the same frozen code** (§6/§11, B2
  contract): wider of the block-bootstrap and symbol-cluster
  intervals; Holm adjustment for the H-EXIT family; grades printed
  (CONFIRMED AT δ / PASS — economics-first / FAIL / INCONCLUSIVE);
  §12 diagnostics reported beside the verdicts, annotating only.
  The verdict-bearing legs are **Tier 3 only** (11 names: BE, ACN,
  IREN, CRDO, TWLO, AAOI, MPWR, SPOT, BABA, COF, BLK) under the §11
  Partly branch.
- **Capture and record:** all outputs hashed and committed as a
  result package (derived results only, no raw vendor bars); the
  §13 register marks Tier 2 and Tier 3-on-holdout **CONSUMED for
  this rule version**; one Stage A report issued from the captured
  outputs.
- **Pre-declared expectation** (Stage A package §3.6, written before
  any access so it cannot be renegotiated after): at DEV realized
  rates the window yields ~80 portfolio closed trades — below the
  100-trade floor — so **H-SYS-1 and H-EXIT-4 are expected to return
  INCONCLUSIVE-by-floor regardless of their estimates**; the paired
  legs (H-BUY-P, H-EXIT-1, H-EXIT-3) are Stage A's decisive content.
  Under §9, a STOP after outcome computation still consumes the
  window for this rule version.

### 2.2 Stage A / Tier 2 — supplementary legs

A Tier 2 inclusion decision (Text 2) authorizes, **within the same
single Stage A session and run**, the computation and reporting of
the Tier 2 legs (the 19 defect-free holdout names) as **supplementary
evidence**: reported beside, never inside, the confirmatory pool,
with **no PASS or FAIL standing** (§11 Partly branch; §2 tier table).
It is not a second opening and cannot be executed as one (AMB-3,
§5): the window is opened once, by the Stage A session, and is
consumed for this rule version by that access.

### 2.3 Stage B / Tier 4 — forward collection

A Stage B GO (Text 3) authorizes:

- **Collection start** under §10 (F1–F7), once F1–F5 are verified
  passing, on the qualified route only, in the **collection mode the
  GO declares** — signal-only is the default if the GO is silent
  (every candidate fire logged with full as-of state and its
  hypothetical entry/exit; no positions opened; the telemetry writer
  refuses EXECUTION records) or paper-execution (paper positions
  under the frozen rules; EXECUTION records written; the fill record
  is the evidence that can retire the §7/§8 fill assumptions).
- **The §10 discipline for the collection's life:** full-state P8
  telemetry from the first bar (F4); bars used **as received, never
  later revisions**; outages and missed signals logged and counted
  as unexecuted candidates, **never backfilled** (F5); interim looks
  restricted to parity and operations, **never performance** (F7).
- **The single verdict analysis** when the §6 validity floors are
  met and the 6-month minimum has elapsed (F6), assessed from counts
  alone. At DEV realized rates (≈7.5 closed trades/month) the
  100-closed-trade H-SYS floor is expected at roughly **13–14
  months** of collection.
- Stage B does **not** wait for Stage A, and Stage A does not wait
  for it (Stage B package §2, F1 note); only the §11 edge rule reads
  the two verdicts together ("edge supported" requires Stage B PASS
  on H-SYS-1 **and** Stage A not FAIL).

---

## 3. What no G7 GO authorizes

No text in §6, and no G7 GO of any scope, authorizes:

- **Live trading**, order placement, or any real-money activity.
- **Production activation** — the V5.4 production stack stays PAUSED
  under its own authority; **S1 stays LAUNCH_HOLD**; neither is
  touched by any Stage A or Stage B result (Stage B package §7).
- **Any change** to the frozen rule set, thresholds, δ, α, interval
  method, block length, horizons, arm set, matching ladder, or cost
  model. Each change is a **new rule version** needing fresh
  untouched evidence; it cannot reuse an opened tier (§2 rule 1,
  §11 no-post-hoc-changes).
- **A second run** of any opened tier, a re-run to check a number,
  subsetting, or mid-session adjustment (Stage A package §7). A
  resumption after a STOP is a new decision by Mike on the logged
  evidence, never an in-session retry.
- **Holdout access beyond the single Stage A session**, or any
  holdout access at all before its GO; Tier 2 used as confirmatory
  evidence under any reading (§11 Partly branch).
- **The O4 computation** (separate direct GO; §4), **the EXP-14B
  study** (exhausted; BUY INCONCLUSIVE; cannot rerun), or any new
  performance test outside the frozen protocol.
- **Purchases or plan upgrades** — including a Twelve Data Grow tier
  as the F2 rights basis. That is a separate hard-gate decision by
  Mike; a Stage B GO presumes it has already been made, it does not
  make it.
- **A Stage B verdict before the floors**, an early or second
  Stage B analysis, or any pre-analysis performance output (F7).

---

## 4. Precondition checklist — current status of record

| # | Precondition | Status | Source |
|---|---|---|---|
| 1 | G5 signed freeze of v1.0 as amended | **CLOSED** — adopted by Mike 2026-10-27 | Issue #1 comment `6440943528`; G5 package `5037311` + addendum `4988f15` |
| 2 | C1 independent review of v1.0 | **CLOSED** — PASS | Issue #1 comment `6430481827` |
| 3 | A5 human-exposure attestation | **CLOSED** — Mike: NO | Issue #1 comment `6431596885`; closure addendum `c31c613` |
| 4 | §9 contamination audit | **CLOSED** — PARTLY CONTAMINATED (F-A2-1 only); §11 Partly branch operative | Audit package `f7b37cc` |
| 5 | P1–P4, P6–P11 preconditions | **PASS / COMPLETE** (bounded as recorded); P11 pins include the bootstrap seed `2999475941474119668` and the `pine_backtest.py` pin `262ec034…` | §3; `P11_PINS_V10.json` |
| 6 | §6 power report published | **PUBLISHED** with two named residues: the 7A paired SDs (row 7) and per-tier half-widths evaluated at staging | `POWER_REPORT.md`; §6 `[V08]` |
| 7 | **O4 — 7A paired SDs (H-EXIT-1, H-EXIT-3) entered into the freeze record** | **OPEN — gated on Mike's direct GO.** Procedure fully specified (`O4_PROCEDURE.md`: DEV-only, arms E0/E1/E3, §7 pre-entry exclusion, variance-only outputs {n, SD, DE, n_eff}); cost basis pinned to the Stage-1 flat 25 bps view of the frozen C1 config `87b8285a…` (`O4_BASIS_PIN.md`, concurred in the addendum review). Nothing computed | §6 residue (i); FREEZE_CHECKLIST row O4 ("Must close before any tier opens"); closure addendum |
| 8 | **P5 — per-fill config hash produced and pinned** | **OPEN — BLOCKED: the artifact does not exist.** The frozen C1 config records only the flat Stage-1 cost views; no config recording the §8 per-fill conversion exists anywhere in the record. Closes when the per-fill config is produced under the P9 Stage-2 staging procedure and its SHA-256 is pinned in the freeze record (owner: Muse, with independent review) | §3 P5; `MECHANICAL_CHECKS.md` (G5 package) |
| 9 | **Per-tier §5 pool counts at staging** | **PARTLY RECORDED.** Name counts are on record (Tier 2 = 19, Tier 3 = 11, Stage-A universe = 30 ≥ the 20-symbol floor; DEV feasibility frozen at ladder step (c), 311 events / 71 dropped / 240 retained). The **per-event** pool counts for Tier 2 and Tier 3 are **OPEN**: they are produced at staging, outcome-blind, **before that tier's G7 GO** (ordering: §5 below) | FREEZE_CHECKLIST row O6; OPEN_ITEMS row O6; `MECHANICAL_CHECKS.md` |
| 10 | Stage B F2 — feed-qualification verdict | **OPEN** — Twelve Data pilot sessions run 2026-10-26 → 10-30; finalization + revision re-poll Mon 2026-11-02 ~08:10 ET; verdict additionally requires ChatGPT's post-pilot checklist review | §10 F2; Stage B package §3; OPEN_ITEMS row O7a |
| 11 | Stage B F2 — ongoing-collection rights basis beyond Basic | **OPEN** — Mike's separate decision (e.g. a higher Twelve Data tier, a purchase at his hard gate, or another qualified route). A successful pilot does **not** authorize ongoing collection on Basic | §10 F2 `[V04]`; OPEN ITEMS row O7b |
| 12 | Stage B F3 — collector parity, zero decision mismatches on replayed inputs | **NOT YET EVIDENCED** for the forward collector — a pre-start verification with no result on record (the -16 parity result covers the offline simulator, not the collector) | §10 F3; Stage B package §2 |
| 13 | Stage B F4 / F5 — telemetry live from first bar; missed-signal discipline | Implementation **PASS (bounded)** under P8; live-from-first-bar and missed-signal handling are verified at collection start, not before | §10 F4/F5; §3 P8 |
| 14 | Per-tier G7 GOs | **NONE GIVEN** for any tier | §15 |

**The P5 question, answered from the protocol text.** *Can Stage A
Tier 3 proceed without the P5 per-fill config hash?* **No.** §3 P5
records the completion evidence as "the new per-fill config hash,
produced as a named freeze-procedure step **before any tier opens**";
FREEZE_CHECKLIST row O5 repeats "**Must close before any tier
opens**"; §3's preamble bars any performance test while a §3 item
fails; the Stage A package (§8) lists "P5 per-fill config hash not in
the freeze record" as making Stage A **INVALID to run**; and the
verdict legs themselves are computed under the §8 per-fill model
(Stage A runbook step 3(e); H-SYS-1 at 25 bps per-fill), so the run
cannot be executed as frozen without the config that records that
model. Stage B is gated the same way: F1's freeze-record verification
includes the P5 hash (Stage B package §2).

**The pool-count ordering, as the frozen record states it.** The
per-event §5 pool counts are a **pre-G7 staging product**, not part
of the G7-authorized run: FREEZE_CHECKLIST row O6 — "At staging,
**before that tier's GO**"; OPEN_ITEMS row O6 and `MECHANICAL_CHECKS.md`
agree ("produced at staging, outcome-blind, before that tier's G7
GO"). What the record does **not** state is which instrument
authorizes that staging access — see AMB-1.

---

## 5. Flagged protocol ambiguities (NOT resolved by this package)

Each item below is a point where the frozen texts, read together, do
not determine a single course. They are flagged for Mike (with
ChatGPT's review) to settle — in the decision texts where possible —
and are **not** resolved by Muse here.

- **AMB-1 — What authorizes the pre-G7 pool-count staging access?**
  The checklists order the per-tier pool counts **before** the
  tier's G7 GO (FREEZE_CHECKLIST O6; OPEN_ITEMS O6), and
  `MECHANICAL_CHECKS.md` states in the same breath that "opening
  that window for any purpose requires the tier's own access
  authority." But the only access authority the protocol defines is
  the G7 GO itself (§15; §2 rule 3's two-person/logged-session
  conditions). The frozen texts never name the instrument that
  authorizes the outcome-blind staging run. Two readings stand:
  (i) a separate, narrow staging-access authorization from Mike
  (Text 0 is drafted for this reading — adopting it *is* the
  ruling); or (ii) the pool counts are produced as step 0 inside the
  G7 session, which contradicts the checklists' "before that tier's
  GO" ordering. **Flagged.**
- **AMB-2 — Does one Stage A GO cover study 7C?** §7 describes study
  7C as "(separate; requires its own future GO)". The Stage A
  execution package, however, builds the 7C replays into the single
  Stage A run (its §1 component table; runbook step 3(e)) under the
  single G7 access GO (its §3.7). One reconciliation reads §7's
  "future GO" as the Stage A GO itself; the other requires a
  distinct 7C authorization — but striking 7C would alter the
  runbook's frozen run order, itself a deviation. Text 1 (§6)
  includes 7C expressly, following the execution package; Mike's
  adoption or striking of that sentence settles the reading on the
  record. **Flagged.**
- **AMB-3 — Tier 2 is not an independent opening.** §15 G7 speaks of
  a GO "for each tier opening," but §9 ("once opened, the holdout is
  consumed for this rule version: one frozen script, one run, no
  iteration"), §11's Stage A definition, and the Stage A runbook all
  define a **single** session and run in which the Tier 2
  supplementary legs and the Tier 3 verdict legs are produced
  together. Two sequential, independent holdout openings are not
  executable under the frozen texts. Text 2 is therefore drafted as
  an include/exclude decision **within** the Stage A session, not as
  a standalone tier opening. **Flagged** so the framing is Mike's,
  adopted knowingly.
- **AMB-4 — Must O4 close before the access session, or only before
  verdicts are read?** §6 requires the paired-SD estimate "entered
  into the freeze record **before any tier opens**";
  FREEZE_CHECKLIST row O4: "**Must close before any tier opens**";
  the Stage A package (§3.4) makes the published power report —
  expressly including paired SDs — a precondition "verified closed
  before the access session is scheduled." Against that, the G5
  package's OPEN_ITEMS row O8 note reads: "O4 need not close for the
  session's non-verdict legs, but no verdict is read until the
  applicable freeze-procedure items close." The strict reading
  (close O4 before the session) is the one §7's recommendation
  assumes, but the texts conflict and the conflict is **flagged**,
  not harmonized here.

No other precondition claim in §4 was found ambiguous: P5's bar on
tier opening (§4, row 8) is stated identically in §3, the freeze
checklist, and both stage packages.

---

## 6. Decision texts (signable, separable)

Each text is complete as written and may be adopted independently of
the others, except where a text states its own preconditions. Signing
any text adopts it against the pins in this package's header.

### Text 0 — Staging access for the per-tier §5 pool counts

> I authorize a single outcome-blind staging session for the §5
> pool counts, conducted under the §2 firewall conditions (two
> people, logged end-to-end, frozen code hash — the pinned matching
> code at the freeze record's pins). In that session the §5 matching
> code is run in pool-sizes-only mode over the sealed holdout window
> (2023-10-19 → 2024-09-15) for Tier 2 and Tier 3 at the frozen
> ladder step (c). The only outputs permitted are, per event: the
> eligible-pool count; the dropped-event count; and the event-mix
> composition summary (by symbol and session bin) — the feasibility
> report §5 defines. No forward return, group difference, or
> performance quantity of any kind may be computed, viewed, or
> recorded. The counts are entered into the freeze record on
> completion. This access is feasibility staging only: it opens no
> tier, consumes no tier, and authorizes no performance test, no
> further holdout access, and no G7 decision by itself.

### Text 1 — Stage A GO (Tier 3 verdict legs; the single session)

> I give the G7 GO for **Stage A**, effective when each of the
> following is in the freeze record: (i) the O4 paired SDs, computed
> under the pinned procedure and basis and entered into
> `POWER_REPORT.md`; (ii) the P5 per-fill config hash, produced under
> the P9 Stage-2 staging procedure and pinned; (iii) the per-tier §5
> pool counts for Tier 2 and Tier 3. On that effectiveness, one Stage
> A session is authorized, exactly as specified in the Stage A
> execution package: two-person logged access; receipt-chain
> re-verification; read-only mount; one run of the frozen script in
> its frozen order, including the 7A paired legs, the 7B descriptive
> legs, and the study 7C full-system replays (E0 and E1); verdict
> computation under the adopted B2 economics-first contract, with
> the verdict-bearing legs on Tier 3 only; outputs captured, hashed,
> and committed; Tier 2 and Tier 3-on-holdout marked CONSUMED for
> this rule version. This GO authorizes no second run, no rule or
> parameter change, no live trading, no production activation, and
> no Stage B activity.

*(Adoption note, not part of the text: the 7C sentence is where
AMB-2 is settled. Striking it leaves 7C unauthorized and, per the
execution package's frozen run order, would require an adjudicated
amendment before the session could be scheduled.)*

### Text 2 — Tier 2 supplementary legs (within the Stage A session)

> Within the Stage A session authorized by my Stage A GO, the
> Tier 2 legs (the 19 defect-free holdout names) **are** computed
> and reported as supplementary evidence — beside, never inside,
> the confirmatory pool, with no PASS or FAIL standing, per the §11
> Partly branch.

*(Alternative, if Mike prefers exclusion: replace "are computed and
reported" with "are **not** computed, and the session records Tier 2
as not reported." The §11 standing text reads "reported as
supplementary"; the as-written text follows it. See AMB-3.)*

### Text 3 — Stage B GO (Tier 4 forward collection)

> I give the G7 GO for **Stage B** forward collection, effective
> when each of the following is verified on record: (i) the F2 feed
> qualification verdict for the collection route, under its own
> adjudication; (ii) my separate rights-basis decision for ongoing
> collection (a successful evaluation pilot is not that basis);
> (iii) F3 collector parity at zero decision mismatches on replayed
> inputs; (iv) the freeze record complete, including the P5 per-fill
> config hash (F1); and (v) F4 telemetry and F5 missed-signal
> discipline verified for the collection start. Collection mode:
> **signal-only** (no positions opened; hypothetical entry/exit
> logged per candidate fire). Collection proceeds under §10 F1–F7:
> bars as received, missed signals counted as unexecuted and never
> backfilled, no performance output before the single verdict
> analysis at the §6 floors and the 6-month minimum. This GO
> authorizes no purchase or plan upgrade (my rights-basis decision
> under (ii) is separate and prior), no live trading, no production
> activation, and no S1 launch.

*(Mode note, not part of the text: to choose paper-execution,
replace the mode sentence with "Collection mode: **paper-execution**
(paper positions under the frozen rules; EXECUTION records
written)." If the GO is silent on mode, the frozen default is
signal-only.)*

---

## 7. Recommended sequencing

1. **Decide the pre-G7 completions now — they are the only
   decision-ready items.** (a) Mike's direct **O4 GO**: the
   computation is fully specified (procedure pinned, basis pinned
   and concurred, variance-only outputs), so the GO covers a known
   quantity and nothing else. (b) **Text 0** (staging access),
   settling AMB-1 by ruling. (c) **P5 production** by Muse under
   the P9 Stage-2 staging procedure, with independent review and
   pinning — a named freeze-procedure step (owner: Muse); no Mike
   decision is needed to start it, and it is on the critical path of
   *both* stages. Together these close every Stage A precondition
   except the G7 GO itself.
2. **Stage A G7 next** (Texts 1 + 2 together). It becomes
   decision-ready the moment O4, P5, and the pool counts are in the
   freeze record. Its content is pre-declared and bounded: the
   paired BUY/exit legs are decisive; H-SYS-1 and H-EXIT-4 are
   expected INCONCLUSIVE-by-floor on the projected counts. Because
   the window is consumed by the session whether it completes or
   STOPs after outcome computation, Stage A should not be scheduled
   until every precondition is verified closed — there is no
   rehearsal.
3. **Stage B G7 last — gated by evidence, not by Stage A.** It
   cannot be decision-ready before the pilot verdict (Mon 2026-11-02
   finalization + post-pilot review) and Mike's rights-basis
   decision close F2, and F3 parity evidence is also outstanding. It
   does not wait for Stage A. But it is the long pole: the decisive
   H-SYS verdict needs ~13–14 months of collection from the start
   date, so once F1–F5 pass, every month of delay in the Stage B GO
   moves the program's decisive verdict a month later.

---

## Appendix — sources and pins relied on

| Item | Pin / citation |
|---|---|
| Frozen protocol | `PREREG_V10.md` SHA-256 `29a0477a13e52ff4467193f69df7ef107048a8801f64c61f43de28d40d2850c6`, commit `4ffb8fb`; amendments `247a1c7` (v1.0.1), `4b45a3e` (v1.0.2); closure addendum `c31c613` |
| G5 adoption | Mike, 2026-10-27, Issue #1 comment `6440943528`; G5 package `503731183b4d9385059b83e1996b5bc3989ebe8d` (manifest SHA-256 `81b881b3574fba5156107bcac0e53e27472dfc9c8fa8217e7f6de17f91b8975e`); addendum `92aaa0a`, correction `4988f15` |
| Frozen rule set under test | C1 config canonical pin `87b8285a522ba0e3e5a80f0097b9668afc1ddf11da4fc5559c0ca31f55218706`, source commit `555ebb1` |
| Simulator pin | `pine_backtest.py` SHA-256 `262ec0340161e72893ca9c5edd9d1fe2cb046fd30004d727b3893d52bd4d3f2a` |
| Bootstrap seed | `2999475941474119668` (contract `fc17041`) |
| Session calendar | Adopted table SHA-256 `00c5555c…`; union extension 1,054 sessions |
| Stage packages | `stage_packages/` in the v1.0 package (staging copies verified byte-identical to the committed files during this preparation) |
| O4 | `O4_PROCEDURE.md` + `O4_BASIS_PIN.md` (G5 package + addendum); -13 ledger SHA-256 `267e794c284a409d7d9b6d8e1056c452976b59746062e9e6e18c5664b74c003b` |
| P5 finding | `MECHANICAL_CHECKS.md` (G5 package): no per-fill config exists in the record; the six standalone `experiment_config.json` bundles (SHA-256 `911750fa…`) record no per-fill conversion |

*Prepared by Muse, 2026-10-27. Preparation only — G7 remains
ungiven for every tier, and the holdout remains sealed.*
