# Selection-Edge Phase 2 (Worker B) — Persistent Cross-Sectional Strength

**Date:** 2026-09-24/25 · **Status:** complete, research only — no production or V5.4 changes.
**Verdicts: RS3 FAIL · RS6 MAYBE · SECTOR_RS FAIL · HI52 FAIL.**

## What was tested

The simplest hypothesis first: "Quality Flow works better on stocks already showing
persistent cross-sectional strength." Four factors, tested **separately, never combined**,
each as a cross-sectional rank at signal time:

| Factor | Definition (strict PIT) | Primary window | Perturbations |
|---|---|---|---|
| RS3 | 63-trading-day stock return minus 63-trading-day SPY return | 63d | 42d, 84d |
| RS6 | 126-trading-day stock return minus 126-trading-day SPY return | 126d | 63d, 168d |
| SECTOR_RS | 63-trading-day sector-ETF return minus 63-trading-day SPY return | 63d | 42d, 84d |
| HI52 | (price − 252-trading-day high) / price (≤ 0; less negative = closer to high) | 252d | 63d, 126d highs |

**Bucketing (pre-registered, not optimized):** at each signal timestamp, rank the working
universe cross-sectionally by the factor and bucket the signal's stock as
TOP QUARTILE / MIDDLE 50% / BOTTOM QUARTILE. Robustness: terciles.
**Primary question:** does expectancy increase **monotonically** top > middle > bottom?

## Blinding

The 14 names (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM, SPCX, ASTX, BBAI, NIO,
HOOD, AMD) are masked from all factor construction, cross-sectional ranking, and
evaluation — verified: zero masked symbols appear in any factor record. Note: only 8 of
the 14 are in the 131-name PIT universe (SOFI, RKLB, ONDS, ASTX, BBAI, HOOD are absent),
so the working set is **123 names**, not 117. All 8 present are excluded.

## Analysis population

The 374 canonical portfolio trades (realized frozen-V5.4 Mode B outcomes under the
canonical $75k / 1% risk / slots / heat replay, leg-based round-trip costs), masked →
**353 working trades** (21 masked-14 trades removed). Per-trade net R is used at
25/50/75/100 bps. Candidate-level outcomes would require a new portfolio replay —
that is Phase 4+ per Mike's spec and was not done here.

## PIT convention (and a leak caught and fixed)

Endpoint = **last completed daily bar as of signal time**: for a 13:30-close signal on
date D that is D−1's bar (D's bar is still forming); for a 16:00-close signal it is D's
bar. The first implementation mistakenly used D's forming bar for 13:30 signals
(midnight-timestamped daily index); this was caught in audit and fixed before results
were finalized — all numbers below use the strict endpoint.

## Gate operationalization

- **PASS** = monotonic top>middle>bottom at 50bps full-sample **and** top bucket positive
  at 50bps **and** monotonic in validation **and** top positive at all four cost levels
  **and** perturbation windows keep the top>bottom direction **and** bootstrap
  P(top−bottom > 0) ≥ 0.95 **and** leave-one-symbol-out min delta > 0 **and** ≥2/3 of
  walk-forward test periods positive **and** top bucket stays positive after dropping its
  top-3 contributing symbols.
- **MAYBE** = directionally consistent (top>bottom, top>0 full-sample) but fails ≥1
  robustness check — thin or fragile.
- **FAIL** = otherwise. "No factor survives" was an acceptable outcome.

Walk-forward = 12-month observe then rolling 6-month test windows on the top−bottom
delta (only 2–3 valid windows: the trade history starts 2024-03-26). Bootstrap = 5,000
resamples. Dev = signal date < 2025-01-01; val = ≥ 2025-01-01.

---

## RS3 — 63-day relative strength vs SPY — **FAIL**

**Hypothesis/mechanism:** a 4H breakout system buys continuation; continuation works when
institutional sponsorship is already behind the name. RS vs SPY > 0 is the simplest PIT
proxy for "this stock is being accumulated relative to the market."

**Monotonicity table (@50bps, quartile):**

| Sample | Top | Middle | Bottom | Monotonic? |
|---|---|---|---|---|
| Full (n=353) | −0.061 (n=174) | +0.048 (n=166) | −0.566 (n=13) | No |
| Dev 2024 (n=115) | −0.341 | −0.035 | −0.494 | No (top worst) |
| Val 2025–26 (n=238) | +0.078 | +0.086 | −0.610 | No |
| 2024 / 2025 / 2026 | −0.341/+0.161/+0.013 | −0.035/+0.057/+0.125 | −0.494/−0.355/−0.763 | — |

