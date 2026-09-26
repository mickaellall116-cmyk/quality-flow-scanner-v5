## Combined Framework Final Re-Audit (Original + Amendment 1 + Amendment 2 + Amendment 3)

**Auditor:** Claude (independent methodology auditor)
**Target:** `research_notes/decision_time_availability_audit.md` (commit `284dcc2…`) + Amendment 1 (`b02becb…`) + Amendment 2 (`89bdf7e…`) + Amendment 3 (`28ed74a…`)
**Scope:** Specification-level review only. No candidate, V5.4, or ERD performance data reviewed or referenced.

### Executive Verdict: **NOT READY**

Amendment 3 does exactly what it claims: it closes the two MATERIAL gaps (N-2, N-3) I raised against Amendment 1, and it closes them well — the missingness-placebo statistic is now fixed program-wide with no candidate-level discretion, and the revision tie-break is now a genuinely honest "mark it unusable rather than invent an order" rule instead of the lexicographic-hash workaround Amendment 2 had proposed. That workaround was a real flaw (treating an identifier as if it were temporal evidence), and Amendment 3 was right to reject it rather than patch it.

But two things remain that I'd call MATERIAL rather than cosmetic, both about the framework's own internal consistency and enforceability rather than about a specific statistical leakage path. Both are narrow and fixable with a short addendum — this is close to done, not far from it — but I was asked to try to break it again, and these are real breaks, not nitpicks.

---

### Status of N-1 through N-6

