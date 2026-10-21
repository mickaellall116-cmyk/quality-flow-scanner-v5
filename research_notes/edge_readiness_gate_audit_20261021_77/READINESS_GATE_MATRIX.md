# QF-EDGE-READINESS-GATE-AUDIT-20261021-77 r1 — READINESS_GATE_MATRIX

**Terminal: EDGE_READINESS_GATE_AUDIT_COMPLETE__READINESS_HOLD__QUALIFIED_4H_COVERAGE_0_OF_51**

Offline, evidence-only audit. Zero vendor calls, zero credits, no data acquisition, no
performance computation, no holdout access (metadata only), no production/trading changes.
Spec: GitHub Issue #1 comment 6328132269 (SENT 2026-10-21T22:39:41Z); Slack TS
1792622389.422019. Every factual claim below carries its pinned source; anything not
recomputed in this audit is labeled with the audit that produced it and its date.

## 0. Frozen anchors (pins)

- Universe UX51 (UNIVERSE_X), 51 symbols, definition_sha256
  `d139d7bf21165c79cb112a091cdcf7b021b86bd06f2165e07fb75932e6fa27dc`
  (complete_manifest_rev2.json, CP1 bundle 03_manifests; set-equality verified in -21).
  Symbols: AAPL, AMAT, AMD, AMZN, APP, ARKK, ARM, ASTS, AVAX-USD, AVGO, BTC-USD, COIN,
  CRM, CRWD, DDOG, DOGE-USD, ETH-USD, F, GOOGL, HOOD, INTC, IWM, LINK-USD, LRCX, LUNR,
  MELI, META, MRNA, MSFT, MSTR, MU, NET, NFLX, NIO, NU, NVDA, PFE, PLTR, PYPL, QCOM,
  RKLB, SHOP, SMCI, SMH, SNOW, SOFI, SOL-USD, SPY, TSLA, XLF, XRP-USD.
- Validation preregistration (frozen, -25): HOLDOUT_WINDOW = 2023-10-19 … 2024-09-15
  (sealed; supplying a holdout session to the materializer is a hard HOLDOUT_TOUCH
  error); DEV_START 2024-09-16; expanding train ≥252 sessions; fixed non-overlapping
  63-session OOS blocks; formal inference only at n=100 signals; Holm family = exactly
  6; economic gates govern (a p-value can never rescue a failed economic gate).
  Source: research_notes/validation_prereg_finalization_20261018_25/PREREGISTRATION.md.
- Qualified calendar: XNYS_SESSION_SCHEDULE_V2, sha256
  `3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88`, 524 sessions,
  span 2024-09-16 → 2026-10-16, parity 48/48, commit 9c62e25 (-35 r2).

## 1. Historical coverage ledger (by source)

