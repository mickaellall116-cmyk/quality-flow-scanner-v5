# ANALYSIS.md — Cross-sectional ranking study on Pine V3.6

Spec: `RANKING_SPEC.md` (frozen before testing; Amendment A: tie-break by
candidate order, documented). Candidates: `CANDIDATES_FROZEN.md` (frozen
before touching 2022). V3.6 entries/exits byte-identical throughout.

## 1. Step 0 — clustering (is ranking even relevant?)

- 263 candidate V3.6 trades, 2024-09-16 → 2026-09-14, UX51 4H.
- Take-all control portfolio skipped **79 entries** on the 5-position cap.
- **82 contested timestamps** (candidates > free slots). Histogram of
  candidates per contested bar: {1: 49, 2: 24, 3: 9}.
  - 49×: a lone signal arrived with zero free slots → dropped in every variant
    (no choice for ranking to make).
  - 33×: 2–3 signals genuinely competed → ranking acts.
- Not moot. Ranking gets to act ~33 times in 2 years.

## 2. Research-window results (@4bps; 25bps in JSON)

| Variant | Trades | Fill% | Win% | Exp R | PF | Ret% | DD% | TP1% | Hold | AvgW/L R |
|---|---|---|---|---|---|---|---|---|---|---|
| V0 control (take-all) | 263 | 100 | 44.9 | +0.195 | 1.27 | +35.3 | 35.2 | 47.5 | 18.1 | +2.02/−1.29 |
| rs_top1 | 153 | 58.2 | 45.8 | **+0.320** | 1.47 | +51.3 | 32.6 | 49.0 | 19.4 | +2.18/−1.25 |
| rs_top2 | 154 | 58.6 | 46.1 | **+0.324** | 1.48 | +52.8 | 32.7 | 49.4 | 19.4 | +2.17/−1.25 |
| vol_top1 | 155 | 58.9 | 45.2 | +0.228 | 1.32 | +31.5 | 32.9 | 48.4 | 18.9 | +2.08/−1.30 |
| vol_top2 | 157 | 59.7 | 45.2 | +0.220 | 1.31 | +30.5 | 33.8 | 48.4 | 18.8 | — |
| composite_top1/2 | 156/157 | — | 44.9/45.2 | +0.212/+0.216 | 1.29/1.30 | — | 34.7/34.9 | — | — | — |

- rs_top2 ≡ rs_top3 on this data (contested bars never have >2 free slots
  with 3 candidates, so the N=2/N=3 caps bind identically).
- At 25bps: rs_top2 +0.260R vs control +0.115R — edge holds under costs.
  vol_top1 fades to +0.154R at 25bps.

## 3. Post-hoc diagnostics (interpretation only, not candidates)

- takeall-taken subset (160 trades the control portfolio actually filled):
  **+0.239R** — ~+0.04R of every variant's edge vs the published +0.195R is
  pure selectivity (fewer trades), present in all variants equally.
- Placebos: random_top2 +0.245R, vol_bottom1 +0.247R, rs_bottom1 +0.208R.
- Decomposition: any ~155-trade subset ≈ +0.21–0.25R (selectivity);
  **RS ordering skill ≈ +0.08R on top** (rs_top2 +0.324R vs placebo cluster).
  rs_bottom1 < takeall-taken confirms the ordering matters in the right
  direction. vol ordering shows no skill beyond selectivity.
- Overlap: rs_top2's taken set shares 141/154 with takeall-taken; it swaps
  19 out / 13 in — a small, decisive reordering.

## 4. 2022 validation (32 symbols, signals ≥ 2022-01-01, EOD liquidation)

| Variant | Trades | Exp R | PF | DD% |
|---|---|---|---|---|
| V0 control (taken) | 37 | +0.376 | 1.47 | 20.4 |
| V0 control (all 39 candidates) | 39 | +0.287 | 1.35 | — (= prior studies, pipeline sane) |
| C1 rs_top2 | 37 | +0.376 | 1.47 | 20.4 |
| C2 vol_top1 | 37 | +0.376 | 1.47 | 20.4 |

**2022 was vacuous for ranking skill:** only 2 contested timestamps, both a
lone signal with zero free slots (dropped identically by every scheme). C1/C2
took exactly the same 37 trades as control. The adoption bar
(exp ≥ control−0.05R = +0.326R, ≥20 trades, DD ok) is met on paper, but 2022
**confirmed no harm rather than confirming the skill** — bear-market signals
didn't cluster, so ranking never engaged.

## 5. Verdict

- **C1 (rs_top2): ADOPT as the tie-break rule**, with a stated caveat (below).
  Passed every pre-registered bar in both windows; 2022-neutral (not
  2022-negative, unlike every rejected idea tonight). The failure mode is
  narrow and importantly different from the RS-filter failure: ranking never
  deletes a lone signal — the counter-trend winners the RS filter destroyed in
  2022 are always taken. It only reorders genuine ties for scarce slots.
- **C2 (vol_top1): REJECT.** No demonstrated skill beyond selectivity, marginal
  gate pass (+0.228 vs +0.225), fades at 25bps.
- Ranking research: question answered; no new schemes.

**Caveat (stated plainly):** the 2022 validation could not test ranking skill
— only 2 no-choice contested bars in the bear sample. Adoption rests on the
research-window mechanism (+0.08R ordering skill, placebo-controlled, 154
trades, better drawdown, holds at 25bps). Re-verify against the next
bear-market sample that actually clusters.

## 6. The adopted rule (exact)

At any 4H bar where valid V3.6 entry signals outnumber free position slots
(max 5 positions, after processing exits at that bar, same 5% portfolio-risk
cap as control): rank the contending signals by **(symbol's 20-bar return
minus SPY's return over the same calendar span, daily closes,
last-bar-≤-timestamp, point-in-time)** and take the **top min(2, free slots)**
in that order. Uncontested bars: take all signals, unchanged. Lone signals
are never deleted by ranking. Entries, exits, sizing: unchanged V3.6.

## Files
- `RANKING_SPEC.md` — frozen pre-test spec (+ Amendment A)
- `CANDIDATES_FROZEN.md` — frozen candidates + post-hoc diagnostics note
- `ranking_results.json` — research-window results
- `ranking_validate.json` — 2022 validation
- `ranking_diagnostics.json` — post-hoc placebos
- `pine_ranking.py`, `pine_ranking_validate.py`, `pine_ranking_diagnostics.py`
