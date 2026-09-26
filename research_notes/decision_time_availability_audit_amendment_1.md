# Decision-Time Availability Audit — Amendment 1

Status: FROZEN GOVERNANCE / FAILURE-MODE CONTROL
Date: 2026-09-25
Supersedes operational ambiguities in `research_notes/decision_time_availability_audit.md`.
Does NOT modify V5.4, ERD v0.1, or any killed research family.

## 1. Family-level decision clock (AV-01)
Every candidate `family_id` must preregister a single deterministic `decision_at` generator before any availability ledger or performance replay is built.

Required fields:
- decision cadence and market/session calendar;
- exact timestamp rule in UTC plus source timezone;
- whether the decision is evaluated at bar open, bar close, scheduled event boundary, or other explicit instant;
- execution timestamp rule separately from `decision_at`;
- calendar/library version or frozen session table used.

The audit implementation must derive `decision_at` from the frozen family specification. Callers may not supply an alternate convention at runtime.

Changing the rule after results are inspected requires a dated amendment and does not erase the family’s prior multiple-testing history.

## 2. Availability semantics and latency (AV-05/06/07/11/12)
For non-price/external features:

`available_at` = earliest timestamp at which the exact value/version was delivered by the specific data channel assumed available to the live strategy.

The underlying event/publication timestamp is stored separately as `event_at` and is not a substitute for feed delivery.

Eligibility is:
`available_at + latency_buffer < decision_at`

The latency buffer is frozen per feature/feed in the candidate preregistration from operational evidence, not performance. No result-driven tuning. The primary buffer is singular. A small a-priori sensitivity range may be reported but cannot replace the primary.

Date-only/coarse timestamps are ineligible for intraday use. For daily-or-slower candidates, their conservative eligibility instant must be preregistered; absent documented feed semantics, use the next tradable session after the dated observation.

At ingestion each timestamp carries:
- `availability_provenance = vendor_recorded | feed_log | inferred`;
- timestamp precision;
- feed/source/version;
- timezone.

`inferred` observations are excluded from the primary replay. Any use as sensitivity-only must be explicitly preregistered.

The delayed-availability diagnostic shift is frozen per feature type before performance inspection.

## 3. Immutable revision/restatement ledger (AV-02)
Facts that can revise/restated must be stored append-only, keyed by a permanent security identifier plus fact identity/event period.

Minimum row fields:
- permanent_security_id;
- display_ticker;
- fact_id / event_period;
- value;
- event_at;
- available_at;
- vendor_version_id or immutable content hash;
- ingestion_at;
- supersedes_version_id / superseded_by;
- source/feed/version.

Historical selection rule:
at a given `decision_at`, choose the latest version satisfying
`available_at + latency_buffer < decision_at`.
Never query a vendor's current/latest value and project it backward.

Raw source snapshots and hashes are retained so a historical decision can be reconstructed.

## 4. Permanent identity and corporate actions (AV-08)
All joins use a permanent identifier appropriate to the source (e.g. FIGI/CIK/vendor security ID) plus an effective-dated identifier map. Ticker is display metadata only.

Ticker changes/reuse, mergers, acquisitions, spinoffs, IPOs, delistings and bankruptcy dates must be effective-dated. No record may cross entity identity because of ticker reuse.

Price adjustment semantics are frozen per feature:
- features requiring tradable contemporaneous prices use data transformations proven not to incorporate future corporate-action knowledge;
- any fully adjusted price series must be documented and audited for whether the adjustment changes information available at historical decision time;
- raw and adjusted provenance is retained.

## 5. PIT universe/snapshot provenance (AV-04)
A candidate may use a historical universe/feature source only when PIT provenance is evidenced by at least one of:
1. vendor documentation explicitly guaranteeing point-in-time/survivorship-bias-free history for the used dataset;
2. vintage-stamped immutable source snapshots covering the period; or
3. independent reconciliation to a frozen PIT source sufficient to test coverage of entries, exits, delistings and historical membership.

A current membership list with historical prices/features attached is not acceptable.

Before performance interpretation, audit a preregistered sample of historical delistings/acquisitions/bankruptcies/ticker changes and confirm presence through the appropriate historical eligibility endpoint.

If PIT provenance cannot be established, the candidate is NOT READY for confirmatory interpretation.

## 6. Cross-sectional missingness control (AV-03)
For every cross-sectional ranking/gating decision, record:
- full PIT eligible universe count;
- valid-feature count;
- excluded count and reason;
- excluded vs included distributions for preregistered observable descriptors available at decision time (at minimum liquidity/size and sector when valid PIT classifications exist);
- coverage rate.

