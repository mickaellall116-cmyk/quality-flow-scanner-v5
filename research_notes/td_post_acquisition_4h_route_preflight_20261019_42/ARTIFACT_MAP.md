# ARTIFACT MAP — how XNYS_SESSION_SCHEDULE_V2 is (and is not) consumed

Artifact: `XNYS_SESSION_SCHEDULE_V2.json`, sha256
`3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88`
(28,046 bytes; package
`research_notes/xnys_isolated_calendar_generation_20261019_35_r2/`,
commit `9c62e255`; verdict QUALIFIED_XNYS_SCHEDULE_V2__PROVENANCE_CLEAN__
CALENDAR_GATE_CLOSED).

## Artifact contents (inspected)

Top level: `artifact` ("XNYS_SESSION_SCHEDULE_V2"), `version` 1,
`exchange` "XNYS", `timezone` "America/New_York", `coverage_start`
2024-09-16, `coverage_end` 2026-10-16, `source` (generation task + primary
record packages -31/-32/-33), `sessions`: 524 entries of
`{date: "YYYY-MM-DD", open: "09:30", close: "16:00" | "13:00"}` (local ET
wall-clock strings). Verified against the bytes: 2025-01-08 present
(09:30/16:00); 2025-01-09 (Carter closure) ABSENT; early-close entries
carry close "13:00" (e.g. 2024-11-29, 2025-07-03).

## Who consumes it today

- `fold_materializer_v3.py` (sha256 `e1b0dfed…`, -28, accepted commit
  `5dc8b2a…`): the ONLY consumer. Timestamp-only: it pin-checks the
  artifact, derives each session's expected anchors (09:30 always; 13:30
  only when close is 16:00 — `expected_anchors(regular_close)`), and
  enforces the coverage-boundary contract (prefix/interior/suffix/
  overshoot). It consumes the artifact DOWNSTREAM of bars, to audit bar
  timestamps — it does not build bars.
- Construction (pilot_build / construct_4h / validate_input): does NOT
  read the artifact at all. Every calendar fact on that path comes from
  live `pandas_market_calendars` (see SEMANTIC_MATRIX row 7).

## What the artifact CAN supply to a future constructor

- The authoritative session set for 2024-09-16 → 2026-10-16 (open days =
  listed dates; closed days = absence, incl. the Carter closure).
- Per-session open ("09:30") and close ("16:00" / "13:00") wall-clock ET —
  exactly the inputs `session_close_et` currently fetches from PMC, and
  exactly what construct_4h's existing `session_closes` override
  (construct_4h.py:71) accepts.
- The expected 1H constituent grid per session (derivable: hourly starts
  from open to close — the same derivation validate_input.expected_1h_
  starts performs from (open, close), validate_input.py:59–74), and hence
  expected interval ends.
- Early-close identity per date (close == "13:00"), DST correctness by
  construction (dates + America/New_York localization; no offsets stored
  or needed).

## What it CANNOT supply

- **Warm-up sessions.** The frozen contract needs a 215-bar warm-up before
  the dev interval; those sessions (~2024-04 → 2024-09-13) are outside
  coverage_start. An artifact-only constructor cannot resolve their
  closes. (The sealed holdout 2023-10-19 → 2024-09-15 borders this zone;
  warm-up bars are indicator inputs, not holdout outcomes — but their
  calendar source must still be pinned: the validator/PMC-4.5.1 leg is
  the only pinned candidate on record.)
- Anything after 2026-10-16 (acquisition/as-of dates beyond coverage_end
  fail closed by design, cf. Amendment v4 consumer semantics).
- Split/corporate-action data, adjustment factors, vendor interval-end
  documentation, or price/volume facts of any kind (by design: the
  artifact is calendar-only).
- UTC instants (it stores wall-clock strings + a named timezone; a
  consumer must localize — the same convention the materializer uses).

## Where live PMC 4.5.1 remains necessary (if route (a) or a hybrid is chosen)

- Inside the pinned validator mechanism (validate_input.xnys_schedule) —
  already chain-bound and proven (-40); replacing it changes pinned bytes
  and voids that proof's object.
- For warm-up-session closes under any artifact-consuming route.
- Nowhere else: no other construction input requires a calendar library
  once closes + grid are supplied.
