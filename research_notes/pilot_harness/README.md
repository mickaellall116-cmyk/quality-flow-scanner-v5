# Pilot Harness — Isolated Offline 4H Construction + Validation

**Version:** v3 (2026-10-07) — bounded repair per ChatGPT 6039806101
**Status:** OFFLINE/SYNTHETIC ONLY. No vendor API calls. No production changes.
**Purpose:** Executable prerequisite for the Twelve Data pilot (ChatGPT 6037625281,
blocker 1). Publishes the minimal isolated acquisition/construction harness,
exact dependency lock, and runnable commands BEFORE any vendor call.

## The cleared entrypoint

**`pilot_build.py` is the ONLY cleared path from 1H input to 4H output.**
It enforces, in order, with no bypass:

1. Source verification: pinned archival SHAs, fail-closed. UNCONDITIONAL —
   there is no flag to omit (ChatGPT 6039806101, finding 3).
2. Request-window validation: expected-session inventory over the whole
   window, interval-end contract, OHLCV schema, and MANDATORY tz-aware
   `as_of` causal cutoff (ChatGPT 6039806101, finding 1). Expected
   constituents are those whose documented interval end is <= as_of; any
   supplied bar with start/end after as_of is REJECTED (V11) — future data
   is never silently discarded. The current open session may be causally
   partial; sessions complete before as_of must be fully present; verified
   closed days must have zero bars.
3. Construction with as-of causal cutoff: constituent end <= as-of, only
   completed bins emitted. No 16:00 fallback, no silent localization.

```bash
python3 pilot_build.py --input 1h.csv --symbol AAPL \
    --window-start 2026-09-08 --window-end 2026-09-08 \
    --as-of 2026-09-08T16:00:00-04:00 \
    --out /tmp/aapl_4h.csv
```

Calling `construct_4h.py` or `validate_input.py` directly bypasses the
mandatory chain and is NOT the cleared path.

## What this is

A standalone, dependency-pinned implementation of:

1. **Deterministic 1H → 4H session construction** (`construct_4h.py`) —
   replicates the archival `resample_closed_4h_session_anchored` binning logic
   (explicit session bins from local time, never `origin='start_day'`).
   Reference: archival `scanner_rules.py`
   SHA-256 `7db282ddfc150c9e9aec7d8f1f10f439ce7e296da2d69da38f97ed8cbec70cac`.

2. **Fail-closed input validator** (`validate_input.py`) — validates interval
   ends, closed-day calendar status, rejects boundary straddles, verifies
   complete constituents BEFORE aggregation. Catches what the archival
   constructor does not (it groups by start timestamp and falls back unknown
   dates to 16:00).

3. **Credit-weighted rolling-window limiter** (`rate_limiter.py`) — v3
   replaces the v2 design (whose window ledger was memory-only, whose
   day-boundary clock misused monotonic time, and whose JSON writes were
   neither atomic nor locked — ChatGPT 6039806101, finding 2). v3 persists
   the full (epoch-wall-time, weight) window ledger, uses epoch wall time
   with an injectable clock, atomic temp+rename writes, and interprocess
   fcntl locking. Rolling 60s window, persistent daily accounting,
   oversized-request refusal, deterministic UTC day rollover.

4. **Synthetic 1H generator + test suite** (`synthetic_data.py`, `tests/`) —
   covers regular day, early-close day, full holiday, DST transition
   (spring-forward and fall-back), partial-bar cases, causally-partial
   as-of captures (10:00/10:30/13:30/close boundaries), plus regression
   fixtures for all ChatGPT counterexamples. **35/35 tests pass**
   (`tests/synthetic_test_output.txt`).

## Quick start

```bash
cd research_notes/pilot_harness

# 1. Create the pinned environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Run the synthetic + regression test suite (no pytest needed)
python3 tests/run_all.py

# 3. Cleared entrypoint: validate + construct a regular day
python3 pilot_build.py --input tests/fixtures/synth_regular.csv \
    --symbol AAPL --window-start 2026-09-08 --window-end 2026-09-08 \
    --as-of 2026-09-08T16:00:00-04:00 \
    --out /tmp/aapl_4h.csv

# 4. Cleared entrypoint: July 3 holiday → 0 bars (verified closed)
python3 pilot_build.py --input tests/fixtures/synth_holiday.csv \
    --symbol AAPL --window-start 2026-07-03 --window-end 2026-07-03 \
    --as-of 2026-07-03T16:00:00-04:00 \
    --out /tmp/aapl_holiday_4h.csv

# 5. Causally-partial capture: as-of 10:00, empty input → PASS, 0 bins
python3 pilot_build.py --input tests/fixtures/synth_holiday.csv \
    --symbol AAPL --window-start 2026-09-08 --window-end 2026-09-08 \
    --as-of 2026-09-08T10:00:00-04:00 \
    --out /tmp/aapl_partial_4h.csv
```

## File map

| File | Purpose |
|------|---------|
| `pilot_build.py` | **Cleared entrypoint**: verify (unconditional) → validate (as_of) → construct (no bypass) |
| `construct_4h.py` | Deterministic 1H→4H session construction (v2: no fallback, as-of) |
| `validate_input.py` | Fail-closed input validator v2 (window, interval-end, OHLCV, V11 causal) |
| `rate_limiter.py` | Rolling-window credit limiter v3 (persisted window, wall clock, fcntl-locked) |
| `synthetic_data.py` | Synthetic 1H bar generator (10 cases incl. regression fixtures) |
| `verify_sources.py` | Archival SHA-256 verification (fail-closed) |
| `warmup_math.py` | EMA200 convergence analysis (blocker 2) |
| `requirements.txt` | Pinned dependencies |
| `tests/` | Synthetic + regression suite (T01–T13, R01–R08) + fixtures |

## Design constraints

- **No vendor calls.** All inputs are synthetic or local fixtures.
- **No archival modification.** The harness replicates logic; it never edits
  `archival_sources_v1/`.
- **Fail-closed.** Any validation failure aborts; nothing is silently
  corrected or defaulted.
- **Deterministic.** Same input → byte-identical output. No randomness
  except seeded synthetic generation (seed pinned in code).
