# Laggard-Veto Risk-Control Test — Report

**Date:** 2026-09-25
**Pre-registration:** `selection_edge/laggard_veto_prereg.md` (frozen 2026-09-24, before execution; rule not modified after results)
**Authorized by:** Mike — Lane 2 narrowed to this single test (2026-09-24 directive)
**Verdict: FAIL** — the veto does not qualify as a risk-control candidate.

Research only. Nothing frozen was modified: no changes to V5.4 entries, exits,
grades, market gate, AI Observer, ranking, or alerts.

---

## 1. Frozen rule (as pre-registered, no tuning)

Veto (exclude) any v54 candidate signal where, at signal time, the stock ranks
in the **bottom quartile of RS3 or RS6** (union), where:

- RS3 = 63-day total return minus SPY total return, strict point-in-time
- RS6 = 126-day total return minus SPY total return, strict point-in-time
- Quartiles cross-sectional across the 123-name working universe, ranked with
  only data available at the signal bar

Veto if bottom-quartile on EITHER factor. Candidates unrankable on both
factors (insufficient history) pass through unvetoed — none occurred in
practice (all 3,963 candidates rankable on at least one factor).

## 2. Method

- **Population:** 131-symbol PIT universe minus the 8 in-universe old-14 names
  (AMD, ANET, DRAM, NIO, PLTR, QQQ, SMCI, SPCX) hard-masked → 123-name working
  set, exactly as in the selection study. 4,127 regenerated v54 candidates →
  3,963 working candidates.
- **Veto construction:** byte-identical to
  `selection_edge/phase2_strength/phase2_strength.py` (strict-PIT endpoint via
  14h backoff, j≥W history requirement, average-rank cross-sectional quartile,
  n≥8). Verified: RS3 buckets agree 353/353 and RS6 buckets 352/352 with the
  selection study's recorded per-trade factors. Zero block-condition violations.
- **Machinery:** worker (d)'s UNMODIFIED `build_v5` (exact Mode B exits,
  strict PIT features, realistic gap-through-stop in research, $75k book,
  1% risk, max 6 positions, ~5% heat, slot competition with production
  `rs_top2` ranking), run via the same monkey-patch pattern as
  `canonical_baseline/lonewolf_rerun.py`. The veto is applied at the
  **candidate stage**; the walk re-runs on the filtered set.
- **Internal comparison:** masked baseline (no veto) vs veto arm on the
  identical 3,963-candidate population. Primary cost: 50 bps round-trip,
  leg-based.
- **Veto fired on 430 / 3,963 candidates (10.85%)**: 132 bottom-quartile on
  RS3, 324 on RS6, 26 on both. By signal year: 2024 11.4%, 2025 12.1%,
  2026 8.6%.

## 3. Headline (@ 50 bps round-trip)

| Metric | Baseline (no veto) | Veto arm | Delta |
|---|---|---|---|
| Trades | 307 | 224 | −83 |
| Expectancy (R/trade) | −0.1186 | −0.2388 | **−0.1201** |
| Total R | −36.42 | −53.48 | −17.06 |
| Win rate | 37.1% | 31.2% | −5.9pp |
| Profit factor | 0.84 | 0.70 | −0.14 |
| **Max drawdown** | **−51.88%** (−$39,769) | **−70.10%** (−$52,215) | **−18.2pp (35% worse)** |
| Total portfolio return | −36.49% | −53.17% | −16.7pp |
| Median trade | −1.11R | −1.14R | — |
| Avg winner / loser | +1.69R / −1.19R | +1.81R / −1.17R | — |
| Max losing streak | 12 | 14 | +2 |

Note: the masked baseline (−0.1186R, −51.88% DD) is worse than the canonical
131-name baseline (−0.0013R, −39.8% DD) because the 8 masked names include
strong contributors (QQQ, SMCI, PLTR). This is expected — the comparison that
matters is baseline-vs-veto on the identical masked population, not vs the
canonical book.

## 4. Pre-registered decision rule → FAIL

PASS required ALL of:

1. **Max drawdown reduced by ≥25% relative:** veto DD is 35.1% *worse*
   (−51.88% → −70.10%). **FAIL.**
2. **Pooled expectancy not worse than baseline by more than 0.05R:**
   delta −0.1201R. **FAIL.**
3. **Drawdown improvement also present in the validation window alone:**
   val-only replay (signal ≥ 2025-01-01, fresh $75k): −45.09% → −34.16%
   (24.2% relative reduction), expectancy −0.0355R → +0.0654R. **PASS** —
   but see §7 for the cross-check that weakens it.

**Verdict: FAIL.** Per the pre-registration, this hardens the conclusion that
V5.4's risk profile is what it is; improvement must come from exits, entries,
or a different system — not from this veto. The veto does NOT qualify for a
forward paper overlay.

## 5. Secondary battery

### Cost sensitivity (expectancy, R/trade)

| Cost | Baseline | Veto | Delta |
|---|---|---|---|
| 25 bps | −0.0069 | −0.1203 | −0.1134 |
| 50 bps | −0.1186 | −0.2388 | −0.1201 |
| 75 bps | −0.2304 | −0.3572 | −0.1268 |
| 100 bps | −0.3421 | −0.4757 | −0.1336 |

The veto is worse at every cost level; the damage widens slightly with cost.

### Year splits (exit year, @50bps)

| Year | Baseline n / E | Veto n / E | Delta E |
|---|---|---|---|
| 2024 | 111 / −0.2043 | 106 / −0.3742 | −0.1699 |
| 2025 | 116 / −0.1825 | 67 / −0.3992 | −0.2167 |
| 2026 | 80 / +0.0928 | 51 / +0.2534 | +0.1606 |

