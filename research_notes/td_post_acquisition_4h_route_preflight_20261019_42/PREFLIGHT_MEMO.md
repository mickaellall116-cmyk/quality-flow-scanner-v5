# QF-TD-POST-ACQUISITION-4H-ROUTE-PREFLIGHT-20261019-42 r1 — PREFLIGHT MEMO

Static / read-only. Spec: Issue #1 comment `6280342431` (the -41 verdict + this
dispatch). One pass, no repair loop, nothing executed, nothing edited.

## TERMINAL VERDICT

`POST_ACQUISITION_4H_ROUTE_HOLD__CONSTRUCTOR_PRECEDENCE_EQUIVALENCE_UNPROVEN`

Two co-blocking findings; the key names the spec §1 condition, and the
preregistered proof below is scoped to close both:

- **B-1 (precedence/equivalence):** No committed record states precedence
  between the TD construction path (`pilot_build.py` → `construct_4h.py`) and
  the restored canonical resampler (`fetch_4h.resample_4h`), and no proof of
  their equivalence exists. They agree on well-formed regular-session input
  by construction inspection only, and diverge behaviorally on closed days,
  missing constituents, duplicates, and partial (as-of) bins — see
  SEMANTIC_MATRIX.md. Spec §1: lack of explicit precedence or proven
  equivalence ⇒ HOLD.
- **B-2 (artifact divergence):** `construct_4h` resolves every session close
  by direct live PMC lookup and never consumes the qualified
  `XNYS_SESSION_SCHEDULE_V2` artifact. Spec §3: direct PMC lookup outside
  the artifact contract is a blocking divergence unless a pinned equivalence
  proof already exists. None covers `construct_4h` (see below).

## What construct_4h is (identity + behavior)

`research_notes/pilot_harness/construct_4h.py`, sha256
`d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd`, 263 lines,
"v2" (repair lineage ChatGPT 6037842097 / 6039806101 / 6043633584, in-file).
The cleared entrypoint is `pilot_build.py` (sha256 `257d5bb9…`): unconditional
`verify_sources.py` (pins only the two archival strategy sources
`pine_backtest.py 447a9a13…`, `scanner_rules.py 7db282dd…` — it does NOT pin
construct_4h, validate_input, or pilot_build themselves) →
`validate_input.validate` (sha256 `1b83cdcd…`) → `construct_4h(df, symbol,
as_of, validated_ends)` (pilot_build.py:124–130).

Behavior (line-cited in SEMANTIC_MATRIX.md): explicit session bins from local
wall-clock minutes — [09:30,13:30) labeled 09:30, [13:30, close) labeled
13:30, early-close day → single 09:30 bin closing at the session close;
mandatory tz-aware `as_of` (constituent ends ≤ as_of; only bins whose close
≤ as_of are emitted); constituent-end precedence validated_ends >
`interval_end` column > expected-grid derivation; agg Open first / High max /
Low min / Close last / Volume sum; output = tz-aware America/New_York
DatetimeIndex + Open/High/Low/Close/Volume. On regular and early-close days
this matches the frozen constructor semantics of the validation contract.

The calendar problem: per-date closes come from `session_close_et`
(construct_4h.py:49–61) — `import pandas_market_calendars` (:53),
`mcal.get_calendar("XNYS")` (:54), `.schedule(date, date)`, raise on empty
(no 16:00 fallback). `pilot_build.py` does NOT pass the `session_closes`
override (construct_4h.py:71), so on the cleared path every date is resolved
by live PMC in whatever environment runs it. Nothing in pilot_build or
construct_4h asserts the PMC version; the 4.5.1 exactness lives in the lock
(`08b38cfa…`) and the supplement/classifier side of the -41 chain, not in
the construction entrypoint. The cleared path therefore resolves the same
calendar fact TWICE: `validate_input.xnys_schedule` (:47–56, live PMC — this
leg IS inside the -41 reconciled chain: validator pin + lock PMC==4.5.1 +
the -40 P1–P8 proof over that mechanism) and `construct_4h.session_close_et`
(same call shape — OUTSIDE the chain, per the -41 verdict's remaining
blocker). construct_4h's bytes are recorded in unadopted Oct 13–14 candidate
evidence (`td_combined_candidate_verify_evidence_20261014/candidate_manifest.json`)
but the file is pinned nowhere in the reconciled readiness chain.

Also recorded: the standalone CLI (`construct_4h.py main`, :220+) still runs
construction bypassing validation — the docstring (:24–27) warns against it,
but the bypass exists as shipped (governance hazard, decision D4).

## Route options

**(a) Pin construct_4h as-is into the 4.5.1 lineage.** Requires: a chain pin
of `d47e8df1…`; an entrypoint-level PMC==4.5.1 assertion (or equivalent env
binding); the E1 closes-equivalence proof (below); and an adjudicated
precedence sentence vs `fetch_4h.resample_4h`. Residual gaps even then:
calendar truth stays library-side and twice-resolved; the qualified artifact
remains unused by construction; Amendment v1 S2 placement (D3) unresolved.

