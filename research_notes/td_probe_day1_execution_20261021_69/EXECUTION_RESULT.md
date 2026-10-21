# TD PROBE DAY-1 EXECUTION — task -69 r1 RESULT

Task: QF-TD-PROBE-DAY1-EXECUTION-20261021-69 r1
Authorization: Mike, direct in chat, 2026-10-21 08:47 ET —
"Yes — Day 1 probe GO (≤12 credits)". Scope DAY 1 ONLY.
Candidate: accepted -68 package (precommit 8a160db, result
47cd24f, cleanup e2bc271; 38/38 synthetic PASS), accepted by
ChatGPT as offline candidate evidence (Issue #1 comment
6313951534).

## TERMINAL

TD_PROBE_DAY1_HOLD__G_USE_USAGE_HEADROOM

The Day-1 execution stopped at the pre-transmission usage gate.
Zero data requests were transmitted. One /api_usage call was
made (1 credit).

## GATES, IN ORDER

- G-PIN PASS — the -68 package verified 65/65 against its
  committed SHA-256 manifest in a detached worktree; `git diff
  e2bc271..origin/main` over the package is empty (byte-identical
  to the accepted cleanup commit). Manifest sha256
  1bb86e17ee7907bae67db9c22b0a74cc61027c495c1f1ed74d65df17585a53e1.
- G-CLK PASS — host UTC vs independent HTTPS Date headers,
  midpoint-corrected: google.com −0.763s (rtt 0.525s),
  microsoft.com −1.553s (rtt 1.895s); both within the 5s
  threshold. (The -18 stale-clock lesson is why this gate exists.)
- G-CRED PASS — credential attached at fetch time only, via the
  sanctioned helper dynamic_credentials.py (8b1f42e8…) using
  url_with_surrogate_query_param for custom.twelvedata, host
  api.twelvedata.com only. The raw key never entered the process
  and was never printed, logged, or written.
- G-USE FAIL → STOP — /api_usage (attempt 1) returned HTTP 200
  with current_usage=1, plan_limit=8. The accepted candidate's
  preflight rule (current + required_headroom 10 ≤ plan_limit)
  refused: 1 + 10 > 8. Remaining headroom 7 < the Day-1 worst
  case of 12 required by the task gate. The runner exited 4
  before any data transport was used:
  "preflight source verification failed: USAGE_HEADROOM:
  current 1 + headroom 10 > limit 8".

## WHAT THE RESPONSE MOST LIKELY MEANS (flagged, not assumed)

plan_limit=8 matches the free plan's documented 8-credits-per-
MINUTE rate limit — and the frozen runner's own limiter encodes
the same pair (RollingCreditLimiter(8, 800): 8/minute, 800/day).
The vendor's /api_usage plan_limit field therefore appears to
report the per-minute limit, NOT a daily allowance, while the
candidate's preflight (built against docs + synthetic fakes with
plan_limit=800) treats it as the budget the day's worst case must
fit inside. That is a field-semantics mismatch discovered only
against the live endpoint — precisely the execution-day unknown
-64 flagged ("endpoint response/schema UNTESTED UNTIL USER GO").
Per the task's G-USE rule, a schema that is not understood stops
the day; overriding the frozen gate live was not an option. The
fix (reconcile the preflight's headroom semantics with the
observed field meaning, e.g. validate the daily budget against
the correct source) is a candidate-repair question for
adjudication — it is NOT made here.

## CREDITS

- Day-1 expected 6, hard ceiling 12. Actual spend: **1 credit**
  (the single /api_usage attempt; the program counts a usage
  check as 1 credit — -18 precedent, -63 accounting — and the
  response's current_usage=1 corroborates one counted call in
  the vendor's current window; the account's previous live call
  was 2026-10-17).
- Data requests transmitted: 0. Retries: 0. Total calls: 1.
- Program live Twelve Data usage to date: 1 (−18) + 1 = 2.

## PER-LEG OUTCOMES

- /api_usage preflight: 1 attempt, HTTP 200, gate refusal above.
- REQ-ADJ-01 (NVDA splits), REQ-ADJ-02 (TSLA splits),
  REQ-ADJ-03 (AAPL splits), REQ-ADJ-01N (NVDA none),
  REQ-ADJ-02N (TSLA none): NOT TRANSMITTED (day stopped at
  G-USE). No receipts, no snapshots, no rows.

## ANALYSIS

NOT RUN — no data was acquired. C1/C2/C3/C4/C6 have no inputs;
C5 remains PENDING_R7_R30 (R7/R30 were not authorized and were
not scheduled). No sampled-window verdicts are issued. No
global KEEP/REPLACE S2 verdict (never this task's to issue).

## STORAGE

- Local store ~/workspace/qf_td_probe_d1_20261021/store contains
  ONLY probe_store.json (runner manifest marker). No raw vendor
  payloads exist from this execution.
- Archive repo mickaellall116-cmyk/qf-data-archive: nothing
  acquired, nothing pushed.
- This package (scanner repo): the transport binding, this memo,
  gate_evidence.json, and the runner refusal record. Sanitized
  only; no key material anywhere.

## DISCLOSURES

1. The /api_usage response BODY was not persisted: the accepted
   candidate's DailyUsageSession writes its receipt file only on
   PASS, so on a refusal the only surviving record of the live
   response is the refusal string (current 1, limit 8, HTTP 200
   implied by successful parsing). Candidate gap worth fixing:
   refusal-path receipts should be persisted for audit.
2. The binding's own G-USE backstop (data transport re-checks
   remaining headroom ≥ 12 before its first fetch) never got to
   run — the candidate's adapter refused first, upstream of it.
   Both gates agree on the outcome.
3. One judgment recorded, none taken: the plan_limit semantics
   reading above is an interpretation offered for adjudication,
   labeled as such; it did not influence execution (the frozen
   gate decided).
4. Elapsed: gates + single call ≈ 4 minutes wall clock of the
   ≤60 budget (12:50Z–12:54Z approx., incl. write-up start);
   no re-execution was attempted or will be under this task.
5. State unchanged elsewhere: REQ-S2 HOLD; entries PAUSED;
   R7/R30 unauthorized; no performance computed; nothing
   adopted or integrated.
