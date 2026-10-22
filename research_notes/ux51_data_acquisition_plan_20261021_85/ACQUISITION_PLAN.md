# UX51 QUALIFIED HISTORICAL DATA — ACQUISITION / COVERAGE PLAN — task -85

**Type:** planning document ONLY. No vendor calls, no captures, no spend,
no holdout access were made or are authorized by this document. It answers
ChatGPT's QF NEXT ACTION (Slack TS 1792627306.219339, 2026-10-21): *"Prioritize
a concrete 51-symbol qualified historical data acquisition/coverage plan,
including cost/terms and earliest attainable dates."*

**Problem it addresses:** qualified, contract-conformant 4H coverage of the
frozen UX51 universe is **0 of 51 symbols** (-77 readiness audit, commit
22b6903). This plan defines the dataset that would qualify, the only route
the record supports, the gates in dependency order, the execution shape for
a future authorization, and the exact decisions Mike must give, in order.

Every load-bearing figure is cited to its pin. Anything not in the record
is marked **UNCONFIRMED** or **TO_BE_CONFIRMED_AT_AUTHORIZATION**; every
forward date is labeled **ESTIMATE** with its assumptions.

---

## 1. Target definition — the exact dataset that would qualify

- **Universe:** UX51, definition_sha256
  `d139d7bf21165c79cb112a091cdcf7b021b86bd06f2165e07fb75932e6fa27dc`
  (-77 §0), designated THE frozen corrected-baseline universe in -82 item 1
  (package d2cca9c; X2 = secondary cohort, never the baseline).
- **Composition (from the -77 §0 symbol list):** 44 session-bound names
  (equities/ETFs) + 7 crypto names (AVAX-USD, BTC-USD, DOGE-USD, ETH-USD,
  LINK-USD, SOL-USD, XRP-USD). The two classes have different bar physics
  and are costed separately throughout this plan.
- **Instrument:** 1h bars — the input of the pinned constructor
  (`construct_4h`, sha d47e8df1…; session bins [09:30, 13:30) and
  [13:30, close); early-close day = single [09:30, 13:00) bin), timezone
  America/New_York, bar datetimes at bar open (-63 fact F4).
- **Windows (frozen, -25 preregistration, PREREGISTRATION.md sha
  ccf1a988a93026a2…):**
  - HOLDOUT 2023-10-19 → 2024-09-15 (sealed; capturing bytes for this
    window does not open it — see gate 9).
  - DEV 2024-09-16 → latest closed session. The pinned qualified calendar
    (-35 r2) ends 2026-10-16; sessions after that date exist in no pinned
    calendar. The capture manifest must either cap dev at 2026-10-16 or
    extend the calendar under the same -34/-35 contract first. Arithmetic
    impact of extension: +7 bars per added session per session-bound
    symbol; chunk counts below are unchanged for ≈190 further sessions
    (dev-chunk headroom 5000 − 3653 = 1347 bars), so the costing is
    robust to the choice.
- **Sessions (enumerated from the calendar artifacts, this task):**
  - Holdout: **227** = 225 regular + 2 early-close (2023-11-24, 2024-07-03)
    — -81 candidate calendar, sha
    `8d659dde9ccb51b9d86d6c45759abceb6ccd90ad7fa49e7478b13c2dc153a0a2`,
    CANDIDATE_NOT_ADOPTED (package 9c59ea1).
  - Dev: **524** = 519 regular + 5 early-close (2024-11-29, 2024-12-24,
    2025-07-03, 2025-11-28, 2025-12-24) — -35 r2 artifact
    XNYS_SESSION_SCHEDULE_V2, sha
    `3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88`,
    commit 9c62e25, parity 48/48.
  - **Total: 751 sessions (744 regular, 7 early-close).**
- **Bars per session-bound symbol** (derivation in COVERAGE_ARITHMETIC.md;
  verified exactly against two independent probe windows):
  - 1h bars: holdout 225×7 + 2×4 = **1583**; dev 519×7 + 5×4 = **3653**;
    total **5236**.
  - Constructed 4H bars: holdout 452; dev 1043; total **1495**.
  - Session-bound totals (44 symbols): **230,384** 1h bars → 65,780 4H bars.
- **Crypto names:** not calendar-derivable (continuous market; the XNYS
  session grid does not bound them). A full-span 1h pull
  (2023-10-19 → 2026-10-16 ≈ 1093 days × 24) is ≈ **26,232 bars/symbol —
  ESTIMATE**; the exact count depends on the capture manifest's crypto
  window/timestamp convention, which the record does not pin —
  **UNCONFIRMED** until the manifest freeze (decision 8) settles it.

## 2. Route analysis (record evidence only)

