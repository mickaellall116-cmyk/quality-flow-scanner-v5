# HEDGE SPEC — pre-specified before any backtest (2026-09-18)

Question: can simple hedge overlays (no signals on the hedge itself) earn their keep on a long-equity portfolio?
Prior context: two research tracks proved this scanner framework cannot short (mirror shorts: -0.08R/trade;
unchanged long engine on SH/PSQ: zero trades by construction). Hedges are the remaining downside-exposure path.

## 1. Data (pre-specified)
- Daily bars, `auto_adjust=True` (matches the live scanner's `download_data`), symbols: QQQ, SPY, SH, ^VIX.
- Download start: 2020-01-01 (warmup for 200-day EMA; warmup bars are NOT test data).
- Test window: 2022-01-01 → 2026-09-14 (covers 2022 bear, 2023-2025 bull, 2026 YTD).
- Source: yfinance daily (no intraday limit issue at daily resolution).

## 2. Regime series (pre-specified)
- Exact replication of the scoring in `backtest.py::regime_at` / `masterscanner_api::get_market_regime`,
  applied to DAILY QQQ/SPY bars (documented adaptation: the original ran on 4H bars; the scoring formula is
  timeframe-generic and this is what `get_market_regime("1d", ...)` would compute live):
  - score = 35*(Close>EMA200) + 35*(EMA21>EMA55) + 15*(EMA21 rising) + 15*(Close>EMA21), EMA via ewm(span, adjust=False)
  - session return = today's close vs prior trading day's close (daily-bar equivalent of `_session_return`)
  - gate: BLOCK if qqq_ret <= -0.75 or (qqq_ret <= -0.40 and spy_ret <= -0.40); CAUTION if qqq_ret<0 or spy_ret<0 or score<75; else CONFIRM
  - regime = RISK-ON if score>=75, CAUTIOUS if score>=50, else RISK-OFF
- Point-in-time: regime at close t uses only bars <= t. First 205 bars of download = UNKNOWN (warmup).
- All hedge actions trigger on the close-t regime and execute at the NEXT open (t+1). No lookahead.

## 3. Portfolio proxy (pre-specified)
- $100,000 starting capital. Long leg = QQQ buy-and-hold (adjusted close), 4bps cost on initial purchase only.
- Hedge overlays are funded from / sized against total portfolio value (long + hedge + cash).
- Combined equity curve drives the max-drawdown comparison (QQQ-only vs QQQ+hedge).

## 4. The four hedges (pre-specified; parameters frozen below, never fitted afterward)

### Hedge A — regime-timed QQQ puts (BS-estimated)
- Trigger: close-t regime flips INTO RISK-OFF while no put held → buy at open t+1.
- Contract: 30 calendar days to expiry, strike K = 0.95 × S_fill (S_fill = QQQ open at fill).
- Sizing: premium budget = 0.5% of total portfolio value at buy time;
  contracts = floor(budget / (put_price_per_share × 100)); if < 1 contract affordable, skip and record.
- Pricing (all marks and fills): Black-Scholes put, r = 4.0%, q = 0.6% (QQQ dividend yield),
  σ = VIX_close/100. σ uses the VIX close on the signal day for fills, VIX daily close for marks.
  DOCUMENTED APPROXIMATION: VIX is SPX 30-day IV; QQQ IV typically runs higher, so real put costs are
  likely HIGHER than modeled (results flatter the hedge). Sensitivity check at σ = 1.15×VIX/100 in analysis.
- Roll: if still RISK-OFF when 30 calendar days elapse → sell old at open (BS value), buy new same open.
- Exit: when close-t regime leaves RISK-OFF → sell entire position at next open. Never exercise, never hold past 30 days.
- Costs: none modeled on option trades (no spread/slippage in BS world; documented optimistic bias, small vs premium).

### Hedge B — always-on QQQ puts (BS-estimated)
- Same contract/pricing/sizing as Hedge A, but held continuously: buy at first test-window open,
  roll every 30 calendar days unconditionally, never exited for regime.

### Hedge C — regime-timed SH
- Trigger: close-t regime flips INTO RISK-OFF while no SH held → buy SH at open t+1 with 10% of total portfolio value.
- Exit: when close-t regime leaves RISK-OFF → sell ALL SH at next open.
- Costs: 4bps each way. SH distributions ignored (immaterial). All prices exact (adjusted).

### Hedge D — always-on SH
- Buy 10% SH at first test-window open; rebalance to 10% of portfolio at each month-end (execute next open); 4bps each way.

## 5. Metrics (pre-specified, reported per hedge)
- Puts: total premium paid vs total payouts (sales); net P&L; annualized drag = net P&L / years / $100k.
- SH: net P&L incl. costs; same annualization.
- Year splits: 2022 / 2023 / 2024 / 2025 / 2026-YTD net P&L per hedge.
- Combined portfolio: max drawdown of (QQQ + hedge) vs QQQ-only; ending equity both.
- Activity: number of buys/rolls/sells per hedge; % of test days spent in RISK-OFF.
- Verdict ranking: 1) does the hedge earn its keep (positive net, DD reduction worth the drag)?
  2) regime-timed vs always-on; 3) puts vs SH. One recommendation.

## 6. Anti-overfit commitment
Parameters above are frozen. No variant may be fitted on these results. A failed hedge is a failed hedge.
