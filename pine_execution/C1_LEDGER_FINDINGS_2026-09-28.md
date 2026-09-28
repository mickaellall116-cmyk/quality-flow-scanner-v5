# C1 143-trade ledger — forensic findings (2026-09-28)

Per Mike's protocol (2026-09-27): first ask Muse for the exact artifact/code/data
that generated the 143-trade C1 result; only if unavailable, reconstruct from
frozen components subject to the acceptance gate (143 trades, +0.337R,
+52.25%, ~31.63% DD).

## 1. The original per-trade ledger file was never saved
Searched: this VM (workspace + scanner repo), GitHub repo (Contents API),
Claude (already confirmed it doesn't have it). No per-trade ledger artifact
exists anywhere. Only summary figures survive.

## 2. The 143-trade C1 was generated with a bug (PROVEN)
`pine_backtest.pine_buy_signal` (pre-2026-09-20) computed `trendScore` with
plain NumPy boolean addition. Verified directly: `np.bool_ + np.bool_`
collapses to a single boolean (logical OR), so the 0–5 integer score was
actually {True, False} — making `score >= 4` and `score >= 3` ALWAYS False.
Consequence: the `confirmed` and `ready_buy` entry conditions were DEAD CODE
in every pre-Sep-20 run. Only `breakout_buy` entries ever fired.

Proof by reproduction (this VM, frozen code + Sep-15 H4 cache, buggy signal
restored via monkeypatch in a COPY — no frozen file modified):
- Buggy signal: 263 candidates → 143 trades, +0.337R, +52.25%, 31.63% DD
  — EXACT match to the canonical figures. Script: `c1_bug_verify.py`.
- Fixed signal: 877 candidates → 240 trades, +0.178R, +42.24%, 38.46% DD
  — gate FAIL. Script: `c1_ledger_reconstruct.py`.

## 3. Timeline of the reference files
- 2026-09-18 11:22–11:24: pine_stack study (263 candidates, buggy signal) →
  C1@4bps = 143/+0.337/52.25/31.63; execution study fidelity check PASS.
- 2026-09-20 10:35: `pine_backtest.py` fixed (int() casts per condition).
- 2026-09-20 10:40: "corrected rerun" of pine_stack.py → 877 candidates,
  C1@4bps = 240/+0.178/42.24/38.46 — OVERWROTE `pine_stack/stack_results.json`.
  The file that EXECUTION_SPEC.md / PARITY_SPEC.md / SLICE3-5 cite as the
  143-trade reference now holds 240-trade figures.
- `pine_stack/archive/C1_BASELINE_INVALID__numpy_boolean_trendScore_bug.json`
  labels the 143-trade figures INVALID / obsolete, replacement =
  `stack_results_C1_CORRECTED_SCORE_BASELINE.json`.

## 4. Where the canonical summary figures still survive
- `pine_execution/execution_results.json` → cases.E0_4bps.C1
  (143 / 0.337 / 52.25 / 31.63 — written 2026-09-18, fidelity-verified)
- `pine_execution/EXECUTION_SPEC.md`, `docs/PARITY_SPEC.md`,
  `pine_live/SLICE3.md`, `pine_live/SLICE4.md`, `pine_live/SLICE5.md`,
  `pine_ablation/ABLATION_SPEC.md` — all cite 143/+0.337/+52.25%/31.63%.

## 5. Open adjudication (for ChatGPT)
Mike's acceptance gate — reproduce 143 trades, +0.337R, +52.25%, ~31.63% DD —
is satisfiable ONLY with the buggy code. Two readings:
  (a) Pin the buggy artifact: the gate reproduces exactly what was validated
      and frozen; the bug is then part of the frozen spec (breakout-only
      entries), documented as such.
  (b) Update the gate to the corrected baseline: 240 trades, +0.178R,
      +42.24%, 38.46% DD @4bps — but this INVALIDATES every downstream
      reference (execution fidelity, parity spec, slices, ablation) and
      re-opens the stack decision (C1 vs C2 vs C3 were compared on buggy
      numbers; the corrected rerun's C2@4bps = 292 trades, +0.204R, +58.93%).

No per-trade ledger for EITHER version was ever saved. No action taken on the
frozen files; `stack_results.json` left as the corrected rerun wrote it.
Awaiting adversarial adjudication before any reconstruction is canonized.
