# BOSWaves Correction Package C1 — FREEZE RECORD (v2)

Frozen: 2026-10-04T01:30:12.845317+00:00
Status: PROPOSED CORRECTION — for Claude's and Mike's review. NOT RUN. No verdict claimed.
Supersedes the v1 freeze (canonical-ticker-wins); see §1a.

## What this corrects (against validate_v3.py, the October run script)

1. **Ticker-rename duplicates (systematic):** 5 rename pairs double-represented 5
   securities. `universe_mapping.json` collapses 831 tickers -> 826 permanent
   security IDs.
1a. **Durable rule (Mike, 2026-10-03): canonical security identity, with
    date-appropriate ticker labels — not "newest ticker wins."** The mapping is
    identity-first: each security carries its ticker history with verified
    effective dates (KORS->CPRI 2019-01-02; BHGE->BKR 2019-10-18; JEC->J 2019-12-10;
    FLT->CPAY 2024-03-25; FISV->FI 2023-06-07 then FI->FISV 2025-11-11 on Nasdaq
    relisting). The admitted trade is labeled with the ticker in effect at its
    signal date — deterministic and order-independent. This resolves the FISV/FI
    review question: both files are byte-identical full-history backfills
    (4,463 bars, 2009-01-02 -> 2026-09-30), so direction never affected P&L;
    the round-trip history is now recorded explicitly.
2. **Dedup before portfolio admission:** caps (20 max, 5/sector, 10% heat) count
   security IDs; rename aliases collapse to one candidate per (signal_date,
   security); re-admission of a held security under any alias is blocked
   (`skipped_duplicate_security`), placed after the per-date collapse and before
   the cap checks.
3. **§7.7 coverage gate wired into verdict code:** `coverage_ok` computed from the
   coverage audit (`missing_no_file` empty = PASS). Non-empty -> verdict
   INCONCLUSIVE per §7.7 (not FAIL). Run blocked if the audit is skipped.
   Verdict precedence: coverage failure -> INCONCLUSIVE regardless of performance
   gates; performance-gate outcomes on partial data are still reported as facts.
4. **Unchanged:** all performance gates and thresholds (expectancy >0.15R @25bps,
   clustered |t|>2, Calmar >1.0, tail survivals, cluster floors), fill sequencing
   (§4B), cost legs, indicator parameters, universe criterion. Same research family;
   today's Calmar FAIL preserved as a reported fact. Coverage is reported as
   831 ticker entries AND 826 unique securities (coverage is per-file; dedup is
   portfolio-admission).

## Test evidence (run 2026-10-03, no full pipeline execution)

- Dedup: alias collapse order-independent; label follows signal date (KORS for
  2014, CPRI for 2020; FI for 2024, FISV for 2026); held-security re-admission
  blocked; heat-cap behavior preserved; cap constants 20/5/10% unchanged;
  security_id stamped on taken trades.
- Coverage gate: October audit (388 missing_no_file) -> INCONCLUSIVE; synthetic
  clean audit -> PASS; Calmar-FAIL + coverage-gap -> INCONCLUSIVE.

## SHA-256

- 0516872fcf36c38faef0349340f3bd7ccfdda1dd6725c89f3150e6c411e740e6  universe_mapping.json
- c37b3cdb1b885129e7147cd6ef3e64af7633396332f63464793f7f49e76e340a  coverage_gate_spec.md
- 04e842e90b543b38176ea0842c44f8297268c6ae63d943f91c8f0c3603cdc04a  validate_v3c1.py

## Review requested (updated)

1. ~~Is dedup-before-admission the right placement, and is canonical-wins the right tie-break?~~
   -> Superseded: identity-first + date-appropriate labels now implemented and tested.
2. Does the §7.7 operationalization match the protocol's letter (no invented thresholds)?
3. Any remaining defect before this is approved for the November full-831 run?

---
## v3 addendum — stable tie-break (2026-10-03, Claude's review)

Claude noted exact mom_score ties are EXPECTED for duplicate files (identical
prices -> identical momentum), not vanishingly unlikely — the v2 "first-wins"
rule left the retained record dependent on input (glob) ordering. Fixed:
on exact ties the lexicographically smallest raw ticker wins; the admitted
trade is still relabeled via ticker_at(), so the fix is pure determinism,
not strategy tuning. Unit-tested across all input permutations.

Claude's v2 review verdict (source-reviewed, no execution): Q1 superseded and
verified correctly implemented; Q2 yes; Q3 no remaining defect found.
Prerequisites: SOURCE-REVIEWED by Claude; execution verification pending
(November run must verify deduplication, exposure accounting, and
coverage-gate behavior end to end). Neither promotion verdict changes.

## SHA-256 (v3, supersedes v2 hashes)

- 0516872fcf36c38faef0349340f3bd7ccfdda1dd6725c89f3150e6c411e740e6  universe_mapping.json
- c37b3cdb1b885129e7147cd6ef3e64af7633396332f63464793f7f49e76e340a  coverage_gate_spec.md
- 6c4137d8ebb392c23a99a1eb3388810fd4d4695baadce7fd38e20295e9f75525  validate_v3c1.py
- f065a3d3ad8e45f79067f538a080ea1428191dbc8f05e829eefd15dfa705d232  ticker_boundary_fixtures.md

---
## v4 addendum — verification-driven fixes (2026-10-04, Mike's action request)

