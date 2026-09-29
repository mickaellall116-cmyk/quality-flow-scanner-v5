# Data Leakage & Corporate-Actions Audit — Quality Flow Scanner Research

**Date:** 2026-09-24 · **Scope:** 14-stock watchlist, Oct 2023–Sep 2026, baseline 237 trades / +0.2388R
**Auditor scope:** data quality + look-ahead leakage only. `pine_backtest.py` imported unmodified, never edited.
**Scripts:** `research_audit/data_leakage/audit_*.py` · **Evidence JSON:** `data_quality_details.json`,
`rklb_trade_verification.json`, `rs_leakage_quant.json`, `lonewolf_strict_sim.json`

---

## 1. DATA QUALITY — verdict: PASS

### 1.1 OHLC pipeline
The 4H backtest data flows: yfinance 1H (`auto_adjust=False`, `prepost=False`, 730d)
→ resampled within-day to 4H bins anchored 09:30 (`pine_entry_timing_backtest/fetch_resample_4h.py`).
The live path uses `auto_adjust=True` via `masterscanner_api.download_data` → `scanner_rules.resample_closed_4h`.

| Check | Result |
|---|---|
| Bad candles (high<low, high<max(O,C), low>min(O,C)) | **0** across all 14 symbols |
| NaN OHLC rows | **0** |
| Zero-volume bars | **0** |
| Duplicated timestamps | **0** |
| Timezone | all `America/New_York`, consistent |
| 4H bar starts | only 09:30 / 13:30 ET |
| 1H bars outside 09:30–16:00 ET (premarket contamination) | **0** (`prepost=False` honored) |
| Days with exactly 2 bars | 99.0% (the 7 one-bar days are exact US half-days: 2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24, 2025-07-03, 2025-11-28, 2025-12-24) |
| Gaps > 4 calendar days | none |

### 1.2 Splits / corporate actions
- **SMCI 10:1 split (effective 2024-10-01): handled.** Close before split window ~$41.71 vs after ~$40.31
  (1.03× — normal price movement, no 10× discontinuity). `auto_adjust=False` still split-adjusts OHLC.
- **ASTX (2× leveraged ETF, frequent reverse splits):** no overnight jump ≥4× in the whole series.
- No ticker changes among the 14.
- Dividend treatment differs between paths (4H/live `auto_adjust=True` vs daily `auto_adjust=False`),
  immaterial for these studies (sub-basis-point effect on 20-day returns).

### 1.3 Coverage note (not an error)
Heterogeneous history starts: DRAM 2026-04-02 (240 bars), SPCX 2026-06-12 (142 bars),
ASTX 2025-07-11 (604 bars); the other 11 run 2023-10-25 → 2026-09-23 (1453 bars).
Early-period statistics are dominated by the 11 full-history names — an unbalanced panel to keep in mind,
not a data error.

### 1.4 Trade arithmetic verification
- Regenerated all 237 canonical trades with the **unmodified** engine (`pb.gen_pine_trades`):
  count **237 = 237**, mean net R @25bps **+0.2388 = +0.2388** — the published baseline reproduces exactly.
- **Top-5 P&L trades** (HOOD +8.67R, RKLB +6.69R, ONDS +6.68R, AMD +5.88R, SOFI +5.85R):
  every entry matches the raw next-bar open and every stop matches `signal close − 1.5×ATR`
  to the tick; R multiples recomputed from stored exits match exactly.
- **RKLB +12.98R (signal 2024-09-09 09:30 ET):** this trade is **not** in the canonical 237 —
  it is an FVG-only trade from `pine_fvg_attribution`. Replicated with the study's FVG signal +
  unmodified engine: signal bar 5.88/6.275/5.88/6.2305 → entry 6.23 (next-bar open), stop 5.7943
  (close − 1.5×0.2908 ATR), TP1 6.8115, exit 11.9008 after 97 bars ("stop" = runner trail close,
  correct Pine semantics). Blended net R recomputed **12.9809 = 12.9809**. Arithmetically correct;
  the trade is real data, not an artifact.

---

## 2. LOOK-AHEAD LEAKAGE — per-feature table

