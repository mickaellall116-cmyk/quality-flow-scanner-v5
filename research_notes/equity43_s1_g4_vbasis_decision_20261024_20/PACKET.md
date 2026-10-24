# G4 / VBASIS decision packet — QF-EQUITY43-S1-G4-VBASIS-DECISION-PACKET-20261024-20 r1

Offline adjudication packet from already committed bytes, receipts and
source. Governing text: GitHub Issue #1 comment 6383818172. This packet
adopts and waives nothing; G4/VBASIS remains **UNADOPTED** regardless of
its outcome. The packet's governed label is at the end.

## Label: **G4_HOLD**

One-paragraph basis: the current fixed band (R-A) flags every leg in the
record (5,751 flags across the 43 DEV legs; 44 on SPY/HO and 94 on
SPY/DEV where no basis event exists), and the event-free step-shape
rule (R-C) also fails the negative controls (167 flags on the seven
no-event control legs — real market volume regime shifts are
step-shaped). The corroboration rule (R-B) separates the predeclared
pilot controls (zero breaks on all seven negative legs; NVDA and AVGO
declared splits handled correctly), but it does not meet the adoption
bar on the full record: one of three declared-split positive controls
(NFLX) ends flagged by the preserved single-session volume-note
mismatch rule, and R-B's corroboration lane inherits STEP-ALL's loose
factor-anchor tolerance, producing six suspect boundaries in five
census legs whose price steps (+35% to +85% overnight moves) are
ordinary news/earnings gaps matched to the 2.0 anchor — so R-B can
neither cleanly qualify the captured bytes nor demonstrate specificity
of its corroboration. No preregistered rule satisfies all five
adoption conditions on the pinned evidence. Minimum missing evidence
is listed in §6.

## 1. Mechanical reproduction (task item 1)

