# CRT sign correction — QF-CRT-SIGN-CORRECTION-20261013-01 r1 — RESULT

**Authorization:** Mike, direct, main chat 2026-10-13 14:13 EDT ("Run the bounded
sign-fix correction"). Work order: GitHub Issue #1 comment 6148146821.
**Budget:** 30 minutes, one repair/rerun allocation. **Actual effort: ~14 minutes.**
Zero vendor calls, zero spend, no Tiingo data, no frozen/production changes.

## ⚠️ Run label

**REPLACEMENT RUN on the newly pinned current cache — NOT a reproduction of the
Oct 12 run.** The original Oct 12 input bytes were never pinned and may have
drifted; the 14 cache files were SHA-256-pinned immediately before this run
(`pine_claims_crt/cache_manifest_20261013.json`, pinned 2026-10-13 14:14 EDT,
before any code change or execution).

## Work-order compliance checklist

- [x] Cache pinned BEFORE execution: 14/14 files, full SHA-256, in
      `cache_manifest_20261013.json`.
- [x] Fix limited to the two sign expressions in `_manage` — patch:
      `pine_claims_crt/sign_fix_patch_20261013.diff`. `r1`: `(entry − tp1)` →
      `(tp1 − entry)`; `r2`: `(entry − exit_px)` → `(exit_px − entry)`, each
      still `× d / entry / risk_frac` per the surrounding structure. No rule,
      gate, universe, split, cost, stop-geometry, or variant change. Original
      preserved in git at `3c7ddb8` (sha256 bf587693…).
- [x] Deterministic unit fixtures (`test_sign_fixtures.py`): long +1R,
      long −1R, short +1R, short −1R, TP1 blended exit.
      **Old code: 0/5 pass** (every implied R exactly negated).
      **Corrected code: 5/5 pass.** Captured output:
      `test_sign_fixtures_output.txt`.
- [x] Exact preregistered set executed ONCE: BASE / CRT-LONG /
      CRT-LONG-MARGIN / CRT-SHORT / CRT-LS. Runtime 5.7 s. Full stdout:
      `crt_run_stdout_20261013.log`; full results:
      `crt_results_corrected_20261013.json` (sha256 6faa02e8…).
- [x] Original `crt_results.json` NOT overwritten — restored byte-identical
      after the run (sha256 f999508f…, verified) and preserved as adverse
      failed-implementation evidence.
- [x] Verdict against the UNCHANGED frozen gate (README pre-registration).

Consistency check inside the run: BASE re-ran at 237 trades, **+0.239R @25bps**
— identical to the canonical baseline, as in the original study.

## Corrected headline numbers (replacement run)

| Variant | Trades | @25bps | @50bps | PF @25 | Notes |
|---|---|---|---|---|---|
| BASE | 237 | **+0.239R** | +0.178R | 1.38 | unchanged, reproduces canonical |
| CRT-LONG | 811 | **−0.037R** | −0.234R | 0.96 | val 2025–26: n=596, **−0.108R**; dev: +0.163R |
| CRT-LONG-MARGIN | 518 | **+0.020R** | −0.100R | 1.03 | perturbation |
| CRT-SHORT | 835 | **−1.002R** | −1.420R | 0.43 | see consistency note |
| CRT-LS | 1,116 | **−0.602R** | −0.902R | 0.61 | claim as stated |

(For reference, the withdrawn Oct 12 figures were: LONG −0.358R, MARGIN
−0.261R, SHORT +0.165R, LS +0.001R. ChatGPT's cost-pair algebra diagnostics in
6148146821 predicted −0.037 / +0.021 / −1.001 / −0.601 — the corrected run
lands on those values to within rounding.)

## Gate verdict — FAIL (unchanged gate, applied as written)

PASS requires ALL of: pooled CRT-LONG ≥ +0.35R @25bps AND ≥ 60 trades AND
validation-half expectancy > 0 AND @50bps ≥ +0.15R AND no symbol > 40% of
total net R.

1. CRT-LONG @25bps ≥ +0.35R → actual **−0.037R** — **FAIL**
2. Trades ≥ 60 → actual **811** — pass
3. Validation (2025→Sep 2026) > 0 → actual **−0.108R** — **FAIL**
4. CRT-LONG @50bps ≥ +0.15R → actual **−0.234R** — **FAIL**
5. Concentration ≤ 40% of total net R → leg total net R is **−29.72R**
   (negative); the largest positive contributor (RKLB, +60.25R) alone exceeds
   the entire net — clause fails in substance; with a negative total it has no
   passing interpretation. — **FAIL**

Under the README's own verdict scale this is also a FAIL (expectancy negative
and below the +0.239R in-study baseline). The correction changes the numbers,
not the verdict: **Candle Range Theory sweep-and-return remains FAIL on 4H.**
The original Oct 12 numbers remain withdrawn / NOT ACCEPTED; this replacement
run is the citable record.

## Short-leg consistency (requested check)

The old output's contradiction is **gone**. Old: mean **+0.165R** alongside
portfolio total return **−101.94%** (opposite signs — the visible symptom of
the inversion). Corrected: mean **−1.002R** with portfolio total return
**−139.0%** — signs agree; the short leg was deeply negative all along, and
the previously reported HOOD-driven short "edge" was an artifact of the sign
inversion. (A total return beyond −100% remains arithmetically possible in
this fixed-fractional simulator given the claim's near-zero stop distances —
a stop-geometry pathology already recorded in the original study — but it no
longer contradicts the leg's mean R.)

## Deliverables

- `pine_claims_crt/run_crt.py` — corrected in place (two lines only)
- `pine_claims_crt/sign_fix_patch_20261013.diff`
- `pine_claims_crt/test_sign_fixtures.py` + `test_sign_fixtures_output.txt`
  (old FAIL / new PASS)
- `pine_claims_crt/cache_manifest_20261013.json` (14 SHA-256 pins, pre-run)
- `pine_claims_crt/crt_results_corrected_20261013.json` +
  `crt_run_stdout_20261013.log`
- This note. Nothing committed by the executing agent; parent commits
  centrally.

— Muse, 2026-10-13
