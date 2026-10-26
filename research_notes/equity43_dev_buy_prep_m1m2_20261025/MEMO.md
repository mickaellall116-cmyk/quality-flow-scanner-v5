# M1/M2 preparatory package — P7b inventory + EXP-14 pin (preregistration v0.3)

**Date:** 2026-10-25 (ET). **Author:** Muse. **Status:** PREPARATORY, NO-RETURN work only. Nothing in this package computes a forward return, a return-based variance or power figure, an EXIT arm, or a backtest on real data. No holdout contact, no vendor call, no production / pilot / S1 change, no trading.

**Governing texts.**
- Issue #1 comment `6405097569` (ChatGPT, 2026-10-25): Claude Final-Gate Review verdict relay — **CONDITIONAL GO for preparing the exploratory DEV BUY study**, with exactly two prerequisites: **M1** build the outcome-blind full observed-bar inventory (P7b) across the DEV generator domain, including non-signal bars and ATR/EMA state, prove signal flags reconcile to the 2,892 existing fires, use synthetic pool-count/negative fixtures; **M2** pin the EXP-14-BUY-DEV-EXPLORATORY script, de-clustered event cohort, deterministic matched-control draws, source hashes and synthetic tests — all before computing any forward returns. Preparatory inventories, no-return pool-count checks, frozen cohort/draws and synthetic tests require no new performance GO; computing actual historical forward returns does.
- Issue #1 comment `6401471382` (ChatGPT independent v0.3 review): HOLD 1 — the v0.3 feasibility §6 claim that the matched-control pool check is "runnable from committed metadata" is unsupported: the all-fire journal writes rows only where the BUY signal fired. Correct to BLOCKED/UNPROVEN unless an exact full-bar artifact is named and hash-pinned; the repair is outcome-blind (schema/coverage/count checks only). (HOLDs 2 and 3 of that review are, per comment `6405097569`, Tier-4-only and EXIT-study-only respectively and are **not** part of this package.)
- Claude's artifact (claude.ai/artifact/HG5ywz7qhhF88GuRy4j66w) sits behind a sign-in wall from this environment and was **not** read directly; the relayed verdict in comment `6405097569` is the governing text used.
- v0.3 draft §5 (the study design implemented here) and §6 (statistics), package `research_notes/equity43_dev_prereg_v03_20261025/` at `b65696a`.

**Single-dispatch check (run before any file operation): CLEAR.** No stage directory, worktree, or pre-execution commit for M1/M2/P7b/EXP-14 exists on origin/main or locally. (The one `--grep` hit, `f84e8c0` "M1/M2 rationale corrections", belongs to an unrelated canonical-spec revision; `qf_prereg32_stage/` is a read-only -28 extraction workspace, not an execution stage.)

---

## M1 — P7b every-observed-bar inventory

