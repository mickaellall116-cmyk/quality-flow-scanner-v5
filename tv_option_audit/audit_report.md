# TradingView Option Audit — frozen V3.6: FINAL REPORT

Date: 2026-09-18. Namespace: `tv_option_audit/` (new files only).
Spec: `tv_option_audit/audit_spec.md` (pre-registered before evaluation).

## Executive verdict

**No TradingView option improves frozen V3.6. Nothing advances. Nothing is
implemented. The freeze stands — strengthened.**

Phase 1 turned up **zero category-5 options** (genuinely untested optional
signal logic). Every selectable element of the canonical V3.6 signal had
already been through one-variable ablation on 2026-09-18
(`pine_entry_ablation/`, pre-registered spec, candidates frozen before 2022
validation). The exotic-sounding options from the brief — FVG, BOS/CHOCH,
liquidity sweep, MTF alignment — do not exist in the canonical V3.6
implementation at all; they are absent features, not deferred options, and
testing them would mean inventing new entry logic (closed door). No new
ablations were run, because there was nothing untested to ablate. Re-running
the completed ablation to shop for better numbers would itself have been a
protocol violation (§6 of the spec).

## 1. Inventory summary

Canonical implementation: `pine_backtest.py::pine_buy_signal` (the V3.6 Pine
Script source with the input panel is not present locally; only older v1.1 /
v1.7 reference scripts exist). Eight signal components + three entry modes,
all verified against code (full catalog in `phase1_inventory.md`):

- Category 1 (canonical): `volume_ok`, `hot_guard`, `trend_bull`,
  `strong_trend`, `score_gate`, `breakout`, `ready_prev`, modes
  `confirmed`/`breakout_buy`/`ready_buy` (Hybrid OR).
- Category 2 (display-only): none in the research implementation.
- Category 3 (legacy/unused): `ready_prev` (never binds), `confirmed` and
  `ready_buy` modes (zero signals in 2y × 51 symbols).
- Category 4 (tested): all of the above — see §2.
- Category 5 (untested): **zero**.

On Mike's TradingView memory (cycling Conservative/Hybrid/Aggressive gave
materially different backtests): the canonical code has no Conservative or
Aggressive selector. Conservative ≈ `confirmed_only` → **0 trades in two
years**. The differences he saw are not reproducible from V3.6 options; they
came from a different script version's inputs or chart/window selection —
the artifact hypothesis, confirmed as far as the canonical code can speak.

## 2. Phase 2 — one-variable ablations (existing evidence, evaluated against the pre-registered rule)

The 2026-09-18 entry ablation ran exactly the §3 protocol: V0 baseline vs
V1–V13, one change each, no parameter search, exploratory window UX51 4H
2024-09-16→2026-09-14 (4bps/25bps) → 2022 validation (32 symbols, 4H,
signals ≥2022-01-01, EOD liquidation). Verdicts below apply the §4
earn-its-place rule.

Exploratory window (4bps), baseline V0: 263 trades, 44.9% win, **+0.195R**,
PF 1.27, +35.3%, DD 35.2%.

| Variant | One change | Trades | Exp (R) | Δ vs base | PF | 2022 Exp (R) | Verdict vs rule |
|---|---|---|---|---|---|---|---|
| V1 no_volume | drop `volume_ok` | 350 | +0.231 | +0.036 | 1.35 | +0.007 (in C1) | **REJECT** — wins bull, collapses in bear (PF 1.01 = noise) |
| V2 no_hot_guard | drop `safe` | 566 | +0.318 | +0.123 | 1.48 | +0.007 (in C1) | **REJECT** — textbook bull-win/bear-loss; bear-market insurance, kept |
| V3 no_trend_bull | drop from breakout | 531 | +0.082 | −0.113 | 1.17 | — | keeper (removal hurt); not a candidate |
| V4 no_strong_trend | drop from breakout | 512 | +0.145 | −0.050 | 1.21 | — | keeper (removal hurt); not a candidate |
| V5 no_score_gate | drop score≥4/≥3 | 1092 | +0.178 | −0.017 | 1.28 | −0.089 (in C2) | **REJECT** — fails outright on 2022; floods 829 extra trades, DD +10.4pp |
| V6 no_breakout | drop 10-bar break | 1309 | +0.139 | −0.056 | 1.30 | — | keeper (avg winner 2.02→1.27R); not a candidate |
| V7 no_ready_prev | drop from ready | 263 | +0.195 | 0.000 | 1.27 | — | no-op; nothing to adopt |
| V8 confirmed_only | only confirmed | 0 | — | — | — | — | **REJECT** — insufficient evidence (zero trades) |
| V9 breakout_only | only breakout_buy | 263 | +0.195 | 0.000 | 1.27 | — | ≡ baseline; no incremental value |
| V10 ready_only | only ready_buy | 0 | — | — | — | — | **REJECT** — zero trades |
| V11 no_confirmed | drop confirmed | 263 | +0.195 | 0.000 | 1.27 | — | no-op |
| V12 no_breakout_mode | drop breakout_buy | 0 | — | — | — | — | **REJECT** — zero trades |
| V13 no_ready_mode | drop ready_buy | 263 | +0.195 | 0.000 | 1.27 | — | no-op |

Frozen candidates built from the bull-window evidence (C1 = drop
volume_ok+hot_guard; C2 = C1 minus score_gate; C3 = C2 breakout-only), all
frozen BEFORE 2022: C1/C3 passed the research bars (+0.283R) and collapsed
on 2022 (+0.007R); C2 failed outright (−0.089R). Per the anti-overfit
commitment, no fourth candidate was built. Prior verdict, unchanged: **KEEP
V3.6**.

Net assessment against the rule: the only variants that "improved"
expectancy in the bull window (V1, V2) are exactly the ones the rule
rejects — they won bull and lost bear. Every other variant either hurt,
did nothing, or had no trades. **Zero survivors.**

## 3. Phase 3 — final-stack confirmation

Not run: no option survived Phase 2, so there is no candidate to test
against the locked four-layer stack (V3.6 + rs_top2 + sector cap + 5% risk
gate).

## 4. Limitations

- **Windows:** two (exploratory 2024-09-16→2026-09-14 + 2022 validation).
  No third unseen validation window exists in the prior work; the brief's
  "any existing unseen validation window" clause found none to use.
- **No new compute:** all Phase 2 evidence is the 2026-09-18 entry ablation
  (reused, not re-run — deliberately, per anti-overfit §6). This audit's own
  compute was inventory/spec/report writing only.
- **Pine-source gap:** the V3.6 input panel Mike cycled in TradingView is not
  in the local tree, so TV-side options that never made it into the canonical
  implementation cannot be audited as options. If Mike's live TV script
  contains inputs with no counterpart here, that is a parity gap to
  investigate as an engineering item — not as a strategy option.
- **2022 validation used EOD liquidation** (not full Pine exit semantics) and
  a 32-symbol subset; directionally adequate for the rule's bear-market check,
  not a precision instrument.

## 5. Confirmations

- No existing file was modified. New files only: `tv_option_audit/`
  (`audit_spec.md`, `phase1_inventory.md`, `audit_report.md`).
- Nothing was implemented. No V3.6 logic, parameter, threshold, or default
  was changed. `pine_live/` untouched.
- Even a winning option would have become a change-control candidate only;
  there were no winners.
- Prior standing verdicts unchanged: V3.6 frozen; entry research closed
  ("~0.20R is the ceiling of this architecture"); the paper phase continues
  under the dual ledger and production gate.
