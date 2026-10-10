# Twelve Data Stage-0 Addendum — 2026-10-10

**Authorization:** Mike, 2026-10-10 direct (Slack, in response to his own status escalation): "Ok so run it."
Supersedes the relayed-clearance dispute (Issue #1 comments 6052603402 / 6055070076, held per Mike-decides until his direct word).

## Frozen scope

- Exactly **two** `/time_series` requests, AAPL only: `interval=1h` + diagnostic `interval=4h`
- Frozen window: **2026-09-08 .. 2026-10-06**, `timezone=America/New_York`, `outputsize=5000`, `order=ASC`
- **2 credits total. Zero retries. Zero extra endpoints. Zero metadata calls.**
- Any failure = blocker report, exit non-zero. No retry, no expansion.

## Prerequisites verified pre-execution

| Prereq | Status |
|---|---|
| Credential | `custom.twelvedata` via authd surrogate; raw key never handled, logged, or persisted |
| Shared limiter | v4 `RollingCreditLimiter` (8/min, 800/day), persisted ledger `research_notes/pilot_harness/credit_ledger.json`, fail-closed |
| Redaction | Sanitized logging; error strings carry no key material |
| Raw-data handling | Snapshots private in `research_notes/twelve_data_stage0/snapshots/` (git-ignored); only manifest committed |

## What Stage-0 proves

Smoke test only: the API key works, `/time_series` returns well-formed bars for the frozen window,
and our limiter/redaction/snapshot plumbing holds. It does NOT prove data quality —
that is the 20-symbol pilot's job (separately gated; ChatGPT spec clearance P4 still pending for it).

## Artifacts

- `stage0_runner.py` — the frozen wrapper (this addendum + runner = the pinned Stage-0 package)
- `snapshots/aapl_1h_2026-09-08_2026-10-06.json` — private, git-ignored
- `snapshots/aapl_4h_2026-09-08_2026-10-06.json` — private, git-ignored
- `stage0_manifest.json` — public manifest (hashes, sanitized params, counts); committed