**Builder:** `code/build_p7b_inventory.py` (hash in `SHA256_MANIFEST.txt`). It consumes **only** existing committed DEV bytes: the -13 stage assets (archive namespaces `td_pilot_20261023` + `td_capture_equity39_continue_20261023`), admitted by the frozen `run_study13` phase2 path and resampled by the frozen phase4 session-anchored resample; indicators from the frozen `engine_successor/pine_backtest.add_pine_indicators`; signal flags from the frozen `pine_buy_signal`. Every input is hash-pinned in `artifacts/p7b_coverage.json` (`input_pins`: session table, driver, engine, the committed P7 journal/summary, and the SHA-256 of each symbol's raw DEV capture file).

**Schema (per bar):** `symbol, idx, ts, session_date, session_ordinal` (position in the 524-session DEV subset of the adopted 751-session table), `bin` (09:30 / 13:30), `close, atr` (ATR(14)), `atr_pct` (= atr/close), `ema21, ema55, ema200, signal` (frozen BUY flag on the completed bar), `in_generator_domain` (215 ≤ idx ≤ n−2). Nulls are the frozen indicators' own NaN warmup — never filled.

**Coverage (from `artifacts/p7b_coverage.json`):**
- Symbols: **43**; bars per symbol: **1,043**; total bars: **44,849**; window 2024-09-16 09:30 ET → 2026-10-16 13:30 ET.
- Generator-domain bars: **827 per symbol, 35,561 total**.
- Bin totals: 09:30 — 22,532; 13:30 — 22,361.
- **Missing fields: ZERO** — in the generator domain, and in fact across the full series, for atr / atr_pct / ema21 / ema55 / ema200 for all 43 symbols (the frozen indicators are `ewm`-based and defined from the first bar — no NaN warmup exists in this engine; recorded as observed from the artifact, per-symbol counts inside). Every field M1 requires is computable from the committed bytes; **no BLOCKED items**.

**Reconciliation (the M1 acceptance test):** the inventory's generator-domain fire set vs the committed P7 journal (`539e0a9`): **2,892 = 2,892, symmetric difference 0 — RECONCILED EXACTLY.** The journal's committed class partition (590 MATCHED_CANDIDATE + 2,301 SUPPRESSED_OVERLAP + 1 GAP_INELIGIBLE_ENTRY) is over the same 2,892 keys.

**Determinism:** the builder was run twice to completion in clean conditions; both runs produced byte-identical output, SHA-256 **`a6bbd19a702120cafd48cd01ee4c8ff59b838a8bd6439822415d6c18278ef02f`**. (Disclosure: a first launch was killed by a runtime restart and briefly overlapped the second; its read-back hash, taken mid-overlap, was discarded. The canonical hash above is the twice-reproduced one, and the delivered file was independently re-validated: 44,849 parseable rows, complete ordered per-symbol index sequences, exact fire reconciliation.)

**Placement (data-rights discipline):** the full inventory contains per-bar closes for the DEV window — derived from Basic-tier vendor bytes, it is **not** committed to this public repo. It is placed in the private `qf-data-archive` at `research_inventory/p7b_20261025/` (commit `282531d`, remote-verified; SHA256SUMS inside), and hash-pinned here. Only schema/coverage/count/reconciliation metadata is published in this package — exactly the publication scope comment `6401471382` prescribes.

## M2 — EXP-14-BUY-DEV-EXPLORATORY, pinned

**Script:** `code/exp14_buy.py` (hash in `SHA256_MANIFEST.txt`), implementing v0.3 §5 as drafted:
- **Events:** generator-domain fires, de-clustered — an event is kept only if the same symbol had no signal bar in the previous 20 bars.
- **B-A pool:** same symbol, same bin, session ordinal within ±30 sessions, no signal bar within ±20 bars, ATR% within ±25% (relative), full forward window inside the data.
- **B-T pool (diagnostic, non-gating):** B-A construction + Close > EMA200, EMA21 > EMA55, signal false.
- **Relaxation ladder (fixed order):** step 0 base → (a) ATR% ±40% → (b) ±45 sessions → (c) minimum pool 6; frozen at the first step with event drop rate ≤ 15%.
- **Draws:** 20 without replacement per retained event (whole pool if fewer than 20); deterministic per event — sub-seed = first 8 bytes (big-endian) of SHA-256(`MASTER_SEED:arm:symbol:idx`); `MASTER_SEED` = first 8 bytes (big-endian) of SHA-256("EXP-14-BUY-DEV-EXPLORATORY") = **7715012043445510037**.
- **Horizons:** 5 / 10 / 20 bars, 10 primary. Pool feasibility and the frozen draws use the primary horizon's forward-window rule; h=20 pool counts are published alongside.
- **Interpretation P-1 (recorded, not silent):** pool bars are restricted to the generator domain — the only bars whose signal status the P7 census certifies. §5 does not state the pool's domain explicitly; this is the conservative reading and is flagged for adjudication with the GO request.
- **Returns mode is DISABLED in this pinned version:** any invocation raises `ExecutionGoRequired`. Enabling it is a new version + new pin + the separate execution GO below.

**Synthetic fixtures:** `tests/test_exp14_synthetic.py` — **35 checks, 0 failures**: de-clustering (incl. the 20/21-bar edge and chain semantics), ±20 exclusion edges, same-bin, session-window, ATR%-band edges (binary-exact boundary), missing-field exclusion, domain restriction (P-1), forward-window rules at h=10/h=20, B-T filter legs, ladder selection on a crafted sparse universe, draw determinism / per-event and per-arm seed sensitivity / small-pool whole-draw, and the three fail-closed negatives (returns gate, inventory-hash mismatch, census mismatch).

**Outcome-blind feasibility results (from `artifacts/exp14_feasibility_counts.json`; pool sizes and counts only — no returns, no group differences):**
- Census fires reconciled in-script: 2,892 (the script refuses to run otherwise).
- De-clustered events: **320**. Dropped by the forward-window rule: h=5 → 2, h=10 → 3, h=20 → 9 → primary-horizon cohort **317**.
- Ladder (B-A, drop = pool below minimum): step 0 → 174 dropped (**54.9%**); (a) → 141 (44.5%); (b) → 95 (30.0%); (c) → 72 (**22.7%**). **The ladder exhausts at step (c) with the >15% drop flag ON** — the predeclared ladder, applied exactly as drafted, does not bring the DEV drop rate under 15%. Frozen step: **(c)** (band ±40%, window ±45 sessions, minimum pool 6), flag recorded.
- Retained events: **245** (≥ the §6 H-BUY validity floor of 200 de-clustered events; the cohort itself is 317). B-A pools at the frozen step: median 15; 135 events have ≥20 (full draws); 38 events have an empty pool.
- Retained event mix (draft §5 [C14]): by bin — 09:30: **206**, 13:30: **39**; by symbol — all 43 symbols present (full table in the artifact).
- B-T diagnostic at the frozen step: median pool **0**; only **45** of the 245 retained events have a B-T pool ≥ the minimum; **200** fall below. As constructed, B-T is largely infeasible on DEV — reported as a design fact; B-T is non-gating and no rule was altered to rescue it.
- Frozen cohort: `artifacts/exp14_frozen_cohort.json`; frozen draws (bar identities only — no prices, no returns): `artifacts/exp14_frozen_draws.json` (245 B-A draws; 45 B-T draws).

**What this means, stated plainly:** M1 and M2 are complete as specified — the evidence gap behind HOLD 1 is closed and the study machinery is pinned and proven on fixtures. The feasibility outcome itself is a **design-level finding for adjudication, not a pass**: the matched-control construction as drafted sheds 22.7% of events even fully relaxed, and its diagnostic baseline (B-T) is mostly empty on DEV. Whether to (i) execute as frozen with the flag recorded, (ii) amend the construction (a design change — new draft text, re-adjudication), or (iii) let the freeze decision absorb it, belongs to ChatGPT's adjudication and Mike's freeze calls (checklist B4). This package changes no rule to make the numbers prettier.

## §6 correction (v0.3 package amendment A1)

`research_notes/equity43_dev_prereg_v03_20261025/OUTCOME_BLIND_FEASIBILITY.md` §6 is corrected **as an amendment, not a silent edit**: the delivered verdict text is retained and marked as the as-delivered wording; amendment block **A1** records that the claim "RUNNABLE from committed metadata" was wrong (the all-fire journal cannot enumerate non-signal bars), states the corrected BLOCKED/UNPROVEN verdict, and records the closure (P7b + this package). The same correction is applied to the bottom-line sentence. `CHANGELOG_V03.md` gains register row **C26**; `FREEZE_BLOCKER_CHECKLIST.md` gains row **A7** (evidence closed; the freeze itself remains HOLD on the open B/C items). The v0.3 package manifest is re-hashed and its `verify_package.py` still passes. No rule, threshold, or design element anywhere in v0.3 changes.

## The exact separate GO request for execution

> **GO REQUEST — EXP-14-BUY-DEV-EXPLORATORY execution (one run, DEV only).**
> Requesting the user's (Mike's) explicit GO, after ChatGPT adjudication of this package, to:
> 1. Enable the returns mode of EXP-14 as a **new pinned version** (the only change: `compute_forward_returns` activated; every other byte of the study logic identical, re-hashed, synthetic suite re-run).
> 2. Run it **once** on the hash-pinned P7b inventory (SHA-256 `a6bbd19a…`, private archive `research_inventory/p7b_20261025/`) with the frozen cohort (317 events), frozen ladder step **(c)** — with the >15% drop flag (22.7%, 72 events) recorded in the output — and the frozen draws in this package. No re-draws, no re-clustering, no parameter changes, no further relaxation.
> 3. Compute, per v0.3 §5: for horizons 5/10/20, each retained event's ATR-normalized forward return (entry = open of bar i+1; exit = close of bar i+h; divided by the signal bar's ATR) and the paired excess vs its drawn B-A control mean (primary endpoint h=10) and B-T diagnostic where a B-T draw exists; report per §5/§6 — n, dropped counts, the wider-of-two interval rule (circular block bootstrap over calendar time, 20-session blocks, 10,000 reps; seed per the frozen contract once the freeze supplies the preregistration hash), and the UNDERPOWERED FOR PASS label where it applies.
> 4. Adjudication points carried into the GO, not decided by it: interpretation P-1 (pool restricted to the generator domain) and the step-(c) drop flag. If adjudication amends either, the cohort/draws are re-frozen in a successor package before any execution.
> 5. Data scope: **DEV window only** (2024-09-16 → 2026-10-16, 43 symbols). Holdout untouched and sealed; no vendor calls; no EXIT arms; no full-system replay; no production/pilot/S1 contact.
> 6. Label: **DEV EXPLORATORY** — the October C1 FAIL verdict stands; a result here informs the freeze decision, never a validated edge.
>
> Until that GO is given, the returns mode stays disabled and this package is the complete deliverable.

## Bounds kept

C1 FAIL preserved; DEV exploratory only; G4 UNADOPTED; S1 LAUNCH_HOLD; production PAUSED; holdout SEALED. No performance figure of any kind appears in this package.
