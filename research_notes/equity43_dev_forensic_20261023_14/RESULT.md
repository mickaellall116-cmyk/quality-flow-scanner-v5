# RESULT — QF-EQUITY43-DEV-FORENSIC-20261023-14 r1

**Task:** independent forensic review of the -13 package `521980a`
(QF-EQUITY43-DEV-ORDER-CENSOR-20261023-13), per GitHub Issue #1 comment
6376686140 (ChatGPT independent ledger audit). **Labels preserved throughout:
EQUITIES-ONLY DEV EXPLORATORY / G4 UNADOPTED / NOT VALIDATED EDGE.** The frozen
C1 FAIL (2026-10-03) is unchanged. Every figure below is **descriptive**,
recomputed from the committed -13 records — not an edge claim, not a
replication of the run.

**Method / bounds:** offline only. Inputs: committed `trade_ledger.json` (590
candidate rows), `results.json`, `run_stdout.txt`, `run_study13.py` from
package `521980a` (its SHA256 manifest re-verified 6/6 by this review), the
pinned engine trees in the -13 stage, and ChatGPT's published figures as
reconciliation targets. NO new performance or sensitivity run was executed; NO
holdout bytes were inspected (HO appears only as chain/hash metadata in the
-13 record); NO vendor calls or credits (program TD total unchanged at 115
desk); PAUSED production pins identical before/after (harness
`ce7c902c…`, PAUSE_NEW_ENTRIES present, RESUME absent). The audit script is
committed as `reconcile_ledger.py`; its full output is `attribution_state.json`.

---

## 1. Reconciliation against ChatGPT's independently computed figures — ALL MATCH

| figure | ChatGPT | this review (from committed ledger) | verdict |
|---|---|---|---|
| candidate rows | 590 (586 closed, 4 censored) | 590 / 586 / 4 (CRM, MRNA, PFE, SHOP) | MATCH |
| 4bps closed / wins | 187 / 90 (48.1%) | 187 / 90 | MATCH |
| 4bps exits | 161 stop / 26 EMA55 | 161 stop / 26 ema55-break | MATCH |
| 4bps sum / avg / PF | +32.4873R / +0.173729R / PF 1.282956 | +32.4873R / +0.173729R / PF 1.282956 | MATCH |
| per-candidate cost ordering | monotone, 0 violations (586) | gross ≥ 4bps ≥ 25bps on all 586 closed, 0 violations | MATCH |
| common closed | 182; +28.6835R gross / +26.3843R net-4bps | 182; +28.6835R / +26.3843R | MATCH |
| gross-only closed | 6, sum −0.5023R | 6, sum −0.5023R | MATCH |
| 4bps-only closed | 5, sum +6.1030R | 5, sum +6.1030R | MATCH |
| first taken-set divergence (gross vs 4bps) | QCOM 2026-09-08 13:30 ET, gross only | QCOM signal_idx 985, 2026-09-08 13:30 ET, gross only; 0 flag diffs in the 550 earlier candidates | MATCH |
| SHOP terminal open | at 4bps, absent gross | SHOP censored: taken 4bps + 25bps, NOT gross | MATCH |
| top-5 winners (4bps) | SNOW +8.0874, INTC +6.4172, AMD +5.9181, QCOM +5.3470, LRCX +4.8903 = +30.6600R | identical five, identical values, sum +30.6600R | MATCH |
| top-5 share | 94.37% of +32.4873R | 94.37% | MATCH |
| entry-year split (4bps) | 2025 +3.3768R / 95; 2026 +29.1105R / 92 | identical | MATCH |
| gross equity decomposition | 12696.6283 realized + 876.6512 marks = 13573.2795 | realized_equity 12696.6283, final 13573.2795 in results.json; marks independently summed from the terminal inventory (MRNA 535.5323 + PFE 323.2551 + CRM 17.8638) = 876.6512 | MATCH (both routes) |
| 4bps equity decomposition | 13273.4476 + 970.1233 = 14243.5709 | realized 13273.4476, final 14243.5709; inventory sum (MRNA 524.3684 + SHOP 90.5440 + PFE 336.4671 + CRM 18.7439) = 970.1233 | MATCH (both routes) |
| 25bps equity decomposition | 11724.9128 + 869.6410 = 12594.5537 | realized 11724.9128, final 12594.5537; inventory sum = 869.6410 (SHOP present) | MATCH (both routes) |

Additional view statistics regenerated for the record — gross: 188 closed,
88 wins, +28.1812R, PF 1.238969, 162 stop / 26 EMA. 25bps: 185 closed, 87 wins,
+19.8892R, avg +0.107509R, PF 1.165550, 159 stop / 26 EMA. C0 fidelity anchor
in the committed record: final equity 12321.3876 on both simulator paths.

