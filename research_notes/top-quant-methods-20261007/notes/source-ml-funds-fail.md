# Source: "10 Reasons Most Machine Learning Funds Fail" — index, 2026-10-07
Primary: López de Prado, M., "The 10 Reasons Most Machine Learning Funds Fail", Journal of Portfolio Management 44(6), pp. 120–133 (2018). SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3104816
Read via: github.com/hudson-and-thames/secondbrain note ( Mary's Room/📕Sources/10 Reasons Most Machine Learning Funds Fail.md ) and tradingstrategy-ai/docs machine-learning.rst — both secondary; consistent with each other.

The "7 reasons" (coursehero slide deck from his Cornell ORIE 5256 lecture, ssrn.com/abstract=3447398):
1. The Sisyphus paradigm (siloed quants) → solution: Meta-Strategy paradigm
2. Integer differentiation (stationarity-vs-memory dilemma) → Fractional differentiation
3. Inefficient sampling, chronological sampling → Volume clock / information-driven bars
4. Wrong labeling: fixed time horizon → Triple-Barrier Method
5. Learning side and size simultaneously → Meta-Labeling
6. Weighting of non-IID samples → Uniqueness weighting and sequential bootstrapping
7. Cross-validation leakage → Purging and embargoing
(The 2018 paper adds: Walk-Forward Backtesting → CPCV; Research Through Backtesting → Feature Importance; Backtest Overfitting → DSR — total 10. The lecture version emphasizes the 7 ML-pipeline reasons.)

mathinvestor.org note (Quant of the Year 2019): summarizes de Prado contributions: volume clock, triple-barrier, meta-labeling, uniqueness-weighting, fracdiff, purged/embargoed CV; AFML proposed applying ML to "discovery of new economic theories, rather than black-box predictions." Notes he was principal/head of ML at AQR, adjunct professor at Cornell.

medium.com AFML Part 0 (secondary summary of AFML ch.1): strategy factory roles — Data Curators, Feature Analysts, Strategists, Backtesting Team, Deployment Team, Portfolio Managers. Thesis: most quant strategies fail as false discoveries of a flawed unscientific research process; financial ML ≠ ML algorithms + financial data.