**Full protocol:** top bucket never clears zero at any window (63d: −0.061; 42d: +0.057;
84d: +0.008) and is negative at 50/75/100bps at the primary window. Perturbation quartile
windows are monotonic (42d, 84d) but terciles are mixed and the primary window is not —
the top-vs-middle ordering flips by window. Bootstrap P(top−bottom>0) = 0.95 and LOSO
min delta +0.42 look strong, **but both are driven by the bottom bucket being reliably
toxic, not the top being good**: the bottom quartile is the worst bucket in dev, val,
every year, and every cost level (−0.36 to −0.76R, PF 0.27, WR 31%). That rests on only
13 trades, and at the 42d perturbation the bottom bucket (n=5) is not even the worst.
The top bucket's full-sample mean is carried by a few outsized trades (SNDK +14.2R,
ARM +10.5R); dropping the top-3 contributors flips it to −0.25R. Walk-forward has only
one valid test window (bottom bucket too thin elsewhere).

**Verdict: FAIL.** The selection hypothesis does not hold: buying 3-month strength does
not produce a positively-profitable subset, and the top bucket was the *worst* bucket in
dev. Secondary observation (fragile, thin): the bottom quartile of 3-month RS is
consistently the worst place for a Quality Flow signal to fire — a laggard-avoidance
pattern, not a strength-selection pattern — but with n=5–13 it does not survive the
"one lucky cutoff" concern the monotonicity requirement guards against.

## RS6 — 126-day relative strength vs SPY — **MAYBE**

**Hypothesis/mechanism:** same as RS3 over ~6 months — persistent rather than recent
strength marks durable sponsorship, filtering out 1–2 month momentum bursts that revert.

**Monotonicity table (@50bps, quartile):**

| Sample | Top | Middle | Bottom | Monotonic? |
|---|---|---|---|---|
| Full (n=352) | +0.044 (n=145, PF 1.06, WR 37.2%) | −0.065 (n=179) | −0.228 (n=28, PF 0.70) | **Yes** |
| Dev 2024 (n=115) | −0.144 | −0.232 | −0.343 | Yes (all negative, ordered) |
| Val 2025–26 (n=237) | +0.129 | +0.015 | −0.142 | **Yes** |
| 2024 / 2025 / 2026 | −0.144/+0.350/−0.025 | −0.232/−0.062/+0.116 | −0.343/−0.081/−0.220 | 2024✓ 2025✓ 2026✗ |

**Full protocol:** the monotonic ordering is unusually consistent — full, dev, val, 2024,
2025, all four cost levels, terciles at 126d, and **all 79 leave-one-symbol-out deltas
positive** (min +0.17). Perturbation windows keep the top>bottom direction (63d, 168d).
**But:** the top bucket barely clears zero — +0.044R at 50bps (bootstrap 95% CI
−0.23 to +0.35, includes zero), positive only at 25/50bps and negative at 75/100bps.
Bootstrap P(top−bottom>0) = 0.79, well short of 0.95. Walk-forward: 1 of 2 valid periods
positive (+0.136 / −0.122). The top bucket depends on a few big winners (SNDK +14.2R,
ARM +6.2R, CRWD +6.0R); dropping the top-3 contributors flips it to −0.147R. 2026 breaks
the pattern (middle +0.116 best, top −0.025).

**Verdict: MAYBE.** Directionally consistent across nearly every cut — the most robust
ordering of the four factors — but thin: the "selected" subset earns ≈+0.04R/trade with
a confidence interval covering zero, dies above 50bps costs, and leans on a handful of
outsized trades. RS6 sorts trades (laggards lose, leaders break even-ish) but does not
isolate a convincingly profitable subset. Not a PASS.

## SECTOR_RS — 63-day sector-ETF RS vs SPY — **FAIL (wrong-signed)**

**Hypothesis/mechanism:** stocks don't break out alone — sector rotation provides the bid
underneath; a breakout in a leading sector rides institutional sector-allocation flows.
(Sector mapping: current-pull GICS as in the canonical baseline; 23 ETF-universe trades
have no sector and are unranked.)

**Monotonicity table (@50bps, quartile, n=330):**

| Sample | Top sector | Middle | Bottom sector | Monotonic? |
|---|---|---|---|---|
| Full | −0.132 (n=121) | +0.008 (n=153) | **+0.284 (n=56)** | No — reversed |
| Dev 2024 | −0.487 | −0.016 | +0.184 | Reversed |
| Val 2025–26 | +0.061 | +0.020 | +0.318 | Reversed |
| 2024 / 2025 / 2026 | −0.487/+0.003/+0.102 | −0.016/+0.162/−0.162 | +0.184/+0.222/+0.434 | Reversed every year |

