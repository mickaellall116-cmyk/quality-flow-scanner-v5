# G4 / VBASIS decision packet r2 — event-table correction — QF-EQUITY43-S1-G4-VBASIS-DECISION-PACKET-20261024-20 r2

Narrow correction to r1 (package `b1d3661`), governed by GitHub
Issue #1 comment 6384407724. Event table only: no new rule, no
threshold change, no additional data. This packet adopts and waives
nothing; G4/VBASIS remains **UNADOPTED** regardless of its outcome.

## Label: **G4_HOLD** (retained)

One-paragraph basis: the correction removes the one fabricated
positive control and re-derives the control evidence from
source-attested issuer records. What survives is thinner than r1
claimed: **two** verified positive controls, of which exactly one
(NVDA/HO) is handled cleanly, while NFLX/DEV still trips the preserved
single-session volume-note mismatch. R-A and R-C still fail the
negative controls outright (unchanged: 471 flags and 167 breaks on
the seven no-event legs), and R-B's corroboration lane still flags
six ordinary-gap boundaries in the census through STEP-ALL's loose
anchor tolerance. No verified true-positive VBASIS-class case exists
in the pinned record. True-positive and specificity evidence is
therefore insufficient, so the governed label stays **G4_HOLD** —
the same label r1 returned, now resting on a valid control table.

## 1. The defect, owned

The error was mine (Muse's r1 work). r1's `DECLARED_SPLITS_DEV`
encoded `("AVGO","DEV"): 2024-10-11 ×10` — a hand-entered date with
no issuer source behind it. Broadcom's own record (below) puts the
first split-adjusted trading date at **2024-07-15**, before the DEV
window opens (2024-09-16). The false row did two things: it
manufactured a positive control (the checker dutifully classified the
ordinary 2024-10-11 boundary as a declared-split boundary and
returned CONTINUOUS_ADJUSTED / UNSCALED / no mismatch), and it
suppressed the ordinary lanes' judgment of that boundary (VBASIS,
STEP-ALL and R-C all skip declared dates). r1's sentence "NVDA +
AVGO splits clean" is therefore **unsupported**, and r1's
positive-control conclusion is labeled **CONTROL_TABLE_INVALID**.
The r1 package and its raw outputs are preserved untouched; §3
quantifies the damage exactly, and it is confined to the control
evidence — no census or rule total moves.

## 2. Source-attested event table (first split-adjusted trading dates)

Every row is pinned to the primary issuer record quoted; no date in
this packet is hand-entered without its citation. The machine-readable
form with full quotes is `code/common.py::ATTESTED_EVENTS`.

| symbol | first split-adjusted trading | factor | primary issuer record |
|---|---|---|---|
| NVDA | **2024-06-10** | ×10 | NVIDIA press release, "NVIDIA Announces Financial Results for First Quarter Fiscal 2025", 2024-05-22 (investor.nvidia.com): record close Thu 2024-06-06; distribution after close Fri 2024-06-07; "Trading is expected to commence on a split-adjusted basis at market open on Monday, June 10, 2024." |
| AVGO | **2024-07-15** | ×10 | Broadcom press release, "Broadcom Inc. Announces Second Quarter Fiscal Year 2024 Financial Results and Quarterly Dividend", 2024-06-12 (investors.broadcom.com): record after close 2024-07-11; shares after close 2024-07-12 (split effective 2024-07-12); "At market open on July 15, 2024, trading is expected to commence on a split-adjusted basis." Corroborated by the company's split FAQ (investors.broadcom.com/static-files/e90fe911-25c9-47eb-afbe-8e763b71eb64). |
| NFLX | **2025-11-17** | ×10 | Netflix press release, "Netflix Announces Ten-For-One Stock Split", 2025-10-30 (PR Newswire, SOURCE Netflix, Inc.; also filed as Exhibit 99.1): record close Mon 2025-11-10; distribution after the close Fri 2025-11-14; "Trading is expected to begin on a split-adjusted basis at market open on Monday, November 17, 2025." Verified against the primary announcement as the governing comment required. |

Window membership: NVDA 2024-06-10 ∈ HO [2023-10-19 .. 2024-09-13];
NFLX 2025-11-17 ∈ DEV [2024-09-16 .. 2026-10-16]; AVGO 2024-07-15 ∉
DEV — so **AVGO is excluded from the DEV positive controls**, and
AVGO/HO bytes are not read under this task's bounds (no substitution).

