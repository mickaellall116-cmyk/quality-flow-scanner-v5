# Tier 3 List — Reproducibility Record

Rule: `TIER3_RULE_FROZEN.md` v1.0, frozen 2026-10-26 before generation
(SHA-256 `b4b993e8e23a221c050a6ceab0274ed59e5c25a4973704b4e545646863297ce3`).
Source date: **2026-10-26**. All runs executed 2026-10-26 (ET), from the
archived sources in `sources/` — sources were fetched once and never
refreshed between runs.

## Inputs (archived, hashed)

| Input | SHA-256 |
|---|---|
| `sources/nasdaqlisted.txt` (File Creation Time 2026-10-26 15:41 ET) | `8e72f822228a2536b0e712e5ee91c14e30db07408cc8863a6d64cb1bac1c2c19` |
| `sources/otherlisted.txt` (File Creation Time 2026-10-26 15:41 ET) | `67c1e321790341bf89172e2dc30119e1a39180d3dd4b2d7cb4e420ba02305ca6` |
| `sources/nasdaq_screener_raw.json` (retrieved 2026-10-26) | `464e82847212024e3c2b871c487c4ac6a3af854763f82dbd124ed4987b39b912` |
| `exclusion_universes.json` (UX51 51 + X2 199, exported from repo modules) | `c7112909009aa605a380b198d07b3ebd421fa44ce5a4751e830c8496ca535e04` |

Liquidity input (rule step 8): Yahoo Finance daily bars, completed sessions
2026-09-01 → 2026-10-25, fetched live per run for the 2,561 step-7
candidates only. No candidate price series is stored; only the aggregates
in the output (ADV20, last close, bars used) persist. No symbol in UX51/X2
was ever fetched. No data from the sealed holdout window was accessed for
any symbol; no return or outcome was computed for any symbol.

## Script versions

| Version | SHA-256 | Difference |
|---|---|---|
| v1.0 (runs 1–2) | `c09606cf75c8432e6bc61a30550af1fcf2fb45da02f9818a41061e0da1e4dcdb` | As frozen with the rule |
| v1.1 (runs 3–4) | `0b39e1d4d447ef6a04fec18d064c439b65e5b7831c682ebb2f6427ce29a8921b` | Transport only: symbols yielding no fetch result are retried once. Eligibility, cutoffs, windows, ranking, and list size are byte-identical logic. Reason recorded under "Discrepancy" below |

## Runs

| Run | Script | Output file | Output SHA-256 |
|---|---|---|---|
| 1 | v1.0 | `tier3_list_run1.json` | `9e7ae05261b02cd6fde20909f86332a7b6cfda82bc330094136f56aba71f5d4e` |
| 2 | v1.0 | `tier3_list_run2.json` | `56e8cde799dc374302a651d270818a74c9a8cb9f9c5869b36268a9a1cb98c2f7` |
| 3 | v1.1 | `tier3_list_run3.json` | `9e7ae05261b02cd6fde20909f86332a7b6cfda82bc330094136f56aba71f5d4e` |
| 4 | v1.1 | `tier3_list.json` (frozen output) | `9e7ae05261b02cd6fde20909f86332a7b6cfda82bc330094136f56aba71f5d4e` |

## Discrepancy (disclosed, runs 1 vs 2)

Runs 1 and 2 selected the **identical 12 symbols in identical order with
identical ADV20/last-close values**, but the output files were not
byte-identical: the diagnostic stage counts differed —
`fetch_failed_or_short` 10 (run 1) vs 15 (run 2), and consequently
`after_step_8_liquidity` 797 vs 795. Cause: the free Yahoo feed drops
requests transiently; five marginal candidates yielded no data in run 2
that had yielded data in run 1. None was anywhere near the selection
boundary (the selected symbols' ADV20 exceeds the $25M cutoff by ~50× or
more), so the selection itself was unaffected. The v1.1 retry pass removes
this transport nondeterminism; runs 3 and 4 test it.

## Verdict

**REPRODUCIBLE.** Runs 1, 3, and 4 produce the byte-identical output file
(SHA-256 `9e7ae052…`), including all stage counts, parameters, and the
selected list. Run 2 differs only in the two diagnostic stage counts, for
the disclosed transport reason above; its selection is identical. The
frozen output is `tier3_list.json` (= run 4, hash `9e7ae052…`). The
remaining 10 fetch failures after the retry pass are permanent (delisted /
no-data symbols: e.g., ENLV, SXTC, PARA, HCTI, IPW, AXG, COCH) and fail
identically in every v1.1 run.

## The frozen Tier 3 list (12)

| Rank | Symbol | ADV20 ($) | Last close ($) |
|---|---|---|---|
| 1 | GOOG | 5,286,833,881.42 | 317.28 |
| 2 | BE | 3,816,275,880.09 | 193.30 |
| 3 | ACN | 1,783,792,453.13 | 249.37 |
| 4 | IREN | 1,675,424,544.16 | 24.905 |
| 5 | CRDO | 1,650,609,398.22 | 147.29 |
| 6 | TWLO | 1,226,616,365.35 | 261.79 |
| 7 | AAOI | 1,106,681,698.20 | 67.51 |
| 8 | MPWR | 928,716,016.86 | 1,140.12 |
| 9 | SPOT | 906,854,434.55 | 584.22 |
| 10 | BABA | 890,485,652.70 | 99.64 |
| 11 | COF | 785,673,699.65 | 201.34 |
| 12 | BLK | 733,841,546.77 | 1,118.25 |

Stage funnel (all agreeing runs): 7,446 listed real securities →
5,905 common-stock screen → 5,862 plain tickers → 5,655 after prior-study
exclusion → 2,561 after IPO-year ≤ 2023 → 797 passing the liquidity cutoff
(10 permanent fetch failures, fail-closed) → top 12 frozen above.
Prospective holdout universe: 19 clean Tier 2 + 12 Tier 3 = 31 symbols
(≥20 floor, with the headroom arithmetic in the rule document).

Independent spot-verification (from archived sources only): all 12 are
common stocks / ordinary shares / ADS with ETF = N and Test Issue = N in
the 2026-10-26 NASDAQ directories; none appears in UX51 or the X2 cohort;
all satisfy ADV20 ≥ $25M and last close ≥ $5; ranks are strictly descending
in ADV20.
