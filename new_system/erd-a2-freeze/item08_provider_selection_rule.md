# Item 8 — Provider-selection rule (frozen, §2.2 quoted verbatim from Amendment 2 rev 4)

**2.2 Pass/fail first.** A candidate is selectable ONLY if it passes EVERY
§1.6 threshold (including the zero-tolerance categories). Among passing
candidates, preference order: (i) reproducibility/PIT provenance strength
(versioned snapshots, documented revision semantics, stable field
definitions); (ii) timing-integrity score; (iii) coverage. Deterministic
tie-breaks frozen ex ante: provenance strength, then timing-integrity
score, then coverage, then lowest revision-incidence in the transition
sample, then alphabetical by provider name. Tiny 49/50 vs 50/50 sample
differences do NOT decide on their own — this is not a beauty contest.

**2.3 Decision rule.** Every candidate gets a full §1 gate report on the SAME
frozen 50-event sample. If NO candidate passes all hard gates, ERD halts — a
failing provider is never adopted because downstream returns would look good.

**2.4 Search ledger.** `new_system/TEST_LEDGER.md` retains EVERY provider
considered, rejected, unavailable, or partially audited, with reason and
date, plus all candidate gate scores and the selection decision — recorded
BEFORE any performance work. The full search path is preserved; no cycling
through vendors until one happens to pass.

**2.5 Current judgments (non-binding; selection by gate score only):**
Benzinga MAYBE — primary candidate for feasibility validation; EODHD MAYBE
backup/control; FMP FAIL as current primary exact-time source; Alpha Vantage
FAIL as primary event-time source, useful survivorship control. Changeable
only via new amendment.

---
