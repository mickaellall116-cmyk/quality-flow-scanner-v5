# ERD v0.1 Amendment 2 — Pre-Data Harness Gap Audit

**Date:** 2026-09-27  
**Branch:** `erd-amendment2-predata-hardening`  
**Scope:** specification/code comparison only. No candidate-provider rows fetched. No ERD reaction, return, P&L, expectancy, or performance data generated or inspected.

## Inputs reviewed

- `new_system/DESIGN.md`
- `new_system/erd-v0.1-preregistration-amendment-1.md`
- `new_system/timing_audit/README.md`
- `new_system/timing_audit/audit_harness.py` (blob `016289d3bbd9945172c7500eaf157ee7c1680e13`)
- `new_system/timing_audit/event_clock.py`
- `new_system/timing_audit/test_edge_cases.py`
- GitHub Issue #3, "ERD v0.1 — non-Zacks earnings-data feasibility gate"
- Amendment 2 rev 2 draft text circulated in the research bridge (still DRAFT / not frozen)

## Verdict

**CURRENT INTRINIO HARNESS MUST NOT BE USED FOR BENZINGA/EODHD VALIDATION.**

It is a useful Amendment-1 artifact, but its sample construction and gate semantics do not satisfy the source-agnostic Amendment-2 design. Reusing it unchanged would weaken the preregistration.

## Critical / material gaps

1. **CRITICAL — sample is provider-defined.**  
   `draw_sample()` first filters the candidate provider's returned rows, then samples from that pool. Amendment 2 requires the 50 identities to come from an independent pre-existing frame before any candidate-provider pull. Provider coverage must not define who can enter the sample.

2. **CRITICAL — missing/ambiguous events are removed before the draw.**  
   `_is_qualifying()` rejects rows with missing time/code before sampling. Amendment 2 fixes the denominator at 50: a sampled identity that is missing, ambiguous, conflicting, or unverifiable at the candidate provider must remain in the denominator and count as failure. No redraw/replacement.

3. **CRITICAL — coverage denominator is wrong for Amendment 2.**  
   The current scorer reports a sample-level `coverage_proxy`. Amendment 2 requires exact-time completeness against the independently frozen eligible-history frame/member-quarters. Returned rows and the 50-event sample are forbidden denominators.

4. **CRITICAL — primary-source precedence is different.**  
   Current harness: IR page > newswire > NYSE calendar > vendor.  
   Amendment 2 rev 2: newswire publication > company IR publication > embedded-document time > SEC acceptance fallback; earliest availability-evidencing timestamp controls. Later updates never override original availability.

5. **CRITICAL — PIT revision check is incomplete.**  
   `detect_vendor_revisions()` detects field changes but does not require a versioned revision artifact with its own availability timestamp. Amendment 2 requires unversioned historical date/time/bucket changes to fail. A current snapshot cannot establish historical PIT correctness.

6. **CRITICAL — no availability/decision-time eligibility assertion.**  
   The Amendment-2 oracle uses an explicit availability inequality: data may be used only when its version was available by the frozen decision boundary after the frozen latency buffer. The current timing harness has no `available_at`, `latency_buffer`, or `decision_time` gate.

7. **MATERIAL — transition sample is not frozen.**  
   Amendment 2 requires two pulls separated by at least 30 days plus a fixed, seeded transition sample with smaller-population fallback and a zero-unversioned-change pass criterion. The current harness provides a diff function but no frozen transition-sample contract.

8. **MATERIAL — identifier/survivorship stress strata are absent.**  
   Amendment 2 requires the independent frame/sample to carry at least two delisted names, at least two ticker-change events, and acquisition/entity-transition coverage when the frame contains them, with smaller-population fallback. Current sample logic only enforces BMO/AMC/year strata.

9. **MATERIAL — provider search order/stop rule is not frozen.**  
   The source-agnostic design must freeze a finite candidate set/order and stop rule before access so the project cannot cycle through vendors until one passes. The Intrinio harness is single-vendor and does not implement provider-selection governance.

10. **MATERIAL — duplicate/conflict handling must move after independent selection.**  
    Current harness refuses a draw if candidate-provider conflicts exist anywhere in the provider-defined pool. Under Amendment 2, sample identities already exist before provider access. Exact duplicates may collapse; a conflict affecting a sampled event must fail closed for that event/provider and cannot trigger a redraw.

11. **MATERIAL — Issue #3 contains stale denominator language.**  
    The issue currently says missing/ambiguous timing is "excluded by rule." That conflicts with the corrected fixed-denominator rule for Amendment 2. The issue should be superseded or annotated, not treated as the controlling spec.

## Components that are worth preserving

The following mechanics are useful and should be ported rather than rewritten casually:

- canonical SHA-256 hashing and tamper refusal
- scorer-version freeze
- no-replacement philosophy
- zero-performance audit scope guard
- deterministic NYSE event-clock behavior, including early-close and exact-close handling
- exact-duplicate detection
- permanent-ID preference over ticker for cross-pull matching
- synthetic adversarial tests and fail-closed exceptions

## Safe next implementation step

Build a **new source-agnostic pre-data harness** beside the Amendment-1 Intrinio harness. It should:

1. ingest a frozen independent frame and exact 50-event identity file;
2. verify their hashes before accepting any provider rows;
3. accept provider exports as inputs rather than fetching them itself while Amendment 2 is still draft;
4. preserve all 50 sampled identities even when provider data is absent;
5. compute coverage against the frozen frame denominator;
6. enforce provider-availability / latency / decision-time rules;
7. enforce versioned-revision evidence across two pulls >=30 days apart;
8. score zero-tolerance failures separately from the ordinary 48/50 timing floor;
9. refuse all performance-like columns;
10. produce a provider gate report only — no ERD returns.

## Governance

No Benzinga, EODHD, FMP, Alpha Vantage, Intrinio, or other candidate-provider row data was fetched during this audit. The Amendment-2 performance gate remains closed. This branch is pre-data hardening only.
