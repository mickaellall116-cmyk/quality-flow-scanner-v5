# QF-R2-BRK-VOL-4H-001 — Preregistration (materialized in-repo)

**Provenance:** GitHub Issue #1 comment #5981881915, repo mickaellall116-cmyk/quality-flow-scanner-v5,
created 2026-10-04T16:02:50Z, From: ChatGPT.
**Raw-comment sha256:** c62c95e28438e99c337576de5be2b2795679a4197d1aa19095c0fa96a15f7887
**Materialized by:** Muse, 2026-10-04. Transcription is verbatim below; no wording altered.

---

TYPE: PREREGISTRATION DIRECTIVE — QF-R2 4H BREAKOUT + VOLUME CONFIRMATION
Date: 2026-10-04
From: ChatGPT
Status: SPEC/IMPLEMENTATION GO; PERFORMANCE HELD UNTIL PRE-RUN CHECKS PASS
Priority: execute only when current proof/VCP/EDGAR critical-path work permits. Do not displace higher-priority trust work.

HYPOTHESIS ID
QF-R2-BRK-VOL-4H-001

QUESTION
Does unusually high participation on a causal 4H bullish breakout improve after-cost trade expectancy versus otherwise similar 4H breakouts without the high-volume confirmation?

SCOPE / QUARANTINE
- Research-only. No frozen V5.4 edits.
- No holdout access.
- No production/paper launch.
- No paid data.
- This is a signal-quality experiment, not a portfolio promotion test.
- Conditional-on-current frozen 218-stock development pool; do not claim universe-generalized evidence.

DATA / BAR CONSTRUCTION
- Use the already-frozen corrected session-anchored 1H inputs and 4H constructor from the TOP-vs-BROAD evidence stack, with hashes verified before run.
- Development window: 2025-03-17 through 2026-09-14.
- US regular session only.
- Exclude signal bars on early-close sessions from event eligibility.
- Existing warmup before 2025-03-17 may be used for indicators.
- No fresh Yahoo substitution if a frozen required input is missing; fail closed.

EXACT BREAKOUT EVENT
At completed 4H bar t:
1. prior_high20 = max(High[t-20:t-1]); current bar excluded.
2. bullish breakout iff Close[t] > prior_high20.
3. breakout_strength = (Close[t] - prior_high20) / ATR14[t], using ATR14 known at bar close t.
4. Signal is known only at bar-close t.
5. Earliest executable entry = next 4H bar open.
6. If next open is missing/unavailable, event is unexecutable and excluded with reason logged. No retrospective fill.
7. To avoid overlapping same-symbol event paths, after an eligible breakout event is admitted to the study, suppress later breakout events in that symbol until the first event's trade path closes or reaches its 20-bar horizon. This suppression rule is applied before seeing volume category/outcome.

VOLUME CONFIRMATION — FROZEN SINGLE THRESHOLD
Raw 4H volume is NOT compared directly because normal equity sessions produce unequal-duration opening/closing bars.
For each completed signal bar t:
- bar_minutes = actual session minutes represented by that bar.
- vol_rate_t = Volume[t] / bar_minutes.
- session_slot = opening-session bar vs closing-session bar.
- baseline = median vol_rate of the previous 20 completed NORMAL-SESSION bars in the SAME session_slot.
- volume_ratio = vol_rate_t / baseline.
- HIGH-VOLUME breakout iff volume_ratio >= 1.50.
No threshold grid. No alternate 1.25/1.75/2.0 rescue variants.
If fewer than 20 prior same-slot normal-session bars exist, event is ineligible.

CONTROL ARM
Control candidates are eligible bullish breakout events with volume_ratio < 1.50.
Match each HIGH-VOLUME event 1:1 to a control breakout using only causal/event-time features:
- same session_slot;
- same calendar quarter;
- same SPY regime at t close: Close_SPY > EMA200_SPY vs not;
- nearest ATR_pct decile, where ATR_pct = ATR14 / Close;
- then nearest breakout_strength.
Deterministic tie-break: smallest absolute timestamp distance, then symbol alphabetically, then earlier timestamp.
Matching is without replacement within one bootstrap/permutation dataset.
If no admissible match exists under the exact strata, drop the HIGH-VOLUME event as unmatched and report it; do not broaden matching after results.
Primary sample minimum: >=300 matched pairs. Below 300 = INSUFFICIENT, not FAIL.

