# Phase 2 Selection-Edge — Worker C (factors FAM2, FAM3, FAM5, FAM6)

_Report date: 2026-09-24. Pre-registered definitions written BEFORE any computation.
Worker C scope per coordinator spec: Phase 2 factor families 2, 3, 5, 6, ONE AT A TIME, no combining._

## 0. Supersession note

FACTOR_MENU.md's F2/F3/F5/F6 (acceleration, ADDV expansion, ATR expansion, 60-day-high proximity)
are covered by other Phase-2 workers. The families below are Mike's exact Phase-2 spec for this
worker and govern here. Worker B covers raw 3-mo/6-mo RS — not duplicated here.

## 1. PRE-REGISTERED FACTOR DEFINITIONS (locked before testing)

**Blinding:** the 14 names (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM, SPCX, ASTX, BBAI,
NIO, HOOD, AMD) are masked out of ALL construction, threshold-setting, and evaluation.
Actual: 8 of the 14 are in the 131-name PIT universe → **123-name working set**
(W1 found the same). Cross-sectional quartile cutpoints are computed over the 123 only;
masked symbols never enter construction.

**Trade population:** canonical_trades.json (374 V5.4 Mode B portfolio trades, $75k/1% risk/
6-slot/5%-heat/rs_top2 competition, net R at 25/50/75/100bps round-trip), minus any trades
on masked symbols → evaluation set recorded in each JSON. Rationale: the question is
"which subset of the system's *taken* trades works" — the same population framing as W1's
trade-level splits; portfolio-replay results below are independent-trade bucket stats on
that population (economic replay reserved for survivors per the menu).

**Strict PIT:** factor endpoint = last COMPLETED daily bar as of signal-bar close (same
convention as W1: tz-aware d1 index, searchsorted right − 1; if signal-bar close hour < 16 ET,
step back one more — the signal-day daily bar is still forming). All indicator math causal
(adjust=False EMA, Wilder ATR, causal rolling windows).

### FAM2 — Trend persistence
- **Primary construction:** for trading day d, `pct63(d)` = fraction of the trailing 63
  trading days (d−62..d) whose daily close is above the 50-day EMA of closes computed
  through d (EMA span 50, adjust=False — causal).
- **Range:** [0, 1]. Higher = name has spent most of the last quarter in a persistent
  uptrend above its intermediate trend filter.
- **Mechanism:** persistent uptrends = institutional sponsorship in place. V5.4 buys
  breakouts; breakouts in names already held above their 50-day EMA most of the quarter
  carry program support underneath. A breakout in a name that cannot stay above its own
  50-EMA is fighting its trend.
- **Perturbations (±1 step, not optimization):** trailing window 63 → 42 / 84
  (EMA span fixed at 50).

### FAM3 — ATR-normalized momentum
- **Primary construction:** for trading day d, 126-trading-day total return divided by
  (14-day Wilder ATR at d / close at d):
  `mom(d) = (C(d)/C(d−126) − 1) / (ATR14(d)/C(d))`, dimensionless.
- **Mechanism:** risk-normalized momentum. A move that is large *relative to the stock's
  own volatility scale* indicates real directional conviction rather than noise; dividing
  by ATR/price lets momentum be compared across names without the volatility bias that
  makes raw momentum just pick the wiggliest stocks. (Worker B covers raw 3-mo/6-mo RS;
  this construction is intentionally different.)
- **Perturbations:** return window 126 → 84 / 168 (ATR span fixed at 14).

### FAM5 — Volatility behavior (own-regime percentile)
- **Primary construction:** for trading day d, 63-day realized vol `rv63(d)` = std of
  daily log returns over the trailing 63 trading days × √252. Factor(d) = percentile
  rank of rv63(d) within its own trailing 252 values (d−251..d), i.e.
  rank/(n) via rolling pct-rank — the value's own-history percentile, PIT-computed on
  data ≤ d.
- **Range:** [0, 1]. High = name's current realized-vol regime sits in the top of its own
  trailing-year range.
- **Mechanism:** the system's exit stack harvests volatility expansion — the trade IS a
  bet that realized volatility stays elevated. Entering when the name is already in its
  own high-vol regime means the market has confirmed the regime the system needs;
  entering in a name sitting in its own low-vol regime means betting on expansion that
  hasn't started. (Distinct from the volume question — FAM6 is participation, this is
  price movement regime.)
- **Perturbations:** rv window 63 → 42 / 84 (history length fixed at 252).

### FAM6 — Liquidity/participation trend
- **Primary construction:** for trading day d, ordinary-least-squares slope of
  log(dollar volume) over the trailing 63 trading days, where dollar volume = close ×
  volume (adjusted; days with non-positive dollar volume dropped from the window; slope
  in units of log-volume per trading day, annualized ×252 for reporting only).
