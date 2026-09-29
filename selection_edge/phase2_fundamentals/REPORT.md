# REPORT.md — Phase 2, Family 7: Fundamental Momentum

## PRE-REGISTRATION (written before any result was computed)

**Factor F7-REV — Net analyst rating revisions, trailing 63 trading days.**

_Why this construction:_ F7's pre-registered candidates were (a) "positive
net EPS revisions in trailing 63 trading days" and (b) post-earnings drift.
The data audit (DATA_AUDIT.md) found (a) untestable as specified — no
accessible source carries EPS estimate *revisions with timestamps* — and
revenue growth untestable (5 quarters of history, ~42% coverage). Analyst
*rating* revisions with per-action timestamps exist with 100% coverage and
strict PIT integrity, and match F7's mechanism ("analysts revising up means
the numbers are improving"). This substitution is explicit, not a proxy.

**Construction (exact):**
- Event log: `yfinance.get_upgrades_downgrades()` per ticker — GradeDate,
  Action ∈ {up, down} only. `main` (reiterations/price-target moves) and
  `init` (initiations) excluded.
- Signal time `t` (signal_bar_close_at); as-of date = last completed daily
  bar ≤ signal-bar close (canonical PIT contract; 91% of signals are
  first-bar 13:30 closes → as-of = prior trading day).
- Raw value for ticker `s` at as-of `d`:
  `V(s,d) = #{up : d−63 trading days < GradeDate ≤ d} − #{down : same window}`
  (63 *trading* days on the NYSE calendar).
- Cross-sectional percentile: rank of `V(signaled ticker, d)` among the
  117 working names' `V(·, d)` at the same `d`; ties get average rank.
- Buckets: **top quartile** (pct ≥ 75, "strong revisions"), **middle 50%**,
  **bottom quartile** (pct < 25, "weak revisions").

**Evaluation population:** `canonical_trades.json`, 14 blinded names masked
out of construction AND evaluation → 353 trades; minus 23 ETF/notes trades
(XLE, GLD, XLF, TLT, ARKK, DIA, XLK, IWM, SMH, SPY — no analyst coverage
exists for ETFs, so the factor is undefined there) → **330 stock trades**.
Both exclusions are scope decisions, made before any result was computed.

**Primary question:** monotonicity — E[top] > E[middle] > E[bottom] at
50bps round-trip (`net_r_50bps`). Secondary: top bucket clears zero; top−bottom spread.

**Protocol:**
- Dev Oct 2023–Dec 2024 / val Jan 2025–Sep 2026 (by signal date).
- Walk-forward 12mo train / 6mo test, 6mo step.
- Costs 25/50/75/100bps round-trip (fields already on each trade).
- Concentration: year splits; top-10 trades' share of each bucket's P&L;
  top symbol's share.
- Bootstrap ≥ 5,000 resamples within buckets: P(top−bottom > 0),
  P(top expectancy > 0).
- LOSO over symbols represented in the top bucket.

**Gates (pre-registered):**
- PASS = monotonic on full sample AND monotonic in validation AND top > 0
  at 50bps AND top > 0 at 75bps AND LOSO sign-stable (no single symbol
  flips top−bottom sign or top positivity).
- MAYBE = directionally consistent (top > bottom) but a gate fails or
  samples are too thin to judge.
- FAIL = otherwise.

---

## RESULTS

**Verdict: FAIL.** The factor has *negative* selection value as constructed —
stocks with the strongest analyst revisions underperform; the weak-revision
bucket wins by a wide, statistically firm margin.

### Full sample (330 stock trades, @50bps round-trip)

| Bucket | n | Expectancy (R) | Win rate | Total (R) |
|---|---|---|---|---|
| Top quartile (strong revisions) | 109 | **−0.1354** | 37.6% | −14.76 |
| Middle 50% | 160 | −0.0820 | 37.5% | −13.11 |
| Bottom quartile (weak revisions) | 61 | **+0.4802** | 49.2% | +29.29 |

Monotonicity (top > mid > bottom): **FALSE** — the ordering is inverted.
Top−bottom spread: **−0.6156R** (in favor of weak revisions).

### Costs (mean R by bucket)

| | 25bps | 50bps | 75bps | 100bps |
|---|---|---|---|---|
| Top | −0.033 | −0.135 | −0.238 | −0.340 |
| Mid | +0.022 | −0.082 | −0.186 | −0.289 |
| Bottom | **+0.586** | **+0.480** | **+0.374** | **+0.268** |

Top is negative at every cost level; bottom is positive at every cost level.
The "top positive at 50bps" gate fails outright.

### Dev / validation (by signal date)

- Dev Oct 2023–Dec 2024 (n=107): top −0.248 / mid −0.105 / bottom −0.223 — no monotonicity.
- Val Jan 2025–Sep 2026 (n=223): top −0.082 / mid −0.073 / bottom **+1.038** — no monotonicity.

### Walk-forward (12mo train / 6mo test)

No train window shows monotonicity (4/4 FALSE); test windows are mixed and
thin (top-bucket n = 16–25 per window).

### Bootstrap (5,000 resamples)

- P(top−bottom spread > 0) = **1.7%** — the negative spread is significant,
  95% CI [−1.18, −0.05].
- P(top expectancy > 0) = **18.4%** — top does not clear zero.

### LOSO (top bucket, 62 symbols)

No single symbol flips the sign of the top bucket or the (negative)
spread — the failure is broad-based, not one bad name. ARM is the largest
top-bucket contributor (+10.49R on 2 trades) and removing it makes top
*worse* (−0.236), so the negative top result is not an ARM artifact.

### Concentration caveat on the bottom bucket

The bottom bucket's +29.29R is concentrated: 3 symbols (OXY, VLO, MU) are
68% of it, across 48 symbols / 61 trades. The inverse pattern is real but
fragile — and adopting it would be un-registered data mining, so it is
reported as an observation only, not a factor.

### Interpretation

Analyst upgrades cluster on crowded, well-sponsored names; V5.4 breakouts
firing *into* that sponsorship underperform, while breakouts in names
analysts are cutting (often washed-out sentiment, e.g. energy 2025–26)
outperform. Whatever the mechanism, the pre-registered direction is wrong
and no gate is met.

### Gate checklist

- [x] Monotonic full-sample: NO (inverted)
- [x] Monotonic in validation: NO
- [x] Top > 0 @50bps: NO (−0.135)
- [x] Top > 0 @75bps: NO (−0.238)
- [x] LOSO sign-stable: n/a — failure is stable, not the success

**F7-REV: FAIL. Do not adopt. Nothing changes in production.**

---

## Artifacts

- `DATA_AUDIT.md` — the data audit (this study's main deliverable)
- `FACTOR.json` — pre-registered factor definition
- `factor_values.json` — per-trade factor values, buckets, net R
- `factor_results.json` — full protocol numbers
- `compute_factor.py`, `analyze_factor.py` — scripts
- `audit_earnings.py`, `audit_revenue.py`, `audit_revisions.py`,
  `fetch_revision_series.py` — audit scripts
- `revision_series.json` — timestamped analyst-action event log (PIT input)
- `daily_prices.pkl` — daily closes for the 113 (trading-day calendar)