| Feature | Code | Bars used | Verdict |
|---|---|---|---|
| **SPY RS (live)** | `masterscanner_api.py:197-199` (`classify_symbol`) — `df.iloc[-1]` / `market_df.iloc[-1]`, both from `download_data` → `resample_closed_4h` (forming bar excluded) | closed bars only | PASS |
| **SPY RS / Sector RS (studies)** | `pine_sector_rs_backtest/run_sector_rs.py:89-98` (`ret20`), `pine_lonewolf_backtest/run_lonewolf.py:ret20`; join at signal date | **signal-date daily close** | **WARNING — genuine mild leak (see §3)** |
| **ADX** | `pine_backtest.py:105-114` (causal Wilder EWM); ranking uses `df[col].iloc[i]` at signal bar `i` (`pine_ranking_confirm/run_ranking_confirm.py:34-58`) | ≤ signal bar | PASS |
| **FVG** | `pine_entry_timing_backtest/run_entry_timing.py:40-78` — state machine `low[i] > high[i-2]`, all reads at index `i`; sidecar `v54_fvg_sidecar.py:128-143` scans `[start, len(df)-1)` on closed-bar feed | ≤ signal bar | PASS |
| **BOS/CHOCH** | `pine_setup_age_backtest/run_setup_age.py:60-79` — `.shift(1).rolling().max()`, `low > high.shift(2)`; `last_event_age` slices `[:pos+1]` | ≤ signal bar | PASS |
| **Market regime (live)** | `masterscanner_api.py:187-226` (`get_market_regime`) — closed 4H bars, backward EMA/momentum/VIX only; V5.4 regime is computed at cycle time for the current closed bar | closed bars only | PASS |
| **Market regime (studies)** | `pine_regime_backtest/run_regime.py:113-130` (`searchsorted(sig_date, right)-1`); `pine_adx_protocol/run_adx_protocol.py:96-104` (`regime_at`) — backward indicators, joined at the signal **date** | same mild same-day leak as RS | WARNING (descriptive bucketing only; no filter adopted — low impact) |
| **Ranking inputs** | `pine_ranking/pine_ranking.py:95-114`; `bench_ret` = last daily bar ≤ timestamp (`pine_signal_quality/pine_signal_quality.py:49-60`); contests ranked at signal bar, one bar before entry | ≤ signal bar | PASS |
| **Exits** | `pine_backtest.py:190-240` — stop/TP1 frozen from **signal-bar ATR** (`sig["atr"]`), never updated; runner trails `close − ATR(current bar)` (known at that close). Mode B `v54_exit_tracker.py:83-108, 120-215` — stop/TP1 stored at open, never moved; `+1R` arming from completed-bar highs only | entry-time levels + completed bars | PASS |
| **Earnings/events** | `pine_timefx_backtest/run_timefx.py:47-80` — actual dates from yfinance, ±5d bucketing; descriptive only (post-earnings thread is watch-only, no filter adopted) | n/a | PASS (low concern) |
| **Lone-wolf overlay (live)** | `v54_lonewolf_overlay.py:180-215` (`classify`) — for a signal fired today, endpoint = **last completed daily bar** (`asof = today − 1d`); `searchsorted(asof, right)-1` can never select today's forming bar | strictly historical | PASS |
| **FVG sidecar (live)** | `v54_fvg_sidecar.py` — signals on completed bars only (see FVG row); pending entries fill at next **completed** bar open (feed excludes forming bars) | closed bars only | PASS |

Notes:
- `v54_forward_harness.py:124-139` (`v53_state_for_bar`) passes the *current-cycle* regime into the
  per-bar V5.3 state used for armed-EXIT detection, but V5.3's `state` (BUY/EXIT/…) is purely
  technical (`classify_symbol` exit/signal triggers) and regime-independent — no leakage path.
- The lone-wolf overlay's **backfill** of past signals replicates the study's signal-date convention
  (see §3); only new live intraday signals use the strict last-completed-bar convention.

---

## 3. THE ONE GENUINE LEAK: signal-date daily close in the RS studies