**Corrected positive-control denominator: 2** (NVDA/HO, NFLX/DEV).

Fail-closed machinery (`code/common.py::validate_declared`): a
declared event is admitted for a leg only if it exactly matches the
attested (date, factor) for that symbol AND falls inside the leg's
window. Unknown events, unattested symbols, wrong factors, and
attested-but-out-of-window events are rejected with an error rather
than silently used (tests ET-4/ET-5/ET-6, §4).

## 3. False-row impact, proven on the same bytes

`code/impact_eval.py` runs r1's evaluation logic under both tables
on identical pinned bytes. Apples-to-apples gate: the FALSE-table run
reproduces r1's committed AVGO/DEV record on all 9 compared fields
and r1's committed census totals exactly. The diff:

**AVGO/DEV leg** (3,653 rows admitted, completeness PASS, both runs):

| field | r1 false table | r2 corrected table |
|---|---|---|
| STEP records | 1 — 2024-10-11, CONTINUOUS_ADJUSTED (0.975287), PASS, basis_mismatch **false** | **none** |
| volume notes | 1 — UNSCALED (0.667136) | **none** |
| R-A VBASIS flags | 138 | 138 |
| VBASIS at 2024-10-11 | not judged (declared dates skipped) | judged — no flag |
| R-B breaks / notes | 0 / 138 | 0 / 138 |
| R-C breaks | 35 | 35 (2024-10-11 is not a break either way) |
| R-C untestable boundaries | 43 | 44 (the boundary re-enters the scan; too early in the window to judge) |

**Census (43 DEV legs):** AVGO/DEV is the *only* leg whose record
changes, and only in the STEP / volume-note / R-C-untestable fields
above. Census totals are **identical to the unit** under both
tables: R-A 5,751 flags (43/43 legs), R-B 6 corroborated breaks in
5 legs, R-C 1,783 breaks (43/43 legs), STEP-ALL 6 suspects in 5 legs.

**Control evidence (where the damage actually sits):**

| | r1 as published | corrected |
|---|---|---|
| positive controls | 3 (NVDA/HO, AVGO/DEV, NFLX/DEV) | **2** (NVDA/HO, NFLX/DEV) |
| handled cleanly | 2 of 3 (NVDA, AVGO) | **1 of 2** (NVDA only) |
| "NVDA + AVGO splits clean" | claimed | **unsupported — CONTROL_TABLE_INVALID** |

So the false row changed no rule arithmetic anywhere; it inflated
the *specificity evidence* for R-B by one fabricated control. R-B's
r1-era claim "separates the pilot controls" survives only weakened:
0 breaks on all seven negative controls (unchanged), but on the
positive side it now stands at 1 of 2, with NFLX failing the
preserved note lane.

## 4. Fail-before / after and rejection tests (`code/event_table_tests.py`, 7/7)

- **ET-1 (fail-before):** under the false table, AVGO/DEV carries the
  manufactured declared-boundary record (CONTINUOUS_ADJUSTED,
  UNSCALED, no mismatch) and no VBASIS judgment at 2024-10-11 is
  possible — exactly r1's published control.
- **ET-2 (fail-after):** under the corrected table, AVGO/DEV has no
  STEP record and no volume note; 2024-10-11 is an ordinary boundary.
- **ET-3:** the positive-control set drops AVGO/DEV (denominator
  3 → 2); AVGO's R-B disposition becomes that of an ordinary
  no-event leg.
- **ET-4:** the false row itself, ("AVGO","DEV", 2024-10-11 ×10), is
  **rejected** by the corrected machinery.
- **ET-5:** the attested AVGO event attached to DEV (2024-07-15) is
  **rejected** as out-of-window rather than silently used.
- **ET-6:** an unattested symbol/event (MSFT) is **rejected**.
- **ET-7:** the corrected controls validate (NVDA/HO, NFLX/DEV);
  `leg_declared("AVGO","DEV")` is empty.

## 5. Recomputed rules on the corrected control set (deterministic, run twice, identical)

Same three preregistered rules as r1, same bytes, same admission,
`adjust=splits` unchanged. Negative controls are untouched by the
correction and reproduce r1 exactly.

