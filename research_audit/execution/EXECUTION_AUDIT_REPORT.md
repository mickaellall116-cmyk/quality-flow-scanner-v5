# Execution Realism & Transaction Cost Audit — Quality Flow Scanner Research

**Date:** 2026-09-24 · **Auditor:** subagent (read-only; nothing modified outside `research_audit/execution/`)
**Scope:** the +0.2388R / 237-trade baseline (14-stock watchlist, Oct 2023–Sep 2026, 4H) that every
candidate study (lone-wolf, ADX, ranking, FVG, CORR_07) builds on. All of them generate trades via
`pine_backtest.gen_pine_trades` (imported unmodified everywhere — verified by grep).

**Headline finding:** the research baseline does **not** implement the frozen Mode B exit stack.
It models Pine V3.6 *strategy* semantics (close-evaluated exits, no resting stop). Mode B
(resting stop, Profit Protect, 30-bar timeout) lives only in `v54_exit_tracker.py`, which the
forward test uses. Under resting-stop execution the same 237 entries make **+0.076R, not +0.239R**
(**−0.163R / −68%**). The baseline is a valid model of V3.6 paper — it is not a valid prior for
the Mode B forward test.

---

## 1. Fill-assumption table — `pine_backtest.py` (canonical backtester)

| # | Assumption | File:lines | What the code does | Realism |
|---|---|---|---|---|
| 1 | Entry fill | `pine_backtest.py:149` | `entry = float(df["Open"].iloc[i+1])` — fills at the **next 4H bar's open** after the signal bar, exact price, **zero slippage** | optimistic (small) — real MOO fills deviate a few bps |
| 2 | Entry gaps below stop | `pine_backtest.py:151-153` | Signal **skipped entirely** if `entry <= stop0` (1 such skip in the 237-trade run) | realistic — you'd cancel the order |
| 3 | Initial stop | `pine_backtest.py:153,179-181,186-188` | `stop0 = signal_close − 1.5×ATR`. **No intrabar stop exists.** Exit triggers only when bar **close < runner**, then fills at the **next bar's open** (exact price, zero slippage) | **optimistic vs a resting stop** — any intrabar dip below the stop that recovers by the close avoids the exit. Faithful to the V3.6 Pine strategy (which never passes `stop=` to `strategy.exit`; `pine_live/exits.py:19-24,153` is character-faithful to this) but **wrong vs Mode B live**, which uses a resting stop |
| 4 | Gap through stop | `pine_backtest.py:186-188` | If close triggered the exit, fills at next **open** however far through the stop it gapped — directionally correct for a stop-market order, but at the **exact open, zero slippage** | realistic direction, optimistic price |
| 5 | TP1 detection & fill | `pine_backtest.py:171-172` | `if not tp_hit and hi >= tp1:` → 50% filled at the **exact TP1 limit price** | realistic detection; fill-at-limit is **conservative** (a real limit gapping above TP1 fills at the better open — the code ignores that improvement) |
| 6 | Profit Protect | — | **Not implemented.** No +1R arming, no pending-exit logic anywhere in `pine_backtest.py` | **wrong vs Mode B spec** — the frozen stack's signature feature is absent from the research |
| 7 | Profit Protect next-bar-open fill | — | N/A in backtester. (It IS implemented in Mode B: `v54_exit_tracker.py:141-147` — `pending_exit` fills at `float(bar["open"])`, zero slippage) | Mode B impl. verified; backtester has nothing to verify |
| 8 | Same-bar stop/TP1 tie | — | **Not implemented** in backtester (no intrabar stop, so ties can't occur; "stop wins" appears only in the docstring, `pine_backtest.py` header). Mode B implements it: `v54_exit_tracker.py:150-152` (`if lo <= stop:` checked before TP1) | **wrong vs Mode B spec** |
| 9 | 30-bar timeout | — | **Not implemented** (module docstring: "No max hold (Pine has none)"). Mode B implements it: `v54_exit_tracker.py:29,178-183` (exit at bar close) | **wrong vs Mode B spec** |
| 10 | Trailing runner | `pine_backtest.py:174-175` | After TP1, `runner = max(runner, close − 2.5×ATR)` updated **at bar close only**; exit only on close < runner | optimistic — a live trailing stop ratchets/stops intrabar |
| 11 | EMA55 / trend-bear exits | `pine_backtest.py:182-188` | Close-evaluated → next bar open, exact price | realistic (signal-based exit, no resting order; matches live V3.6) |
| 12 | Slippage | — | **None anywhere** in trade generation | optimistic (small — see §2) |
| 13 | Costs | `pine_backtest.py:214-218` (`_outcome`) | `net_ret = gross_ret − cost`, **one flat deduction per trade** (25bps headline), applied to the blended exit | optimistic structure — a real trade pays entry + TP1 partial + runner exit (≈2 full-size one-way legs); see §3 |
| 14 | End-of-data | `pine_backtest.py:190-191` | Fills at bar close if no next bar | realistic (edge case) |

**Mode B cross-check** (`v54_exit_tracker.py`, the forward-test/live implementation): resting stop
intrabar at exact stop price (`:151-152, :169-170`) — **gap-through-stop fills at the stop price,
not at the open beyond it** (optimistic even vs a stop-market order); PP arms on bar high ≥ +1R
(`:189-197`, sticky) and fills at next-bar open (`:141-147`); stop wins ties (`:150`); 30-bar timeout
at bar close (`:178-183`); zero slippage anywhere.

---

## 2. Conservative replay — modeled vs conservative expectancy

Script: `research_audit/execution/conservative_replay.py` (results:
`conservative_replay_results.json`). Replays the exact 237 baseline trades bar-by-bar.
Conservative model: entry at open +5bps adverse; **resting stop-market** (stop wins same-bar ties);
gap-through-stop (bar open ≤ stop) filled **at the open** −10bps; intrabar stop touch filled at
stop −10bps; TP1 detection unchanged (`high ≥ TP1`), 50% at exact limit; EMA55/trend exits at
next open −5bps; R denominated in the **planned** risk unit so the gap is pure execution.
Slippage rationale: 5bps ≈ 2–3× typical 1–3bps effective spreads on these names, tiny vs the
~6.2% mean planned risk width; 10bps on stop-markets covers spread widening into adverse momentum,
still ≪ the 1.5×ATR stop distance.

| Metric | Modeled (baseline) | Conservative | Gap |
|---|---|---|---|
| Expectancy @25bps | **+0.2388R** | **+0.0757R** | **−0.1630R (−68%)** |
| Win rate | 50.6% | 44.3% | −6.3pp |
| TP1 hit rate | 53.2% | 46.0% | −7.2pp |
| Avg hold (bars) | 18.6 | 13.1 | −5.5 |

Decomposition (per-trade, same 25bps cost):
- **Slippage-only** (keep close-evaluated exits, add 5bps entry + 5bps market fills): −0.0244R → 0.2143R.
  This is the honest execution haircut **for the V3.6 system the baseline actually models**
  (live V3.6 paper uses the same close-evaluated exits — verified `pine_live/exits.py`).
- **Intrabar resting stop only** (zero slippage): **−0.1386R**. 216/237 trades (91%) touched the stop
  intrabar on a bar whose close stayed above it; 38/237 (16%) gapped through the stop and were
  filled at the open beyond it. Median per-trade delta is +0.05R (early stops dodge some losers)
  but the mean is −0.14R — the resting stop **clips eventual winners** (worst single-trade delta −9.7R).

Unmodeled Mode B features (diagnostics, not in the replay — adding them would conflate execution
with rule changes): **43/237 trades (18%) were held >30 bars**; those trades total **+113.9R** in the
baseline, i.e. the absent 30-bar timeout binds almost exclusively on winners. Profit Protect arming
(+1R) has no baseline counterpart at all.

---

## 3. Transaction costs

### 3a. Collation of existing 25/50/75/100bps sweeps

Expectancy (net R) by cost. All from the studies' own JSON outputs.

| Study / variant | 25bps | 50bps | 75bps | 100bps | Notes |
|---|---|---|---|---|---|
| Baseline (237 trades) | **0.2388** | 0.1777 | 0.1167 | 0.0556 | lone-wolf + FVG-robustness agree exactly; −0.061R per +25bps, linear |
| Lone-wolf retained (154) | **0.3773** | 0.3143 | 0.2512 | 0.1881 | ΔE vs baseline: 0.139 / 0.137 / 0.135 / 0.133 — edge is cost-robust |
| Lone-wolf blocked (83) | −0.0183 | — | — | — | dead money at every cost |
| FVG (robustness) | 0.2852 | 0.2245 | 0.1637 | 0.1030 | survives costs; still FAIL on protocol grounds |
| ADX vs take-all (per-contest, n=21) | +0.350 | +0.364 | +0.378 | +0.392 | contest-level advantage only, not population expectancy |
| ADX vs rs_top2 (per-contest, n=21) | +0.583 | +0.558 | +0.533 | +0.507 | same caveat |
| Ranking-confirm (25bps only) | take-all 0.221 / adx 0.314 / rs_spy 0.160 | — | — | — | n≈178 (5-slot cap), different population |
| CORR_07 (25bps only) | control 0.272 / CORR_07 0.321 | — | — | — | n=180/165 (admission sim), different population |

### 3b. Liquidity/volatility-adjusted cost — feasible?

**Feasible: yes for impact, estimated for spread.** Script: `research_audit/execution/cost_model.py`
(results: `liquidity_cost_estimate.json`). The pipeline has 4H OHLCV for all 14 symbols
(zero zero-volume bars). No quote/spread data exists, so spread is estimated via Corwin-Schultz
on 4H bars — an **upward-biased upper bound** (QQQ prints 7.5bps half-spread vs ~1bp true effective).
Impact model: 10bps per 1% of ADV participation. Sizing per the standing rule
(research: $10k/1% = $100 risk; live: $75k/$750 risk; notional = risk/risk_frac).

- **Impact ≈ 0 at any realistic size**: avg participation 0.0002% of ADV (research) / 0.0017% (live),
  max 0.012% (NIO, live). Even a 10× size-up wouldn't register.
- **All-in one-way cost (trade-weighted avg): ~29bps** (spread 29 + impact 0.0) — upper bound;
  realistic range ~10–20bps given the CS bias. Per-symbol: QQQ 7.5bps → ASTX 77bps, ONDS 73bps,
  BBAI 46bps, RKLB 38bps.
- **Structural point:** the studies deduct 25bps **once per trade**, but a real trade pays
  entry + TP1 partial + runner exit ≈ **2 full-size one-way legs**. So 25bps/trade ≈ 12.5bps/leg
  vs an estimated ~10–29bps/leg → realistic per-trade cost ≈ **20–58bps**, not 25bps.
  At the empirical −0.061R/25bps sensitivity: realistic costs shave **−0.01 to −0.08R** off the
  baseline (0.2388 → ~0.16–0.23R). Thin names (ONDS/ASTX/BBAI) likely cost 2–6× the flat
  assumption — a per-trade understatement of up to ~0.2R on those names.
- DRAM and SPCX produced **zero** baseline signals in 3 years (their LOSO rows show n=237 unchanged)
  — no cost estimate needed; noted for completeness.

---

## 4. Verdicts

### Execution realism: **FAIL** (as a model of the frozen Mode B system) / Warning (as a model of V3.6)

- The research baseline implements **zero** of the four Mode B exit features (no intrabar stop,
  no Profit Protect, no stop-wins-ties, no 30-bar timeout). The numbers Mike sees (+0.2388R and
  every candidate delta) describe the **V3.6 Pine strategy**, not the forward test that is supposed
  to validate them.
- Under resting-stop execution the same entries make **+0.076R (−0.163R, −68%)**; the 30-bar timeout
  would additionally cut into the +113.9R sitting in 43 over-held trades. The baseline is not a
  valid prior for Mode B forward-test performance — treat the forward test as starting from
  ~zero evidence, not from +0.24R.
- Narrower claim — "the backtest faithfully models V3.6 paper": **Warning**, haircut only **−0.024R**
  (slippage). `pine_live/exits.py` is character-faithful to the backtester, so V3.6 paper/live and
  research agree with each other; they just aren't Mode B.
- Separately: Mode B's own implementation is optimistic in one spot — `v54_exit_tracker.py:151-152`
  fills gap-through-stop **at the stop price** instead of at the open beyond it.

### Transaction costs: **Warning**

- The flat 25bps is in the right zone on average (estimated all-in one-way ~10–29bps; impact ≈ 0),
  and every cost sweep shows edges surviving to 100bps — not a Fail.
- But: (a) the once-per-trade deduction understates the 2-leg reality by ~5–33bps/trade
  (**−0.01 to −0.08R** on the baseline); (b) thin names (ONDS/ASTX/BBAI) cost multiples of the flat
  rate; (c) no spread data exists in the pipeline, so the spread leg is an upward-biased estimate,
  not a measurement. Candidate edges are cost-robust in *relative* terms (lone-wolf ΔE 0.133–0.139R
  across the sweep), but absolute expectancies should be read ~0.02–0.08R lower than printed.

### Estimated impact on the +0.2388R baseline and candidates

| Adjustment | Baseline 0.2388R → | Lone-wolf retained 0.3773R → | ADX / CORR_07 |
|---|---|---|---|
| Slippage-realistic (V3.6 semantics) | ~0.214R (−0.024) | ~0.35R (−0.024, parallel shift) | parallel shift |
| Realistic multi-leg costs (~35bps/trade) | ~0.20R (−0.04) | ~0.34R | parallel shift |
| Upper-bound costs (~58bps/trade) | ~0.16R (−0.08) | ~0.30R | parallel shift |
| **Mode B resting-stop execution** | **~0.076R (−0.163)** | not recomputed — same clipping mechanism applies; ΔE sign cost-robust but absolute level unmeasured under resting stops | unmeasured |

**Recommended follow-ups (for parent, not done here):** (1) re-run the headline studies with a
resting-stop + PP + 30-bar Mode B exit stack so research and forward test speak the same language;
(2) fix `v54_exit_tracker.py:151-152` gap-through-stop fill to the bar open; (3) replace the flat
25bps with a per-trade 2-leg cost (or at least 35–50bps/trade) and a thin-name surcharge.

**Files:** [conservative_replay.py](sandbox://workspace/quality-flow-scanner-v5/research_audit/execution/conservative_replay.py),
[cost_model.py](sandbox://workspace/quality-flow-scanner-v5/research_audit/execution/cost_model.py),
[conservative_replay_results.json](sandbox://workspace/quality-flow-scanner-v5/research_audit/execution/conservative_replay_results.json),
[liquidity_cost_estimate.json](sandbox://workspace/quality-flow-scanner-v5/research_audit/execution/liquidity_cost_estimate.json)
(all under `~/workspace/quality-flow-scanner-v5/research_audit/execution/`).
