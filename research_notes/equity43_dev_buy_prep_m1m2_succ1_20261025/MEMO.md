# EXP-14 successor package — horizon rule, analysis contract, revised step-(c) counts

**Date:** 2026-10-25 (ET). **Author:** Muse. **Status:** PREPARATORY, NO-RETURN work only. Nothing in this package computes a forward return on real data, a return-based variance or power figure, an EXIT arm, or a backtest. The finished analysis path is exercised **only on synthetic fixtures**. No holdout contact, no vendor call, no production / pilot / S1 change, no trading.

**Predecessor:** the M1/M2 preparatory package `research_notes/equity43_dev_buy_prep_m1m2_20261025/` at commit `5e02503` — byte-untouched by this successor. M1 (P7b inventory) stands as **evidence recorded**; nothing here reopens it.

**Governing text.** Issue #1 comment `6405786931` (ChatGPT independent review of `5e02503`): **P-1 ACCEPTED for exploratory-only DEV; EXP-14 on EXECUTION HOLD** with three tightly scoped acceptance items. This package addresses exactly those items, in the manner the review prescribes, and nothing else. The v0.3 freeze stays HOLD on all other items; this package touches no other v0.3 element.

**Single-dispatch check (run before any file operation): CLEAR.** No successor stage directory, worktree, branch, or pre-execution commit for this review existed on origin/main or locally; origin/main after `5e02503` carried only its RESULT bridge post and the hourly KAMA log updates.

---

## Item 1 — 20-bar horizon / endpoint integrity: RESOLVED as prescribed