Negative controls (no declared event in window):

| leg | R-A flags | R-B breaks | R-C breaks |
|---|---|---|---|
| NVDA/DEV | 90 | 0 | 29 |
| TSLA/HO | 12 | 0 | 8 |
| TSLA/DEV | 91 | 0 | 34 |
| AAPL/HO | 32 | 0 | 16 |
| AAPL/DEV | 108 | 0 | 25 |
| SPY/HO | 44 | 0 | 19 |
| SPY/DEV | 94 | 0 | 36 |
| **total** | **471** | **0** | **167** |

Positive controls (denominator **2**):

| leg | event (attested) | STEP classification | volume note | mismatch |
|---|---|---|---|---|
| NVDA/HO | 2024-06-10 ×10 | CONTINUOUS_ADJUSTED (0.993671) | UNSCALED (1.307109) | no |
| NFLX/DEV | 2025-11-17 ×10 | CONTINUOUS_ADJUSTED (0.995681) | OTHER_VOLUME_STEP (0.405241) | **yes** |

Census disposition of the captured EQUITY43 DEV bytes, per rule —
unchanged totals, now on a valid table:

| rule | flags/breaks | legs blocked | would qualify the captured bytes? |
|---|---|---|---|
| R-A | 5,751 flags | 43 / 43 | **No** |
| R-B | 6 corroborated breaks | 5 / 43 (+ NFLX/DEV via note mismatch) | **Not cleanly** |
| R-C | 1,783 breaks | 43 / 43 | **No** |

R-B's six corroborated boundaries are the same six as r1 (AMD
2025-10-06, APP 2024-11-07, LUNR 2024-09-18 and 2025-03-07, MRNA
2026-08-19, SNOW 2026-05-28) — ordinary overnight gaps loosely
matched to the 2.0 anchor; the correction does not touch that
specificity failure, and it remains a bar to adoption.

## 6. Recommendation and minimum missing evidence

**G4_HOLD.** The governed adoption conditions fail on the corrected
record: R-A and R-C do not distinguish the negative controls at all;
R-B distinguishes the negative controls but handles only 1 of 2
verified positive controls cleanly, and its inherited corroboration
lane lacks demonstrated specificity. With the fabricated control
removed, the true-positive side of the ledger is one clean control
(NVDA) and zero verified VBASIS-class true positives — insufficient
specificity evidence by the packet's own fail-closed bar.

Minimum missing evidence for a future adoption packet (r1 §6,
corrected where the defect touched it):
1. A corroboration specification with demonstrated specificity on
   pinned bytes, preregistered before it is run (unchanged).
2. A multi-session volume-note specification for declared
   boundaries, re-tested on the **verified** positive controls —
   NVDA and NFLX. AVGO cannot serve as a DEV positive control; an
   AVGO control would require a window containing 2024-07-15, which
   sits on the holdout side and is out of bounds here.
3. At least one verified true-positive VBASIS-class case in pinned
   bytes (unchanged; none exists in the current record).

## 7. Preservation and provenance

- r1 package (`b1d3661`) untouched; its positive-control conclusion
  is labeled CONTROL_TABLE_INVALID **here**, in r2 — r1's files and
  raw outputs are preserved as evidence, not edited.
- -19 r2 package unchanged; production PAUSED byte-identical
  before/after (pins in RESULT.md); holdout sealed — no holdout body
  read anywhere in this task, AVGO/HO included. SMCI bodies unread.
- Checker byte-identical to r1/-02/-94 (sha256 `4fdc31cb…`,
  pin-verified before any run); session table pinned (`00c5555c…`,
  hash-refused on mismatch). Inputs: the same pilot store and
  capture-store DEV legs r1 used (AVGO/DEV admitted 3,653 rows in
  both impact runs).
- Offline only; 0 vendor calls; 0 credits; no performance computed;
  no production change; no S1/S2 activation; no T0; no trades.
  (The only network use in preparing this packet was reading the
  three primary issuer records cited in §2 — the governing comment
  itself requires the dates be pinned to those records.)
- This packet's label is a RESULT for adjudication; it is not an
  independent PASS and it does not change the standing UNADOPTED
  status of G4/VBASIS.
