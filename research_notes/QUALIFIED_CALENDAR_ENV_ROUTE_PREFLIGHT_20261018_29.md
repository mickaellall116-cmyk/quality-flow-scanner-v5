# QF-QUALIFIED-CALENDAR-ENV-ROUTE-PREFLIGHT-20261018-29 r1

Spec: GitHub Issue #1 comment `6257423673` (accepts -28 as
`FOLD_CONSUMER_CONTRACT_ACCEPTED__REAL_CALENDAR_AND_TIMESTAMPS_UNQUALIFIED`,
dispatches this preflight). OFFLINE / READ-ONLY inventory and static
analysis only. One pass, no repair/rerun. Nothing imported, installed, or
executed from any candidate distribution; wheel identity was read
statically (file hashes + `.dist-info/METADATA` / `RECORD` as zip
members). Elapsed ~11 min of the ≤25 hard cap.

## Verdict

**`ROUTE_A_READY__COMPLETE_HASH_PINNED_OFFLINE_CLOSURE_EXISTS`** — the
spec's step-6 negative return (`NO_REPRODUCIBLE_OFFLINE_CALENDAR_ENV`)
does NOT apply: a complete closure already exists locally, so this
package includes the proposed hash-lock and the isolated future
execution plan. No real schedule exists yet and none was generated;
the calendar artifact and qualified timestamps remain UNQUALIFIED
until a future authorized task runs the plan and the qualification
gate below passes.

## The route (summary)

- **Environment identity:** CPython 3.12.3, linux x86_64, glibc 2.39.
  Target environment = the accepted NL lock, sha256
  `08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068`
  (committed copies: `td_nl_env_rebuild_evidence_20261016/lock_copy.txt`,
  `pip_freeze.txt`; `td_p2_spot_v2_derivation_candidate_evidence_20261015/env_rebuild_freeze.txt`).
- **Wheel closure:** the persistent wheelhouse
  `~/workspace/td_nl_wheelhouse_20261016/wheels` — 11/11 wheels, manifest
  sha256 `210b8273a15cc7317b4a8029198f8d6e1401c1e375acdbe7f8602167c13e815b`,
  re-verified `sha256sum -c` 11/11 OK in this preflight. It holds BOTH
  calendar entry points — `pandas_market_calendars` 4.5.1
  (`7b4f3478…`) and `exchange_calendars` 4.13.2 (`fc5a2ad0…`) — plus
  pandas 2.2.3, numpy 1.26.4, python-dateutil 2.9.0, pytz 2024.2,
  tzdata 2026.5, pyluach 2.3.0, toolz 1.2.0, korean_lunar_calendar
  0.4.0, six 1.17.0 (full per-wheel METADATA/RECORD inventory in
  `INVENTORY.json`).
- **Closure proof:** every runtime (non-extra) `Requires-Dist` edge of
  both calendar packages resolves inside the set for this
  interpreter/platform, including the two exact-floor edges
  (numpy ≥1.26.4 → 1.26.4; pyluach ≥2.3.0 → 2.3.0). Platform tags match
  (cp312 manylinux_2_17 x86_64; rest none-any). This same wheel set was
  installed in isolation on 2026-10-16 and froze byte-identical to the
  lock — the rebuild verdict was PASS — so Route A is not merely
  present, it is previously exercised.
- **System site-packages are NOT a route:** pandas 2.1.4+dfsg
  (Debian-patched), numpy 1.26.4, dateutil 2.8.2, pytz 2024.1, and no
  calendar packages or tzdata at all — mixed provenance, unpinned.
  Recorded in the inventory as UNQUALIFIED; never proposed.

## Route matrix (spec item 4)

| Route | Class | Exact missing item |
|---|---|---|
| **A** — complete cached hash-pinned wheel closure | **READY** | Nothing missing for the closure itself. (Generation is a future authorized step, not a closure gap.) |
| **B** — existing immutable authoritative schedule snapshot, no runtime package | **BLOCKED** | The snapshot: no real XNYS session/holiday/early-close artifact exists anywhere searched — only labeled SYNTHETIC_FIXTURE schedules in the -27/-28 test files and prose resampler evidence (`RESAMPLER_XNYS_EVIDENCE.md`), which is not a session artifact. |
| **C** — stdlib adapter consuming a future authoritative snapshot | **PARTIAL** | The authoritative `XNYS_SESSION_SCHEDULE_V2` artifact to consume. The adapter already exists and is accepted: `fold_materializer_v3.py` (sha256 `e1b0dfed…`, -28), pure stdlib, hash-pinned consumption, fail-closed. |

