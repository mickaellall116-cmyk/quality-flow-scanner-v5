# EXP-14B — RUN RECORD: the single authorized DEV exploratory run (2026-10-25 ET)

**Study:** EXP-14-BUY-DEV-EXPLORATORY, as amended under Decision B (matched subpopulation).
**This was the ONE run.** It executed exactly once, under the authority below, and the gate is re-closed (see §6).

## 1. Authority

- **Decision B (Mike, chat 2026-10-25 21:19 ET):** prospective DEV-only matched-subpopulation amendment adopted; original EXP-14 protocol STOP preserved (step-(c) drop 22.83% > 15%); this run is approval-of-design executed under the conditional GO below — the study establishes **no validated trading edge** and authorizes **no live-strategy change**.
- **Conditional GO:** Issue #1 comment `6406229148` (Mike: "I authorize everything") — ONE DEV-only exploratory run, effective only after a committed, independently verified execution-readiness package; any failed check STOPs without outcomes; no repeat runs.
- **Readiness PASS:** Issue #1 comment `6407503923` (2026-10-26T03:23:17Z) — ChatGPT independently reconstructed all 13 corr2 files (`7a0e487`) from GitHub with exact bytes; `verify_package.py` PASS; synthetic suite 110 checks, 0 failures; four input hashes confirmed compiled into `PINNED_INPUT_SHA256`. (Also on the desk, Slack TS `1792984996.581039`.)
- **Single-dispatch check before any action: CLEAR.** No execution stage dir, worktree, or run-output artifact for EXP-14B existed anywhere; origin/main tip was the corr2 RESULT post `baf8ec1`; `RETURNS_ENABLED = True` existed only as fixture strings inside synthetic test files. Exactly one output file exists from this run (§5); no second run occurred.
- **Desk notice BEFORE execution, both channels:** bridge commit `ee9fd9d` (ancestor-verified on origin/main before the run); Slack TS `1792985506.711579`.

## 2. Execution version

- Base: corr2 pinned script `code/exp14_buy.py`, SHA-256 `77bd53e82963d65ab743a57f1eff0d23b54467a0e17aaf1831b42e6e96b6f3d8` (package `7a0e487`).
- Execution version: `exp14_buy_execution_version.py` in this package, SHA-256 `a5e583c969ecec2e1a815551f3d54f371970593c4bc8d79ce22cbd95d8c5ef1c`.
- **Sole change (verified by diff): line 143 — `RETURNS_ENABLED = False` → `True`, with an annotation comment naming the authority. Nothing else differs.**

## 3. Inputs (hash-verified twice: externally before the run — `input_hash_verification.log` — and by the execution path itself against the compiled-in `PINNED_INPUT_SHA256` before anything loaded)

| Input | SHA-256 | Match |
|---|---|---|
| P7b inventory (private, qf-data-archive `research_inventory/p7b_20261025/p7b_inventory.jsonl`) | `a6bbd19a702120cafd48cd01ee4c8ff59b838a8bd6439822415d6c18278ef02f` | exact |
| Execution-only price input (private, qf-data-archive `research_inventory/exp14_exec_prices_20261025/exp14_exec_prices.jsonl`) | `4adb8320bd10e8e1e8c650d847290c5a66344b9a21704fba40fc53992af205b8` | exact |
| Frozen cohort (corr2 package artifact) | `35690b806e51eefe388fadf35b04baf5ed4c52f8e30ac193a38cf88246332824` | exact |
| Frozen draws (corr2 package artifact) | `fe54808e282515807703692fb08cf3928ee9a4435d04b6939f2b9f47157e4a8a` | exact |

Raw inventory / price rows stay private (qf-data-archive only); this package carries hashes and aggregates only.

## 4. The run

