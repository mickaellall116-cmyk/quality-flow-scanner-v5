# TD PROBE OFFLINE CLOSURE — task -67 r1 RESULT

Task: QF-TD-PROBE-OFFLINE-CLOSURE-20261021-67 r1
Spec: Issue #1 comment 6311907793 (independent adjudication of -66:
HOLD with three remaining fail-closed gaps; one successor-package
closure, new files only, -65/-66 preserved immutable, one
implementation/test attempt after precommit, ≤35 min).

## TERMINAL

TD_PROBE_OFFLINE_CLOSURE_HOLD__Q11_RECEIPT_TS_FUTURE

The single qualification attempt stopped at its FIRST failure
(case 11 of 38; Q01–Q10 passed). Per the task discipline there was
NO repair in-run and NO byte-identity repeat (a repeat is permitted
only after a passing first run). The failure is preserved below
exactly as observed.

## First failure (verbatim evidence)

Command: `python3 -W error tests_qualification.py`
Exit code: 1. Stderr: empty. Stdout: QUALIFICATION_RESULTS.json
(sha256 9241d02702aea7d29cf509d4f178cce66b198fa01089f388d903b4843eafc49a).

```
Q11_uniform_factor_pass — AssertionError: {'verdict': 'HOLD',
'hold_tag': 'RECEIPT_TS_FUTURE', 'detail': 'RECEIPT_TS_FUTURE:
receipt 1760000000000 > now 1700000000000', 'checks': {}}
```

Root cause (stated, not repaired): the carried-over synthetic
fixtures pin receipt timestamps at BASE_TS_MS = 1_760_000_000_000
(make_fixtures.py, inherited from -65/-66), while the harness clock
constant NOW_MS = 1_700_000_000_000 predates them. In -66 this was
invisible: `now_ms` was an optional analyzer argument the harness
never passed, so the future-receipt check never fired. Closure C-A
makes `now_ms` mandatory, the harness now passes NOW_MS, and the
mandatory RECEIPT_TS_FUTURE check (probe_analyzer.py, verify_receipt)
correctly refuses every fixture receipt as future-dated. The closure
machinery behaved as designed; the successor package's harness and
its inherited fixtures disagree about "now". Aligning them (harness
NOW_MS at/after the fixture base time, or fixture regeneration at a
consistent epoch) is a repair and therefore belongs to a successor
task, not this run.

## What was built (precommit be83d9c, before execution)

1. **Mandatory expectations — CLOSED in source** (`probe_analyzer.py`).
   `analyze_window` (L431) and `analyze_revision` (L492) take
   expected request IDs, symbol, interval, window, and `now_ms` as
   REQUIRED keyword arguments (no defaults). `_validate_expectations`
   (L99) raises EvidenceHold EXPECTATION_INVALID /
   EXPECTATION_AMBIGUOUS (blank/None IDs, symbol, interval;
   malformed or reversed window; non-integral or non-positive
   now_ms; duplicate expected IDs) before any receipt is read.
   `verify_receipt` (L183) and `parse_bars` (L233) take their
   expectations as mandatory keyword arguments and apply every
   check unconditionally. NOT exercised by the attempt: cases
   B01/B02 (which assert exactly this) sit after Q11 in run order
   and never ran.

2. **C5 structure-first — CLOSED in source** (`probe_analyzer.py`
   L492). `analyze_revision` parses and validates BOTH snapshots
   via `parse_bars` (status/meta, numeric shape, strictly ascending
   unique datetimes, window containment) BEFORE the byte-identical
   PASS branch; the diff branch reuses the parsed bars. NOT
   exercised: B03/B04/B05 never ran; Q15 (identical/different
   revision regression) also never ran.

3. **Usage execution-date binding — CLOSED in source**
   (`account_preflight.py`). `utc_date_string` (L70);
   `AccountPreflight.check` stamps `execution_date_utc` from the
   injected clock (L145); `DailyUsageSession._verify_cached`
   re-verifies endpoint params == USAGE_PARAMS (USAGE_CACHE_PARAMS,
   L232) and requires the stored execution date to equal the UTC
   dates of the receipt's own timestamps and today's UTC date per
   the session clock (USAGE_CACHE_DATE, L277–288), in addition to
   the inherited age/future checks — cross-midnight reuse refuses
   before data and usage transport. Vendor reset-zone semantics are
   recorded in the module docstring as an execution-day UNKNOWN,
   never inferred. Exercised partially: Q07 passed (fresh receipt
   carries a consistent execution_date_utc; same-day reuse served).
   NOT exercised: B06 (cross-midnight) and B07 (wrong endpoint)
   never ran.

4. **Malformed numerics -> HOLD — CLOSED in source**
   (`probe_analyzer.py`). `_decimal_field` (L136) requires every
   OHLC/volume field to be a Decimal-parseable string at parse
   time (SNAPSHOT_MALFORMED otherwise); the check-evaluation paths
   additionally convert ArithmeticError/ValueError/TypeError into
   HOLD NUMERIC_EVALUATION_ERROR. NOT exercised: B08 never ran.

Runner changes are provenance/wiring only: store marker
"td_probe_runner_candidate_67"; `temporal_gate.py` carried
unchanged apart from its header. New fixtures: byte-identical
revision pairs over meta-wrong / out-of-window / duplicate-bar
snapshots (base+revision receipts over the same body) and
malformed-numeric snapshots (close "not_a_number", volume "12x34").

## Qualification accounting

- Regression Q01–Q20: 10 run, 10 PASS, then stop (Q11 FAIL).
- Prior adversarial A01–A10: NOT RUN (0/10).
- New adversarial B01–B08: NOT RUN (0/8).
- Byte-identity repeat: NOT RUN (not permitted after a failure).
- Cases Q12–Q20, A01–A10, B01–B08: no outcome claimed, in either
  direction.

## Pins

- Precommit (source/manifest/fixtures/SHA manifest, before
  execution): be83d9c9422396dbeb23e86758f8db686e266aa1
- SHA256_MANIFEST.txt in the precommit covers 63 package files.
- Key sources (sha256): probe_analyzer.py ebea8272…,
  account_preflight.py aae93734…, probe_runner.py e486636f…,
  temporal_gate.py f882dd29…, tests_qualification.py 7565856a…,
  make_fixtures.py 28733bed…, probe_manifest.json 1bb86e17…

## Elapsed / repair

Elapsed ≈9 min of the ≤35 cap (spec fetch 08:57:51Z → result
commit). Repair minutes: 0 — no repair was attempted after the
first failure. One authoring correction was made BEFORE precommit
and is part of the single build, disclosed here: an `import
datetime` initially placed ahead of the `__future__` import in
account_preflight.py was moved into the import block.

## Attestation

Zero vendor/network/API/model calls beyond the read-only spec
fetch; zero credentials read or resolved; zero credits/spend;
synthetic data only; no real ADJ/S4/REV; no scheduling; no edits to
-65/-66/frozen/live paths (this package is new files only); no
adoption/integration; no S2 implementation or -61 rerun; no
performance, holdouts, production, deployment, entries, or trading.
REQ-S2 HOLD; entries PAUSED; live probe USER-GO HOLD — all
unchanged.
