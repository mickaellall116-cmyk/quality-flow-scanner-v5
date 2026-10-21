# REQ-S2 split-exclusion — contract + boundary inventory

Task: QF-TD-REQ-S2-SPLIT-EXCLUSION-OFFLINE-IMPLEMENTATION-20261020-59 r1
Spec: Issue #1 comment 6304679072. Synthetic fixtures only. NOT integrated,
NOT adopted. Route remains OFFLINE_CANDIDATE_NOT_ADOPTED; entries PAUSED.

## Boundary inventory (existing 4H assembly path)

- Vendor receipts are validated by the validator candidate
  (`validate_input_v3_dstfix.py`, pin ca3bafd8…) and constructed into
  per-symbol 4H bars by the constructor candidate
  `construct_4h(df, symbol, validated_ends)` (-49 package
  `td_route_transaction_offline_proof_cli_closure_20261020_49/
  construct_4h_v3_cliguard.py`, pin 3f432e7e…), bound by the entrypoint
  candidate `pilot_build_v7_clibound.py` (pin 84ccd2c6…). Output: a bars
  DataFrame (Open/High/Low/Close/Volume, America/New_York index) per symbol.
- Downstream, `fold_materializer_v3.py` (-28 package
  `validation_fold_coverage_boundary_20261018_28/`) consumes a pinned
  session-schedule artifact plus bars; indicators/signals consume bars
  after that. Candidate entries are derived from bars downstream of
  construction.
- FINDING: no existing module assembles constructed bars + candidate
  entries into a research dataset at one named boundary. Assembly is
  implicit between construct_4h output and the fold/indicator consumers.

## Placement decision

Per spec §1 fallback: create a SEPARATELY VERSIONED offline candidate
module, `s2_split_exclusion_v1.py` in this package, and STOP SHORT of
integrating it. Its contract places it exactly at the missing boundary:
input = constructed bars + candidate entries (post-construction,
pre-indicator, pre-fold); output = post-exclusion bars + entries that
downstream must recompute from.

## Transform contract (REQ-S2, frozen from the validation contract)

Inputs:
- bars: records {bar_id, symbol, session "YYYY-MM-DD", bar_start ISO-8601
  tz-aware, open, high, low, close, volume}.
- entries: records {entry_id, symbol, session, entry_time ISO-8601
  tz-aware}.
- split_events: per-symbol ledger records {symbol, effective_session,
  source, provenance, as_of, version} — all fields required.
- acquisition_receipt: opaque validated receipt, carried through
  byte-identical; exclusion NEVER alters it and never upgrades an
  incomplete acquisition to complete.

Rule: for each valid event with XNYS effective session D, exclude that
symbol's bars AND candidate entries for sessions {prev_session(D), D,
next_session(D)} where prev/next are XNYS SESSION neighbors (PMC NYSE
calendar), never civil-day arithmetic. Overlapping windows union;
removed-session ledger deduplicates with all causing events recorded.
No cross-symbol leakage. No imputation, replacement, fill, or synthetic
bars: output bars/entries are an exact subset of the inputs. Inputs are
never mutated.

Fail closed (S2Refusal with code):
- NON_SESSION_EFFECTIVE: effective_session not an XNYS session.
- MISSING_FIELD / EMPTY_FIELD: any required event or record field
  missing/empty (symbol, session, provenance, as-of, version, source).
- DUPLICATE_CONFLICTING_EVENT: same (symbol, effective_session) with any
  differing field. (Byte-identical duplicates deduplicate.)
- TZ_NAIVE: bar/entry timestamp without an offset.
- SESSION_LABEL_MISMATCH: record's session label != the America/New_York
  calendar date of its timestamp, or label not an XNYS session, or
  duplicate bar/entry id — i.e. the record is not assignable to exactly
  one session.
- WINDOW_EDGE: D lacks a prev or next session inside the calendar range
  supplied to the transform.
