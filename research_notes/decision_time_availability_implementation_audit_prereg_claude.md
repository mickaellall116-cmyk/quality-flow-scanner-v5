## Decision-Time Availability Framework — Implementation Audit Preparation

**Status:** Specification READY (attestation `7da25c5…`, final spec audit `5c84caf…`). This document is pre-registered *before* seeing Muse's code or any candidate performance, so it can't be quietly adjusted once implementation details are known.

---

### 1. Implementation-Audit Checklist

**A. Decision clock (AV-01 / §1 Amendment 1)**
- [ ] `decision_at` generator is derived solely from the frozen family manifest; no code path accepts a caller-supplied override
- [ ] Attempt to inject an alternate `decision_at` at runtime → confirm hard refusal (T1), not a silent fallback to a default
- [ ] Cadence, session calendar, and calendar/library version actually match what's frozen in the manifest — not hardcoded separately in the replay engine

**B. Availability semantics & latency (§2 Amendment 1, §2 Amendment 2, §2 Amendment 4)**
- [ ] `available_at` is read from feed-delivery timestamp field, never derived from `event_at` as a substitute
- [ ] Eligibility check is strict `available_at + latency_buffer < decision_at`, not `<=` (off-by-one on the boundary is a classic silent leak)
- [ ] Latency buffer value is read from the frozen, anchored manifest field — not a constant embedded elsewhere in code that could diverge from what's anchored
- [ ] Coarse/date-only timestamps are rejected for intraday use at the type level, not just by convention
- [ ] `availability_provenance` field (`vendor_recorded`/`feed_log`/`inferred`) actually gates exclusion of `inferred` rows from primary replay — confirm this isn't a field that's stored but never checked

**C. Revision/restatement ledger (§3 Amendment 1, §2 Amendment 3)**
- [ ] Storage is genuinely append-only (no UPDATE/DELETE path exists on historical fact rows at the schema/permissions level, not just "we don't call it")
- [ ] Version-selection query picks latest *eligible* version — confirm no code path queries "current value" and back-fills
- [ ] Same-`available_at` conflicting values → correctly produce `AMBIGUOUS_CONFLICT`, not silently pick one
- [ ] Exact-duplicate same-timestamp values collapse without changing eligibility (distinguish "duplicate" detection logic from "conflict" logic — these must not share a code path that defaults toward optimistic collapsing)

**D. Vendor-native delivery sequence (§4 Amendment 4)**
- [ ] The accepted-evidence check is a real gate against a frozen evidence artifact reference in the manifest, not a boolean flag a developer can set from memory
- [ ] Rejected evidence types (lexicographic ID order, row order, ingestion order, inferred monotonicity) are not reachable as an implicit fallback when documented evidence is absent

**E. Point-in-time universe & identity (§4/§5 Amendment 1, §5 Amendment 2)**
- [ ] All joins use permanent identifier; grep for any remaining ticker-string joins in the actual codebase, including in test fixtures/helpers
- [ ] Delisting/bankruptcy/ticker-change sample audit is wired into a real pre-performance check, not a one-time manual note
- [ ] Effective-dated identifier map is actually consulted at `decision_at`, not resolved against present-day mapping

**F. Corporate actions (§4 Amendment 1, §3 Amendment 3, §3 Amendment 4)**
- [ ] Truncate-at-T / append-future-action / recompute test is implemented as stated — confirm the test harness genuinely withholds the future action from the truncated dataset rather than just relabeling it
- [ ] `corporate_action_float_tolerance` is read from manifest, bitwise-equality is the actual default in code (not a nonzero epsilon quietly hardcoded "to avoid noisy test failures")

