# Validation Contract — Governance Closure + Amendment v1

**Task:** `QF-VALIDATION-GOVERNANCE-CLOSURE-20261018-24 r1`
**Spec:** GitHub Issue #1 comment `6254403898` (verdict `SOURCE_ADOPTION_PASS__EXECUTABLE_BYTES_COMPLETE__GOVERNANCE_FIELDS_HOLD`, dispatching -24)
**Predecessor records:** -21 consolidation (memo sha256 `92ea4a999479b73a…`, matrix sha256 `d913ce6a95d6fffa…`, commit `0704484`) · -22 recovery (commit `8e0a187`) · -23 adoption (memo sha256 `cfc1102e9e65f914…`, adoption manifest sha256 `51144cd2c960dcda…`, content commit `a81e1c3`, merge `b5af7da`; review comment `6253626132`)
**Mode:** OFFLINE, metadata/governance records only. One pass, no repair/rerun.
**Date:** 2026-10-18

---

## 1. Legacy holdout exact-date search — outcome: RECOVERED BY RECORD (not LOST)

**Window re-pinned: 2023-10-19 → 2024-09-15 · 51 UX51 symbols · 4H bars · ~11 months.**

Terrain searched (records ABOUT the window only): committed text (`*.md`/`*.txt`) across all branches and refs, git commit messages, preregistrations, readiness packages, proposals, and governance documents. **No holdout data file was opened, listed, hashed, enumerated, or inferred from — at any point.**

Findings:

1. **Primary contemporaneous record** — `research_notes/top_stocks_universe_proposal_v3_20261004.md`, sha256 `f88c2b9e23fea266dd2771ed6a13b49aad22df8aa7f83b2e5b4b43389d503f6b`, commit `f054ff73631307103d64e86d73937c2b400c8dcc` (2026-10-03). Written expressly as a record reconciliation, it states the exact window three times (lines 11, 35, 141): *"The sealed 11-month 4H holdout is 2023-10-19 → 2024-09-15, 51 UX51 symbols"*, citing `forward_test/holdout_protocol_v2_20261003.md` and the 2026-10-03 inventory.
2. **Independent corroboration** — `research_notes/top_stocks_readiness_package_20261004.md`, sha256 `5c0268bcd53617958d602724d6ae256aa32bbd959e6768c86ddb81ed8f813698`, commit `2e37099` (2026-10-03): *"the sealed 4H holdout (Oct 2023–Sep 2024)"*; the v2 addendum independently records the window *"ends Sep 2024"*; the same package's data window begins 2023-10-19.

Acceptance test (per spec §1): **met under both prongs** — (a) two independent immutable references (items 1 and 2 above), and (b) one contemporaneous immutable governance record created before any associated result: the v3 reconciliation is dated the same day as the protocol it cites (2026-10-03), and **no holdout result has ever been computed** — every record states the holdout stays sealed / UNTOUCHED / PARK RULE non-spend. There is no associated result for the record to precede; it precedes all possible ones.

**Disclosed caveat (provenance honesty):** the named primary source, `forward_test/holdout_protocol_v2_20261003.md`, is **not committed in this repository** — no tree on any branch (`main`, `origin/main`, `recovery-4h-20261004`) contains any file matching `*holdout*`. The exact-date pin therefore rests on the contemporaneous v3 reconciliation record plus the readiness-package corroboration, not on the protocol's own bytes. This is the same failure class as -21/-22 (a search-scope miss: the -21 consolidation searched only the committed main tree's readiness records and did not surface the v3 proposal's reconciliation statements). The "sealed" property itself is a governance assertion carried by these records; this task performed no content access, so nothing here verifies contents — by design, since verification by inspection would itself breach the seal protocol.

**Classification:** the legacy dates are **NOT** `LEGACY_HOLDOUT_DATES_LOST`. The spec §3 contingency is therefore **not invoked**: the "sealed holdout" label is **retained**, the window is re-pinned by citation above, and no replacement temporal slice is frozen by this amendment. Any future use of this holdout still requires its own separate authorization (unchanged governance).

---

## 2. AMENDMENT v1 — Split / corporate-action handling (NEWLY FROZEN)

**Status of the original:** the operative split-exclusion protocol referenced by the preregistrations is **LOST** (failure-memory key `SPLIT_EXCLUSION_PROTOCOL_DEFINITION_MISSING`, established by -22: prose references everywhere, operative windows/thresholds/lists nowhere). **This amendment REPLACES the lost protocol with a newly frozen one. It is not, and does not claim to be, the recovered original.** No clause below is derived from, or tuned on, any result or dataset; the exclusion window is a governance constant fixed here, before any data pull or performance computation, and is provider-neutral (it binds any future dataset, whatever its vendor).