- **Exact command:** see `run_command.sh` (byte-exact record of the invocation: `--mode returns` with the four pinned inputs, their pinned `--*-sha` declarations, and `--out-analysis`).
- **Window:** 2026-10-26T03:32:20Z → 2026-10-26T03:32:24Z (23:32 ET, Oct 25).
- **Exit state (as recorded at invocation, `run_exit.txt`): exit code 0.** stderr empty (`stderr.txt`). stdout (`stdout.txt`): `{"analysis_written": ".../exp14b_analysis.json", "label": "DEV EXPLORATORY", "claim": "NONE"}`.
- All guards passed: byte-hash binding, loaders, ts-equality and finite-open validation, disclosure recomputation, complete-window checks. No STOP occurred; nothing was retried or patched.

## 5. Output

- File: `exp14b_analysis.json` (in this package), SHA-256 `d9f4864e88db97d24a94734c4d847105b9fe0a6f7513e1ab9ba003e147b76467`.
- **Verified against the pinned corr2 output schema (`48a9534d…`) field by field:** study / label / claim / verdict consts exact; disclosure header present and exact (below); percentage views at h=5/10/20; 25 bps cost line present; **no PASS/FAIL token anywhere in the file** (whole-file scan); verdict = the neutral const; intervals labeled per the corrected semantics; **no UNDERPOWERED label is emitted by this schema/run**.
- **Disclosure header (verbatim from the output):** eligible 311 · retained (matched) 240 · excluded (unmatched) 71 · exclusion rate 0.2282958199356913 (22.829581993569132%). Scope statement: "MATCHED SUBPOPULATION ONLY — these results describe only the events meeting the frozen step-(c) matching criteria (the retained events). They do NOT describe all Quality Flow BUY signals, and they establish no validated trading edge." matched_subpopulation_only = true.

### Headline numbers (verbatim from the output file)

- **Primary — h=10 paired excess vs B-A (n=240):** mean **+0.18158046332385522 ATR** · mean_pct **+0.008388794352771678** (+0.8389%). Interval used: **cluster** (the wider of the two). Interval bounds are **separate one-sided 95% bounds** (5th/95th resample-mean percentiles), jointly a **central 90%** interval — NOT a two-sided 95% interval: **[−0.14233499203156924, +0.5183824331686139] ATR** — the interval crosses zero. Block bootstrap bounds: [−0.12421164689529339, +0.49412452864793804]. design_effect 0.8802850324842751 · n_eff 272.638964816532 · reps 10,000 · block 20 sessions · seeds master 7715012043445510037, bootstrap 6050949521315240661.
- **h=10 event return (unpaired):** −0.04266983433838185 ATR · +0.0031314846328136343 pct.
- **h=5:** paired excess **+0.17354365638005215 ATR** · **+0.006230021474747595 pct**; event return −0.028082645421531584 ATR · +0.0012421517288280803 pct.
- **h=20:** paired excess **−0.24320975586565927 ATR** · **−0.0012466046454382965 pct**; event return +0.2990990091680148 ATR · +0.014382985996880966 pct.
- **Cost sensitivity (descriptive only, never a verdict input):** round trip 25 bps; primary paired excess pct 0.008388794352771678; minus round trip **0.0058887943527716775**.
- **B-T diagnostic (gating = false):** n = **43 of 240** retained events had a B-T draw (sparsity disclosed; non-gating); mean paired excess +0.6497392636994823 ATR · +0.011311057725417762 pct.
- **Verdict field (const):** "DESCRIPTIVE ONLY — no promotional or validated-edge conclusion". Claim: NONE. Label: DEV EXPLORATORY.

## 6. Re-close

The standing corr2 pin on origin/main is byte-untouched: `RETURNS_ENABLED = False` (verified in the fresh origin/main tree after the run). The flipped execution version exists **only** as this archived run record. The conditional GO `6406229148` is spent — it authorized exactly this one run; any further run requires new authorization.

Bounds kept throughout: original EXP-14 STOP preserved; C1 FAIL preserved; DEV exploratory only; holdout SEALED (never contacted); production PAUSED; no vendor call; no trading; no S1/S2/G4/T0 action. — Muse
