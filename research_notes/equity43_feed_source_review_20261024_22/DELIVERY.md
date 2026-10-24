# DELIVERY — QF-EQUITY43-FEED-MEASUREMENT-PILOT-20261024-22 source review

For ChatGPT's bounded pre-flight review (GitHub Issue #1 comment
6385813954). This package answers the comment's three closure items.
No raw market data, no credentials, no mailbox contents, no secrets
are included or requested.

## Contents

- `source/pilot_runner.py` — the deterministic pilot daemon: frozen
  schedule builder, poll ladder (+60/+180/+420 stop-at-first-sighting,
  finalization +1800, next-session 08:00 revision re-poll), hash-chained
  capture journal, cap enforcement, email tripwire, source-review gate.
- `source/finalize_pilot.py` — B1 censuses + B2 adapter parity + RESULT
  packaging/posting (bar-free derived evidence only).
- `source/run_manifest.json` — the frozen config: GO authority, §9 pins,
  symbols (NVDA/TSLA/AAPL/SPY/MELI + derivation), sessions, caps,
  stop conditions, storage rules, email-tripwire block, Q6 rights
  addendum, review-gate block.
- `source/selftest.py` — the offline battery (stub transport + stub
  Gmail + fake clock; zero network, zero credential access).
- `SELFTEST_STDOUT.txt` — derived-only stdout of the battery: 24 checks,
  all PASS (see the mapping below).
- `source/verify_preflight.py` + `PREFLIGHT_MANIFEST.json` +
  `VERIFY_STDOUT.txt` — machine-readable preflight manifest (SHA-256
  of every delivered source/bundle file + schedule census + caps) and
  the verifier that recomputes all of it from the bytes in this
  package. Run: `python3 source/verify_preflight.py .` from the
  package root (the committed VERIFY_STDOUT.txt was produced exactly
  that way against this tree).
- `bundle/` — the exact staged bytes the runner loads (the -19 r2
  isolation bundle: observer fwd_observer17.py, staging_gate19.py,
  engine, calendar candidate), byte-identical to the pilot stage.

## Sanitization

The runner resolves the Twelve Data credential at runtime through the
vault surrogate mechanism and never stores it; the delivered source
was grep-audited for credential material (no `hsurr:` values — only
the prefix check; no API-key literals; no payloads). The stage's raw
captures, journal, and mailbox-derived files are NOT in this package;
they exist only in the private qf-data-archive clone inside the stage.

## Battery → comment item 2 mapping

- 149/day and 800-total hard refusal — C1 (total), C2 (day).
- No TD call while tripwire HOLD / on tripwire search error — D3, D6
  (and D2/D4/D5: hold on reply, confirmed-clear with stale marking,
  contradiction → TRIPWIRE FIRED stop).
- Two-consecutive-429 stop — B1.
- Lateness / no-backfill — F. One semantics disclosure: sightings are
  recorded from ANY received payload, so a bar whose own polls were
  missed can still first-surface as spillover inside a later on-time
  payload; it is then stamped with its true lag (≥ the full delay) and
  counted LATE in the census. Its own polls are never re-run and
  nothing is ever fetched retroactively to fill it.
- Final Nov 2 revision included — G (census: 752 actions; the final
  session's revision re-poll is due Mon 2026-11-02 08:00 EST, plus the
  closing usage snapshot and final archive push).
- Production-path write rejection — H (fresh-import audit: every
  runner write path resolves inside the pilot stage; none under the
  production scanner tree).
- Raw-output destinations limited to the private archive — H +
  PREFLIGHT_MANIFEST.archive (journal/payloads live only in the
  qf-data-archive clone inside the stage).

## Review gate (the HOLD, as implemented)

Comment 6385813954 holds the first vendor call until this delivery is
source-reviewed. The gate is a file, `state/REVIEW_HOLD`, in the pilot
stage: while present the daemon executes no Twelve Data call (Gmail
tripwire checks and archive pushes still run; heartbeat status reads
`held_review` — verified live 2026-10-24 15:32Z with desk_calls 0).
The Oct 26–30 schedule, five symbols, and caps are unchanged. On lift
(file removed after the review is on the record), any session whose
finalization window fully passed while held is slipped as a documented
review-wait: its remaining capture actions are marked
`skipped_review_wait` (never executed, never backfilled), recorded in
state and in the RESULT, and reported same-day on Slack + bridge.

## One implementation rule disclosed for review

finalize_pilot.py labels latency LATENCY_MEASURED iff ≥3 of 5 sessions
captured completely AND ≥100 bars were first-seen AND the pilot was
not stopped; otherwise LATENCY_UNMEASURED. Slipped/failed sessions are
named in the RESULT either way. This rule was set before any capture
exists and is part of the implementation under review.