| Source | Bytes today (recomputed 2026-10-21) | Span / shape | Qualification |
|---|---|---|---|
| D1 Yahoo 1H→4H `backtest_cache/v3` (52 h4 files: 51 UX51 + QQQ) | **ABSENT — destroyed** (verified: no `backtest_cache/` on this VM). SHA-256 pins survive for 52/52 files (CP1 bundle `01_cache_grid/h4_cache_hashes.json`). 1H input manifest (2026-10-04): window 2024-10-07 → 2026-09-14, rows/file 2226–3375. | As-run 4H store 2024-09-15 → 2026-09-15 (-07 map) | **UNQUALIFIED + ABSENT.** Even before destruction, CP1 found the grid defective (fixed-UTC anchor; 332 EST bars mislabeled). All D1 derivatives (240-trade baseline, −15.23R replay, C1 +0.178R) are evidence about lost bytes only. |
| D2 Yahoo watchlist 4H cache (`pine_entry_timing_backtest/cache/`) | **PRESENT** — 14 files verified on disk today: AMD ANET ASTX BBAI DRAM HOOD NIO ONDS PLTR QQQ RKLB SMCI SOFI SPCX. Of these, 7 are UX51 (AMD, HOOD, NIO, PLTR, RKLB, SMCI, SOFI). | 2023-10-25 → 2026-09-23, 1453 rows typical (ASTX 604, from 2025-07-11) — per -07 diagnostics 2026-10-15; grid ET-clean per -07 | **DIAGNOSTIC_ONLY.** Wrong universe (watchlist ≠ UX51); adjustment policy unpinned. Not baseline-eligible. |
| D3 Tiingo EOD (VCP phase-1a store) | **PRESENT** — 444 eod files verified on disk today; 16 of 51 UX51 symbols present (per -07 coverage_matrix.csv) | Daily bars, 2009 → 2026-09-30 (-07) | **UNQUALIFIED for the 4H contract:** interval mismatch (daily, contract needs 1H→4H), raw+adjusted fields both present (policy-ambiguous vs frozen `auto_adjust=False`), terms HOLD (persistence barred). |
| D4 Twelve Data spot + probe | Stage-0 AAPL snapshots (1h+4h, 28 days); SPOT8 pilot receipts; -75 Day-1 probe raw bodies archived in qf-data-archive `captures/td_probe_day1_20261021/` @ `2f223cf9a478283951c5b4eb6f36f254a745b4bd` (independently accepted, -76, comment 6328021675) | Sampled 1h windows only: NVDA 2023-12-13→2024-06-21; TSLA 2022-03-07→2022-09-09; AAPL dividend-window control | **Qualification evidence only — not baseline history.** SPOT8: 6 COMPLETED / 1 ERROR_EVIDENCE (REQ-SPT-07, HTTP 400) / 1 NOT_ATTEMPTED; **P2 HOLD (persistent)**. -75 verdicts: NVDA sampled PASS; TSLA **DATA_UNQUALIFIED** (C2); AAPL structural PASS. |
| D5 Live forward artifacts (`v54_forward/`) | Present (signal ledger, state) | Operational records, not a price-history archive | Not a data source for a baseline. Feed evidence only (see §3). |
| D6 Canonical re-baseline inputs (Sep 2026) | **ABSENT** — runtime pulls never archived; engine code not in git (.pyc only) (-07) | 131 symbols, unrecoverable | **ABSENT.** |
| D7 Sealed holdout (11-month, 4H UX51) | **No holdout files exist on this VM** (identity-only; -07, -21, -25 agree). Contents not opened, hashed, or enumerated in this audit. | Window pinned by -25 prereg: 2023-10-19 … 2024-09-15 | **SEALED.** Openable at most once, only after (a) independent checkpoint approval on the bridge and (b) a pinned qualified dataset + calendar exist (-25 §50). |

**Qualified, contract-conformant 4H coverage of UX51 today: 0 of 51 symbols, 0 sessions.**
Data *present* (any form): D2 7/51 (4H, diagnostic), D3 16/51 (daily, terms HOLD),
D4 3/51 sampled windows (qualification only). 30 UX51 symbols appear in neither D2 nor D3
(per -07 matrix): ARKK, ARM, ASTS, AVAX-USD, BTC-USD, DOGE-USD, ETH-USD, IWM, LINK-USD,
LRCX, LUNR, MELI, META, MRNA, MSTR, MU, NET, NFLX, NU, NVDA, PFE, PYPL, QCOM, SHOP, SMH,
SNOW, SOL-USD, TSLA, XLF, XRP-USD.

### The 2023 gap — persists, and is now structural

- Contract span target starts 2023-01-01 (prereg rev2, via -07 contract map). No held
  source covers 2023 at 4H for UX51: D1 began 2024-09-15; D2 begins 2023-10-25 for 7
  UX51 symbols and is diagnostic-only; the sealed holdout window itself
  (2023-10-19 → 2024-09-15) has **zero bytes on this VM**.
- Yahoo 1H reachback is ~730 days (prereg rev2, via -07): from Oct 2026 the earliest
  reachable Yahoo 1H is ≈ Oct 2024. **Pre-Oct-2024 Yahoo 1H is no longer acquirable at
  any authorization level** — the 2023 gap cannot be closed by a Yahoo re-capture.
- Twelve Data served 1h bars back to 2022 in the -75 sampled windows (TSLA leg), so a
  TD route is the only *demonstrated* path to 2023-era 1H — but TD history is
  unqualified beyond those windows, TSLA is DATA_UNQUALIFIED, and no TD capture of the
  51-symbol history is authorized.
- Consequence: the frozen design's DEV_START (2024-09-16) is reachable in principle;
  the sealed holdout window is currently **unpopulatable from held or Yahoo-reachable
  bytes** — a fact any future holdout-opening decision must face explicitly.

### Calendar coverage gap

