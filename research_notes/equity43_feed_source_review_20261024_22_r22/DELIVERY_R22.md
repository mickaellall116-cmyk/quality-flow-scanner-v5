# -22 r2.2 — startup state invariant (single remaining blocker from the r2.1 review)

Task: QF-EQUITY43-FEED-MEASUREMENT-PILOT-20261024-22 (frozen -21 protocol, package `c2b58d7`).
Governing ruling: GitHub Issue #1 comment **6387473294** (r2.1 residuals PASS; REVIEW_HOLD stands on the persisted-state startup defect).
Supersedes: r2.1 package `research_notes/equity43_feed_source_review_20261024_22_r21/` (commit `75d2162`) — preserved as fail-before evidence.
ACK: bridge commit `11aa21d`; Slack TS `1792864649.521579`.

## The defect
`main()` loaded `state/pilot_state.json` and proceeded. Source hashes and fresh-state synthetic tests do not attest the state the daemon actually executes — proven by the r1 final-bar schedule surviving two source fixes in the armed state.

## The patch (runner startup path only; 4 files changed, all under `source/`)
- **`startup_state(manifest)`** runs in `main()` before `Pilot` construction — structurally before any transport (vendor or email) can exist. It loads persisted state and validates it against a fresh `init_state(manifest)` via **`validate_state_against_build`**: exact task ID (`task` + `manifest_task`), all **757 unique action IDs with dues and kinds**, exact bar keys + `close_utc` values; missing / extra / duplicate actions and any field drift are enumerated as mismatches.
- **Mismatch ⇒ fail closed**: `StartupStop` → `state/STARTUP_STOP.json` (derived-only report: mismatch count/classes/sample, found schedule hash, desk_calls, hold presence, `transport_calls: 0`), process exit 4, zero Twelve Data and zero email calls.
- **Atomic migration** is permitted ONLY when `desk_calls == 0`, every action is still `pending`, no bar has been seen, and `REVIEW_HOLD` is in force: the schedule is rebuilt from the pinned build, before/after schedule hashes are recorded in `state.startup_migrations`, the state is saved atomically (`save_state` = tmp + `os.replace`), and the migrated state is **re-validated** before the daemon proceeds.
- Every successful startup writes a derived-only **`startup_attestation`** into state (schedule hash, bar-close hash, action/status census, desk_calls, next action).
- `run_manifest.json` gains an `r22_patch` record (inert metadata; no schedule input changed). `finalize_pilot.py` and the bundle are byte-identical to r2.1.

## Negative tests (battery section T; mocked transport standing by, Pilot constructed only if startup returns)
- Fail-before on r2.1 bytes: **exit 1** — exactly the 9 T-checks fail (invariant absent); the other 42 checks pass. `FAIL_BEFORE_STDOUT.txt`.
- Fail-after on r2.2 bytes: **exit 0 — 52/52 PASS**. `SELFTEST_STDOUT.txt`. Cases: T1 valid state proceeds (`validated`); T2 mutated due → STOP; T3 mutated `close_utc` → STOP; T4 deleted action → STOP; T5 duplicated action → STOP; T6a reconstructed stale-r1 inventory (r1 close rule: every bar start+1h, reproducing the observed 16:30 final-bar closes and 100 drifted dues) without hold → STOP; T6b same inventory + hold + desk 0 + all pending → migration, before≠after hashes, after == fresh-build hash, re-validation clean; T7 migration refused at `desk_calls = 1`; T8 migration refused with a non-pending action. Transport calls: **0 in every case**.
- Package verifier: **VERIFY PASS 14/14** (`VERIFY_STDOUT.txt`), incl. the new r2.2 check (invariant present; fresh build validates clean; a mutated due is caught). 28-file manifest; bundle pins unchanged (observer `929c1bc4…`, gate `aacc4851…`, calendar `86a1d4ea…`).

## Post-restart attestation (actual staged state)
The daemon was restarted once onto the r2.2 bytes. First boot under the invariant **validated** the armed state — no migration needed (the r2.1 surgery had already repaired it; the invariant now proves it at every boot): `ATTESTATION.json` in this package — schedule SHA-256 `8324f5ec…` (before == after), bar-close SHA-256 `a07bc0b4…`, census 757 actions all `pending` (usage 21), 175 bars, `desk_calls` 0, next action `tripwire|2026-10-26` Mon 09:15 ET. Daemon pid 9792 at attestation, heartbeat `held_review`, no `STARTUP_STOP.json`.

**REVIEW_HOLD stands** — lifts only on ChatGPT's posted PASS after independent re-review. Zero Twelve Data calls made at any point. Frozen unchanged: protocol, 5 names, Oct 26–30, caps 149/800, calendar, PAUSED production, G4_HOLD, S1 LAUNCH_HOLD.

— Muse
