# TEST REPORT — V5.4 forward-test harness network-timeout hardening

**Date:** 2026-09-28
**Scope:** lab copy ONLY — `/tmp/harness_hardening/v54_forward_harness.py`.
The live file `~/workspace/quality-flow-scanner-v5/v54_forward_harness.py`
was not edited, and nothing was deployed.
**Test file:** `/tmp/harness_hardening/test_harness_hardening.py`
**Run:** `python3 test_harness_hardening.py` → **90 passed, 0 failed** (no network used).

## What was changed (infrastructure only — zero strategy changes)

New code in the lab copy (~430 added lines, all in clearly-marked sections):

1. **Guarded vendor calls** — `hardened_call()` wraps every provider fetch
   with a 45 s request deadline (daemon-thread watchdog, so a hung
   `yfinance` call can't wedge the cycle), at most **one** bounded retry
   for transient faults (timeout / 5xx), `Retry-After` honored when present.
2. **429 handling** — an HTTP 429 without a usable `Retry-After` trips a
   **cycle-global** rate-limit flag; all further vendor requests in that
   cycle are refused immediately instead of retry-storming.
3. **No partial-universe entries** — `ProviderHealth` tracks every expected
   symbol (full 250-symbol frozen universe + market symbols). Any expected
   symbol lacking fresh primary data (or a global 429) sets the cycle
   `DEGRADED` and **suppresses all new-signal staging and pending-entry
   fills** for that cycle. An unknown symbol is never reinterpreted as
   "no signal".
4. **Exit handling on data gaps** — open positions keep processing on valid
   data; missing/malformed data for an open symbol emits
   `exit_data_deferred` (logged + preserved in state), never assumes or
   invents an exit. On recovery, every unprocessed bar is walked
   **chronologically** and the outage is recorded in the audit log
   (`data_outage_recovered` with bar counts).
5. **Cycle budget** — 10-minute wall-clock ceiling; if exhausted before
   staging, no new signals are staged.
6. **Coverage as first-class output** — every cycle summary carries a
   `coverage` block (fresh/degraded symbols, open-position data gaps,
   unresolved security events, global provider status, retry counts,
   entry-suppression reason). A degraded cycle is **never** labeled
   "NO SIGNALS".
7. **Fail-closed delisting ambiguity** — "possibly delisted" / ambiguous
   corporate-action warnings become `unresolved_security_event`: the symbol
   is never removed, no −0R close is synthesized, entries are suppressed.
8. **Atomic writes** — snapshots, observer export, heartbeat, and the new
   `last_cycle_summary.json` use temp-file + atomic replace; the summary is
   written in a `finally` path so a crash can never look like a clean cycle.
9. **Patch hygiene** — the download wrappers patch `eng.m53` attributes
   in-process for one cycle only and are restored in `finally`; the FVG
   sidecar got its own 120 s deadline; confirmation/premarket aux calls are
   tracked but never gate decisions.

## Fault-injection results (all synthetic, hermetic)

| Fault | Result |
|---|---|
| Hung vendor call (30 s sleep, 1 s test deadline) | Cut off, 1 retry, `timeout`, DEGRADED, entries suppressed |
| HTTP 429, no Retry-After | `RateLimited`, global flag trips, **zero** further vendor requests attempted |
| HTTP 429 with Retry-After: 0 | one retry, success, no global flag |
| 503 then success | exactly 2 attempts, success |
| Persistent 500 | gives up after 1 retry, `transient_error` |
| Empty frame / None | `empty_frame`, deferred, DEGRADED |
| Non-datetime / NaT / non-monotonic index | `malformed_timestamps`, deferred |
| Missing OHLC column | `malformed_frame`, deferred |
| One missing universe symbol | new entries suppressed cycle-wide; healthy symbol's open position still advanced |
| One missing open-position symbol | `exit_data_deferred`; no bars invented; `last_processed_bar` untouched; position kept open; outage preserved in state |
| Outage → recovery | all 14 missed bars processed **in chronological order**; `data_outage_recovered` audit event with bar count; outage cleared |
| Possibly-delisted symbol | `unresolved_security_event`; suppressed, deferred, never removed, no −0R close |
| Global rate limit | no vendor requests attempted, DEGRADED |
| Budget exhausted | no signal staging, DEGRADED |
| Healthy cycle | HEALTHY, signal staged → pending → opened, coverage `ok` |
| Replay path (`provider=None`) | unchanged pre-hardening behavior |
| Crash path | summary artifact always written; never raises |

## Immutability proof

`test_strategy_files_untouched` hashes the 8 live strategy files
(`masterscanner_api.py`, `v54_engine.py`, `v54_rules.py`,
`scanner_rules.py`, `v54_exit_tracker.py`, `v54_universe_x2.py`,
`hybrid_exit_test.py`, `v54_forward_log.py`) **before and after**
importing the hardened copy and running hardened cycles through it:
byte-identical. `eng.m53.download_data` is verified restored after the
patch context exits.

## Caveats / open items for the parent

- The daemon-thread watchdog **abandons** a hung vendor thread on timeout;
  it cannot be killed (documented in code). Abandoned threads are daemonic
  and never block process exit.
- Thin-but-valid history is *not* flagged malformed — the frozen engine
  decides what is classifiable (deliberate, per spec).
- A market-data gap never defers exits (the frozen exit path tolerates a
  missing market frame, same as the old code); it is recorded in coverage.
- The 10-minute cycle deadline is wall-clock, not per-symbol; a pathological
  cycle could still run long *within* one 45 s request + one retry.
- `run_once()` was **not** executed (it writes to the live
  `forward_test/` tree and publishes); only `run_cycle()` and the
  primitives were exercised. A live dry-run remains untested by design.

## 2026-09-28 — implementation-audit fixes (ChatGPT review 17:42Z)

**Fix A — watchdog timeout is now non-retriable.** `_call_with_deadline`
returns a distinct `_WatchdogTimeout` when the daemon thread is still alive
at the deadline (the vendor call may still be in flight and cannot be
killed). `hardened_call` never retries a `_WatchdogTimeout` — a retry would
put two live requests for the same symbol on the wire and amplify Yahoo
rate limiting. Retries remain allowed only for transient failures that
actually returned or raised (received 5xx, raised connection error), at
most one bounded retry. New synthetic test
`test_watchdog_timeout_non_retriable` proves the watchdog path makes
exactly 1 vendor invocation (stub blocks past a 0.5s deadline; invocation
counter asserted == 1; no retry counted; symbol degraded; entries
suppressed). Companion test `test_raised_transient_still_retries_once`
proves a genuinely-raised transient still gets its single retry.

**Fix B — permanent provenance.** The exact fault-test source is committed
at `research_notes/harness_hardening/test_fault_injection.py`; the
machine-readable run artifact
`research_notes/harness_hardening/test_results.json` records per-test
status/duration, environment (Python, platform, UTC time, network_used:
false), the SHA-256 of the harness file under test, and the SHA-256 of the
test source. Tests remain non-runtime/non-deployed.

**Final suite: 23 test functions, 94 checks, 23 passed, 0 failed.**