- **Mechanism:** breakouts need participation — a rising trend in dollar volume means new
  money arriving, the fuel a breakout needs to sustain; a flat or declining trend means
  the move is happening on shrinking participation and should fail more often. A *trend*
  (not a level) is used so the factor measures changing sponsorship, not size — a level
  would just re-select large caps.
- **Perturbations:** window 63 → 42 / 84.

## 2. BUCKETING (pre-registered)

At each signal time, the factor is computed for ALL 123 working symbols at the PIT
endpoint D (strict PIT as above). The signal's bucket = cross-sectional quartile of its
own value at D among symbols with non-null factor values:

- **TOP** = value ≥ 75th percentile of the cross-section at D
- **BOTTOM** = value ≤ 25th percentile of the cross-section at D
- **MIDDLE** = middle 50%

Cutpoints are never fit — they are mechanical quartiles of the contemporaneous
cross-section. **Primary question: monotonic expectancy improvement TOP > MIDDLE > BOTTOM.**

## 3. PROTOCOL (per factor)

1. Per-bucket at 50bps (headline): n, expectancy (R), profit factor, win rate, max DD
   (on cumulative net-R equity, chronological).
2. Monotonicity: TOP > MID > BOTTOM on expectancy (primary); TOP−BOTTOM delta.
3. Cost ladder 25/50/75/100bps RT on the delta and per bucket.
4. Dev Oct 2023–Dec 2024 / untouched val Jan 2025–Sep 2026 (verdict on val).
5. Year splits 2024 / 2025 / 2026-YTD.
6. Rolling 12mo-observe / 6mo-test walk-forward on TOP−BOTTOM delta (fixed quartile rule;
   observe window = context).
7. Perturbations ±1 step (headline + val only).
8. Concentration: drop top 1/3/5 symbols by TOP-bucket total-R contribution; recompute
   TOP−BOTTOM delta and TOP expectancy.
9. Bootstrap 5,000 on the delta (trade-level primary + symbol-block secondary); bootstrap
   CI on TOP-bucket absolute expectancy.
10. Leave-one-symbol-out on delta and TOP expectancy.
11. Absolute check: does the TOP bucket clear zero (bootstrap 95% CI)?

## 4. GATES (pre-registered)

- **PASS** = monotonic TOP>MID>BOTTOM + TOP positive at 50bps + survives validation
  (dev/val consistent direction, val delta ≥ 0) / costs (positive at 75bps) /
  perturbation (±1 step keeps direction) / LOSO (min ≥ 0) + bootstrap CI on delta
  excludes 0.
- **MAYBE** = directionally consistent but thin (fails ≥1 gate).
- **FAIL** = otherwise. "No factor survives" is an acceptable result.

---

## 5. RESULTS

_(appended after computation; everything above was written first)_

### 5.1 Population and blinding audit

- Canonical trades: 374 → **353 evaluated** after masking 21 trades on the masked names
  (AMD, ANET, NIO, PLTR, SMCI — the 5 of the 14 that appear in the 131-name universe;
  QQQ, DRAM, SPCX had no taken trades). QQQ/DRAM/SPCX/SOFI/RKLB/ONDS/ASTX/BBAI/HOOD
  were never in the universe or never traded — nothing to mask.
- Cross-sectional quartile cutpoints computed over the **123-name working set only**
  (131 minus the 8 masked names present in the universe); masked symbols never enter
  construction, cutpoints, or evaluation.
- Headline cost = 50bps round-trip; net R per cost level taken from canonical_trades.json.
- Bucketing machinery spot-checked on a sample trade (MSFT 2024-03-26): own value
  vs cross-sectional q25/q75 lands in the assigned bucket; PIT endpoint follows the
  W1 strict convention (last completed daily bar as of signal-bar close).

### 5.2 Headline monotonicity table (@50bps, TOP / MIDDLE / BOTTOM expectancy, R)

| Factor | TOP (n) | MIDDLE (n) | BOTTOM (n) | Mono | TOP−BOT Δ | TOP PF | TOP win% | TOP maxDD |
|---|---|---|---|---|---|---|---|---|
| FAM2 trend persistence | −0.0735 (125) | 0.0273 (186) | −0.1435 (42) | **No** | +0.070 | 0.90 | 35.2% | −18.8R |
| FAM3 ATR-norm momentum | +0.0565 (144) | −0.0972 (184) | −0.0798 (24) | **No** | +0.136 | 1.08 | 39.6% | −16.2R |
| FAM5 vol-regime pctile | −0.0034 (72) | −0.0838 (131) | +0.1182 (66) | **No** | −0.122 | 1.00 | 40.3% | −14.4R |
| FAM6 dollar-vol trend | +0.0698 (140) | −0.0756 (158) | −0.1449 (55) | **Yes** | +0.215 | 1.11 | 41.4% | −21.1R |

(PF/win/maxDD from the JSONs' headline blocks; maxDD on chronological cumulative
net-R within bucket.)

### 5.3 Protocol summary per factor

