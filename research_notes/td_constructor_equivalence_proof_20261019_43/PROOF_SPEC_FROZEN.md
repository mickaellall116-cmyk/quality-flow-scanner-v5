# QF-TD-CONSTRUCTOR-EQUIVALENCE-PROOF-20261019-43 r1 — FROZEN PROOF SPEC

Frozen BEFORE the single offline attempt. Spec authority: Issue #1 comment
`6281741142`. Budget ≤45 min, ONE attempt, first material failure stops,
repair minutes = 0. No exploratory fixtures, parameter changes, reruns, or
post-failure repair.

## Immutable inputs (hash-gated before execution; any mismatch = HOLD, no run)

- `construct_4h.py` `d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd`
- `pilot_build.py` `257d5bb99bcbae50442491b71429abb6b37b8c5cbcd1e4bf93b6010ad9e5a508`
- `validate_input.py` `1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58`
- `fetch_4h.py` `2a4994a26dbb98e244a14173a06697476835206c3d8d268ad21900dd43e0cbeb`
- XNYS artifact `XNYS_SESSION_SCHEDULE_V2.json`
  `3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88` @ commit `9c62e255`
- TD lock `integration_requirements.lock`
  `08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068`
- Wheelhouse manifest `SHA256_MANIFEST.txt`
  `210b8273a15cc7317b4a8029198f8d6e1401c1e375acdbe7f8602167c13e815b` (11/11 wheels verify)
- CPython 3.12.3, pandas_market_calendars 4.5.1 (pinned NL451 wheelhouse env,
  rebuilt offline `--no-index --require-hashes` if absent; freeze must equal
  the TD lock byte-for-byte; network probes inside the namespace must fail).

## Cleared route (as executed)

pilot_build.py's steps, in-process, using the identical pinned modules:
(1) `verify_sources.py` subprocess, exit 0 required (run before every
fixture's cleared-route invocation, as pilot_build does);
(2) `validate_input.validate(df, symbol, window_start, window_end, None,
as_of=as_of)`;
(3) `construct_4h(df_capitalized, symbol, as_of=as_of,
validated_ends=<validator canonical ends, as pilot_build carries them>)`.
CSV serialization is skipped so both routes consume identical in-memory
inputs; pilot_build.py itself is hash-gated above.

## Reference route (isolated)

`resample_4h` + its `AGG` are extracted TEXTUALLY from the hash-verified
`fetch_4h.py` bytes (AST source segments) and exec'd with pandas in scope.
Module import of fetch_4h.py is impossible in the pinned env (it imports
yfinance, deliberately absent from the offline wheelhouse). The executed
source text is hashed and recorded in the results. This is the "isolated
resample_4h reference" of the spec.

## Synthetic bar generator (deterministic, no market data)

For the k-th bar of a fixture in chronological order (k from 0):
Open = 100+k, High = Open+2, Low = Open−2, Close = Open+1,
Volume = 10000+100·k. Bar starts = the real session grid from the pinned
validator (`xnys_schedule` + `expected_1h_starts`) for the fixture's
sessions. Canonical serialization of an output frame:
`{index_iso}|{Open!r}|{High!r}|{Low!r}|{Close!r}|{Volume!r}` per row
(floats via repr), rows joined by `\n`; byte-identity = string equality
(sha256 recorded).

## E1 — calendar equivalence (fixed family, 761 dates)

Coverage = every calendar date in the closed interval
[2024-09-16, 2026-10-16] = 761 dates. Artifact must list exactly 524
sessions; the remaining 237 are non-session dates.
- Session date: `session_close_et(date)` must equal the artifact close
  (artifact `close` wall time localized to America/New_York).
- Non-session date: `session_close_et(date)` must raise ValueError.
- PASS requires 761/761 (524 close matches + 237 closed-date matches).
- Failure keys: `E1_ARTIFACT_SHAPE`, `E1_SESSION_RAISED`,
  `E1_CLOSE_MISMATCH`, `E1_CLOSED_DATE_NO_RAISE`,
  `E1_CLOSED_DATE_WRONG_EXCEPTION`.

## E2 — constructor behavior (fixed family, 8 synthetic fixtures)

- F1 regular day 2025-01-08, all 7 constituents, as_of 16:00 ET.
  PASS = cleared and reference outputs byte-identical (2 bars).
- F2 early close 2024-11-29 (13:00), 4 constituents, as_of 13:00 ET.
  PASS = byte-identical (1 bar).
- F3 DST-spring week: window 2025-03-07 → 2025-03-14 (sessions Mar 7 EST,
  Mar 10–14 EDT), as_of 2025-03-14 16:00 ET. PASS = byte-identical.
- F4 DST-fall week: window 2025-10-31 → 2025-11-07 (sessions Oct 31 EDT,
  Nov 3–7 EST), as_of 2025-11-07 16:00 ET. PASS = byte-identical.
- F5 overlapping identical bars under two window lengths: bars for
  2025-01-06/07/08 generated once; WIDE window = all three days, NARROW
  window = 2025-01-07 only (identical bar subset), as_of 2025-01-08 16:00
  ET (WIDE) / 2025-01-07 16:00 ET (NARROW). PASS = cleared(WIDE) ==
  reference(WIDE), cleared(NARROW) == reference(NARROW), and each route's
  WIDE output restricted to 2025-01-07 == its NARROW output, all
  byte-identical.
- F6 closed day with stray bars: window 2025-01-09 (Carter National Day of
  Mourning closure) with stray bars at 09:30 and 10:30, as_of 16:00 ET.
  PASS = cleared route raises the preregistered validator condition **V4**
  (bars present on exchange-closed day). Reference output recorded as
  expected divergence (not promoted, not a failure).
- F7 missing due constituent: 2025-01-08 with the 11:30 constituent
  omitted, as_of 16:00 ET. PASS = cleared route raises the preregistered
  validator condition **V6** (missing due 1H constituents). Reference
  output recorded as expected divergence.
- F8 mid-day as-of: 2025-01-08 constituents 09:30–13:30 (5 bars),
  as_of 14:30 ET. PASS = cleared route emits completed bins only: exactly
  one bar, the 09:30 bin, byte-equal to F1's 09:30 bar. Reference output
  recorded as expected divergence.
- Failure keys: `E2_F1_BYTE_IDENTICAL` … `E2_F5_BYTE_IDENTICAL`,
  `E2_F6_VALIDATOR_CONDITION`, `E2_F7_VALIDATOR_CONDITION`,
  `E2_F8_COMPLETED_BINS_ONLY`, `E2_CLEARED_ROUTE_ERROR` (unexpected
  exception on a fixture where the cleared route must succeed),
  `E2_SOURCE_VERIFY` (verify_sources non-zero).

Environment failure keys (stop before/without proof execution):
`HASH_GATE_<NAME>`, `ENV_BUILD`, `ENV_FREEZE_MISMATCH`,
`ENV_NETWORK_PROBE`.

## Terminal verdict (exactly one)

- `TD_CONSTRUCTOR_EQUIVALENCE_PROOF_PASS__AWAITING_ROUTE_ADJUDICATION`
- `TD_CONSTRUCTOR_EQUIVALENCE_PROOF_HOLD__<first-failure-key>`

A PASS does not itself adopt either route.