No mismatch required attribution; nothing was smoothed.

## 2. First-divergence attribution — the gross-vs-4bps inversion

**Verdict: PROVEN at gate level from the committed records. The inversion is
100% allocation-path effect; per-trade, costs never helped (0 monotone
violations in 586). One dollar-exact sub-item is BLOCKED on missing telemetry
(§2.4, with a narrow proposed gate).**

### 2.1 The exact R-bridge (arithmetic identity on the committed ledger)

Δ(4bps − gross) = **+4.3061R** = friction on the 182 common trades
(26.3843 − 28.6835 = **−2.2992R**) + allocation effect (4bps-only +6.1030R
minus gross-only −0.5023R = **+6.6053R**). On identical trades the lower-cost
view wins by exactly the friction, as it must. The portfolio-level inversion
comes entirely from the two views holding *different* trades after
2026-09-08.

### 2.2 The first divergence — QCOM, 2026-09-08 13:30 ET (signal_idx 985)

State at the instant, reconstructed from the ledger (in `attribution_state.json`):

- Taken sets gross↔4bps are **identical for all 550 earlier candidates**
  (176 taken per view). The *dollar* paths already differ: every earlier
  closed trade netted less at 4bps, so marked equity and every open
  position's risk dollars (sized at 1% of marked equity at *its* entry,
  along each view's own path) differ by view before any set divergence.
- Cohort at the instant: QCOM (SEMIS, rs 0.099) and TSLA (rs 0.025).
- Both views hold the **identical open set** {CRM (AI_SOFTWARE), MRNA
  (HEALTHCARE), MSTR (CRYPTO), NU (FINTECH)} — 4 of 5 slots, SEMIS count 0.
  Slot cap and sector cap are therefore **provably non-binding** in both views.
- Recorded 4bps disposition for QCOM: **skipped_risk**. Gross: taken
  (outcome +1.8065R gross — the first divergence actually favored gross).
- The only inputs that can differ are dollar-denominated: marked equity and
  Σ open risk dollars entering the 5% portfolio heat test (heat vs
  5% × marked equity), plus QCOM's prospective risk dollars. Under the gross
  path the heat test passed; under the 4bps path it failed. **Mechanism:
  marked-equity path dependence inside the risk gate** — costs change cash
  flows, cash flows change the equity path, the equity path changes both the
  heat numerator (positions sized off different entry-date equities) and the
  cap denominator, and at this instant the ratio straddled the cap.

### 2.3 The cascade (12 divergent events, 2026-09-08 → 2026-10-09)

All 12 gross↔4bps divergences occur in one five-week late-window cluster;
every one at a 13:30 ET coincident-timestamp allocation event. Full
per-event open sets, sector counts, and cohorts are in
`attribution_state.json`. Summary (4bps dispositions are RECORDED in the
ledger; gross-side gates are NOT recorded — the ledger carries only
`disposition_4bps_c1` — so gross-side attribution is classed):

| entry (ET) | sym (sidx) | gross | 4bps | 4bps disposition (recorded) | gross-side attribution |
|---|---|---|---|---|---|
| 09-08 13:30 | QCOM (985) | taken | skip | skipped_risk | taken (passed all gates) |
| 09-10 13:30 | META (989) | skip | taken | taken (+2.3050R) | state-exclusion: slot free (4/5), sector free, top rs of cohort → risk gate is the remaining candidate — INFERENCE |
| 09-14 13:30 | INTC (993) | skip | taken | taken (+2.3335R) | state-exclusion (slot free, SEMIS 1<2, top rs) → risk gate — INFERENCE |
| 09-16 13:30 | CRWD (997) | taken | skip | skipped_risk | taken |
| 09-17 13:30 | ARKK (999) | skip | taken | taken (+0.9854R) | state-exclusion (slot free, sector free, sole candidate) → risk gate — INFERENCE |
| 09-21 13:30 | GOOGL (1003) | taken | skip | skipped_rank | 4bps book FULL (5 opens incl. ARKK/INTC/META) — mechanical |
| 09-23 13:30 | HOOD (1007) | taken | skip | skipped_rank | 4bps book full — mechanical |
| 09-30 13:30 | RKLB (1017) | skip | taken | taken (+0.1623R) | state-exclusion (slot free, sector free, top rs) → risk gate — INFERENCE |
| 10-05 13:30 | PLTR (1023) | taken | skip | skipped_rank | 4bps book full — mechanical |
| 10-07 13:30 | GOOGL (1027) | skip | taken | taken (+0.3168R) | gross book FULL (5 opens) — state-proven |
| 10-08 13:30 | SHOP (1029, censored) | skip | taken | taken (terminal mark +90.5440) | **STATE-PROVEN: sector cap** — gross held 2 AI_SOFTWARE opens {CRWD, PLTR} (cap 2), slot free (3/5), sole candidate |
| 10-09 13:30 | CRWD (1031) | taken | skip | skipped_gate (sector) | taken |

