---
id: v54-forward-test-watchdog
title: V5.4 forward-test watchdog
enabled: true
owner: goal:v5-4-forward-test
mode: task
schedule:
  kind: interval
  timezone: America/Denver
  at: 2026-09-15T11:50:48
  every: 1h
timeout_secs: 300
delivery:
  - surface: side_chat
    to: a0f82a2b-ab10-4677-b800-2a87c66021af
metadata:
  originating_channel_context_json: '{"originating_channel":"side_chat","chat_kind":"direct","conversation_id":"a0f82a2b-ab10-4677-b800-2a87c66021af","delivery_channel":"side_chat","delivery_target_id":"a0f82a2b-ab10-4677-b800-2a87c66021af","event_kind":"message","require_mention":false}'
  presentation_locale: en-US
---
V5.4 forward-test watchdog. Check whether the hourly forward-test cycle is still completing successfully. Do this:

1. Read `~/workspace/quality-flow-scanner-v5/v54_forward/last_cycle.json`. It contains `finished_at` (UTC ISO timestamp), plus `new_signals`, `opened`, `closed`, `errors`.
2. The cycle is BROKEN if any of these is true:
   - the file is missing or unreadable,
   - `finished_at` is more than 6 hours older than the current UTC time,
   - `errors` is a non-empty list.
3. If BROKEN: read `~/workspace/quality-flow-scanner-v5/v54_forward/watchdog.json` (may not exist). If it contains `last_alert_at` less than 6 hours ago, stay silent (already alerted). Otherwise, send Mike a concise alert in this chat: what is wrong (stale timestamp with its age, or the error details), when the last good cycle finished, and that the forward test needs attention. Then write `watchdog.json` with `{"last_alert_at": "<current UTC ISO>"}`.
4. If NOT broken: stay silent, end quietly. Do not report healthy status.

Do not modify any scanner code, do not push to git, do not restart or change the `v54-forward-test-cycle` schedule. This job only watches and alerts.
