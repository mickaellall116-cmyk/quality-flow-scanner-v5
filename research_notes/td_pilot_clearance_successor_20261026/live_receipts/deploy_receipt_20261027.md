# TD pilot corr1 deployment receipt — 2026-10-27 (deploy step only)

Authority: ChatGPT corr1 PASS (Issue #1 comment 6433891782), package commit 93db881.
Scope: install + restart + verify ONLY. tripwire_clear.json NOT written; the hold was NOT lifted.

- Old runner sha256: 63e2ccbfe836b5f81e1d8285dff7626e28f6f8936fa5ce32cbf712268dd1e8f2 (pre-fix)
- Installed runner sha256: b587c483e5453ffa5968447f87efbaf540f5424aaaf37ef870dd36ea9f4275b9 (corr1, sourced from the committed package at 93db881; hash matched exactly)
- Old daemon PID 4235 (watchdog restart lineage; pre-check heartbeat 2026-10-27T04:57:13Z) — SIGTERM, exited ~2s
- New daemon PID 4368 — first heartbeat 2026-10-27T04:58:04Z, confirmed advancing 04:59:36Z, status held
- State before == state after: tripwire.hold true; desk_calls 0; desk_calls_by_day {} (no 2026-10-26 or 2026-10-27 entries — zero TD calls); journal 757 (done 1 / pending 756); stopped null; no state/tripwire_clear.json
- Backups untouched: pilot_runner.py.bak_20261026_prefix / _optionB_prefix / _corr1_pre
- Anomaly: heartbeat.json briefly absent during startup (atomic-rewrite gap); present and advancing on re-check. Nothing else.

Next (separate step): Tue 09:15 ET tripwire must complete clean under the inherited hold, then clearance (verdict confirmed for 1a174da9074a6edf) before 09:25 ET. Abort/skip on any hash, heartbeat, journal, mailbox, headroom, or timing failure; never backfill.