Checker: checker-v3-candidate-2, `tsla_completeness_check.py` sha256
`4fdc31cb…` (byte-identical copy of the -02/-94 module, pin-verified
before any run). Session table: pinned adopted table sha256
`00c5555c…` (XNYS-751-UNION-20261021), hash-refused on mismatch.
Inputs: the eight receipted pilot legs in the local byte store
(source sha256 per leg in `evidence/reproduction.json`, each equal to
the -02 committed report's `source_sha256`). Admission: the -02
generic pinned-session membership rule, unchanged. Event table:
`{NVDA/HO: 2024-06-10 ×10}` exactly as -02.

Reproduction vs the -02 committed `checker_report.json` — **exact on
every leg and every compared field** (rows admitted, VBASIS count,
STEP-ALL count, overall verdict, completeness verdict):

| leg | admitted | VBASIS flags | STEP-ALL | completeness | convention |
|---|---|---|---|---|---|
| NVDA/HO | 1,583 | 32 | 0 | PASS | SUSPECT (VBASIS only) |
| NVDA/DEV | 3,653 | 90 | 0 | PASS | SUSPECT (VBASIS only) |
| TSLA/HO | 1,583 | 12 | 0 | PASS | SUSPECT (VBASIS only) |
| TSLA/DEV | 3,653 | 91 | 0 | PASS | SUSPECT (VBASIS only) |
| AAPL/HO | 1,583 | 32 | 0 | PASS | SUSPECT (VBASIS only) |
| AAPL/DEV | 3,653 | 108 | 0 | PASS | SUSPECT (VBASIS only) |
| SPY/HO | 1,583 | **44** | 0 | PASS | SUSPECT (VBASIS only) |
| SPY/DEV | 3,653 | **94** | 0 | PASS | SUSPECT (VBASIS only) |

The reported control fact is proven from the bytes: SPY carries 44
(HO) and 94 (DEV) standalone VBASIS flags with no declared split or
basis event in either window, and the price-side lanes (STEP, STEP-ALL)
are clean everywhere — the convention failure is driven solely by the
volume lane. SMCI/HO was not read (this task's bounds); its -02
classification stands as prior record only.

## 2. Lane separation (task item 2) — negative tests, all pass

Synthetic fixtures on the pinned table (`code/negative_tests.py`,
`evidence/negative_tests.json`):

- **NT-1** (completeness ⇏ convention): a leg with one session dropped
  and three zero-volume price-moving bars, volumes continuous →
  completeness **FAIL**, convention **PASS**, R-C breaks 0.
- **NT-2** (gradual regime ⇏ discrete break): volume ramping
  +10%/session across the whole span, flat prices, complete grid →
  the current VBASIS lane flags **52** boundaries (the documented
  failure mode, reproduced fail-before); under R-B the same series is
  **NOTE_ONLY** (no price/event corroboration exists); under R-C the
  stability conditions reject every boundary (0 breaks).
- **NT-3** (independence, other direction): an undeclared 2:1-shaped
  price step with continuous volumes → completeness PASS, STEP-ALL
  suspect fires from the price lane alone.
- **NT-4** (sensitivity probe): a discrete ×3 volume step, flat
  prices, no event → R-A flags it (5), R-C flags it (5), R-B leaves it
  a NOTE. This is R-B's structural sensitivity limit, stated plainly:
  on volume evidence alone, a price-silent vendor volume-basis change
  is indistinguishable from a market regime shift.

## 3. Preregistered rules compared (task item 3)

Specified in full before execution; no rule uses returns, trade
outcomes, holdout outcomes, or post-result tuning. No other rules
were compared.

- **R-A — current fixed band.** The checker's VBASIS lane as-is
  (5-session medians, band 1.5, undeclared boundaries): any flag →
  CONVENTION_BREAK_SUSPECT.
- **R-B — declared-action / STEP corroboration.** A VBASIS flag stands
  as a convention break only if the same boundary carries price-side
  corroboration (a STEP-ALL factor-shaped suspect at the same boundary
  date, a declared event at that boundary, or the declared-boundary
  note-mismatch rule). Uncorroborated flags become VOLUME_REGIME_NOTE
  (information, never a failure). Declared boundaries keep the
  existing STEP + NOTES lanes unchanged.
- **R-C — event-free step-shape rule.** An undeclared boundary is a
  break iff (i) the VBASIS 5-session ratio is outside [1/1.5, 1.5],
  (ii) the pre-window is stable (5 pre sessions vs the 20 before them,
  medians inside the band), and (iii) the post-window is stable
  (sessions +5..+25 vs the first 5 post sessions, inside the band).
  Boundaries without 25 sessions on both sides are UNTESTABLE, never
  breaks. No events, prices, or returns consulted.

## 4. Confusion counts on the predeclared controls (task item 4)

Negative controls — legs with no declared split/basis event in window
(flag counts; a leg is "blocked" by a rule if it carries ≥1 break):

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

Positive controls — declared splits (correct handling = prices
classified CONTINUOUS_ADJUSTED under `adjust=splits`, no basis
mismatch, leg not blocked by the volume lane):

| leg | event | STEP classification | volume note | mismatch |
|---|---|---|---|---|
| NVDA/HO | 2024-06-10 ×10 | CONTINUOUS_ADJUSTED (0.9937) | UNSCALED (1.307) | no |
| AVGO/DEV | 2024-10-11 ×10 | CONTINUOUS_ADJUSTED (0.9753) | UNSCALED (0.667) | no |
| NFLX/DEV | 2025-11-17 ×10 | CONTINUOUS_ADJUSTED (0.9957) | OTHER_VOLUME_STEP (0.405) | **yes** |

NFLX's prices are clean; its single-session volume-note ratio (0.405)
trips the preserved mismatch rule. Whether the vendor's NFLX volume
basis is genuinely inconsistent around the split or the one-session
note is simply noisy at that boundary cannot be decided from the
pinned record — it is a residual unknown, and under a fail-closed bar
it counts against the rule set that preserves the note lane as-is.

## 5. Disposition of the captured EQUITY43 bytes, per rule (task item 4)

Census = all 43 DEV legs (39 capture-store legs + 4 pilot DEV legs),
same admission rule, `adjust=splits` convention unchanged:

| rule | flags/breaks | legs blocked | would qualify the captured bytes? |
|---|---|---|---|
| R-A | 5,751 flags | 43 / 43 | **No** — every leg CONVENTION_BREAK_SUSPECT |
| R-B | 6 corroborated breaks | 5 / 43 | **Not cleanly** — see below |
| R-C | 1,783 breaks | 43 / 43 | **No** — every leg carries step-shaped regime shifts |

R-B's six corroborated boundaries (VBASIS flag + same-boundary
STEP-ALL suspect): AMD 2025-10-06 (price step 1.375, volume ratio
3.09), APP 2024-11-07 (1.366, 2.85), LUNR 2024-09-18 (1.480, 7.74) and
2025-03-07 (0.642, 1.57), MRNA 2026-08-19 (1.847, 20.5), SNOW
2026-05-28 (1.352, 3.20). Each price step was matched to the 2.0
anchor inside STEP-ALL's log(1.5) tolerance; on their face these are
ordinary overnight news/earnings gaps, not split signatures (no
declared event exists at any of them, and none is within 10% of the
anchor). R-B therefore blocks five legs on corroboration evidence
that does not withstand scrutiny — its specificity failure is in the
corroboration lane it inherits, not in the corroboration idea.
Additionally NFLX/DEV is blocked under R-B by the note-mismatch
above. Under R-B, 37 of 43 legs would carry clean convention lanes
(their VBASIS flags all demoted to notes); 6 legs would not qualify.

## 6. Recommendation and minimum missing evidence (task item 5)

**G4_HOLD.** Against the governed test — deterministic ✓ for all
three rules; source-pinned ✓; no return-conditioned choice ✓ — the
distinguishing and qualification conditions fail: R-A and R-C do not
distinguish the negative controls at all; R-B distinguishes the pilot
controls but (a) fails one of three positive controls via the
single-session note lane, and (b) cannot qualify the captured bytes
cleanly because its corroboration lane (STEP-ALL at the inherited
log(1.5) anchor tolerance) flags ordinary gaps. Tightening either
lane would be a new rule, and designing it against these same results
would be post-result tuning — expressly out of scope here.

Minimum missing evidence for a future adoption packet:
1. A corroboration specification with demonstrated specificity on
   pinned bytes (e.g. a tightened anchor tolerance or a second
   confirming signature), preregistered before it is run.
2. A multi-session volume-note specification for declared boundaries,
   re-tested on the NVDA/AVGO/NFLX positive controls (the
   single-session note is the NFLX failure point).
3. At least one verified true-positive VBASIS-class case (a real
   undeclared volume-basis break in pinned bytes) to demonstrate any
   candidate rule's sensitivity; none exists in the current record,
   and NT-4 shows the sensitivity question is rule-dependent
   (R-C-shaped rules catch the synthetic case; R-B-shaped rules
   structurally cannot).

Residual unknowns: the NFLX volume-note anomaly (vendor basis vs
note noise); the true nature of the six R-B census boundaries (each
would need its own event adjudication); R-C UNTESTABLE edge
boundaries (44 per pilot leg) where no step-shape judgment is
possible.

## 7. Preservation

-19 r2 package, production PAUSED state, and the sealed holdout are
byte-identical before/after (pins in RESULT.md). No vendor calls, no
credits, no performance computation, no production change, no
activation. This packet's label is a RESULT for adjudication; it is
not an independent PASS and it does not change the standing
UNADOPTED status of G4/VBASIS.
