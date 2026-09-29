# TradingView Option Audit — AUDIT SPEC (pre-registered 2026-09-18)

FROZEN. This spec governs the audit; results do not amend it. Any deviation is a
protocol violation and must be documented as such, not silently edited.

## 0. Authority and boundaries

- Commissioned by Mike as a BOUNDED EXCEPTION to the V3.6 strategy freeze.
- The freeze itself stands: NOTHING from this audit gets implemented. Even a
  winning option becomes a change-control candidate only (documented failure
  mode + pre-registered test + out-of-sample validation). V3.6, `pine_live/`,
  and all frozen modules stay untouched.
- All work in the new read-only namespace `tv_option_audit/`. No existing
  research or strategy file may be modified.
- Scope: EXISTING TradingView options of the canonical V3.6 implementation
  only. Anything not present in the canonical implementation is new logic, not
  an "option", and is out of scope (new entry filters are closed).

## 1. Canonical implementation

`pine_backtest.py::pine_buy_signal` (documented as "Quality Flow System V3.6,
V3.3 engine, Hybrid entry mode, default inputs"). The V3.6 Pine Script source
with selectable TradingView inputs is NOT present in the local workspace (only
v1.1 and v1.7 reference scripts, which are older/different versions). The
inventory is therefore built against the canonical local implementation, and
every "option" is verified against that code — UI labels are not trusted.

## 2. Phase 1 — inventory (no testing)

Catalog every selectable element of the canonical signal logic and classify:
1. already canonical V3.6 logic
2. display-only
3. legacy/unused
4. previously tested and rejected
5. genuinely untested optional signal logic

Record exact defaults and the precise code path each changes.

## 3. Phase 2 — one-variable ablations

For every category-5 option ONLY:
- V3.6 baseline vs V3.6 + exactly one option. No combinations.
- No parameter searching. No changing thresholds after seeing results.
- Baseline is frozen V3.6 signal logic only (no ranking/sector-cap/risk-gate
  in the signal comparison; portfolio handling must be identical across
  variants so the comparison stays one-variable).
- Windows, in order: bull/research window (UX51 4H, 2024-09-16→2026-09-14) →
  2022 validation (4H, signals ≥2022-01-01) → any existing unseen validation
  window.
- Report per option: trade count, expectancy (R/trade), PF, max drawdown,
  win rate, return, trades added/removed vs baseline. Costs at 4bps and 25bps.

## 4. Pre-registered earn-its-place rule

An option advances ONLY if ALL hold:
- (a) it materially improves expectancy or risk-adjusted performance vs
      baseline on the research window;
- (b) it retains enough trades that the result is not a tiny-sample artifact
      (fewer than ~60 trades on the research window = insufficient evidence);
- (c) it does not collapse on 2022 (positive expectancy, no sign flip);
- (d) it does not depend on one or two giant outliers;
- (e) it remains directionally beneficial in the independent validation
      window.

REJECT if any hold:
- wins bull but loses (or goes to noise in) bear;
- amazing number on very few trades (insufficient evidence);
- merely reduces trade count (and thus drawdown) without genuine selection
  skill — fewer trades is not an improvement by itself.

## 5. Phase 3 — final-stack confirmation

Only options surviving Phase 2 get one final test: V3.6 + candidate option +
rs_top2 ranking + sector cap + 5% risk gate, versus the locked four-layer
stack. Tests whether the value is still incremental after portfolio layers.

## 6. Anti-overfit constraints

- Judge on expectancy and robustness, not win rate.
- No fourth candidate / no re-running with tweaked definitions after seeing
  validation. Failed options stay failed.
- Prior completed ablations on the same components count as evidence; they
  are not re-run to shop for better numbers.
