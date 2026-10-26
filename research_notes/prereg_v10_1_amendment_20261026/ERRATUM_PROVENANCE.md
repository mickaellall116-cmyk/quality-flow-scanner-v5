# Erratum — Provenance of the v1.0 Package (C1 Finding 4)

**The v1.0 record contains a false statement, corrected here.**

Preregistration v1.0 (commit `4ffb8fb`) states, in two places, that no
vendor call was made in producing the package:

- `PACKAGE_README.md`: "No performance test was run, no holdout data was
  accessed, and **no vendor call was made in producing this package**."
- `bridge_record_20261026.md` (also appended to
  `research_notes/bridge_thread.md`): "No performance test was run, no
  holdout data was accessed, and **no vendor call was made in producing
  this package**."
- The commit message of `4ffb8fb` itself: "No performance run, no
  holdout access, **no vendor calls**." (Commit messages are immutable;
  this erratum is the correction of record for that sentence too.)

The first two clauses are true. The third is **false as applied to the
package**, because the package includes the Tier 3 list, and generating
that list fetched market data.

## What actually happened (the corrected record)

On 2026-10-26, generating the Tier 3 list under the frozen rule
(`TIER3_RULE_FROZEN.md` v1.0, S4) fetched **Yahoo Finance daily bars via
the yfinance library for the 2,561 step-7 candidate symbols** — completed
sessions 2026-09-01 → 2026-10-25, the rule's current-liquidity window.
The fetch ran in full on each of the four generation runs (script v1.0:
runs 1–2; script v1.1, with its disclosed retry pass: runs 3–4). Scope
and limits of those calls:

- Public web data from Yahoo Finance; **no licensed API key, no vendor
  account, no Twelve Data call** of any kind.
- Candidate symbols only: **no symbol in UX51 or X2 was ever fetched**,
  and no data from the sealed holdout window (2023-10-19 → 2024-09-15)
  was requested or received for any symbol.
- Only aggregates were computed and (for the 12 selected symbols)
  persisted: ADV20, last close, bar count. **No return, forward return,
  or performance quantity was computed for any symbol.**

## How the false statement arose

The sentence described the v1.0 *assembly* lane's own work — assembling
documents, audits, pins, and packages — which indeed made no data calls.
It was written package-wide, over a package that also contains the Tier 3
generation lane's output. Notably, the Tier 3 lane's own record
(`REPRODUCIBILITY_RECORD.md`, inside the v1.0 package) disclosed the
Yahoo fetches accurately and in detail; the false claim is confined to
the two assembly/bridge texts quoted above and to repetitions of the same
claim in the v1.0 delivery record (including the bridge record's
"POWER_REPORT.md (variance only; both verdict grades powered per
endpoint…)" phrasing, corrected separately in the amendment's
supersession table).

## Correction and going-forward rule

The corrected provenance statement for the v1.0 package is: *no
performance test was run; no holdout data was accessed; the only data
calls made in producing the package were the Yahoo Finance daily-bar
fetches for Tier 3 candidate liquidity described above.* This amendment
itself was produced with **zero network data calls**: all of its inputs
were already captured on disk, its generator is local-input-only, and no
replacement fetches were made to repair any gap (the S4 shortfall is
disclosed, not repaired — see `tier3_inputs/INPUTS_AND_GAPS.md`).
