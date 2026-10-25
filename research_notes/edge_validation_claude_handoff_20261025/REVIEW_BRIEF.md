# Claude independent review brief — Quality Flow v0.3 (2026-10-25)

**Task:** Source-based *adversarial* pre-test gate review, not a general rewrite. **Read the pinned actual documents and code**, challenge ChatGPT and Muse equally. **Do not run any strategy/backtest, touch holdout bars or vendor feeds, change production, initiate trading, or authorize S1/G4/T0.**

## Required sources, pinned

- Original Claude v0.2, 23-page PDF, commit `02568b2`, SHA-256 `01c4fff0c94cbf1d48f420b4e71619b7f477b07deaacd76705e9ca788abf00ae`: [original](https://github.com/mickaellall116-cmyk/quality-flow-scanner-v5/blob/02568b2/research_notes/edge_validation_prereg_20261025/Quality_Flow_Edge_Validation_PreRegistration_Draft_v0.2.pdf).
- Muse v0.3, commit `b65696a`: [full draft](https://github.com/mickaellall116-cmyk/quality-flow-scanner-v5/blob/b65696a/research_notes/equity43_dev_prereg_v03_20261025/PREREG_V03_DRAFT.md); [change register](https://github.com/mickaellall116-cmyk/quality-flow-scanner-v5/blob/b65696a/research_notes/equity43_dev_prereg_v03_20261025/CHANGELOG_V03.md); [outcome-blind feasibility](https://github.com/mickaellall116-cmyk/quality-flow-scanner-v5/blob/b65696a/research_notes/equity43_dev_prereg_v03_20261025/OUTCOME_BLIND_FEASIBILITY.md); [freeze checklist](https://github.com/mickaellall116-cmyk/quality-flow-scanner-v5/blob/b65696a/research_notes/equity43_dev_prereg_v03_20261025/FREEZE_BLOCKER_CHECKLIST.md).
- P7 [all-fire collector code](https://github.com/mickaellall116-cmyk/quality-flow-scanner-v5/blob/539e0a9/research_notes/equity43_dev_measurement_fixes_20261025_29/code/allfire_journal.py); P7 [summary](https://github.com/mickaellall116-cmyk/quality-flow-scanner-v5/blob/539e0a9/research_notes/equity43_dev_measurement_fixes_20261025_29/artifacts/allfire_summary.json).
- ChatGPT review [Issue #1 comment 6401471382](https://github.com/mickaellall116-cmyk/quality-flow-scanner-v5/issues/1#issuecomment-6401471382) — **challenged claims, not assumed facts**.
- Measurement independently reviewed in [Issue #1 comment 6400814802](https://github.com/mickaellall116-cmyk/quality-flow-scanner-v5/issues/1#issuecomment-6400814802); -28 corrections [f625921](https://github.com/mickaellall116-cmyk/quality-flow-scanner-v5/blob/f625921/research_notes/equity43_dev_prereg_v03_delta_20261025_28/MEMO.md).

## Four bounded questions

**Q1 — Matched controls (evidence and causal inputs).** Verify or refute claim that B-A **pool-size feasibility** cannot be run from the *cited committed metadata alone*: `allfire_journal.py` appears to output only BUY-fire rows, not the non-signal same-symbol bar Close/ATR%, full observed bar grid, or non-signal EMA21/EMA55/EMA200 for diagnostic B-T. Cite exact fields and any counter-evidence source/hash. Distinguish “possible from private price input” from “runnable from committed metadata”. Name minimum outcome-blind, **no-return** inventory/derivation to close any evidence gap. Is it a prerequisite for **DEV exploratory test**, document freeze, or only confirmatory use?

**Q2 — Prospective STOP/parity clauses.** Compare v0.2 §10 with v0.3 §10 word for word. Has v0.3 removed or weakened any original provisions for ET bar completion and vendor delay, initial 5-session/20-session and weekly replay parity, exact decision/entry/stop/TP1 checks, as-received BAR hashes, order/ACK/fill timestamps, or no discretionary overrides? Review new F5 claim that outages generate “missed signals” — with no bar, could BUY status be unknown? Specify minimal literal replacement clauses and synthetic fail-closed tests for gaps, duplicated/revised bars, hash/schema drift, and premature outcome visibility. **Five-symbol Oct 26–30 feed measurement pilot is not 43-symbol strategy validation**; do not conflate.

**Q3 — EXIT downside/tail diagnostics.** Source-diff v0.2 §7/§12 versus v0.3 §7/§12. Have explicit non-gating loss >1R/tail, overshoot/MAE-MFE, worst 5% expected shortfall, worst-five trades, TP1 execution, wick-stop/whipsaw-recovery count, holding periods, winner collateral, and TAIL-WORSE warning or predeclared fragility thresholds been removed? Restore only actually dropped diagnostics (with exact definitions and fields). Specify whether any omission blocks the initial **BUY DEV exploratory** test, an **EXIT DEV exploratory** test, or merely a later confirmatory EXIT study; don't incorrectly make all diagnostics global launch blockers.

**Q4 — Fastest legitimate testing path.** Provide a *single* precise, reproducible, bounded **DEV exploratory BUY-signal** study design and its minimum inputs/guards (2,892 all fires vs 590 serialized candidates; de-clustering; 10-bar primary/5-20 secondary; B-A controls; ATR-normalization; symbol/time clustering; return availability). Spell out what work is possible offline **without a new performance run**, and which exact next action requires Mike's separate GO. Are the v0.3 requirements for **document freeze**, **first exploratory DEV study**, **forward collection**, and **confirmatory holdout** appropriately separated? If not, classify them rather than relitigating earlier repair work.

## Standing evidence/governance

- DEV Sep 2024–Oct 2026 on 43 symbols **exploratory only**. Frozen 4bps 191 taken/187 closed/+32.4873R, top five winners account for 94.37% of net R. Original C1 = FAIL.
- P7 DEV fire census: **2,892 = 590 matched + 2,301 suppressed + 1 gap-ineligible**. These are NOT 2,892 independent tests.
- Correct 25bps own-taken-set view: 189 taken/185 closed/+19.8892R; old “185-vs-187” is a resolved wrong-selection error, not an open blocker absent novel evidence.
- Bounded measurement engineering P1/P2/P3/P4/P6/P7/P8/P9 accepted. G4 UNADOPTED, S1 LAUNCH_HOLD, production PAUSED, holdout SEALED. No validated edge.
- Use existing committed source and metadata only, no holdout bar reads, no vendor requests/spending, new backtests, tuning, trading, S1/S2 activation, future T0 or changes to the separately-approved feed pilot. An *independent written review* does not authorize execution.

## Output contract: 1–2 pages + exact source references

1. **Verdict:** GO to finalize *bounded exploratory design* / CONDITIONAL GO / HOLD. Clarify that this is never execution GO.
2. Q1/Q2/Q3 evidence matrix: CONFIRMED / PARTIAL / REFUTED / UNVERIFIED, with file+section/line and direct ref.
3. **No more than three** true pre-DEV-exploratory blockers, each with a single acceptance test and a concrete closure artifact. If none, state NONE.
4. Later-only requirements for Tier 4, confirmatory tests, data-rights/S1 etc., explicitly separated.
5. One test-ready exploratory BUY design, what can be done right now without run authorization, and the exact authorization needed for performance.
6. **STOP**; no broad new redline list, no parameter optimization, no reruns. If pinned bytes unavailable, label specifically UNVERIFIED, don't speculate.

The purpose is to end the repeat-review loop while retaining sound research controls.