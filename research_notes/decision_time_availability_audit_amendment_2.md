# Decision-Time Availability Audit — Amendment 2

Status: FROZEN GOVERNANCE / FAILURE-MODE CONTROL
Date: 2026-09-25
Builds on Amendment 1. No V5.4, ERD v0.1, or killed-family change.

## 1. Missingness-mask falsification rule
Test the information-availability mask, not candidate alpha.

For each decision with missing external data, apply the observed availability mask to the frozen baseline opportunity set under identical portfolio rules. Let M_obs be the change in the candidate's preregistered primary portfolio metric caused solely by that mask.

Generate exactly 1,000 placebo masks with a frozen seed. Each preserves the exact exclusion count per decision and samples exclusions within preregistered point-in-time size/liquidity strata. Use point-in-time sector only if reliable and preregistered.

For each placebo compute the same M_j.

Primary two-sided empirical p-value:
p = (1 + count(abs(M_j) >= abs(M_obs))) / 1001.

Frozen decision rule:
- p < 0.05: FAIL availability audit because observed missingness materially changes the frozen baseline beyond matched random coverage loss.
- p >= 0.05: diagnostic does not reject matched-random coverage loss; this does not establish candidate alpha or independently create PASS.
- fewer than 100 masked decisions, or inadequate matching controls in more than 10% of masked decisions: REVIEW for insufficient resolution.

Primary metric, seed, permutation count, matching strata, and rule are frozen before performance. Secondary variants are descriptive only.

## 2. Uniform preregistration manifest and provenance lock
Before any replay can expose performance, commit a machine-readable family manifest containing every Amendment 1 frozen item plus:
- missingness primary metric/rule;
- placebo seed, count, matching strata;
- latency buffer per feed/feature and hash/reference to operational evidence;
- PIT provenance spot-check design;
- revision tie-break;
- corporate-action price semantics;
- REVIEW resolution rule.

Manifest hash and commit must predate the first performance artifact. Replay code receives the manifest hash and refuses if required fields are missing, changed, or uncommitted. Later changes require dated amendments retaining prior hashes and multiple-testing history.

T11: alter latency buffer or another frozen field after a performance artifact without amendment. Expected: hard refusal.
T13: remove each required manifest field one at a time. Expected: replay refuses before loading performance data.

## 3. Revision tie-break
For identical eligible available_at timestamps, select by:
1. latest eligible ingestion_at;
2. if tied, lexicographically greatest immutable vendor_version_id/content hash.
ingestion_at never makes a version eligible before available_at.

Extend T2 with an identical-available_at case.

## 4. Corporate-action leakage test
T12: create a synthetic future split/dividend/corporate action. A feature evaluated before the action must be identical whether the future action record is present or withheld, unless the frozen feature explicitly consumes a contemporaneously known announced action that independently passes its availability gate.

A backward adjustment changing a pre-event feature solely because a not-yet-available future action was inserted is FAIL.

## 5. PIT provenance spot-check
Freeze before performance:
- minimum 20 historical membership transitions when available;
- at least 5 delistings/bankruptcies and 5 acquisitions/ticker/entity transitions when the source period contains that many;
- spread across at least 3 calendar years when possible;
- if population is smaller, audit all available cases and record limitation.
Freeze selection method and seed in the manifest.

## 6. REVIEW quarantine
REVIEW is non-confirmatory. A REVIEW candidate cannot be called PASS, support confirmatory interpretation, advance toward deployment discussion, or be used to tune a replacement rule on the inspected data.

Resolve the trigger through a dated preregistered amendment and rerun the affected audit/replay to PASS or FAIL. Multiple-testing history remains attached.

## 7. Framework gate
Framework may be called READY only after Amendments 1 and 2 are frozen, applicable T1-T13 tests pass, manifest/provenance lock is implemented, and no unresolved CRITICAL or MATERIAL audit finding remains.

READY refers only to the governance framework, not a trading candidate.