Reading of the cascade: after the QCOM risk-gate flip, the two books hold
different positions, so different slots/sectors/heats bind at every later
coincident instant — including *mechanical* full-book rank skips on the 4bps
side (GOOGL/HOOD/PLTR) caused by the 4bps book having taken META/INTC/ARKK.
The divergent sets' quality is asymmetric by outcome, not by construction:
the five 4bps-only closed trades are **5/5 winners** (+6.1030R); the six
gross-only closed trades split 3 winners (+3.9233R) / 3 losers (−4.4256R) =
−0.5023R — and QCOM itself, the trade that started the split, was a +1.8065R
winner the 4bps view *missed*. Cross-view noise confirms path chaos rather
than a quality signal: CRWD (997) was taken at 25bps while skipped at 4bps,
and the first gross-vs-25bps divergence dates to NIO 2025-07-16. Nothing here
is a cost effect; it is small-number path dependence in a concentrated book
(§3), stated descriptively.

*Disambiguation (prevents a natural misreading):* the top-5 QCOM (+5.3470R)
is signal_idx 803, entered 2026-04-28, taken in ALL views; the top-5 INTC
(+6.4172R) is entered 2025-08-18, taken in all views. Neither is a divergent
trade. The divergent QCOM (985) and INTC (993) are different candidates.

### 2.4 BLOCKED sub-item + proposed gate (not executed)

The exact dollar values at the QCOM instant — per-view marked equity,
Σ open risk dollars, QCOM prospective risk dollars, and the resulting heat
ratios — exist in **no committed record**: the -13 driver emits no per-event
equity/gate telemetry, and the ledger carries risk dollars only for terminal
inventory. Consequently the realized-dollar gap (+576.8193) cannot be split
exactly into friction / sizing / allocation components from committed records
(the marks gap *can*: Δmarks +93.4721 = SHOP only-at-4bps +90.5440 + shared-open
sizing deltas MRNA −11.1639, PFE +13.2120, CRM +0.8801 — exact). The R-bridge
in §2.1 is the exact causal split the records support.

**Proposed narrow gate (for adjudication; NOT executed):** a telemetry-only
replay of the pinned -13 driver (`run_study13.py` sha256 4962e30d…) on the
pinned archive bytes, with an observer wrapper OUTSIDE the simulators
emitting per-event (marked equity, open risk dollars, gate inputs/outputs)
for all three views. Acceptance criterion fixed in advance: every output
field of the existing -13 package must reproduce byte-identically before the
new telemetry is admitted as evidence; no configuration or parameter change;
DEV bytes only. Estimated scope: one bounded offline task.

## 3. Concentration — the result is five trades

Top-5 4bps winners (SNOW 2026-05-27 +8.0874R; INTC 2025-08-18 +6.4172R; AMD
2026-04-02 +5.9181R; QCOM 2026-04-28 +5.3470R; LRCX 2025-12-18 +4.8903R) sum
to **+30.6600R = 94.37%** of the +32.4873R total. The remaining **182 closed
trades sum to +1.8273R (average +0.0100R)** — flat. The year split is the same
story in another cut: 2025 contributes +3.3768R over 95 trades (with two of
the top five), 2026 contributes +29.1105R over 92 (with three). Descriptively,
the DEV exploratory result is a handful of concentrated winners riding on an
otherwise flat book, exactly as ChatGPT's audit framed it. No ex-post
removal, filter, or exclusion is proposed or was tested — that would be
tuning on the same data, and it is out of scope by the governing text.

## 4. Source auditability — code-only lineage, pinned and published

This package closes the reproducibility boundary ChatGPT flagged: the -13
package pinned the simulator hashes but did not include inspectable
snapshots. Included under `code/` (simulator code ONLY — no market data):
snapshots of `engine_fork09` and `engine_successor` for both simulator files
plus the shared `asof_benchmark.py`, four unified diffs (orig→fork09 and
fork09→successor for each simulator), and `code/PINS.md` with the full hash
table. Verified by this review:

- Successor pins match `results.json` P0 AND the executed stage files:
  `pine_backtest.py` 874d2a9b…, `pine_stack.py` 8d4a964f…; fork09 pins
  becea082… / 30594231…; asof_benchmark f0f4582c… (unchanged -09 → -13).
- Committed `run_study13.py` is byte-identical to the executed stage copy
  (4962e30d…). The -13 package manifest re-verifies 6/6.
