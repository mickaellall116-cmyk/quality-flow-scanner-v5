# TD Pilot Archive-Push Incident — Reconciliation & Closure (2026-10-27)

Pilot: QF-EQUITY43-FEED-MEASUREMENT-PILOT-20261024-22 (Twelve Data 1h feed measurement)
Archive repo: `qf-data-archive` (private), pilot subtree `captures/td_feed_measure_pilot_20261026`
Requested by: ChatGPT (Slack #qualityflowscaner TS 1793136595.263719)
Status: **CLOSED — parity PASS, cause identified, recovery verified. No data loss, no duplicates.**
Derived-only receipt: no raw payload content is reproduced here.

## 1. Parity — PASS (no loss, no duplicates)

- The pilot subtree tree hash is **identical** in the original local commit `129fa00` and the
  rebased remote commit `5bab217`:
  **`a22304acd51c8c6a57c3a506540ce478b10e6b15`**
  (path `captures/td_feed_measure_pilot_20261026` in `qf-data-archive`).
- `journal.jsonl` = **64 rows in both**, byte-identical (diff clean).
- **64 payload files** under `payloads/2026-10-27/` in `5bab217`.
- `desk_calls` for 2026-10-27 at recovery time = **64**.
- The rebase touched commit parentage only; content unchanged.

## 2. Cause — concurrent-writer non-fast-forward (NOT transient / size / secret-scan)

- The runner's archive push at **2026-10-27T20:40:01Z** returned `push_rc=1`
  (recorded in `state/last_push.json`).
- **Tooling gap on record:** the runner did not capture push stderr — only the return code.
  The cause below was proven independently, not read from the runner's logs.
- Independent proof: `git push --dry-run` reproduced git's rejection verbatim —
  "the tip of your current branch is behind its remote counterpart" (non-fast-forward).
  A fetch showed `origin/main` had advanced `b53fca3 -> 62e1bae` via two commits from a
  **parallel workstream** after the pilot clone's base:
  - `282531d` — P7b every-observed-bar inventory archive
  - `62e1bae` — EXP-14 execution-only price input archive
- Paths are fully disjoint (pilot `captures/td_feed_measure_pilot_20261026/**` vs
  `research_inventory/**` and the EXP-14 archive directory), so the rebase was conflict-free.
- **Recovery:** fetch + rebase of the runner's own journaled capture commit onto the current
  origin tip at **20:59:15Z**, pushed as **`5bab217`**. Content-preserving: no force push,
  no reset, no hand-created commits.
- Independent confirmation: the pilot watchdog's 17:25 ET run verified
  `HEAD = origin/main = 5bab217` via `ls-remote`, zero unpushed commits.

## 2b. `--status` diagnostic hang — explained, no daemon defect

- The watchdog's diagnostic `pilot_runner.py --status` produced no output and was terminated.
- By design the runner holds an flock (`state/daemon.lock`, `LOCK_EX | LOCK_NB`) for the
  daemon's lifetime; a diagnostic invocation while the daemon is live contends with that lock.
- State-file reads (`pilot_state.json` / `heartbeat.json` / `last_push.json`) are the safe live
  diagnostic path and were used for this closure.
- The live runner (pid 4065) was never killed or disturbed.

## 3. Item 3 — position for ChatGPT adjudication (NO code change made)

- The deployed runner is hash-pinned by the corr1 PASS
  (sha256 `b587c483e5453ffa5968447f87efbaf540f5424aaaf37ef870dd36ea9f4275b9`), and the daily
  watchdog/clearance chain verifies that hash. Editing `pilot_runner.py` mid-pilot would void
  the PASS basis and trip the hash checks for the remaining sessions (Wed–Fri).
- Safeguards in force for the remaining sessions:
  - (a) watchdog archive check after 16:45 ET each session day (this is what detected the incident);
  - (b) the exercised repair: fetch + rebase the runner's own journaled capture commit onto the
    current origin tip + push (content-preserving, no force push, no reset, no hand-created commits);
  - (c) single-writer in practice: only the pilot runner creates capture commits in this clone.
- Proposed for the **post-pilot successor** (not this pilot): fetch/rebase-before-push inside the
  push step, bounded retry with backoff on non-fast-forward only, and capture push stderr into
  `last_push.json`.
- **Adjudication requested:** confirm the deferral. If a mid-pilot code change is insisted on, it
  requires a corr2 review cycle and is **not** done here.

## Bounds

- No runner code changed. No force push. No reset.
- Caps, tripwire, and the no-backfill rule untouched.
- Monday 2026-10-26 remains missed with zero Twelve Data calls (preserved fact, unchanged by this incident).

— Muse
