# SIGNAL_QUALITY_SPEC.md — Final signal-quality study on Pine V3.6 (2026-09-18)

FROZEN. Written before any backtest was run. No definition changes after results.
Any deviation is documented as a protocol violation, not a silent edit.

## Goal
Test whether adding GENUINELY NEW information at entry improves the existing 4H
breakout signal. NOT loosening V3.6, NOT retuning parameters, NOT revisiting exits —
those paths were tested and mostly overfit the bull market.

## AMENDMENT A (2026-09-18, before any backtest was run)
Benchmark bars are DAILY, not 1h. Reason: Yahoo Finance restricts 1h bars to the
last 730 days, which cannot cover the research window start (2024-09-16) or the
2022 validation window. Mike's brief explicitly permits daily with documentation.
The approximation: benchmark return over the symbol's prior-20-4H-bar calendar
span is measured with daily closes (last daily bar ≤ each span endpoint) instead
of 1h closes. For a ~10-trading-day RS window this changes results only at day
granularity; the filter definition (strict outperformance vs SPY, QQQ, sector)
is unchanged. bench_ret() in pine_signal_quality.py implements the daily lookup.

## Control (unchanged V3.6)
- `pine_backtest.pine_buy_signal` (Hybrid), bar-for-bar fidelity verified.
- UX51, 4H, 2024-09-16 → 2026-09-14. Exits byte-identical to baseline Pine exits.
- $10k start, 1% risk/trade, max 5 concurrent positions, 4bps + 25bps cost legs,
  next-bar-open entries, stop-first on same-bar ambiguity, gap-below-stop skip.
- Sanity gate: control rerun must reproduce ~263 trades, +0.195R @4bps.

## Hypotheses — each tested FIRST as an additional AND-filter on top of the
unchanged V3.6 signal. Evaluated at signal bar i. No lookahead. No threshold
tuning after the fact. One definition each, pre-registered below.

### H1 — RELATIVE STRENGTH
Do V3.6 signals perform better when the stock is outperforming SPY/QQQ (and,
where practical, its sector ETF) before the breakout?

- RS window: the symbol's prior 20 4H bars. t1 = timestamp of signal bar i,
  t0 = timestamp of bar i−20.
- sym_ret = Close_i / Close_{i−20} − 1.
- Benchmark return for B in {SPY, QQQ, sectorETF}, measured over the SAME
  calendar span: bench_ret(B) = C1 / C0 − 1, where C1 = close of the last B 1h
  bar with timestamp ≤ t1, C0 = close of the last B 1h bar with timestamp ≤ t0.
  span endpoint) — see Amendment A. (Benchmark data: daily bars, downloaded once,
  cached. If B has no bar ≤ t0,
  the filter FAILS for that signal — conservative, no signal rather than a guess.)
- Why daily instead of 4H/1h: Yahoo restricts intraday bars to the last 730 days,
  which cannot cover the research window or 2022 (Amendment A). Daily closes give
  exact signal-time alignment via last-bar-≤-timestamp lookup across 24/7 crypto
  grids and session-only equity grids without resampling; documented here.
- Why 20 bars: ~10 trading days on the equity 4H grid — one simple, defensible
  momentum window. NOT optimized.
- Sector ETF (best effort, "where practical"): one attempt per stock symbol via
  yfinance GICS sector → fixed map:
  Technology→XLK, Financial Services→XLF, Healthcare→XLV, Energy→XLE,
  Industrials→XLI, Consumer Defensive→XLP, Utilities→XLU, Consumer Cyclical→XLY,
  Communication Services→XLC, Real Estate→XLRE, Basic Materials→XLB.
  The sector mapping that results is frozen at setup and saved in the results.
  Crypto spot symbols (BTC-USD, ETH-USD, SOL-USD, DOGE-USD, AVAX-USD, LINK-USD,
  XRP-USD) and symbols that ARE ETFs (SPY, IWM, SMH, ARKK, XLF): sector
  comparison not practical → SPY+QQQ only, documented per symbol.
- H1 PASSES iff sym_ret > spy_ret AND sym_ret > qqq_ret
  AND (no sector ETF mapped OR sym_ret > sector_ret).
  Strict >. No margin. No lookback optimization.

### H2 — VOLATILITY CONTRACTION
Do signals emerging from a clear contraction phase beat ordinary V3.6 breakouts?

- H2 PASSES iff atr_ratio < 1.0 at signal bar i,
  where atr_ratio = ATR14 / SMA(ATR14, 50) — the exact series V3.6 already
  computes. Threshold 1.0 pre-registered. No tuning.
- New-information note: V3.6 measures volatility LEVEL (hard floor atr_ratio >
  0.85 in strong_trend; atr_ratio > 1 is one of five score points). H2 measures
  the compression STATE — volatility contracting into the breakout. Partial
  overlap with the score bonus is acknowledged; the filter (squeeze state) is
  not measured by any existing V3.6 component.

### H3 — BREAKOUT BASE QUALITY (tight base)
Does the structure immediately before the breakout matter?

- base_hi = max(High[i−10 : i]), base_lo = min(Low[i−10 : i]) — the same 10-bar
  window the V3.6 breakout condition itself uses.
- base_range = base_hi − base_lo.
- H3 PASSES iff base_range < 2.0 × ATR14_i. Multiplier 2.0 pre-registered.
  No tuning.
- Rationale: a breakout from a genuinely tight multi-bar base vs breaking a
  high inside a wide, sloppy range. New information: no V3.6 component measures
  base tightness (the hot guard measures extension from EMA9, not the range of
  the base).

## Metrics per hypothesis (4bps primary judgement, 25bps reported)
trades, win rate %, expectancy (R/trade), profit factor, total return %,
max drawdown %, avg winner (R), avg loser (R), stop-out %, TP1 hit %,
average hold (bars), trade reduction % vs control.
Judged on expectancy and robustness — NEVER on win rate alone.
Main question: does the new information improve expectancy and/or drawdown
enough to justify taking fewer trades?

## Candidate freeze — MAXIMUM 2
A hypothesis becomes a frozen candidate iff ALL of the following hold on the
research window @4bps:
(a) expectancy ≥ +0.225R (control +0.195R plus a +0.03R materiality margin);
(b) maxDD ≤ 40% AND no worse than control DD + 5pp;
(c) ≥ 60 trades (stability floor; ≥ 100 preferred);
(d) adds genuinely new information, not duplicating an existing V3.6 filter
    (judged in the writeup against: ADX, EMA alignment, volume filter,
    hot guard, score gate, breakout requirement).
No combinations of hypotheses (anti combinatorial creep). Frozen definitions
written to results JSON BEFORE touching 2022 data.

## 2022 validation (bear market)
- Data: union of v6_short_v2/cache/d4h_2022_*.pkl and
  pine_exit_fix/cache_2022/d4h_2022_*.pkl (32 symbols) + the same cached 1h
  benchmark data for H1.
- Run CONTROL and the frozen candidates ONLY. Same conventions, same exits.
- Adoption bar — ALL required:
  (i) research-window criteria (a)–(d) met;
  (ii) 2022 expectancy @4bps > 0;
  (iii) 2022 expectancy ≥ (control 2022 expectancy) − 0.05R;
  (iv) 2022 maxDD ≤ 45% and ≤ (control 2022 DD) + 10pp.
- An adopted feature is reported as a CANDIDATE for Mike to decide —
  NOT a recommendation to change his live TradingView script.
- If no candidate is adopted: verdict = "V3.6 signal research is exhausted."
  No fourth hypothesis. Ever.
