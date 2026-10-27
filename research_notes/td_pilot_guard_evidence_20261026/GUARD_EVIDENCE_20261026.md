# Guard Evidence — QF-EQUITY43-FEED-MEASUREMENT-PILOT-20261024-22 (-22)

Derived-only evidence package, produced 2026-10-26 (ET) ahead of the pilot's
first Twelve Data call (Tue 2026-10-27 session). Contains hashes, counts,
states, and code paths only — no raw payloads, no bar data.

**Authority chain.** Mike directed the rights determination (chat,
2026-10-26). Determination posted to Slack #qualityflowscaner, TS
`1793043021.036639`: the frozen pilot qualifies as API/feed evaluation under
Twelve Data Basic (feed measurement only; no strategy analytics; no replay).
ChatGPT concurrence: GitHub Issue #1 comment `6431629522` (2026-10-27T01:42:00Z,
verified first-hand at production time) — narrow concurrence CONDITIONAL on
the -22 guards, ≤149 credits/day and ≤800 total, zero backfill, derived-only
evidence publication, raw archive private, fail-closed STOP on any failed
guard. This package is that derived-only publication. **All six guards PASS.**

## Guard (a) — Startup / schedule pins: PASS

- `run_manifest.json` (FROZEN, untouched): md5
  `0f42df43e54c1270defb1670c711864a` — matches the frozen package pin on
  record (package `c2b58d7`); sha256
  `596e9e81c7b62a2370c4caa6df8ac9149657189a4684f419784ca4914f6922db`.
- Manifest scope: symbols NVDA, TSLA, AAPL, SPY, MELI; sessions
  2026-10-26 … 2026-10-30.
- Schedule derivation reproduced offline from the manifest
  (`build_schedule` + `schedule_hash` in `pilot_runner.py`): 757 actions,
  schedule sha256 `8324f5ecf8918a0f784c18405cd24664aff4c80714495c44e470e647c1adfd61`
  — identical to the daemon's live `startup_attestation.schedule_sha256`.
- Bar-slot derivation: 175 bars, bar-close sha256
  `a07bc0b49077bf313f645549e60cbb70fee6e80ab98d3736c7fe96f4f73008bd` —
  identical to the attestation.
- The live action journal's IDs equal the rebuilt schedule IDs, in order.
- Latest startup attestation: 2026-10-27T00:55:47Z, source `validated`,
  `schedule_sha256_before` == `schedule_sha256` (no drift across restarts).

## Guard (b) — Email / terms tripwire: PASS

- Mechanism armed: daemon action kind `tripwire` due 09:15 ET each session
  day, before the 09:25 usage snapshot and all polls (`pilot_runner.py`
  `build_schedule` line 277; `gmail_tripwire_search` line 212;
  `execute_tripwire` line 824; manifest `email_tripwire.check`). Query:
  `from:twelvedata.com after:2026/10/24`, cutoff 2026-10-24T14:32:00Z,
  fail-closed on search failure or unknown dates.
- Today's check ran: 2026-10-26T13:15:00Z, candidates
  [`1a174da9074a6edf`], outcome `reply_pending_review`; hold set at 13:15Z,
  reason "TD reply awaiting adjudication". The hold therefore preceded the
  day's first scheduled TD action (09:25 ET usage snapshot).
- The pending daemon entry `1a174da9074a6edf` is an Intercom
  conversation-rating footer (Dooz / api@twelvedata.com, 2026-10-25T20:57:22Z,
  thread `1a16e539bce6f334`) with no Q1–Q3 content. The governing substantive
  staff reply in the same thread is on record: Artemis (Twelve Data staff),
  Gmail `1a174d86fc89c552`, 2026-10-25T20:55:03Z — Basic permits non-display
  evaluation/integration; ongoing research analytics require Grow; storage
  permitted while subscribed, delete within 30 days after end.
- Determination + concurrence adjudicated that record for THIS frozen
  evaluation use (see Authority chain). Clearing verdict for the pending
  entry: `confirmed` (no Q1–Q3 content; the substantive reply stands
  adjudicated by the determination + concurrence).

## Guard (c) — Quota / headroom guard: PASS

- Code: `DAY_CALL_CAP = 149`, `TOTAL_CALL_CAP = 800` (`pilot_runner.py`
  lines 54–55); `Pilot.cap_check` (line 528) runs before every TD action in
  `run_due`; a refusal sets the action `refused_cap` and STOPs the pilot.
  Behind it, `provider_precheck` (line 605) gates on the provider
  `/api_usage` reading (`refused_provider_precheck` STOP).
