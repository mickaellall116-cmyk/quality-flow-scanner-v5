# Lone-wolf CANONICAL-PROTOCOL study (2026-09-25)

First candidate run through Mike's 12-step canonical protocol. Pre-registered
in HYPOTHESIS.md BEFORE any results were computed. No rule changes after.

**Main question:** does weak sector confirmation hurt stock setups across
nearby RS lookbacks and unseen periods?

## Pre-registration summary
- Two candidate formulations: **F_A** = sign-cut 20d (block if stockRS(20)>0
  and sectorRS(20)<=0), **F_B** = relative-cutoff 20d (block if stockRS(20)>0
  and sectorRS(20) < trailing-1y median, point-in-time).
- Baseline: canonical 4H Hybrid, same 237-trade population (admission hook).
- DEV = 2023-10-25 → 2024-12-31; VAL = 2025-01-01 → 2026-09-23.
- Formulation selected on DEV by predeclared rule; reported frozen on VAL.
- Costs 25/50/75/100bps on every cut.

## Step 4 — Dev/val selection (predeclared rule)
DEV (n≈108): F_A Δ +0.0242 (blocked exp +0.1585 < control +0.4203 ✓);
F_B Δ +0.0225 (blocked +0.1790 < control ✓). |ΔA−ΔB| = 0.0017 < 0.01 →
**tiebreak invoked**; F_A had the lower blocked expectancy → **F_A selected**.
Dev could not distinguish the formulations — per HYPOTHESIS, MAYBE at best
even if everything else passed.

Frozen F_A on VAL (n=121 control / 88 filtered): control +0.1998R,
filtered **+0.3435R, Δ = +0.1437R**. Validation delta LARGER than dev —
the predeclared gate (a) Δ > +0.05R passes.

## Step 5 — Rolling walk-forward (12mo train / 6mo test / roll 6mo)
| Window | Test period | Control | Filtered | Δ |
|---|---|---|---|---|
| T1 | 2024-10 → 2025-03 | +0.6867 (n=33) | +0.8915 | +0.2048 |
| T2 | 2025-04 → 2025-09 | +1.1668 (n=32) | +1.1966 | +0.0298 |
| T3 | 2025-10 → 2026-03 | −0.4477 (n=36) | −0.4515 | −0.0038 |
| T4 | 2026-04 → 2026-09 | +0.1229 (n=39) | +0.3131 | +0.1902 |
**Combined untouched test windows (n=140): Δ = +0.1629R.** Gate (b) passes.
Note T3 is flat/negative — the edge is not uniform across windows.

## Step 6 — Year and regime splits
Years (25bps): 2024 Δ +0.024 (n=59, dev); **2025 Δ +0.057** (n=68);
**2026 Δ +0.190** (n=53). Gate (c): both VAL years positive ✓.
2023 partial: no trades before Oct 25 — year absent by construction.
Regimes (SPY-based; no VIX in cache): bull+lowvol Δ +0.0815 (n=87);
bull+highvol Δ +0.0492 (n=83) — directionally present in both.
Weak-market: thin (n=10 / n=0) — not judged, honestly marked.

## Step 7 — Perturbation (predeclared family, reported not ranked)
Δ vs control @25bps:
- SIGN15 **+0.020** · SIGN20 **+0.108** · SIGN25 **−0.016** → 2 of 3 positive
- REL15 **−0.075** · REL20 **+0.097** · REL25 **−0.009** → 1 of 3 positive
Gate (d) required ≥2/3 in EACH family → **FAILS**. The relative-cutoff idea
does not generalize across lookbacks either (REL15 is clearly negative).
The 20-day lookback remains load-bearing for both formulations.

## Step 8 — Concentration
Blocked set (n=62, flagged ∩ control-taken): total +7.67R — i.e. blocked
trades were net mildly positive (+0.124R expectancy), below-average not losers.
Avoided losses: QQQ −7.71R, AMD −2.67R, ONDS −1.78R, NIO −1.39R, BBAI −1.29R.
Opportunity cost: XLF-blocked +9.77R and XLI-blocked +8.88R of winners left
on the table.
Gate (h) as coded (<50% top-1 share) was ambiguous under the sign convention
(blocked total is positive); the binding concentration evidence is LOSO
below: QQQ removal cuts Δ to +0.034 (from +0.108) — QQQ is load-bearing but
does not flip the edge. Reported honestly rather than hidden behind the gate.

