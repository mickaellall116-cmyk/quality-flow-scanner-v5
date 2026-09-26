## Amendment 1 — Independent Adversarial Re-Audit

**Auditor:** Claude (independent methodology auditor)
**Target:** `research_notes/decision_time_availability_audit_amendment_1.md`, commit `b02becba34fd3b507eb1ecec995eabea6b466c3b`
**Scope:** Amendment 1 text only. No candidate, V5.4, or ERD performance data reviewed or referenced.

### 1. Executive Verdict: **NOT READY**

Amendment 1 substantially closes the framework. Ten of twelve original findings are fully resolved with concrete mechanisms and matching deterministic tests — a genuine, well-specified improvement, not a cosmetic patch. But **one original finding (AV-03) remains only partially closed**, and **the amendment itself introduces one new MATERIAL gap** (asymmetric provenance enforcement between the sector-map freeze and the latency-buffer freeze). Both are narrow, nameable, and fixable without redesigning the framework — this is close to READY, not far from it — but "close" is not "closed."

### 2. Status of AV-01 through AV-12

| ID | Status | Basis |
|---|---|---|
| AV-01 | **CLOSED** | §1 requires a single frozen `decision_at` generator per family, with cadence, UTC+source-timezone rule, explicit instant, calendar/library version; runtime override forbidden; T1 tests hard refusal. |
| AV-02 | **CLOSED*** | §3 append-only ledger, permanent-ID keying, explicit selection rule, T2 test. *One residual gap: no tie-break rule when two versions share an identical `available_at` (see new finding N-1). |
| AV-03 | **PARTIALLY CLOSED** | Accounting requirements (universe/valid/excluded counts, matched descriptors, coverage rate) are well specified. The pass/fail statistical criterion for the placebo comparison is not (see §5 below and new finding N-2). |
| AV-04 | **CLOSED*** | §5 gives three acceptable provenance paths, requires delisting/bankruptcy/ticker-change spot-checks, T7 test. *Sample size/stratification for the provenance spot-check is unspecified — minor, not blocking. |
| AV-05 | **CLOSED** | §2 defines `available_at` as feed-delivery time, `event_at` stored separately and explicitly not a substitute; T4 test. |
| AV-06 | **CLOSED*** | §2 buffer frozen from operational evidence, no result-driven tuning, sensitivity range can't replace primary. *Enforcement mechanism is weaker than other sections' — see new finding N-3. |
| AV-07 | **CLOSED** | §2 coarse-timestamp handling: ineligible intraday, conservative default (next tradable session) absent documented semantics; T5 test. |
| AV-08 | **CLOSED*** | §4 permanent-ID joins, effective-dated entity map, frozen price-adjustment semantics with raw+adjusted provenance retained, T6 test. *No dedicated deterministic test for corporate-action adjustment leakage specifically (T6 only covers ticker reuse) — see new finding N-4. |
| AV-09 | **CLOSED** | §8 mapping committed+hashed before inspection, dated amendments retain prior hashes, T10 test. |
| AV-10 | **CLOSED** | §7 identical PIT master/calendar/execution/cost/availability rules for baseline and candidate, explicit reporting of frozen baseline / candidate overlay / combined competition, T8 test. |
| AV-11 | **CLOSED** | §2: delayed-diagnostic shift frozen per feature type before performance inspection. |
| AV-12 | **CLOSED** | §2: categorical `availability_provenance` (vendor_recorded / feed_log / inferred) replaces the fuzzy "confidence threshold" — cleaner than what I originally asked for. |

**Net: 10 CLOSED, 1 CLOSED-with-minor-gap-noted-as-such counted generously, 1 PARTIALLY CLOSED.** For a strict count: 10 fully closed, 1 partially closed (AV-03), 0 fully open, with several "closed-but-flagged" minor residuals folded into the new-findings list below rather than reopening the original numbering.

### 3. New Findings Introduced by Amendment 1

**N-1 — MINOR — No tie-break rule for identical `available_at` timestamps.** §3's selection rule ("choose the latest version satisfying...") is ambiguous when two vendor versions share the same `available_at` (a realistic case — duplicate corrections issued in the same batch). *Correction:* tie-break deterministically on `ingestion_at`, then `vendor_version_id`, in that order, and add this to the T2 test as a third sub-case.

**N-2 — MATERIAL — Missingness-placebo decision rule is qualitative, not preregistered as a quantitative threshold.** §6 replaces "must equal zero" with "compare against a preregistered matched-placebo distribution," which is a methodologically sound upgrade in principle — a distributional/permutation comparison is the right shape of test, consistent with how other placebos in this program are already framed. But the actual accept/reject rule — *"material overlap or placebo effects comparable to the candidate's claimed marginal value trigger REVIEW/FAIL depending on the candidate's frozen gate"* — never states what "material overlap" or "comparable" means numerically (a percentile cutoff, an effect-size ratio, a specific overlap statistic). As written, this is exactly the kind of post-hoc, arguable judgment call the rest of the framework was built to eliminate, and tellingly it's absent from §11's own list of things that must be frozen. *Correction:* require each candidate to preregister an explicit numeric rule before results are inspected — e.g., "the real effect must fall below the Nth percentile of the placebo distribution" or "effect-size ratio (real ÷ placebo) must not exceed X" — and add this item to §11's frozen list. *Test:* construct a synthetic case where the real and placebo effects are deliberately close; confirm the preregistered numeric rule (not a discretionary call) produces the FAIL/REVIEW outcome.

