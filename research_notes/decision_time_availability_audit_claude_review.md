## Decision-Time Availability Framework — Adversarial Pre-Validation Audit

**Auditor:** Claude (independent methodology auditor)
**Target:** GitHub commit `291e224c95f8f72b93b5a3b912ba3bd2ed0e1f5a` — `research_notes/decision_time_availability_audit.md`
**Scope:** The `available_at <= decision_at` governance framework itself. No candidate performance, ERD data, or V5.4 results were reviewed or referenced in forming this judgment.

### Executive Verdict: **NOT READY**

The framework's core gate (`available_at <= decision_at`, hard exclusion of LATE observations) is sound as far as it goes, but several load-bearing definitions it depends on are either undefined or left discretionary in what was provided — most importantly, **`decision_at` itself is never pinned down**. A gate that compares against an unpinned reference point can be satisfied trivially by choosing a convenient `decision_at`. This and the gaps below need resolution before the framework can be trusted to certify any candidate.

---

### Findings

**AV-01 — CRITICAL — `decision_at` is undefined at the framework level**
*Problem:* The document specifies what must be `<= decision_at`, but never specifies what generates `decision_at` itself — cadence (per-bar, daily, continuous), or which specific instant in a scanning loop counts as "the decision."
*Failure example:* A researcher testing two variants could quietly use end-of-day `decision_at` for one and pre-market `decision_at` for another, making a LATE feature look available in one run and not another — with no rule broken, because nothing pins the reference point.
*Correction:* `decision_at` must be defined once, per family_id, before the availability ledger is built — matching the candidate's own preregistered decision cadence (e.g., ERD's next-session-open, V5.4's 4H bar-close) — and frozen alongside it, not left to the audit script's caller.
*Falsification test:* Re-run the same historical ledger with two different plausible `decision_at` conventions for the same family; results must be identical if the framework is genuinely enforcing a single fixed convention. If they diverge, the gate is not actually pinned.

**AV-02 — CRITICAL — No revision/restatement storage model specified**
*Problem:* Section 7 requires excluding LATE observations but never requires storing multiple historical vendor values per fact. Without an append-only, version-aware ledger, "the value on file" for a past date is whatever the vendor's *current* database says it was — which is frequently the *latest revision*, not what was knowable at `decision_at`.
*Failure example:* A company's Q2 revenue is revised six months later; if the database only stores the final value, a decision made the week after the original release silently uses the corrected number.
*Correction:* Require an immutable, append-only record per `(symbol, fact, event_period)` with each row carrying its own `available_at`, `vendor_version_id`, and a `superseded_by` pointer. Value selection at any `decision_at` = the row with max `available_at <= decision_at` for that tuple — never "current" or "latest" value.
*Falsification test:* Inject a synthetic fact with two vendor versions (original + later correction) into the harness; confirm the framework retrieves the original at an early `decision_at` and the correction only at a `decision_at` on or after the correction's own `available_at`.

**AV-03 — CRITICAL — Cross-sectional missingness may itself carry information**
*Problem:* Ranking only the subset with valid contemporaneous data (e.g., 150 of 200) can encode survivorship/quality bias if the *reason* for missingness correlates with the outcome (smaller/troubled names have slower or absent vendor coverage).
*Failure example:* Names approaching distress get dropped from a data provider's feed before they're formally delisted; excluding them from ranking systematically removes future losers, inflating the apparent edge without look-ahead in any single field.
*Correction:* Report, per ranking period, the count/characteristics (size, sector, liquidity) of excluded names, and run a missingness-matched placebo — e.g., randomly exclude the same fraction of the eligible universe (matched on liquidity/size) and confirm this does not itself produce an "edge."
*Falsification test:* Missingness-matched placebo expectancy must not be statistically distinguishable from zero; if it is, missingness is doing work the framework isn't accounting for.