**Mechanism.** `ret20` uses the *signal date's* daily close as the 20-day-return endpoint
(`daily_closes_4h` = full-day `resample("1D").last()`; ETF daily caches = session closes).
A signal fired on the first 4H bar (09:30–13:30) therefore sees the 13:30–16:00 bar —
up to ~6.5 hours of data not known at signal time. **91.1% of the 237 baseline signals fire on the
first 4H bar**, so this is not a corner case.

**Quantified impact** (strict point-in-time = live-overlay convention: first-bar signals use the
signal-bar close for the stock leg and the previous trading day's close for ETF legs; second-bar
signals unchanged since the 13:30 bar closes at 16:00 = daily close):

| Metric | Study method | Strict PIT |
|---|---|---|
| Lone-wolf blocked trades (per-trade) | 83 @ **−0.0183R** | 93 @ **+0.0616R** |
| Allowed (per-trade) | 154 @ +0.3773R | 144 @ +0.3532R |
| NO_LONE_WOLF through real portfolio sim (taken / exp / blocked) | 137 / **+0.3797R** / 74 @ +0.0639R | 129 / **+0.3646R** / 82 @ +0.0961R |
| CONTROL (sim) | 180 / +0.2721R | — |

- 18 of 83 lone-wolf classifications flip; 24 of 237 P10 bucket assignments flip.
- The strict variant would have blocked the sample's biggest winner: **HOOD 2025-04-29 (+8.67R)** —
  study method keeps it, strict blocks it.
- My strict sim reproduces the published study-method numbers exactly
  (137 taken / +0.3797R / blocked 74 @ +0.0639R = `lonewolf_results.json`), so the comparison is apples-to-apples.

**What it invalidates.**
1. The lone-wolf protocol's supporting claim "blocked 83 trades at −0.0183R (genuinely dead money)":
   under strict PIT the blocked set is 93 trades at **+0.0616R** — and even under the study's own
   convention, the *portfolio-relevant* blocked subset (74 the sim would actually take) was
   **+0.0639R**, already not dead money. The −0.0183R was a pre-capacity per-trade figure on a
   different subset — operationally misleading.
2. It weakens (but does not kill) the TEST 1 PASS: the filter's edge over control shrinks from
   **+0.1076R to +0.0925R** per taken trade (~14% smaller), and the edge is more concentrated
   (fewer, different blocked trades). The verdict should carry this caveat; the live overlay's
   conservative intraday convention means live results will track the *strict* numbers, not the
   published study numbers.
3. P10 sector-RS bucket stats (both_pos/stock_lead/…) shift by 24 flipped assignments — direction
   and significance of the MAYBE should be re-read with strict labels before any post-verdict use.

**What it does NOT invalidate:** the canonical 237-trade baseline (+0.2388R), the engine, exits,
grades, or any live forward-test logging — none of them consume RS.

---

## 4. VERDICTS

- **Data quality: PASS.** Splits handled (SMCI 10:1 verified, no 4× discontinuities incl. ASTX),
  zero bad/duplicate/zero-volume candles, timezone-consistent, no premarket contamination,
  no missing-bar gaps; half-days correctly single-bar. Top-5 trades and the RKLB +12.98R trade
  re-derived from raw bars to the tick.
- **Look-ahead leakage: WARNING (one genuine finding).** Everything is point-in-time except the
  RS studies' signal-date daily-close endpoint (§3), a mild same-day leak affecting 91% of signals,
  which (a) kills the "blocked = dead money" claim, (b) shrinks the lone-wolf edge from +0.1076R
  to +0.0925R, and (c) means the live overlay (strict convention) will underperform the published
  study numbers slightly. All live systems (lone-wolf overlay, FVG sidecar, Mode B tracker,
  regime gate, ranking) are verified clean and cannot see future data.

## 5. RECOMMENDED FOLLOW-UPS (for the parent, not done here)
1. Re-run the P10 bucket stats and the lone-wolf TEST 1 headline table under strict PIT and amend
   the protocol README — the published "blocked 83 @ −0.0183R" line should not stand.
2. Note in the lone-wolf overlay docs that backfilled past signals carry the study convention while
   new signals carry the strict convention — the overlay log mixes two RS conventions.
3. No data or code fixes needed: the leak is measurement-only, confined to two research scripts.
