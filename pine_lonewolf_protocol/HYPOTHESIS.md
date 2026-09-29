# HYPOTHESIS.md — PRE-REGISTERED (written BEFORE any results were computed)

Study: pine_lonewolf_protocol — lone-wolf sector-RS under the canonical 12-step protocol.
Date pre-registered: 2026-09-25. No rule changes after results.

## 1. Hypothesis
Stock setups that are strong on their own (positive 20-day RS vs SPY) but whose
sector is NOT participating (weak sector confirmation) are genuinely lower
quality. Skipping them (an admission filter) improves expectancy, profit factor,
and drawdown without concentrating the book.

Mechanism: a breakout is a bet that demand overwhelms supply. When the whole
sector is bidding (sector RS positive), the stock's move rides a real flow.
When the stock moves alone against a weak sector, the move is idiosyncratic —
more likely a head-fake, short squeeze, or fading news.

## 2. Exact rules (two candidate formulations, both predeclared)

- **F_A (sign-cut, 20d):** block a signal when stockRS(20d) > 0 AND
  sectorRS(20d) ≤ 0. RS = 20-trading-day return vs SPY, point-in-time at the
  signal bar date, P10 sector mapping
  (QQQ→XLK, SMCI→SOXX, PLTR→XLK, ANET→XLK, SOFI→XLF, RKLB→XLI, ONDS→XLK,
  DRAM→SOXX, SPCX→XLI, ASTX→XLK, BBAI→XLK, NIO→XLY, HOOD→XLF, AMD→SOXX).
- **F_B (relative-cutoff, 20d):** block when stockRS(20d) > 0 AND
  sectorRS(20d) < trailing-1y median of sectorRS(20d) at the signal date
  (point-in-time; median series shifted 1 day).

Perturbation family (predeclared, reported not ranked): sign-cut {15d, 20d,
25d} and relative-cutoff {15d, 20d, 25d} — same construction, lookback
substituted everywhere including the trailing median.

## 3. Baseline, universe, dates, costs
- Baseline: canonical 4H Hybrid, same 237-trade population (admission hook on
  the portfolio sim — same dates, same names).
- Date range: 2023-10-25 → 2026-09-23. DEV = 2023-10-25 → 2024-12-31.
  VAL = 2025-01-01 → 2026-09-23.
- Symbols: the 14-name watchlist (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS,
  DRAM, SPCX, ASTX, BBAI, NIO, HOOD, AMD).
- Costs: 25 / 50 / 75 / 100 bps, automatic on every cut.
- Exits: frozen Mode B, unchanged.

## 4. Formulation selection on DEV (predeclared rule)
Compute dev-period Δexpectancy (filtered taken − control taken, 25bps) for
F_A and F_B. Select the formulation with the larger dev Δ, PROVIDED:
(a) dev Δ > 0, and (b) dev blocked-trade expectancy < dev control-taken
expectancy (it must block worse-than-average trades).
Tiebreak: if |Δ_A − Δ_B| < 0.01R, prefer the formulation with the lower
blocked-trade expectancy; if still tied, default to F_A (the live-overlay
formulation). If neither satisfies (a)+(b): NO formulation is selected,
verdict = FAIL, and no validation comparison is run.
The selected formulation is then reported FROZEN on VAL with zero retuning.

## 5. Rolling walk-forward (predeclared anchors)
Train 12mo / test 6mo / roll 6mo:
- T1 train 2023-10-25→2024-09-30, test 2024-10-01→2025-03-31
- T2 train 2024-04-01→2025-03-31, test 2025-04-01→2025-09-30
- T3 train 2024-10-01→2025-09-30, test 2025-10-01→2026-03-31
- T4 train 2025-04-01→2026-03-31, test 2026-04-01→2026-09-23
Nothing is tuned in train windows (formulation frozen at step 4); train
windows are reported for context. The verdict-relevant number is the
COMBINED untouched test windows: Δexp(filtered − control) pooled over
T1–T4 test trades.

## 6. Year and regime splits (predeclared)
Years: 2023 (partial, Oct–Dec), 2024, 2025, 2026 — taken-trade expectancy,
filtered vs control, 25bps.
Regimes at the signal date (no VIX data available in cache — SPY-based only,
predeclared): market trend = SPY above/below its 200-day SMA; market vol =
SPY 20d realized vol above/below its trailing-1y median (point-in-time).
Report the 2×2 (bull/weak × high-vol/low-vol); buckets with control-taken
n < 15 are marked thin, not judged.

## 7. Cost stress — automatic
Every cut reports 25/50/75/100bps.

## 8. Concentration (predeclared)
For the selected formulation: per-symbol, per-sector (via the mapping), and
per-year totals of blocked-trade R (sum). Report the share of the total
improvement (sum of blocked R, sign-flipped) attributable to the best 1, 3,
and 5 symbols / sectors / years.

## 9. Bootstrap (predeclared)
B = 10,000 resamples, seed 42.
Primary: resample the full 237-trade population WITH replacement; apply the
selected formulation's deterministic block flags; compute
Δ = E[filtered taken] − E[control taken] at 25bps. Report mean, 5th/50th/95th
percentiles, and P(Δ > 0).
Secondary: blocked-vs-allowed gap — resample taken and blocked sets
separately, compute E[taken] − E[blocked]; same percentiles.
This answers: is the observed Δ typical of the distribution or a lucky tail?

## 10. Leave-one-symbol-out (predeclared)
14 reruns, each dropping one symbol from the population: rerun control and
the SELECTED formulation (full portfolio sim, 25bps). Report Δexp per
removal. Red flag: any single removal flipping pooled Δ ≤ 0.

## 11. Economic effect (predeclared)
On pooled and on VAL: Δ expectancy, Δ PF, Δ max DD, trades removed vs added
(a filter only removes: report blocked count and any cap-interaction
difference), opportunity cost = blocked-trade expectancy, return per unit of
risk = total return % / max DD %.

## 12. Live paper status
The F_A (sign-cut 20d) formulation is already papered live via
v54_lonewolf_overlay.py (hourly cron). This study does NOT change the overlay
regardless of outcome. If the selected formulation differs from F_A, the
report will say so explicitly and recommend only a paper-sidecar change,
never a production change.

## PASS / MAYBE / FAIL (predeclared gates)
PASS requires ALL of:
  (a) selected formulation VAL Δexp > +0.05R (25bps);
  (b) combined rolling-test-window Δexp > 0;
  (c) VAL Δexp > 0 in BOTH 2025 and 2026;
  (d) perturbation: ≥2 of 3 sign-cut lookbacks {15,20,25} directionally
      positive on the pooled sample AND ≥2 of 3 relative-cut lookbacks
      directionally positive on the pooled sample;
  (e) no single-symbol removal flips pooled Δ ≤ 0;
  (f) bootstrap P(Δ > 0) ≥ 0.95;
  (g) Δ > 0 at 100bps on the pooled sample;
  (h) top-1 symbol contributes < 50% of total improvement.
MAYBE: (a)–(c) hold but any of (d)–(h) fails, or dev selection was ambiguous
(tiebreak invoked).
FAIL: (a) fails, or the effect exists only in one exact configuration.

The standard: survive different years, nearby parameters, higher costs,
symbol removal, and untouched forward data — or kill it.
