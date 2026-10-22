# ADOPTION NOTES -93 — everything HOLD; the rulings that are Mike's alone

This package adopts nothing. It closes the implementation half of
Claude's -92 HOLD items and hands the decision half back, itemized.
Status of every gate after -93:

| Item | State after -93 | Whose move |
|---|---|---|
| CH-1 retirement | PASS conditions discharged: archive bytes verified byte-exact (SPEC §5), supersession note drafted | ChatGPT/Claude adjudication of the note; freeze record itself is never edited |
| Guard adoption (G3) | v3 candidate ready: NONFINITE, INTERVAL_END, CALENDAR_BINDING implemented + fixture-proven; version uniquely pinned | Adjudication, then Mike's G3-v3 GO (successor pin + route manifest + re-proof, as before) |
| Checker adoption (G4) | v3 candidate ready: STRUCTURAL, invalid-OHLC, boundary-UNTESTABLE, crypto mode implemented + fixture-proven | Adjudication, then Mike's G4 GO. The -75 snapshot re-analysis rides on G4 and was NOT executed here |
| R1–R5 freeze (G2 ext) | -88 text + -93 amendment clauses AM-1…AM-6 ready as one adoption unit | Adjudication of the amended text, then Mike's one-GO freeze |
| Credit scheme | HOLD minor lifted in substance: one receipt schema (kind-discriminated), pacing/reset/closing-read accounting stated inside BLOCK-BRACKET-10; totals unchanged (146 expected / 289 worst) | Adjudication; no scheme change to totals |
| Capture / pilot | Still HOLD. Nothing here authorizes a vendor call | Mike's capture GO (route + ceiling + manifest pin incl. the §4.6 session-table line) after adjudication |

## Mike-only rulings (explicit, per the -92 assignment — not assumed, not recommended into existence)

1. **Sequence.** Probe legs (R7 from 2026-10-28, R30 from
   2026-11-20, each separately GO'd) vs the capture sequence
   (pilot → Phase 1): which runs first, under the §4.5 discipline
   (never a shared execution day; separate chains; citation by
   reference, never replacement).
2. **Crypto pilot implementation.** Whether the pilot's BTC-USD
   chunks are qualified under the v3 checker crypto mode as
   specified — including its two disclosed convention points
   (fall-back repeated hour = DUPLICATE_TIMESTAMP structural
   defect; spring-forward absent hour = COUNT missing-bar) — or
   whether adjudication wants a different DST convention first.
3. **Ceiling: 300 vs ~320.** The corrected worst case is 289.
   Under 300 the margin is 11 credits; ~320 restores a ~31-credit
   margin. The -91 position (300 stands, no amendment requested)
   is unchanged by -93; the choice is Mike's at the capture GO,
   and -93 flags it only because the -92 assignment named it.
4. **Calendar binding at adoption.** Whether the G3-v3 route pin
   makes `expected_calendar_sha256` mandatory for every guarded
   construction (the candidate keeps it optional to avoid silently
   breaking the v2/-91 call contract).

## Disclosed divergences and convention points (nothing tuned around)

- Guard v2 suite vs v3 module: 14/15 — the sole divergence is the
  suite's version-anchor assertion, superseded by the deliberate
  v3 version bump (Claude's pin-minting condition). All behavioral
  checks pass against v3.
- Checker v1 floor vs v3 module: 10/14, identical four checks as
  against pristine v2 — the -82 fixture's own embedded undeclared
  step (documented in -89), not a v3 effect.
- Checker v3 tightens one v2 classification on purpose: an
  all-zero flat bar is a ZERO_OR_NEGATIVE_PRICE defect, not
  NO_TRADE_FLAT (SPEC §2.2).
- Guard interval-end exactness admits two final-bar conventions
  (close, or nominal next hour); adjudication may tighten to one
  (SPEC §1.2).
- The pinned constructor cannot construct a column-less frame in
  its fixture copy (its derivation path imports `validate_input`);
  chain fixtures therefore always carry explicit interval_end
  (SPEC §1).

## Consolidated pin (MANIFEST_AMENDMENT §4.6)

Over the eight entries fixed today: **`258aea36cf9b07f33bfa38cbbe85fed13dd655980f1cdf681730a56e6932fd34`**
(recipe in §4.6; the session-table line joins at the capture GO).
