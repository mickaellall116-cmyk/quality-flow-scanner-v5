# EVIDENCE MANIFEST — QF-V54-PAUSE-ENFORCEMENT-20261019-37 r2 (closure-only pin)

Task start (verification): 2026-10-19T19:39:24Z. All hashes SHA-256, computed from
bytes on disk at pin time. Copies are byte-exact (`cp`); live files were not moved,
replaced, or modified.

## Live anchors (verified at task start AND task end — see closure memo)

| Item | SHA-256 | Bytes |
|---|---|---|
| Live harness `v54_forward_harness.py` (working tree) | `ce7c902ce182683ca1723468a0109747abd80db287c39556ea4db78210a0833d` | 86,618 |
| Live sentinel `forward_test/PAUSE_NEW_ENTRIES` | `3f4b7811a577cc989438edc568d40d739281f76bcfbb0d0f36b900b2ccaa3ea2` | 533 |
| `forward_test/RESUME_NEW_ENTRIES` | ABSENT (verified at start and end) | — |
| Pre-change harness (rollback) | `dc3ee392c808aa2e52d468cad0020d8fe85b6f2bda0adc656304193563cba0c8` | 80,326 |

## Pinned package contents (this directory)

```
3f4b7811a577cc989438edc568d40d739281f76bcfbb0d0f36b900b2ccaa3ea2  pinned/PAUSE_NEW_ENTRIES.bytes
85072c1a8f2bc0e834ec1367697ef0e933ab1c3761ac4bf2e093a8ee24341675  pinned/SHA256SUMS.pre_change.txt
bfdebd09d38dbc601c9c182d782b25f42626bc93f838a82342cded8990b774f3  pinned/last_cycle_runs679.json
a859ccea0e0ef72632fdafb5826071e86cec1f8211dee7d468592f3f81ae2a0f  pinned/pending_fill_blocked_pause_event.jsonl
ce7c902ce182683ca1723468a0109747abd80db287c39556ea4db78210a0833d  pinned/v54_forward_harness_DEPLOYED_ce7c902c.py
dc3ee392c808aa2e52d468cad0020d8fe85b6f2bda0adc656304193563cba0c8  pinned/v54_forward_harness_PRE_CHANGE_dc3ee392.py
30af05a3df8d9857f928bb59460859de24b2787ec54b5913f74837e94bd0593a  pinned/v54_status_at_pin.json
8eb7e21c0dd0217a85a508d3ec26767c68727b1eefde99e1cfc25570f3c288a8  test_pause_enforcement.py
```

## Sources of pinned copies

- `pinned/v54_forward_harness_DEPLOYED_ce7c902c.py` — byte copy of the live working-tree
  `v54_forward_harness.py` (the exact deployed implementation; hash equals the live anchor).
- `pinned/v54_forward_harness_PRE_CHANGE_dc3ee392.py` and `pinned/SHA256SUMS.pre_change.txt` —
  byte copies from the r1 rollback bundle at
  `~/workspace/goals/v5-4-forward-test/hidden_files/pause_enforcement_20261019_37/pre_change/`
  (bundle also holds pre-change state.json, forward_test.jsonl, ai_observer.jsonl,
  last_cycle.json, v54_status.json, v54_closed_trades.json, v54_ai_observer.json snapshots,
  each listed in the copied SHA256SUMS manifest; the `.pre` harness entry in that manifest
  reads `dc3ee392c808…`, matching the pinned copy).
- `pinned/PAUSE_NEW_ENTRIES.bytes` — byte copy of the live sentinel. Content is operational
  text only (pause notice + gate explanation); no secrets, credentials, or nonpublic details,
  so the bytes themselves are committed rather than a redacted proof.
- `pinned/last_cycle_runs679.json` — byte copy of `v54_forward/last_cycle.json` as of pin time
  (the gated cycle receipt: runs=679 per `v54_forward/state.json`, last_run
  2026-10-19T18:56:01Z, HEALTHY, entries_paused true, pause_control sentinel,
  entries_suppressed true, new_signals 0, opened 0).
- `pinned/v54_status_at_pin.json` — byte copy of `forward_test/v54_status.json` as of pin time
  (carries entries_paused / pause_control / pause_reason; corroborated immutably by status
  snapshot commit `40e0479099b4d61369c381ea0a56004ab8eec3e0`).
- `pinned/pending_fill_blocked_pause_event.jsonl` — the single matching line extracted from
  `v54_forward/forward_test.jsonl`: MSFT `pending_fill_blocked_pause`, intended fill bar
  2026-10-19T10:30:00-04:00, intended fill open 534.09 (extraction only; the source JSONL
  was not modified).
- `test_pause_enforcement.py` — the original r1 offline synthetic suite source, committed
  unchanged.
