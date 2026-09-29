# Phase 1 — TradingView Option Inventory (no testing)

Date: 2026-09-18. Status: complete.

## 0. Source limitation (material)

The V3.6 TradingView Pine Script source — the script whose input panel Mike
manually cycled — is **not present in the local workspace**. The only `.pine`
files present are `pine_v11/v1_1_reference.pine` and
`pine_v17/v1_7_reference.pine` (older/different script versions with different
option sets: auto hybrid mode, early entry, adaptive 200 EMA, smart exits,
CMF/MFI exits, per-asset-class cooldowns and max entries).

The canonical V3.6 implementation used for every validated number is
`pine_backtest.py::pine_buy_signal` ("Quality Flow System V3.6, V3.3 engine,
Hybrid entry mode, default inputs"). This inventory is therefore built against
that code, per the brief's rule: verify against the implementation, do not
trust the UI label. Any TradingView-only input with no counterpart in the
canonical implementation is **not an auditable option** — testing it would be
inventing new entry logic, which is out of scope (new entry filters are
closed).

## 1. Canonical V3.6 signal components (all defaults frozen)

From `pine_backtest.py` (constants: EMA 9/21/55/200, ATR 14, ADX 14,
VOL_L 20, BREAKOUT_BARS 10, TP_ATR 2.0, SL_ATR 1.5, TRAIL_ATR 2.5,
HOT_ATR 1.5):

| # | Component | Code path (`pine_buy_signal`) | Default | Role |
|---|-----------|-------------------------------|---------|------|
| 1 | `volume_ok` | `Volume > SMA(Volume,20)` | required ON | volume gate |
| 2 | `hot_guard` (`safe`) | `hot = close > EMA9 + ATR×1.5`; `safe = not hot` | required ON | buy-zone / extension filter |
| 3 | `trend_bull` | `EMA21 > EMA55 and close > EMA200` | required ON (in `breakout_buy`) | EMA confirmation |
| 4 | `strong_trend` | `ADX(14) > 20 and atr_ratio > 0.85`, where `atr_ratio = ATR14 / SMA50(ATR14)` | required ON (in `breakout_buy`) | market-regime gate |
| 5 | `score_gate` | `score=(EMA9>EMA21)+(EMA21>EMA55)+(close>EMA200)+(ADX>25)+(atr_ratio>1.0)`; `confirmed` needs score≥4, `ready_buy` needs score≥3 | required ON | composite confirmation |
| 6 | `breakout` | `close > max(High, prior 10 bars)` | required ON (in `breakout_buy`) | structural trigger |
| 7 | `ready_prev` | prior bar: `close<EMA21 and close>EMA55 and EMA21>EMA55 and atr_ratio>0.85` | required ON (in `ready_buy`) | pullback setup |
| 8 | entry modes | `confirmed = close>EMA21 & EMA21>EMA55 & close>EMA200 & score≥4 & volume_ok & safe`; `breakout_buy = trend_bull & strong_trend & breakout & volume_ok & safe`; `ready_buy = ready_prev & close>EMA21 & score≥3 & volume_ok & safe`; signal = `confirmed OR breakout_buy OR ready_buy` (Hybrid) | all three ON | entry-mode selector |

## 2. Classification of every brief-named option

**Conservative / Hybrid / Aggressive (entry modes)** → category 4
(previously tested). In canonical code the modes are
`confirmed`/`breakout_buy`/`ready_buy`; "Hybrid" = OR of all three (the
frozen default). There is NO Conservative or Aggressive selector in the
canonical implementation. Closest mapping: Conservative ≈ `confirmed_only`.
The 2026-09-18 entry ablation tested every mode isolation/removal (V8–V13):
`confirmed_only` → **0 signals in 2y × 51 symbols**; `ready_only` → 0
signals; `breakout_only` ≡ baseline (100% of baseline signals are
`breakout_buy`); `no_confirmed` / `no_ready_mode` ≡ baseline (no-ops);
`no_breakout_mode` → 0 signals. A Conservative mode, as literally defined,
produces no trades at all. An "Aggressive" mode has no canonical definition —
any definition would be new logic. Implication for Mike's TradingView memory:
the materially different backtests he saw when cycling modes cannot be
reproduced from V3.6 options; they came from a different script version's
inputs (v1.7 has "Use Auto Hybrid Mode" / "Use Early Entry") or from
chart/window selection — the artifact hypothesis this audit was designed to
check.

**FVG (fair value gaps)** → not present in canonical V3.6. Not an option;
would be new entry logic. Out of scope. (No category — does not exist.)

**BOS/CHOCH (break of structure / change of character)** → not present as a
named concept. The canonical structural trigger is `breakout` (10-bar high
break), category 4: tested (V6 removal → Δ−0.056R, avg winner 2.02→1.27R) —
ADDITIVE, keeper.

**Liquidity sweep** → not present in canonical V3.6. Not an option. Out of
scope. (The v5.3 scanner's `mode_setup` string mentions "SWEEP OFF" as a
display label only — no logic behind it.)

**MTF alignment** → not present in canonical V3.6. Not an option. Out of
scope.

**EMA confirmations** → `trend_bull` + the EMA terms inside `score_gate`,
category 4: tested (V3 removal → Δ−0.113R, avg winner collapses 2.02→1.39R,
TP1 rate 47.5→29%) — strongest ADDITIVE keeper.

**Volume / RVOL gates** → `volume_ok`, category 4: tested (V1 removal →
+0.036R in bull window) then **rejected** — the relaxed variant collapsed on
2022 (+0.007R, PF 1.01). Bear-market insurance; kept in baseline.

**Buy-zone requirements** → `hot_guard`/`safe`, category 4: tested (V2
removal → +0.123R in bull window) then **rejected** — collapsed on 2022 as
part of candidate C1. Bear-market insurance; kept in baseline.

**Market-regime gates** → `strong_trend` (ADX>20 + ATR-ratio), category 4:
tested (V4 removal → Δ−0.050R) — ADDITIVE, keeper.

**v1.7-only options** (auto hybrid mode, early entry, adaptive 200 EMA, smart
exits, CMF/MFI exits, per-class cooldowns, max entries per asset class,
ATR-baseline ratio): belong to an older/different script, not V3.6. Not
auditable as V3.6 options. (Exits were separately frozen by the exit-ablation
study; cooldowns/max-entries are portfolio construction, not signal options.)

## 3. Category tallies

- **Category 1 — already canonical V3.6 logic:** components 1–8 above, as
  configured (all ON, Hybrid OR).
- **Category 2 — display-only:** none in the canonical research
  implementation (pure signal/trade logic; no plotting toggles affect it).
- **Category 3 — legacy/unused:** `ready_prev` (removal Δ=0.000 — never
  binds; redundant), `confirmed` mode and `ready_buy` mode (zero signals in
  2y × 51 symbols — dead code on this data).
- **Category 4 — previously tested and rejected (or confirmed as keepers):**
  `volume_ok` removal, `hot_guard` removal (both rejected via 2022
  validation), `score_gate` removal (rejected — C2 failed outright),
  `trend_bull` / `strong_trend` / `breakout` removals (tested; removal
  worsened → keepers), all mode isolations/removals V8–V13 (tested; zero or
  no-op).
- **Category 5 — genuinely untested optional signal logic: ZERO.**

## 4. Phase 1 finding

There is nothing left to ablate. Every selectable element of the canonical
V3.6 signal was already subjected to one-variable removal/isolation testing
on 2026-09-18 (`pine_entry_ablation/`, spec pre-registered, candidates frozen
before 2022 validation). The brief-named options that sound untested
(FVG, BOS/CHOCH, liquidity sweep, MTF alignment) do not exist in the
canonical implementation — they are not deferred options, they are absent
features, and testing them would violate the closed door on new entry
filters. Per the brief, this zero-category-5 result is itself a finding, and
it strengthens the freeze.
