# CANDIDATES_FROZEN.md — frozen BEFORE 2022 validation (2026-09-18)

Research-window results @4bps (control: 263 trades, +0.195R, PF 1.27, DD 35.17%):

| Variant | Trades | Win% | Exp R | PF | Ret% | DD% | AvgWin R | AvgLos R | Stop% | TP1% | Hold | Trade reduction |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V0 control | 263 | 44.9 | +0.195 | 1.27 | +35.30 | 35.17 | +2.02 | −1.29 | 93.9 | 47.5 | 18.1 | — |
| H1_rs | 216 | 47.2 | +0.294 | 1.43 | +41.54 | 33.15 | +2.08 | −1.30 | 95.8 | 49.5 | 18.6 | −17.9% |
| H2_contraction | 117 | 47.9 | +0.213 | 1.28 | +20.18 | 30.83 | +2.04 | −1.47 | 94.0 | 48.7 | 19.3 | −55.5% |
| H3_tightbase | 27 | 51.9 | +1.517 | 3.83 | +46.98 | 9.63 | +3.96 | −1.11 | 88.9 | 55.6 | 24.8 | −89.7% |

Freeze decisions (mechanical, per SIGNAL_QUALITY_SPEC.md):

- **H1_rs → FROZEN as C1.** (a) +0.294R ≥ +0.225R ✓; (b) DD 33.15% ≤ 40% and
  better than control ✓; (c) 216 trades ≥ 60 ✓; (d) genuinely new information:
  relative strength vs SPY/QQQ/sector is not measured by any V3.6 component
  (ADX/EMA alignment/volume/hot guard/score/breakout) ✓.
  Exact definition: unchanged V3.6 signal AND sym_ret(20 4H bars) > SPY_ret AND
  > QQQ_ret AND (> sectorETF_ret where a sector ETF was mapped; 39/51 symbols
  mapped, 12 use SPY+QQQ only). Benchmark returns over the symbol's own
  prior-20-bar calendar span, daily closes, last-bar-≤-timestamp, no lookahead.
- **H2_contraction → NOT frozen.** +0.213R misses the +0.225R materiality gate
  (a). Directionally positive but does not clear the bar. No judgment override.
- **H3_tightbase → NOT frozen.** 27 trades fails the ≥60 stability floor (c).
  +1.517R on 27 trades is a textbook small-sample artifact; adopting it would
  be exactly the overfitting this study was designed to prevent.

Only C1 (H1_rs) proceeds to 2022 validation, alongside the unchanged control.