**FAM2 — trend persistence → FAIL.**
Headline not monotonic (MIDDLE best at +0.0273; TOP −0.0735), TOP negative, TOP
absolute 95% CI [−0.376, +0.254] does not clear zero. Dev Δ −0.452 vs val Δ +0.310
(sign flip); year splits: 2024 −0.452 / 2025 +0.543 / 2026 +0.035 (regime-flippy).
Perturbation fam2_84 flips headline direction (−0.020). Bootstrap Δ CI
[−0.437, +0.577], p(positive)=0.61. LOSO Δ min −0.002. Verdict: FAIL on 5 hard gates.

**FAM3 — ATR-normalized momentum → FAIL.**
Headline not monotonic (BOTTOM −0.0798 > MIDDLE −0.0972; BOTTOM bucket thin, n=24 —
the trade population barely samples the bottom quartile). Val Δ −0.043 (wrong way);
walk-forward test windows swing −0.85..+1.60 (thin buckets, n=56–79). Year splits:
2024 +0.238 / 2025 +0.232 / 2026 −0.404. Bootstrap Δ CI [−0.623, +0.843],
p(positive)=0.67. TOP absolute CI [−0.229, +0.348], does not clear zero.
Perturbations directionally agree (fam3_84, fam3_168) but on thin, unstable buckets;
concentration: dropping top 3 (SNDK, MELI, CRWD) flips Δ negative. Verdict: FAIL.

**FAM5 — volatility-regime percentile → FAIL.**
Headline Δ −0.122 (wrong direction: BOTTOM +0.118 best). Warmup cost is severe:
rv63-over-252 needs ~315 trading days, so 84 of 353 trades have no factor value
(dev period reduced to 42 factor-bearing trades). Dev Δ −1.989 (n=42, BOTTOM +1.534
on n=9 — noise), val Δ +0.184 monotonic-but-thin. Bootstrap p(positive)=0.35
(leans wrong way); LOSO Δ negative in 103/104 removals. TOP absolute CI
[−0.365, +0.402]. Verdict: FAIL — no evidence the system's exit stack prefers
own-regime high-vol entries.

**FAM6 — dollar-volume trend → FAIL** (closest of the four; override documented).
Headline IS monotonic (TOP +0.070 / MID −0.076 / BOT −0.145, Δ +0.215) and val is
monotonic and strong (Δ +0.661) — but:
- **dev/val inconsistent:** dev Δ −0.593 (TOP −0.240, BOTTOM +0.353) vs val Δ +0.661.
  Fails the written MAYBE gate ("directionally consistent").
- **Concentration:** the TOP bucket's +9.8R total is entirely SNDK (+14.24R) and ARM
  (+11.27R); ex those two the bucket is −15.7R net. Dropping the top 3 TOP-bucket
  symbols (SNDK, ARM, MS) kills the Δ (0.215 → −0.006) and flips TOP expectancy
  negative (+0.070 → −0.151).
- **Absolute:** TOP 95% CI [−0.216, +0.384] does not clear zero.
- **Bootstrap:** Δ CI [−0.370, +0.751] includes 0, p(positive)=0.78.
- **Walk-forward:** 2 of 4 test windows negative (−0.242, −0.415); the positives are
  2025-10–2026-04 (+1.812) and 2026-04–2026-10 (+0.344) — the effect is a
  2025–2026 phenomenon.
- Perturbation fam6_42 flips headline direction (−0.072); fam6_84 agrees.
Auto-judge initially returned MAYBE; corrected to FAIL against the written gates
(see FAM6.json "override"). Nothing here survives as a selection rule.

### 5.4 Verdicts

| Factor | Verdict | Headline Δ @50bps | Monotonic | Val Δ | Top clears 0? |
|---|---|---|---|---|---|
| FAM2 trend persistence | **FAIL** | +0.070 | No | +0.310 | No |
| FAM3 ATR-norm momentum | **FAIL** | +0.136 | No | −0.043 | No |
| FAM5 vol-regime percentile | **FAIL** | −0.122 | No | +0.184 | No |
| FAM6 dollar-volume trend | **FAIL** | +0.215 | Yes | +0.661 | No |

**No factor survives.** No combination work is triggered (per spec, combos wait for
independent survivors). No production changes, no V5.4 changes.

### 5.5 Artifacts

- `trade_factors.json` — 353 masked trades with per-factor values + quartile buckets
  (base lookback + ±1-step perturbation variants), strict PIT.
- `FAM2.json`, `FAM3.json`, `FAM5.json`, `FAM6.json` — full protocol numbers per factor.
- `compute_factors.py`, `analyze_factors.py` — scripts (definitions locked in
  REPORT.md §§1–4 before these ran).
- Engine imported, not rebuilt: `canonical_baseline/simlib.py`
  (daily-data loaders, PIT helpers); net R and trade records from the frozen
  `canonical_trades.json` portfolio replay.
