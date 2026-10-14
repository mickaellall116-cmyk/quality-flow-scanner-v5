# Amendment to TD_MANIFEST_V2_OFFLINE_REPLAY_20261014 (-11) — effort, trials, session aggregates

**Amendment task:** QF-TD-V2-SPOT-BATCH-PREFLIGHT-20261014-12 r1,
step 1 (per ChatGPT adjudication, Issue #1 comment `6172067035`,
which gave -11 a SCOPED PASS and named this documentation gap).
**Amends:** `research_notes/TD_MANIFEST_V2_OFFLINE_REPLAY_20261014.md`
(commit `9d87b1c`). That report is immutable; this amendment is a
separate file and changes none of its bytes or findings.

**Method:** reconstructed ONLY from artifacts already in evidence
(the -11 evidence directory's file timestamps, `replay_output.json`
lifecycle timestamps, and the -11 report's own recorded statements).
No test was rerun to fill this gap. Anything not reconstructable is
marked **UNKNOWN** rather than estimated.

## 1. Actual effort (as evidenced)

All times UTC, 2026-10-14, from evidence artifacts:

| When | Evidenced event |
|---|---|
| 15:01–15:02 | Nasdaq/ISO reference fetches (report §2, recorded fetch window) |
| 15:04:00 | `exact_diff_v1_v2.json` written (V2 build + machine diff complete) |
| 15:04:19 | `validate_manifest_v2_output.txt` + `preflight_v2_output.txt` written |
| 15:05:21 | Replay lifecycle: CREDIT_RESERVED / STARTED (REQ-P1H-01, disposable state) |
| 15:09:09 | Replay lifecycle: CONSTRUCTION_HOLD + COMPLETED (terminal COMPLETE) |
| 15:13:30 | `replay_driver.py`, `replay_output.json`, `symbol_mic_evidence.json` finalized |
| 15:14:54 | Report + V2 + evidence committed (`9d87b1c`) |

- **Evidenced artifact-producing span:** 15:01Z → 15:14:54Z
  ≈ **14 minutes**.
- **Replay wall time:** the -11 report records ~7.6 min wall for the
  replay run, nearly all inside `validate_input.validate`
  (CPU-heavy full-window bar validation). The lifecycle timestamps
  span 3m48s (15:05:21→15:09:09); the difference between the two
  figures (process setup/validation outside the lifecycle span) is
  **not further resolvable from artifacts** and is recorded as-is.
- **Total task wall-clock** (including reading/setup before the
  first artifact): **UNKNOWN** — no start timestamp was persisted
  in the -11 evidence.

## 2. Every trial and failure

| # | Trial | Outcome |
|---|---|---|
| 1 | V2 construction with byte-faithful serializer (precondition: V1 re-dump byte-identical to V1 file) | PASS, first attempt. Exact diff: 45 differing fields (6 provenance + 39 mic_code), 0 disallowed differences |
| 2 | `validate-manifest` on V2 (pinned collector `bd003c3c…`) | PASS, first attempt — 0 manifest errors, 51 requests |
| 3 | `preflight` on V2 | PASS, first attempt — 0 prerequisite failures; dispatch BLOCKED (zero-call build, no vendor transport) |
| 4 | Offline replay: `Collector.run()` with local stub transport returning the preserved receipt bytes, disposable state + disposable limiter ledger, under `unshare -n` + in-process socket guard | PASS, first attempt — terminal classification COMPLETE; 0 socket connect attempts recorded |
| 5 | Cross-check: fresh Collector `_verify_receipt` on the receipt the replay produced | PASS — `(True, "ok")`, byte-identical to the preserved payload (sha256 `c47bf899…`) |

**Failures:** none recorded in the -11 evidence. No failing run,
error output, or aborted attempt left an artifact.

**Known non-trial (disclosed in the -11 report, not a failure):**
direct `_verify_receipt` on the rejected receipt is impossible by
design (rejected evidence has no RECEIVED + COMPLETED lifecycle
pair); trial 4 was the pre-declared closest faithful equivalent.

**Repair usage:** no repair pass is recorded; repair minutes = 0
as evidenced. Informal iteration that left no artifact, if any,
is **UNKNOWN** and is not claimed either way.

## 3. Sanitized session aggregates (from existing evidence only)

From `replay_output.json` and the accepted session validator's
outcome — counts and timestamps only, no bar data:

| Aggregate | Value |
|---|---|
| Window | 2026-04-01 → 2026-10-06 (America/New_York) |
| Rows validated | 910 |
| First bar | 2026-04-01 09:30:00 |
| Last bar | 2026-10-06 15:30:00 |
| Validation scope | `session_1h` — full session-completeness validation, PASS |
| Response bounds | 910 < outputsize 5000; ≤ one-response bound 1323 |
| Venue identity (receipt meta) | NASDAQ / XNGS / USD — binds under V2 |

**Derived aggregate** (arithmetic on the recorded facts above,
flagged as derived, not separately logged in -11): the frozen 1H
grid has 7 regular-session constituents (09:30…15:30); 910 ÷ 7 =
**130 sessions, all fully present** — a session with any missing
constituent would have failed the session-completeness validation,
so session-level missingness for this receipt = **0 incomplete
sessions**. A per-session missingness table was **not** persisted
in the -11 evidence and is **unavailable** beyond this aggregate;
it was not re-derived from the receipt for this amendment (no
rerun, per the adjudication instruction).

## Scope

This amendment records bookkeeping facts about -11 only. It does
not change the -11 verdicts, does not rewrite the live -09 HOLD,
admits no bytes into live state, and authorizes nothing.