## Qualification gate (spec item 5) — for any future real V2 artifact

A real artifact is QUALIFIED only if ALL of the following hold; any
failure = HOLD, no partial credit:

1. **Full requested interval:** sessions cover the closed interval
   [coverage_start = 2024-09-16, coverage_end] with no gaps; the
   coverage_end is fixed inside the artifact before any outcome data
   exists (the -28 V2 contract enforces this structurally).
2. **Official calendar semantics:** holidays/closures and early closes
   are the exchange's official ones; exchange = XNYS, timezone =
   America/New_York, per-session open/close stated explicitly; an
   early close is declared by the schedule, never inferred from bars.
3. **Independent agreement:** the artifact is produced or verified by
   TWO independent references — here: the dual-implementation emission
   (pandas_market_calendars path vs direct exchange_calendars path,
   both inside the pinned closure) agreeing session-for-session — OR
   one primary authoritative source plus an independently pinned
   cross-check of the same strength. Disagreement anywhere = HOLD.
4. **Exact hash chain:** generator source hash, environment lock hash
   (08b38cfa…), wheelhouse manifest hash (210b8273…), library
   versions, and the artifact SHA-256 are all recorded in a committed
   generation receipt; the artifact hash is pinned before consumption.
5. **No contamination:** no performance figures and no OHLC are
   supplied at any point during qualification; qualification judges
   the calendar only.

## Qualified timestamps — the second half of the route

No separate timestamp source is needed. Once the schedule artifact is
qualified and pinned, timestamps from any future authorized data pull
are qualified BY CONSUMPTION: `fold_materializer_v3.py` validates every
supplied timestamp against the pinned schedule (09:30/13:30 anchors,
early-close single-bar sessions, coverage prefix/interior/suffix) and
fails closed on mismatch. Until the artifact exists, timestamps remain
UNQUALIFIED regardless of source — including the canonical resampler
`fetch_4h.py` (sha256 `2a4994a2…`, adopted -23), whose output the
materializer, not the resampler, qualifies.

## Residual gates — what each remaining step needs

1. **Environment build + generation** — needs a NEW separately
   authorized task (install/run authority). Plan: `FUTURE_EXECUTION_PLAN.md`;
   lock: `PROPOSED_HASH_LOCK.txt`. $0, offline, no downloads.
2. **Qualification review** — independent reviewer pass over the
   generation receipt against the gate above (same pattern as the
   -21…-28 reviews).
3. **Data pull for timestamps/OHLC** — NOT part of this route; it
   remains behind the TD lane's own gates (txn
   `QF-TD-READINESS-LIVE-20261017-20` still UNUSED) and its own
   authorization. This preflight neither advances nor prejudges it.

## Failure-memory keys

- `NO_REAL_XNYS_SCHEDULE_ARTIFACT` (Route B blocked; synthetic fixtures
  and prose evidence are not a schedule).
- `SYSTEM_SITE_PACKAGES_UNQUALIFIED` (Debian-patched, unpinned,
  calendar packages absent — never a fallback).
- Closed by this preflight: the open question from -28 of whether a
  reproducible offline calendar environment exists at all — it does.

## Accounting (exact)

Vendor calls 0; API calls 0 (the read-only public GitHub spec fetch and
the git delivery push are the only network use, per spec); model calls
0; installs 0; imports of candidate distributions 0; executions of
calendar code 0; schedule generations 0; market/OHLC fetches 0;
credentials 0; credits 0. Files searched: the 11 wheelhouse wheels +
manifest; committed NL rebuild evidence (`td_nl_env_rebuild_evidence_20261016/`,
`td_closed_session_classifier_nlqual_evidence_20261015/nl_env_freeze.txt`,
`td_p2_spot_v2_derivation_candidate_evidence_20261015/env_rebuild_freeze.txt`);
repo tree + full git history (`--all --name-only`) for schedule/calendar
paths; -27/-28 packages; system site-packages listings and `pip list`
metadata. Prohibitions honored: no real schedule generation, no market
data, no holdout access in any form, no strategy execution or imports
beyond static reference, no tuning, no live/production/ledger writes,
no Issue #9 work, no prior frozen record edited.
