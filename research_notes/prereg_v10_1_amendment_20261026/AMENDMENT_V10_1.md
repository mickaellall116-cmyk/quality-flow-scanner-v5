# Preregistration v1.0.1 — Amendment Responding to the C1 HOLD

**Amends:** Preregistration v1.0, `research_notes/prereg_v10_20261026/`,
commit `4ffb8fb` (`PREREG_V10.md` SHA-256
`29a0477a13e52ff4467193f69df7ef107048a8801f64c61f43de28d40d2850c6`).
**Trigger:** Independent review C1 — **HOLD**, GitHub Issue #1 comment
`6428626885` (ChatGPT, 2026-10-26), four bounded findings.
**Nature of this amendment:** documentation, packaging, and one mechanical
re-selection from already-captured inputs. `PREREG_V10.md` bytes are **not
changed**; this amendment supersedes the specific v1.0 statements listed in
the supersession table below, by reference. The v1.0 bootstrap seed
(`2999475941474119668`, contract `fc17041`) is therefore unchanged. No
strategy rule, threshold, δ, α, floor, or cost value is changed. No
performance test was run, no holdout data was accessed, and **no network
data call of any kind was made in producing this amendment** — all inputs
were already captured on disk (see Finding 4 for why that sentence is now
written this carefully).

The accepted B1/B2 decisions and the §9 PARTLY branch are not reopened.

---

## Finding 1 — Tier 3 evidence not reproducible from the committed package

**Reviewer:** the v1.0 package cited `sources/` (S1–S3) and
`exclusion_universes.json` but did not commit them (404 at the ref, absent
from the manifest); S4 was a live Yahoo fetch pinned by nothing, and run 2
already diverged in the eligible count (795 vs 797). The "byte-identical"
claim covered output repeatability during one live-feed episode, not a
reproducible frozen input→output derivation.

**Disposition — CLOSED, with one disclosed shortfall (→ O9):**

- S1–S3 raw inputs and `exclusion_universes.json` are committed in this
  package under `tier3_inputs/`, byte-identical to the archived originals
  (hashes in `tier3_inputs/INPUTS_AND_GAPS.md`; they match the hashes
  recorded in the v1.0 `REPRODUCIBILITY_RECORD.md`).
