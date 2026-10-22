# ADOPTION NOTES — guard v2 / checker v2 (task -89)

**Status: BOTH CANDIDATES ARE OFFLINE_CANDIDATE_NOT_ADOPTED.**
This package adopts nothing, moves no pin, and edits no pinned or
production file. Each candidate has its own separate GO. The
re-proof sequence for the constructor chain is -84's
REPROOF_PLAN.md (cited, unchanged), as extended by -86 §F3.

## A. Guard v2 — GO G3-v2 (Mike, after Claude + ChatGPT review)

Adoption form (inherited from SPEC_GUARD_H3B §4 / -84 REPROOF_PLAN
§A): a NEW constructor version — the v2 guard folded into a
successor of `construct_4h.py`, or bound as a named chain element
the entrypoint must call — minted under its own adjudicated task.
Never an in-place edit of the pinned constructor.

What changes on adoption:
  * constructor pin d47e8df1… → NEW successor pin.
  * route manifest 9573118c… → superseded by a successor manifest
    binding the new constructor pin.
  * entrypoint pin 84ccd2c6… → changes ONLY if its bytes change
    (wrapper-binding form); re-proof assumes it changes.
  * fixture copies citing d47e8df1… (the -82, -84, and -89
    packages) → re-extracted at the new pin; suites re-run; the
    -82 T3 expectation inverts (merge → refusal) under the guard
    and is re-baselined as a NEW expectation in the successor
    package, never edited in the old ones.
What does NOT change (verify-don't-assume at re-proof):
  validator ca3bafd8… · CLI-guard constructor 3f432e7e… · r5 set
  (adapter 6980b5b3… / driver d11c6b58… / gate 94ef967c… /
  executor bbc23616…) · supplement v2 55ad6f40… · calendar
  artifact 3358f2d9… · fold materializer / inference layer.
Re-proof sequence: -84 REPROOF_PLAN §A steps 1–6, with the -86
extension — step 3's candle-parity gate (byte-identical OHLCV,
DST-spanning, two window lengths, guard active on both paths)
gains the V2-3 fixed-offset DST case and a guard-active
duplicate-injection parity case.
Gate position: per -86/D-85-3, G3-v2 adoption is a HARD
PREDECESSOR to construction of any captured bytes. The -88
capture manifest's provenance chain assumes it lands first.

## B. Checker v2 — GO G4 (adjudication; carries two payloads)

Adoption makes checker v2 the qualification instrument of record
(-86 DATA_ROUTE_DELTA_85 D-85-6), minting a successor instrument
pin; the -82 v1 checker (0a7712be…) remains the cited instrument
until then. The -88 manifest discloses that pilot checker
records are v1 until G4 lands — G4 closes that gap.

**G4's GO includes — explicitly — the re-analysis of the -75
Day-1 snapshots under checker v2.** That re-analysis is part of
G4, and it was NOT executed in this package: the -75 snapshots
(archive captures/td_probe_day1_20261021/, commit 2f223cf, and
the local store) are untouched by -89, no snapshot bytes were
read by these suites, and every fixture here is synthetic. G4
also carries adoption of the corrected TSLA C2 label
("C2 NOT_EVALUABLE — VOLUME COMPLETENESS FAILURE", already PASSED
in Claude's re-review) into reporting.

What changes on adoption:
  * the qualification instrument of record: v1 → v2 (new pin).
  * DECLARED-BOUNDARY SEMANTICS CHANGE (disclosed in
    SPEC_CHECKER_V2): v1's blanket |log step| > log(1.5) suspect
    rule is replaced by anchor classification. A readout produced
    under v1 STEP semantics is NOT silently comparable to a v2
    readout; any pre-adoption readout citing the v1 STEP lane
    must be re-derived under v2 before being cited post-adoption.
    (The -82 floor finding in TEST_EVIDENCE.md is the worked
    example of why: lanes added in v2 can see defects v1 could
    not, on the same bytes.)
  * S2 reopen trigger T2 (per the -87 freeze, adopted 2026-10-21)
    becomes armed on real data: checker v2's STEP-ALL / VBASIS
    lanes firing on captured data is one of the three standing
    triggers that reopen the retired REQ-S2.
What does NOT change: the checker's single-series design
constraint; the COUNT/ANOMALY v1 classes and verdict strings; the
-82 package (never edited — the floor finding is recorded here
and in TEST_EVIDENCE, for adjudication to note against -82 by
reference if it wishes).

## C. What this task did NOT do

No adoption, no pin minted or moved, no production or pinned
file edited, no vendor call, no real-data run, no -75 snapshot
read or re-analysis, no holdout access, no backtest. The two
candidates cite the current pins as evidence and will themselves
need re-basing if an adoption step above is ever executed.
