# V6 Short V2 — Fast-Failure Exit Spec (Track A autopsy)

**Status:** RESEARCH ONLY. Written 2026-09-18, **before any v2 backtest code runs.**
**Purpose:** Pre-specify one mechanical v2 exit hypothesis for the v1 short setups,
then test it on a window it was NOT fitted on (2022 bear market). If it fails
there, the verdict is: this framework has no short edge, period.

Nothing in this track modifies any frozen file. All state lives in
`v6_short_v2/`. No signals surface to the user. No real money, ever.

---

## 1. What v1 showed (motivation, not a fitting exercise)

V1 (mirror of the long framework, 2024-09-16→2026-09-14, 18 liquid large caps):
230 trades, 35.2% win, **−0.576% / −0.08R per trade**, PF 0.79, max DD 40.5%
at 1% risk. Reference long backtest same window: +11.3%, +0.165R, PF 1.41.

Two observations from the v1 autopsy motivate v2 (they are the *reason* for the
hypothesis, not parameters to fit):
1. **−1R stop-outs dominated the losses.** Losers routinely rode the full
   structural stop while the thesis was already dead.
2. **In RISK-OFF, breakdown signals fired at maximum fear** (Apr-2025 tariff
   bottoms: NVDA @98.75, MSFT @358, META @514) right before V-shaped recoveries.
   The position stayed short into the reclaim instead of covering when the
   breakdown failed.

## 2. The v2 hypothesis (one sentence)

*Shorts lose because they ride dead theses to the full stop; covering
mechanically when the breakdown thesis is invalidated cuts the left tail
without needing better entries.*

## 3. V2 fast-failure exit rule (mechanical, pre-specified)

Setups S1/S2/S3 and entries are **identical to v1** (`SHORT_SPEC.md` §2):
same shared gates (ADX≥20, close < VWAP, close < EMA21), same signal logic,
same priority (S2 > S3 > S1), same next-bar-open entry and skip rules.

**Breakdown level** (thesis line), defined per setup at signal time:
- S1_BREAKDOWN → the broken `support` (20-bar lowest low)
- S2_PULLBACK_SHORT → `zone_low` (the broken support of the originating S1)
- S3_BULL_TRAP → `res` (the resistance that failed)

**Fast-fail cover rule.** After entry, on every closed 4H bar `j`
(`j` > entry bar), evaluate at the close:
- if `Close[j] >= breakdown_level` **OR** `Close[j] > VWAP[j]`
- → cover the full position at `Open[j+1]` ("fast-fail cover").

Rationale for the VWAP leg, stated before testing: entry requires
close < VWAP (the downtrend thesis). A close back above VWAP invalidates that
thesis exactly as reclaiming the breakdown level does. Either invalidation
fires the cover; whichever condition is met first on a closed bar governs.

**Precedence (unchanged conservatism):**
1. The structural stop is checked intrabar on every bar — **stop wins all ties**,
   same as v1. A fast-fail condition observed at bar j's close never overrides a
   stop hit during bar j (the stop already filled).
2. The 2R cover target is unchanged (full cover at target).
3. 30-bar maximum hold unchanged (cover at close).
4. Costs unchanged: 4 bps round trip + 1% annualized borrow over trading days held.
5. 1 position per symbol; scanning resumes the bar after a position closes.

What v2 does NOT add (deliberately): no scanner-EXIT analog, no EMA-trend-flip
rule, no partial covers, no breakeven move, no parameter search. One rule,
stated here, tested once.

## 4. Test design — out-of-sample for the hypothesis

- **Window:** 2022-01-01 → 2022-12-31, 4H bars (SPY −19.4% that year — the
  regime where shorts *should* work if they ever do).
- **Universe:** the same 18 liquid large caps as v1 (NVDA, AAPL, MSFT, META,
  AMD, AVGO, TSLA, PLTR, NFLX, CRM, ORCL, JPM, XOM, LLY, COST, GOOGL, AMZN, WMT).
- **Point-in-time:** signals on closed 4H bars only, next-bar-open entries,
  same warmup (215 bars) and indicator code as v1.
- **Regime:** tagged, not filtered (QQQ-based regime_at, verbatim copy) —
  reported split by regime, same as v1.
- **Out-of-sample claim:** the v2 rule was motivated by v1's 2024–2026
  *loss pattern*, but no v2 parameter was chosen using 2022 data (there are no
  parameters — the levels are the setup's own structural levels). 2022 is a
  different market window the rule has never seen.

## 5. Verdict criteria (written before seeing results)

- **V2 shows short edge** if ALL hold: expectancy > **+0.1R per trade**,
  profit factor > **1.2**, at least **30 trades**.
- **No short edge** if expectancy ≤ 0, or positive expectancy rests on a
  handful of trades, or the system is untradable outside deep RISK-OFF.
- **If v2 fails in 2022** — a sustained bear market, the friendliest possible
  regime for shorts — the verdict is: **this structural framework has no short
  edge, period.** (Scope note: this kills *this framework's* shorts, not every
  conceivable short system. Alternatives like long-inverse-ETF exposure are a
  separate track, not a rescue of this one.)
- **Anti-overfit commitment:** if v2 fails, there is no v3 fitted on 2022.
  The 2022 window gets spent exactly once, on exactly this rule.

## 6. Metrics (same shape as v1 for comparability)

Trade count, win rate, expectancy (% and R per trade), profit factor, max
drawdown at 1% risk/trade ($10k start), avg hold bars, exit-reason mix
(stop / target / fast-fail / time), per-symbol and per-regime splits,
borrow cost per trade. Results go into `track_a_results.json` unedited.
