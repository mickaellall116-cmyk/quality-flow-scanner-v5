# Stage B Execution Package — Clean Forward Collection and the Decisive Verdict

**Assembled:** 2026-10-26 · **Protocol:** Preregistration v0.3 §10 (F1–F7) and §11, as amended by the 2026-10-26 decisions (B1 REDUCED, B2 ECONOMICS-FIRST) · **Shared preconditions:** `preconditions_checklist.md` (same directory).

> **This package authorizes nothing.** Freezing v1.0 is not a collection GO; Stage A's GO is not Stage B's GO. Forward collection (Tier 4) starts only on Mike's separate, explicit GO for Tier 4 (gate G7), after F1–F5 below are verified passing. Collection start and the verdict are separate events: the verdict waits for sample size, not for a calendar date someone prefers.

---

## 1. What Stage B is

Clean forward capture of the **complete frozen strategy** (same rule set as Stage A: config pin `87b8285a…8706`, source commit `555ebb1` — signal, suppression, ranking, sector caps, position limits, sizing, exits) on data that does not exist yet, collected under the §10 protocol with full-state telemetry from the first bar, and judged **once**, when the §6 validity floors are met. Stage B is the decisive stage: it is the only tier with real (paper) fills and live parity checks, and §11's edge rule requires its H-SYS-1 PASS (with Stage A not FAIL) before "edge supported" may be said.