**AV-04 — CRITICAL — Vendor-snapshot backfill/purge risk unaddressed**
*Problem:* Nothing confirms the historical universe/feature data is a genuine point-in-time snapshot rather than a "current membership list with history attached." Many commercial datasets retroactively add coverage for names that later became liquid/notable and purge delisted/failed names from what looks like historical files.
*Correction:* Require documented proof (vendor attestation, vintage-stamped snapshot files, or independent cross-check against a known-frozen PIT source) that the historical file used was captured *at* or near the historical date, not reconstructed from today's universe.
*Falsification test:* Spot-check a sample of known historical delistings/bankruptcies against the dataset; confirm they appear in the universe up to their actual last trade date and are not silently absent.

**AV-05 — MATERIAL — `available_at` semantics ambiguous (vendor receipt vs. true public availability)**
*Problem:* The framework doesn't specify whether `available_at` is the source's publication timestamp, the exchange/regulatory disclosure timestamp, or the vendor's ingestion/batch timestamp. These can differ by hours.
*Failure example:* A vendor stamps a record with the company's original press-release timestamp, but the vendor's own feed doesn't actually deliver it to subscribers until a nightly batch hours later — the framework would treat it as available earlier than any real subscriber could have used it.
*Correction:* Define `available_at` explicitly as "the timestamp at which the specific feed to be used in live trading delivered this value," not the underlying event's origination timestamp.
*Falsification test:* For a sample of records, compare vendor-stamped `available_at` against the feed's actual batch/delivery log; flag and correct any systematic gap.

**AV-06 — MATERIAL — No mandatory latency/processing buffer**
*Problem:* `available_at <= decision_at` permits knife-edge cases where information is technically available a second before the decision — untradeable in practice.
*Correction:* Require a fixed, preregistered minimum buffer between `available_at` and `decision_at` (chosen from realistic data-processing/dissemination time, not tuned after seeing results), and use strict inequality, not `<=`.
*Falsification test:* Vary the buffer within a small, preregistered a priori range and confirm eligibility counts and results are not being cherry-picked toward one buffer value.

**AV-07 — MATERIAL — Timestamp precision / date-only data path underspecified**
*Problem:* No stated convention for coarse (date-only) timestamps — treating them as "available at midnight" versus "available at next session open" changes eligibility materially and is currently a hidden choice.
*Correction:* Default coarse timestamps to the *conservative* end (next tradable session), and separately track/report what fraction of the ledger relies on coarse timestamps for sensitivity purposes.
*Falsification test:* Confirm coverage report of date-only vs. timestamped records; re-run with the conservative convention and confirm no material praise-worthy result depends on the permissive alternative.

**AV-08 — MATERIAL — Identifier continuity (ticker reuse / changes) not addressed**
*Problem:* Joining on raw ticker strings across history risks attaching one company's later data to a different, earlier company that once used the same ticker.
*Correction:* Require a permanent identifier (CIK, FIGI, or equivalent) for all joins; ticker used only as a display field.
*Falsification test:* Construct a synthetic ticker-reuse case in the harness and confirm the framework does not cross-contaminate the two entities' histories.

**AV-09 — MATERIAL — Sector-mapping freeze not independently verifiable**
*Problem:* The "no outcome-driven remapping" rule is stated as intent but nothing enforces or proves it was actually frozen before results were seen.
*Correction:* Commit the sector mapping file with its own hash/commit before any candidate touches performance data; any later change must be a dated amendment, matching the audit's own immutability standard.
*Falsification test:* Confirm the sector-mapping commit timestamp predates any performance-inspection commit for the same family_id.

**AV-10 — MATERIAL — Baseline vs. candidate information symmetry unstated**
*Problem:* If availability filtering is applied only to the candidate and not identically to the frozen baseline portfolio, any measured "excess" could reflect an information-set asymmetry rather than genuine signal.
*Correction:* Explicitly require identical availability rules (including buffer, missing-data policy, and universe filtering) applied to both baseline and candidate in every replay.
*Falsification test:* Run the baseline through the availability gate itself; confirm it is unaffected (or that any effect is reported) rather than assumed away.

