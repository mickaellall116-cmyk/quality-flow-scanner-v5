# TD PROBE DAY-1 RERUN — task -75 RESULT

Task: QF-TD-PROBE-DAY1-RERUN-20261021-75
Authorization: Mike, direct in chat, 2026-10-21 17:28 ET —
"Yes — Day 1 rerun GO (≤12 credits)". Scope DAY 1 ONLY.
Candidate: accepted -74 package (precommit b223595, result
71eee93; 70/70 synthetic PASS incl. the monotonic-commit
preflight), accepted by ChatGPT. The first attempt (-69)
stopped at G-USE under the old (-68) preflight semantics.

## TERMINAL

TD_PROBE_DAY1_RERUN_EXECUTED__NVDA_PASS__TSLA_DATA_UNQUALIFIED_C2__AAPL_CONTROL_PASS

The preflight PASSED under the repaired semantics, all five
Day-1 legs were acquired on first attempts, and the analyzer
ran. Sampled-window verdicts only; C5 remains
PENDING_R7_R30. No global KEEP/REPLACE S2 verdict (never this
task's to issue); no performance computed.

## GATES, IN ORDER

- G-PIN PASS — the -74 package verified 66/66 against its
  committed SHA-256 manifest in a detached worktree at
  origin/main. Frozen pilot pins match the runner's constants
  exactly (pilot_acquire.py acf39bbd…, rate_limiter.py
  06ad383d…). Manifest sha256 1bb86e17… equals the store
  marker's binding from -69 (the manifest bytes never changed
  across -66..-74), so the -69 store was reusable as-is.
- G-CLK PASS — host UTC vs independent HTTPS Date headers,
  midpoint-corrected: google.com −0.301s (rtt 0.719s),
  microsoft.com −0.665s (rtt 0.554s); both well inside the
  5s threshold.
- G-CRED PASS — credential attached at fetch time only via
  the sanctioned helper dynamic_credentials.py
  (url_with_surrogate_query_param, custom.twelvedata,
  api.twelvedata.com only). The raw key never entered the
  process and was never printed, logged, or written. All six
  fetches completed through the helper.
- G-USE PASS — the open -69 schema question is now resolved
  with persisted evidence: the live /api_usage body (131
  bytes, sha256 6c7f4766…, preserved in the local store as
  api_usage.D1.body.bin) DOES carry the daily pair. Full live
  field set: timestamp "2026-10-21 21:33:00",
  current_usage=1, plan_limit=8 (minute bucket),
  daily_usage=2, plan_daily_limit=800, plan_category="basic".
  The frozen daily gate evaluated: 2 + required_headroom 10
  <= 800 — PASS. Header reconciliation: api-credits-used 1
  == current_usage 1; 1 + api-credits-left 7 == plan_limit 8
  — PASS. The receipt persisted on the outcome (PASS) with
  commit_state "1": the monotonic activation completed after
  the final directory fsync. The binding's data-transport
  backstop verified the committed PASS before its first
  fetch (see disclosure 2).

## CREDITS — EXACT, RECONCILED

- This execution: **6 calls** = 1 /api_usage (1 attempt,
  HTTP 200) + 5 /time_series (1 attempt each, all HTTP 200).
  Retries: 0. Expected 6 — exact. Hard ceiling 12 — the
  binding's process-wide counter capped total fetches at 12
  pre-transmission and was never approached.
- Vendor counter cross-check: each data response's
  api-credits-used header incremented 2,3,4,5,6 in leg order
  (the usage call reported 1), confirming one credit per
  /time_series call in the vendor's own accounting.
- The usage response reported daily_usage=2. That is
  consistent with -69's single call earlier today plus this
  rerun's usage call being the day's second counted call;
  the vendor's reset semantics are a standing unknown, so
  this is recorded as consistency, not proof.
- Program live Twelve Data usage to date: 1 (−18) + 1 (−69)
  + 6 (−75) = **8 credits**.

## PER-LEG RECEIPTS (all HTTP 200, 1 attempt, ASC, 1h,
America/New_York, outputsize 5000, zero pagination)

- REQ-ADJ-01 NVDA splits 2023-12-13→2024-06-21: 116,908 B,
  sha256 69b87f03…, 917 rows.
- REQ-ADJ-02 TSLA splits 2022-03-07→2022-09-09: 117,690 B,
  sha256 c5f70188…, 911 rows.
- REQ-ADJ-03 AAPL splits 2026-02-19→2026-08-24: 117,272 B,
  sha256 1f3169f5…, 903 rows.
- REQ-ADJ-01N NVDA none (twin): 118,655 B,
  sha256 a3b4578c…, 917 rows.
- REQ-ADJ-02N TSLA none (twin): 116,870 B,
  sha256 35026525…, 911 rows.

## ANALYSIS (analyzer = -74 probe_analyzer.py, unmodified)

- NVDA window — **PASS**. C1 PASS (0 deviations); C2 PASS,
  convention SCALED_BY_FACTOR (uniform); C3 PASS — factor
  flip at 2024-06-10 09:30, ON_EFFECTIVE_DATE; C4 PASS —
  pre/post ratio step 10.000000165…, matches factor 10;
  C6 PASS (917 = 917 rows, no pagination).