### Twelve Data — the only demonstrated 2023-capable route
- Demonstrated reach: served 1h bars back to 2022 in the -75 probe (TSLA
  leg, 2022-03-07 → 2022-09-09, 911 rows; receipts in
  td_probe_day1_rerun_20261021_75, result 8533a59). No other route in the
  record has served 2023-era 1H for any UX51 symbol.
- Documented terms (-63 desk packet, doc snapshot fa940cf49f…):
  /time_series = **1 credit per symbol/request** (F2); `outputsize`
  range 1–5000 (F3); `adjust` default `splits` (F1); /api_usage = 1
  credit (program record, -63 §6b A4).
- Account standing, live-verified (-75 receipts, 2026-10-21T21:33:00Z):
  Basic/Free, **$0**, plan_daily_limit **800**, minute plan_limit **8**;
  program Twelve Data spend to date = **8 credits**.
- Chunking math: one session-bound symbol needs ceil(5236 / 5000) = **2
  requests** per basis. The provenance-clean split — one request for the
  holdout window (1583 rows) + one for the dev window (3653 rows), each
  under the cap — is also exactly 2, so seam-aligned chunking costs
  nothing extra. (Manifest discipline, -63 §6c C6: a response at exactly
  5000 rows is a truncation suspect and triggers seam verification, never
  silent pagination.)
  - Session-bound: 44 × 2 = **88 requests (firm)**.
  - Crypto: ≈ 7 × ceil(26,232 / 5000) = 7 × 6 = **≈42 requests (ESTIMATE)**.
- **$ cost:** free tier **$0**. Paid-tier prices / credit allowances for
  /time_series are **not in the record** (the only paid-tier fact recorded
  is that /splits requires Grow+, -63 F6) → **TO_BE_CONFIRMED_AT_
  AUTHORIZATION**. No price is invented in this plan.

### Yahoo — structurally disqualified for this dataset
- 1H reachback ≈730 days → earliest reachable ≈ Oct 2024 today, receding
  daily (-77 §1). It could nominally serve only the dev sub-span
  [≈Oct 2024 → present]. It cannot serve: the holdout span (any
  authorization), nor dev 2024-09-16 → ≈Oct 2024. A Yahoo dataset is
  therefore incomplete at the frozen seam by construction.
- A split-route dataset would additionally put a route seam inside dev,
  with Yahoo's adjustment policy unpinned (D2 = DIAGNOSTIC_ONLY, -77 §1).
- The Yahoo clean-capture route is PARKED (executor candidate
  READY_FOR_SEPARATE_ADOPTION, never adopted, no capture ever run), and
  its 1H→4H construction is the chain whose grid defect produced the
  2026-10-03 candle failure — the reason the parity gate exists.
- **Verdict: NOT a route to the qualified dataset.** (A future cross-check
  role is not proposed here and would need its own adjudication.)

### Tiingo — cannot serve
Held store is EOD **daily only** (interval mismatch vs the 1h contract),
raw+adjusted policy-ambiguous, and under a terms HOLD that bars
persistence (-77 §1, D3). Tiingo intraday exists in the record only as an
unevaluated sample-eval candidate. **Verdict: CANNOT SERVE.**

### Other record-named candidates — not plannable
Benzinga and EODHD were named in the 2026-10-06 data-feed sample-eval
spec and never evaluated to qualification in the record; Intrinio/Zacks
were declined by Mike ($950/mo). No qualification evidence exists for any
of them → **UNCONFIRMED as routes**, excluded from the decision set.

**Route verdict: Twelve Data, single-basis, seam-aligned chunks — the
only route the record supports.**

## 3. Qualification gates (dependency graph, owners)

Each gate blocks the next. (G-numbers here are this plan's; -82's G1–G5
are referenced explicitly where they coincide.)

1. **CALENDAR ADOPTION** — adopt the -81 candidate (8d659dde…) as the
   qualified holdout-window calendar, and disposition the 2023
   core-hours sub-gap (the candidate applies the -34 contract's session
   definition; in-era core-hours proof remains absent, -81 REAUDIT_MEMO).
   Owners: ChatGPT adjudication → **Mike adoption GO**. Blocks: manifest
   freeze (the session grid must name its calendar).
2. **FREEZES AFTER CLAUDE'S TARGETED RE-REVIEW of -82** (re-review in
   flight per the -85 spec): **E3 PIT freeze** (A: decision-time
   `announced_at` rule, vs B: retrospective exclusion labeled
   non-tradable — no silent middle, -77 §2b) and **R1–R5
   session-handling freeze** (-82 G2). Owners: Claude (review),
   ChatGPT (adjudication), **Mike (both freezes)**.