The qualified calendar artifact spans only 2024-09-16 → 2026-10-16 (524 sessions).
There is **no qualified calendar for 2023-10-19 → 2024-09-15** (the holdout window) —
holdout exclusion can be enforced by date rule in the materializer, but session-level
parity for that window has no qualified artifact. Separately, the `ab254c3`
closed-session classifier (candidate pinned at commit
`ab254c3458697dd450356146abcf4ad4f75ecef4`) remains **integration HOLD**: -38 r1
DEPENDENCY_ARTIFACT_MISSING — the pinned calendar library (PMC 5.5.0 wheel + closure)
is absent in the standing environment, so the classifier that consumes calendar data
is not integrated. The calendar artifact itself is qualified; its consumer chain is not.

### Documentation inconsistency (disclosed, not resolved here)

The -25 package's READINESS_MATRIX.json rows 4.3/4.4 still carry the pre-governance
text ("exact window MISSING / no committed record states the window") while the same
package's PREREGISTRATION.md pins HOLDOUT_WINDOW = 2023-10-19 … 2024-09-15
("re-pinned by governance record in -24"). This audit treats PREREGISTRATION.md as
governing; the stale matrix rows should be corrected by a governance record, not
silently relied on in either direction.

## 2. Readiness gates & earliest route (dependency order)

### (a) Offline implementation-only replay / dry run — NOT edge evidence
Achievable with existing pinned components (fold materializer -25, construct_4h,
calendar artifact 3358f2d9…, route proof -49…-58 closed PASS on synthetic fixtures).
Blockers: none for a *fixture-only* dry run. It proves plumbing/parity mechanics only.
Status: **route exists; no new authorization needed for synthetic work; proves nothing
about edge.**

### (b) Corrected DEVELOPMENT baseline — blocked, in order
1. **S2 disposition after Day-1 evidence** (adjudication): NVDA sampled PASS vs TSLA
   DATA_UNQUALIFIED under frozen C2. -76 independent finding: TSLA's 166 zero-volume
   paired bars span 29 dates and **all 166 show nonzero OHLC range and changed
   open/close** — consistent with missing/zeroed volume data, NOT with no-trade bars.
   C2 is frozen; it may not be retroactively waived or imputed (spec + -75 adjudication).
   Until adjudication rules, the TD feed's volume basis is unqualified.
2. **E3 PIT rule freeze** (Mike/ChatGPT decision, still open): (A) decision-time
   `announced_at` ≤ earliest affected decision, vs (B) retrospective exclusion labeled
   non-tradable, applied symmetrically. No silent middle. Blocks any real-data
   validation freeze.
3. **C5 revision evidence (R7/R30)** — see §3 for earliest instants; authorization
   absent. Without it, TD bar-revision behavior is unobserved.
4. **A capture authorization + execution** for a pinned, qualified 51-symbol history
   (route undecided: TD is the only demonstrated 2023-capable route and is itself
   gated by 1–3; the Yahoo clean-capture route is PARKED, its executor candidate
   READY_FOR_SEPARATE_ADOPTION but not adopted, no capture ever run, and Yahoo cannot
   reach pre-Oct-2024 1H regardless). Storage target exists (qf-data-archive,
   designated 2026-10-15).
5. **End-to-end parity gate** on the captured bytes (byte-identical candles backtest
   vs live construction across a DST boundary and two window lengths — standing rule
   from the 2026-10-03 candle failure) + full portfolio-decision parity.
6. **ab254c3 classifier integration** (pinned PMC 5.5.0 closure) if the TD route is
   the baseline source.
Only after 1–6: materialize folds on qualified timestamps (exact fold dates do not
exist until then, by -25 design) and compute the development baseline.

### (c) Credible OOS / multiple-testing-controlled edge test — blocked behind (b), plus
- Minimum data under the EXISTING frozen design: dev span from 2024-09-16 with
  ≥252-session expanding train before the first 63-session OOS block. Arithmetic on
  the pinned calendar (524 sessions, 2024-09-16→2026-10-16): at most
  floor((524−252)/63) = **4 full OOS blocks** exist in the qualified-calendar span —
  and that is an upper bound that assumes qualified price bytes for the full span,
  which do not exist (0/51). Formal inference additionally requires n=100 signals in
  the evaluated family; the frozen Holm family is exactly 6; failure memory and the
  family accounting stay intact (no new family members after seeing results).
- The sealed holdout remains the final confirmation and is single-use; it cannot be
  opened until a pinned qualified dataset + calendar exist, and its window currently
  has no populatable bytes (§1) — so the honest OOS path today is the walk-forward
  dev/OOS design, with the holdout question deferred to an explicit governance
  decision, not assumed away.