- TSLA window — **DATA_UNQUALIFIED**. C1 PASS (0
  deviations); **C2 FAIL — convention INCONSISTENT: "166
  pre-split bar(s) fit neither convention; 0 post-split
  bar(s) off ratio 1"**; C3 PASS — flip at 2022-08-25
  09:30, ON_EFFECTIVE_DATE; C4 PASS — ratio step
  3.000000010…, matches factor 3; C6 PASS (911 = 911).
  Descriptive decomposition (computed from the snapshots,
  NOT an analyzer output and NOT a re-verdict): the 166
  bars are zero-volume in BOTH series (volume "0" in the
  splits and the none snapshot alike), spanning
  2022-03-28→2022-07-20 across all regular-session hours;
  every one of the other 668 pre-split pairs has a nonzero
  volume scaled exactly ×3, and no pair shows any other
  ratio. A 0/0 pair fits neither of the analyzer's
  conventions, which is what its C2 rule counts. The frozen
  verdict stands as issued; what the zero-volume bars mean
  for qualification is an adjudication question.
- AAPL control — **PASS** (structural). Receipt identity/
  hash/params verified; bars parse inside the window; C4
  per-bar OHLC consistency PASS (no inconsistent bars);
  C6-style row count PASS (903 < 5000, no pagination).
  C1/C2/C3 are NOT_APPLICABLE: the frozen manifest gives
  the dividend-window control no none-twin (see
  disclosure 4).
- C5 — PENDING_R7_R30 (revision legs not authorized, not
  run, not scheduled by this task).

## STORAGE

- Local task store ~/workspace/qf_td_probe_d1_20261021/store
  holds the raw payloads: the five REQ-ADJ-*.json snapshots
  (raw vendor bytes), per-leg receipts + attempts logs, the
  usage body bytes + committed receipt, the limiter ledger,
  and the store marker. (-69 left only probe_store.json in
  this store; every other artifact is -75's, timestamped
  2026-10-21 21:33Z — the two executions are separated by
  artifact timestamps and by -69 having produced no
  payloads at all.)
- Archive repo mickaellall116-cmyk/qf-data-archive: **push
  FAILED on both available routes — nothing landed.**
  (a) git clone/push over HTTPS with the stored credential:
  403 "Write access to repository not granted" — the
  fine-grained PAT is scoped to quality-flow-scanner-v5
  only. (b) The custom.github Contents-API helper
  (gh_contents.py put): sandbox-blocked, authd 403 S693585 —
  the known dead path. Per the task's terms the local bytes
  + their SHA-256s (in the store receipts, the analyzer
  input verification, gate_evidence.json, and this memo)
  stand as the evidence until an authorized archive route
  exists.
- This package (scanner repo): the transport binding, the
  analysis driver, analysis_results.json, gate_evidence.json,
  the sanitized usage receipt, the five sanitized leg
  receipts, and the runner stdout/stderr. Sanitized only;
  no raw bars, no key material.

## DISCLOSURES

1. Archive push failed (above). Nothing was sent anywhere
   else; no third route was improvised.
2. The -75 binding differs from -69's in exactly two
   places, both forced by the -70..-74 repairs and recorded
   in the binding's own docstring: (i) the header scrub
   allowlist also passes api-credits-used/api-credits-left —
   the -74 preflight captures and reconciles exactly these
   (refuse-only); the -69 binding dropped them because the
   -68 preflight had no header reconciliation. (ii) The
   data-transport backstop no longer computes
   plan_limit − current_usage ≥ 12 (that arithmetic WAS the
   defective -68 semantics); it requires the persisted
   usage receipt to be a committed PASS (verdict PASS,
   commit_state "1"). The candidate's frozen preflight
   remained the only pass/refuse authority.
3. A static py_compile syntax check of the binding ran
   before the live run (not a test execution); its
   __pycache__ was removed, as was the analyzer import's.
4. One judgment, recorded: analyze_window requires a twin
   pair and the frozen manifest has no AAPL none-twin, so
   the AAPL control was evaluated with the analyzer's own
   primitives (verify_receipt, parse_bars, _ohlc_consistent,
   row count) and C1/C2/C3 marked NOT_APPLICABLE rather
   than synthesized.
5. Elapsed: ≈7 minutes wall clock end-to-end (gates from
   ≈21:30Z, runner 21:32:53Z→21:33:02Z, analysis, archive
   attempts, package + push verified by 21:36Z) of the
   ≤60 budget. One pass; no leg was re-executed.
   (Figure corrected in the labeled correction commit
   following the result commit: the original memo overstated
   the end time as ≈21:44Z / ≈13 minutes.)
6. State unchanged elsewhere: REQ-S2 HOLD (the TSLA C2
   finding is evidence for adjudication, not a verdict on
   S2); entries PAUSED; R7/R30 unauthorized; nothing
   adopted or integrated; no performance computed.
