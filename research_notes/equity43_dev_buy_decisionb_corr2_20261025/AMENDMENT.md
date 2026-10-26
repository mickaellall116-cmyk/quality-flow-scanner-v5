# AMENDMENT — Decision B: EXP-14 DEV-only matched-subpopulation study (execution-ready design, NOT execution)

**Date:** 2026-10-25 (ET). **Author:** Muse. **Status:** AMENDED DESIGN PINNED. Nothing in this package computes a forward return on real data. The finished analysis path is exercised **only on synthetic fixtures**. Returns mode remains **DISABLED** in the pinned script (`RETURNS_ENABLED = False`; the entry point raises `ExecutionGoRequired`). No holdout contact, no vendor call, no production / pilot / S1 change, no trading.

**Predecessors:** the M1/M2 preparatory package `research_notes/equity43_dev_buy_prep_m1m2_20261025/` (commit `5e02503`) and its successor `research_notes/equity43_dev_buy_prep_m1m2_succ1_20261025/` (commit `32dfdb3`) — both byte-untouched by this amendment. The frozen cohort, draws, and feasibility artifacts are carried into this package **byte-identical** from the successor (SHA-256s re-verified; see Pins).

**Governing texts:** Issue #1 comment `6405786931` (independent review: P-1 accepted; successor items 1–2 resolved; item 3 presented as the user's explicit choice) and **Decision B**, delivered by Mike in chat 2026-10-25 21:19 ET — the delivery of record, his direct Slack/GitHub posts having failed — recorded on the bridge at commit `243df1a` and on Slack (TS `1792977869.995769`). Single-dispatch check before any file operation: **CLEAR** (no Decision-B / amendment stage, worktree, or pre-execution commit existed; origin/main tip was the successor's RESULT post `e4364e7`).

---

## The decision (verbatim in substance)

> **DECISION B — adopted by Mike: a prospective amendment for a DEV-only matched-subpopulation study.**
>
> The original EXP-14 protocol remains **STOP**, because 71 of 311 events (22.8%) cannot be matched under its final rules. We will not pretend that passing the 200-event sample floor overrides that restriction.
>
> Instead, the 240 events that meet the frozen matching criteria may be studied, with these conditions:
>
> 1. **No further relaxation of matching rules or selection based on returns.**
> 2. **All 71 excluded events and the 22.8% exclusion rate must be prominently disclosed.**
> 3. **Results apply only to the matched subpopulation — not all Quality Flow BUY signals.**
> 4. **The study cannot establish a validated trading edge or authorize changes to the live strategy.**
>
> Mike verified the successor's published cohort and draw records: they reconcile to 311 eligible events, 240 retained, and no remaining 20-bar window violations in the frozen draws.
>
> **This is approval of the research-design amendment, not permission to execute the performance test.**

Milestone sequence fixed by the decision: Muse pins the amended, execution-ready design (this package) → **Mike verifies it** → **Mike's explicit separate authorization** → the single DEV exploratory run. Neither of the last two steps has happened.

## What this amendment changes — and what it does not

**Changes:** only the three implementation items from Mike's source review, closed together below (script v3, this package). **Does not change:** the study design, pools, ladder, frozen step (c), the frozen cohort (311) and draws, the seeds, the complete-window rule, the §5 endpoint formula, the inferential basis (ATR-unit paired excess; wider-of-two bootstrap interval), the DEV-only scope, or any other v0.3 item (the freeze stays HOLD elsewhere). The original protocol's STOP is preserved, not laundered: the amended study is a *different, narrower* study of the matched subpopulation, labelled as such on every output.

## Item (a) — separate private execution-only price input: CLOSED

Claude prohibited open fields in the outcome-blind P7b inventory. The successor's proposed fix (amend the inventory) is therefore **superseded by the decision**: the P7b inventory is **not amended** — its pin stands unchanged (SHA-256 `a6bbd19a702120cafd48cd01ee4c8ff59b838a8bd6439822415d6c18278ef02f`, private archive commit `282531d`).

Instead, `code/build_exec_prices.py` derives a **separate execution-only price input** — the open of every observed bar — from the **same committed DEV capture bytes through the same frozen pipeline** (run_study13 phase2/phase4) that produced the P7b inventory. **Alignment proof (fail-closed):** for all **44,849** bars, the pipeline frame's timestamp and Close equal the pinned inventory row at the same (symbol, idx) exactly — **0 mismatches** — so the input provably prices the identical series. Derivation run twice in clean conditions: byte-identical output, SHA-256 **`4adb8320bd10e8e1e8c650d847290c5a66344b9a21704fba40fc53992af205b8`**.

**Placement (raw-private guardrail):** the price file lives **only** in the private qf-data-archive — `research_inventory/exp14_exec_prices_20261025/`, archive commit `62e1bae`, SHA256SUMS inside, remote-verified. This public package publishes the descriptor only (`artifacts/exec_prices_descriptor.json`: schema, counts, alignment result, hashes, input pins incl. per-symbol raw-capture hashes) — **no prices**. In script v3 the analysis reads **no price from the inventory**: entry = price-input open[i+1]; exit = inventory close[i+h]; scale = inventory ATR[i]. Coverage is fail-closed: the price input's symbols and indices must equal the inventory's exactly, and any missing/invalid open raises.

## Item (b) — CLI returns-mode wiring: CLOSED, synthetic-proven