**Full protocol:** the top-sector bucket is negative at every cost level
(25bps: −0.03 → 100bps: −0.34) and is the worst or second-worst bucket in every window
(42d/63d/84d), every year, dev and val. Bootstrap P(top−bottom>0) = 0.06; all 79 LOSO
deltas negative (min −0.54); walk-forward 0 of 3 periods positive (−0.708, −0.041, −0.432).

**Verdict: FAIL, with the sign reversed.** Breakouts in *leading* sectors do worse, not
better — the hypothesis is backwards in this sample. This is a clean rejection, not a
thin null: the direction is consistently wrong across windows, years, costs, bootstrap,
LOSO, and walk-forward. (It does not license the inverse trade either — that would be a
new hypothesis requiring its own pre-registration.)

## HI52 — distance from 52-week high — **FAIL**

**Hypothesis/mechanism:** the best breakouts come from stocks already near highs — no
overhead supply, every holder in profit, no trapped sellers. A "breakout" far below the
52-week high is a range trade masquerading as a breakout. (48 early trades lack 252
trading days of PIT history and are unranked.)

**Monotonicity table (@50bps, quartile, n=305):**

| Sample | Top (near high) | Middle | Bottom (far from high) | Monotonic? |
|---|---|---|---|---|
| Full | −0.070 (n=111) | +0.010 (n=160) | −0.171 (n=34) | No |
| Dev 2024 | −0.063 | −0.083 | −0.840 | Yes (bottom n=5) |
| Val 2025–26 | −0.073 | +0.038 | −0.047 | No |
| 2024 / 2025 / 2026 | −0.063/−0.033/−0.110 | −0.083/−0.172/+0.218 | −0.840/+0.188/−0.447 | No pattern |

**Full protocol:** the near-high bucket is negative at 50/75/100bps and never the best
bucket in any year. Perturbation windows (63d/126d highs) show no consistent ordering —
at 63d the *bottom* (far-from-high) bucket is +0.082 while top is +0.003; at 126d the
bottom is −0.50. Bootstrap P(top−bottom>0) = 0.63 (coin flip); walk-forward 2/3 positive
but the deltas swing −0.605/+0.252/+0.336 with no stability.

**Verdict: FAIL.** Proximity to the 52-week high carries no selection signal in either
direction; bucket orderings flip across windows and years.

---

## Cross-factor observations

1. **The robust sub-pattern is laggard toxicity, not strength selection.** In both RS
   factors the bottom quartile is the worst bucket in nearly every cut (RS3 bottom:
   −0.36 to −0.76R every year; RS6 bottom: −0.23R, PF 0.70), while the top quartile
   hovers around zero. Quality Flow signals also rarely fire on laggards (bottom buckets
   hold 13–28 trades vs 145–174 in top) — the entry system already self-selects away
   from them. This is a veto-shaped finding (in the spirit of the old lone-wolf idea),
   not a passed selection factor, and it rests on thin buckets.
2. **Two clean wrong-signed rejections.** SECTOR_RS and HI52 both point the wrong way
   with consistency (SECTOR_RS especially: reversed in every year, window, cost level,
   and all 79 LOSO deltas). Persistent strength helps, if at all, at the *stock* level
   over 6 months — not at the sector level and not via proximity to highs.
3. **Nothing here clears the bar for production.** The strongest candidate (RS6) earns
   ≈+0.04R/trade before realistic costs, with a confidence interval covering zero. No
   factor, alone, identifies a subset of Quality Flow trades worth sizing into.

## Files

- `phase2_strength.py` — full pipeline (data → factors → bucketing → protocol → JSONs)
- `RS3.json`, `RS6.json`, `SECTOR_RS.json`, `HI52.json` — per-factor results incl.
  per-trade factor values/buckets, all splits, walk-forward, bootstrap (5,000),
  leave-one-symbol-out, concentration, gate flags, verdict
- `REPORT.md` — this file
- `run.log` — run output

**Caveats:** trade outcomes are portfolio-simulated (slot/heat competition), not
independent — the rebaseline's effective-n warning (7 chained episodes) applies to
bucket stats too. HI52 excludes 48 early trades (insufficient PIT history). SECTOR_RS
excludes 23 ETF trades (no sector). Walk-forward has only 2–3 valid test windows.