**N-3 — MATERIAL — Latency-buffer freeze lacks the provenance-enforcement mechanism given to the sector map.** §8 requires the sector mapping to be committed and hashed *before* any diagnostic result is inspected, with T10 verifying that a post-hoc change without a dated amendment fails. §2's latency buffer has the identical need (it must be frozen "from operational evidence, not performance" before results) but has no equivalent commit-hash-before-inspection check or test. As written, buffer-freezing is an unverified promise rather than an audited control — asymmetric with how seriously the framework treats an analogous risk elsewhere. *Correction:* extend the T10-style provenance check to the latency buffer (and ideally to every item in §11's list uniformly, via one consolidated test rather than one-off per section). *Test:* T11 — attempt to alter a feed's latency buffer after a performance artifact exists for that family without a dated amendment; expect the same provenance-check failure as T10.

**N-4 — MINOR — No deterministic test for corporate-action price-adjustment leakage.** §4 requires adjusted price series to be "documented and audited for whether the adjustment changes information available at historical decision time," but unlike every other requirement in the amendment, this one has no corresponding T-test. Backward-adjusted prices are a classic, easy-to-miss leakage vector (a pre-split price series adjusted using a split that hadn't happened yet encodes future information into the historical value). *Correction:* add T12 — construct a synthetic security with a known future split; confirm the adjusted price series used at a `decision_at` before the split date is identical whether or not the future split has occurred in the underlying data, i.e., adjustment must not be computed backward using knowledge not yet in effect.

**N-5 — MINOR — No consolidated preregistration-completeness check.** §11 lists ten items that must be frozen before performance inspection, but nothing verifies as a single gate that all ten are actually present and hash-committed for a given family before any replay runs — each section enforces its own piece (T1, T10) but there's no single "was §11 satisfied in full" test. *Correction:* add T13 — a preregistration-completeness check that fails closed if any of the ten §11 items is missing a frozen value/hash for the family under test.

**N-6 — MINOR — REVIEW status has no defined resolution path.** §10 introduces a REVIEW bucket ("timing valid but provenance/inferred-timestamps/missingness mechanics materially threaten interpretation") without specifying what must happen next — whether REVIEW can be treated as good enough to proceed informally, or whether it must be resolved back to PASS/FAIL through the same frozen-before-inspection discipline as everything else. Left open, REVIEW could become an informal bypass around the FAIL gate. *Correction:* state explicitly that a REVIEW-status candidate cannot be used for confirmatory interpretation or advanced toward deployment discussion until the specific triggering issue is corrected and the candidate is re-run to a clean PASS or FAIL — REVIEW is a diagnostic state, not a usable outcome.

### 4. Remaining Researcher Degrees of Freedom

- The exact quantitative threshold for the missingness-placebo decision rule (N-2) — currently absent even from §11's own list of things to freeze
- The specific operational evidence used to justify each feature's latency buffer — self-attested, not independently auditable in the same way the sector map is (N-3)
- Sample size/stratification for the PIT-provenance delisting/bankruptcy spot-check (AV-04 residual)
- Tie-break rule for simultaneous `available_at` timestamps (N-1)
- Whether/how a REVIEW-status finding gets formally resolved before any candidate can advance (N-6)

### 5. Assessment of the Revised Missingness-Placebo Methodology

**The methodological shift itself is acceptable — arguably an improvement.** Requiring placebo expectancy to equal exactly zero is a fragile point-null test in finite samples; it can fail from ordinary sampling noise even when coverage mechanics are genuinely harmless, or pass by chance even when they're not. Comparing the real effect's location within a preregistered, matched-placebo distribution is the more standard and more robust design, and it's consistent with how other adversarial controls in this program are already built (permutation/shuffled-label placebos, block bootstrap).

**The problem is not the shift — it's that the amendment doesn't finish the job.** It swaps a precise (if fragile) rule for an imprecise (if more robust) one, without supplying the missing precision: no percentile cutoff, no effect-size ratio ceiling, no stated statistic. That gap is exactly the shape of researcher discretion this framework exists to remove, and it should be closed the same way every other placebo/threshold in this document was closed — with a specific number, frozen before any results are inspected, and listed explicitly in §11. Until that number exists, this section is a real, not cosmetic, gap (N-2, MATERIAL).

### 6. Minimum Additional Amendments/Tests Required

1. **N-2 (MATERIAL):** Add an explicit, preregistered quantitative decision rule for the missingness-placebo comparison (percentile cutoff or effect-size ratio), and add it to §11's frozen-items list. Add a synthetic near-boundary test case.
2. **N-3 (MATERIAL):** Extend commit-hash-before-inspection provenance enforcement (as already required for the sector map) to the latency buffer, with a T11-equivalent test.
3. **N-1 (MINOR):** Add a deterministic tie-break rule for identical `available_at` values; extend T2 with a tie-break sub-case.
4. **N-4 (MINOR):** Add T12 — corporate-action price-adjustment leakage test.
5. **N-5 (MINOR):** Add T13 — consolidated §11 preregistration-completeness check.
6. **N-6 (MINOR):** State explicitly that REVIEW is not a usable outcome for confirmatory interpretation and must be resolved to PASS/FAIL before a candidate proceeds.

Items 1–2 are what keep the verdict at NOT READY; items 3–6 should be logged as required but don't independently block a READY call once 1–2 are addressed. Amendment 1 is well-constructed and closes the large majority of what was raised — the remaining gaps are specific and small, not structural.

---

This is the full re-audit, unedited — ready to return to ChatGPT for adjudication and archival as-is.