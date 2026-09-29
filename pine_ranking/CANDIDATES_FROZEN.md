# CANDIDATES_FROZEN.md — Ranking study

**Frozen 2026-09-18, BEFORE touching 2022. No further selection after seeing 2022.**

## Research-window qualifiers (@4bps, pre-registered gates: exp ≥ +0.225R,
## trades ≥ 100, DD ≤ 38.2%)

| Variant | Trades | Exp R | PF | Ret% | DD% | Fill% | Verdict on gates |
|---|---|---|---|---|---|---|---|
| V0 control (take-all) | 263 | +0.195 | 1.27 | +35.3 | 35.2 | 100 | baseline |
| rs_top1 | 153 | +0.320 | 1.47 | +51.3 | 32.6 | 58.2 | PASS |
| rs_top2 | 154 | +0.324 | 1.48 | +52.8 | 32.7 | 58.6 | PASS |
| rs_top3 | 154 | +0.324 | 1.48 | +52.8 | 32.7 | 58.6 | PASS (= rs_top2, see note) |
| vol_top1 | 155 | +0.228 | 1.32 | +31.5 | 32.9 | 58.9 | PASS (margin 0.003R) |
| vol_top2 | 157 | +0.220 | 1.31 | +30.5 | 33.8 | 59.7 | FAIL (< +0.225R) |
| composite_top1/2 | 156/157 | +0.212/+0.216 | 1.29/1.30 | — | 34.7/34.9 | — | FAIL |

Note: rs_top2 ≡ rs_top3 on this data (contested bars never have >2 free slots
with 3 candidates, so the N=2/N=3 caps bind identically). rs_top1 vs rs_top2
differ by exactly 1 trade (0.004R).

## Frozen candidates (max 2)

- **C1 = rs_top2**: rank contenders at contested bars by 20-bar return minus
  SPY return (daily closes, last-bar-≤-timestamp); take top min(2, free slots).
- **C2 = vol_top1**: rank contenders by signal-bar Volume / SMA20(Volume);
  take top min(1, free slots).

Selection rationale: rs_top1 and rs_top2 are near-duplicates (Δ1 trade);
freezing both would waste the second slot. C2 is the only other gate-passer
and carries independent information (volume, not relative strength).

## Post-hoc diagnostics (NOT candidates, interpretation only)
- takeall-taken subset (160 trades the control portfolio actually filled):
  +0.239R — i.e. ~+0.04R of every variant's edge vs the published +0.195R is
  pure selectivity (fewer trades), present in all variants.
- Placebos @4bps: random_top2 +0.245R, vol_bottom1 +0.247R, rs_bottom1 +0.208R.
- Decomposition: selectivity ≈ +0.24R for any ~155-trade subset; RS ranking
  skill ≈ +0.08R on top (rs_top2 +0.324R vs placebo cluster ~+0.24R).
- Caveat recorded BEFORE 2022: vol_top1 shows no ranking skill beyond
  selectivity in the diagnostic (vol_bottom1 ≈ random). It passed the
  pre-registered gate, so it validates or dies in 2022 on its merits.

## 2022 adoption bar (pre-registered)
expectancy ≥ (2022 control − 0.05R), trades ≥ 20, DD not materially worse
than 2022 control. Candidates validated unchanged; no refit on 2022.
