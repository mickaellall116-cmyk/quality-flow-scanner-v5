# MasterScanner V5.4 — Frozen Spec (draft for sign-off)

Status: **research only, local file**. Live scanner remains V5.3 (`2026-09-14-v3`).
Frozen 2026-09-15 by Mike. No live rules modified.

## 1. What V5.4 is

V5.4 keeps the validated 4H pullback core and demotes the V5.3 hard vetoes
(market CONFIRM, full MTF alignment, RVOL ≥ 0.8, R:R ≥ 2) to grading inputs.
Two independent systems (~500 trades) showed the CONFIRM-style gates were
selecting *worse* trades, not better ones.

## 2. Hard gates for BUY NOW (unchanged core)

- Structural candidate (existing V5.3 structural logic)
- ADX ≥ 20 — kept as a hard filter. Cost only 0.019R of expectancy on UX51
  while materially reducing drawdown (21.3% vs 29.4%).
- Existing SAFE / protection requirements
- Above VWAP / buy-zone logic
- Completed-bar logic (signals scored on closed 4H bars only)

## 3. Exit — FROZEN (Mode B, locked 2026-09-15)

- Take 50% at TP1
- Keep remaining 50% as the runner
- Runner keeps the structural stop — **do not force breakeven**
- Scanner EXIT is ignored before the trade reaches +1R
- Once the trade reaches +1R, Profit Protect arms and scanner EXIT may close/protect the runner

Evidence (same 4H signals, entries identical, 4bps costs, 1% risk/trade):

| Mode | UX51 exp | UX51 PF | UX51 ret | UX51 DD | U15 exp |
|------|----------|---------|----------|---------|---------|
| A protect-1R (baseline) | +0.316R | 1.57 | +72.5% | 21.3% | +0.291R |
| **B 50%-TP1 + runner** | **+0.400R** | **1.71** | **+109.2%** | **17.4%** | **+0.311R** |
| C 50%-TP1 + breakeven | +0.380R | 1.70 | +90.4% | 16.7% | +0.200R |

B also held at 25bps costs (+0.325R UX51 — still beats A at 4bps).
Runner rides ~15 bars on average; TP1 taken ~42% of the time.

**Methodological note (keep attached):** trade counts differ by mode
(A: 251, B: 230, C: 234 on UX51) because exit timing affects when a symbol
becomes available for its next signal under the one-position-per-symbol
rule. This is legitimate but it is **not** a perfectly paired 251-vs-251
comparison. Do not describe it as one.

## 4. Grade definitions — FROZEN (signed off 2026-09-15)

Grades are information for priority and later sizing. They are **not** vetoes.
No grade may block a BUY NOW that passes the hard gates.

- **A — EARLY**: hard gates pass + early/partial confirmation profile (not
  fully confirmed/mature). Highest forward-test priority. Historical
  buckets: not-both-MTF +0.505R (n=138), BLOCK +0.511R (n=38),
  CAUTION +0.388R (n=100). Thesis: confirmation is lateness for a
  pullback engine.
- **B — CONFIRMED**: hard gates pass + fully confirmed/mature profile
  (Daily+Weekly both aligned and/or market CONFIRM). Valid trade, lower
  priority — full alignment is treated as potential lateness, not extra
  quality. Historical: both-MTF +0.084R (n=113), CONFIRM +0.186R (n=113).
- **C — OBSERVATION**: hard gates pass but contextual quality is
  weaker/uncertain. **Paper-trade / watchlist during V5.4 validation; no
  sizing rule yet.** C is explicitly *not* defined as "bad trade" — we have
  not demonstrated that weak-context combinations are negative-expectancy,
  and hand-building that filter now would repeat V5.3's mistake.

**Logging rule (anti-V5.3):** every hard-gate-qualified signal is logged,
including C. Throwing away C signals would destroy the data needed to
determine whether C is actually bad.

**Raw fields on every signal record** — the letter grade never replaces the
underlying data: market gate (BLOCK/CAUTION/CONFIRM), exact RVOL, Daily and
Weekly states, R:R, 15m confirmation state, premarket context.

**C decision gate:** after ~50–100 genuinely out-of-sample signals, decide
whether C deserves 0.25% sizing, watchlist-only status, or promotion.
Not before.

Soft grading inputs and their historical UX51 buckets (structural+ADX,
protect-1R... note: exit was Mode A in this study, not Mode B):
- RVOL 1.0–1.5: +0.466R (positive grade); RVOL <0.8: +0.272R (not a veto)
- R:R 2–3: +0.343R; R:R <2: +0.277R (not a veto)

Open questions for sign-off:
1. Exact A boundaries (how strict should "not fully confirmed" be?).
2. Whether C trades at reduced size or is watchlist-only during forward test.
3. 15m confirmation and premarket context: forward-test only (no historical
   data). Proposed as the A-grade separator, not a veto.

## 5. What is NOT in V5.4

- **No grade-based sizing yet.** Sizing A/B/C at different risk is deferred
  until grades are frozen here and validated on forward/out-of-sample
  trades. Sizing buckets by in-sample winners would be circular.
- **No fresh-BUY breakout system.** The pullback engine is not loosened to
  manufacture breakout signals. A breakout system would be a separate
  strategy with its own hypothesis, rules, and backtest.
- **No further exit tuning.** The exit is frozen. Continued optimization
  against this two-year (bull-heavy) sample risks curve-fitting.

## 6. Validation plan

1. ~~Hybrid-exit test~~ — done, Mode B frozen.
2. Freeze grade definitions — this document, pending sign-off.
3. Forward-test: 15m/premarket tags and grade separation on live bars.
4. Only then: test grade-based sizing on validated grades.

## 8. Forward-test record schema (frozen 2026-09-15)

Every qualifying 4H signal becomes evidence, never a reason to retune.
Each record captures:

- Signal ID, symbol, signal bar timestamp, grade (A/B/C)
- Raw context: market gate (BLOCK/CAUTION/CONFIRM), exact RVOL, Daily state,
  Weekly state, R:R, 15m confirmation state, premarket context
- Entry price, TP1, structural stop
- Whether +1R was reached
- Partial TP result (first 50%), runner result (remaining 50%)
- Final R (blended, net of costs), MFE, MAE, bars held

After ~50–100 signals this answers: do A/B/C actually separate future
expectancy? V5.3 stays live as the control — it shows specifically which
profitable trades V5.3 would have vetoed.

**Freeze discipline:** no changes to entry, exit, or grade definitions on
the basis of individual winning or losing trades during forward testing.

## 7. Proven vs provisional

- **Proven:** the 4H core (structural + ADX) has edge in two systems;
  market-CONFIRM as a veto hurts in both; Mode B exit beats protect-1R.
- **Provisional:** grade boundaries and labels; BLOCK-trade sizing
  (n≈40–60, encouraging but thin); 15m/premarket behavior; bear-market
  robustness (sample is bull-heavy).