**Collection mode — must be declared in the Tier 4 GO.** The GO states one of:
- **Signal-only (default if the GO is silent):** every candidate fire is logged with full as-of state and its hypothetical entry/exit under the frozen rules; no positions are opened. The telemetry writer runs with `execution_authorized=False` and **refuses EXECUTION records** (a signal-only feed cannot establish fills — P8 design).
- **Paper-execution:** positions are opened/closed on paper under the frozen rules; EXECUTION records (order/ack/fill per leg) are written, and the resulting fill record is the evidence that can retire the §7/§8 fill assumptions (touch-equals-fill at TP1; E1's declared 0.05 ATR slippage) over time.

Neither mode is S1, and neither activates production: **S1 stays LAUNCH_HOLD and production stays PAUSED** under their own separate authorities, untouched by this package and by any Stage B result.

**Universe.** The frozen 43-name universe, plus forward Tier 3 new symbols selected by the same frozen mechanical rule as Stage A (checklist C5), generated before their collection starts. Tier 3 forward results join the Stage B verdict pool; Tier 3 on the DEV window remains supplementary and is never pooled with Tier 1 as if independent.

## 2. Preconditions — F1–F5 verified passing, then the GO

| Gate | Requirement | Verification before start |
|---|---|---|
| **F1** | Version lock: code, config, calendar, and the frozen protocol pinned by hash; freeze record complete (§15, P11 — including the numeric bootstrap seed and the P5 per-fill config hash) | Pin verification against the freeze record, logged. Collection may start as soon as F1–F5 pass and the version is locked — it does **not** wait for Stage A, and Stage A does not wait for it. Only the verdict waits |
| **F2** | **Feed qualification for the collection route**: route qualified under its own adjudication; raw data stays in the private environment | **OPEN DEPENDENCY — see §3.** No route is qualified today, and this package names no substitute |
| **F3** | Parity: the collector reproduces the frozen signal set on replayed inputs | **Zero decision mismatches** on the replayed-input test (the -16 standard: the earlier 201-mismatch failure mode, root-caused to a stored exit-price field, is the standing example of what this gate exists to catch). End-to-end candle parity is part of this: same 09:30 America/New_York session anchor, same DST handling, verified on actual OHLCV bars across a DST boundary and two window lengths — never on code intent |
| **F4** | Full-state telemetry journal live (P8) | Journal writing every candidate fire with full state from the first collection bar; append integrity verified (hash chain re-walked); a refused record leaves state/hash/lines byte-identical |
| **F5** | Missed-signal handling | Outages and missed signals are logged and counted as **unexecuted candidates, never dropped and never backfilled**; bars are used **as received, not later revisions** (the standing forward-test integrity rule: missed pending entries are unexecutable after an outage — no historical backfill) |
| **G7** | Separate explicit GO from Mike for Tier 4 collection start, declaring the collection mode (§1) | On record before the first collection session. The freeze, the B1/B2 decisions, Stage A's GO, and this package are each **not** this GO |

F6/F7 are not start gates; they are the standing duration and analysis-discipline rules in §5–§6.

## 3. OPEN DEPENDENCY — F2 feed qualification (Twelve Data pilot)

The candidate collection route is Twelve Data, and its qualification rests on the feed-measurement pilot **QF-EQUITY43-FEED-MEASUREMENT-PILOT-20261024-22** (5 symbols — NVDA, TSLA, AAPL, SPY, MELI — measuring the 1h feed itself: timestamps, coverage, revision behavior), frozen under its own protocol. State of the dependency at this package's assembly:

- Pilot sessions: **Mon 2026-10-26 → Fri 2026-10-30**; finalization + revision re-poll **Mon 2026-11-02, ~08:10 ET**; the pilot RESULT is due at finalization.
- A feed-qualification **verdict** additionally requires ChatGPT's post-pilot checklist (Issue #1 comment `6390693595`): **five complete sessions + independent review** before any feed-qualification conclusion. The pilot running is not the feed qualifying.
- Known complication, recorded not resolved here: the Mon Oct 26 session was **tripwire-held** (a Twelve Data staff reply on Basic-tier rights is under adjudication; the daemon made zero calls that day), and Mike's 2026-10-26 rights determination (pilot = API evaluation under Basic, narrowly) is posted for ChatGPT adjudication. Whether the pilot still produces five complete sessions, and whether the rights position supports an ongoing collection route (as opposed to a bounded evaluation), are questions the pilot's finalization and the F2 adjudication must answer on their own evidence. **This package presumes neither.**
- If Twelve Data does not qualify, F2 stays open until another route qualifies under its own adjudication (the standing pattern: free vendor terms have repeatedly failed on archival/redistribution rights; a purchased license is a hard gate at Mike's desk and is not proposed here). Stage B does not start on an unqualified route, on a "probably fine" route, or on DEV/Yahoo bytes relabelled as forward capture.

## 4. Collection runbook

1. **Daily operation (per session day):** collector runs the frozen code on the qualified route; every candidate fire — taken or not — is written to the P8 journal at decision time with the full SIGNAL_FIRE state (see §5); open positions accrue BAR_PATH records per bar; exits produce EXIT_DECISION records; EXECUTION records only in paper-execution mode. Bars are stored **as received** in the private archive environment only (append-only, hash-receipted); later vendor revisions are never substituted.
2. **Daily ops check (operations only, never performance):** journal integrity re-walk (hash chain, monotonicity, no gaps in signal_idx per symbol); collector liveness; outage log review; missed-signal count updated (unexecuted candidates, carried in the operations record). Parity spot-checks against replayed inputs continue under F3 discipline.
3. **Weekly (operations only):** floor projection updated **from candidate counts alone** (candidates, de-clustered events, closed trades, blocks, symbols — counts, never returns); any feed anomalies logged as operations facts (missing bars, timestamp irregularities) for the F2 file.
4. **Incidents:** collector outage → affected signals are logged as missed/unexecuted; there is no catch-up run and no backfill, ever. Feed defect discovered mid-collection → logged same day to Mike + bridge with exact evidence; collection continues or pauses only as the incident ruling states — the affected days' data are flagged in the record, and whether they count toward the verdict pool is a pre-analysis ruling by Mike + Muse, logged before the analysis date (never decided after seeing performance).
5. **No performance output at any point before the verdict analysis** (F7): no P&L, no expectancy, no win rate, no equity curve — for anyone, in any channel, including "just checking the plumbing" runs that compute trade outcomes. Interim looks cover parity and operations only.

## 5. Telemetry requirements (P8, from day one — non-waivable)

Telemetry cannot be reconstructed after the fact; a collection day without the journal live is a day that does not count, and starting collection before F4 passes makes the package invalid (§7). The journal is the pinned `qf_telemetry.py` implementation (checklist §4):

- **SIGNAL_FIRE** at every candidate fire, taken or not: entry-predicate values with thresholds and margins; **ADX / DI±; trend_score; SessionVWAP distance; relative volume; EMA geometry** (`ema_state`); rs with its benchmark as-of stamp (P3); **market-gate state**; signal grade; gate/disposition reasons; admission state (open slots, sector occupancy, planned heat before/after, rank margin); **every price level** (signal close, ATR, initial stop threshold, TP1 level, intended entry); disposition.
- **BAR_PATH** per bar of every open position: bar OHLC; geometry in force (entry, stop threshold, TP1, runner); threshold events (first TP1 touch, first stop-threshold breach, breach count, bars under threshold); MAE/MFE inputs.
- **EXIT_DECISION** at every exit decision: the decision bar's full OHLC **including its close** (the field whose absence in DEV made the overshoot split NOT_RECOVERABLE), runner and EMA55 values in force, the decision, exit reason, and the fill reference.
- **EXECUTION** (paper-execution mode only): order / acknowledgment / fill price + timestamps per leg.
- **Causality guards (fail-closed):** records only from finalized bars; decision_time = signal_time + bar duration; recorded_at ≥ decision_time; per-symbol monotonic append (no backfill); strict schemas — unknown fields refused, required fields non-null; each line hash-chained (prev_hash + record sha256); availability split ENTRY_OBSERVED / EXIT_FILL_OBSERVED under session-table binning (union calendar, 1,054 sessions through 2027).

## 6. Duration, accrual, and the single-verdict rule (F6/F7)

- **Accrual expectations (from DEV realized rates, §10 F6 as corrected):** ≈23.6 candidates/month → **≈7.5 closed trades/month**. The H-BUY floor (200 de-clustered events) arrives in months; the **H-SYS floor (100 closed trades) is expected at roughly 13–14 months** of collection. Minimum collection before any verdict analysis: **6 months**, regardless of counts.
- **Verdict trigger:** the single verdict analysis runs when **all** §6 floors are met (≥200 de-clustered events, ≥100 closed trades, ≥30 independent blocks, ≥20 symbols) **and** the 6-month minimum has elapsed — assessed from counts alone. The power report (checklist G3/C4) must be published before the analysis; UNDERPOWERED FOR PASS determinations are made then, not after.
- **One analysis, once:** the same frozen analysis code and verdict computation as Stage A (checklist §4; B2 economics-first grades; Holm for H-EXIT; fixed sequence for H-BUY; wider-of-two intervals; per-fill 25 bps gating cost; 4 bps descriptive). Open-at-boundary positions are excluded from closed-trade means and disclosed (count + marked equity, all-bar MTM). §12 diagnostics reported beside the verdicts, annotating only.
- **Edge rule (§11):** "Edge supported" requires **Stage B PASS on H-SYS-1 AND Stage A not FAIL**. A Stage B FAIL on H-SYS-1 is "edge rejected." Anything else is INCONCLUSIVE and is reported as that. No second analysis, no early analysis, no "updated" verdict: if the single analysis cannot be run as frozen, the stage reports a protocol deviation (see §7), not a substitute analysis.

## 7. Stop / report protocol and invalidity

**Operational STOPs (collection):** telemetry journal failure, parity mismatch discovered, feed-route rights or qualification revoked, or frozen-code/config drift → collection pauses the same day, the incident is reported to Mike + bridge with exact evidence, and resumption requires the defect to be closed on evidence (the -15 lesson: never report a PASS or a healthy state from a wrapper exit code — verify against the actual artifacts). Paused/missed periods are logged as unexecuted candidates under F5.

**Deviations:** any deviation from the frozen protocol (including any pre-analysis performance view, by anyone) is logged; the affected verdict defaults to **INCONCLUSIVE** unless Mike + Muse declared the deviation immaterial before the analysis ( §11). There is no silent absorption of a deviation into "operations."

**What would make Stage B INVALID to run:**
- Collection started before any of F1–F5 verified passing, or without the separate Tier 4 GO (G7) declaring the mode.
- Collection on an unqualified feed route, or on a route whose rights position does not cover the collection's storage/use (P10) — including presuming the Nov 2 pilot outcome.
- Telemetry not live from the first collection bar, or journal integrity broken and unlogged.
- Any backfilled signal, substituted revised bar, or dropped missed-signal record.
- Any performance output viewed before the single verdict analysis (F7 breach).
- The frozen rule set, universe rule, δ values, floors, or cost model altered after F1 — each alteration is a new rule version, and Tier 4 evidence collected under the old version cannot be re-labelled for the new one.
- Treating Stage B collection, or any Stage B result, as authority for S1 launch or production activation — both remain under their own separate gates regardless of outcome.
