# CANONICAL-PROTOCOL STUDY B of 3: FVG-as-entry — full 12-step report (2026-09-24)

Pre-registered in `HYPOTHESIS.md` (written before the run; frozen). FVG
definition FIXED — no threshold search. Matched on (symbol, signal_time):
237 BASE trades, 266 FVG trades, 203 shared, 34 BASE-only (omitted),
63 FVG-only (added). Costs 25/50/75/100 bps. `pine_backtest` imported
unmodified; research only; nothing frozen touched.

**Main question (Mike's): Matched-trade comparison — same setup, baseline
entry vs FVG entry. Is FVG improving trade quality, or merely changing the
sample?**

## Step 1 — Pre-registration
`HYPOTHESIS.md` frozen before running. No rule changes after results.

## Step 2 — Same trade population
- Shared-setup ΔR (FVG entry − baseline entry on the same 203 setups):
  **0.000000** (0 nonzero deltas). Third verification. FVG is definitively
  NOT a better entry mechanism.
- Pooled differential ΔE = E_FVG − E_BASE = 0.2852 − 0.2388 = **+0.0464R**.
- FVG-only (added): +0.3871R, n=63. BASE-only (omitted): +0.1504R, n=34.
- PF: FVG 1.477 vs BASE 1.382.

## Step 3 — Dev / validation (Oct2023–Dec2024 / Jan2025–Sep2026)
- FVG_all: dev +0.4554 (n=80) → val +0.2120 (n=186). Decays by more than half.
- BASE_all: dev +0.3474 (n=75) → val +0.1884 (n=162).
- Validation differential: +0.0236 — directionally positive but thin. The
  RKLB monster trade (2024-09-09) sits in DEV, so validation excludes it.

## Step 4 — Rolling walk-forward (train 12mo / test 6mo / roll 6mo)
Test windows only (untouched):
- Oct2024–Mar2025: −0.2287 · Apr2025–Sep2025: +0.1512 ·
  Oct2025–Mar2026: +0.2040 · Apr2026–Sep2026: −0.0807
- **Combined test windows: −0.0289** (n=215 FVG / 190 BASE). NEGATIVE.
  The differential does not survive rolling walk-forward. (The RKLB trade
  falls in a train window, not a test window.)

## Step 5 — Year and regime splits
- 2023: no trades fired (n=0 both variants — no signal, no contribution).
- 2024: +0.108 · 2025: +0.0904 · **2026: −0.0305** (flips negative).
- Bull regimes (246/221 trades, the bulk of the data): **+0.0019 — flat.**
  The entire pooled edge lives in the tiny bear/sideways bucket
  (+0.5078, n=20/16), i.e. the RKLB trade.

## Step 6 — Cost stress
ΔE survives at 25/50/75/100 bps (+0.0464 → +0.0474). Passes on paper — but
cost stress on a one-trade edge is meaningless; the monster trade is so
large that friction can't touch it.

## Step 7 — Selection-boundary perturbation (no optimization)
- Drop top-1 trade (RKLB 2024-09-09, +12.98R): ΔE = **−0.0015** (flips).
- Drop top-3 trades: ΔE = **−0.0584**.
- The differential does not survive removal of its best trade. This is the
  pre-registered robustness FAIL condition, and it triggered.

## Step 8 — Concentration (share of the 19.27R total-R differential)
- Best 1 trade (RKLB): **67.4%**. Best 3 trades: **147%** (everything else
  nets negative). Best 5 trades: 186%.
- Best 1 symbol (RKLB): 75.6%. Best 3 symbols: 147%.
- Best 1 theme (Space): 87.4%. Best 3 themes: 159.8%.
- Best year (2025): 75.5%; 2026 contributes −5.65R (negative).
- Every concentration gate is a red flag.

## Step 9 — Bootstrap (10,000 resamples, seed 42)
- Fraction with ΔE > 0: **0.5931** — a coin flip, not a typical outcome.
- Fraction with ΔE > +0.02R (material): 0.5501.
- ΔE distribution: p5 = −0.2432, p50 = +0.0431, p95 = +0.3397.
- The observed +0.0464 sits at the median, but positive expectancy is
  barely more likely than negative. Lucky-tail territory, not a reliable
  edge. (Pre-registered PASS needed ≥80%; FAIL <50%. This is 59%.)

## Step 10 — Leave-one-symbol-out
No single-symbol removal flips the differential's sign (RKLB removed:
+0.0243; AMD removed: +0.0178 — the thinnest). Passes the LETTER of the
gate — but only because RKLB has offsetting trades in BOTH variants. Step 7
shows the SPIRIT fails: remove just the monster trade (not the symbol) and
the edge dies.

## Step 11 — Economic effect
- Δ expectancy: +0.0464R. Δ PF: +0.095 (1.477 vs 1.382).
- Δ max DD: **+5.34R WORSE under FVG** (36.08 vs 30.74) — the variant
  digs a deeper hole for the extra return.
- Trades added: 63 / removed: 34. Opportunity cost: added bucket +0.3871R
  vs removed bucket +0.1504R.
- Return per unit of risk: FVG 2.10 vs BASE 1.84 — marginally better, but
  built on a deeper drawdown and one trade.

## Step 12 — Paper it forward untouched
The exact FVG version is papered live via the FVG paper sidecar since
2026-09-23. This study does not change it. The sidecar remains the
uncontaminated arbiter — but the backtest verdict below stands on its own.

## VERDICT: FAIL

Per the pre-registered gates AND Mike's explicit standard ("if the
differential survives only with the RKLB trade included, that's a FAIL of
robustness even if the pooled number is positive"):

- Pooled ΔE is positive (+0.0464) — the pretty backtest.
- Removing the single best trade flips it to −0.0015 → pre-registered
  FAIL condition triggered.
- Rolling walk-forward combined test windows: −0.0289 → the edge does not
  persist out-of-sample under the protocol's own walk-forward.
- 2026 flips negative; bull regimes (the bulk of trades) are flat at
  +0.0019; the edge lives in one bear-regime trade.
- Bootstrap: 59% positive — a coin flip.
- One trade = 67% of the differential; top 3 = 147%.
- Max DD is 5.34R WORSE under FVG.

This is not "needs more data" (MAYBE). The protocol's job was to stop
getting seduced by pretty backtests, and the pretty +0.285R vs +0.239R
does not survive the sequence. FVG-as-entry is **changing the sample, not
improving trade quality** — and the sample change was one trade.

What remains open: the live paper sidecar (since 2026-09-23) is untouched
by this verdict. If live FVG-only trades run hot against the −0.37R
historical median, that is NEW data and can reopen the question. The
backtest evidence, however, is closed: FAIL.

## Files
- `HYPOTHESIS.md` — pre-registration (frozen pre-run)
- `run_fvg_protocol.py` — study script (imports `pine_backtest` and prior
  study helpers unmodified)
- `fvg_protocol_results.json` — all 12 steps, machine-readable
- `README.md` — this file

Guardrails respected: research only. V5.4, Mode B, production alerts,
grades, market gate, AI Observer, and the live FVG sidecar untouched.