- **Strategy sources are byte-identical across orig / fork09 / successor:**
  scanner_rules.py 62aa743a…, pine_ranking.py 77afae0d…,
  pine_signal_quality.py b1b39ee8…, pine_exposure.py 9f646161c…. The trading
  strategy never changed in this lineage.
- What changed, exactly: orig→fork09 (-09) = B2 as-of mark fix in both
  simulators + canonical (-rs, symbol, signal_idx) tie key in the stack
  (B1 benchmark as-of lives in asof_benchmark.py). fork09→successor (-13) =
  right-censored terminal-candidate treatment + terminal as-of accounting +
  per-candidate ledger/disposition returns in both simulators; the canonical
  (symbol, signal_idx) candidate order is applied by the -13 driver, which
  sorts the candidate list before BOTH simulator paths (configuration pinned
  in -13 results.json, config sha 87b8285a…).

## 5. Blockers / next gate — one-page disposition

- **G4/VBASIS — UNADOPTED, unchanged by -13/-14.** Every Twelve Data leg
  still prints CONVENTION_BREAK_SUSPECT from the volume-basis leg alone
  (candidate checker, unadopted; the -02 calibration evidence stands: flags
  fire with no basis event, e.g. SPY 44 flags). Until the G4/checker
  adjudication — including the VBASIS calibration question — is decided,
  all DEV inputs and results remain **candidate-grade**: no QUALIFIED label,
  no validation claim, no promotion path. Decision: ChatGPT adjudication,
  then Mike.
- **Holdout coverage — the frozen 44-name W_HO cannot currently be fielded.**
  Both-window candidate coverage is 19/44; **25/44 HO legs are
  NOT_EVALUABLE_PROVIDER_VOLUME**. The defect is one vendor window: 145
  price-moving zero-volume bars total (SMCI 19 + PLTR 3 + 123 across the -11
  census), **all inside 2024-04-04 → 2024-04-22**, zero outside it. A future
  W_HO evaluation therefore needs one of: (a) a second-source cure for the
  April-2024 slice only; (b) a disclosed reduced-universe holdout under a new
  governed freeze (breaks frozen-universe comparability — a decision, not a
  default); or (c) deferral. The holdout remains **sealed**: -13 and this
  review opened no HO returns or signals.
- **SMCI — absent, not imputed.** The DEV study ran 43/44 for a stated
  reason (TD HO volume defect; DEV leg unattempted under its disposition).
  The Alpaca one-month sample card exists but is gated behind a license
  screen that FAILED (persistence not affirmative, prep package a3ec37e)
  plus a separate GO. Disposition B1/B2/B3 remains Mike's decision.
- **Forward observation — bounded readiness only, no claim beyond evidence.**
  Evidenced today: shadow-lane design + offline code closeout PASS
  (2026-10-22/23); corrected-grid parity proven on real DEV bytes (-12/-13
  preflights); hash-chained capture/logging pattern proven end-to-end. NOT
  yet evidenced — what a successor task (-15) must still prove: a live
  corrected-grid 1h byte route (those bytes do not exist; the live harness
  keeps 1h in memory only), session-table re-pin beyond its 2026-10-16 end,
  fail-closed behavior on live frames, and a supervised first cycle. Any
  launch additionally requires Mike's explicit GO naming a future T0. This
  review makes no readiness claim beyond the evidence list.
- **True independent decisions still outstanding:** (1) G4/VBASIS adoption +
  calibration; (2) holdout route (a)/(b)/(c); (3) SMCI disposition; (4)
  forward-observation launch GO + T0; (5) whether to authorize the §2.4
  telemetry gate for a dollar-exact attribution at the QCOM instant (the
  gate-level attribution is already proven; this is completeness, not a
  blocker for the study's own verdict).

## Process disclosures

- The bridge ACK for this task landed as commit `6081f7b` after two empty
  commits (`b82784d`, `a453299`) caused by path-resolution slips in the
  staging commands; the final ACK content was verified on the remote tree.
  No content was lost; the slips are recorded here per standing practice.
- This review ran in parallel with task -15 in a separate lane; no -15
  stage, package, or code was touched.

**Bottom line:** ChatGPT's ledger audit reconciles exactly (15/15 figure
groups). The headline inversion is explained: friction cost the 4bps view
−2.2992R on shared trades, and a single risk-gate flip at QCOM 2026-09-08 —
driven purely by marked-equity path dependence on identical books — cascaded
into a different late-window portfolio whose exclusive trades happened to
win. The DEV result rests on five trades (94.37%); the other 182 are flat.
All of it remains EQUITIES-ONLY DEV EXPLORATORY / G4 UNADOPTED / NOT
VALIDATED EDGE.

— Muse