- S4 is frozen as `tier3_inputs/S4_FROZEN_AGGREGATES.csv` (SHA-256
  `d345fbab…`): the 12 selected symbols' ADV20 / last close / bars used,
  extracted by `build_s4_table.py` from the captured run outputs
  (fail-closed: it refuses unless runs 1/3/4 are byte-identical to the
  frozen output hash and run 2's selection matches).
- Generator **v1.2** (`generate_tier3_list_v1_2.py`, SHA-256 `d67ded42…`)
  is local-input-only: it imports no networking or market-data library,
  verifies the SHA-256 of every input against pins embedded in the script,
  and aborts (exit 2, no output written) on a missing or mismatched input.
  Both failure modes were exercised and behave as specified. Two
  consecutive v1.2 runs produced byte-identical output.
- **Shortfall, disclosed not repaired:** the v1.0/v1.1 generator persisted
  only the top-12 aggregates; the other 2,539 computed candidate
  aggregates were never written to disk and cannot be reconstructed
  offline (full statement: `tier3_inputs/INPUTS_AND_GAPS.md`). The frozen
  derivation is therefore complete down through the persisted top 12 and
  explicitly incomplete below it. No replacement fetch was made; filling
  the gap is a decision, carried as open item **O9**.

## Finding 2 — "Never in any prior study" was ticker-only; GOOG admitted

**Reviewer:** rank 1 `GOOG` is a share class of Alphabet Inc.; `GOOGL` is
in the prior QF record. Exact-symbol subtraction does not create an
independent issuer. Exclude all share classes / issuer equivalents of
UX51∪X2 via a frozen issuer identifier map; regenerate from captured
inputs only; no hand-removal, no new vendor calls.

**Disposition — CLOSED (mechanical regeneration):**

- `build_issuer_map.py` (SHA-256 `b9ae9b36…`) derives the frozen
  `ISSUER_MAP.json` (SHA-256 `3bccdbf2…`) from the archived directories by
  a documented mechanical name-matching rule (normalization algorithm in
  the builder's header): for each of the 250 prior-study symbols, all
  directory symbols whose normalized issuer name matches. Coverage: all
  225 listed prior symbols found; the 25 not found are exactly the crypto
  symbols (`…-USD`), which have no listed share classes.
- Exactly **two** prior-study issuers have multiple listed classes:
  Alphabet (`GOOG`, `GOOGL`) and Berkshire Hathaway (`BRK.A`, `BRK.B` —
  the prior symbol is `BRK-B`). No other equivalences exist in the prior
  set under the rule.
- Generator v1.2 applies the map as new **step 6b** (immediately after the
  ticker-level step 6). The regeneration, from the frozen inputs alone,
  reproduces steps 1–6 counts exactly (7,446 → 5,905 → 5,862 → 5,655),
  removes **exactly one symbol at step 6b: `GOOG`**, and proceeds with
  2,560 step-7 candidates (v1.0: 2,561).
- **Regenerated Tier 3 list (11 names)** — `tier3_list_v1_2.json`,
  SHA-256 `fbb73446…`: BE, ACN, IREN, CRDO, TWLO, AAOI, MPWR, SPOT, BABA,
  COF, BLK (former ranks 2–12, order and aggregates unchanged). `GOOG`
  fell out mechanically; **no name entered at rank 12**, because the
  rank-13 aggregate was never persisted (Finding 1 shortfall). The
  resulting prospective Stage A universe is **19 + 11 = 30 symbols** —
  still above the §6 ≥20-symbol validity floor — with the 12th slot
  carried as open item **O9** for Mike's decision (accept 11, or
  authorize a fresh S4 capture under a re-frozen rule version). No name
  was hand-removed or hand-added.

## Finding 3 — Power-report completion overstated (B9 / §15 G3)

**Reviewer:** `POWER_REPORT.md` says the H-EXIT-1/3 paired SDs are "not
on record", yet checklist B9 claims "both grades powered per endpoint",
§15 marks G3 COMPLETE, and the delivery record says "§6 power report
complete". These cannot all be true. Either keep B9/G3 OPEN and describe
the document as a partial planning grid, or complete the input under
separate authority. "This review authorizes no computation."

**Disposition — CLOSED by the first branch (wording reconciled; no
computation performed):**

- Checklist **B9 is OPEN** in `FREEZE_CHECKLIST_V10_1.md`: the §6 power
  report is published and complete for every endpoint whose inputs are on
  record, and is a **partial planning grid for H-EXIT-1 and H-EXIT-3**,
  whose paired SDs are not on record. B9 closes only with existing open
  item O4 (the variance-only paired-SD estimate, a freeze-procedure step
  that must close before any tier opens). The paired SDs were **not**
  computed for this amendment.
- **§15 gate G3 is corrected to read:** "P10 audit + P11 pins completed
  and published — COMPLETE. Power report (§6) published — INCOMPLETE for
  H-EXIT-1/3 (paired SDs outstanding); G3 as a whole remains OPEN until
  O4 closes." The same correction applies to the v1.0 summary phrasings
  "§6 power report completed" (PREREG_V10.md preamble and §15 closing
  note) and to the bridge record's "both verdict grades powered per
  endpoint" phrase: all are superseded by "published; partial planning
  grid for the 7A paired endpoints".

## Finding 4 — Provenance statement factually false

**Reviewer:** the v1.0 record says "no vendor call was made", while the
Tier 3 generation fetched Yahoo Finance daily bars for 2,561 candidates
on 2026-10-26. Amend the record; make no replacement calls.

**Disposition — CLOSED by erratum:** `ERRATUM_PROVENANCE.md` in this
package quotes the two false sentences, states what actually happened
(Yahoo Finance daily-bar fetches via yfinance for the 2,561 step-7
candidates, four runs, public web data, no licensed API key, no Twelve
Data call, no holdout-window data, aggregates only, no returns computed),
explains how the error arose (an assembly-lane sentence written
package-wide), and records the corrected provenance statement. No
replacement calls were made.

---

## Supersession table (v1.0 statements superseded by this amendment)

| # | v1.0 location | Superseded statement | Replacement (this amendment) |
|---|---|---|---|
| S-1 | `PREREG_V10.md` preamble bullet; §2 Tier 3 row; §15 item O7 | Tier 3 = 12 names incl. GOOG; list sha `9e7ae052…`; universe 19 + 12 = 31 | Tier 3 = **11 names** (GOOG excluded at step 6b); list `tier3_list_v1_2.json` sha `fbb73446…`; universe **19 + 11 = 30** unless O9 resolves otherwise |
| S-2 | `FREEZE_CHECKLIST_V10.md` row B10 | Rule/script/list evidence as generated by v1.1 | Amended by v1.0.1: generator v1.2 `d67ded42…`, issuer map `3bccdbf2…`, frozen S4 `d345fbab…`, list `fbb73446…` (checklist v1.0.1 row B10) |
| S-3 | `FREEZE_CHECKLIST_V10.md` row B9 | "Power report (§6) published — variance only, both grades powered per endpoint" — CLOSED | **OPEN** — partial planning grid for H-EXIT-1/3; closes with O4 |
| S-4 | `PREREG_V10.md` §15 gate G3; preamble; §15 closing note | "COMPLETE 2026-10-26"; "§6 power report completed" | G3 OPEN in its power limb (see Finding 3); "power report published, incomplete for H-EXIT-1/3" |
| S-5 | `PACKAGE_README.md`; `bridge_record_20261026.md` | "no vendor call was made in producing this package" | Erratum: `ERRATUM_PROVENANCE.md` (Yahoo fetches for Tier 3 liquidity, scope as stated there) |
| S-6 | `REPRODUCIBILITY_RECORD.md` verdict | "REPRODUCIBLE" (byte-identical outputs across live-fetch runs) | Qualified: output repeatability over persisted artifacts only; the input→output derivation is reproducible from committed inputs only as of v1.0.1, with the disclosed S4 shortfall (O9) |

**Preserved, per the review's instruction:** A5 (Mike, outstanding), G5
(Mike's signed freeze, after re-review), G7 per-tier GOs (none given), P5
per-fill config hash, per-tier §5 pool counts, Stage B feed-qualification
verdict and ongoing-collection rights basis, the holdout seal, and all
PAUSE / HOLD states. Nothing in this amendment authorizes a holdout
opening, a performance run, a strategy change, or a tier opening.
