# entries_suppressed — code semantics (from the pinned live harness body)

Source: `live_harness_dc3ee392.py` in this package (sha256
`dc3ee392c808aa2e52d468cad0020d8fe85b6f2bda0adc656304193563cba0c8`, byte-identical
to the live `v54_forward_harness.py` and to the harness blob of deployed
candidate commit `10ae732c91e1c2e5d76f461e0c04c7015c522d30`).

## What the field means

`entries_suppressed` is a **per-cycle feed-health gate**, not a trading pause:

- `ProviderHealth.entries_suppressed` (property, ~line 250):
  `return bool(self.primary_failures) or self.global_rate_limited`
  — true only when symbols lack fresh primary data or the provider
  rate-limited the cycle.
- In `run_cycle` (~lines 1067–1090): the summary starts with
  `entries_suppressed: False`; it is set `True` if the cycle wall-clock budget
  is already exhausted ("budget exhausted before staging", cycle marked
  DEGRADED) or if `provider.entries_suppressed`. Only when it remains `False`
  does the harness run new-signal detection
  (`eng.v54_qualified_signals(ctx.scan_rows)`) and stage entries.
- Therefore `entries_suppressed: false` in the run-567/569 raw bodies means:
  **the feed was healthy and the entry gate was OPEN** — signal detection ran
  and any qualified signal would have been staged as a (paper) entry.

## Pause search — locations inspected, all negative

- `v54_forward_harness.py`, `v54_engine.py`, `v54_rules.py`: no `PAUSED` /
  `paused` / `PAUSE` token; no entry-disable flag; CLI surface is
  `run_once(publish: bool)` (invoked as `python3 v54_forward_harness.py --publish`).
- `v54_forward/state.json` (pinned body): keys are `close_logged`,
  `data_outages`, `last_run`, `pending`, `positions`, `runs`,
  `seen_signal_ids`, `snapshots` — no pause field.
- Scheduler job definitions (`scheduler_cycle_job.md`,
  `scheduler_watchdog_job.md` in this package; source
  `~/workspace/goals/v5-4-forward-test/crons/hourly/`): no pause instruction;
  the cycle job instructs normal signal logging and paper-position advancement.
- Goal record `~/workspace/goals/v5-4-forward-test/GOAL.md`: no pause language.

## What actually kept entries at zero in runs 567–569

- Each gated cycle reported `new_signals: 0`, so `opened: 0` mechanically.
- The append-only log `v54_forward/forward_test.jsonl` contains exactly 30
  signal events; every signal_id is dated 2026-09-15 → 2026-09-28. **No new
  signal has fired since 2026-09-28** — before the 2026-10-03 FAIL verdict.
  The last two closes (CRWD +1.6305R, OKTA +3.5523R, 2026-10-12) were runners
  from 2026-09-28 signals.
- The "entries PAUSED" state is Mike's 2026-10-03 governance decision
  (V5.4 closed FAIL; no promotion, no real-money entries, no auto-relaunch).
  It is real as a decision and is honored operationally, but **no code, config,
  state, or scheduler artifact enforces it**, and the harness contains no
  broker/real-money path at all (positions are paper entries in `state.json`).
- Consequence: the gated window never exercised an entry decision, and the
  standing claim "entries remain PAUSED" cannot be independently established
  from artifacts. If a qualified signal fires in a future healthy cycle, the
  harness as configured **would** stage a paper entry.