Mike authorized controlled-fixture verification against the frozen v3 code
("run we need to get back on track" — engineering tests + reversible fixes on
research code; NOT a strategy relaunch, no performance runs, no holdout).

Two code fixes resulted, both spec-to-code corrections, neither strategy tuning:

1. **Alphabetical tie-break on cross-security ranking ties** (protocol §2:
   "Exact ties: broken by symbol alphabetical ascending"). The ranking sort was
   `(signal_date, -mom_score)` with no alphabetical fallback, so exact ties
   resolved by input order (stable sort) rather than per the spec. Now
   `(signal_date, -mom_score, symbol)`. Only affects exact floating-point ties
   across different securities (vanishingly rare with real data); no impact on
   any computed result.

2. **`ticker_at()` fallback for unknown securities.** `sec_id()` maps unknown
   symbols to `SEC_<sym>`, but `ticker_at()` raised KeyError for them. Now
   returns the raw symbol — needed for synthetic fixture inputs and any
   out-of-mapping symbol.

Verification suite `run_verification_fixtures.py`: 61/61 pass against the
actual frozen code with synthetic inputs (no network/data/holdout):
  A. dedup — all 5 alias pairs x both arrival orders x exact ties x 20 random
     shuffles; held-alias block; 12 boundary dates; 831/826 counts.
  B. portfolio — staggered cohorts, heat/sector/position caps, exit-release,
     alphabetical tie-break (behavioral + source).
  C. fills — next-open entry, invalid gap entry, entry-day stop, gap-through
     active stop, stop-before-flip sequencing, hand-derived P&L at 4/25bps.
  D. coverage — INCONCLUSIVE precedence over FAIL, strict-> boundaries,
     hand-derived Calmar.

## SHA-256 (v4, supersedes v3 hashes)

- 0516872fcf36c38faef0349340f3bd7ccfdda1dd6725c89f3150e6c411e740e6  universe_mapping.json
- c37b3cdb1b885129e7147cd6ef3e64af7633396332f63464793f7f49e76e340a  coverage_gate_spec.md
- 3bb93b91699ec5be978e74df9cf2fdd6fbec07fd2378dcedcc501a579f39cc9a  validate_v3c1.py
- f065a3d3ad8e45f79067f538a080ea1428191dbc8f05e829eefd15dfa705d232  ticker_boundary_fixtures.md
- 18f6b593cdad8a768368a9507360f6d608f775c6dd03b8ce18395f41f6364196  run_verification_fixtures.py

---
## v5 addendum — ChatGPT's independent-execution findings (2026-10-04)

ChatGPT independently executed the v4 fixture suite: 61/61 passed. Additional
checks found one real defect and four test-coverage gaps; all addressed here.

**Real defect: tied-alias retained record was order-dependent (FIXED).**
The dedup tie-break compared the incoming raw `t["symbol"]` against
`prev["symbol"]` — but `prev` had already been relabeled via `ticker_at()`,
so the comparison was raw-vs-relabeled, not raw-vs-raw. Repro (ChatGPT):
tied FI/FISV candidates with marker payloads — input [FISV,FI] retained the
FISV record, input [FI,FISV] retained the FI record (displayed symbol and
security_id identical either way). Fix: keep `_raw_symbol` separately during
the collapse, compare raw-to-raw, relabel via `ticker_at()` only AFTER the
collapse loop, and drop the raw key from the final record. Full-record
signatures now identical across all input permutations.

**Test-coverage corrections (all in run_verification_fixtures.py):**
- A1: compares FULL retained-record signatures (incl. marker payloads) across
  20 random shuffles + both orders per pair, not just displayed symbol.
- B5: uses binding-cap contenders (11 tied candidates, heat binds at 10) and
  inspects the engine's actual admission order — no re-sorting in the test.
- B1: documents that the 20-position cap is UNREACHABLE under the frozen 1%
  risk sizing (heat ~= n_open * 1% always binds first at 10). The cap remains
  as defense-in-depth; this is a protocol observation, not a code change.
- D: tests the REAL production functions — `compute_verdict`,
  `max_drawdown`, `annualized_return`, `calmar_ratio` — extracted from main()
  with behavior-identical refactoring. The local `verdict_for` copy is gone.
- C1: asserts the expected trade unconditionally (was len>=0 with conditional
  fill check).

**Also published (were local-only):** `scanner_rules.py` with the cutoff +
early-close fixes (commit b3a7251) and `tests/test_scanner_rules.py` with
TestRowCompletion (commit 6523e33) — ChatGPT's "not available at path" gap.

Suite: 68/68 pass (builder). ChatGPT's 61/61 independent run was on v4;
independent re-execution of v5 pending.

## SHA-256 (v5, supersedes v4 hashes)

- 0516872fcf36c38faef0349340f3bd7ccfdda1dd6725c89f3150e6c411e740e6  universe_mapping.json
- c37b3cdb1b885129e7147cd6ef3e64af7633396332f63464793f7f49e76e340a  coverage_gate_spec.md
- 67e1a6d69a5fefc34efc853efa1299831f8fae58c209324ff8baba735033bbdd  validate_v3c1.py
- f065a3d3ad8e45f79067f538a080ea1428191dbc8f05e829eefd15dfa705d232  ticker_boundary_fixtures.md
- e4cc0a0478759d83acf71bb0fe8455a1f7d2ce7627558114764073c059b7874c  run_verification_fixtures.py
