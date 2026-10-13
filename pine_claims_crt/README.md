# Candle Range Theory (CRT) sweep-and-return — weekly outside-claims sweep

**Date:** 2026-10-12 (weekly sweep, Mike-approved 2026-09-24). **Status:** research, local-only.
Modifies nothing frozen (V5.4, Mode B, production alerts, grades, market gate, AI Observer untouched).
`pine_backtest.py` imported UNMODIFIED.

## Origin

**Primary source:** @think_ict Instagram reel "Candle Range Theory (CRT) for Beginners",
posted 2026-10-10 (https://www.instagram.com/reel/DeTuCZlBXQ9/). The claim, in the
reel's terms: *every candle has a high and low; if price sweeps above the high of a
candle but then closes back below it, that's a strong signal the market is likely to
move toward that candle's low. The reverse is true for a sweep below the low.*

**Corroborating sources (same rule, same week):**
- TTrades fractal-model article (~2026-10-03, https://proea.app/en/blog/fractal-model-what-we-measured):
  "a candle sweeps the last one's high or low and closes back inside it, and the
  target is its other side" — the CRT skeleton without the CISD filter. Their 108-version
  study ran on SIMULATED candles, not real market data.
- @jireh_trades "THE REVERSAL CANDLE" (2026-10-06, https://www.instagram.com/reel/DeKuLNsDsl0/):
  a candle that pushes beyond the previous high/low but closes back inside = sweep/rejection.
- "Liquidity Logic — THE HOOK / THE SWEEP / THE POINT" (2026-10-10,
  https://www.facebook.com/reel/1041493982271024/): a low is swept because "that low is full
  of stops," price trades through it and closes back inside — defined as a liquidity sweep.

**Why it qualifies.** (a) Precise rule definable on 4H bars (below — purely OHLC, no
multi-timeframe discretion). (b) Plausible market mechanism: stop-hunt/liquidity sweep —
resting stops are flushed, breakout traders get trapped, and the failed auction reverts
toward the prior range's far end. (c) Applies to 4H swing entries on the 14-stock
watchlist. No data we lack. Not previously tested (breakout-retest was Sep-24 FAIL;
PoC pullback was Oct-05 FAIL; this is the stop-run reversal family).

**Runners-up rejected this week:** liquidity-sweep + break-of-structure + Fib-0.71 confluence
(@chavan.v4 reel 2026-10-06, https://www.instagram.com/reel/DeJu9uFITAE/) — precise but
requires 15M rejection/structure-break data we don't test on; the 4H portion reduces to
"buy 4H support in an uptrend," which is a vague vibe. ICT "PD array tap → rejection
candle 50% entry" (Jin Ren Tenh, FB reel 2026-10-05) — discretionary arrays, same FVG
family already tested FAIL.

## Pre-registration (frozen BEFORE running)

**Hypothesis.** A 4H candle that sweeps the prior candle's range extreme and closes back
inside it marks a completed stop-hunt; price then gravitates toward the reference
candle's far end — a tradable 4H mean-reversion with defined risk at the sweep extreme.

**Mechanism (why it could be real).** Resting stop clusters sit at visible prior-candle
extremes; a wick through the level flushes them and traps breakout-chasers; the failure
to hold beyond the level is the information (new shorts/long-stops all push one way).
Tight, one-bar pattern = few researcher degrees of freedom.

**Exact rule, pre-declared, no tuning.** Reference candle C1 = bar i−1; signal candle
C2 = bar i (confirmed at close of bar i). On bar index i:
- **BULLISH CRT:** `low[i] < low[i-1]` (swept below C1's low) AND
  `close[i] > low[i-1]` AND `close[i] <= high[i-1]` (closed back inside C1's range).
  → LONG, toward C1's high.
- **BEARISH CRT:** `high[i] > high[i-1]` (swept above C1's high) AND
  `close[i] < high[i-1]` AND `close[i] >= low[i-1]` (closed back inside C1's range).
  → SHORT, toward C1's low.
- Entry: open of bar i+1. Stop = sweep extreme (bullish: `low[i]`; bearish: `high[i]`).
  If the entry open crosses the stop, the trade is skipped (same convention as the
  canonical engine).
- **Exits: canonical Mode B**, mirrored bar-for-bar from `gen_pine_trades` (TP1 limit
  intrabar at `entry ± 1.333·risk`, +1R Profit Protect arms runner trail at
  `close ∓ atr·TRAIL_ATR`, close-evaluated exits filled at next-bar open, stop wins
  ties, EMA55 / EMA200-trend exits mirrored for shorts). The reel's "target = C1's
  other end" is NOT used — exits are the canonical engine's; the test is about the ENTRY.
- **Adaptation (stated, not hidden):** the claim defines risk as `entry − stop` (sweep
  extreme) instead of the canonical `1.5·ATR` stop. TP1 preserves the canonical Mode B
  TP1:R multiple: `TP1 = entry + (entry − stop) × (TP_ATR/SL_ATR) = entry + 1.333·risk`.
- One position per symbol at a time; new setups while in a trade are ignored.
- Requires `i ≥ WARMUP+1` and `i+1 ≤ n-2` (entry bar must be manageable).

**Variants.**
- **CRT-LONG (primary):** bullish sweeps only. Compared against the in-study long-only
  baseline. This is the PASS/MAYBE/FAIL gate variant.
- **CRT-SHORT:** bearish sweeps only, mirrored exits. Standalone vs ~0R (no short
  baseline exists in this stack).
- **CRT-LS:** pooled bidirectional = the claim as stated (both legs). Reported vs ~0R
  and vs the long baseline with the asymmetry noted.
- **Perturbation (pre-declared, NOT a variant swap):** sweep-margin filter — require
  the sweep to exceed 0.25·ATR(14) beyond C1's extreme (hairline 1-tick sweeps are noise).
  Run as a robustness check on CRT-LONG; the primary stays the unfiltered exact claim.

**Test plan.**
- Universe: 14-stock watchlist (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM, SPCX, ASTX,
  BBAI, NIO, HOOD, AMD). 4H bars, Oct 2023 → Sep 2026
  (`pine_entry_timing_backtest/cache/h4_<SYM>.pkl` — same corrected cache as prior studies).
- BASE: standard Hybrid `pine_buy_signal` + `gen_pine_trades`, **rerun in-study** (never
  reuse numbers across studies). Expected ≈237 trades, +0.239R @25bps.
- Costs: 25/50/75/100 bps (plus 4bps for the table), portfolio `simulate_portfolio`
  @1% risk, max 5 positions, 5% heat — identical to prior studies.
- Splits: development Oct 2023–Dec 2024 vs validation Jan 2025–Sep 2026; per-year
  breakdown; per-symbol concentration; top-1/3 symbol R-share; @50bps stress.

**Success gate (pre-declared, same as sweep #1):**
- **PASS:** pooled CRT-LONG expectancy ≥ +0.35R @25bps AND ≥ 60 trades AND
  validation-half (2025→Sep 2026) expectancy > 0 AND @50bps expectancy ≥ +0.15R AND
  no single symbol contributes > 40% of total net R.
- **MAYBE:** beats the in-study baseline with ≥ 40 trades, but fails ≥ 1 robustness
  dimension (concentration / a year / validation / cost stress).
- **FAIL:** expectancy @25bps ≤ in-study baseline, or negative, or < 40 trades
  (too thin to mean anything).

## Results (2026-10-12)

BASE (in-study rerun): 237 trades, win 50.6%, exp **+0.239R @25bps**, PF 1.38,
maxDD 21.63% — reproduces the canonical 4H Hybrid baseline exactly; comparison is valid.

CRT-LONG (bullish sweeps, primary, pooled, 14 names):

| Cost | Trades | Win% | Expectancy | PF | MaxDD |
|---|---|---|---|---|---|
| 4bps | 811 | 48.7 | −0.192R | 0.80 | 100.1% |
| 25bps | 811 | 46.6 | **−0.358R** | 0.65 | 100.0% |
| 50bps | 811 | 42.0 | −0.555R | 0.51 | 100.0% |
| 100bps | 811 | 33.2 | −0.949R | 0.32 | 100.0% |

Attribution: 1,438 bullish sweeps + 1,359 bearish sweeps observed while flat;
495 ambiguous (both extremes swept in one bar, closed back inside — skipped per prereg);
811 long trades taken; 8 skipped on gap-through-stop.
Year splits (25bps): dev 2023–24 n=215 −0.568R; val 2025–26 n=596 −0.282R.
By year: 2024 n=215 −0.568R; 2025 n=299 −0.773R; 2026 n=297 +0.213R.
Per-ticker: only SMCI (+8.7R) and HOOD (+68.6R) positive of 14; worst RKLB −80.4R,
ONDS −77.8R. Broad-based failure, not concentration.

CRT-LONG-MARGIN (perturbation, sweep depth ≥ 0.25·ATR): 518 trades, **−0.261R @25bps**,
PF 0.66 — the nearby formulation fails too; the idea does not survive perturbation.

CRT-SHORT (bearish sweeps, mirrored exits): 835 trades, **+0.165R @25bps**, PF 1.15 —
positive headline, but HOOD contributes +309.7R of +137.6R total (225% top-1 share:
without HOOD the leg is negative), and @50bps it is already −0.254R. Same lottery-ticket
pathology as the Oct-05 PoC study, same ticker. Not a signal.

CRT-LS (claim as stated, pooled bidirectional): 1,116 trades, **+0.001R @25bps**,
PF 1.00 — a coin flip. @4bps +0.253R, @50bps −0.299R. HOOD = +407.3R of +1.3R total.

**Verdict: FAIL** (pre-declared gate). Primary CRT-LONG expectancy −0.358R @25bps vs
+0.239R baseline; negative in dev and validation halves and in 2024 and 2025;
the perturbation fails too. The failure is structural twice over: (1) buying the close
back inside after a low sweep is anti-edge — 4H stocks that flush a prior candle's low
keep falling more often than they snap back; (2) the claim's stop geometry ("stop at the
sweep extreme") routinely puts the stop a few cents from entry (observed 5e-5 risk
fraction = $0.05 on a ~$95 HOOD bar), which sizes the position at up to 200× equity in
the canonical fixed-fractional framework — the ~100% maxDD is the verdict on the stop
geometry, and the expectancy is negative even setting that aside. No forward paper.
Sweep #1 (cap harami) and sweep #2 (PoC pullback) also FAILED; the stop-run reversal
family is now 0-for-3 on 4H.

**Why it failed (adverse evidence, preserved):** on 4H bars the sweep-and-close-back
is most often a pause inside a continuing move, not a reversal. The reel examples are
cherry-picked single candles; in the full 2023–2026 replay the failed auction continues
down ~54% of the time, and the TP1/runner structure of Mode B cannot rescue an entry
with negative drift. The ~495 ambiguous bars (both extremes swept) are also informative:
violent 4H bars that sweep both sides are continuation, not exhaustion.

Evidence: `run_crt.py` (frozen logic), `crt_results.json` (full numbers), this README.