**(b) Separately versioned artifact-consuming constructor.** Mechanically
small: a caller that builds `session_closes` from `XNYS_SESSION_SCHEDULE_V2`
(pin `3358f2d9…`) and passes it in — construct_4h's override already exists.
But: (i) validate_input still resolves its own schedule via live PMC, so a
closes-only variant leaves the validator PMC-backed (acceptable — that leg
is pinned + proven) while a FULL artifact variant changes the pinned
validator bytes and voids the NL451 proof's object; (ii) **the artifact
cannot cover the warm-up**: its coverage is exactly the dev interval
2024-09-16 → 2026-10-16, while the frozen contract needs a 215-bar warm-up
before 2024-09-16 (≈108 sessions the artifact does not list). An
artifact-route constructor needs a second, pinned calendar source for
warm-up sessions — the pinned validator (PMC 4.5.1) is the only candidate
on record. (iii) New version ⇒ new supplement/proof cycle (governance).

**(c) fetch_4h.resample_4h as the TD constructor.** NOT viable: it is a
Yahoo fetch script (canonical_baseline/scripts/fetch_4h.py, sha256
`2a4994a2…`, :27–40) with no calendar, no validation, no as-of, silent
missing-bar aggregation, and dedupe-keep-last. It remains the historical
convention REFERENCE (the semantics the validation lineage was built
against), not a candidate producer for vendor receipts.

**Recommendation:** neither (a) nor (b) is PREP_READY today; the gating item
is the same for both — the unrun equivalence proof plus adjudicated
precedence. Run the proof (below), then adjudication picks the route.

## Preregistered smallest future integration proof (NOT run here)

Name: QF-TD-CONSTRUCTOR-EQUIVALENCE-PROOF (future task, est. ≤45 min,
offline, single attempt, first failure stops, repair minutes must be 0).
Environment: pinned 4.5.1 lineage only (lock `08b38cfa…`, wheelhouse
manifest `210b8273…`), no-network namespace. Inputs = committed bytes only:
construct_4h `d47e8df1…`, validate_input `1b83cdcd…`, pilot_build `257d5bb9…`,
fetch_4h `2a4994a2…`, artifact `3358f2d9…` (@ `9c62e255`).

- **E1 — closes equivalence (524 + closed-set):** for every session in the
  artifact, `session_close_et(date)` under the pinned env == artifact close
  localized to America/New_York; for every non-session date in coverage,
  `session_close_et` raises ⇔ date absent from the artifact. PASS = 524/524
  and full closed-set agreement.
- **E2 — fixture matrix (synthetic 1H, 8 fixtures):** F1 regular day;
  F2 early-close day (13:00); F3 DST-spring week; F4 DST-fall week;
  F5 two window lengths over identical bars (the Oct 3 parity shape:
  overlapping bars byte-identical); F6 closed day with stray bars —
  cleared path must FAIL at validation (resample_4h divergence from the
  cleared path is preregistered as EXPECTED here, not a failure);
  F7 missing mid-session constituent — validation V6 must FAIL (divergence
  likewise expected); F8 as-of mid-day — only completed bins emitted
  (divergence likewise expected). PASS on F1–F5 = byte-identical 4H output
  from the cleared path and from `resample_4h` on identical in-session
  inputs; PASS on F6–F8 = the cleared path fails/emits exactly as
  preregistered above.
- On PASS: adjudication records the precedence sentence and selects route
  (a)-pin or (b)-artifact for adoption work. On any FAIL: HOLD with the
  failing cell named; no in-run repair.

## Decisions that belong to adjudication / Mike (not engineering)

- D1: route selection (a) vs (b), after the proof.
- D2: the precedence sentence itself (construct_4h authoritative for TD
  receipts; fetch_4h = historical convention reference).
- D3: where Amendment v1 S2 split exclusion (bars + entries, D−1…D+1) lives
  in the TD pipeline — pre-construction on 1H or post-construction on 4H;
  S3 (recompute after exclusion, no imputation) interacts with the choice.
  Neither constructor implements S2 today; it is a dataset-assembly act.
- D4: whether the construct_4h standalone CLI bypass is disabled in any
  future adoption package.

## Searchable failure memory

- `CONSTRUCTOR_PRECEDENCE_EQUIVALENCE_UNPROVEN` — NEW (this task, B-1).
- `DIRECT_PMC_CLOSE_RESOLUTION_OUTSIDE_ARTIFACT_CONTRACT` — NEW (B-2).
- Standing context: `ORIGIN_START_DAY_ANCHOR_DRIFT` (2026-10-03 candle
  failure — the reason anchor semantics are proven, never assumed);
  `FOLD_DEV_PREFIX_SUFFIX_NOT_BOUND` (closed by Amendment v4 / -28);
  `SPLIT_EXCLUSION_PROTOCOL_DEFINITION_MISSING` (closed by Amendment v1
  replacement, -24).

## Scope guard restated

The 51-request FRESH manifest is a 20-symbol vendor SCREEN. The 51-symbol
(UX51) validation baseline dataset is a separate, larger acquisition that
has not been specified or run; exactly 1 TD credit has ever been spent
(the -18 `/api_usage` check). Nothing here authorizes acquisition,
construction, or performance work.

Elapsed: ~15 min of the ≤35 cap. Repair minutes: 0.
Prohibitions honored: no module/test execution (all files read as text;
hashes recomputed only), no installs/env changes, no market/vendor/helper/
API/model calls beyond the read-only public GitHub spec fetch, no credits,
no SPT-08, no backtests/performance, no holdout access, no ledger/state/
production/trading changes, no Issue #9 work, V5.4 harness untouched.