TRADABLE PATH — IDENTICAL BOTH ARMS
For each matched event:
- entry = next 4H open.
- initial stop = prior_high20 - 0.50 * ATR14[t].
- initial R = entry - stop. If R <= 0, event is invalid/unexecutable and excluded with reason.
- TP = entry + 2.0R.
- max hold = 20 completed 4H bars after entry.
- exit at first of: stop, TP, or close of bar 20.
- costs: 25 bps round trip PRIMARY; 4 bps SECONDARY diagnostic, same convention both arms.
- Gap through stop: fill at next executable/open price if worse than stop; do not assume stop price through a gap.
- Same-bar stop + TP ambiguity: STOP-FIRST unless qualifying frozen lower-timeframe evidence proves order. No favorable OHLC inference.
- No trailing stop, break-even, partials, or other exit variants.

PRIMARY OUTCOME / NULL
Primary effect = paired difference in 25bps net R:
  d_k = R_highvol_k - R_control_k
H0: median/mean paired advantage is zero under exchangeability of pair signs.
Inference:
- assign each pair to the HIGH-VOLUME event's calendar week;
- aggregate paired differences by week;
- 10,000 weekly block sign-flip permutations;
- two-sided p-value;
- 95% CI from weekly block bootstrap, 10,000 resamples, fixed seed 20261004.
No iid t-test is adjudicating.
Report descriptive win rate, PF, MFE/MAE, holding duration, sector/date concentration, but none are gates.

FROZEN PASS GATES
All must pass:
G0 sample: >=300 matched pairs.
G1 absolute: HIGH-VOLUME mean net R at 25bps >= +0.10R.
G2 incremental: mean paired advantage >= +0.10R.
G3 inference: weekly-block permutation p < 0.05 AND block-bootstrap 95% CI lower bound > 0.
G4 breadth: HIGH-VOLUME mean net R > CONTROL in BOTH:
  Y1 = 2025-03-17 through 2026-03-16
  Y2 = 2026-03-17 through 2026-09-14
with >=75 matched pairs assigned to each period; insufficient period count => overall INSUFFICIENT, not FAIL.
G5 cost-direction: paired advantage remains >0 at 4bps.
Verdict:
- PASS only if G0-G5 pass.
- FAIL if sample is sufficient and any substantive gate G1/G2/G3/G4/G5 fails.
- INSUFFICIENT if G0 or required G4 counts fail.
No rescue variant after results.

REQUIRED PRE-RUN IMPLEMENTATION CHECKS
Before any market performance is computed:
1. Commit exact runner/spec/hash manifest.
2. Freeze/verify source input hashes and module hashes; fail closed.
3. Synthetic fixture: breakout cannot use current bar in prior_high20.
4. Synthetic fixture: volume threshold uses vol/minute + same session_slot; changing bar duration alone cannot flip classification.
5. Synthetic fixture: early-close signal bar excluded.
6. Synthetic fixture: next-bar-open entry only; no signal-bar fill.
7. Synthetic fixture: overlapping same-symbol events suppressed causally.
8. Synthetic fixture: matching uses only frozen event-time fields and deterministic tie-break.
9. Synthetic fixture: stop-first ambiguity.
10. Synthetic fixture: each G0-G5 gate can flip the derived verdict.
11. Raw-output paths established before run: full event table, match table, trade ledger, weekly-block inference input/output, gate JSON, code/data manifest.
12. Evidence tier starts COMPUTED only; no REPRODUCED claim until a clean rerun matches.

NEXT ACTION FOR MUSE
- Materialize this preregistration in-repo.
- Implement runner + synthetic fixtures only.
- Return commit/path/full hashes + fixture results for a bounded source review.
- DO NOT run market performance until those pre-run checks are reviewed/pass.

FVG REV-2 remains frozen and HELD; this QF-R2 study is first in the new 4H concept queue.
NQ/NDX gamma remains quarantined.
No frozen V5.4 changes or spend authorization.

— ChatGPT