3. **C5 REVISION LEGS** — R7 on/after **2026-10-28T21:33:00Z**, R30
   on/after **2026-11-20T21:33:00Z** (eligibility from the immutable -75
   receipt instant 2026-10-21T21:33:00Z; -77 §3). Each leg: 1 usage + 2
   data first attempts, ≤6 credits under the ≤2-attempt cap (-63 §6b).
   Owner: **Mike GO each**; Muse executes.
4. **S2 DISPOSITION** on C1–C6 including C5 (-63 §6d terminals:
   KEEP / REPLACE / HOLD). Owner: ChatGPT adjudication.
   - REPLACE → capture basis = the uniform adjusted basis; no split-event
     producer is needed for the baseline.
   - KEEP → the split-event producer gate (**GATE-E1…E5**, -82 G1;
     producer = new component, separate GO) becomes a predecessor to
     capture finalization.
   - HOLD → all downstream stays held.
5. **CONSTRUCTOR DUPLICATE-GUARD DISPOSITION** — Claude's re-review
   covers the duplicate-merge finding + upstream validator sufficiency
   (-82 item 5: the pinned constructor silently merges duplicate
   timestamps; duplicate safety is validator-layer today). If validator
   sufficiency is NOT accepted, guard H3b (pinned-chain change + full
   route re-proof, -82 G3) precedes any consumption of captured bytes.
   Owners: adjudication → **Mike GO if pursued**.
6. **CAPTURE AUTHORIZATION** — route, manifest freeze (including the
   crypto window convention and the dev-end rule from §1), and credit
   ceiling (§4). Owner: **Mike**. Policy A does NOT cover this capture
   (its 52-credit ceiling is for the FRESH screen day only, -63 §6b);
   the FRESH 51-request manifest is a different object (a 20-symbol
   screen) and is never this capture.
7. **CAPTURE EXECUTION** — pilot → full (§4), archive-first storage.
   Owner: Muse, under the authorization.
8. **POST-CAPTURE QUALIFICATION** of the captured bytes, all required:
   per-symbol independent completeness check (-82 item 4, fixture-proven
   14/14) with zero unexplained anomalies; constructor index-equality
   against the adopted calendars; **end-to-end candle parity**
   (byte-identical candles, backtest vs live construction, spanning a
   DST boundary and two window lengths — standing rule from the
   2026-10-03 failure); full portfolio-decision parity. Any failure →
   the affected symbol/span is DATA_UNQUALIFIED and the dataset is not
   declared. Owners: Muse executes, ChatGPT adjudicates, Claude
   spot-replicates.
   - Conditional gate 8b: **ab254c3 classifier integration** (pinned
     PMC 5.5.0 closure, absent — -77 §1) is required only if the TD
     route is the baseline source (-77 §2b step 6); its dependency
     artifact needs its own acquisition decision.
9. **QUALIFIED DECLARATION → BASELINE** — only after gate 8 passes:
   fold materialization on qualified timestamps (-25: expanding train
   ≥252 sessions, 63-session OOS blocks; on the pinned dev calendar
   that is at most floor((524−252)/63) = 4 full OOS blocks, -77 §2c)
   and the corrected DEVELOPMENT baseline run — itself a further
   authorization in Mike's sequence (his review → Claude re-review →
   backtest decision). Capturing holdout-window bytes does NOT open
   the sealed holdout: its single use remains governed by -25 §50
   (independent checkpoint + pinned qualified dataset + calendar —
   this plan is how those preconditions come to exist).

## 4. Execution shape (for the future authorization — not now)

- **Phase 0 — pilot (5 symbols, full span, single basis):** NVDA, TSLA,
  AAPL (continuity with -75 receipts), SPY (ETF), SMCI (in-span 10:1
  split, Oct 2024 — seam/split stress). All session-bound: 5 × 2 = 10
  data requests + 1 usage preflight = **11 credits expected (firm)**.
  Pilot gate: completeness check + parity machinery run clean on real
  full-span bytes before Phase 1 is requested.
- **Phase 1 — full:** remaining 39 session-bound symbols × 2 = 78 data
  requests; 7 crypto × ≈6 ≈ 42 (ESTIMATE); + 1 usage preflight per
  execution day.
- **Program totals, single basis (recommended):** expected ≈
  88 + 42 + 2 usage = **≈132 credits** (88 firm, ≈44 estimated);
  worst case under the ≤2-attempt cap ≈ **264 credits**.
  Dual-basis variant (splits + none twins across the full span, for
  full-span C1-style verification): expected ≈262, worst ≈524 — NOT
  recommended: the basis is decided at gate 4 before capture; a dual
  capture insures against a decision the gate chain already makes.
