# REQ-S2 boundary + coverage static contract — task -60 r1

Task: QF-TD-REQ-S2-BOUNDARY-AND-COVERAGE-STATIC-CONTRACT-20261020-60 r1
Spec: Issue #1 comment 6306263477 (independent -59 review; basis -59
commits 6da0783 / 2832d39).
Method: ONE read-only/offline static pass. Source inspection only —
no execution, no tests, no reruns, no staging, no code edits.
Start convention: elapsed from spec fetch 2026-10-21T02:10Z.
Status of this commit: PRE-RESULT (DAG + inspection record committed
before the terminal designation is recorded in the result commit).

## 1. Sole ownership

Pre-check before any file operation: no -60 commit on origin/main,
no qf_td60 owner lease, no td60 stage/worktree. Parent pre-check
re-verified by this worker. One lane only. This is a read-only pass;
no lease was needed for execution because nothing executes and no
shared stage exists — the memo package is committed from a fresh
detached worktree of origin/main (7dcc1cc).

## 2. Frozen REQ-S2 contract text (what must be satisfied)

- -48 PIN_DAG.md (sha256 55173ce2…), lines 99–103: "adjudicated
  placement is the future 4H dataset-assembly component downstream
  of the constructor — validate/construct the complete receipt set
  first, then exclude bars AND candidate entries D-1..D+1 around
  each split effective session, recompute with no imputation."
- -48 PREP_MEMO.md (61cc86ab…), line 81; NEXT_TRANSACTION_PROOF_SPEC.md
  (bd5b3c90…), lines 48–52: same requirement; no corrected-performance
  use until REQ-S2 is proven.
- -59 CONTRACT.md (a2928ff8…): transform input = constructed bars +
  candidate entries at a post-construction / pre-indicator /
  pre-fold boundary; output = post-exclusion bars + entries that
  downstream must recompute from. Its own boundary inventory records:
  "no existing module assembles constructed bars + candidate entries
  into a research dataset at one named boundary. Assembly is implicit
  between construct_4h output and the fold/indicator consumers."

## 3. DAG of ACTUAL data flows (path / line / SHA-256 keyed)

### Nodes

| # | Role | Path | SHA-256 | Key lines |
|---|------|------|---------|-----------|
| N1 | Acquisition manifest (frozen TD-PILOT-MANIFEST-R3-20261010) | research_notes/pilot_harness/request_manifest.json | a0a001b7458993ff… | defaults L8–15: endpoint `/time_series` only, `adjust: "splits"` |
| N2 | Acquisition | research_notes/pilot_harness/pilot_acquire.py | acf39bbd98f717… | L129 `adjust` field ("splits", pinned default) |
| N3 | Entrypoint candidate v7 | research_notes/td_route_transaction_offline_proof_cli_closure_20261020_49/pilot_build_v7_clibound.py | 84ccd2c68aea0f0c… | L64 validator import (by module name); L69–75 constructor bound BY EXACT PATH via `_c4h_mod`; L88–125 `_decode_validated_ends`; main: verify_sources subprocess → validate() L198 → construct_4h L215–216 → bars CSV out |
| N4 | Validator candidate | research_notes/td_validator_dst_repair_requalification_20261019_44/validate_input_v3_dstfix.py | ca3bafd87e7cb4… | validate() L99 |
| N4o | Validator original (name-binding target in pilot_harness) | research_notes/pilot_harness/validate_input.py | 1b83cdcd4f6e2a… | — |
| N5 | Constructor candidate (CLI-refusing) | research_notes/td_route_transaction_offline_proof_cli_closure_20261020_49/construct_4h_v3_cliguard.py | 3f432e7e30d3d9… | construct_4h L74; refusing CLI main L224 |
| N5o | Constructor original (precedence reference) | research_notes/pilot_harness/construct_4h.py | d47e8df14ec5f6… | construct_4h authoritative per -48 PIN_DAG precedence |
| N6 | S2 transform candidate (-59) | research_notes/td_req_s2_split_exclusion_20261020_59/s2_split_exclusion_v1.py | 7791ca91eb18e6… | xnys_sessions L36–40; _check_record_session L52–75; _validate_events L84–105; apply_split_exclusion L115–171 |
| N7 | Fold consumer | research_notes/validation_fold_coverage_boundary_20261018_28/fold_materializer_v3.py | e1b0dfed43c7c0… | materialize(timestamps, schedule_bytes, schedule_sha256) L211; coverage contract docstring L1–52 |
| N8 | Entry/indicator derivation (scanner lineage) | pine_signal_quality/pine_signal_quality.py | b1b39ee8d0bd4b… | gen_trades(sym, df, filt) L100 — derives trades/entries from a bars DataFrame |
| N8b | Ranking / exposure (downstream of entries) | pine_ranking/pine_ranking.py 77afae0d…; pine_exposure/pine_exposure.py 9f646161… | — | — |
| N9 | Historical resampler (NO production edge, -48) | canonical_baseline/scripts/fetch_4h.py | 2a4994a26dbb98… | reference only |

