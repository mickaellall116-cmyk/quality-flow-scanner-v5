# TEST_EVIDENCE — shadow successor candidate (2026-10-22)

Environment: pinned venv (CPython 3.12.3 / pandas 2.2.3), runs
under `unshare -n` (offline). The live adapter was never
constructed against the network; its first use sits behind the
authorization refusal proven by J1. All fixtures synthetic.

## Acceptance suite — tests/test_shadow_signal_observer.py

**24/24 checks passed** (run twice, identical), mapped to the
assignment's acceptance criteria:

- (A) A1 recorded once · A2 record labels (cohort
  SHADOW_OBSERVATION, counts_as_trade false, shadow id, T0
  carried on the record) · A3 idempotent re-presentation
- (B) B1 pre-T0 signal refused as PRELAUNCH_SIGNAL, refusal
  appended, nothing recorded
- (C) C1 market frame unavailable → DEGRADED, zero signals ·
  C2 health keys absent → DEGRADED (fail-closed defaults; the
  B2 regression guard)
- (D) D1 incomplete scan → DEGRADED · D2 partial bar refused
  PARTIAL_BAR_NOT_CLOSED · D3 naive stamps refused
  TZ_NAIVE_OR_UNPARSEABLE_STAMPS · D4 off-grid start refused
  OFF_GRID_BAR_START · D5 a valid signal in the same batch is
  still recorded
- (E) E1 restart rebuilds the seen-set from the log (no
  duplicate) · E2 torn final line truncated as never-committed,
  recovery logged, the torn signal then recorded exactly once ·
  E3 log fully parseable after recovery
- (F) F1 sandbox production files (PAUSE_NEW_ENTRIES sentinel +
  state) byte-identical after cycles · F2 the observer's writes
  are exactly {launch_manifest.json, shadow_log.jsonl} inside
  its root
- Frozen T0: G1 reopening with a different T0 refuses · G2 same
  T0 reopens
- Pins & gate: H1 pins pass on a matching stack · H2 tampered
  module refused · J1 live mode refuses without
  LAUNCH_AUTHORIZED.json BEFORE any fetch (fetch counter 0, no
  files written) · J2 observe_once performs exactly one fetch,
  after pin verification
- Isolation: I1 importing core + runner in a subprocess loads
  zero production modules
- Entrypoint: K1 `main()` dry-run end-to-end in a subprocess
  against the real repo's pins (read-only hash verification) —
  one signal recorded in a temp shadow root

## Regression — the -80 record stands

The -80 safety suite (safety_checks/run_safety_checks.py) re-run
against its pristine committed package (7d7d6b7): **S1–S6 ALL
PASS**. This successor does not alter that record; it addresses
the deployability properties the -80 suite never claimed.

## One assertion fix during build (disclosed)

F2 initially compared the shadow-root file list in sorted order
and failed on ordering alone; the write SET was already exactly
the two expected files. The assertion now compares sets. No
module code changed after the first full run except this test
assertion.