Primary policy: missing/LATE data never become neutral values, ranks or imputations.

A missingness placebo is required when the candidate's information source exhibits non-trivial or non-random coverage loss. The placebo preserves decision timestamps and exclusion counts and randomly excludes controls matched on preregistered PIT liquidity/size buckets. Its sole purpose is to test whether coverage mechanics themselves create apparent portfolio improvement. It is not a candidate model and cannot be selected/tuned.

Do not require placebo expectancy to equal exactly zero in a finite sample. Instead compare the real missingness effect against the preregistered placebo distribution; material overlap or placebo effects comparable to the candidate's claimed marginal value trigger REVIEW/FAIL depending on the candidate's frozen gate.

## 7. Baseline/candidate information symmetry (AV-10)
In any comparative portfolio replay, baseline and candidate are reconstructed from the same PIT security master, session calendar, execution model, costs, and availability framework for every input they actually consume.

A candidate-only external feature may of course not exist in the baseline. That feature's availability filter must not silently shrink the baseline universe. Comparison must separately report:
- frozen baseline on its legitimate information set;
- candidate overlay/book on its legitimate PIT information set;
- combined portfolio competition with exact candidate eligibility and displacement accounting.

Any baseline input that is external/revisable is subject to the same availability/version rules as candidate inputs.

## 8. Sector mapping freeze (AV-09)
Any sector-time diagnostic requiring classifications must reference a mapping artifact committed and hashed before the diagnostic result is inspected.

Point-in-time sector classifications are primary when reliable. If unavailable, static mapping is sensitivity-only and may not determine PASS/FAIL. Missing classification remains UNKNOWN. Amendments are dated and retain prior mapping hashes.

## 9. Deterministic tests
The implementation must pass at minimum:

### T1 Decision clock lock
Attempt to supply a runtime `decision_at` convention different from the frozen family rule.
Expected: hard refusal.

### T2 Revision selection
Two versions of the same fact:
- v1 available 2025-02-01 12:00;
- v2 correction available 2025-08-01 12:00.
Decision 2025-03-01 selects v1 only.
Decision after buffer on 2025-08-01 selects v2.
Expected: exact version correctness.

### T3 Impossible-future feature
Inject a feature whose availability is mechanically after every historical decision.
Expected: 100% excluded; any accepted row = FAIL.

### T4 Feed-vs-event timestamp
Event timestamp precedes feed delivery by 6h.
Expected: eligibility uses feed delivery + buffer, never event timestamp.

### T5 Coarse timestamp
Intraday candidate receives date-only external feature.
Expected: primary intraday eligibility rejected unless a frozen documented delivery convention resolves it.

### T6 Ticker reuse
Entity A and Entity B share the same ticker in disjoint periods.
Expected: no fact/price/universe record crosses permanent IDs.

### T7 PIT delisting
Synthetic/fixture security is eligible until historical delisting date and absent after.
Expected: exact effective-dated membership.

### T8 Baseline symmetry
Inject a late value into an external baseline input.
Expected: baseline reconstruction rejects it under same availability machinery.

### T9 Missingness accounting
Drop a known subset at a decision.
Expected: ledger reports exact universe/valid/excluded counts and reasons; matched-placebo generator uses only PIT matching fields.

### T10 Sector freeze
Attempt to change mapping after a result artifact exists without a dated amendment.
Expected: provenance check fails.

## 10. Decision rule
Framework implementation verdict:
- FAIL if any accepted decision uses a value/version not demonstrably available after applying the frozen latency rule, wrong entity identity, non-PIT universe membership, or post-hoc mapping/decision-clock substitution.
- REVIEW if timing is valid but PIT provenance, inferred timestamps, or missingness mechanics materially threaten interpretation.
- PASS only after the deterministic tests pass and candidate-specific replay satisfies all frozen availability/provenance controls.

Passing this framework remains necessary, never sufficient, for a candidate trading PASS.

## 11. Researcher degrees of freedom now frozen before candidate results
Each candidate preregistration must freeze:
- decision clock;
- authoritative feed/source hierarchy;
- latency buffer;
- coarse timestamp policy;
- inferred timestamp policy;
- delayed-diagnostic shift;
- permanent identifier source;
- PIT universe source/provenance test;
- missingness placebo matching variables and seed/design;
- sector mapping source if used.

No choice above may be selected because it produces better historical performance.