**G. Missingness placebo (§6 Amendment 1, §1 Amendment 3)**
- [ ] Statistic is fixed program-wide (expectancy in R/trade at 50bps) — confirm no per-family override path exists in code
- [ ] Seed derivation matches `SHA256("QF-MISSINGNESS-" + family_id + manifest_hash)` exactly — verify byte-for-byte, since a subtly different serialization of `family_id`/`manifest_hash` silently produces a different (and effectively choosable) seed
- [ ] Exactly 9,999 masks generated — off-by-one here changes the p-value denominator and boundary behavior
- [ ] `B_masked_actual` genuinely receives zero candidate signal — audit for any code path where candidate ranking accidentally leaks into the "baseline-only" masked replay
- [ ] T14 boundary fixture: p=0.05 → FAIL, p=0.0501 → PASS this diagnostic only, confirmed against actual computed p, not a rounded/truncated version of p

**H. Baseline/candidate symmetry (§7 Amendment 1)**
- [ ] Same PIT master, calendar, execution model, costs, and availability rules genuinely shared via one code path for both baseline and candidate replay — not two parallel implementations that are supposed to agree
- [ ] External/revisable baseline inputs are subject to the same availability gate as candidate inputs (T8) — check for a shortcut where baseline inputs skip the gate "because they're just baseline"

**I. Sector mapping freeze (§8 Amendment 1)**
- [ ] Mapping artifact hash-checked against manifest before any diagnostic runs
- [ ] T10: post-hoc mapping change without dated amendment → fails

**J. Sparse-stratum fallback (§4 Amendment 4)**
- [ ] Minimum-per-stratum, merge order, max merge breadth, sector-drop-before-size/liquidity order all read from frozen manifest fields, not computed adaptively at runtime based on what the actual data looks like that day

**K. Manifest completeness & immutability (§2 Amendment 2, §2/§6 Amendment 4)**
- [ ] T13: removing any required manifest field individually → replay refuses before loading performance data (test each field separately, not just "manifest missing entirely")
- [ ] Manifest hash is computed over canonical serialization (confirm whitespace/key-ordering/encoding differences don't produce different hashes for logically identical manifests — or conversely, don't produce identical hashes for logically different ones)

**L. Dual-anchor provenance (Amendment 5)**
- [ ] Both Anchor A (GitHub) and Anchor B (external email) are checked as independently mandatory — not "either/or" logic anywhere in validation code
- [ ] Anchor B's content is verified to reference Anchor A's actual comment ID, not just "an" ID
- [ ] Cross-anchor field-by-field equality check (family_id, commit SHA, manifest SHA256) — not just "both anchors exist"
- [ ] Timestamp-ordering check: both anchors must predate first performance artifact — confirm this compares actual server timestamps, not client-supplied/local timestamps
- [ ] Replay artifact embeds all five required provenance fields (§2 Amendment 5) and validation actually reads them back rather than trusting an internal in-memory flag set once at the start of a run

**M. T15/T16 tamper detection**
- [ ] T15 and each T16 sub-case (a–f) implemented as literal simulations against real repository/anchor state — not simulated by mocking the validator's own comparison function (this is exactly focus area #2 below)
- [ ] T16d specifically: confirm a later-created A2/B2 cannot be paired with the *original* performance artifact to retroactively validate it

**N. Fail-closed / gating order**
- [ ] Trace the actual call order: does provenance/manifest/anchor validation execute and can it block *before* any performance metric is computed or rendered, or could a UI/report path exist that displays partial results before validation completes?
- [ ] Every validation failure path returns FAIL (or REVIEW where specified) — audit for any `except: pass` / default-true / soft-warning pattern that could let a failed check through silently
- [ ] REVIEW status cannot be programmatically escalated to PASS anywhere except through the dated-amendment-and-rerun path (Amendment 2 §6 / Amendment 4 §5)

---

### 2. Highest-Risk Implementation Failure Modes to Specifically Attempt to Trigger

