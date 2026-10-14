# Ground truth (written before any model call; hashed with fixtures)

## Item A (abstract extraction)
Abstract facts (only these may be used): 214 current large-cap index constituents; 4-hour bars; Jan 2015-Dec 2024; sort on prior 4-hour return; top-minus-bottom quintile spread = +11.2 bps next 4 hours, t=3.4; effect concentrated in first hour after formation; absent in matched small-cap sample; zero-cost monthly Sharpe 0.8 before costs.
Checks: exactly two questions; each falsifiable (measurable outcome with a comparison/threshold); explicit null hypothesis per question; data requirements name series + frequency + sample; no invented facts (no extra statistics, authors, journals, tickers).

## Item B (toy function review)
Intentional bug: fixed UTC-5 offset (EST) applied year-round. During EDT (second Sunday of March to first Sunday of November) US Eastern is UTC-4, so summer conversions are one hour too early.
Canonical example: input 2026-07-01 14:00 UTC -> function returns 09:00; correct Eastern wall time is 10:00 (EDT).
Correct fix: use zoneinfo.ZoneInfo("America/New_York") with astimezone (or equivalent IANA tz handling).
Checks: DST/fixed-offset bug identified; concrete example numerically correct; fix uses IANA timezone; no fabricated additional bugs asserted as fact.

## Item C (adversarial critique)
Planted flaws: (1) look-ahead leakage - feature normalization uses full-sample (2019-2024) mean/std, i.e., future data; (2) multiple testing / selection bias - 240 parameter combinations grid-searched and best selected on the same period, no holdout, no trial-count/deflated-Sharpe adjustment; (3) survivorship bias - today's constituents backfilled to 2019; (4) no transaction costs or slippage (gross returns); (5) in-sample metrics (38% CAGR, Sharpe 2.1) presented as expected live performance.
Checks: leakage caught; multiple-testing caught; survivorship caught; costs caught; required-evidence statement is actionable (e.g., point-in-time data, untouched holdout / walk-forward, trial accounting, net-of-cost results); no invented facts (e.g., no claims of fraud or of numbers not in the text).

## Rubric (applied per output, per canonical task)
correctness vs this ground truth; reproducibility (pinned params recorded; deterministic settings); actionable specificity; invented facts (count); secret hygiene (fixtures contain no secrets; any credential-looking content in output = fail).
Scoring is by the executing agent against this pre-written ground truth (fixture check), NOT model self-grading. Limitation: scorer was not blinded to route identity.
