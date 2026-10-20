# Idea intake — TradingView MCP + Claude workflow (@hypertech carousel, 2026-10-18)

Source: instagram.com/p/Deo-s4RESdY/ (@hypertech, 1.4M followers, posted 2026-10-18).
Mike sent 2026-10-20 and directed: "Brain storm with chat on if this can help us."

## What the post actually is
A promotional carousel for a guide: connect Claude to TradingView via a local MCP
bridge so Claude can analyse charts, generate Pine Script, run backtests (incl.
replay), spot opportunities, and run scanner templates from prompts.

Evidence quality: marketing. Deck shows a portfolio animation $288K -> $408K, a
"CLAUDE FABLE 5 - MIROFISH" dashboard (x80 multipliers), and a tweet screenshot
(@lisaknowsai) claiming +$4,780 THEORETICAL profit / 83% hit rate on BTC futures.
No costs, no OOS, no methodology. The caption itself warns AI strategies overfit.
MiroFish was previously adjudicated on this desk: PARK / IDEA ONLY.

## The salvageable core (workflow, not edge)
A TradingView MCP bridge is a real tooling pattern. Candidate uses for OUR program,
to be judged against the actual bottleneck list (data quality / PIT access, feed
reliability, validation throughput — NOT Pine iteration speed):
1. Pine iteration loop: faster drafting/refactoring of Pine indicators with the
   model driving TradingView directly, vs manual paste-compile cycles.
2. Cross-engine parity spot-checks: our standing rule is the Python build is the
   comparator and TradingView Strategy Tester results are NOT execution-realistic
   (V3.7 freeze). Could an MCP-driven TradingView serve as an independent
   candle/signal cross-check for parity audits (cf. the 2026-10-03 parity gate)?
3. Scanner-template prototyping for RESEARCH lanes only (frozen systems untouched).
4. Replay-based eyeball review of specific historical bars during audits.

## Hard constraints for the brainstorm
- Nothing touches the frozen systems (V5.4 paused, V3.7 frozen) or production.
- Any new data path inherits the full qualification burden (PIT audit, parity
  vs qualified sources). TradingView data via MCP is a vendor path, not a free pass.
- Cost/account questions are real: TradingView plan tier, MCP server provenance
  (third-party code with account access = security review), desktop-app dependency.
- Simulated/theoretical numbers in the deck count for zero.

## Ask of ChatGPT (brainstorm, then converge)
- Which of 1-4 (or others) genuinely relieve a bottleneck we actually have?
- What would a bounded, offline-first evaluation look like (no account linking
  until the evaluation says the workflow clears a stated bar)?
- Kill criteria: what result ends this as PARK like MiroFish?

Status: INTAKE — brainstorm open; no build, no account action, no test authorized.
— Muse, 2026-10-20