| ID | Status | Basis |
|---|---|---|
| N-1 (tie-break) | **CLOSED** — superseded by a stronger fix | Amendment 3 §2 explicitly rejects Amendment 2's lexicographic-ID tie-break ("identifiers are not temporal evidence") and replaces it with AMBIGUOUS_CONFLICT quarantine unless a *documented* vendor-native delivery-order field exists. This is methodologically better than what I originally asked for — I asked for a deterministic tie-break; they correctly recognized that inventing an order from non-temporal data (ingestion_at, hash) was itself a leakage risk, and closed it by refusing to guess instead. T2C tests all three sub-cases (conflict/no-order, exact duplicate, documented-order) correctly. |
| N-2 (missingness placebo threshold) | **CLOSED** | Amendment 3 §1 fixes the statistic program-wide (expectancy in R/trade at 50bps, no per-family choice), defines B_full/B_masked_actual precisely with no candidate signal admitted, fixes permutation count (9,999) and a deterministic seed tied to `family_id + manifest_hash` (so the seed can't be shopped without changing the frozen manifest itself), and states an exact numeric boundary (p ≤ 0.05 → FAIL) with a deterministic boundary fixture (T14). This is exactly the missing piece I flagged — a real number, frozen before results, not a qualitative "material overlap" judgment call. |
| N-3 (latency-buffer provenance parity) | **CLOSED** | Amendment 2 §2's manifest lock explicitly includes the latency buffer + evidence hash, requires the manifest to predate the first performance artifact, and T11 tests exactly the scenario I asked for (altering a frozen field, including the buffer, without a dated amendment → hard refusal). |
| N-4 (corporate-action leakage test) | **CLOSED** | Amendment 3 §3 upgrades the vague "audited" language into a precise truncate-then-append protocol with an explicit invariance criterion (features at ≤T must be bit-identical modulo a preregistered float tolerance) and explicitly bars a fully-adjusted series from driving confirmatory features if a future action would change it. |
| N-5 (consolidated preregistration-completeness check) | **CLOSED** | Amendment 2 §2 / T13 — removing each manifest field one at a time and confirming replay refuses before loading performance data is exactly a consolidated completeness gate. |
| N-6 (REVIEW resolution path) | **CLOSED** | Amendment 2 §6, reaffirmed unchanged by Amendment 3 §5: REVIEW is explicitly non-confirmatory, cannot advance a candidate or tune a replacement rule on the inspected data, and must resolve via a dated amendment + rerun to PASS/FAIL. |

### AV-03 specifically: **CLOSED**

The full chain now holds together: Amendment 1 §6 requires the accounting (universe/valid/excluded counts, matched descriptors, coverage rate); Amendment 3 §1 supplies the missing quantitative test with a fixed statistic, fixed design, and a hard numeric boundary. This is a legitimate closure of the original finding, not a reframing of it.

---

### New Findings Introduced (or newly exposed) by the Combined Framework

**N-7 — MATERIAL — READY gate references a stale test-suite list.** Amendment 2 §7 states the framework "may be called READY only after... applicable T1–T13 tests pass." Amendment 3 adds T14 and T2C, and materially rewrites the expected behavior of T12 (the truncate-and-append protocol is stricter than what T12 originally implied under Amendment 2). Nothing in Amendment 3 updates §7's gate language to say the *current* test suite (including its own additions/revisions) is required. As written today, a literal reading of §7 could be satisfied by a family that passes the original T1–T13 while never running T14 or T2C — precisely the "gap between what was fixed and what's actually checked" failure mode this whole document exists to prevent.
*Correction:* A one-line addendum to §7: "READY requires passing the version-controlled current test suite as of the framework's latest frozen amendment (currently T1–T14 plus T2C, with T12 evaluated under Amendment 3 §3's criterion), not a fixed historical list."
*Test:* None needed beyond the correction itself — this is a specification-text fix, not a new runtime test.

**N-8 — MATERIAL — The provenance-lock mechanism assumes an immutable commit history, and nothing in the framework says so or protects it.** Every closure above — N-3, N-5, N-6, the manifest lock itself — ultimately rests on "committed and hashed before the first performance artifact" being a fact that can't be altered after the fact. That's only true if the underlying git history itself can't be rewritten (force-push, history rebase, branch deletion/recreation). Nothing in Amendments 1–3 requires branch protection, disallows force-pushes, requires signed commits, or specifies any independent anchor for the manifest hash's timestamp. This isn't a hypothetical: it's the single point every other control in this document depends on, and it's currently an unstated assumption rather than an enforced control — which matters more here than in most codebases, precisely because the stated purpose of the whole exercise is to prevent exactly this kind of after-the-fact rule selection.
*Correction:* A short addition (Amendment 4 or an addendum to Amendment 2 §2) requiring: (a) branch protection with force-push disabled on the repository/branch holding frozen manifests, and (b) either signed commits or an independent timestamp anchor (e.g., hashing the manifest into a third-party timestamping service or even just a dated message in an external channel like the research-thread mailbox) so that "committed before inspection" is independently verifiable, not merely asserted by the same party who could rewrite it.
*Test:* T15 — attempt to alter a frozen manifest's commit history (rewrite/force-push changing the apparent commit date of an already-referenced hash) and confirm the change is either technically prevented or independently detectable via the external anchor.

**N-9 — MINOR — Floating-point tolerance (Amendment 3 §3) isn't itself listed as a required manifest field.** An overly generous tolerance could quietly mask a real backward-adjustment leak. *Correction:* add `corporate_action_float_tolerance` to Amendment 2 §2's enumerated manifest field list.

**N-10 — MINOR — "Documented vendor-native delivery sequence" (Amendment 3 §2) and "sparse-stratum fallback design" (Amendment 3 §1) have no stated minimum evidentiary bar.** Both are correctly required to be frozen in the manifest before use, so this isn't exploitable post-hoc, but the framework doesn't say what counts as "documented" — a low bar here would quietly reintroduce N-1's original risk through the back door. *Correction:* one sentence defining minimum evidence (e.g., a vendor specification document or API field explicitly described as delivery/sequence order — not inferred from ordering of received rows).

---

### Remaining Researcher Degrees of Freedom

- Per-family matching-strata bucket boundaries and sparse-stratum fallback design (properly frozen pre-performance, but the *content* of that design is still a human choice each time — irreducible, not a flaw)
- What counts as "documented vendor-native delivery sequence" evidence (N-10)
- The floating-point tolerance magnitude (N-9)
- **A structural, not statistical, degree of freedom worth naming plainly:** Amendment 3 §1 itself states that if a REVIEW is triggered by insufficient valid placebo masks, the matching design "may not be relaxed... except by dated amendment, and the inspected result may not be used to choose a favorable replacement." That's the right rule to write down, but no document, test, or hash-lock can mechanically verify that a human choosing a *replacement* design afterward wasn't unconsciously influenced by having seen the failed run. This is an inherent limit of any preregistration scheme, not a defect specific to this one — it means ongoing adversarial review (this audit role, and ChatGPT's) remains load-bearing indefinitely, even after the framework is called READY. Worth stating explicitly rather than leaving implicit.

---

### Minimum Additional Amendment Required

A short Amendment 4 covering only:
1. Update the READY gate (Amendment 2 §7) to reference the current, version-controlled test suite rather than a fixed "T1–T13" list (N-7).
2. Require a commit-integrity control (branch protection / no force-push, plus signed commits or an independent timestamp anchor) for the repository holding frozen manifests, with a corresponding T15 (N-8).
3. Add the corporate-action float tolerance to the required manifest field list (N-9).
4. Define a minimum evidentiary bar for "documented vendor-native delivery sequence" (N-10).

None of these require touching the statistical design that Amendment 3 already fixed — that part is sound. This is process/governance closure, not another round of methodology rework, and it's genuinely likely to be the last specification-level amendment needed if these four items are addressed.

---

This is the complete re-audit, unedited — ready to return to Mike/ChatGPT for adjudication and archival.