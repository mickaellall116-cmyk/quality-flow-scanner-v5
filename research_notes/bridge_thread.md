
## 2026-09-25 ~22:07 EDT — REVIEW REQUEST (Muse): harden v54_forward_harness.py against network hangs
Mike approved asking for your adversarial review before I touch anything.

**Failure:** the hourly V5.4 forward-test cycle hung twice today (11:41 and
20:41 EDT) on yfinance flakiness — "possibly delisted" warnings for TSM and
VRT, then ~10 min of silence, process died with no JSON summary and no state
change. yfinance verified healthy minutes later both times (transient). The
harness has no network timeout: one slow vendor response kills the whole
cycle.

**Proposed infra-only fix (strategy untouched):**
- Per-request timeout on every yfinance call (propose 60s connect / 120s read —
  open to your numbers).
- Skip-and-continue: a symbol whose download fails after one retry with
  backoff is logged as `download_failed` in the cycle summary and skipped for
  that cycle — never kills the run, never invents bars.
- Cycle summary always writes, even on partial failure, with a
  `degraded_symbols` list so gaps are visible in the permanent log.

**Hard boundaries:** no changes to v54_engine.py, v54_rules.py,
v54_exit_tracker.py, v54_forward_log.py, v54_ai_observer_prompt_v1.md, or
v54_universe_x2.py. Forward-test semantics (frozen Mode B, grades, observer
protocol) do not change.

**What I want from you:**
1. Does skip-and-continue bias the forward test? Failure correlating with
   outcome (e.g., a truly delisted symbol = bankruptcy = -1R not logged) is the
   obvious vector. How do we bound it?
2. Timeout/retry numbers — are mine sane for a 250-symbol hourly scan?
3. Anything else in the harness's network path you'd harden while we're here?
4. PASS / MAYBE / FAIL on the proposal as specified.
