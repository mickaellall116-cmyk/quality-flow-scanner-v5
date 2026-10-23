# COVERAGE IMPACT RECORD — QF-TD-PILOT-ADJUDICATION-20261023-02

Companion to ADJUDICATION.md. This record exists so the SMCI hole
is a stated fact in every downstream document, never a silent one.

## Frozen membership — unchanged

UX51 membership is FROZEN under Universe Ruling G6, Option A
(freeze record `research_notes/UNIVERSE_FREEZE_OPTION_A_20261021.md`,
commit `2705c02`; membership sha256
`b5d8877ee7d6ddd105904d7f4ca35901ebb611dac7afeab2f7676529c112e6a2`):
44 equities + 7 crypto pairs. **SMCI remains a member.** The
classification below removes nothing from the universe; it marks
one member's holdout-window leg as not evaluable on this provider's
bytes. Any future document that reports coverage as "44/44" or
"51/51" without this qualification is wrong.

## Qualification state after the pilot + this adjudication

| Branch | State |
|---|---|
| Equities with full-span (HO+DEV) completeness-qualified bytes | **4 of 44** — NVDA, TSLA, AAPL, SPY (admitted bytes, ADJUDICATION.md Result 1) |
| SMCI HO leg | **NOT_EVALUABLE_PROVIDER_VOLUME** (19 price-moving zero-volume bars, April 2024; ADJUDICATION.md Result 2) |
| SMCI DEV leg | Never attempted (pilot stopped at the abort); no bytes exist |
| Remaining 39 equities | No bytes captured; Phase 1 never authorized or run |
| Crypto (7 pairs) | **0 of 7 attempted** — BTC stamp phase untested (pilot gate criterion (iv) undetermined); the route is NOT qualified for the crypto branch |

**44/44 equity qualification is UNMET**, on two independent
grounds: (i) SMCI's HO leg is classified not evaluable; (ii) 39 of
44 members have no captured bytes at all. Separately, 7/7 crypto
qualification is unmet (0 attempted).

## What a corrected baseline loses if SMCI's HO window stays not evaluable

Stated mechanically, without softening:

1. The corrected baseline is specified over the frozen UX51 across
   the 751-session union, with the HO window (2023-10-19 →
   2024-09-13, 227 sessions) as the sealed holdout span and DEV
   from 2024-09-16. A baseline computed "as specified" requires an
   evaluable HO leg for every equity member. SMCI's is not
   evaluable on Twelve Data bytes. **The baseline as specified
   cannot be computed.**
2. The available paths are exactly two, and the choice is a
   decision for Mike/adjudication — not this package's:
   (a) compute the HO-window baseline over **43 of 44** equities
   with SMCI's exclusion-by-classification DISCLOSED in the
   baseline's own record (membership frozen; the exclusion is a
   data-qualification fact, not a universe change) — accepting
   that comparability to the legacy C1 record, which included
   SMCI, is broken in a stated way; or (b) hold the baseline until
   an SMCI disposition produces evaluable HO bytes by another
   route — no such route currently exists (a Twelve Data re-ask
   is the prohibited retry and would be expected to return the
   same zeroed volumes; Yahoo 1h reachback no longer covers the
   HO window).
3. A DEV-only SMCI capture does NOT repair the hole: the missing
   span is the holdout window itself, fold discipline forbids
   substituting windows, and the holdout stays sealed — DEV bytes
   cannot be back-filled into an HO role under any labeling.
4. What is NOT lost: SMCI's membership, its DEV-window future
   (contingent on disposition), the 4 qualified full-span symbols,
   and the audit trail — the quarantined body is preserved
   byte-exact in the private archive under its UNQUALIFIED label.

## Standing instruction to downstream documents

Any coverage claim, capture manifest, readiness card, or baseline
preregistration that cites this pilot must carry the sentence:
**"SMCI HO: NOT_EVALUABLE_PROVIDER_VOLUME (pilot adjudication
20261023_02); equity qualification 4/44 full-span, 44/44 unmet;
crypto 0/7 attempted."** — or a successor sentence from a later
adjudication that supersedes this record BY REFERENCE.

— Muse
