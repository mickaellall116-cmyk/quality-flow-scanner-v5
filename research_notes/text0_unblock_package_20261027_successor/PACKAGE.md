# Text 0 unblock package — SUCCESSOR (corr4), 2026-10-29

PREPARATION ONLY. This package was built under ChatGPT's HOLD on
the first unblock package (commit e3f5e8e), which expressly
requested a preparation-only successor closing its four blockers.
No holdout/sealed-window data was read in preparing it, no vendor
call was made, no performance quantity was computed, and no Text 0
run was performed. The Text 0 session itself still awaits
ChatGPT's reviewed PASS on this package.

## What changed vs e3f5e8e, per HOLD blocker

1. REPRODUCIBILITY — the suite is fully self-contained in this
   package. The pinned corr2 source the tests depend on is
   included (corr2_src/, sha256 = the P11 pin). The builder's
   frozen engine modules (engine/run_study13.py, pine_backtest.py,
   scanner_rules.py) and the adopted session table
   (session_table_751.json, sha256 = the P11 pin) are vendored and
   hash-verified at runtime. All fixtures are committed or
   generated deterministically by committed generators. No file
   outside the package is read (the e3f5e8e suite read a reference
   inventory from a private archive clone and a session table from
   a stage home; both are gone). One documented command runs the
   whole suite (below); the suite additionally rebuilds the full
   fabricated inventory inside a COPIED package tree and asserts
   the identical inventory hash. The e3f5e8e dev-validate check
   (byte-reproduction of the P7b DEV inventory) is dropped by
   design: it inherently required private archive bytes, which
   cannot be committed to this repo; builder correctness on the
   sealed-window path is instead proven end-to-end on fabricated
   captures over the real pinned window (suite Part C).
2. PRE-READ PINS, NO OVERRIDES — window (2023-10-19 →
   2024-09-15), tier membership (19 Tier 2 + 11 Tier 3, listed in
   stage1_manifest.json and re-derived in tier_derivation.json),
   and code/data hashes are pinned in stage1_manifest.json BEFORE
   any access; its binding content is pinned by canonical-content
   hash compiled into BOTH the matcher and the builder, which
   verify before reading anything else (the builder also verifies
   its own bytes against the manifest's builder pin). The
   e3f5e8e interfaces are removed, not gated: no --symbols,
   --manifest, --session-table, --fixture-table, or --mode
   arguments exist on the builder; the matcher takes no --manifest
   argument (the manifest lives at a fixed path beside the code);
   no environment-variable latch exists anywhere. Override
   attempts are rejected by argparse itself (suite A10/C1).
   Session authorization for the builder is an artifact, not an
   env var: a JSON record naming the pinned content hash, the
   builder's hash, window, tiers, mode, session id, and exactly
   two operators, verified before the raw directory is touched.
3. NON-CIRCULAR BINDING — staged, explicit (next section). No step
   completes or repins a manifest after a sealed read; the
   counting step creates no pins of any kind.
4. TIER 3 BYTES — DECISION_CARD_TIER3_BYTES.md documents the
   absence (Tier 3 holdout-window captures do not exist), what a
   capture would require, and that obtaining it is a separate
   scoped decision NOT taken here. The code fails closed with
   named errors — builder: TIER3_CAPTURE_MISSING (exit 3);
   matcher: TIER3_INVENTORY_MISSING — and never silently shrinks
   the tier (suite A5/C5 prove both).

## The staged design (non-circular)

- Stage 1 — THIS package, committed and independently reviewable
  now: stage1_manifest.json pins the binding content (binding id,
  window, tier membership, session-table pin, corr2 pin, engine
  pins) by canonical-content hash, compiled into both programs.
  The manifest deliberately does NOT pin the matcher (that would
  be circular: the matcher pins the manifest); the matcher's own
  sha256 is pinned here in SHA256_MANIFEST.txt and enters the
  freeze record with this package's commit.
- Stage 2 — the future reviewed session, which only verifies the
  pins it was given and counts:
  1. a session-authorization artifact is issued for the builder
     (two operators, naming the Stage-1 content hash);
  2. the builder verifies all Stage-1 pins + the authorization,
     builds the sealed-window inventory from the session's raw
     captures, and emits a provenance summary (inventory hash +
     census as addendum inputs — evidence, not a pin);
  3. the Stage-2 addendum (stage2_addendum.json: binding id,
     content-hash reference, builder/table pins copied from
     Stage 1, inventory hash, census, session record) is created
     as a separate reviewed artifact, and ITS hash is entered in
     the freeze record before any counting run;
  4. the matcher verifies Stage 1 + addendum, loads the inventory
     against the addendum's hash, verifies tier membership and
     window, reconciles the census, and counts. It writes only
     the outcome-free pool-count report (plus cohort/draws files
     if the session passes those paths, per the frozen protocol).
  At no point does a step that has touched sealed data create or
  alter a pin that a later step trusts: pins flow Stage 1 →
  addendum → counting, each created before the access it governs,
  each hash entered in the record before use.

## Contents

SHA256_MANIFEST.txt pins every file. In brief:

- exp14_buy_corr4.py — the counting matcher, derived from the
  pinned corr2 by build_corr4.py (exact asserted replacements;
  corr2_to_corr4.diff is the line-by-line record; suite Part B
  machine-verifies that everything except the binding is
  AST-identical to corr2).
- corr2_src/exp14_buy_corr2.py — the pinned predecessor, verbatim.
- build_holdout_inventory_corr4.py — the Stage-2 inventory
  builder (vendored engine, authorization artifact, named
  missing-capture errors).
- engine/ — the frozen -13 pipeline modules, verbatim, pinned.
- session_table_751.json — the adopted qualified calendar, pinned.
- stage1_manifest.json — the Stage-1 pins.
- tier_derivation.json — machine-checkable tier derivation
  (44 UX51 equities − 25 quarantined holdout legs = Tier 2;
  frozen 12 − GOOG = Tier 3), re-executed by suite Part D.
- build_corr4.py — the package build script (derives corr4, sets
  both content pins, composes the manifest, emits the diff and
  SHA256_MANIFEST.txt).
- fixtures/ — committed fabricated fixtures + make_fixtures.py
  (deterministic regeneration, asserted by suite Part D).
- test_text0_unblock_successor.py — the suite.
- DECISION_CARD_TIER3_BYTES.md — the Tier 3 bytes decision card.
- test_output.txt — the recorded suite run from staging.

## Running the suite

    cd research_notes/text0_unblock_package_20261027_successor
    python3 test_text0_unblock_successor.py

Requires an interpreter with pandas and pandas_market_calendars
(the frozen engine's own documented dependency). The suite runs
entirely on fabricated fixtures; it reads no holdout data and
makes no vendor call. Expected result: all checks PASS (count
recorded in test_output.txt; the committed package is additionally
verified by running the same command from a fresh checkout of the
commit — see the delivery post for that result).

## Boundaries kept

Outcome-free by construction on the counting path (counts only;
RETURNS_ENABLED remains False and the returns machinery is
byte-identical to corr2, gates intact). Nothing here authorizes
the Text 0 session: it opens only on ChatGPT's reviewed PASS of
this package under the freeze, with the Tier 3 decision card
answered or the session explicitly scoped around it.