## Step 9 — Bootstrap (B=10,000, seed 42, predeclared)
Primary (Δ filtered−control over resampled full population):
mean +0.1396, p5 −0.0042, p50 +0.1382, p95 +0.2857, **P(Δ>0) = 0.9442**.
Gate (f) required ≥0.95 → **FAILS by 0.006**. The 5th percentile sits
essentially at zero — there is real mass near no-effect. Positive expectancy
is typical (94%) but not at the predeclared confidence bar.
Secondary (blocked-vs-allowed gap): mean +0.256, P(gap>0) = 0.816.

## Step 10 — Leave-one-symbol-out (selected formulation, 25bps)
All 14 removals keep Δ > 0 → gate (e) passes. But: QQQ +0.034, BBAI +0.037,
ONDS +0.047 — three removals cut the edge by ~two-thirds. No single-name
collapse, but the edge leans on a few names.

## Step 11 — Economic effect (pooled sim, 25bps)
Δ expectancy **+0.108R** · Δ PF **+0.22** (1.43→1.65) · Δ max DD **−2.78pp**
(21.63%→18.86%) · trades removed 62, added 0 · opportunity cost (blocked
expectancy) **+0.124R** · return per unit risk 2.60 → **3.51**.
Cost stress on selected: +0.108 / +0.106 / +0.087 / **+0.086 @100bps** —
gate (g) passes; the edge does not wash out at 4× costs.
Note: the filter also reduces slot-cap skipping (57 → 26 cap-skips) since
fewer candidates compete for the 5 slots.

## Step 12 — Live paper status
F_A (sign-cut 20d) is already papered live via `v54_lonewolf_overlay.py`
(hourly cron). This study does NOT change the overlay. Selected formulation
(F_A) matches the overlay's formulation.

## Verdict: MAYBE
Gates: a✓ b✓ c✓ d✗ e✓ f✗(0.944 vs 0.95) g✓ h~(ambiguous, LOSO binding).
The dev selection was ambiguous (tiebreak invoked), the lookback is
load-bearing for both formulations (gate d fails — REL15 −0.075 kills the
"relative cutoff generalizes" hope), the bootstrap misses the predeclared
95% bar by 0.006, and T3's rolling window is flat.
Against that: validation Δ (+0.144) exceeds dev, both VAL years positive,
2026 flips positive, combined rolling windows +0.163, survives 100bps,
no single-symbol collapse, DD improves, return/risk improves.
This is a 20-day-window-specific effect that keeps surviving every
out-of-sample and cost test thrown at it — but it has not earned PASS.
The live paper overlay remains the arbiter; revisit at the ~50-signal
checkpoint (late Oct 2026).

## Files
- `HYPOTHESIS.md` — pre-registration (written before results)
- `run_protocol.py` — study script (imports `pine_backtest` unmodified)
- `protocol_results.json` — all cuts, bootstrap, LOSO, gates
- `README.md` — this file

Guardrails respected: research only. V5.4, Mode B, production alerts, grades,
exits, market gate, AI Observer, and the live overlay untouched.

---

## Mike's exact validation prompt — TEST 1 (run 2026-09-24/25)

Mike issued a fixed validation protocol that supersedes the HYPOTHESIS.md
gate battery for the final report. Rule fixed by fiat for the main test:
BLOCK when stock 20-bar RS vs SPY > 0 AND sector ETF 20-bar RS vs SPY <= 0.
Baseline = all 237 original V5.4 trades; variant = same 237 minus the 83
blocked (simple removal — no slot-cap simulation). Costs 25bps unless noted.
Script: `run_mike_validation.py` → `mike_validation_results.json`.
`pine_backtest` imported unmodified. Nothing frozen touched.

### First report
| set | n | expectancy | win% | PF | max DD | avg winner | avg loser | avg MFE | avg MAE |
|---|---|---|---|---|---|---|---|---|---|
| baseline | 237 | +0.2388R | 50.6 | 1.38 | 30.74R | +1.7065R | −1.2666R | 2.828R | 1.131R |
| retained | 154 | +0.3773R | 52.6 | 1.64 | 15.62R | +1.8355R | −1.2407R | 3.073R | 1.093R |
| blocked | 83 | −0.0183R | 47.0 | 0.97 | 19.70R | +1.4386R | −1.3097R | 2.374R | 1.202R |

