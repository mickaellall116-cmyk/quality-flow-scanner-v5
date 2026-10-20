# IDEA INTAKE — Volatility-forecast stop sizing reel (2026-10-20)

**Source:** Instagram reel, sent by Mike 2026-10-20 ~13:53 ET with no instruction text. Standing pattern applies (cf. Gartley/Wyckoff 2026-10-19, TradingView MCP carousel 2026-10-20): intake + adjudication with ChatGPT; no test without adjudication and preregistration.
**URL:** https://www.instagram.com/reel/Des85-5O8hJ/
**Creator:** Thomas Skinner (@deltatrendtrading), Columbia-affiliated finance educator; founder of QuantPad (the AI IDE with integrated market data used in the demo — the reel is also product marketing for QuantPad).
**Posted:** 2026-10-19 21:16 ET. 1,313 likes, 19 comments at fetch. Fetched via instagram-cli 2026-10-20 (post JSON `~/workspace/ig_reel_des855o8hj.json`; media understanding `~/workspace/ig_reel_des855o8hj_mu.json`).

## What the reel actually teaches

"How to PREDICT NQ's Range Using Volatility Forecasting Models" (NQ = Nasdaq-100 futures, daily bars):

- Direction is near-unpredictable: return persistence correlation ≈ −0.105 (his data).
- Range/volatility is forecastable because of **volatility clustering**: volatility persistence correlation ≈ 0.76 (his data).
- Model comparison for next-day range forecasting (average error, NQ points): combined model (lagged range + week + month aggregates + VIX) 62.7 < options-implied volatility 67.3 < naive "same as today" 83.2.
- Application demonstrated: forecast tomorrow's range (474 NQ points for the example day) and **size stop distance off the forecast** so stops sit outside the expected noise range — "stop getting stopped out unnecessarily."

## Evidence quality

- The core claim is textbook-established (volatility clustering is the empirical basis of GARCH-family models); the reel teaches a real phenomenon, not a guru pattern.
- All numbers are the creator's own, produced inside his own product (QuantPad): no dataset description, no out-of-sample protocol stated, no code shown for verification. The combined model's edge over options-implied (62.7 vs 67.3) is modest (~7%). Treat figures as plausible-but-unverified, per the standing rule (creator numbers are an idea board, never evidence).
- No return/P&L claims are made — the claim is forecast accuracy of range, a checkable and narrower claim than most reel content.

## Mapping to our program (Muse's opening position for adjudication)

- **Timeframe/instrument mismatch:** his object is the *daily range of an index future*; our frozen system trades 4H equity bars with a structural stop and fixed 1%-risk sizing. A vol forecast does not slot into V5.4 without touching stops/sizing — both frozen.
- **Exit research is closed by standing rule:** stop/exit changes open only if live forward evidence shows stops clipping winners or large MFE left uncaptured — that is exactly the parked MFE/MAE diagnostic at the ~50-signal checkpoint. A vol-scaled stop is a *candidate answer to a question we have not yet measured*; adopting it before the diagnostic would invert the sequence.
- **Adjacent backlog item:** harvest #2 candidate #4 (volatility-managed exposure) is the exposure-side cousin; this reel is the stop-side cousin. Both are vol-regime conditioning; neither touches the binding constraints (qualified data route, PIT earnings timing).
- **What IS testable here, later, on our own data:** (a) is next-bar/next-day range on our universe forecastable above naive/implied baselines (a measurement study, no trading claim); (b) IF the MFE/MAE diagnostic shows stop-outs clustering inside forecastable noise ranges, a preregistered vol-scaled-stop variant becomes a legitimate candidate for the exit-research queue.

## Proposed disposition (for ChatGPT adjudication)

BACKLOG NOTE ONLY, no test now. File as a stop-side research candidate explicitly gated behind (1) the ~50-signal MFE/MAE diagnostic showing a stop problem worth solving, and (2) the data-route program. The forecastability measurement (a) may be proposed separately as a small measurement study on data we already hold, with a frozen accuracy bar vs naive and implied baselines — but it earns nothing tradable by itself.

— Muse, 2026-10-20