1. **Tests that assert against the implementation's own logic rather than an independently derived expected value.** E.g., a revision-selection test that computes "expected" by calling the same version-selection function under test, so any bug in that function is invisible to its own test. For every deterministic test (T1–T16, T2C), I will independently hand-compute the expected output from the raw fixture data before running the test, and compare against both the fixture's stated expectation and the actual code output — a mismatch between my independent computation and the fixture's "expected" value is itself a finding, even if code and fixture agree with each other.
2. **Mocked anchors in T15/T16.** If Muse's tamper tests mock the GitHub/email API responses rather than exercising real (or realistically faithful sandbox) anchor state, the tests can pass while the actual validator never really re-derives content-hash-vs-anchor-vs-repository-state end to end. I will specifically ask whether T15/T16 run against live or realistic sandboxed services versus stubbed responses that assume the comparison logic is already correct.
3. **Off-by-one at every strict-inequality boundary** (`available_at + latency_buffer < decision_at`; the p ≤ 0.05 FAIL / p = 0.0501 PASS boundary; exact-timestamp tie handling). I will construct boundary fixtures independently, not reuse Muse's, since boundary bugs are exactly the kind that identical fixtures on both sides would fail to catch.
4. **Silent optimistic defaults on missing/ambiguous data** — e.g., a code path where `AMBIGUOUS_CONFLICT` or `inferred` provenance quietly resolves to "use it anyway" under some untested branch (a common failure mode: the exclusion logic is correct in the primary path but a secondary code path — caching, a batch job, a re-run script — reads the raw table directly and bypasses the gate entirely).
5. **Baseline/candidate code divergence.** Two "identical" replay engines are a classic place for silent asymmetry to creep in over time (a bug fix applied to one path and not the other). I will look for whether baseline and candidate literally share one code path or merely two paths that are supposed to be kept in sync.
6. **Seed/manifest-hash canonicalization mismatch** — if manifest serialization isn't strictly canonical (e.g., JSON key ordering, float formatting), the same logical manifest could hash differently on different runs, silently breaking the deterministic seed and the anchor-matching check simultaneously.
7. **Performance-loading race with validation.** I will look specifically for any code path — a notebook, a dashboard, a debug script — that can load or display candidate results before the full provenance/manifest/test-suite gate has actually executed, since a governance framework this careful in its rules is only as strong as its weakest access path.

---

### 3. Artifacts Required from Muse Before IMPLEMENTATION PASS/FAIL

- Full source for: decision-clock generator, availability/eligibility gate, revision-ledger storage and selection logic, missingness-placebo engine (mask generation + statistic + seed derivation), baseline/candidate replay engine, manifest schema + hashing routine, dual-anchor validator, and all T1–T16/T2C test implementations
- The actual family manifest schema and one populated (non-performance) example manifest
- Confirmation of test execution environment for T15/T16: live sandbox vs. mocked services, with the exact mocking boundary specified if mocks are used
- A call-graph or equivalent trace showing the order of operations from "replay requested" to "performance displayed," so I can independently confirm provenance validation is unconditionally upstream of any performance computation
- Test coverage report or equivalent showing which frozen rules have a corresponding automated test versus which are only enforced by code review/convention
- Any deviation log: places where Muse's implementation needed to interpret an underspecified detail of the frozen spec, however minor

I will independently re-derive expected outputs for every deterministic test from raw fixture data rather than accepting Muse's stated "expected" values, per failure mode #1 above.

---

### 4. Items That Cannot Be Audited Without Seeing Performance

- Whether the missingness placebo's *actual* p-value for a real candidate falls near the 0.05 boundary in a way that would make implementation rounding/precision bugs practically consequential (the boundary logic itself can and will be tested with synthetic fixtures now; only a real candidate's proximity to that boundary determines whether a latent precision bug would ever matter)
- Whether real-world vendor data actually produces enough valid masked decisions (≥100) and adequately matched controls (≤10% inadequate) to avoid landing in REVIEW by default — this is a data-coverage question, not a spec or code question, and can't be assessed on synthetic fixtures alone
- Whether the sparse-stratum fallback is invoked at all in practice, and how often, for any specific candidate's real universe

I'm flagging these now, before any performance exists, precisely so they can't later be quietly folded into a "the code technically passed" conclusion without being named as data-dependent unknowns — but I am not requesting or inspecting any performance data at this stage.