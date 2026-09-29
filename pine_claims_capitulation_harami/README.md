# Capitulation-candle harami reversal — weekly outside-claims sweep #1

**Date:** 2026-09-28 (weekly sweep, Mike-approved 2026-09-24). **Status:** research, local-only.
Modifies nothing frozen (V5.4, Mode B, production alerts, grades, market gate, AI Observer untouched).

**Origin:** @smart.forexpips Instagram reel, posted 2026-09-21 (https://www.instagram.com/reel/DdjHIT9jlBB/),
53K followers, 2.4K likes. The creator's claim, in his words: after a sharp downtrend, the **largest
red candle of the move** is capitulation — sellers exhausted. If the next candle is a small green
bullish harami **printed completely inside** that red candle ("the market catching its breath"), the
silence means sellers stopped pushing. **Enter long when price closes above the big red candle's
high, stop below its low, target the last swing high.**

## Pre-registration (frozen BEFORE running)

**Hypothesis.** A largest-range down candle in a sharp decline = capitulation; a fully-inside green
harami the next bar = absorption of selling; a close back above the capitulation high = trapped shorts
covering → a tradable 4H bounce.

**Mechanism (why it could be real).** Exhaustion/volatility-climax: the largest-range bar of a move
concentrates panic selling; an immediate inside bar shows supply was absorbed at that price; reclaiming
the climax bar's high forces the shorts that sold the climax to cover. This is the classic volatility-
climax/2-bar-reversal structure (turtle-soup family), stated precisely enough to be falsifiable.

**Why it qualifies.** (a) Precise rule definable on 4H bars (below). (b) Plausible mechanism
(capitulаtion + absorption + short-covering), not numerology. (c) Applies to 4H swing entries on the
14-stock watchlist. No data we lack. Not previously tested (breakout-retest was the Sep-24 study and
FAILED; this is an exhaustion reversal, a different family).

**Exact rule, pre-declared, no tuning:**
- Signal bar `i` (the "capitulation candle"):
  1. `close[i] < open[i]` (red candle).
  2. `high[i]-low[i] > max(high-low of bars i-10..i-1)` (largest range of the last 10 bars).
  3. `close[i] < close[i-10]` (sharp downtrend precondition, net decline over 10 bars).
- Harami bar `i+1`: `close[i+1] > open[i+1]` (green) AND `high[i+1] <= high[i]` AND `low[i+1] >= low[i]`
  (prints entirely inside the prior bar's range — matches the reel).
- Trigger bar `i+2`: **enter long at close[i+2] iff close[i+2] > high[i]**. If the trigger bar does
  not close above the capitulation high, the setup expires — no trade. (The reel: "enter long when
  price closes above the red candle's high".)
- Stop = `low[i]` (the reel: "place stop loss below the red candle's low").
- **Exits: canonical Mode B**, mirrored bar-for-bar from `gen_pine_trades` (TP1 limit intrabar,
  +1R Profit Protect arms runner trail at `close − atr·TRAIL_ATR`, close-evaluated exits filled at
  next-bar open, stop wins ties, EMA55 / EMA200-trend exits). The reel's "target the last swing high"
  is NOT used — exits are the canonical engine's; that keeps the test about the ENTRY.
- **Adaptation (stated, not hidden):** the claim defines risk as `entry − low[i]` instead of the
  canonical `1.5·ATR` stop. TP1 preserves the canonical Mode B TP1:R multiple:
  `TP1 = entry + (entry − stop) × (TP_ATR/SL_ATR) = entry + 1.333·risk`.
- One position per symbol at a time; new setups while in a trade are ignored; one trigger bar only.
- Requires `i ≥ WARMUP+10` and `i+2 ≤ n-2` (trigger bar must be manageable).

**Test plan.**
- Universe: 14-stock watchlist (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM, SPCX, ASTX, BBAI, NIO,
  HOOD, AMD). 4H bars, Oct 2023 → Sep 2026 (same cache as prior studies).
- BASE: standard Hybrid `pine_buy_signal` + `gen_pine_trades`, **rerun in-study** (never reuse numbers
  across studies). Expected ≈237 trades, +0.239R @25bps.
- `pine_backtest.py` imported UNMODIFIED; signal/exit mechanics mirrored from the canonical engine.
- Costs: 25/50/75/100 bps (`pb.COSTS`), portfolio `simulate_portfolio` @1% risk.
- Splits: development Oct 2023–Dec 2024 vs validation Jan 2025–Sep 2026; per-year breakdown;
  per-symbol concentration; top-1/3 symbol R-share.

**Success gate (pre-declared):**
- **PASS:** pooled expectancy ≥ +0.35R @25bps AND ≥ 60 trades AND validation-half (2025→Sep 2026)
  expectancy > 0 AND @50bps expectancy ≥ +0.15R AND no single symbol contributes > 40% of total net R.
- **MAYBE:** expectancy @25bps beats the in-study baseline with ≥ 40 trades, but fails ≥ 1 robustness
  dimension (concentration / a year / validation / cost stress).
- **FAIL:** expectancy @25bps ≤ in-study baseline, or negative, or < 40 trades (too thin to mean
  anything).

## Results (2026-09-28)

BASE (in-study rerun): 237 trades, win 50.6%, exp **+0.239R @25bps**, PF 1.38, maxDD 21.63% —
reproduces the canonical 4H Hybrid baseline exactly; comparison is valid.

CAP_HARAMI (pooled, 14 names):

| Cost | Trades | Win% | Expectancy | PF | MaxDD |
|---|---|---|---|---|---|
| 4bps | 15 | 40.0 | −0.01R | 0.97 | 3.9% |
| 25bps | 15 | 33.3 | **−0.049R** | 0.86 | 4.3% |
| 50bps | 15 | 33.3 | −0.095R | 0.76 | 4.7% |
| 100bps | 15 | 33.3 | −0.187R | 0.59 | 5.5% |

Attribution: 348 capitulation candles → 114 haramis (32.8% of capitulations print an
inside-green bar) → 15 triggers (13.2%), 99 expired (86.8% never close back above the
capitulation high on the trigger bar).
Year splits (25bps): dev 2023–24 n=2, −0.78R; val 2025–26 n=13, +0.06R. By year: 2024
n=2 −0.78R; 2025 n=11 +0.08R; 2026 n=2 −0.04R. Per-ticker: only HOOD (3, +0.92R) and
AMD (3, +0.59R) positive; QQQ/PLTR/ANET all negative.

**Verdict: FAIL** (pre-declared gate). Expectancy −0.049R @25bps vs baseline +0.239R;
sample too thin (15 trades) to mean anything, and 40% of trades sit in two names.
The failure point is structural: after a capitulation candle and an inside harami, price
closes back above the capitulation high on the next bar only ~13% of the time — the
reclaim the reel's entry depends on almost never comes. 4H stocks keep falling after
capitulation instead of snapping back (no V-shaped short squeeze on this timeframe).
