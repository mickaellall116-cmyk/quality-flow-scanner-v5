# TradingView Input Parity Map — live V3.6 script vs canonical Python reference

**Date:** 2026-09-18. **TV source:** live script pasted by Mike ("Quality Flow System V3.6 - V3.3 Engine + V3.5 Dashboard", `//@version=6`).
**Python reference:** `pine_backtest.py::pine_buy_signal` (docstring: "Hybrid buySignal evaluated on completed bar i").
**Rule:** Python is canonical. Anything in TV with no Python counterpart is non-canonical and fenced off from production decisions.

## Verdict

At defaults, the TV script's `buySignal` **exactly matches** the canonical Python signal:
`confirmedBuy or breakoutBuy or readyBuy` == `confirmed or breakout_buy or ready_buy`.
`extraEntry` is false at defaults (all three sub-toggles default false), so it contributes nothing.

## Bucket A — canonical (in Python, affect validated signals)

EMA 9/21/55/200, ATR 14, ADX 14/14, Volume MA 20, Breakout Lookback 10,
TP1 ATR 2.0, Stop ATR 1.5, Runner Trail ATR 2.5, HOT ATR Distance 1.5,
Use Volume Filter (true), Avoid HOT Entries (true).
Entry Mode at its **default "Hybrid"** reproduces the canonical signal path.

## Bucket B — non-canonical SIGNAL inputs (change buySignal, absent from Python — FENCED OFF)

1. **Entry Mode selector** (`Conservative` / `Hybrid` / `Aggressive`). Not in Python.
   Conservative drops `readyBuy`; Aggressive adds `earlyBuy` (with its own 10-bar throttle).
   Mike's manually-cycled "materially different backtests" came from this TV-only control.
   Production rule: stays at **Hybrid**. Any other setting is a TV experiment, not V3.6.
2. **Use Pullback as Real Entry** (default false). Not in Python. Must stay **false**.
3. **Use FVG as Real Entry** (default false). Not in Python. Must stay **false**.
4. **Use Sweep as Real Entry** (default false). Not in Python. Must stay **false**.
   (All three feed `extraEntry`, which is OR'd into `buySignal` in every mode — a single
   `true` here silently changes the strategy with zero Python counterpart.)

## Bucket C — display / informational only (not in Python, not wired to strategy.entry)

Show Labels, Show Dashboard, Show Buy Zone, Show Latest Bull FVG.
MTF state engine (W/D/4H `request.security`, mtfScore, mtfAligned) — feeds the dashboard
"ENTRY YES/NO" row and W/D/4H row only. `buySignal` never reads it.
Dashboard ENTRY logic (`entryContextOK`/`entryLocationOK`/`entryRiskOK`), profit-protection
text, `stateText`/`actionText`, FVG box, sweep diamonds, buy-zone shading, `hotPrint`,
BOS/CHoCH labels, structure text. None of these reach `strategy.entry`.
**Production rule:** the dashboard's "ENTRY YES" is advisory, not the validated system.
No trade is taken off dashboard state, MTF score, or alert text.

## Footnotes (real discrepancies found)

- **F1 — "BUY Signal" alert under-reports.** `alertcondition("BUY Signal")` fires on
  `confirmedBuy or breakoutBuy or extraEntry` — it omits `readyBuy`, which IS part of
  the Hybrid `buySignal`. Alerts set on "BUY Signal" miss ready-mode entries.
- **F2 — TV strategy-tester sizing is not comparable.** The script header sets
  `default_qty_value=100` (100% of equity per trade). TV's own backtest P&L therefore
  cannot be compared to the Python portfolio simulation (1% risk, 5-slot cap, rs_top2,
  sector cap, 5% risk gate). Only Python numbers count for validation.
- **F3 — FVG-extended buy zone is always on for display.** `useFvgZone` is not gated
  behind `useFvgAsEntry`; the shaded zone widens near FVGs regardless. Display-only at
  defaults (only `pullbackBuy` reads the zone, and it needs the fenced-off toggle).

## Standing production rules from this map

1. Entry Mode = Hybrid, always, for any production-relevant reading.
2. The three "Use X as Real Entry" toggles = false, always.
3. Dashboard ENTRY/MTF/profit-protection are for chart context only — never a trade trigger.
4. TV strategy-tester equity curve is not evidence; Python ledgers are.
