# HEMA Pre-TP1 Protective Exit — Preregistration (2026-09-28)

Research-only. Frozen/live Quality Flow remains unchanged.

## Question
Can HEMA reduce failed-trade losses **before TP1** without acting as an entry gate?

## Fixed mechanics
- Exact baseline QF accepted entries from the 50-bps rs_top2 run.
- Entry, structural stop, TP1, shares and 30-bar timeout held fixed.
- Post-TP1 runner management remains the current Profit Protect logic.
- Headline costs 50 bps; 25/75/100 bps sensitivity.
- Any protective signal is evaluated on a completed bar and fills at the next 4H open.

## Rules
1. **current** — existing pre-TP1 behavior: scanner exit can only trigger after +1R arms Profit Protect.
2. **h4_hema_emergency** — before TP1, a completed 4H HEMA20/40 bearish crossover can exit even if +1R has not armed; otherwise current behavior.
3. **daily_hema_emergency** — same concept using a completed Daily HEMA bearish crossover.
4. **unarmed_scanner_exit_control** — allow the existing scanner exit before TP1 without the +1R arm. This tests whether any benefit comes from earlier exits generally rather than HEMA specifically.
5. **h4_ema20_40_emergency** — ordinary 4H EMA20/40 bearish crossover as a simple trend-control exit.

No parameter search and no rule combinations beyond the five pre-registered variants.

## Metrics
- paired net R versus current;
- number of trades changed;
- number of structural-stop losses avoided;
- number of early exits that would later have become winners under current;
- paired bootstrap and entry-month block bootstrap;
- yearly results, especially 2026;
- cost ladder 25/50/75/100 bps.

A positive result must improve paired results on a meaningful number of trades and not merely shift a few outliers. Any positive screen still requires canonical 131-symbol PIT confirmation.