- Exercised offline this evening (production `cap_check`, stub transport
  that raises if invoked — never invoked):
  - counters 0 → `None` (allowed)
  - day count 148 on the action day → `None` (allowed)
  - day count 149 on the action day → `day_call_cap_149_reached:2026-10-27`
  - total 800 → `total_call_cap_800_reached`
- Live counters after a full held session day: `desk_calls = 0`,
  `desk_calls_by_day = {}`, `desk_nonusage_calls = 0`.

## Guard (d) — Restart stability: PASS

- Daemon code `pilot_runner.py` sha256
  `24407d862d1a2f3e0ee41a345b6e29fae0d92380e5e0f6ce7042975b50d8cea04`
  (2026-10-26 repair build: self-detach double-fork + setsid, single-instance
  flock on `state/daemon.lock`, fatal tracebacks to `logs/daemon_errors.log`).
- Instance lineage today (lock file + watchdog records; each death was a VM
  replacement, not a code crash): PID 23960 (19:33Z) → 7959 (20:56Z) →
  4087 (22:55Z) → **7409 (2026-10-27T00:55:47Z, current)**.
- Current instance: PPID 1, own session, alive >1h at evidence time;
  heartbeat advancing (02:01:39Z → 02:02:04Z across a 25 s observation,
  status `held`, `desk_calls` 0).
- Single-instance proof: a duplicate launch attempt is on record in
  `logs/daemon.out` — `{"pilot": "already_running", "pid": 23988}`.
- Restart-from-state without repetition: every restart revalidates the
  persisted journal against the rebuilt schedule (attestation source
  `validated`); the journal census is unchanged across all of today's
  restarts (done 1 / pending 756 — see Guard (f)).

## Guard (e) — Fail-closed paths: PASS

- Hold gate: `run_due` returns `held` before executing any action while
  `tripwire.hold` is true (`pilot_runner.py` ~line 926); a tripwire check
  that sets the hold returns `held` immediately (~line 946).
- Observed behavior, full session day 2026-10-26 under hold: exactly **1 of
  757 actions executed — the 09:15 tripwire check itself**. Zero TD-kind
  actions (usage / ladder / finalization / revision) executed;
  `desk_calls = 0`. Nothing was backfilled.
- Encoding robustness (2026-10-26 repair): `encoding="utf-8",
  errors="replace"` at all three subprocess text sites (lines 157, 221,
  1011) — a decode error can no longer kill the daemon; adjudication stays
  fail-closed because an unparseable tripwire search sets the hold.
- Atomic persistence: state and heartbeat writes go through tmp-file +
  `os.replace` (lines 134, 1045). `logs/daemon_errors.log` has never been
  created — no fatal traceback post-repair.
- Permanent-stop paths intact: STOP file, tripwire contradiction verdict,
  cap refusal, and provider-precheck refusal all set `stopped` and halt;
  live state `stopped = null` (no stop has fired).

## Guard (f) — Journal / offline parity: PASS

- Journal audit of `state/pilot_state.json` at evidence time: 757 actions,
  757 unique IDs, **0 duplicates**; status census {done: 1, pending: 756} —
  identical to the startup attestation census; kind census {ladder: 525,
  finalization: 175, revision: 25, usage: 21, archive_push: 6, tripwire: 5}
  — identical to the attestation action census and to the manifest-derived
  schedule.
- Bars: 175 slots, all unobserved (no first-seen recorded) — consistent
  with zero calls made.
- Usage guard state clean: baseline null, no external events, no 429s.
- No action executed out of order: the single executed action is the
  earliest-due TD-gating action (the 2026-10-26 tripwire check).

## Clearance

With all six guards PASS and the concurrence's conditions met (including
this derived-only publication), the tripwire hold is cleared with verdict
`{"1a174da9074a6edf": "confirmed"}`. Expected daemon behavior on clearance:
Monday 2026-10-26's aged actions are marked `missed_late` with cause
`tripwire_hold` — never backfilled (the concurrence expressly preserves the
Oct 26 session as missed with zero calls) — and the pilot proceeds with the
Tue 2026-10-27 session. No Twelve Data call is made by the clearing step
itself.