The v2 command line called `compute_forward_returns()` with **no arguments** — returns mode could never have run. Script v3 wires every required input as an explicit CLI argument with its expected SHA-256 (`--cohort`, `--draws`, `--exec-prices`, plus the inventory), loads and hash-checks each, builds the disclosure from the cohort artifact, and passes all of it to `compute_forward_returns(by_symbol=…, exec_prices=…, cohort_obj=…, draws_obj=…, expected_cohort_sha=…, expected_draws_sha=…, disclosure=…)`, writing `--out-analysis`. The function's arguments all default to `None` **after** the gate check, so the gate — not a `TypeError` — is what refuses every call in this pin.

Proof (all in the synthetic suite): the **plain CLI** on fixture files assembles its inputs and is refused by the GO gate — **exit 3, no output file written**; omitting the price-input wiring fails at argparse (**exit 2**); a cohort hash mismatch fails closed (**exit 2**). A **synthetic end-to-end run** (fixture inventory + fixture price input → CLI → full pipeline → output file), with the gate flipped **only inside the test's own subprocess**, exits 0 and its output matches hand-computed values exactly. The shipped pin keeps `RETURNS_ENABLED = False`, verifier-asserted.

## Item (c) — reporting: percent view, cost sensitivity, mandatory disclosure: CLOSED

The pinned output (schema: `artifacts/exp14_output_schema.json`) now includes:

- **Percentage-return views** at every horizon (mean event return and mean paired excess in percent, alongside the ATR-unit views), and `mean_pct` on the primary paired excess. Inference stays on the frozen ATR-unit basis — percent is a reporting view, not a new endpoint.
- **The declared cost-sensitivity view** (preregistration v0.3 §5, H-BUY): costs cancel in the paired difference; the output carries the descriptive line **primary paired excess (percent) minus a 25 bps round trip**, labelled descriptive-only, never a verdict input.
- **A mandatory disclosure header** (Decision B condition 2): eligible / retained / excluded counts and the exclusion rate, **recomputed from the cohort artifact by the analysis itself** and **fail-closed** — output is refused if the disclosure is absent, miscounted, or its scope/basis text drifts from the pinned Decision B texts. On the frozen cohort it reads: **311 eligible, 240 retained (matched), 71 excluded (unmatched), 22.83%**. The scope statement is pinned verbatim: *results describe only the matched subpopulation; they do NOT describe all Quality Flow BUY signals; they establish no validated trading edge* (conditions 3–4).
- Labels remain **DEV EXPLORATORY** with claim **NONE**; the output's verdict field is the const NONE statement — **no PASS/FAIL labels anywhere**.

## Synthetic tests

`tests/test_exp14_synthetic.py` — **91 checks, 0 failures**: the full v2 coverage adapted (seeds, de-clustering, exclusion, window rule, pools, B-T, ladder, draws, census and hash gates, analysis negatives) plus the Decision B proofs — hand-computed percent excess and the 25 bps cost line; exec-price coverage/shape/duplicate/smuggled-field negatives; the planted-bogus-inventory-`open` proof that entry prices come only from the price input; disclosure absent/miscounted/reworded negatives; the CLI gate, wiring, hash, and end-to-end tests above. `verify_package.py` re-checks the manifest, the byte-identical frozen-artifact carry and its coherence, the Decision B record, the descriptor, the schema, the gate, and the suite — **PASS**.

## Pins

| Artifact | SHA-256 |
|---|---|
| Amended script `code/exp14_buy.py` (v3) | `777cc035d8b6fc17c2ca8ef31de338ccd41f8e7832edd5db97a5e4027853c661` |
| Price-input builder `code/build_exec_prices.py` | `2a0d9f0c7469a99e27250870c61421f8abbb173c3f5f10a37fe2d2017f6f343b` |
| Execution-only price input (PRIVATE, archive only) | `4adb8320bd10e8e1e8c650d847290c5a66344b9a21704fba40fc53992af205b8` |
| P7b inventory (unchanged, PRIVATE) | `a6bbd19a702120cafd48cd01ee4c8ff59b838a8bd6439822415d6c18278ef02f` |
| Frozen cohort (carried from `32dfdb3`) | `35690b806e51eefe388fadf35b04baf5ed4c52f8e30ac193a38cf88246332824` |
| Frozen draws (carried from `32dfdb3`) | `fe54808e282515807703692fb08cf3928ee9a4435d04b6939f2b9f47157e4a8a` |
| Feasibility counts (carried from `32dfdb3`) | `80c9f5fe708f67e3dcea5cb84efd83d477511536e152a79589cf6dc041567684` |

Seeds unchanged: master (draws) **7715012043445510037**; bootstrap **6050949521315240661**.

## Status and the next milestone

This package is the pinned amended, execution-ready design. **STOP here.** The next steps belong to Mike: (1) his verification of this package; (2) his explicit separate authorization. Only then may a successor pin flip the gate and run the study **once** — DEV window only (2024-09-16 → 2026-10-16, 43 symbols), on the pinned cohort/draws and the pinned price input, reporting per the pinned schema with the disclosure header on the output. Until then the returns mode stays disabled and no result exists.

Bounds kept: original EXP-14 STOP preserved; C1 FAIL preserved; DEV exploratory only; G4 UNADOPTED; S1 LAUNCH_HOLD; production PAUSED; holdout SEALED. No performance figure of any kind appears in this package.
