# V6 Short Research — SHORT_SPEC.md

**Status:** RESEARCH ONLY. Written 2026-09-17, before any code.
**Purpose:** Define structural SHORT setups as the mirror of the V5.4 long framework,
then backtest them over 2 years of 4H bars to answer one question honestly:
*does short edge exist in this framework, or does the long-term upward drift kill it?*

Nothing in this track modifies any frozen file. All state lives in
`v6_short_research/`. No signals surface to the user. No real money, ever,
until (a) this research shows edge AND (b) the V5.4 long forward test reaches
its verdict (~50-signal interim late Oct 2026 / ~100-signal verdict late Nov 2026).

---

## 1. What the long framework does (reference, not copied)

V5.4 long logic, frozen 2026-09-15:
- Structural candidate: `entry == "YES"`, `protection == "SAFE"`,
  `state in {"BUY", "PULLBACK BUY"}`, `above_vwap is True`, price inside buy zone.
- Hard gate: ADX >= 20 (momentum filter).
- Live gates (backtested ex-15m): market gate CONFIRM, rel vol, R:R >= 2, MTF alignment.
- Entry: next-bar open. Stop: scanner stop (structure − ATR buffer). Target: TP1.
- Stop wins same-bar ties. 4 bps round-trip costs. 1 position/symbol. 30-bar max hold.

The short system mirrors the *structure* of this approach. It does not reuse
`classify_symbol` (long-specific); all short logic below is fresh.

## 2. Short setups (3)

All signals are evaluated on **closed 4H bars only**. Entry is at the **next bar's open**.
Indicator math is reused read-only from `masterscanner_api.add_indicators`
(EMA9/21/55/200, ATR, ADX, VOL_BASE, VWAP) so the short research speaks the same
indicator language as the long framework.

Shared hard gates (mirror of V5.4):
- **ADX >= 20** — same momentum filter, both directions.
- **Close below VWAP** — mirror of the long `above_vwap` requirement.
- **Close below EMA21** — short-term downtrend structure (mirror of the long
  framework's implicit uptrend posture).

### Setup S1 — BREAKDOWN (mirror of BUY)
A momentum breakdown through support.
- `support` = lowest Low of the prior 20 bars (bars i−20 … i−1).
- Signal bar i: `Close[i] < support` (breakdown close), plus shared gates above,
  plus `Volume[i] > VOL_BASE[i]` (breakdown on expanding volume — mirror of the
  long rel-vol gate).
- Stop = `High[i] + 0.5 × ATR[i]` (breakdown-bar high + buffer — mirror of the
  long `trade_levels` stop = zone_low − ATR × buffer).
- Cover target = entry − 2 × risk (exactly 2R — the R:R>=2 long gate, by construction).

### Setup S2 — PULLBACK SHORT (mirror of PULLBACK BUY)
The highest-probability short in classical technical analysis: short the retest
of broken support turned resistance.
- A BREAKDOWN signal (S1) fired within the last 15 bars. Its zone is
  `[zone_low = broken support, zone_high = breakdown-bar high]`.
- Signal bar i: price rallied back into the zone (`High[i] >= zone_low`) AND
  shows rejection: `Close[i] < zone_low`, or an upper wick
  (`High[i] − max(Open[i], Close[i]) > 0.5 × ATR[i]`) with `Close[i] < Open[i]`.
- Shared gates (ADX>=20, below VWAP, below EMA21).
- Stop = `zone_high + 0.5 × ATR[i]`. Cover target = 2R.

### Setup S3 — BULL TRAP (failed upside breakout)
- `res` = highest High of bars i−23 … i−4 (resistance, excluding the last 3 bars).
- Within bars i−3 … i−1, price broke above `res` (`High > res` on at least one bar).
- Signal bar i: `Close[i] < res` (failed breakout — closed back below), plus shared gates.
- Stop = `max(High[i−3 … i]) + 0.5 × ATR[i]`. Cover target = 2R.

**Priority** if multiple setups fire on the same bar: S2 > S3 > S1
(pullback-into-resistance is theoretically the best risk/reward; documented
assumption, not a proven ranking).

## 3. Trade management (mirror of long backtest)

- **Entry:** next-bar open after the signal bar closes.
- **Skip:** if next-bar open >= stop (adverse gap through the stop) → no trade.
  If next-bar open <= target (gap beyond target) → record as instant cover at open.
- **Exits:** stop (structure + 0.5 ATR buffer), full cover at 2R target,
  30-bar maximum hold (cover at close). **Stop wins same-bar ties** (conservative,
  same convention as the long backtest).
- **No scanner-EXIT early exit** in v1. The long backtest used scanner state flips;
  there is no short scanner yet. Documented limitation: a trend-flip cover rule
  (e.g. close back above EMA55 with EMA21 > EMA55) is a candidate v2 exit.
- **1 position per symbol.** After a position closes at bar j, scanning resumes at j+1.
- **Costs:** 4 bps round trip (same as long backtest) PLUS borrow cost:
  **1% annualized, accrued per trading day held** (`0.01 × entry_value × days_held / 252`,
  subtracted from P&L). This is an **approximation** — real borrow rates vary by
  symbol and day; 1% is representative for liquid large caps in normal conditions
  and is deliberately conservative-vs-zero but optimistic-vs-stressed. Hard-to-borrow
  names are excluded from the universe (see §5), which is what makes 1% defensible.

## 4. Market-regime handling — measure, don't filter

The long backtest ran variants (full gates vs structural-only). For shorts, the
central open question is *"do shorts only work when the market is falling?"*
Filtering by regime up front would beg that question. So:

- **No market-gate filter on entries.** Every structural short signal is taken.
- Each trade is **tagged** with the broad market regime at entry, using the
  repo's existing QQQ-based regime logic (copied verbatim from `backtest.py`'s
  `regime_at`: RISK-ON / CAUTIOUS / RISK-OFF from EMA score + session gate).