**Frozen clauses (operative from this amendment, before any data/performance):**

- **S1 — Required split metadata.** A dataset is eligible only if it carries an explicit per-symbol corporate-action/split table and a documented adjustment convention. No table or no documented convention ⇒ the symbol is `DATA_UNQUALIFIED`.
- **S2 — Exclusion window.** For every split with effective session **D**, exclude all bars **and** all candidate entries from the prior full regular session through the next full regular session (**D-1 … D+1**, XNYS sessions).
- **S3 — Recompute after exclusion.** All indicators and derived features are recomputed after exclusion. **No imputation across the removed window** — no forward/back-fill, interpolation, or synthetic bars spanning D-1 … D+1.
- **S4 — Adjustment-convention verification.** The documented adjustment convention must be verified with deterministic pre/post price-ratio checks and OHLC-consistency checks across each split. A failed check ⇒ that symbol is `DATA_UNQUALIFIED`.
- **S5 — Fail closed, no exceptions.** Any missing or ambiguous split metadata, or any failed adjustment check, makes that symbol `DATA_UNQUALIFIED`. **No manual symbol exceptions.**

---

## 3. Matrix delta (full updated matrix in `validation_governance_closure_20261018_24/READINESS_MATRIX.json`)

| Field | Was (-21) | Now | Provenance |
|---|---|---|---|
| 1.2 Benchmark symbol identity (SPY) | PROSE_ONLY | **PASS** | RECOVERED — adopted byte-pinned code hardcodes SPY (`ETF_SYMS`, RS vs SPY/QQQ) in `pine_signal_quality.py` `b1b39ee8…` (-23 adoption) |
| 1.3 Benchmark loader bytes | MISSING | **PASS** | RECOVERED — exact bytes (-22), adopted (-23) |
| 1.4 Frozen sector mapping (51) | MISSING | **PASS** | RECOVERED — canonical digest `9bab23b7…` match (-22), adopted (-23) |
| 2.4 RS feature computation bytes | MISSING | **PASS** | RECOVERED — exact bytes (-22), adopted (-23) |
| 3.6 Split / corporate-action handling | PROSE_ONLY | **PASS** | **NEWLY_FROZEN** — Amendment v1 §2 above (original protocol LOST; replaced, not recovered) |
| 4.3 Sealed holdout designation | PROSE_ONLY | **PASS** | RECOVERED-BY-RECORD — designation + window pinned by the contemporaneous record set (§1) |
| 4.4 Sealed holdout exact window | MISSING | **PASS** | RECOVERED-BY-RECORD — 2023-10-19 → 2024-09-15 (§1; primary protocol bytes absent from repo — disclosed) |

All other 20 fields are unchanged from -21 (18 PASS carried; 4.2 and 4.5 remain PROSE_ONLY — see §4).

**New totals: 25 PASS / 2 PROSE_ONLY / 0 MISSING / 0 CONFLICT (of 27).**

## 4. Contract verdict: REMAINS HOLD — not `STATICALLY_VALIDATION_READY`

Every byte, date, and split-definition blocker is closed. The contract nevertheless remains **HOLD**, on exactly two remaining fields:

- **4.2 Walk-forward fold calendar (exact OOS boundaries) — PROSE_ONLY.** The preregistration's own freeze-at-pull rule leaves exact fold dates to be frozen when a corrected dataset is pulled; they cannot be frozen before that pull exists, and no pull is authorized by this task.
- **4.5 No parameter selection on OOS / unseen data (governance rule) — PROSE_ONLY.** The rule exists as preregistration/mandate prose only; no byte-level or amendment-level pin was directed for it in this task, and none is claimed.

Nothing in this amendment authorizes data capture, a dataset pull, performance computation, holdout access or use, or execution of the restored modules.

## 5. Prohibitions — confirmation

Holdout contents were **never** opened, listed, hashed, enumerated, or accessed in any form; the date search touched governance text and git records only. Zero data capture; zero vendor/helper/model/API calls (network used only for the spec fetch and the delivery push); zero performance/backtest computation; zero strategy changes; the restored modules were not imported or executed (static text inspection only); zero live/production/ledger writes; zero Issue #9 work; no prior frozen record was edited — this amendment is a new document that supersedes by reference only.

---

**Signed:** Muse (executing agent) — 2026-10-18
**Hash chain:** spec comment `6254403898` · -21 memo `92ea4a999479b73a…` · -21 matrix `d913ce6a95d6fffa…` · -22 commit `8e0a187` · -23 memo `cfc1102e9e65f914…` · -23 adoption manifest `51144cd2c960dcda…` · this amendment's own sha256 is recorded in `validation_governance_closure_20261018_24/SHA256_MANIFEST.txt`.
