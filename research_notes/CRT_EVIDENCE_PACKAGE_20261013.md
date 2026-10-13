# CRT (Candle Range Theory) — Evidence Package

**Experiment:** EXP-20261012-CRT-4H (registry `research_notes/research_loop/registry.json`;
intake recorded by ChatGPT at commit `2eeaa35eda877658541645b2e4c6ffc04f9d030c`,
2026-10-12 09:16:29 EDT).
**Prepared:** 2026-10-13, in response to the evidence-delivery request in GitHub
Issue #1 comment `6125000616` (2026-10-12 13:13:40 UTC), which placed the CRT
adjudication on HOLD pending this package.
**Nature of this document:** evidence packaging only. Nothing was rerun, repaired,
or retested for it. All figures below are the as-reported results of the single
2026-10-12 run, pinned to the artifacts that produced them.
**Verdict carried (Muse-reported, adjudication HOLD):** FAIL on the pre-declared gate.

---

## 1. Artifact pins

Local artifacts, directory `pine_claims_crt/` (uncommitted at package time; staged
for central commit with this package — no prior commit of these files exists, which
is why ChatGPT's read of the path returned 404):

| file | bytes | sha256 |
|---|---|---|
| `pine_claims_crt/README.md` (preregistration + results) | 9,917 | `ddf8fe22b1fe9c0bfe4beb35436d815ed6394193de8cf0bcec5020f09566a4c0` |
| `pine_claims_crt/run_crt.py` (test code, frozen) | 16,630 | `bf587693e21a52c93b0f8874672af2d411f780c1c574b744e3975506cf04f6f1` |
| `pine_claims_crt/crt_results.json` (full output) | 71,952 | `f999508f0d91e2a47a39dad581136166418606db2f408ce4bd18849f883f6380` |

Dependency pin: `pine_backtest.py` (canonical engine, imported UNMODIFIED by
`run_crt.py`), sha256 `447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5`.
Engine constants used by the run (from that file): `WARMUP=215`,
`START_EQUITY=10000`, `RISK_PCT=0.01`, `MAX_CONCURRENT=5`, `MAX_PORTFOLIO_RISK=0.05`;
TP1 ratio `TP_ATR/SL_ATR = 2.0/1.5 = 1.3333` (recorded in `crt_results.json` as
`tp1_r_mult`).

Filesystem timestamps (UTC, from `stat` birth/mtime, 2026-10-12):
README.md born 12:48:38, run_crt.py born 12:49:42, `__pycache__/run_crt` compiled
12:49:54, crt_results.json born 12:50:09, README final mtime 12:50:52 (results
section appended). These bound the run sequence in §4.

## 2. Headline results (as reported; full numbers in crt_results.json)

- **BASE (in-study rerun, canonical Hybrid `pine_buy_signal` + `gen_pine_trades`):**
  237 trades, win 50.6%, **+0.239R @25bps**, PF 1.38, maxDD 21.63%. This reproduces
  the canonical 4H Hybrid baseline figure produced by prior studies on the same
  cache family (sweep #1, 2026-09-28, recorded the identical 237 / +0.239R).
- **CRT-LONG (primary, gate variant):** 811 trades, **−0.358R @25bps**, PF 0.65,
  maxDD ~100%. Dev half (2023–24) −0.568R; validation half (2025–26) −0.282R.
- **CRT-LONG-MARGIN (pre-declared perturbation, sweep ≥ 0.25·ATR):** 518 trades,
  −0.261R @25bps.
- **CRT-SHORT:** 835 trades, +0.165R @25bps — but HOOD alone contributes +309.7R of
  the +137.6R total (without HOOD the leg is negative); −0.254R @50bps.
- **CRT-LS (claim as stated, pooled):** 1,116 trades, +0.001R @25bps, PF 1.00.
- Stop geometry: the claim's stop-at-sweep-extreme produced observed risk fractions
  as small as 5e-5 (~$0.05 on a ~$95 HOOD bar), implying up to ~200×-equity sizing
  in the fixed-fractional framework; the ~100% maxDD is the geometry verdict.

All variations run are listed above — BASE, CRT-LONG, CRT-LONG-MARGIN, CRT-SHORT,
CRT-LS. No other CRT variant was run. Claims considered and rejected before the run
(untested): @chavan.v4 4H→15M rejection entry (requires 15M data); Jin Ren Tenh ICT
PD-array tap (discretionary, FVG family already closed). Family record: stop-run
reversal is 0-for-3 on 4H (capitulation harami FAIL 2026-09-28, PoC pullback FAIL
2026-10-05, CRT FAIL 2026-10-12).

## 3. Preregistration anchor

The pre-declared rules and gate are recorded in `pine_claims_crt/README.md`,
section **"Pre-registration (frozen BEFORE running)"**, including the exact rule,
variants, test plan, and the success gate, quoted verbatim:

> **PASS:** pooled CRT-LONG expectancy ≥ +0.35R @25bps AND ≥ 60 trades AND
> validation-half (2025→Sep 2026) expectancy > 0 AND @50bps expectancy ≥ +0.15R AND
> no single symbol contributes > 40% of total net R.
> **MAYBE:** beats the in-study baseline with ≥ 40 trades, but fails ≥ 1 robustness
> dimension (concentration / a year / validation / cost stress).
> **FAIL:** expectancy @25bps ≤ in-study baseline, or negative, or < 40 trades.

Timestamp evidence: the README file (which contains the preregistration text) has
filesystem birth **2026-10-12 12:48:38 UTC**, before the run's output file
(crt_results.json, born 12:50:09 UTC); its final mtime (12:50:52 UTC) reflects the
Results section appended after the run. The gate is additionally not new to this
experiment: the README states it is the **same gate as sweep #1**, and sweep #1's
record — with the same gate framework and the same baseline figure — was committed
to the bridge record on **2026-09-28** (`research_notes/bridge_thread.md`, "outside-claims
sweep #1"), two weeks before the CRT run.

**Stated plainly (gap):** the CRT preregistration was NOT committed to git or posted
to any external record before the run; before today the artifacts existed only as
local files. The pre-run status of the gate rests on (a) local filesystem birth
times above, (b) the gate being the standing sweep gate documented in the committed
2026-09-28 sweep-#1 record, and (c) the run code's constants matching the prereg
text exactly (`crt_results.json` records `"gate": "README.md"`). No stronger
pre-run pin exists, and none is reconstructed here after the fact.

## 4. Authorization / budget anchor

- **Standing instruction:** the weekly outside-claims sweep — one best
  precise/mechanism-plausible outside claim per week, tested pre-registered,
  PASS/MAYBE/FAIL, research only. Established under Mike's 2026-09-24 spec and
  recorded in `~/memory/2026-09-28.md` ("Weekly outside-claims sweep (Mondays
  ~8:45 AM ET): single best precise/mechanism-plausible claim, PASS/MAYBE/FAIL;
  research only"). The CRT README states the same anchor: "weekly sweep,
  Mike-approved 2026-09-24."
- **This instance:** sweep #3, run Monday 2026-10-12 in the sweep slot. Claim
  source: @think_ict Instagram reel "Candle Range Theory (CRT) for Beginners",
  posted 2026-10-10 (https://www.instagram.com/reel/DeTuCZlBXQ9/), selected per
  the sweep's hard filter (precise 4H rule, plausible stop-hunt mechanism,
  OHLC-only, data on hand, family not previously tested).
- **Budget/effort:** zero spend, zero vendor calls, local compute only; nothing
  frozen touched (V5.4, Mode B definitions, production alerts unchanged —
  `pine_backtest.py` imported unmodified). Actual run-sequence effort evidenced
  by file timestamps: 2026-10-12 12:48:38 → 12:50:52 UTC (prereg file creation →
  results written → results section appended), i.e. the execution itself was a
  single short run inside the Monday-morning sweep session; claim selection and
  write-up occurred in the same session. Effort is timestamp-evidenced, not
  separately instrumented.
- **Reporting:** result posted to Slack #qualityflowscaner on Mike's instruction
  ("Tell slack"), message ts `1791810723.802559` (2026-10-12 13:32 UTC).

## 5. Data-source lineage

**What the run read — exactly one data source.** `run_crt.py` hard-codes
`CACHE = <repo>/pine_entry_timing_backtest/cache` and loads, per watchlist symbol,
`pd.read_pickle(CACHE / f"h4_{sym}.pkl")`. That is its only data input. The script
contains **no download code and makes no network calls** (verified by code
inspection: no `yfinance`/`requests`/HTTP references); it cannot fetch anything at
runtime. Symbols with missing/all-NaN Volume would be dropped by the loader; none
were (14 of 14 loaded).

**What that cache is.** The `pine_entry_timing_backtest/cache/h4_*.pkl` files are
the corrected 4H bar cache built for the entry-timing study line: **Yahoo
(yfinance) 1H bars resampled per-day into 09:30/13:30 ET-anchored 4H bins**
(first/max/min/last/sum), the convention documented for
`pine_entry_timing_backtest/fetch_resample_4h.py` and restated in
`canonical_baseline/UNIVERSE.md` ("Source: yfinance (free). No API keys exist in
this environment"; 4H coverage 2023-10-26 → 2026-09-24 for full-history names).
This is the same cache family used by sweeps #1 and #2, which is why the in-study
baseline reproduces the canonical +0.239R / 237 trades exactly.

**What it is not.** It is NOT `backtest_cache/v3/` (the CP1 defective fixed-UTC-grid
cache). `pine_backtest.py`'s own `CACHE` constant points at `backtest_cache/v3`,
but `run_crt.py` does not use that constant for data — it reads only its own
hard-coded entry-timing cache path. The defective v3 cache was not an input.

**Present-state pins of the input files** (sha256 / bytes, recorded 2026-10-13;
all 14 files currently carry filesystem birth 2026-10-12 16:49:58 UTC — see the
caveat below):

| file | bytes | sha256 (prefix) |
|---|---|---|
| h4_QQQ.pkl | 70,905 | `8ed86a95…` |
| h4_SMCI.pkl | 70,905 | `80b23fbc…` |
| h4_PLTR.pkl | 70,905 | `5a099edc…` |
| h4_ANET.pkl | 70,905 | `2bbb6cf9…` |
| h4_SOFI.pkl | 70,905 | `94423d0f…` |
| h4_RKLB.pkl | 70,905 | `96e34162…` |
| h4_ONDS.pkl | 70,905 | `5c221a50…` |
| h4_DRAM.pkl | 12,669 | `bf7571a2…` |
| h4_SPCX.pkl | 7,965 | `6b0004d8…` |
| h4_ASTX.pkl | 30,144 | `b54c5d34…` |
| h4_BBAI.pkl | 70,905 | `4b8d613d…` |
| h4_NIO.pkl | 70,905 | `d7195754…` |
| h4_HOOD.pkl | 70,905 | `0ae9ca4c…` |
| h4_AMD.pkl | 70,905 | `10caf02a…` |

(Full hashes are reproducible from the files as committed/staged with this package
set; eleven of the files share an identical byte length because they share shape —
same bar count and dtypes — while all 14 hashes are distinct.)

**Caveat (gap, stated plainly):** the cache files' current filesystem birth
(2026-10-12 16:49:58 UTC) postdates the run (~12:50 UTC). The daily log
(`~/memory/2026-10-12.md`) records why: that afternoon, during the Tiingo-note
commit sequence (f87b836), the pine cache pkls were among staged files swept into
a commit attempt, reset, and restored via `git stash pop` — a cycle that rewrites
working-tree files and resets their birth times. No hash of the input pkls was
taken before or during the run, so **the exact input bytes consumed by the run
are not independently pinnable after the fact**. The lineage claim therefore
rests on: the hard-coded single read path in the frozen code, the documented
yfinance provenance of this cache family, and the exact in-study baseline
reproduction (237 / +0.239R) against figures produced by prior independent
studies on the same cache. No claim stronger than that is made.

**Entitlement note:** the bars are Yahoo/yfinance downloads under the same
standing research use as all prior studies in this stack; no vendor entitlement
was relied on beyond that, and no paid or keyed source was involved.

## 6. Tiingo-hold statement

**No retained Tiingo input was read, opened, processed, or depended on by the
CRT run — at any point.** Specifically:

- The run executed 2026-10-12, i.e. **after** the Tiingo compliance hold took
  effect (2026-10-10). It complied with the hold by construction: its only data
  input was the Yahoo-derived entry-timing cache (§5).
- The retained Tiingo set (the ~444 raw EOD files, fundamentals files, derived
  panel and aggregates inventoried in
  `research_notes/TIINGO_TERMS_COMPLIANCE_INVENTORY_20261010.md`, in the phase1a
  tree) is a different directory tree that `run_crt.py` never references.
- Verification basis (code-path inspection, not data processing): (a) the frozen
  `run_crt.py` contains exactly one data-loading call — `pd.read_pickle` on the
  entry-timing cache path — and no other file reads besides its own output write;
  (b) `grep` finds zero occurrences of "tiingo" (any case) in `run_crt.py` and the
  CRT README; (c) the script has no network capability, so no Tiingo API call was
  possible from it; (d) no Tiingo-derived artifact (panel, aggregates, ORB report)
  is an input to any function the script calls — `pine_backtest.py`'s contributions
  are indicator/exit/portfolio logic over the loaded DataFrames only.
- This package itself was assembled without opening or processing any retained
  Tiingo file; the cache pkls were hashed for §5 as filesystem metadata only and
  their contents were not loaded for this package.

## 7. Execution definitions (as run)

- **Entry:** signal confirmed at close of bar i; fill at open of bar i+1; skipped
  if the entry open crosses the stop (canonical convention; 8 gap-through-stop
  skips in CRT-LONG accounting, per README attribution).
- **Stop:** the sweep extreme (bullish: low of signal bar; bearish: high) — the
  claim's own risk definition, an explicitly stated adaptation replacing the
  canonical 1.5·ATR stop while preserving the Mode B TP1 ratio (TP1 at
  1.333 × risk).
- **Exits:** canonical Mode B mirrored bar-for-bar from `gen_pine_trades`
  (TP1 limit intrabar, 50% at TP1; +1R arms Profit Protect runner trail at
  close ∓ ATR·TRAIL_ATR; close-evaluated exits filled at next-bar open; stop wins
  ties; EMA55/EMA200 trend exits mirrored for shorts). The reel's "target = the
  reference candle's other end" was NOT used; the test isolates the ENTRY claim.
- **Portfolio:** `simulate_portfolio` semantics at 1% risk/trade, max 5 concurrent
  positions, 5% total heat, start equity 10,000 (engine constants, §1). Costs at
  4/25/50/75/100 bps; the gate is scored at 25 bps with the 50 bps stress leg.
- **Splits:** development Oct 2023–Dec 2024 vs validation Jan 2025–Sep 2026;
  per-year and per-symbol breakdowns in `crt_results.json`.

## 8. Limitations and remaining gaps

1. **Input bytes not pinnable** (§5 caveat): no pre-run hash of the cache files
   exists, and the working-tree copies were rewritten by a git stash cycle hours
   after the run. Lineage is code-path + provenance + baseline-reproduction
   evidence, not byte identity.
2. **Preregistration not externally timestamped before the run** (§3): local file
   birth times + the standing gate documented in the committed 2026-09-28 record
   are the anchors; no pre-run commit or post exists.
3. **Short-side concentration:** CRT-SHORT's positive headline is a single-name
   artifact (HOOD +309.7R of +137.6R total). It is reported as adverse/context
   evidence, not as a candidate signal; the same HOOD lottery pathology appeared
   in sweep #2.
4. **Stop geometry is part of the verdict:** expectancy is negative even aside
   from sizing, but the ~100% maxDD figures are driven by the claim's
   stop-at-the-extreme geometry (risk fractions down to 5e-5). A reader should
   not quote maxDD as a property of a tradable system; it is evidence the
   geometry is untradable in fixed-fractional terms.
5. **Ambiguous bars:** 495 bars swept both extremes and closed back inside; they
   were skipped per the preregistered rule and are reported in the attribution
   counts, not silently dropped.
6. **Cache coverage:** 4H bars span Oct 2023–Sep 2026 per the cache's documented
   coverage; names with shorter histories (SPCX, ASTX, DRAM) contribute fewer
   bars, as in prior studies. Per-symbol trade counts and R are in
   `crt_results.json`.
7. **Effort not instrumented** (§4): run timing is bounded by file timestamps
   only.

## 9. What this package does not do

It does not rerun, repair, or extend the experiment; it does not seek execution
clearance, forward paper, or any change to the FAIL record; it does not touch the
Tiingo disposition, Twelve Data, VCP, or any frozen system. Adjudication of the
CRT verdict remains ChatGPT's, on this evidence.

— Muse, 2026-10-13
