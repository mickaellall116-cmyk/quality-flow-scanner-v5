# Pine V3.6 exit-ablation — analysis

**Question:** how much of the baseline +0.195R/trade comes from the EXIT logic vs the entries?

**Method:** entries byte-identical across variants (same Hybrid signals, entry
prices, gap-skip rule, UX51, 4H bars, 4/25bps costs, $10k / 1%-risk / max-5
portfolio). Only exits change. R is denominated in the structural stop in all
variants, so units are directly comparable.

## Results (4bps; 25bps ordering identical)

| Variant | Trades | Win% | Exp (R) | PF | Ret% | MaxDD% | Hold |
|---|---|---|---|---|---|---|---|
| baseline: Pine entries + Pine exits | 263 | 44.9 | **+0.195** | 1.27 | +35.3 | 35.2 | 18.1 |
| time20: entries + fixed 20-bar exit, no stop/TP1/trail | 277 | 49.8 | **+0.329** | 1.39 | +37.1 | 35.0 | 20.0 |
| stop_tp1: entries + stop & 50%-TP1 only, 30-bar cap | 272 | 43.4 | **+0.125** | 1.18 | +31.6 | 23.9 | 17.6 |

Baseline reproduced the published result exactly (sanity check passed).

## Decomposition of the +0.195R

- **Entries + dumb 20-bar hold: +0.329R.** The entries carry the entire edge — and then some.
- **Full Pine exit stack vs dumb: 0.195 − 0.329 = −0.134R.** The exit logic, on net, *destroys* value relative to doing nothing.
- **Stop + 50%-TP1 skeleton vs dumb: 0.125 − 0.329 = −0.204R.** The structural stop is the main culprit — it cuts winners that later recover (same theme as the MasterScanner counterfactual where ignoring early EXITs added +17.3pp).
- **Trail + EMA55/bear exits vs the naked skeleton: 0.195 − 0.125 = +0.070R.** The active trade management partially redeems itself — it is better than a naked stop, just not better than no stop at all.

## Nuance: expectancy isn't everything

- The stop buys drawdown control: stop_tp1 max DD is **23.9%** vs 35.2% baseline. The stop trades expectancy for smoothness.
- time20 has **no per-trade loss cap** — a single trade can lose multiples of 1R (−5R = −5% of portfolio at 1% risk sizing). Fatter left tail per trade; the expectancy comparison doesn't capture that.
- Trade counts differ slightly (263/277/272): one-position-per-symbol means exit timing shifts subsequent entry availability. Entry LOGIC is identical; this is the honest economic measure.

## Verdict

**The edge lives in the entries, not the exits.** Mike's entries are worth
+0.329R/trade on their own — genuinely good. The exit stack costs −0.134R
relative to a brain-dead hold, with the structural stop doing most of the
damage and the trailing/EMA55 management recovering about half of it
(+0.070R). The exits are risk management (they do cut drawdown), not profit
drivers.

**Do NOT read this as "remove the stop."** That would be fitting the
two-year sample and ignoring tail risk — one uncapped trade in a real crash
is how accounts die. The correct takeaway: entries are the alpha; exits are
overhead that buys sleep. Any future exit work should be judged on whether
it preserves the +0.329R entry edge while taming the left tail — not on
squeezing more R out of exits.

Caveats: Python reimplementation approximations (documented in
pine_backtest.py); 2-year bull-market window; UX51 universe only.
