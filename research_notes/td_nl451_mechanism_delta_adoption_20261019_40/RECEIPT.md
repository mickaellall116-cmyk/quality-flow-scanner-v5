# RECEIPT — QF-TD-NL451-MECHANISM-DELTA-ADOPTION-20261019-40 r1

- **Return verdict: `NL451_DELTA_PROOF_PASS__ADOPTION_CANDIDATE_AWAITING_REVIEW`**
- Spec: Issue #1 comment `6278932260` (read in full before execution). Cap ≤45 min, one clean attempt.
- Elapsed: ~13 min (2026-10-19T22:58:40Z start → ~23:12Z package complete). **Repair minutes: 0.** Attempts: exactly ONE probe invocation; zero repairs, retries, or re-runs.

## Hash gates (all verified BEFORE any execution — all MATCH)

| Source | Expected | Result |
|---|---|---|
| Collector `td_min_collector.py` @ ab254c3 | `b683d277…` | MATCH |
| NL451 candidate supplement | `9c712330…` | MATCH |
| Validator `validate_input.py` @ ab254c3 | `1b83cdcd…` | MATCH |
| TD lock `integration_requirements.lock` @ ab254c3 | `08b38cfa…` | MATCH |
| Pilot requirements @ ab254c3 | `812c526f…` | MATCH |
| Original supplement @ ab254c3 | `cccd5226…` | MATCH |
| Fixture suite @ ab254c3 | `3122bdfc…` | MATCH |
| NLQUAL manifest (20 entries) | `ce5ba84e…` | MATCH — 20/20 entries reproduce |
| Interpreter | CPython 3.12.3 | MATCH |

## Environment

The pre-existing NL451 environment (`/tmp/tdqual/venv`, Oct 16 rebuild) no longer exists (/tmp is ephemeral). Per spec step 2, ONE disposable environment was built **offline only** inside a `unshare -n` no-network namespace from the pinned 11-wheel local wheelhouse (`~/workspace/td_nl_wheelhouse_20261016/wheels`, manifest 11/11 verified), `pip install --no-index --require-hashes` (hashes in `requirements_hashes.txt`). Network probes inside the namespace all failed as required (socket `Errno 101`, DNS `Errno -3`, curl connect failure — see `env_build_output.txt`). Resulting freeze is **byte-identical to the TD lock** `08b38cfa…` (`env_freeze.txt`); PMC version probe = `4.5.1`; CPython 3.12.3. Env location (disposable): `/tmp/td40/venv`.

## P-family delta — single invocation, fixed order (2026-10-19T23:01:22Z–23:01:24Z, exit 0, stderr empty)

Executed against the REAL pinned `validate_input.xnys_schedule` (executed copy hash = `1b83cdcd…`) + real PMC 4.5.1. The prior 28-case NLQUAL matrix was NOT rerun.

| Check | Expectation | Observed | Result |
|---|---|---|---|
| P1 | 2025-01-08 regular 09:30–16:00 | 09:30–16:00 (-05:00) | PASS |
| P2 | 2025-01-09 closure → None | None (Carter closure) | PASS |
| P3 | 2024-11-29 early close 13:00 | 09:30–13:00 (-05:00) | PASS |
| P4 | 2025-07-03 early close 13:00 | 09:30–13:00 (-04:00) | PASS |
| P5 | 2025-01-11 weekend → None | None (Saturday) | PASS |
| P6 | 2025-03-10 DST-spring regular | 09:30–16:00 (-04:00) | PASS |
| P7 | 2025-11-03 DST-fall regular | 09:30–16:00 (-05:00) | PASS |
| P8 | record `get_calendar("XNYS")` class/name; P1–P7 through it | class `XNYS`, module `pandas_market_calendars.class_registry`, name `XNYS`; P1–P7 reproduced through the object: True | PASS |

**Total: 8/8 PASS** (fixed total 8). Full detail: `p_delta_results.json`, `probe_stdout.txt`, `probe_stderr.txt` (empty), probe script `p_delta_probe.py`.

## Adoption candidate

Created per spec step 4 (8/8 PASS): `ADOPTION_CANDIDATE_RECORD.md` in this package, binding the unchanged collector, the NL451 supplement, the validator, the lock, the prior 28-case NLQUAL proof, and this 8-case delta proof — byte copies included for collector/supplement/validator/lock. Status `AWAITING_INDEPENDENT_REVIEW`. No old bytes edited or superseded in place; nothing placed in any production/live path; nothing adopted, merged, or activated.

## Prohibitions — all honored

No TD/vendor/API/model calls; no credentials, credits, tokens, or spend; no market/OHLC/real-timestamp data (probes ran on committed primary-record calendar facts only); no SPT-08; no holdout; no performance/backtest/tuning; no production/trading/state/ledger mutation; no Issue #9 work; no network use beyond the read-only public spec fetch (environment built and probe run inside a no-network namespace); the paused V5.4 harness untouched (package delivered via temp worktree off `origin/main`; the main tree's pre-existing harness merge state was never disturbed).
