# HEMA Slot-Ranking Test — Preregistration (2026-09-28)

Research-only. The frozen/live Quality Flow system is not modified.

## Question
Can recent HEMA bullish crossover information improve which valid Quality Flow signals receive scarce portfolio slots **without acting as an entry gate**?

## Fixed candidate rule
Quality Flow setup generation, stops, TP1, Profit Protect, 30-bar timeout, next-bar execution, costs, 1% planned risk, max 6 positions, 5% heat, and existing 20-bar return-minus-SPY score are unchanged.

At a decision timestamp, after removing busy/pending symbols and calculating available slot/heat capacity:

- If every candidate fits, ranking has no effect.
- If fewer candidates fit than are available, baseline ranks by existing `rs20_spy` descending.
- **HEMA ranking candidate:** rank `recent_big_green_4 == True` ahead of `False`, then rank by the unchanged `rs20_spy` descending, then symbol for deterministic ties.
- `recent_big_green_4` means a 4H HEMA20/HEMA40 bullish crossover occurred on the signal bar or one of the prior three completed 4H bars.
- HEMA never invalidates a QF setup. It only reorders candidates when actual capacity competition exists.
- No HEMA weights, lookback search, parameter optimization, or alternative HEMA ranking formulas are allowed in this test.

## Controls
1. **Baseline:** `rs20_spy` only.
2. **EMA control:** `EMA20 > EMA40` preference first, then `rs20_spy`.
3. **Matched random preference:** within each candidate batch, permute the HEMA preference labels while preserving how many preferred candidates exist in that batch; then rank preferred first, followed by `rs20_spy`. Use fixed seeds 0–199. This tests whether HEMA identity beats an arbitrary same-sized preference.

Price > EMA200 is not a useful ranking control here because the QF structural-core candidate already requires the trend condition. A SPY-wide regime is common to all same-timestamp candidates and therefore cannot choose among them.

## Primary metrics
- number of candidate decision batches;
- number of true ranking-pressure decisions (`0 < available < candidates`);
- number of candidates ranked out due to capacity;
- accepted trades;
- total net R;
- net expectancy R/trade;
- net profit factor;
- marked portfolio return;
- maximum marked-equity drawdown;
- yearly metrics, especially 2026;
- net results at 25/50/75/100 bps.

## Robustness
- Directly compare HEMA-strategy trades that are unique versus baseline trades that are displaced.
- Remove top 1, 3, 5, and 10 trades and recompute.
- Report entry-notional/book ratios and sensitivity excluding >1x and >2x entries as diagnostics only; these are not replacement strategies.
- Explicitly identify whether the APLD 2024-01-03 extreme trade appears in each variant.

## Decision standard
The HEMA ranking hypothesis is not supported merely by higher expectancy. It must improve system-level results under real slot pressure, compare favorably with the EMA and matched-random controls, avoid dependence on a handful of trades/episodes, and not deteriorate materially in 2026.

This 30-symbol surrogate can only screen the hypothesis. A positive result still requires the canonical 131-symbol PIT data before any frozen/live change.
