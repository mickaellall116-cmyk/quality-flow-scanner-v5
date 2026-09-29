# ChatGPT Handoff Brief — MasterScanner V5.4

Paste this whole document into ChatGPT as context. It is a complete,
self-contained sync brief. The human (Mike) is the decision-maker; the
spec below is frozen and should not be re-litigated without new evidence.

## 1. What this is

MasterScanner is a 4-hour-bar pullback scanner for US equities and crypto.
V5.3 (live) over-filtered: full confirmation gates produced ~2 tradeable
signals in 2 years. Research on V5.4 is **closed** — entries, exit, and
grade definitions are frozen for forward testing. No more backtest-driven
tuning.

## 2. Frozen V5.4 spec

**Hard gates for BUY NOW (all must pass):**
- Structural pullback candidate (existing V5.3 structural logic)
- ADX ≥ 20
- Existing SAFE / protection requirements
- Above VWAP / in buy zone
- Signal scored on completed 4H bars only

**Exit (frozen — "Mode B"):**
- Take 50% at TP1
- Runner (remaining 50%) keeps the structural stop — never force breakeven
- Scanner EXIT signals are ignored before the trade reaches +1R
- After +1R, Profit Protect arms: scanner EXIT may close/protect the runner

**Grades (frozen — informational, never vetoes):**
- **A — EARLY:** hard gates pass + early/partial confirmation profile.
  Highest forward-test priority. Thesis: for a pullback engine,
  confirmation is lateness.
- **B — CONFIRMED:** hard gates pass + fully confirmed/mature profile
  (Daily+Weekly both aligned and/or market CONFIRM). Valid, lower priority.
- **C — OBSERVATION:** hard gates pass, weaker/uncertain context.
  Paper-trade/watchlist only during validation. C is explicitly NOT "bad
  trade" — that was not demonstrated.

**Logging rule:** every hard-gate-qualified signal is logged, including C.
Each record keeps raw fields (market gate, exact RVOL, Daily/Weekly states,
R:R, 15m state, premarket context) plus entry, TP1, stop, +1R flag, partial
and runner results, final R, MFE/MAE, bars held. The letter grade never
replaces the data.

**C decision gate:** after ~50–100 out-of-sample signals, decide whether C
gets 0.25% sizing, stays watchlist-only, or is promoted.

**Freeze discipline:** no changes to entry, exit, or grades from individual
trades during forward testing. V5.3 stays live as the control.

## 3. Key evidence (why the spec looks like this)

Backtests: 2 years of 4H bars, point-in-time signals (no lookahead),
next-bar-open entries, 4bps costs, 1% risk/trade, max 30-bar hold.
Two universes: U15 (15 tech-heavy symbols, 63–94 trades) and UX51
(51 symbols incl. equities/ETFs/crypto, 230–263 trades).

- **4H core works:** structural + ADX ≥ 20 → UX51: +0.316R/trade, PF 1.57,
  +72.5% return, 21.3% max DD (251 trades). U15: +0.291R, PF 1.55.
- **Confirmation gates were inverted (two independent systems, ~500
  trades):** market BLOCK bucket +0.51R vs CONFIRM +0.11–0.19R; Daily+
  Weekly both-confirmed +0.08R vs not-both +0.51R (scanner). The vetoes
  weren't neutral — they selected worse trades. Hence demotion to grades.
- **Mode B exit beats baseline:** 50%-at-TP1 + structural-stop runner →
  UX51 +0.400R, PF 1.71, +109.2%, DD 17.4% vs protect-1R all-or-nothing
  +0.316R / +72.5% / 21.3%. Held at 25bps costs. Breakeven-stop variant
  cut winners (worse). Runner rides ~15 bars avg; TP1 taken ~42%.
- **ADX ≥ 20 as hard filter:** cost only 0.019R expectancy, cut drawdown
  materially (21.3% vs 29.4% on UX51).
- **Indicator cross-check:** Mike's separate TradingView strategy (Pine
  V3.6, reimplemented in Python) shows the same market-gate inversion and
  a thinner edge (+0.195R UX51). It stays as chart-side confirmation only.

## 4. Methodology notes (do not let anyone hand-wave these)

- Exit-mode trade counts differ (A: 251, B: 230, C: 234) because exit
  timing affects signal availability under one-position-per-symbol. Not a
  perfectly paired comparison — but the ranking is valid under the same
  convention used throughout.
- Sample is bull-heavy (2024–2026); bear robustness untested.
- 15m confirmation and premarket behavior have no 2-year historical data —
  forward-test only.
- The Pine/TradingView reimplementation is approximate (bar alignment,
  ATR handling differ); directionally reliable, not exact.
- Grade-based position sizing was deliberately deferred: sizing buckets by
  in-sample winners would be circular. Freeze grades → validate forward →
  then size.

## 5. What is provisional / open

- Grade boundaries (evidence-backed but still labels, not proof)
- C's eventual fate (the 50–100-signal decision gate)
- BLOCK-regime sizing (encouraging, n≈40–60 — thin)
- 15m/premarket as A-grade separators (forward test only)

## 6. How to work with Mike on this

- The spec above is frozen. Suggest freely, but distinguish suggestion
  from evidence, and do not propose re-tuning entries/exits/grades on
  backtest data.
- If you propose an experiment, say what would falsify it and what data
  it needs (historical vs forward-only).
- Mike decides. Present trade-offs plainly; keep answers short and practical.
