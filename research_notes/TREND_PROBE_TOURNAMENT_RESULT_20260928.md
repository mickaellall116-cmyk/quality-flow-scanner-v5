# Trend-Probe Tournament Result — 2026-09-28

Research-only. Frozen/live Quality Flow remains unchanged.

## What was tested
On the DST-safe 30-symbol 4H surrogate:
- EMA20/40
- HEMA20/40
- HMA20/40
- KAMA20/40
- ZLEMA20/40

2024-2025 was used for discovery/descriptive splits and 2026 as the holdout. 2023 was excluded from the probe-learning splits because it is only a short partial period.

## Study A — standalone bullish crossovers
At the 10-bar horizon, none of the crossover signals beat their symbol/month-matched random controls:

- EMA: +0.27% SPY-relative vs +2.10% matched random, p=1.00
- HEMA: +0.85% vs +1.39%, p=0.98
- HMA: +0.53% vs +1.10%, p=0.986
- KAMA: +0.98% vs +2.32%, p=1.00
- ZLEMA: +0.68% vs +1.28%, p=0.994

HMA showed a one-horizon 4-bar excess signal (+0.69%, p≈0.03), but it did not persist: 2026 HMA crossover 4-bar excess was negative and 10-bar excess was -0.93%. Treat this as a non-robust isolated result.

Conclusion: **no standalone crossover earns promotion**.

## Study B — what the probes teach us about QF entries

### 1. KAMA state is the clearest new diagnostic
At a QF signal:

2024-2025 discovery:
- KAMA bullish: n=159, +2.32% mean 10-bar SPY-relative
- KAMA bearish: n=42, -0.35%
- difference: +2.67 percentage points

2026 holdout:
- KAMA bullish: n=61, +3.87%
- KAMA bearish: n=17, -3.27%
- difference: +7.13 percentage points

Post-hoc robustness audit (performed only after the preregistered result was visible):
- individual-trade bootstrap discovery difference 95% interval: +0.36 to +5.16 pp
- individual-trade bootstrap 2026 difference: +2.64 to +12.06 pp
- month-block bootstrap discovery: -0.60 to +5.40 pp (includes zero)
- month-block bootstrap 2026: +2.43 to +14.51 pp
- leave-one-symbol-out difference stays positive:
  - discovery range +1.71 to +3.12 pp
  - 2026 range +5.27 to +9.69 pp

Removing the best events weakens the discovery effect substantially; after the top 10 overall discovery events are removed, the KAMA bull-minus-bear difference is near zero. In 2026, however, the difference remains +3.15 pp even after the top 10 events are removed. This is promising but still selected from a multi-probe tournament and therefore not proof of a deployable rule.

### 2. Absolute trend separation looks more informative than crossover timing
KAMA fast-slow gap tertiles were frozen from 2024-2025 and applied unchanged to 2026.

KAMA gap:
- discovery low: -0.33% excess; high: +2.75% (high-low +3.08 pp)
- 2026 low: -2.06%; high: +5.69% (high-low +7.74 pp)

Leave-one-symbol-out keeps the high-minus-low KAMA-gap relationship positive:
- discovery: +1.63 to +3.60 pp
- 2026: +5.58 to +9.48 pp

EMA gap showed the same broad direction:
- discovery high-low: +3.72 pp
- 2026 high-low: +5.49 pp

This suggests the useful information may be **an already-established trend**, not the instant a moving-average crossover occurs.

### 3. Short-term gap expansion is not what the best QF entries want
For both EMA and KAMA, high one-bar gap expansion was worse than low gap change:

EMA gap-delta high minus low:
- discovery: -3.57 pp
- 2026: -7.91 pp

KAMA gap-delta high minus low:
- discovery: -2.11 pp
- 2026: -9.66 pp

A low gap-delta means the fast/slow spread is contracting or expanding less. Combined with the positive absolute-gap result, the emerging hypothesis is:

> **QF may work best inside an already-established trend during a temporary compression/pullback, rather than at a fresh trend crossover or at maximum short-term acceleration.**

That is a hypothesis to validate, not a rule to add yet.

### 4. HEMA/HMA/ZLEMA appear largely redundant
HEMA, HMA and ZLEMA probe features are strongly correlated on QF bars. Examples:
- HMA/ZLEMA gap-delta Spearman ≈ 0.93
- HMA/ZLEMA price-distance ≈ 0.96
- HEMA/ZLEMA price-distance ≈ 0.93
- HEMA/HMA gap-delta ≈ 0.82

KAMA is materially less correlated with those low-lag probes on many features, so it appears to contribute a more distinct view of trend quality.

### 5. HEMA lesson is reinforced
HEMA bullish state at the QF signal was worse than HEMA-bearish state in both periods:
- discovery bull-minus-bear: -1.91 pp
- 2026: -4.65 pp

That supports the prior timing result: waiting for HEMA confirmation can be late.

HMA and ZLEMA bullish-state advantages seen in discovery reversed in 2026, so they do not validate as QF quality filters.

## Current research conclusion
The tournament did **not** find a better standalone crossover.

It did find a useful research direction:
- preserve the QF entry core;
- investigate **established trend strength + temporary compression/pullback**;
- KAMA state/gap is the strongest adaptive probe found so far;
- ordinary EMA gap conveys a similar simpler signal;
- avoid implementing KAMA/EMA filters from this 30-name sample until canonical 131-symbol PIT validation is possible.

No live/frozen change.
