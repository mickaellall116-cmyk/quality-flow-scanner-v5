# CORRECTION corr1 — EXP-14 Decision B package: two pre-execution source corrections

**Date:** 2026-10-25 (ET). **Author:** Muse. **Status:** CORRECTED PIN, synthetic-only. Nothing in this package computes a forward return on real data; the analysis path is exercised **only on synthetic fixtures**. Returns mode remains **DISABLED** (`RETURNS_ENABLED = False`; the entry point raises `ExecutionGoRequired`). No holdout contact, no vendor call, no production / pilot / S1 change, no trading.

**Predecessor:** the Decision B amendment package `research_notes/equity43_dev_buy_decisionb_amendment_20261025/` (commit `f69c470`), carried here in full and corrected in exactly two places. `AMENDMENT.md` (the Decision B record) is carried **byte-identical**.

**Governing texts:** Issue #1 comment `6406403886` (independent review of `f69c470`: strong partial PASS; feasibility/cohort/draws verified byte-identical to frozen `32dfdb3` — 311 eligible, 240 matched, 71 unmatched (22.83%); TWO narrow pre-execution corrections only) and Issue #1 comment `6406229148` (the user's recorded **conditional GO** for ONE DEV-only EXP-14B exploratory run, effective only after a committed, independently verified execution-readiness package). Single-dispatch check before any file operation: **CLEAR** (no correction stage, worktree, or pre-execution commit for review `6406403886` existed; origin/main tip was the Decision B RESULT post `58ba657`).

---

## Correction 1 — verdict token (review item 1)

**Defect:** `_analysis_impl` emitted the literal prohibited token pair inside the `verdict` value (`"…issues no PASS/FAIL…"`), violating the explicit no-PASS/FAIL-token output rule — the field denied the tokens using the tokens.

**Fix:** the verdict value is now the neutral const prescribed by the review:

> `DESCRIPTIVE ONLY — no promotional or validated-edge conclusion`

The same wording was removed from the module docstring, and the pinned output schema's `verdict` entry now names the same const.

**Evidence (synthetic):** a new check serializes the full emitted analysis object (fixture run, in-process) and asserts the prohibited tokens appear in **no field**; a second check pins the verdict value to the const exactly; a third repeats both assertions on the output file written by the CLI end-to-end fixture run. All pass.

## Correction 2 — execution-price timestamp + non-finite opens (review item 2)

**Defect:** `load_exec_prices` parsed each row's `ts` and discarded it; `validate_exec_prices` checked symbol/index/value only. A price row bearing a wrong timestamp therefore passed whenever its separately supplied file hash matched — the timestamp was attested nowhere in the analysis path.

**Fix:**
- The loader now **retains** the timestamp: the price map is `{symbol: {idx: {"ts": ts, "open": open}}}`.
- `validate_exec_prices` — called by `_analysis_impl` **before any return is computed** — asserts **exact timestamp equality** against the pinned inventory `ts` for every (symbol, idx), on top of the unchanged exact symbol/index coverage.
- Opens must now be **finite** positive numbers: NaN and ±inf are refused (previously NaN slipped through, since `NaN <= 0` is false), at validation and at the `forward_return` endpoint alike.

**Evidence (synthetic, all fail-closed as required):** wrong-timestamp price map refused by the validator **and** at analysis level; NaN open refused by the validator, at analysis level, and at the endpoint; infinite open refused by the validator and at the endpoint; the exactly-equal retained-ts map validates. The package verifier additionally re-proves the timestamp-mismatch / NaN / inf refusals on its own inline fixtures.

## What did NOT change

- **Frozen artifacts byte-identical** to `f69c470` (and to successor `32dfdb3`): feasibility `80c9f5fe…`, cohort `35690b80…`, draws `fe54808e…`. Cohort/draws/seed: **no drift**.
- Exec-prices descriptor byte-identical (`351cff4f…`); price-input builder byte-identical (`2a0d9f0c…`); the price-source separation is unchanged — the inventory is not amended, no prices appear in this public package.
- Seeds unchanged: master **7715012043445510037**, bootstrap **6050949521315240661**. The original EXP-14 protocol's **STOP stands**. Decision B's four conditions stand (311 / 240 / 71 / 22.83% disclosed; matched subpopulation only; no validated-edge claim; no live-strategy change).
- `RETURNS_ENABLED` is still **False** in this pin.

## Tests

`tests/test_exp14_synthetic.py` — **101 checks, 0 failures** (the f69c470 suite's 91, with fixture price records adapted to the retained-ts shape, the verdict check re-pinned to the new const, and 10 new corr1 checks: token absence in emitted output ×2, verdict const, timestamp mismatch at validator + analysis level, NaN at validator + analysis + endpoint, inf at validator + endpoint, exact-ts positive control). `verify_package.py` — **PASS** (manifest; byte-identical frozen carry and coherence; Decision B record; descriptor; schema incl. the corr1 verdict const; the corr1 functional proofs; gate holds; disclosure recomputes; suite PASS).

## Pins

| Artifact | SHA-256 |
|---|---|
| Corrected script `code/exp14_buy.py` (v3, corr1) | `651b19610e3d783b42ee864b2e07b7640fc58d7ac01b0a4863baa1016488aa35` |
| Synthetic suite `tests/test_exp14_synthetic.py` (corr1) | `fed0bc843fd9509bb07448e6765073d63a6fe8e4d727e32adffe81ee07162944` |
| Output schema `artifacts/exp14_output_schema.json` (corr1) | `95f9b4e86563280c2b759f8968f6c5bbe83bb5a448bb24ec41a60af061bd81eb` |
| Price-input builder (unchanged from `f69c470`) | `2a0d9f0c7469a99e27250870c61421f8abbb173c3f5f10a37fe2d2017f6f343b` |
| Frozen cohort / draws / feasibility (unchanged) | `35690b80…` / `fe54808e…` / `80c9f5fe…` |

## Readiness boundary — what happens next

This package is submitted for ChatGPT's independent **readiness PASS**. Execution of the single EXP-14B run follows that PASS under Mike's recorded conditional GO (comment `6406229148`) — **no new GO is requested, and none is needed for this exact single run**. Muse **will NOT execute before** the readiness PASS lands, and will notify on the desk before running. If any required check fails at execution time, the run STOPs without real outcomes and the precise defect is surfaced.

Bounds kept: original EXP-14 STOP preserved; C1 FAIL preserved; DEV exploratory only; holdout SEALED; production PAUSED; S1 LAUNCH_HOLD. No performance figure of any kind appears in this package.
