# forward_scoreboard.py — live forward-test scoreboard

Read-only scoreboard for the confirmatory research phase
(mandate: `research_notes/research_mandate.md`, "Forward-test scoreboard").

## What it does
Reads the frozen forward-test log (`v54_forward/forward_test.jsonl`) and the
two paper sidecar logs (`v54_forward/fvg_sidecar.jsonl`,
`v54_forward/lonewolf_overlay.jsonl`) and prints one plain-text scoreboard
covering:

- **V5.4 baseline** — the frozen production forward test
- **FVG paper sidecar** (`hybrid+fvg-entry`) — its own variant trades
- **Lone-wolf paper overlay** (`hybrid+no-lonewolf`) — joins `would_block`
  verdicts to baseline outcomes by signal id; reports blocked vs allowed
- **ADX ranking shadow** — reconstructs per-bar candidate sets from the
  forward-test signal log (per-signal `adx` is present on all signals) and
  compares what ADX-descending top-5 selection would have taken vs the
  harness's real admission on crowded bars (>5 signals/bar)

For each: signals seen, closed trades, expectancy R, win rate, PF, worst MAE,
best MFE, missed winners / avoided losers (filters only, where outcomes
exist), and a mandatory sample-size warning. Never declares a winner from a
tiny live sample.

## Run it
```
python3 forward_scoreboard.py          # plain text
python3 forward_scoreboard.py --json  # JSON for automation
```

## Guardrails
READ-ONLY. Opens the logs for reading only; never writes to them, never
touches the forward-test harness, V5.4, Mode B, production alerts, grades,
market gate, AI Observer, or the sidecars themselves. It reuses the sidecars'
own log/state files and does not duplicate their classification logic.

## Current status (2026-09-24)
- Baseline: 19 signals, 4 closed (all −1.0R stops) — noise, do not judge
- FVG sidecar: 6 signals, 4 open, 0 closed yet
- Lone-wolf: 19 overlays, 0 blocked (18 unmapped to the 14-name sector map,
  1 mapped + allowed) — validates slowly by construction
- ADX shadow: feasible (ADX on all signals) but vacuous so far — ranking
  never bound (max 2 signals/bar; skips were per-symbol dedup, not ranking)
