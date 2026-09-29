# ANALYSIS.md — Portfolio correlation / exposure study on Pine V3.6

Spec: EXPOSURE_SPEC.md (frozen before testing). Candidate: CANDIDATES_FROZEN.md
(frozen before 2022). V3.6 entries/exits byte-identical; sizing fixed 1%;
portfolio-level gates only. Fidelity: no-gate sim reproduces pb.simulate_portfolio
to the cent (both cost legs).

## Control reproduction

V0 (take-all) @4bps: 160 taken of 263 candidates, exp 0.239R/taken-trade,
PF 1.35, +35.30%, DD 35.17%. (The documented "+0.195R / 263 trades" averages
over all 263 candidates including 103 skipped by cap/risk; the portfolio took
160. Return and DD match the published baseline exactly.)

## Diagnostics (D1–D4, no rule changes)

**D1 — max-DD episode anatomy.** The 35.17% DD ran 2024-11-22 → 2025-06-13
(~7 months). Average concurrency during the window: **1.13**; max 5. At the DD
start only 2 positions were open — both CRYPTO, pairwise trailing corr 0.46.
The max drawdown was a **sequential grind of losers, not a crowded-portfolio
event**.

**D2 — concurrency share of DD.** Only **42.8%** of the peak→trough decline
occurred on bars with ≥3 concurrent positions. Concurrency histogram over the
DD window (1492 bars): 0:859, 1:146, 2:143, 3:153, 4:153, 5:38. The portfolio
spent most of the DD window with 0–2 positions open.

**D3 — same-bar cohorts.** 14 multi-trade cohorts (31 trades). Median
var(cohort total R)/sum(var_i) = **1.55**; mean within-cohort sign agreement
0.85. Clustered same-bar signals behave like **~1.5x one trade, not 2x+** —
correlated, but not a pure double-down.

**D4 — sector concentration** (160 taken trades): CRYPTO 68 trades / +20.8R
(26% of trades, biggest R contributor); AI_SOFTWARE 21 / +15.5R; SEMIS 26 /
+3.4R (churn, little profit); ETF 9 / +5.0R; FINTECH 9 / +2.9R;
SPACE 7 / −2.0R; HEALTHCARE 10 / −3.1R; CONSUMER 10 / −4.2R.
Crypto was also +22.5R on trades open during the DD window — the DD was driven
by non-crypto losers while crypto positions were making money.

**Diagnostic bottom line:** clustered/correlated positions are NOT what's
driving the 35% drawdown. The DD is the documented price of a 44.9%-win-rate
edge grinding through a 7-month loser sequence.

## Rule comparison @4bps (research window)

| Variant | Trades | Exp R | PF | Ret % | DD % | Calmar | Gate skip |
|---|---|---:|---:|---:|---:|---:|---:|
| V0 control | 160 | 0.239 | 1.35 | 35.30 | 35.17 | 1.004 | 0 |
| E1 sector2 | 143 | 0.299 | 1.44 | 42.29 | 29.68 | 1.425 | 20 |
| E2 mega3 | 162 | 0.212 | 1.31 | 30.32 | 33.84 | 0.896 | 3 |
| E3 corr70 | 146 | 0.281 | 1.41 | 40.29 | 31.30 | 1.287 | 32 |
| E4 cap3 | 111 | 0.437 | 1.65 | 50.79 | 32.51 | 1.562 | 0 |

- **E1 sector2** (max 2 concurrent per sector): DD −5.49pp, exp +0.06R, Calmar
  1.43. Passes all three pre-registered gates.
- E2 mega3: gate bound 3 times all window — MEGA_AI rarely has 3 concurrent.
  Rejected (DD cut 1.33pp).
- E3 corr70: 32 gate skips, helped expectancy (+0.04R) but DD cut only 3.87pp.
  Rejected.
- E4 cap3: best expectancy (+0.437R) and return (+50.8%) — pure selectivity —
  but DD cut only 2.66pp, because the baseline DD wasn't a crowding event.
  Rejected per the pre-registered bar.

What E1 actually skipped (23 trades in control but not E1): mean +0.20R,
**median −0.76R**, sum +4.6R; sectors CRYPTO 15, SEMIS 4, AI_SOFTWARE 2,
SPACE 1, FINTECH 1. The gate dodged a cluster of correlated crypto/semis
losers (median −0.76R) plus a few winners — consistent with D3's sign
agreement. The edge is real selectivity against loser clusters, not just
fewer trades.

## 2022 validation (frozen C1 only)

| Variant | Trades | Exp R | PF | Ret % | DD % |
|---|---|---:|---:|---:|---:|
| V0 control | 36 | 0.376 | 1.46 | 11.21 | 20.42 |
| C1 sector2 | 36 | 0.376 | 1.46 | 11.21 | 20.42 |

The gate **never engaged** in 2022 (gate_skip=0) — no two same-sector positions
were ever concurrently open. 2022 verdict: **no harm, not the skill** (same
pattern as the ranking study's 2022). Adoption bar met: exp ≥ control−0.05R ✓,
DD ≤ control+3pp ✓.

## Stacked secondary (rs_top2 ranking first, then E1 gate — reported, not a candidate)

| Variant @4bps | Trades | Exp R | PF | Ret % | DD % | Calmar |
|---|---|---:|---:|---:|---:|---:|
| rs_top2 alone | 154 | 0.324 | 1.48 | 52.78 | 32.65 | 1.617 |
| rs_top2 + E1 | 143 | 0.337 | 1.49 | 52.25 | 31.63 | 1.652 |

(The stacked sim's ranking-only leg reproduces the ranking study's rs_top2
exactly: 154 / +0.324R / 52.78% / 32.65%. Production stacking order: at a
contested bar, rs_top2 selects top min(2, free slots) first; the sector2 gate
then applies to the selected candidates in rank order. The two rules are
orthogonal: ranking picks *which* slots to fill, the gate caps *sector*
concentration.)

## Verdict: ADOPT C1 (E1_sector2)

**Adopted rule:** at each entry event (after same-timestamp exits are
processed), skip the candidate if ≥2 positions in its sector — per the
EXPOSURE_SPEC.md map — are already open. All other portfolio rules unchanged
(max 5 positions, 5% portfolio risk, 1% risk/trade for this study).

**Caveats (stated plainly):**
1. The baseline's max DD was a low-concurrency grind, so E1 does not fix "the"
   drawdown mechanism — it trims correlated loser clusters (mostly crypto).
2. At 25bps the DD cut shrinks to 1.7pp (35.46% vs 37.16%) — cost-sensitive.
3. 2022 confirms no harm, not the skill (gate never engaged).
4. Research window only: E1's improvement could still be partly selective luck;
   the next clustered bear-market sample is the real test.

**Rejected:** E2 (never binds), E3 (helps expectancy, insufficient DD cut),
E4 (best expectancy, insufficient DD cut — selectivity without DD benefit).
Exposure research is now **closed**; no new rules invented.

## Files
- EXPOSURE_SPEC.md (frozen pre-registration: sector map, 4 rules, bar)
- CANDIDATES_FROZEN.md (frozen before 2022; only C1 passed)
- ANALYSIS.md (this file)
- exposure_results.json (research-window variants + diagnostics)
- exposure_stacked.json (rs_top2+E1 stacking secondary)
- exposure_validate.json (2022: V0 vs C1)
- pine_exposure.py, pine_exposure_stacked.py, pine_exposure_validate.py

Nothing else touched: no existing files modified, no GitHub, no forward test,
no live signals, no money. V5.4 untouched.
