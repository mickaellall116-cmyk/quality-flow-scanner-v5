# Gamma exposure (GEX) — mechanics note for the backlog

Source: Instagram reel by @nickelninjatrades (Nick Ireland), 2026-10-12 — a sales
pitch for his "Gamma Exposure University." Mike asked if we can learn from it.
The mechanics below are public knowledge; no course needed. Written plain on
purpose.

## The idea in one breath

Options dealers have to hedge. When lots of options sit at one strike price,
the dealers' hedging buys and sells push the stock around at that price. If you
add up all that hedging pressure across every strike, you get a map of prices
where the stock tends to stick, bounce, or break through fast. That map is the
gamma exposure (GEX) profile.

## How it works

- Every option has a "gamma": how fast its hedge needs to change as the stock
  moves. Multiply gamma by open interest at each strike and you get the hedging
  pressure dealers face at that price.
- **Positive gamma zone** (dealers long gamma): dealers sell into rallies and
  buy dips to stay hedged. That fights the move — price gets pinned, ranges
  shrink, big levels hold like walls.
- **Negative gamma zone** (dealers short gamma): dealers buy into rallies and
  sell into drops. That feeds the move — price accelerates through levels,
  ranges expand, stops cascade.
- The price where it flips (the "gamma flip" / zero-gamma level) is treated as
  the day's regime line: above it, expect calm/pinning; below it, expect
  follow-through.
- Biggest strikes by open interest act as magnets (pinning into expiry) and as
  support/resistance — not because of chart lines, but because real hedging
  money has to transact there.

## The reel's entry rule (the part with discipline value)

Trade only when three things line up, otherwise walk away:
1. EMA stack (trend agrees),
2. a flag pattern (a pause after a move),
3. volume expansion (participation confirms).

Filter, not prediction: "read the map, take only the setups that line up."

## What it would take for us

- **Live use:** a current options chain feed (strikes, open interest, Greeks)
  for our tickers — computable into a daily GEX map with public formulas.
- **Backtesting:** historical options chains as they were seen at the time.
  We do not have that data, and it is the same wall that already parks the
  "unusual options activity / money flow as entry filter" candidate: no
  PIT-clean options history, no honest test.
- **Timeframe if ever tested:** GEX is a daily/intraday market-structure
  input. For us it could only be a filter or grade input on the existing
  entries (e.g., no longs below the flip in negative gamma), never a
  standalone signal — and only after the PIT audit passes.

## Status

PARKED, 2026-10-12, next to the options-flow candidate in the post-verdict
backlog (~100-signal verdict, late Nov 2026). No test authorized, no data
purchased, no course. Learning the mechanics is done — this note is the
learning. Using it waits on an options data route we do not currently have.

— Muse, 2026-10-12
