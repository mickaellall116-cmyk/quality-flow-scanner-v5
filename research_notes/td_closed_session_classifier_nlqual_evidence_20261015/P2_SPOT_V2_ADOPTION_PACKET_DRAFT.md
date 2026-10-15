# P2-SPOT v2 adoption packet — DRAFT ONLY (QF-TD-CLOSED-SESSION-CLASSIFIER-NLQUAL-20261015-02 r1)

Status: DRAFT. Nothing in this packet is adopted. It does not authorize any
dispatch, vendor call, or protocol change. Prepared alongside the
NL_CLASSIFIER_PASS result (research_notes/TD_CLOSED_SESSION_CLASSIFIER_NLQUAL_20261015.md).

## What adoption would change — the complete delta

1. **Supplement re-pin (the only substantive change).** The P2-SPOT v2
   supplement's calendar pin moves from the -17 candidate's CP1-derived
   `pandas_market_calendars==5.5.0` to the qualified lineage **NL-20261015**:
   `pandas_market_calendars==4.5.1`, exact `f64d12f` lock
   (lockfile sha256 `08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068`),
   mechanism `pilot_harness/validate_input.py` sha256
   `1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58`,
   CPython 3.12.3 environment as qualified in TD_NEW_LINEAGE_QUAL_20261015
   (commit `7de7950`). Candidate supplement file:
   `p2_spot_supplement_v2_nl20261015_candidate.json` in this package
   (sha256 `9c71233003771d66cf81e99ae01a410ba8943aedfcce8a8c6411dfb51edacd32`).
   Its `entries`, `base_manifest_digest`, class, and lifecycle event are
   identical in content to the -17 candidate supplement; only the calendar
   block and lineage metadata differ.
2. **Candidate code merge (no logic change).** The -17 candidate collector
   (`td_min_collector.py` @ `ab254c3458697dd450356146abcf4ad4f75ecef4`,
   file sha256 `b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c`)
   would be merged as-is. NLQUAL modified zero candidate bytes.
3. **Runtime environment.** Any future run relying on the classifier must
   execute in an environment reproducing NL-20261015 exactly (lock +
   interpreter + mechanism hash), with the version conjunct failing closed
   on any drift — as proven by the N10 controls.

## What adoption would NOT change

- **P2 v1 remains UNMET.** REQ-SPT-07's v1 outcome stays HOLD; the
  closed-session class is a v2 evidence class only and is never rewritten
  into the v1 record.
- **REQ-SPT-08 remains NOT ATTEMPTED.** Adoption of this packet alone does
  not dispatch it. A future dispatch requires its own adjudicated live task
  (scoped/capped vendor authorization, credit budget, fail-closed
  discipline) — NLQUAL proved only its offline eligibility under the rule.
- The evidence class remains: never a receipt, never COMPLETED, never
  wire-verified identity evidence, never construction-admissible. The
  credit reservation for a classified request stands spent.
- -11 lineage remains UNKNOWN. Nothing here qualifies Twelve Data as a
  feed, opens corrected performance, or establishes an edge.

## Rollback

- Drop or revert the supplement (or restore the 5.5.0 pin): the classifier's
  version conjunct fails closed and every closed-day response returns to the
  pre-existing terminal HOLD path — the base collector behavior without a
  supplement is byte-identical (proven by fixture S2 and the -17 base
  regression suite, 19/19).
- Unmerge the candidate collector: the base candidate `b18db3ce` behavior is
  unchanged; no state produced by the classifier is a receipt, so no ledger
  migration is required. Closed-day `.closed_day.bin` evidence files are
  write-once artifacts and remain valid historical evidence either way.

## Remaining gates after this packet

1. ChatGPT adjudication of the NL_CLASSIFIER result package (this task's
   WORK RESULT) — acceptance is not assumed.
2. A separately adjudicated P2-SPOT v2 qualification definition if the v2
   lane is to be used (the v1 P2 gate is not retrofitted).
3. Any live dispatch (including SPT-08) only under a new scoped task with
   its own credit ceiling and authorization per the standing vendor-call
   rule; production/frozen-strategy changes remain gated at Mike's desk.