### Edges that EXIST (pinned code)

- N1 → N2 → 1H CSV (vendor bars, split-ADJUSTED prices; no event data).
- 1H CSV → N3: verify_sources (unconditional, exit 3 on failure) →
  N4 validate() (window/session/interval-end contract + mandatory
  tz-aware as_of cutoff) → N5 construct_4h(df, symbol, as_of,
  validated_ends) → bars DataFrame (NY DatetimeIndex, OHLCV) → CSV file.
- N7 consumes bar TIMESTAMPS + the pinned XNYS_SESSION_SCHEDULE_V2
  artifact bytes + its SHA-256 pin. It accepts no prices.
- N8 consumes a bars DataFrame and derives entries (gen_trades).

### Edges that DO NOT EXIST (the gaps this task was asked to find)

- G-EDGE-1 (split events → anywhere): NO producer. The frozen
  acquisition manifest (N1) contains only /time_series requests with
  adjust="splits"; there is no splits-event request, no event-ledger
  file, and no event receipt schema anywhere in the pinned chain.
  N6's `split_events` input and its `acquisition_receipt` parameter
  have no real-world source — in -59 they were synthetic fixtures.
- G-EDGE-2 (entrypoint output → consumers): NO pinned assembly code
  connects N3's bars CSV to N7 or N8. Assembly is manual/implicit
  (confirmed by -59 CONTRACT.md's own inventory).
- G-EDGE-3 (N3 → N6): N5 emits a DataFrame with a NY DatetimeIndex and
  OHLCV columns — no bar_id, no session field. N6 consumes record
  dicts {bar_id, symbol, session, bar_start, OHLCV}. No adapter exists.
- G-EDGE-4 (entries at the boundary): NO module in the TD route emits
  entry records {entry_id, symbol, session, entry_time}. Entries
  exist only downstream of N8-style derivation from bars.
- Note (binding asymmetry): N3 binds the constructor BY EXACT PATH
  (hash-proven in -58) but imports the validator BY MODULE NAME
  (L64); which validate_input bytes run depends on staging
  discipline, not on the entrypoint source. Recorded as a DAG fact;
  not an S2 blocker, but any future assembly proof must pin the
  staged validator bytes explicitly (as the -53..-58 shadows did).

## 4. Cutpoint finding

A feasible deterministic cutpoint EXISTS in principle, at exactly one
place: **immediately at the entrypoint's construction output, before
any indicator, entry-derivation, or fold computation** — implemented
as a NEW, separately versioned assembly shim. No frozen candidate
needs modification (see §6). The shim contract:

1. Invoke the cleared entrypoint (N3) per symbol/window (subprocess,
   the F1 pattern) — never re-implement validate→construct.
2. Adapt bars → N6 record schema deterministically:
   bar_id = symbol + "|" + bar_start ISO-8601 (NY index instant,
   offset preserved); session = America/New_York calendar date of
   bar_start; OHLCV copied exactly. The CSV round-trip must be proven
   float-exact in the acceptance plan (§7), fail closed otherwise.
3. Entries at the cutpoint: **entries = []**. No entry list exists
   before the cutpoint anywhere in the pinned chain (G-EDGE-4), so
   there is nothing pre-cutpoint to filter. All entries are recomputed
   downstream from bars_out only — which is exactly N6's own contract
   ("downstream must recompute"). An entry derived solely from
   surviving bars can never reference an excluded session's bar.
4. If a future design ever produces an entry list BEFORE the cutpoint,
   the no-lookahead co-filter is: drop any entry whose entry_time's
   NY session ∈ removed_sessions_ledger for that symbol (N6's
   _partition semantics, L139–156); never re-time, never re-derive
   from pre-exclusion bars; the entry set after the cutpoint must be
   a strict subset of derivations from bars_out.
5. Folds: N7's coverage contract REQUIRES every scheduled session in
   [2024-09-16, coverage_end] to be present (COVERAGE_PREFIX /
   INTERIOR / SUFFIX_MISSING fail-closed). A post-S2 gapped timestamp
   set fed to N7 fails BY DESIGN. Therefore folds are materialized
   from the PRE-exclusion timestamp set, and excluded sessions are
   intersected out of fold membership downstream. Fold boundaries are
   never recomputed from gapped data (recomputing 252/63 boundaries
   on a gapped series would silently shift every fold — a determinism
   and anti-leakage violation).
6. Indicator warmup: exclusion removes bars; indicators recompute on
   the gapped series with NO imputation/fill (frozen rule). Warmup
   insufficiency downstream is a consumer-side fail-closed concern,
   not a reason to fill.

The cutpoint is therefore specifiable and deterministic — but it is
NOT buildable into a qualified integration today, because its
split-events input has no producer (§5) and its downstream wiring
does not exist (G-EDGE-2). Specifying a cutpoint is not readiness.

## 5. Completeness / PIT / edge-coverage gates (fail-closed)

These gates sit at the future acquisition/assembly boundary. N6
validates the FORM of what it is given; it cannot prove any of the
following, and none may be assumed from its 16 synthetic passes:

- GATE-E1 (producer existence): a pinned split-event acquisition leg
  — endpoint, request manifest, receipt schema — must exist before
  integration. STATUS: ABSENT (G-EDGE-1). Missing pin: no file, no
  hash can be cited.
- GATE-E2 (coverage completeness): the event inventory must provably
  cover every symbol × the full bar window. A missing event fails
  SILENTLY (no exclusion happens), so completeness needs evidence
  outside the transform: an independent cross-check or a vendor
  completeness attestation bound into a hash-pinned receipt whose
  symbol×window set equals the bars' set exactly. Assembly refuses
  on any mismatch or on a receipt asserting less than full coverage.
- GATE-E3 (PIT availability): each event carries as_of, but nothing
  populates or checks it. Assembly must refuse if any event's as_of
  is after the dataset's as_of cutoff, if the receipt lacks an
  acquisition timestamp, or if event provenance is not bound to the
  receipt bytes. (N3's validate() enforces the causal cutoff for
  BARS; no equivalent exists for events.)
- GATE-E4 (calendar-range edge coverage): the calendar range supplied
  to N6 must extend ≥1 XNYS session beyond the bars' span on BOTH
  sides, and must be derived from (event inventory ∪ bars span),
  never set independently — an event just outside a too-narrow range
  whose D−1 falls inside the data is invisible to the transform.
  N6's WINDOW_EDGE refusal (range-edge D) and SESSION_LABEL_MISMATCH
  (record session ∉ supplied set) are necessary, not sufficient.
  Assembly-side check: bars span ⊆ sessions[1..−2] of the supplied
  range, fail closed otherwise.
- GATE-E5 (calendar source pinning): N6 derives adjacency from live
  pandas_market_calendars NYSE at runtime (L36–40) and takes NO
  schedule artifact or pin — unlike N7, which is pin-bound to the
  qualified XNYS_SESSION_SCHEDULE_V2. In proof environments the PMC
  version is freeze-pinned (08b38cfa…), but the module itself records
  no calendar provenance in its output. The boundary contract
  requires the assembly receipt to record the calendar source +
  version/freeze hash used, or a future versioned transform to take
  the pinned schedule artifact as input.

## 6. Schema adaptation without modifying frozen candidates

- Bars: YES. An external adapter (new file) converts N3's CSV /
  DataFrame output to N6 records with the deterministic derivation
  in §4.2. N3, N4, N5 are untouched; the entrypoint's output file is
  the stable interface.
- Entries: YES — vacuously. entries=[] at the cutpoint; derivation
  stays downstream.
- Split events: NO — there is nothing to adapt. A producer must be
  CREATED (new component, its own adjudicated task; any vendor call
  is separately hard-gated). No schema adaptation of existing pinned
  files can manufacture an event ledger.
- Folds: YES with the §4.5 ordering (materialize pre-exclusion,
  intersect downstream). N7 is untouched.
