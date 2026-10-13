# TimesFM — learning note

Source: Instagram reel by @ai.with.andrew, 2026-10-11, about Google Research's
TimesFM. Mike asked whether we can learn from it; this note is the learning,
and a small pre-registered test follows it (see
timesfm_spike_prereg_20261012.md).

## What it is, plain

TimesFM is a free, open-source AI model from Google that forecasts time
series. It was pre-trained once on ~100 billion real data points (sales,
traffic, energy, weather, and more), so you don't train anything: you hand it
a series of past numbers and it predicts the next values, with a
best-case/worst-case range (quantiles) instead of a single guess. Newer
versions run inside Google Sheets and BigQuery.

"Zero-shot" means it works on a series it was never specifically trained on,
the way a language model answers questions about topics it wasn't separately
taught.

## Where it is genuinely strong

Series with real repeating structure: retail demand (weekends, holidays),
electricity load (daily/weekly cycles), web traffic, weather-driven series.
There, patterns exist before anyone trades on them, and a model that has seen
millions of such series learns their shapes well.

## Why stock prices are its weak spot

- A price is not a physical process; it is the crowd's current prediction.
  Any forecastable pattern invites trading that erases it.
- Fed past prices, the model mostly learns "tomorrow ≈ today" — accurate on
  average, worthless after trading costs.
- Pretraining contamination: a model trained on web-scale data may have seen
  the very price history you test it on. Scores on older data can flatter it;
  only the newest, post-cutoff data is a fair exam, and the exact training
  cutoff is not public.
- Regime shifts: the model cannot know the market's character changed. It
  extrapolates the recent past smoothly right up to the day that stops working.

## What we take from it regardless

- Ranges, not points: its quantile outputs are the honest way to present any
  forecast — a lesson for how we report our own numbers.
- Baseline discipline: a fancy forecaster earns nothing until it beats the
  dumb ones (no-change, simple drift) out-of-sample, after costs. That is the
  test we run on it, and the test everything here lives under.

— Muse, 2026-10-12
