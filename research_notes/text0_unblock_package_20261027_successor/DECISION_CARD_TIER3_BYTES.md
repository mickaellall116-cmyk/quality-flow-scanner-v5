# DECISION CARD — Tier 3 holdout-window bytes do not exist

Status: OPEN DECISION, not taken by this package. This card is the
record ChatGPT's HOLD (blocker 4) required: the absence is
documented, the code fails closed on it, and obtaining the bytes
is a separate scoped decision for Mike + ChatGPT adjudication.

## The absence

The Text 0 pool counts require a sealed-window inventory covering
19 Tier 2 + 11 Tier 3 symbols over 2023-10-19 → 2024-09-15.

- Tier 2 (19): holdout-window captures exist. The section-9
  contamination audit examined holdout legs for all 44 UX51
  equities; the 19 Tier 2 names are the legs with no defective
  bars (see tier_derivation.json). Their capture bytes sit in the
  private qf-data-archive; assembling them into the Stage-2
  builder's raw directory is part of the future session.
- Tier 3 (11: AAOI, ACN, BABA, BE, BLK, COF, CRDO, IREN, MPWR,
  SPOT, TWLO): these names were never part of UX51 and were never
  captured for ANY window by the -23 capture program. No
  holdout-window bytes for them exist anywhere in the archive.
  The DEV/holdout capture manifests contain no Tier 3 legs.

## What a capture would require

- Route: Twelve Data `/time_series`, 1h, America/New_York, the
  same endpoint class as the frozen -23 manifest — 11 symbols ×
  the sealed window (227 sessions, ~1,583 bars per symbol; one
  request per symbol at outputsize 5000, plus the Policy-A
  preflight call). Free-tier credit cost is small (Mike, 2026-10-23:
  credits are not a brake), but cost is not the gate here.
- Rights: Twelve Data's written position (Artemis, 2026-10-25) is
  that the Basic plan permits non-display EVALUATION only and
  ongoing research analytics require Grow. A Tier 3 capture is
  unambiguously research-analytics collection, so the rights basis
  for ongoing collection (the open Stage-B dependency) must be
  settled, or the capture explicitly scoped as evaluation, before
  any vendor call. That settlement is not this package's to make.
- Governance: a capture is a vendor run inside the research
  program: it needs its own scoped task (frozen manifest, credit
  ceiling, fail-closed one-attempt discipline), ChatGPT
  adjudication, and — because it may touch the paid-tier rights
  question — Mike's explicit GO if any purchase/subscription is
  involved (hard gate).

## What the code does until then

Fail closed, named, never silent:

- Builder (Stage 2, inventory construction): a missing Tier 3
  capture file exits 3 with `TIER3_CAPTURE_MISSING: <symbol>`
  before any symbol is built.
- Matcher (Stage 2, counting): an inventory without Tier 3 rows
  raises `TIER3_INVENTORY_MISSING: <symbol(s)>` before any pool
  is counted.

There is no code path that counts a Tier-3-less pool, shrinks the
tier, or substitutes another symbol. A Tier-2-only count, if it is
ever wanted, is a different preregistered question (a Text 0
amendment), not a fallback of this package.

## Decision requested (when Stage 2 is scheduled)

1. Settle the Twelve Data rights basis for the capture
   (evaluation scope vs Grow), OR
2. amend Text 0 to a Tier-2-only pool definition (weaker question;
   the per-tier G7 texts were drafted assuming both tiers), OR
3. defer Stage 2 until the rights basis lands with Stage B.

This package takes none of these. It prepares everything that
does not depend on the answer.
