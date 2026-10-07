# Pilot Harness — Isolated Offline 4H Construction + Validation

**Version:** v1 (2026-10-07)
**Status:** OFFLINE/SYNTHETIC ONLY. No vendor API calls. No production changes.
**Purpose:** Executable prerequisite for the Twelve Data pilot (ChatGPT 6037625281,
blocker 1). Publishes the minimal isolated acquisition/construction harness,
exact dependency lock, and runnable commands BEFORE any vendor call.

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

3. **Credit-weighted rate limiter** (`rate_limiter.py`) — design for the
   8 credits/min, 800/day free tier. Weighted token bucket; 8-second spacing
   alone is insufficient for repeated 2-credit requests.

4. **Synthetic 1H generator + test suite** (`synthetic_data.py`, `tests/`) —
   covers regular day, early-close day, full holiday, DST transition
   (spring-forward and fall-back), and partial-bar cases.

## Quick start

```bash
cd research_notes/pilot_harness

# 1. Create the pinned environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Verify pinned archival sources (fail-closed: abort if mismatch)
python3 verify_sources.py

# 3. Run the synthetic test suite
python3 -m pytest tests/ -v
# or without pytest:
python3 tests/run_all.py

# 4. Construct 4H bars from synthetic 1H (example)
python3 construct_4h.py --input tests/fixtures/synthetic_1h_regular.csv \
    --symbol AAPL --out /tmp/aapl_4h.csv

# 5. Validate 1H input before construction (fail-closed)
python3 validate_input.py --input tests/fixtures/synthetic_1h_earlyclose.csv \
    --symbol AAPL --calendar xnys
```

## File map

| File | Purpose |
|------|---------|
| `construct_4h.py` | Deterministic 1H→4H session construction |
| `validate_input.py` | Fail-closed input validator (blocker 3) |
| `rate_limiter.py` | Credit-weighted limiter design (blocker 5) |
| `synthetic_data.py` | Synthetic 1H bar generator |
| `verify_sources.py` | Archival SHA-256 verification (fail-closed) |
| `warmup_math.py` | EMA200 convergence analysis (blocker 2) |
| `requirements.txt` | Pinned dependencies |
| `tests/` | Synthetic test suite + fixtures |

## Design constraints

- **No vendor calls.** All inputs are synthetic or local fixtures.
- **No archival modification.** The harness replicates logic; it never edits
  `archival_sources_v1/`.
- **Fail-closed.** Any validation failure aborts; nothing is silently
  corrected or defaulted.
- **Deterministic.** Same input → byte-identical output. No randomness
  except seeded synthetic generation (seed pinned in code).
