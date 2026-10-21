# ITEM 4 — TSLA: COMPLETENESS FAILURE ≠ SPLIT-ADJUSTMENT FAILURE
## Governance correction record (proposal) + independent check

## The original verdict text (PRESERVED, untouched, quoted exactly)

From the -75 Day-1 execution result
(`research_notes/td_probe_day1_rerun_20261021_75/EXECUTION_RESULT.md`,
sha256 51916dfcd8d52469…), TSLA window:

> C2 FAIL — convention INCONSISTENT: "166 pre-split bar(s) fit
> neither convention; 0 post-split bar(s) off ratio 1"

and the terminal `TD_PROBE_DAY1_RERUN_EXECUTED__NVDA_PASS__
TSLA_DATA_UNQUALIFIED_C2__AAPL_CONTROL_PASS`. The -75 record is not
edited by this package; the DATA_UNQUALIFIED terminal stands under
either label. What this record corrects is the LABEL's meaning.

## Why the label is wrong

The same -75 result contains the decomposition that refutes its own
label: all 166 flagged bars are **zero-volume in both series**; every
other pre-split pair (668) scales exactly ×3; no pair shows any other
ratio. A 0/0 volume pair cannot satisfy either of the analyzer's two
conventions (scaled-by-factor or unscaled), so the pairing rule
counts it as "fits neither" — an artifact of dividing by an absent
quantity, not evidence about the adjustment convention. ChatGPT's -76
follow-up added the decisive fact: the 166 bars show **nonzero OHLC
range with changed O/C** — prices moved on bars reporting no volume.
That is a **completeness defect** (volume missing or zeroed in the
feed for those bars), a different failure class from a **convention
defect** (prices/volumes adjusted on a mixed basis). On the evaluable
subset, the convention evidence is uniformly consistent (×3 exactly,
flip on the 2022-08-25 effective date, C1/C3/C4/C6 all PASS).

Calling a completeness failure "INCONSISTENT convention" is not a
cosmetic issue: it points repair at the wrong layer (adjustment
logic instead of feed completeness) and it contaminates the S2
question — S2 guards against mixed-basis series, and this window
provides no mixed-basis evidence at all.

## Corrected label (proposed for adoption by adjudication)

> **C2 NOT_EVALUABLE — VOLUME COMPLETENESS FAILURE.** 166 pre-split
> bars report zero volume with nonzero price range and are excluded
> from convention evaluation as completeness defects. On the
> remaining evaluable pre-split bars (668), the volume convention is
> uniformly SCALED_BY_FACTOR (×3, no exceptions); C1/C3/C4/C6 PASS.
> The window remains DATA_UNQUALIFIED — on completeness grounds.

Adoption mechanics: this label replaces the C2 label in FUTURE
reporting by reference (a governance amendment pinned by hash). The
-75 bytes, the -74 analyzer, and the frozen verdict text are never
rewritten; any re-issue of the window verdict cites both labels with
this record as the correction authority.

## The independent completeness check (defined + implemented)

`fixtures/tsla_completeness_check.py` defines a check that shares NO
logic with the C2 pairing rule — it never opens a second series:

- **COUNT** — per-session bar reconciliation against a session table
  (the qualified-calendar stand-in): each session in span must carry
  exactly its expected hourly starts; missing/extra bars fail the
  completeness lane.
- **ANOMALY** — enumerates zero-volume PRICE-MOVING bars
  (volume = 0 with high > low or close ≠ open) as completeness
  defects; zero-volume FLAT bars (O=H=L=C) are classified
  NO_TRADE_FLAT and are not defects — a tradeless hour is a market
  fact.
- **STEP** — single-series continuity at declared split boundaries:
  a uniformly adjusted series is price-continuous across the
  boundary; a step near the declared factor (or its reciprocal) is
  the mixed-basis signature, detected from inside the one series.

The two verdict lanes are structurally separate
(`completeness_verdict` vs `convention_verdict`), so a completeness
failure cannot print as a convention failure again.

**Fixture proof** (`fixtures/test_tsla_completeness_check.py`,
14/14 PASS, exit 0, repeat-identical — full output in
`fixtures/TEST_EVIDENCE.md`): (a) clean adjusted series →
QUALIFIED_CLEAN; (b) 5 zero-volume price-moving bars →
COMPLETENESS_FAIL with the convention lane untouched; (c) mixed-basis
series → CONVENTION_BREAK_SUSPECT (observed step 0.333333 = 1/3) with
the completeness lane untouched; (d) flat zero-volume bars stay
QUALIFIED_CLEAN and are counted as NO_TRADE_FLAT; (e) a dropped bar
fails COUNT with the exact missing timestamp.

Applied prospectively, this check is the instrument that would
classify a TSLA-shaped window correctly on first contact. Applying it
to the actual -75 snapshots is a separate, separately-authorized
re-analysis (the snapshots are pinned evidence; nothing in this task
re-opens them) — see the separate-GO list.

**Status: label correction DOCUMENTED (adoption by adjudication);
check FIXTURE_PROVEN.** Owner: Muse. Claude's targeted re-review
is the natural adopter of the corrected label.