### Can any valid route bypass the TD +7/+30 wait WITHOUT relaxing requirements? — No.
C5 tests whether Twelve Data revises already-served bars; revision behavior at +7d is
unobservable before +7d elapses — the wait is intrinsic to the measurement, not a
procedural delay. No other held source answers a TD-specific revision question (Yahoo
provides no version evidence and its capture route is parked/never run; Tiingo is
terms-HOLD and daily-only). Proceeding on C1–C4/C6 alone would mean deciding S2 with
one frozen gate unobserved — a scope change that belongs to ChatGPT adjudication +
Mike, and would have to be recorded as such, not presented as the frozen gate set
passing.

## 3. Current leads (recorded evidence only)

- **Yahoo r2 feed recovery (operational, recorded):** post-deploy ordinary scheduled
  cycles 563 (2026-10-14T22:51:03Z, 250/250 fresh, 535.3s) and 564 (23:51Z, 250/250,
  468.4s) met the pre-registered bar of two consecutive HEALTHY 250/250 cycles <600s;
  565/566 corroborating (FEED_RECOVERY_OBSERVATION_PIN_20261014.md). Closure package
  (yahoo_r2_observation_closure_evidence_20261015/) pins raw run 567/569 bodies
  (HEALTHY, 250/250, 466.6s coverage), live harness sha dc3ee392…, pre-deploy rollback
  file sha 11829353…, state pins. Scope: feed/harness recovery only — **not** data
  qualification, not a baseline source (no bar archive retained; D5).
- **TD archive -76:** independently accepted (comment 6328021675); archive commit
  2f223cf…; NVDA sampled PASS and AAPL structural control stand; TSLA DATA_UNQUALIFIED
  stands (see §2b-1 for the -76 zero-volume finding). C5/R7/R30 and performance remain
  HOLD.
- **R7/R30 earliest eligible instants** (from the immutable -75 receipts):
  preflight receipt_ts 2026-10-21T21:33:00.042Z; data receipts 21:33:00.7–21:33:02Z.
  Anchoring on the Day-1 receipt instant 2026-10-21T21:33:00Z:
  **R7 ≥ 2026-10-28T21:33:00Z; R30 ≥ 2026-11-20T21:33:00Z.** Authorization for both
  legs is **absent** — eligibility is not a GO.
- **ab254c3 unpinned-calendar blocker:** classifier candidate pinned (ab254c3…);
  integration HOLD for the absent pinned PMC 5.5.0 wheel + closure (-38 r1). The -35
  calendar artifact does not by itself close this — the dependency is the classifier's
  library closure in the standing environment.

## 4. One ranked next offline action

**RANK 1 — Qualified-calendar backward-extension audit (offline, desk-only).**
Determine, from already-pinned evidence only, whether a qualified XNYS calendar can be
generated for the missing span 2023-10-19 → 2024-09-15 under the existing -34/-35
contract, and exactly which sessions/dates the pinned official-calendar evidence does
or does not cover.
- Exact input pins: -34 generation contract + -35 r2 artifact
  `3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88` (commit 9c62e25);
  NYSE_OFFICIAL_CALENDAR_CAPTURE_20261018_31.md (-31 capture record); -25
  PREREGISTRATION.md holdout window (2023-10-19 … 2024-09-15).
- Pass/fail stopping rule: PASS only if the pinned official-calendar evidence covers
  every session in 2023-10-19 → 2024-09-15 (closures + early closes enumerable without
  new acquisition). On the first uncovered date, STOP and report the exact uncovered
  span — no new capture, no vendor call, no generation run inside this action.
- Expected artifact: a committed coverage memo (per-date coverage table + verdict)
  under research_notes/, feeding the (b) dependency chain at step 5/6 and the
  holdout-populatability question in §1.
- Requirements: user decision **no** (offline audit inside standing auto scope);
  vendor credits **no**; Claude independent checkpoint **not required** (ChatGPT
  adjudication of the memo suffices).

## 5. What this audit does NOT claim

No performance result, no strategy edge, no Yahoo recovery beyond the recorded
operational cycles, no TD data qualification beyond the sampled -75 windows, no S2
verdict, no baseline readiness. Readiness verdict: **HOLD** — the earliest defensible
edge test waits on, in order: S2/C2 adjudication → E3 PIT freeze → R7 (≥2026-10-28)
and R30 (≥2026-11-20) legs under separate GOs → a capture authorization for the only
demonstrated 2023-capable route → parity gates → fold materialization on qualified
timestamps. No ETA is stated; several steps are decisions, not engineering.

— Muse
