---
id: v54-forward-test-cycle
title: V5.4 forward-test cycle
enabled: true
owner: goal:v5-4-forward-test
mode: task
schedule:
  kind: interval
  timezone: America/Denver
  at: 2026-09-15T11:41:07
  every: 1h
timeout_secs: 1800
delivery:
  - surface: side_chat
    to: a0f82a2b-ab10-4677-b800-2a87c66021af
metadata:
  originating_channel_context_json: '{"originating_channel":"side_chat","chat_kind":"direct","conversation_id":"a0f82a2b-ab10-4677-b800-2a87c66021af","delivery_channel":"side_chat","delivery_target_id":"a0f82a2b-ab10-4677-b800-2a87c66021af","event_kind":"message","require_mention":false}'
  presentation_locale: en-US
---
Run one V5.4 forward-test cycle. Execute: `cd ~/workspace/quality-flow-scanner-v5 && python3 v54_forward_harness.py --publish` (via the shell). This scans the frozen forward-test universe — cohort 1: UX51 (51 symbols, theme Forward-UX51) plus cohort 2: X2 (199 symbols, theme Forward-X2), 250 symbols total — with the V5.4 engine, logs new qualified A/B/C signals, advances Mode B paper positions bar-by-bar, persists state, writes forward_test/v54_status.json, forward_test/v54_closed_trades.json and forward_test/v54_ai_observer.json, and publishes changed files to GitHub (mickaellall116-cmyk/quality-flow-scanner-v5) via the GitHub Contents API using the stored connector — no git push, no SSH.

Hard boundaries: do NOT modify any V5.3 file (scanner_rules.py, masterscanner_api.py, streamlit apps, tests for V5.3, workflows), do NOT touch any other repo path or file. Only forward_test/*.json may be published. NEVER modify v54_ai_observer_prompt_v1.md (frozen). NEVER modify v54_universe_x2.py (frozen 2026-09-15). If the script fails, do not invent workarounds that change behavior — report the failure.

AI OBSERVER (AI-OBS-v1) — observational only; it never affects V5.4 in any way. After the harness run, for each signal_id in the printed summary's "new_signal_ids" (these were generated THIS cycle, before any outcome exists):
1. Get the raw snapshot (V5.4 grade is excluded by construction — use nothing else, never look up the grade):
   python3 -c "import json, v54_forward_harness as h; print(json.dumps(h.observer_raw_snapshot('<signal_id>')))"
2. Read the frozen prompt v54_ai_observer_prompt_v1.md and produce exactly one assessment following its output schema. Use ONLY the snapshot from step 1. You do not know the trade outcome — never invent or look up later price action.
3. Append via the validating helper (it refuses bad schemas, duplicates, and backfills):
   python3 -c "import json, v54_forward_harness as h; obj=<your assessment JSON with features=<snapshot from step 1> and assessed_at=<current UTC ISO>>; print(h.observer_append_assessment(obj))"
   If it returns ok:false, report the errors concisely and do NOT retry with a weaker assessment.
4. After all new signals are handled, refresh the export and publish:
   python3 -c "import v54_forward_harness as h; h.write_observer_export(); print(h.publish_snapshot())"
Rules: assess ONLY this cycle's new_signal_ids. If a signal_id was already assessed, skip it permanently — never regenerate or edit. If assessment fails this cycle, skip it permanently for AI-OBS-v1 — never backfill in a later cycle (later price action would contaminate it). The INTC signal from 2026-09-15 predates the observer and must never be assessed.

After the run, read the JSON summary it prints:
- If `errors` is non-empty, or state/log/output files look wrong, or `publish` shows ok:false, or any observer append returned ok:false: report the problem concisely in this chat.
- If `new_signals` > 0 or any position opened/closed: report one line per signal — symbol, grade, entry/stop/TP1, observer classification if assessed, and close result if closed. No trading advice, no tuning suggestions, no rule changes.
- Otherwise (no new signals, no position changes, no errors): end the run quietly with no user-facing report.

The forward-test log lives at ~/workspace/quality-flow-scanner-v5/v54_forward/forward_test.jsonl and state at v54_forward/state.json. latest_v54_signals.json at the repo root is the separate V5.4 output namespace.
