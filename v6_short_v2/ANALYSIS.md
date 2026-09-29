# V6 Short V2 — Two-track downside research: ANALYSIS

**Status:** RESEARCH ONLY. Local-only under `v6_short_v2/`. Nothing frozen was
modified, nothing was published, no forward test, no signals, no money.
Completed 2026-09-18.

**Question:** "Can you make a better short?" Two tracks were authorized:
- **Track A (autopsy):** v1 short setups + a *pre-specified* fast-failure exit
  (`SHORT_V2_SPEC.md`, written before any v2 code ran), tested on the 2022 bear
  market — a window the hypothesis never saw.
- **Track B (the real bet):** the *proven, unchanged* long framework
  (backtest.py's structural variant: +0.165R/trade reference) pointed at
  single-inverse ETFs SH and PSQ, on 4H 2y and on 2022.

---

## Track A results — 2022-01-01 → 2022-12-31, 4H, 17 stocks

| Metric | V2 (fast-fail) 2022 | V1 (2024–2026, ref) |
|---|---|---|
| Trades | 210 | 230 |
| Win rate | 40.5% | 35.2% |
| Expectancy | **−0.152% / −0.056R** per trade | −0.576% / −0.08R |
| Profit factor | 0.87 | 0.79 |
| Avg hold | 3.2 bars | — |
| Exit mix | fast-fail 187, stop 16, target 7 | — |
| $10k @1% risk → | **$8,468 (−15.3%)** | $7,746 (−22.5%) |
| Max drawdown | 19.2% | 40.5% |

Context: QQQ −33.2%, SPY −18.7% in 2022 — the friendliest possible regime for shorts.

**Verdict criteria** (pre-specified in `SHORT_V2_SPEC.md` §5): edge iff expectancy
> +0.1R/trade AND PF > 1.2 AND ≥30 trades. **Result: expectancy ≤ 0 → FAIL.**

**Verdict: this structural framework has no short edge, period.** The fast-fail
exit worked *mechanically* exactly as designed — it replaced slow −1R bleed-outs
(only 16 full stops) with fast thesis-invalidation covers (187/210 exits, 3.2-bar
avg hold) — but the winners never paid for it: only 7 covers hit the 2R target,
avg win +2.49% vs avg loss −1.95% at a 40.5% win rate. Cutting losers faster
cannot fix entries with no edge. In RISK-OFF (200/210 trades): −0.069R.

Per the spec's anti-overfit commitment, the setup split below is reported, not
acted on — there is no v3 fitted on 2022:
- S1_BREAKDOWN (116 trades): −0.168R — still the worst.
- S2_PULLBACK_SHORT (65): +0.054R — no longer catastrophic, still ~zero.
- S3_BULL_TRAP (29): +0.145R — best, but 29 trades is not a system.

Scope note: this kills *this framework's* shorts, not every conceivable short
system. But no further variants of this logic will be tested — the 2022 window
was spent exactly once, on exactly the pre-specified rule.

---

## Track B results — unchanged long framework on SH / PSQ

| Window | SH trades | PSQ trades | Pooled |
|---|---|---|---|
| W1: 4H, 2024-09-18 → 2026-09-17 | 0 | 0 | **0** |
| W2: daily 2022 (adaptation, labeled) | 0 | 0 | **0** |

Buy-and-hold context: W1 — SH −20.7%, PSQ −31.0% (bull-market bleed, expected);
W2 — SH +19.7%, PSQ +37.8% (the payoff regime). The framework captured none of it.

**Why zero — diagnosed, not guessed** (SH, 2022 daily; PSQ identical pattern):
the framework's buy-zone geometry is structurally incompatible with inverse ETFs.
14 would-be PULLBACK BUYs in 2022 printed with **score 100, protection SAFE,
above VWAP, ADX ≥ 20** — textbook setups in every respect — but price sat
**+0.5 to +1.3 ATR above EMA21** while the buy zone is **EMA21 ± 0.45 ATR**, so
all of them stuck at `entry=WATCH` ("near entry zone") instead of `YES`.
SH/PSQ uptrends grind; their pullbacks hold above the zone rather than tagging it.

Second, independent blocker (kept unchanged per the task, counted not overridden):
the framework's own rule downgrading `entry YES → WATCH` in RISK-OFF regimes
vetoes entries **exactly when inverse ETFs trend** (~6–13 vetoed per symbol per
window). Even with the veto removed, the zone geometry above would still leave
~zero signals.

**Verdict: the unchanged long framework cannot be pointed at inverse ETFs.**
This is not a data artifact and not a tuning invitation — it is what "unchanged"
means. Adapting it (wider zone for low-vol ETFs, rethought regime veto) would be
a new framework requiring its own spec, freeze, backtest, and forward test —
not a reuse.

---

## Data notes (so the numbers can be trusted)

- yfinance serves no intraday bars older than 730 days (verified empty); Stooq is
  JS-challenge-blocked. 2022 4H came from Dukascopy's free hourly feed
  (`data_2022.py`), resampled with the repo's own `scanner_rules.resample_closed_4h`.
- Universe 17/18: **META is absent from Dukascopy** — dropped and documented.
- Split status was **verified per split** against yfinance adjusted closes
  (ratio ≈1.0 pre/post for TSLA 3:1, AMZN 20:1, GOOGL 20:1 — Dukascopy histories
  are already split-adjusted; no-op correctly applied). Dividends unadjusted
  (negligible). Volume is CFD tick volume — only *relative* volume is ever used.
- Dukascopy hourly bars are hour-labeled in UTC; the 14:00 UTC (= 9:00 ET) bar
  falls outside the scanner's regular-session filter, so each day's first 4H bar
  is built from 10:00/11:00/12:00 ET bars. Minor OHLC difference vs
  yfinance-based bars; no lookahead.
- Track B W2 ran at **daily** resolution because no free keyless source has 2022
  hourly SH/PSQ (Dukascopy lacks inverse ETFs). Bar-count rules kept literal
  (30-bar hold = 30 trading days); verdict weight stays on W1 and its regime split.

## Files

- `SHORT_V2_SPEC.md` — pre-specified v2 hypothesis + verdict criteria (written before code)
- `data_2022.py` — Dukascopy 2022 pipeline (+ `cache/` pickles)
- `track_a_v2_autopsy.py` / `track_a_results.json` / `track_a_trades.csv`
- `track_b_inverse_etf.py` / `track_b_results.json` / `track_b_trades_w*.csv` (empty — zero trades)

---

## Recommendation (one)

**Stop trying to make the scanner short.** Track A failed its pre-specified
verdict in the friendliest regime shorts will ever see — the framework has no
short edge, and no variant of it will be tested further. Track B's cleaner idea
(long the inverse) is also dead *as a reuse*: the unchanged framework fires zero
signals on SH/PSQ because its 0.45-ATR buy zone and its own RISK-OFF entry veto
are structurally incompatible with inverse ETFs.

For downside exposure, skip scanner signals entirely: **defined-risk index puts
(SPY/QQQ) or a static inverse-ETF hedge allocation** — instruments that don't
need the scanner to work. A signal-driven inverse-ETF system would be a new
from-scratch research program with its own freeze/test discipline, and nothing
in this research justifies starting one.
