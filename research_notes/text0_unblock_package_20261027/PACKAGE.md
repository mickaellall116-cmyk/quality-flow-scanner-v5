# Text 0 Unblock Package — corr3 successor + holdout inventory builder

**PREPARATION ONLY.** Built 2026-10-27 under ChatGPT's desk guidance on
the Text 0 STOP ("prepare only — no holdout read — minimal corr3 +
outcome-blind inventory-builder package for review"), inside Mike's
2026-10-27 ruling (relayed approvals inside the research program
execute as scoped; hard gates unchanged). **No holdout bars were read,
no sealed-window data was accessed, and no performance quantity was
computed in building this package.** All executions were on DEV data
or fabricated fixtures. The Text 0 run itself does **not** happen
here: it executes later, in the authorized session, on ChatGPT's
reviewed send under Mike's ruling.

## Why this package exists

Text 0 (the authorized outcome-blind §5 pool-count session) STOPPED
before any holdout access (commit `da65466`,
`research_notes/text0_pool_counts_20261027/`) because the
freeze-pinned matching code — EXP-14 corr2 `exp14_buy.py`, P11 pin
sha256 `77bd53e8…` — is DEV-bound by compiled-in constants:
`EXPECTED_FIRES = 2892` (the DEV P7 census, line 137) and the DEV
window `DEV_START/DEV_END = 2024-09-16/2026-10-16` (lines 138–139),
so `run_pool_counts()` fail-closes on any holdout-domain inventory.
The STOP record's unblock path named exactly two artifacts: a
corr3-style successor whose binding points at a pinned holdout
inventory, and a pinned holdout inventory builder. This package is
those two artifacts, plus their evidence.

## Contents and proposed pins

| File | SHA-256 | Role |
|---|---|---|
| `exp14_buy_corr3.py` | `361dc4e8eb28720a1bd9ca1284041e6c8ce51b52dc88e4ab628a41fcad174266` | corr3 successor of the pinned corr2 matching code |
| `corr2_to_corr3.diff` | `b9c6a93b76ff7fc312d7a7fe245f87ed5e617146adb7d97e12080309e0d63406` | unified diff, corr2 (pin `77bd53e8…`) → corr3 |
| `holdout_binding_manifest.json` | `f991965fcc4e26976be60a11c65308ec6357e689c65a6e07bb767112e2999705` | binding manifest, STAGING TEMPLATE (see below) |
| `build_holdout_inventory.py` | `3a7e454f8254a5be26b2073fe3948d52c19eaec38ed11efadd2b79ff117c119b` | outcome-blind holdout inventory builder |
| `test_text0_unblock.py` | `1667bd01fe1b47650ea6d5a8c36e4e53bfbbe9c8a855bef1d03849bc5d86784d` | full test suite (28 checks) |
| `test_output.txt` | `82320f8b981e8133393a5f211d66ab1e7163c159ed58bb37d078353169a7d70a` | recorded suite run, 28/28 PASS |

## corr3 — what changed, and proof nothing else did

The diff is 270 lines; every hunk is one of these enumerated
binding changes:

1. **Docstring** — a CORR3 successor note appended; the corr2 text
   is untouched.
2. **Constants** — `EXPECTED_FIRES` / `DEV_START` / `DEV_END`
   removed; added `PINNED_MANIFEST_SHA256` (the compiled-in hash of
   the binding manifest), `WINDOW_START = 2023-10-19`,
   `WINDOW_END = 2024-09-15`.
3. **New binding trio** — `load_binding()` (verifies the manifest
   file against the compiled-in pin — caller-supplied hashes are
   never the expectation, the same discipline as corr2's
   `PINNED_INPUT_SHA256`; strict key set; window cross-checked
   against the compiled-in constants; tiers non-empty, disjoint,
   duplicate-free), `require_completed_binding()` (a template
   manifest can never run), `verify_holdout_binding()` (loaded
   inventory's symbol set must equal Tier 2 ∪ Tier 3 exactly; every
   row's `session_date` inside the sealed window; returns the
   manifest's pinned census).
4. **Census reconciliation** — `run_pool_counts(by_symbol,
   expected_fires)`: the expectation is the manifest's census (the
   holdout inventory's own fire count, recorded at staging), not
   2892.
5. **Window check** — `_check_dev_ts` → `_check_window_ts`, bound to
   the holdout window constants; its two call sites in
   `_analysis_impl` updated. The analysis path remains gated
   (`RETURNS_ENABLED = False`); this change keeps the gated path
   domain-consistent and is not an authorization.
6. **Version marker** — `script_version` 3 → 4 in the three output
   artifacts (successor identification, not logic).
7. **CLI** — `--manifest` argument; the pool-count branch verifies
   manifest → completed binding → inventory hash (against the
   manifest, refusing a disagreeing `--inventory-sha` as a wiring
   error, mirroring corr2's returns branch) → membership/window →
   counts, in that order, before any pool is counted.

**Proof (test part B, AST-level):** every function shared by corr2
and corr3 is AST-identical except `run_pool_counts`, `main`, and
`_analysis_impl` (the last proven identical modulo the renamed
window check at its two call sites; `_check_window_ts` proven
identical to `_check_dev_ts` modulo the binding tokens). The only
new functions are the binding trio. Module-level constants differ
only in the enumerated binding set — ladder, seeds, and
`PINNED_INPUT_SHA256` are byte-identical. `STUDY_ID` and the seed
family are deliberately **unchanged** (draw identities inherit the
frozen derivation); flagged here for review rather than silently
re-derived.

**Deliberate design point for review:** corr3's `main()` writes the
cohort/draws artifacts only when `--out-cohort` / `--out-draws` are
passed (corr2 behavior, unchanged). Text 0's permitted outputs are
the report's counts only, so the session invocation passes only
`--out-report`.

## The binding manifest (staging template)

`holdout_binding_manifest.json` as shipped carries the final window
(2023-10-19 → 2024-09-15) and tier membership, with
`inventory_sha256` and `expected_fires` **null**:

- **Tier 2 (19)** — AAPL, AMD, AMZN, ARKK, ARM, AVGO, COIN, IWM,
  LUNR, META, MSFT, NFLX, NIO, NVDA, SHOP, SMH, SPY, TSLA, XLF.
  Derivation from the record: the 44 XNYS names minus the 25
  defective HO legs — the §9 audit quarantine census (23 legs, 123
  bars; `s9_contamination_audit_20261026/evidence/
  quarantine_census.json`) plus SMCI and PLTR (G4 feed facts,
  -17 package: 145 defective bars program-wide = 123 + SMCI 19 +
  PLTR 3).
- **Tier 3 (11)** — AAOI, ACN, BABA, BE, BLK, COF, CRDO, IREN, MPWR,
  SPOT, TWLO (the frozen 12-name list minus GOOG, removed on the
  issuer gap per the closure addendum `c31c613`).

corr3's compiled-in `PINNED_MANIFEST_SHA256` pins this template.
At staging, the session completes the manifest with the built
inventory's SHA-256 and census, re-hashes it, and re-pins that one
constant in corr3 — the re-pinned corr3 hash is the successor pin
entered in the freeze record. Test A7 proves the shipped template
refuses to run.

## The builder

`build_holdout_inventory.py` is the successor of the P7b builder
(`build_p7b_inventory.py`, sha `f01b3afc…`), emitting the identical
row schema (the corr2/corr3 `REQUIRED_ROW_KEYS` + fields) for the
holdout domain:

- Admission re-implements the frozen `run_study13.phase2` gates in
  substance (session-table expected starts; meta check; finite /
  positive values; duplicate stamps; excluded stamps only in the
  generic early-close class; admitted set exactly the expected set;
  zero admitted price-moving zero-volume bars), parameterized by
  window/suffix.
- The 4H resample is the frozen `phase4` itself, with its
  compiled-in `EXPECTED_BARS_4H` temporarily set to the count
  computed from the window's session subset (DEV computes to
  exactly 1043, asserted; nothing on disk is modified).
- Indicators/signals only from the frozen engine
  (`add_pine_indicators`, `pine_buy_signal`, `WARMUP`);
  `session_ordinal` = position in the window subset of the adopted
  751-session table (sha `00c5555c…`), mirroring the DEV
  convention; domain = `WARMUP <= idx <= n-2`.
- Session ordinals, bins, and field provenance are identical in
  construction to P7b; nulls are the frozen indicators' own NaN
  warmup.
- **Latch:** `--mode holdout` refuses unless
  `TEXT0_SESSION_AUTHORIZED=1` is set — only the authorized session
  may set it. The suite never runs that mode.
- The summary records the inventory SHA-256 and the domain fire
  census — the two values that complete the binding manifest.

**Builder evidence (test C1):** in `--mode dev-validate`, this code
path reproduces the pinned P7b inventory **byte-for-byte per
symbol** for NVDA, AMD, PLTR (3,129 rows, incl. the PILOT-namespace
and PLTR cases), against the reference inventory hash-verified at
`a6bbd19a…` before comparison.

## Test results — 28/28 PASS (`test_output.txt`)

- **A (corr3 binding, synthetic fixtures):** positive run under a
  completed fixture binding reconciles the planted census (6) and
  cohort (5); refusals proven for tampered inventory (hash
  binding), tampered manifest (compiled-in pin), extra symbol
  (tier membership), out-of-window row, census mismatch, and the
  shipped template; corr2 control reproduces the STOP blocker
  (`P7 census 2892`) on the same synthetic inventory.
- **B (diff audit):** AST proof as above (6 checks).
- **C (builder):** DEV byte-reproduction (C1); synthetic
  holdout-parameterized build on fabricated captures over 40 real
  sessions produces the exact schema, correct bar counts
  (79 = 2×40 − 1 early close), and a summary carrying the inventory
  hash + census (C2 series); poisoned capture (price-moving
  zero-volume admitted bar) STOPs with no output (C3); holdout
  latch (C4).

## How Text 0 then runs (one session, under the successor pin)

1. Session opens under the §2 firewall conditions (two people,
   logged end-to-end) per Text 0 as adopted. Pins verified first:
   re-pinned corr3, builder, session table, manifest.
2. Holdout capture bytes are presented read-only from the private
   archive environment (raw bytes never leave it). Builder runs
   with the latch set → holdout inventory JSONL + summary in the
   private environment.
3. Manifest completed with the inventory SHA-256 + census from the
   builder summary; manifest re-hashed; corr3's
   `PINNED_MANIFEST_SHA256` re-pinned; re-pinned hashes entered in
   the freeze record.
4. corr3 runs once, `--mode pool-counts --out-report` only. Outputs
   limited to Text 0's permitted set: per-event eligible-pool
   counts, the dropped-event count, and the event-mix composition
   summary. Counts entered into the freeze record; FREEZE_CHECKLIST
   row O6 closes.

## Open staging facts, flagged not papered over

- **Tier 3 capture bytes do not yet exist in the archive namespaces
  the builder reads.** The committed captures cover the UX51 names
  (Tier 2's source); the 11 Tier 3 names have no `__HO` capture
  files in `td_pilot_20261023` / `td_capture_equity39_continue_20261023`.
  Step 2 above requires committed Tier 3 holdout-window bytes in
  the -13 raw format, presented by the session; producing them is
  a capture step outside this package and is **not** authorized by
  it. The builder STOPs at file-open if a manifest symbol has no
  capture file — it invents nothing.
- The manifest completion + re-pin (step 3) is a freeze-record
  action taken inside the session under the reviewed send; the
  hashes in this package pin the *template* state only.

## What remains gated

ChatGPT's review of this package; then the pin + Text 0 rerun
execute on ChatGPT's reviewed send under Mike's 2026-10-27 ruling.
No second sealed-window session is inferred or authorized by
anything here. G7 and all tier openings remain ungiven. The hard
gates (purchases, deletions, real-money trades, production /
frozen-strategy changes) are untouched by this package.
