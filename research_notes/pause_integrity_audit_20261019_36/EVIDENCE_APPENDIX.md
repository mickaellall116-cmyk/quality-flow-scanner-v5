# EVIDENCE APPENDIX — QF-PAUSE-INTEGRITY-INCIDENT-20261019-36 r1

All values read from artifacts on disk / git objects on 2026-10-19 during the audit window (~15:52–16:07Z). Nothing modified.

## Commits inspected (git log/show, local objects; also on origin/main)

| Commit | Time (UTC) | Author | Files touched | Role |
|---|---|---|---|---|
| `19e3834b206cb3ea932496760f355619ab076c0c` | 2026-10-19T14:54:37Z | Mektech (local git identity) | `forward_test/v54_status.json` only (39+/15−) | Harness status snapshot: signals 37→38, MRNA/TEAM open, MSFT pending |
| `2257ead72fc0b163a06649a6773d864111b0dc0d` | 2026-10-19T14:55:21Z | KAMA Shadow Bot `<actions@github.com>` | `forward_test/kama_shadow.json` only (34+/3−) | Separate GH Actions shadow watcher; unrelated to V5.4 entries |
| `2d7f1fe00243666f217728f3f23989bbffca75cb` | 2026-10-19T15:11:11Z | Mektech (local git identity) | `forward_test/v54_ai_observer.json` only (65+/2−) | Harness observer export: count 36→37, MSFT assessment |
| `997e7867a8b296ae9d42eeb6ce1adc78e9da11de` | 2026-10-19T15:11:39Z | KAMA Shadow Bot `<actions@github.com>` | `forward_test/kama_shadow.json` only (2+/4−) | KAMA shadow; unrelated |

Pre-incident baseline: `git show 19e3834b^:forward_test/v54_status.json` — as_of 2026-10-16T20:49:35.115344Z, signals_logged 37, closed_trades 24, cumulative_r 10.0547, live_control "V5.3 (unchanged)", pending_entries [MRNA (B, signal_bar 2026-10-16T14:30:00-04:00), TEAM (B)].

## File hashes (sha256, at audit time)

- `v54_forward_harness.py` — `dc3ee392c808aa2e52d468cad0020d8fe85b6f2bda0adc656304193563cba0c8` (matches the Oct 14 r2 deployed live harness pin in the record)
- `v54_forward/state.json` — `2454d0e32b83ab32f96f89e776e2423c64e0bc95a10d01e7d58021c7be10b508` (runs 676, last_run 2026-10-19T15:50:19.385878Z; positions registry 27 ids; pending [MSFT]; close_logged 24)
- `v54_forward/forward_test.jsonl` — `72515b5bf6bcfe49cd06c269e2e0838c4c6ae92b0c2379f0fb7c39679015508a`
- `v54_forward/ai_observer.jsonl` — `beeb16569b40a412a6f9af0f7532e86e82dd2cbf38c2fa8551dde27bcbf60ee9`
- `forward_test/v54_status.json` — `8ee939d8623cf3ad93c4ffe0298ff31a7356fbef0020f435fa412a627463f697` (as_of 2026-10-19T15:50:19.442184Z)
- `forward_test/v54_ai_observer.json` — `88a37f242d72471c4d28d1ff735eaab63f18c608f4b37892258cfbf49758e386`

## Log lines relied on (v54_forward/forward_test.jsonl)

- TEAM `pending_entry`: signal_bar_start 2026-10-16T14:30:00-04:00, logged_at 2026-10-16T20:49:35.073688Z (MRNA pending in the same cycle).
- MSFT `signal` record: logged in the 2026-10-19 cycle; price 533.9749755859375, stop 526.7577215435374, tp1 552.3276647124237, entry YES, protection SAFE, state "PULLBACK BUY", signal_bar_start_at 2026-10-19T06:30:00-04:00, signal_bar_close_at 2026-10-19T10:30:00-04:00.
- MSFT `pending_entry`: logged_at 2026-10-19T14:54:35.339515Z.
- MRNA `opened`: bar 2026-10-19T06:30:00-04:00, entry 217.27000427246094, logged_at 2026-10-19T14:54:35.343577Z; `profit_protect_armed` logged_at .358249Z.
- TEAM `opened`: bar 2026-10-19T06:30:00-04:00, entry 208.11000061035156, logged_at 2026-10-19T14:54:35.369057Z.

## Observer records (v54_forward/ai_observer.jsonl)

Record keys (all): assessed_at, classification, confidence, features, invalidation, observer, primary_risk, prompt_version, reasons, signal_id, timing. **No provider/model/request-id/token/cost fields exist in any record.**
- MRNA + TEAM: assessed_at 2026-10-16T20:50:47.736019Z.
- MSFT: assessed_at 2026-10-19T15:07:59.884043Z, classification CAUTION, confidence 62.

## Code-path citations (v54_forward_harness.py, sha256 dc3ee392…)

- `PAUSE` string: **0 matches** across all `v54_*.py` (grep, exit 1). Sentinel path `forward_test/PAUSE_NEW_ENTRIES`: absent on disk.
- Data-quality suppression: `CycleProvider.entries_suppressed` property line 250; `suppression_reason` line 253; wall-clock suppression lines 1074–1075; guard application lines 1082–1086 (`provider.entries_suppressed`); summary field lines 309, 1626, 1662.
- Publish: `publish_snapshot()` git subprocess block lines ~1299–1402 (incl. line 1339 mapping `v54_ai_observer.json` → `forward_test/v54_ai_observer.json`); no HTTP/LLM client anywhere in the file (subprocess used only for git).

## Cycle record (v54_forward/last_cycle.json, latest cycle only retained)

finished_at 2026-10-19T15:50:22.501273Z; cycle_status HEALTHY; entries_suppressed false; suppression_reason ""; new_signals 0; opened 0; closed []; errors []; publish {ok: true, pushed: false, note: "up to date"}; coverage: expected 250 / fresh 250 (fresh_via_prefetch 250), benchmark 2/2, global_provider_status "ok", retries 0.

## Spec / governance references

- Incident spec: Issue #1 comment `6271273070` (2026-10-19T15:48:20Z) — https://github.com/mickaellall116-cmyk/quality-flow-scanner-v5/issues/1#issuecomment-6271273070
- Incident commits: https://github.com/mickaellall116-cmyk/quality-flow-scanner-v5/commit/19e3834b206cb3ea932496760f355619ab076c0c and https://github.com/mickaellall116-cmyk/quality-flow-scanner-v5/commit/2d7f1fe00243666f217728f3f23989bbffca75cb

## Evidence gaps (stated, not filled)

1. Per-cycle records for the Mon 14:54 cycle (its own coverage/health block) were overwritten by the 15:50 cycle in `last_cycle.json`; the 14:54 cycle's effects are proven by its jsonl events + published snapshot instead.
2. No workflow/run ID exists in repository artifacts for the local harness publications or for the observer-append step; KAMA Actions run IDs are not in the repo.
3. No provider/model/token/cost meter for AI-OBS-v1 exists in the repo → external-call status UNVERIFIED (fail closed), not resolved either way.