**AV-11 — MINOR — "One publication interval" undefined per feature type**
*Problem:* The delayed-feature diagnostic needs a concrete shift amount, but publication cadence varies (quarterly earnings vs. monthly macro vs. daily price-derived features).
*Correction:* Require a per-feature-type shift value specified in the preregistration, not decided ad hoc when the diagnostic is run.
*Falsification test:* N/A — documentation/hardening fix; verify the spec lists a shift value for every feature type in use.

**AV-12 — MINOR — "Inferred vs. vendor-recorded" threshold unspecified**
*Problem:* Section 7 requires removing inferred-timestamp observations, but doesn't define confidence threshold for "vendor-recorded."
*Correction:* Require an explicit vendor-provenance flag (recorded vs. inferred) at ingestion, not inferred after the fact.

---

### Leakage Paths (explicit list)

1. Unpinned `decision_at` reference point (AV-01)
2. Latest-revision substitution absent versioned storage (AV-02)
3. Missingness-correlated survivorship in cross-sectional ranking (AV-03)
4. Backfilled/purged vendor snapshots masquerading as point-in-time (AV-04)
5. `available_at` measured from origination rather than true feed-delivery time (AV-05)
6. Zero-buffer knife-edge availability (AV-06)
7. Permissive coarse-timestamp defaulting (AV-07)
8. Ticker-reuse cross-contamination (AV-08)
9. Post-hoc sector remapping without a provable freeze point (AV-09)
10. Asymmetric availability enforcement between baseline and candidate (AV-10)

### Researcher-Degrees-of-Freedom Audit

Still discretionary, and therefore changeable after results are seen unless frozen now:
- `decision_at` cadence/definition per family
- Latency buffer value
- Which vendor is authoritative on `available_at` when vendors disagree
- Coarse-timestamp handling convention
- "Inferred vs. recorded" confidence threshold
- Per-feature-type publication-interval shift for the delayed diagnostic
- Missing-data alternate-policy choices used for sensitivity (beyond the primary exclude-by-default rule)

### Minimum Required Amendments (smallest set to reach READY)

1. Define and freeze `decision_at` per family_id (AV-01)
2. Adopt an append-only, version-aware ledger with explicit value-selection rule (AV-02)
3. Add a missingness-matched placebo and per-period exclusion reporting (AV-03)
4. Document/verify PIT-snapshot provenance, not current-database reconstruction (AV-04)
5. Define `available_at` as feed-delivery time, with strict inequality plus a fixed pre-decided buffer (AV-05, AV-06)
6. Require permanent-identifier joins instead of ticker-string joins (AV-08)

Items AV-07, AV-09, AV-10, AV-11, AV-12 are worth fixing but don't block a READY call on their own if 1–6 above are addressed first — they should still be logged as open amendments, not dropped.

### Tests to Add (deterministic, synthetic)

- **Revision test:** two vendor versions of one fact → correct value selected at each `decision_at` (AV-02)
- **Impossible-future-feature test:** inject a feature mechanically defined as a future value (e.g., next-quarter return) through the full pipeline → must be flagged LATE/excluded at every historical `decision_at`. Classify this as a pipeline-correctness unit test, not an economic placebo — it shouldn't consume multiple-testing budget.
- **Ticker-reuse test:** synthetic case of two entities sharing a ticker across time → confirm no cross-contamination (AV-08)
- **Missingness-matched placebo:** random exclusion matched on liquidity/size → expectancy indistinguishable from zero (AV-03)
- **Buffer-sensitivity test:** small preregistered buffer range → no material result dependent on the most permissive buffer (AV-06)
- **`decision_at`-convention test:** two plausible conventions on identical data → identical output once one is frozen (AV-01)

---

This is the whole audit, unedited from this point forward — if performance is later inspected and any correction proves necessary, it needs to be a separately dated amendment, not a change to this document.
