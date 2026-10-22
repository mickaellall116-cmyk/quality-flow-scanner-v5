# SPEC — constructor guard v2 (candidate)

**Task:** -89. **Design authority:** -86 REMEDIATION_PLAN §F3
(Claude's -82 re-review HOLD on the constructor). **Base:** -84
SPEC_GUARD_H3B + guard/constructor_guard.py (sha256 ee403f9a…,
"h3b-candidate-1", 12/12). This spec covers only the v2 DELTA;
the H3b spec's placement, adoption-form, and no-in-place-edit
rules are inherited unchanged.

**Module:** `guard/constructor_guard.py`, GUARD_VERSION
`guard-v2-candidate-1`. It wraps the same constructor boundary
(validator ca3bafd8… → guard → pinned constructor d47e8df1…),
exercised here against the pin-verified byte-copy only.

## Refusal classes (check order is contractual)

Input, BEFORE the constructor is invoked (spy-verified):
1. `CONSTRUCTOR_GUARD_DUPLICATE_TIMESTAMP` — v1, unchanged
   (semantics, message format, first-appearance ordering).
2. `CONSTRUCTOR_GUARD_TIMEZONE` — the input index must be tz-aware
   America/New_York, the chain's declared input basis. Naive,
   fixed-offset, or any other zone refuses, naming the found tz.
   Rationale: the pinned constructor tz_converts any aware index
   silently; a fixed offset cannot represent EST/EDT transitions,
   so accepting one re-opens the 2023-10-03 candle-failure class
   at the input boundary.
3. `CONSTRUCTOR_GUARD_NON_MONOTONIC` — the index must be strictly
   increasing; the refusal names the first violating row pair.
   Rationale: the constructor sorts silently (sort_index) — the
   same silent-repair class as the duplicate merge.

Output, AFTER construction:
4. `CONSTRUCTOR_GUARD_DUPLICATE_TIMESTAMP` — v1 post-check.
5. `CONSTRUCTOR_GUARD_VOLUME_CONSERVATION` — whole-frame law:
   every output bin's Volume equals the sum of its constituent
   input volumes, and Σ output == Σ constructed-span input. The
   expectation is computed by an independent shadow binning of the
   guarded input (the constructor's documented semantics —
   in-session filter, interval-end precedence
   validated_ends → interval_end → grid derivation, as-of
   constituent cutoff, completed-bin emission, OHLC-dropna
   exclusion — tracking Volume only). A constituent dropped or
   altered between the guard's pre-check and aggregation is
   therefore caught (V2-6). If the expectation cannot be computed
   (no session close available, off-grid bar, missing validated
   end), the guard refuses with the same code — fail-closed,
   never skip.

## Pinned behavior record (V2-3)

Fixed-offset (−05:00) wall-clock stamps spanning the 2024-03-10
spring-forward boundary, run UNGUARDED through the pinned
constructor under pandas 2.2.3 with warnings-as-errors:
  * completes with NO warning raised — the failure is silent;
  * 2024-03-08 (EST; fixed offset correct) bins are correct
    (406 / 315);
  * 2024-03-11 (EDT; stamps one hour stale) bins are silently
    wrong: 09:30 bin Volume 303, 13:30 bin Volume 312, vs the
    NY-true 406 / 315; the 15:30 stamp converts to 16:30 EDT, is
    out of session, and is dropped (session total 615 vs 721);
  * output csv sha256
    90cc21e7efdbec9ad7aae6008b2982a031b41f88e8edbda7e33c7b87e7f32f6b.
The v2 suite asserts this record exactly; an environment change
that alters unguarded behavior (e.g. a future pandas that DOES
warn) fails the suite loudly, forcing re-adjudication of the
record rather than silent drift.

## Suite

`guard/test_constructor_guard_v2.py` — exit 0, **15/15**:
the -84 suite (byte-copy, sha256 06029fd2…) executed unchanged as
a subprocess against this module (**12/12** — the regression
floor), a version/code anchor, and V2-1…V2-6 per the -86 spec
(V2-5 additionally pins byte-identity to the -84 clean case, csv
sha prefix 077e0c6b81509624 from -84 TEST_EVIDENCE G3, and the
per-bin conservation map 406/315/406/315/406, total 1848).
Repeat-identical across two runs (see TEST_EVIDENCE.md).

## Non-goals / invariants

The guard never merges, drops, sorts, converts, or repairs
anything; on valid input the output is byte-identical to the
unguarded path. The pinned constructor is never edited — adoption
is a successor pin + route re-proof (ADOPTION_NOTES.md, GO G3-v2).