- Results are reported **split by regime**. The verdict section must answer the
  regime question from the numbers.

## 5. Universe — 18 liquid large caps

NVDA, AAPL, MSFT, META, AMD, AVGO, TSLA, PLTR, NFLX, CRM, ORCL, JPM, XOM, LLY,
COST, GOOGL, AMZN, WMT.

Selection rationale: mega/large-cap, high daily volume, easy to borrow
(typical borrow rates well under 1%). **Explicitly excluded:** meme/hard-to-borrow
names (GME, AMC, DJT), crypto spot pairs, leveraged/inverse ETFs. If a symbol has
no 4H data it is dropped and documented — never substituted silently.

## 6. Backtest mechanics

- **Data:** 2 years of 4H bars via the repo's `masterscanner_api.download_data`
  (yfinance), same source as the long backtest. Warmup 215 bars
  (> EMA200 + 5, same as long test) so indicators are settled.
- **Point-in-time:** every signal uses only bars ≤ i. Indicators are causal
  (EMA/ADX/ATR/VWAP); rolling-window levels (20-bar support) are computed with
  windows ending at i−1. No lookahead by construction.
- **Regime series:** QQQ + SPY 4H, same `regime_at` replication as `backtest.py`.
- **Metrics:** expectancy per trade (R and %), win rate, profit factor,
  max drawdown at 1%-risk-per-trade equity, avg hold, exit-reason mix,
  per-symbol and per-regime splits. Same `summarize()` shape as the long
  backtest for comparability.

## 7. Documented assumptions & limitations

1. Borrow at flat 1% annualized is an approximation (§3).
2. No early trend-flip cover rule in v1 (see §3).
3. yfinance data is dividend/split-adjusted; corporate-action edge cases ignored.
4. Survivorship: universe is today's large caps (same limitation as the long backtest).
5. 4H bars are session-derived; overnight gaps are captured via next-bar-open entries.
6. Setup priority S2 > S3 > S1 is a prior, not a finding.
7. The regime tag uses QQQ as the market proxy (same as the long backtest).
8. Sample size: expect far fewer short signals than the long test's 76 structural
   trades — short setups are rarer in a 2-year window that includes a strong bull
   market. Small-sample honesty applies to the verdict.

## 8. Verdict criteria (written before seeing results)

- **Edge exists** if: expectancy > +0.1R per trade with profit factor > 1.2,
  across at least 30 trades, AND the regime split shows shorts working in at
  least CAUTIOUS/RISK-OFF (not only in deep RISK-OFF, which would make the
  system a rare-regime toy).
- **No edge** if: expectancy ≤ 0, or positive expectancy rests entirely on a
  handful of trades, or shorts lose money in RISK-ON/CAUTIOUS badly enough that
  the unconditional system is untradable.
- Either way, the numbers go in `short_backtest_results.json` unedited.