Veto worse in 2024 and 2025; better expectancy in 2026 but on fewer trades
(51 vs 80), so 2026 total R still falls.

### Dev / val splits (signal date, @50bps)

| Window | Baseline n / E | Veto n / E | Delta E |
|---|---|---|---|
| Dev (Oct 2023–Dec 2024) | 116 / −0.1433 | 109 / −0.3658 | −0.2225 |
| Val (Jan 2025–Sep 2026) | 191 / −0.1037 | 115 / −0.1183 | −0.0146 |

Worse in both windows; the damage concentrates in dev.

### Concentration (top-k trades' share of total R, @50bps)

| Arm | Top-1 | Top-3 | Top-5 |
|---|---|---|---|
| Baseline (total −36.42R) | +8.96R (−24.6%) | +22.51R (−61.8%) | +33.61R (−92.3%) |
| Veto (total −53.48R) | +9.30R (−17.4%) | +23.30R (−43.6%) | +33.13R (−61.9%) |

Both books are net-negative while top trades are positive (hence negative
shares); the veto does not fix concentration — it deepens the hole around the
same fat tail.

### Bootstrap (5,000 reps, veto-minus-baseline expectancy delta)

- Mean delta: −0.118R; 95% CI [−0.417, +0.184]
- P(delta > 0) = 0.218; P(delta > −0.05) = 0.327

The veto's expectancy shortfall is not a sampling fluke at the trade level —
only ~22% of resamples favor the veto.

### Rolling walk-forward (12mo observe / 6mo test, signal date)

| Test window | n base/veto | ΔE (veto−base) | DD base | DD veto |
|---|---|---|---|---|
| 2025-03-26 → 2025-09-24 | 53 / 28 | −0.056 | −28.21% | −33.65% |
| 2025-09-24 → 2026-03-25 | 53 / 33 | +0.122 | −19.19% | −18.92% |
| 2026-03-25 → 2026-09-23 | 51 / 33 | −0.004 | −14.58% | −14.47% |
| 2026-09-23 → 2027-03-24 | 2 / 1 | −0.665 | −6.17% | −4.04% |

Window-local DD improved in 3 of 4 windows, but mean ΔE is −0.151R and the
only window with a real sample and a positive delta is 2025-09-24→2026-03-25
(+0.122R on 33 veto trades). Thin and inconsistent — no walk-forward support.

### Left-tail

| Metric | Baseline | Veto |
|---|---|---|
| Worst 5% of trades (mean R) | −1.538R (n=15) | −1.581R (n=11) |
| Max losing streak | 12 | 14 |

The veto does not trim the left tail; both metrics worsen slightly.

### Mechanism: why the veto hurts (same pattern as lone-wolf)

- **38 vetoed candidates were in the baseline book**: total −7.58R
  (mean −0.20R). Removing them alone would have *helped* — the veto correctly
  identified toxic trades.
- **Reshuffling destroys the gain**: 167 baseline trades dropped by the
  re-run competition (−9.36R total, mean −0.06R, roughly neutral); **84 newly
  admitted replacement trades lost −26.42R total (mean −0.31R)** — this is the
  entire damage.
- Only 140 of 307 baseline trades survive in the veto book. Candidate-stage
  filtering frees slots/heat that get filled by much worse replacements.

## 6. Skip-count funnel

| Stage | Baseline | Veto |
|---|---|---|
| Candidates | 3,963 | 3,533 |
| Busy-skipped | 521 | 365 |
| Slot-skipped | 78 | 35 |
| Heat-skipped | 3,057 | 2,909 |
| **Accepted** | **307** | **224** |

## 7. The val-only nuance (decision rule 3, passed — with a cross-check)

The val-only replay (signals from 2025-01-01, fresh $75k start) favors the
veto: DD −45.09% → −34.16% (24.2% relative reduction, just under the 25% bar
used in rule 1) and expectancy −0.0355R → +0.0654R on 239 → 275 trades. This
is a genuine favorable data point and is why rule 3 passed.

But the subperiod cross-check on the **pooled** equity curves disagrees:

| Window | Baseline DD | Veto DD |
|---|---|---|
| Dev (pooled curve) | −28.83% | −39.46% |
| Val (pooled curve) | −44.93% | −51.66% |

On the pooled path — the pre-registered primary comparison — the veto's
drawdown is worse in *both* subperiods. The val-only improvement does not
survive the pooled walk, where dev-period damage carries into the val window.
Two of three decision rules fail; the verdict stands.

## 8. Honesty caveat (recorded before running)

The hypothesis was formed on this same dataset
(`selection_edge/SELECTION.md`: bottom-quartile RS buckets ran −0.23R to
−0.76R). This test is confirmatory-with-caveats, not independent validation —
and it failed even on its home data. The real arbiter remains forward data,
but nothing here earns the veto a forward paper overlay.

## 9. Files

- `selection_edge/laggard_veto_prereg.md` — frozen pre-registration (unchanged)
- `selection_edge/laggard_veto_run.py` — this worker's script
- `selection_edge/laggard_veto_decisions.json` — per-candidate veto decision
  (RS3/RS6 values, buckets, reason; 430 vetoed / 3,963)
- `selection_edge/laggard_veto_baseline.json` — 307 masked-baseline trades
- `selection_edge/laggard_veto_trades.json` — 224 veto-arm trades
- `selection_edge/laggard_veto_results.json` — all metrics + decision record
- `selection_edge/laggard_veto_report.md` — this report

Guardrails honored: no frozen module modified (v54 engine, Mode B exits,
grades, ranking, alerts, forward-test log untouched — only read via imports);
no parameter perturbation or threshold search; the single frozen rule only.