**The defect (review's reproduction, independently confirmed on the pinned bytes):** v1 froze the cohort and pool eligibility on the primary horizon's window (h=10). Five retained h=10 events lack a full h=20 outcome — AMAT:1024, AMZN:1031, GOOGL:1027, SHOP:1029, SMH:1025 — and eight B-A draw groups contained h=20-ineligible control indices (COIN:965, HOOD:965, IWM:939, NFLX:967, NU:955, PYPL:941, SOFI:963, TSLA:985; the h=20 ceiling for the 1,043-bar series is idx 1022).

**The fix (one pinned rule):** in `code/exp14_buy.py` v2, eligibility for **events and controls alike** is the single complete-window rule — `idx + 20 <= n - 1` — identical for h=5/10/20. Horizons differ only in the exit bar used at execution time. No control is silently omitted: pools are computed under the rule before any draw exists, and the per-horizon drop counts remain published (h=5 → 2, h=10 → 3, h=20 → 9 of the 320 de-clustered events).

**Re-derived, outcome-blind, from the hash-pinned P7b inventory (SHA-256 `a6bbd19a…`):**
- Cohort: **311** events (320 de-clustered − 9 boundary exclusions — the review's figure exactly). All five named events are absent; the maximum drawn control index anywhere is 1021 ≤ 1022; all eight previously violating draw groups are clean.
- Ladder on the corrected cohort (B-A): step 0 → 170 dropped (54.66%); (a) → 139 (44.69%); (b) → 94 (30.23%); (c) → 71 (**22.83%**). The ladder still exhausts at step (c); frozen step (c) (band ±40%, window ±45 sessions, minimum pool 6), flag ON.
- Retained: **240** events. Mix by bin: 09:30 — 202, 13:30 — 38; all 43 symbols present.
- **Determinism re-proven:** the pool-counts regeneration was run twice in clean conditions; all three artifacts are byte-identical across runs (hashes in `SHA256_MANIFEST.txt`).

**P-1 acceptance records (carried with the corrected counts, per the review):**
- Pool restriction to the frozen generator evaluation domain stands as an **intentional §5 interpretation**, accepted for exploratory-only DEV, with **no later switching based on returns**.
- Draws are **all available controls** whenever the eligible pool holds 6–19 bars: of the 240 B-A groups, **134 drew the full 20 and 106 drew all-available below 20**. No claim is made that all groups used 20 controls.
- B-T remains a **non-gating sparse diagnostic**: 43 of 240 retained events have a viable B-T pool; 197 fall below the minimum. It is not rescued, selected, or treated as a confirmation claim, and its sparsity is not separately a STOP for B-A.

## Item 2 — pinned executable analysis contract: RESOLVED as prescribed

`code/exp14_buy.py` v2 now contains the complete, hash-pinned analysis path Claude's M2 required, finished **on synthetic fixtures only**:
- **Endpoint:** forward return `(close[i+h] − open[i+1]) / atr[i]` (percent alongside), per §5; paired excess vs the drawn B-A control mean at h=5/10/20, primary h=10; B-T diagnostic excess where a B-T draw exists.
- **Inference:** circular block bootstrap over calendar time (20-session blocks, 10,000 reps) and a symbol-cluster bootstrap; the reported interval is the **wider of the two** (frozen rule); n, blocks, design effect and n_eff are reported. The output shape is pinned in `artifacts/exp14_output_schema.json`. Every real-data output header must say **DEV EXPLORATORY** with claim **NONE** — the script issues no PASS/FAIL and no edge claim.
- **Gate retained:** the public entry `compute_forward_returns()` raises `ExecutionGoRequired`; `RETURNS_ENABLED` is `False` in this pin and the verifier asserts both. Enabling returns remains a new version + new pin + the separate execution GO.
- **Fail-closed (all fixture-proven):** cohort or draws artifact hash mismatch; invalid inventory keys / non-contiguous indices; a cohort event that is absent, not a generator-domain fire, or window-incomplete; a control that is absent or window-incomplete; any event/control timestamp outside the DEV window (2024-09-16 → 2026-10-16); any missing forward datum.
- **Seed reconciliation (chosen and recorded before any outcome, as the review directs):** the study keeps ONE seed family. `MASTER_SEED` (draws) = first 8 bytes (big-endian) of SHA-256("EXP-14-BUY-DEV-EXPLORATORY") = **7715012043445510037** (unchanged from v1 — the frozen draws the review independently reproduced were derived under it). `BOOTSTRAP_SEED` = first 8 bytes (big-endian) of SHA-256("7715012043445510037:bootstrap") = **6050949521315240661**, pinned as a literal in code, artifacts, and the verifier; the cluster stream derives from it by the same sub-seed convention. **Not adopted:** the preregistration-hash seed (v0.3 §6 [C10] / frozen contract `fc17041`) — v0.3 is an **unfrozen draft** (freeze HOLD), so its hash is not fixed today and would move with any amendment; and the script-hash seed (Claude final-gate p.9) — the script hash changes with the very version bump that enables returns, so pin and execution would carry different seeds. This is a recorded deviation from §6 [C10]'s seed wording for EXP-14 specifically, made deliberately and before outcomes, for the freeze record to see.

**One contract gap found while finishing the path — surfaced, not worked around:** the pinned P7b inventory carries **no `open` field** (schema: close/atr/atr_pct/ema21/ema55/ema200/signal only), while §5's endpoint is entry = **open of bar i+1**. The analysis path therefore **fails closed on the inventory as pinned** (fixture-proven). No price was substituted and no endpoint was altered. Any execution first needs an inventory amendment adding `open` from the **same committed DEV bytes** (a preparatory successor, no new data) — carried as an explicit precondition in the GO request below.

## Item 3 — the >15% step-(c) rule: counts revised; the decision is the user's

Recomputed **only after** the outcome-blind horizon correction, as the review prescribes: step (c) drops **71 of 311 = 22.83%** (v1: 72 of 317 = 22.71%). **The rate remains above 15%, so under Claude's written EXP-14 protocol this is a STOP — no result is to be produced or published from an as-is run.** The retained count (240) still exceeds the §6 validity floor of 200; per the review, that is **not** a basis to authorize the as-is run, and this package does not ask for one. Item 3 is a governance decision on these final counts, presented in the GO request below as the single explicit choice the review specifies.

## Synthetic tests

`tests/test_exp14_synthetic.py` — **61 checks, 0 failures**: everything the v1 suite covered (35, adapted to the single window rule) plus endpoint fixtures for events and controls at the h=20 boundary, forward-return arithmetic against hand-computed values, the full analysis path on fixtures (paired excess 4.75 ATR hand-verified; B-T diagnostic; determinism under the pinned seeds), all seven fail-closed negatives, the retained gate, and the seed literals. `verify_package.py` re-checks the manifest, the ladder/cohort/draw coherence, the review's named-event exclusions, the seed pins, the gate, and the suite — **PASS**.

## The updated exact GO request

> **DECISION + GO REQUEST — EXP-14-BUY-DEV-EXPLORATORY (DEV only).**
> The successor package above resolves review items 1–2 and reports the revised item-3 counts (step-(c) drop **22.83%**, still >15%). Requesting the user's (Mike's) explicit decision, after ChatGPT adjudication of this package:
>
> **Step 1 — the item-3 decision (one of):**
> - **(A) Preserve the STOP.** EXP-14 does not run on DEV; the study closes as STOP under the preregistered step-(c) rule, with this record as its final artifact. — OR —
> - **(B) Prospectively amend the DEV-EXPLORATORY-only contract** to permit a labelled **matched-subpopulation descriptive study**: the original step-(c) rule and its >15% flag stay in force and are printed on the output; the 71 excluded events (22.83%) are disclosed; **no relaxation** of any rule; **no broad population or general edge inference** — results describe only the 240-event matched subpopulation.
>
> **Step 2 — only if (B) is adopted, the execution GO proper:**
> 1. First, a preparatory inventory amendment adding the `open` field from the same committed DEV bytes (no new data), pinned as its own successor artifact; the §5 endpoint is not substituted.
> 2. Enable the returns mode as a **new pinned version** (sole change: the gate flip; re-hashed; synthetic suite re-run) and run it **once** on the successor cohort (311 events, 240 retained) and frozen draws in this package, against the amended inventory. No re-draws, no re-clustering, no parameter changes.
> 3. Report per §5/§6 and the pinned output schema: horizons 5/10/20, primary h=10 paired excess, wider-of-two intervals (20-session circular block + symbol-cluster, 10,000 reps, BOOTSTRAP_SEED 6050949521315240661), n / blocks / design effect / n_eff, the step-(c) flag and exclusion count on the output, and the UNDERPOWERED FOR PASS label where §6 applies. Headers: DEV EXPLORATORY, matched-subpopulation (under (B)), no PASS/FAIL claim.
> 4. Data scope: **DEV window only** (2024-09-16 → 2026-10-16, 43 symbols). Holdout untouched and sealed; no vendor calls; no EXIT arms; no full-system replay; no production/pilot/S1 contact.
>
> Until that decision and GO are given, the returns mode stays disabled and this package is the complete deliverable. **Nothing in this request executes on delivery.**

## Bounds kept

C1 FAIL preserved; DEV exploratory only; G4 UNADOPTED; S1 LAUNCH_HOLD; production PAUSED; holdout SEALED. The v0.3 freeze remains HOLD on every item outside this review's three. No performance figure of any kind appears in this package.
