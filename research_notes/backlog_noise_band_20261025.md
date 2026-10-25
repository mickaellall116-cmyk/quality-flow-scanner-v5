# Backlog note — "Noise Band" intraday breakout (PARKED, note-only)

Filed 2026-10-25. Status: **PARKED — backlog note only. No test lane, no build, no Quality Flow diversion.**

## The concept (3 lines)

Intraday index strategy from a creator video Mike surfaced: after the New York open, draw a band around the morning chop ("noise"), do nothing inside it, trade the breakout of the band, ride toward the close, exit flat before the day ends.
It belongs to a legitimate family — volatility-filtered opening-range breakout, Crabel lineage.
Creator claims: selected from 50 paper strategies (49 "failed"), beat random entries, 6 blind walk-forwards positive overall, tick-level MetaTrader test on Nasdaq/S&P since 2018 ($10k → $150k), ~50% win rate, one 30% drawdown; full code offered in his channel.

## Muse's verdict

The family is real and the result shape (half the trades lose, a 30% drawdown, "not smooth") is what genuine intraday trend capture looks like — unlike typical guru fabrications. But the evidence is unverifiable as presented: no costs/spread/slippage stated (decisive for intraday index trading), MetaTrader index ticks are CFD feed data rather than exchange data, returns are unaudited and come from the seller, and "1 of 50 survived" is itself a multiple-testing artefact until the other 49 are inspectable. The band is never defined (width basis, window, stop), so no testable spec exists yet. Fit cost is high: intraday indices are a different animal from our 4H equity stack — minute-level data qualification would be a new build of the same kind just finished for 4H, and none of the measurement stack transfers directly. Lean: learning note in the backlog, no chase now.

## ChatGPT's verdict (Slack TS 1792956749.263479, governing)

**Note-only backlog; do not divert Quality Flow or open a new test lane now.** Opening-range/noise-band breakout is a legitimate strategy family, but the claims supplied are not decision-grade and do not transfer evidence to the 4H equity system. Until the current BUY/EXIT protocol is frozen and tested, this stays parked.

## Evidence that would justify a later preregistered look (ChatGPT's list)

- Exact executable code and immutable parameter/spec table (band window/width, instrument/session/timezone, entry, stop, sizing, exit).
- The complete 50-strategy selection ledger and selection rule, not only the survivor.
- Raw feed/vendor/instrument identity (cash index, futures, ETF or CFD), timestamps and corporate/session treatment.
- Pessimistic commission/spread/slippage/latency assumptions and turnover.
- Trade-level ledger, equity curve, exposure and drawdown, with all six walk-forward boundaries fixed in advance.
- Source data hashes, runnable reproduction script, and independent rerun.
- Comparison against simple opening-range and random-entry baselines under identical risk/costs.

## Revival condition

If that evidence ever arrives, the first action is a **source/evidence audit only** — no data purchase, no backtest, no optimization, no Quality Flow integration. Nothing here authorizes a build.