- **Days:** at the documented free allowance (800/day), transmission
  fits in **one day in every scenario** (worst-case dual-basis 524 <
  800). The 8/min rate limit sets a transmission floor of ≈17 minutes
  for 132 requests (132/8 ≈ 16.5). The plan schedules **2 execution
  days** (pilot day, full day) as a discipline choice — the pilot gate
  sits between them — not a credit necessity (ESTIMATE).
- **Ceiling proposal (Policy A discipline: a ceiling is not an
  execution GO; each phase still gets its own GO record):** authorize
  a capture ceiling of **300 credits** (covers single-basis worst case
  264 + usage + margin), fail-closed ledger, one /api_usage preflight
  per execution day before any data call, ≤2 attempts per request, any
  429/limit refusal = hard stop for the day.
- **Storage, archive-first:** raw bodies land ONLY in the private
  qf-data-archive as `captures/<capture_id>/` with capture_manifest.json
  + SHA256SUMS, verified by re-fetch before the phase is reported (the
  -75/-81 procedure; archive commits 2f223cf, 58ad260). Sanitized
  receipts go to the scanner-repo package. Nothing raw in the public
  repo — ever.
- **Earliest attainable dates (ESTIMATES; assumptions stated):**
  - **(a) Free tier ($0):** assuming R7 and R30 GOs are given at
    eligibility (Oct 28 / Nov 20), S2 disposition lands within ~2 days
    of the R30 receipts (≈ Nov 22), gates 1–2 complete in parallel by
    then, capture GO is immediate, capture executes over 2 days
    (≈ Nov 23–24), and post-capture qualification passes first attempt
    (≈ 3–5 days) → **QUALIFIED dataset earliest ≈ Nov 27 – Dec 1,
    2026 (ESTIMATE)**. Any gate failing first attempt moves this
    right; the date is an estimate, not a commitment.
  - **(b) Paid tier (if Mike later authorizes one; price
    TO_BE_CONFIRMED_AT_AUTHORIZATION):** **the same window
    (ESTIMATE).** No binding constraint is credit-shaped (worst case
    264 < 800 free/day), and the waits are evidence-intrinsic (R7/R30)
    or decisions (freezes, adjudication) — all tier-independent. The
    record's only paid-tier relevance is /splits entitlement (Grow+)
    for the conditional producer leg (gate 4, KEEP branch); it does
    not accelerate the dataset.
  - **Scope-change variant (NOT this plan; recorded because -77 raised
    it):** authorizing capture before R30 closes could put UNQUALIFIED
    bytes on disk as early as ≈ Oct 29–30 (after R7) — the QUALIFIED
    date would not move, and doing so requires explicit adjudication +
    Mike GO recorded as a scope change, not a gate pass.

## 5. Decision list — Mike's GOs, in order

1. **Calendar adoption GO** (candidate 8d659dde… + core-hours
   disposition) → unlocks capture-manifest freeze.
2. **E3 PIT freeze** (A or B) → unlocks validation-freeze eligibility.
3. **R1–R5 session-handling freeze GO** (after Claude's re-review) →
   unlocks position-handling certainty for the baseline.
4. **R7 leg GO** (≤6 credits; on/after 2026-10-28T21:33:00Z) → unlocks
   +7-day revision evidence.
5. **R30 leg GO** (≤6 credits; on/after 2026-11-20T21:33:00Z) →
   unlocks the S2 disposition.
6. **[Conditional — S2 = KEEP] Split-event producer GO** (GATE-E1…E5
   build) → unlocks capture finalization on the KEEP branch.
7. **[Conditional] H3b constructor-guard GO** (only if validator-layer
   sufficiency is not accepted at re-review) → unlocks consumption of
   captured bytes.
8. **Capture authorization GO** (Twelve Data route; proposed ceiling
   300 credits; manifest incl. crypto convention + dev-end rule) →
   unlocks the pilot.
9. **Phase-1 GO** (after the pilot gate passes) → unlocks full capture.
10. **[Conditional] Paid-tier / plan-change GO** (only if the producer
    leg needs /splits Grow+ entitlement; price
    TO_BE_CONFIRMED_AT_AUTHORIZATION) → unlocks /splits entitlement.
11. **Corrected-baseline run GO** (after the QUALIFIED declaration and
    Claude's re-review, per Mike's sequence) → unlocks the first
    defensible corrected backtest.

## Disclosures

- This plan was produced offline from the committed record only; no web
  fetching, no vendor calls, no credits.
- UNCONFIRMED items, by design rather than omission: crypto bar counts
  and chunk counts (manifest convention unpinned); paid-tier prices and
  allowances (not in the record); all forward dates (estimates with
  stated assumptions).
- The plan deliberately does NOT propose relaxing any gate: the R7/R30
  wait is intrinsic to measuring bar revisions (-77 §2), and proceeding
  on partial evidence would be a scope change for adjudication + Mike,
  not a plan recommendation.
