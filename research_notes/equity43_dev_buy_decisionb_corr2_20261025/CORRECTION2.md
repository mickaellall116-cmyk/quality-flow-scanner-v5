# CORRECTION corr2 — EXP-14 Decision B package: execution-readiness binding + interval semantics

**Date:** 2026-10-25 (ET). **Author:** Muse. **Status:** CORRECTED PIN, synthetic-only. Nothing in this package computes a forward return on real data; the analysis path is exercised **only on synthetic fixtures**. Returns mode remains **DISABLED** (`RETURNS_ENABLED = False`; the entry point raises `ExecutionGoRequired`). No holdout contact, no vendor call, no production / pilot / S1 change, no trading.

**Predecessor:** the corr1 package `research_notes/equity43_dev_buy_decisionb_corr1_20261025/` (commit `6fc983b`), carried here in full and corrected in exactly the two places below. `AMENDMENT.md` (the Decision B record) and `CORRECTION.md` (the corr1 record) are carried **byte-identical**.

**Governing texts:** ChatGPT's desk reply of 2026-10-25 22:48 ET (Slack TS `1792982883.654249`) — corr1 independently **PASSED** as a package (synthetic suite 101/0; no verdict tokens; ts / NaN / inf fail-closed; cohort/draws unchanged), with execution remaining **HOLD** pending this one separate readiness finding with exactly two items — and Issue #1 comment `6406229148` (the user's recorded **conditional GO** for ONE DEV-only EXP-14B exploratory run, effective only after a committed, independently verified execution-readiness package). Single-dispatch check before any file operation: **CLEAR** (no corr2 stage, worktree, or pre-execution commit for this reply existed; origin/main tip was the corr1 RESULT post `86de84b`; the empty `qf_exp14b_corr_stage` directory is the corr1 lane's spent staging area, last touched before the finding was posted).

---

## Item 1 — the four approved byte hashes are hard-bound in the execution path

**Finding:** whatever the loaders checked, the binding expectation ultimately came from the caller (CLI `--*-sha` arguments; `_analysis_impl`'s expected-hash parameters fed from the just-loaded objects). An altered file accompanied by its own matching hash would pass.

**Fix:** the four approved input byte hashes are compiled into the script itself as `PINNED_INPUT_SHA256`:

| Input | SHA-256 (full) |
|---|---|
| P7b inventory (private, qf-data-archive) | `a6bbd19a702120cafd48cd01ee4c8ff59b838a8bd6439822415d6c18278ef02f` |
| Execution-only price input (private, qf-data-archive) | `4adb8320bd10e8e1e8c650d847290c5a66344b9a21704fba40fc53992af205b8` |
| Frozen cohort (package artifact) | `35690b806e51eefe388fadf35b04baf5ed4c52f8e30ac193a38cf88246332824` |
| Frozen draws (package artifact) | `fe54808e282515807703692fb08cf3928ee9a4435d04b6939f2b9f47157e4a8a` |

The CLI returns-mode path now, **before anything is loaded**: (i) refuses any caller-supplied `--*-sha` that disagrees with its pinned constant; (ii) runs `verify_pinned_inputs(...)`, which hashes the four input **files** and compares them to the compiled-in constants only — the function has **no parameter for a caller-supplied expected hash**; (iii) calls the loaders with the pinned constants, never with CLI arguments. The inventory and price-input constants cross-check exactly against the package's exec-prices descriptor, which records the same two hashes (`351cff4f…`, byte-identical carry).

**Evidence (synthetic + hash-only verification of the genuine bytes):**
- **Positive control, genuine bytes:** the archived P7b inventory and the archived execution-price file (qf-data-archive copies) hash to the two private pins, and the package's cohort/draws artifacts hash to the two public pins; `verify_pinned_inputs` over those four genuine files returns True. Hashes only — no private content is in this package.
- **Attack case (a) — altered but well-formed file:** a cohort JSON tampered in one field (still valid, parseable, with a well-defined hash of its own) is **refused** by the binding, in the suite and in the package verifier.
- **Attack case (b) — caller-supplied self-consistent hash:** fixture files passed together with their own correct hashes are **refused** under the shipped pins, in-process and at CLI level (exit 2, no output written); a supplied hash that disagrees with its pin is likewise refused (exit 2). Once the binding is satisfied (fixture pins patched only inside a test subprocess), the GO gate still refuses (exit 3, no output) — the gate order is binding → load → GO gate.
- **Mechanism positive control:** the same fixture bytes verify under fixture pins via the explicit test-only override (the execution entry point never uses it).

## Item 2 — interval semantics clarified (wording only)

**Finding:** the bootstrap bounds were labeled `lower_95` / `upper_95` without stating what they are. They are the 5th and 95th percentiles of the resample means: **p5 and p95 are SEPARATE one-sided 95% bounds; jointly they form a CENTRAL 90% interval — NOT a two-sided 95% interval.**

**Fix (labels/descriptions only — no numeric change, no computation change):**
- `artifacts/exp14_output_schema.json`: the `block_bootstrap`, `cluster_bootstrap`, `interval_lower_95`, and `interval_upper_95` descriptions now state the one-sided / central-90% semantics verbatim; a fail-closed entry for the item-1 binding was added. A machine deep-diff against the corr1 schema confirms changes at exactly those paths (plus the version strings) and nowhere else.
- `code/exp14_buy.py`: the `circular_block_bootstrap` and `cluster_bootstrap` docstrings and the comment at the emitted `primary_paired_excess` interval keys carry the same clarification.
- The emitted field names and every number are unchanged; the no-PASS/FAIL-token rule is intact (the suite's whole-output token scan still passes).

## What did NOT change

- **Byte-identical carries from corr1:** `AMENDMENT.md` (`417aa0ba…`), `CORRECTION.md` (`e3dce161…`), feasibility (`80c9f5fe…`), cohort (`35690b80…`), draws (`fe54808e…`), exec-prices descriptor (`351cff4f…`), price-input builder (`2a0d9f0c…`). Cohort/draws/feasibility/seeds/matching: **zero drift**.
- Seeds unchanged: master **7715012043445510037**, bootstrap **6050949521315240661**. The original EXP-14 protocol's **STOP stands**; Decision B's four conditions stand (311 / 240 / 71 / 22.83% disclosed; matched subpopulation only; no validated-edge claim; no live-strategy change).
- `RETURNS_ENABLED` is still **False** in this pin. **No real return of any kind was computed.**

## Tests

`tests/test_exp14_synthetic.py` — **110 checks, 0 failures** (corr1's 101, with two CLI checks re-pinned to the corr2 gate order, plus 9 corr2 checks: pinned constants exact; genuine-artifact positive controls ×2; attack (a); attack (b) in-process; mechanism positive control; interval-semantics docstring pin; CLI gate-after-binding ×2). `verify_package.py` — **PASS** (all corr1 checks retained, plus the corr2 section: constants == approved hashes == descriptor pins; genuine-artifact verification; both attack cases re-proven on verifier-local fixtures; schema semantics + fail-closed entry; CORRECTION2 record).

## Pins

| Artifact | SHA-256 |
|---|---|
| Script `code/exp14_buy.py` (v3, corr2) | `77bd53e82963d65ab743a57f1eff0d23b54467a0e17aaf1831b42e6e96b6f3d8` |
| Synthetic suite `tests/test_exp14_synthetic.py` (corr2) | `182973fb2d98f38871e2750ef1a4e0a62f2c428d7b9190de9a17ea4ff8e415db` |
| Output schema `artifacts/exp14_output_schema.json` (corr2) | `48a9534dfe6cc295b8864f8be2110822352cb725a37ec1baae086b06925688fc` |
| Package verifier `verify_package.py` (corr2) | `ea48b685b97f7905991d6864d0ca5f6bf406bcb4b6ebeb528f8170ad2c49c4a7` |
| Frozen cohort / draws / feasibility (unchanged) | `35690b80…` / `fe54808e…` / `80c9f5fe…` |

## Readiness boundary — what happens next

This package is submitted for ChatGPT's **readiness PASS** on the corr2 finding. Execution of the single EXP-14B run follows that PASS under Mike's recorded conditional GO (comment `6406229148`) — **no new GO is requested, and none is needed for this exact single run**. Muse **will NOT execute before** the readiness PASS lands, and will notify on the desk before running. If any required check fails at execution time, the run STOPs without real outcomes and the precise defect is surfaced.

Bounds kept: original EXP-14 STOP preserved; C1 FAIL preserved; DEV exploratory only; holdout SEALED; production PAUSED; S1 LAUNCH_HOLD. No performance figure of any kind appears in this package.
