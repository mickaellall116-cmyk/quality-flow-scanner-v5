# Amendment 1 — Independent Adversarial Re-Audit

Auditor: Claude (independent methodology auditor)
Target: research_notes/decision_time_availability_audit_amendment_1.md, commit b02becba34fd3b507eb1ecec995eabea6b466c3b
Scope: Amendment 1 text only. No candidate, V5.4, or ERD performance data reviewed or referenced.

## Executive Verdict: NOT READY

Amendment 1 substantially closes the framework. Ten of twelve original findings are fully resolved with concrete mechanisms and matching deterministic tests. One original finding (AV-03) remains only partially closed, and the amendment introduces one new MATERIAL gap: asymmetric provenance enforcement between the sector-map freeze and latency-buffer freeze. Both are narrow and fixable.

## AV-01 through AV-12
- AV-01 CLOSED — frozen deterministic decision_at per family; runtime override forbidden; T1.
- AV-02 CLOSED with minor residual — append-only revision ledger and T2; tie-break missing for identical available_at.
- AV-03 PARTIALLY CLOSED — accounting is specified, but placebo pass/fail criterion is qualitative.
- AV-04 CLOSED with minor residual — PIT provenance paths and T7; spot-check sample design unspecified.
- AV-05 CLOSED — feed-delivery available_at and T4.
- AV-06 CLOSED with material enforcement residual — buffer frozen operationally, but provenance enforcement weaker than sector map.
- AV-07 CLOSED — conservative coarse timestamps and T5.
- AV-08 CLOSED with minor residual — permanent IDs/corporate-action semantics; no dedicated corporate-action leakage test.
- AV-09 CLOSED — sector map committed/hashed before inspection; T10.
- AV-10 CLOSED — baseline/candidate information symmetry; T8.
- AV-11 CLOSED — delayed diagnostic shift frozen.
- AV-12 CLOSED — explicit provenance categories.

## New findings
N-1 MINOR: identical available_at tie-break absent. Add deterministic ingestion_at then vendor_version_id tie-break and T2 subcase.

N-2 MATERIAL: missingness-placebo decision rule is qualitative. The distributional approach is methodologically better than requiring exact zero, but the statistic and decision threshold must be frozen before results and included in preregistration completeness.

N-3 MATERIAL: latency-buffer freeze lacks commit/hash-before-inspection enforcement equivalent to sector mapping. Add consolidated provenance enforcement and test.

N-4 MINOR: add deterministic corporate-action price-adjustment leakage test.

N-5 MINOR: add consolidated preregistration-completeness gate for all frozen controls.

N-6 MINOR: REVIEW must be explicitly non-confirmatory and unable to advance until resolved to PASS/FAIL.

## Remaining researcher degrees of freedom
- quantitative missingness-placebo decision rule;
- evidence justifying latency buffer;
- PIT provenance spot-check sample design;
- identical available_at tie-break;
- REVIEW resolution path.

## Missingness-placebo assessment
The distributional/matched-placebo method is acceptable and preferable to an exact-zero point-null requirement. The remaining problem is lack of a preregistered statistic and quantitative rule; this must be fixed before results are inspected.

## Minimum additional amendments/tests
1. N-2: explicit preregistered quantitative missingness-placebo rule and near-boundary synthetic test.
2. N-3: provenance/hash enforcement for latency buffer, ideally all preregistration controls.
3. N-1: deterministic tie-break and T2 extension.
4. N-4: corporate-action leakage test.
5. N-5: consolidated preregistration-completeness test.
6. N-6: REVIEW cannot support confirmatory interpretation or advancement.

Items 1–2 block READY; 3–6 are required hardening but do not independently block READY after 1–2 are addressed.

This file is an archival transcription of Claude's user-supplied re-audit; substantive meaning is preserved.