Baseline expectancy reproduces the canonical +0.239R exactly. Blocked trades
are genuinely dead money (−0.018R, PF 0.97). Retained winners are bigger
(+1.84R vs +1.44R) and run further (MFE 3.07R vs 2.37R). DD in R is halved
(30.7R → 15.6R).

### Checks A–H
- **A (year):** 2024 Δ +0.120 (n=75), 2025 Δ +0.081 (n=102),
  2026 YTD Δ +0.205 (n=60). All positive. (2023: no trades — sample starts
  2023-10-25, "if sample permits" does not permit.)
- **B (lookback 15/20/25):** Δ +0.065 / +0.139 / +0.008 — all positive,
  20 bars the strongest. Directionally visible around 20, but 20 is
  load-bearing: 25 is a whisper (+0.008).
- **C (costs):** Δ +0.139 / +0.137 / +0.135 / +0.133 at 25/50/75/100bps.
  Rock solid.
- **D (leave-one-symbol-out):** min Δ +0.114 (remove ONDS), max +0.167
  (remove SOFI). No single removal destroys the result.
- **E (concentration):** of the improvement, top-1 symbol (QQQ) = 43%,
  top-3 = 86%, top-5 = 114% (over 100% because some names contribute
  negatively); by sector XLK = 69%. The effect is tech/XLK-concentrated —
  the honest weak spot.
- **F (dev/val):** dev (Oct23–Dec24) Δ +0.120, val (Jan25–Sep26) Δ +0.146.
  Rule fixed before validation; no validation tuning.
- **G (walk-forward, rolling 12mo obs / 6mo test / roll 6mo):** untouched
  test windows Δ +0.261 / +0.164 / +0.056 / +0.206; combined n=191,
  Δ +0.182. All four windows positive.
- **H (bootstrap, 10,000 resamples):** median Δ +0.138R, 5th −0.004R,
  95th +0.286R, P(Δ>0) = 94.42%. DD distribution: baseline median 35.7R /
  p95 58.7R vs retained median 21.7R / p95 38.7R — the filter cuts tail
  drawdown, not just mean expectancy.

### Verdict under Mike's rule
PASS iff positive across validation, costs, nearby lookbacks, symbol-removal.
All four hold: validation +0.146 ✓, all costs +0.13–0.14 ✓, lookbacks all
positive ✓, LOSO min +0.114 ✓. **Verdict: PASS.**

Honest caveats (for the comparison table's evidence-strength ranking):
1. The pre-registered HYPOTHESIS.md protocol had extra gates the rule didn't
   clear: DEV formulation selection was ambiguous (SIGN20 vs REL20 coin flip
   — Mike's prompt fixes the rule by fiat, so this is provenance, not a
   failure of this test's execution), and the bootstrap 94.42% missed the
   95% gate by 0.58 points.
2. L25 at +0.008 is directionally positive but razor-thin — the 20-bar
   window remains load-bearing.
3. Concentration: 43% of the improvement is QQQ alone; XLK is 69%.
4. The live paper overlay has classified 19 signals with only 1 sector-mapped
   and 0 blocked — live sample far too thin to confirm anything.

**STOP. No new research branch.** The live lone-wolf overlay remains the
arbiter; revisit at the ~50-signal checkpoint (late Oct 2026).

## Research backlog (ideas noticed — NOT tested, per Mike's instruction)
1. **Slot-cap efficiency mechanism.** In the sim version the filter cut
   slot-cap skips 57→26: blocking lone-wolves frees slots for later trades.
   Part of the "improvement" may be portfolio plumbing, not trade quality.
   Pre-register a study that separates the two.
2. **XLK-concentration / is it just QQQ timing?** 43% of improvement is QQQ,
   69% is XLK. Test a sector-neutral variant (within-sector rank) to check
   whether "sector RS" is the mechanism or a tech-momentum proxy.
3. **Regime interaction.** Largest delta is 2026 YTD (+0.205), a choppy year —
   lone-wolf breakouts may fail hardest in weak markets. Pre-register a
   regime-interaction test on NEW data only.
4. **MFE asymmetry.** Retained trades run further (MFE 3.07R vs 2.37R
   blocked). Whether blocked trades' lower MFE implies anything about
   partial-profit design is a separate, pre-registered question.
5. **Cutoff variants are new hypotheses.** The relative-cutoff variant
   reproduced the effect in the earlier protocol run, but Mike fixed the
   sign-cut rule — any variant is a NEW hypothesis requiring its own
   pre-registration and forward test.
