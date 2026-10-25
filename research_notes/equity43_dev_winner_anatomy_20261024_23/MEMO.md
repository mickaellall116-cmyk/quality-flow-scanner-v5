# -23 DEEP Winner Anatomy — Final Auditable Memo (CLOSES -23)

Task QF-EQUITY43-DEV-WINNER-ANATOMY-20261024-23 (deep expansion). Governing: Issue #1 comment 6391746367; desk exchange: opening position (bridge 7457c68, Slack TS 1792890881.675409), ChatGPT counter-read (thread replies 1792891329.772059, 1792891431.600999, 1792891491.658709), scope ACK (bridge 53c599a, Slack TS 1792891985.498059).

**Nature of this document:** offline diagnostic on pinned artifacts only. No new strategy runs, no backtests, no vendor calls, no holdout access, no tuning, no rule-change recommendations. The October V5.4 FAIL verdict is untouched. Production PAUSED untouched; the feed-measurement pilot untouched.

## 0. Pins and reproducibility

- Trade ledger: `research_notes/equity43_dev_order_censor_20261023_13/trade_ledger.json`, sha256 `267e794c284a409d7d9b6d8e1056c452976b59746062e9e18c5664b74c003b` (-13 package commit `521980a`).
- Results: same package `results.json`, sha256 `42b05ce32ce545e95b919692ad3736316f8f42d9f603b1db42005342be413956`; config pin `87b8285a…`; forensic attribution (-14) `attribution_state.json` sha256 `c6e71da21d53da6f7f4f59013f330d445a2fae463b9a5962e0400354a40353e4`.
- Simulator source: -13 package `run_study13.py` (`gen_candidates_censored`, lines 499–573) over `pine_backtest` constants TP_ATR 2.0 / SL_ATR 1.5 / TRAIL_ATR 2.5 / WARMUP 215; candidate generation has **no max hold**.
- Bars for the intrabar audit: pinned 1h captures in the -13 stage archive clone (`td_pilot_20261023`, `td_capture_equity39_continue_20261023`), aggregated locally into the two session 4H bins. **Verification: reconstructed bar Open at entry equals the ledger entry price for 191/191 taken candidates, exact float equality; 1,043 reconstructed 4H bars per symbol.** Aggregation script `deep2.py` (this package); census script `deep1.py`.
- All R figures below are recomputed from the pinned ledger and tie to -13/-14 exactly (see §1).

## 1. Denominator reconciliation (exact, no residual)

| Quantity | Count | Decomposition |
|---|---|---|
| Candidates generated | 590 | 586 closed + 4 censored |
| Dispositions over 590 | 590 | taken 191, skipped_rank 326, skipped_risk 45, skipped_gate 28 |
| Taken | 191 | 187 closed + 4 censored |
| Censored (terminal-open, all taken) | 4 | CRM, MRNA, PFE, SHOP |
| Closed candidates | 586 | taken 187, skipped_rank 326, skipped_risk 45, skipped_gate 28 |
| Taken closed | 187 | gross **+34.8454R**, net @4bps **+32.4873R** (ties -13/-14) |
| Top 5 taken closed | 5 | net **+30.6600R** = 94.37% of total |
| Remaining taken closed | 182 | net **+1.8273R** (+0.0100R/trade) |

## 2. (A) Full census of the 187 taken closed trades

Exit-path × TP1-reached (net @4bps):

| Exit path | TP1 reached | n | Net R | Positive |
|---|---|---|---|---|
| stop (trailing runner, close-based) | yes | 92 | **+144.2131** | 87 |
| stop | no | 69 | **−94.6100** | 0 |
| ema55-break | yes | 3 | +1.7962 | 3 |
| ema55-break | no | 23 | −18.9120 | 0 |
| **Total** | | **187** | **+32.4873** | **90** |

Descriptive facts (in-sample, path-selected — see §8/H1 before interpreting):

- TP1 was reached in 95/187 trades (50.8%). **Every one of the 92 trades that never reached TP1 closed negative; every one of the 90 positive trades had reached TP1.** TP1 reach perfectly separates sign in this ledger. It is an outcome of the price path, not a decision-time variable.
- Exit-path attribution (descriptive, NOT causal — counter-read point 1, accepted): stop-path exits sum +49.6031R over 161 trades; ema55-break exits sum −17.1158R over 26.
- Holding time: median 11 bars (range 1–139); top-5 median 34 bars; rest median 10.5.
- Entry-year split: 2025 — 95 trades, +3.3768R; 2026 — 92 trades, +29.1105R. (DEV window opens Sep 2024; first taken entries occur in 2025.) The window's profit is concentrated in time as well as in names.

## 3. (F) Risk consistency

- Planned loss is −1R by construction (initial stop = signal Close − 1.5·ATR; entry next-bar Open; gap-through candidates with entry ≤ stop are rejected at generation).
- Realized gross losses exceed plan structurally: of 97 gross losers, **66 lost more than −1.0R gross** (52 more than −1.1R; worst −3.1113R). Cause is in the model itself: exit triggers evaluate on bar Close and fill at the NEXT bar's Open, so adverse gaps between trigger close and fill open add loss beyond the stop distance. This is a simulator-modeled effect, not a data error — and it would also occur live with close-based exits.
- Initial stop width: median 3.86% of entry (range 0.61–13.67%); top-5 median 4.65% (range 2.85–5.04%). No stop-width separation between winners and the rest is claimed beyond these medians.
- Position-size/share telemetry is not in the ledger (portfolio heat is a portfolio-layer quantity); risk consistency is therefore assessed in R space only.

## 4. (B) The five winners — timelines and matched counterexamples

All five: TP1 reached, exited via the trailing-stop path. `exit` is the ledger's synthetic blended exit value (50% at TP1 + 50% at exit fill), not a single traded price.

| Symbol | Signal | Entry | Stop → TP1 | Exit (time, synth) | Hold | RS | Sector | Gross / Net R |
|---|---|---|---|---|---|---|---|---|
| SNOW | 2026-05-26 13:30 | 2026-05-27 09:30 @ 174.68 | 169.70 → 185.29 | 2026-06-03 13:30, 215.02 | 11 | 0.1622 | AI_SOFTWARE | +8.1014 / +8.0874 |
| INTC | 2025-08-18 09:30 | 2025-08-18 13:30 @ 23.77 | 22.58 → 25.38 | 2025-11-04 13:30, 31.47 | 110 | 0.1842 | SEMIS | +6.4252 / +6.4172 |
| AMD | 2026-04-02 09:30 | 2026-04-02 13:30 @ 215.18 | 204.96 → 228.80 | 2026-04-28 13:30, 275.73 | 34 | 0.0842 | SEMIS | +5.9265 / +5.9181 |
| QCOM | 2026-04-28 09:30 | 2026-04-28 13:30 @ 150.74 | 144.88 → 158.62 | 2026-05-12 13:30, 182.16 | 20 | 0.0989 | SEMIS | +5.3573 / +5.3470 |
| LRCX | 2025-12-18 09:30 | 2025-12-18 13:30 @ 165.24 | 157.56 → 175.40 | 2026-02-04 09:30, 202.84 | 60 | 0.0720 | SEMIS | +4.8989 / +4.8903 |

Matched counterexamples (same sector, closest recorded RS among losing taken trades — the counterexample discipline of governing §A):

| Winner | Counterexample | RS (Δ) | Path | Net R |
|---|---|---|---|---|
| SNOW | DDOG 2026-06-04 | 0.1318 (0.0304) | stop, no TP1, 4 bars | −1.0488 |
| INTC | MU 2026-03-19 | 0.1934 (0.0092) | stop, no TP1, 4 bars | −1.5593 |
| AMD | LRCX 2026-07-01 | 0.0711 (0.0130) | stop, no TP1, 1 bar | −1.4809 |
| QCOM | INTC 2026-03-16 | 0.1013 (0.0024) | ema55-break, no TP1, 1 bar | −0.8202 |
| LRCX | LRCX 2026-07-01 | 0.0711 (0.0009) | stop, no TP1, 1 bar | −1.4809 |

(The same July-2026 LRCX loser is the nearest-RS same-sector counterexample for both AMD and LRCX; disclosed, not hidden.) In every pair the recorded decision-time state is near-identical and the outcomes diverge entirely on the subsequent path: the counterexamples died within 1–4 bars without reaching TP1; the winners survived to TP1 and then compounded for 11–110 bars. Nothing in the recorded fields, examined honestly, tells them apart at entry — subject to the missing-features bound in §7 (absence of a recorded separator is not proof none exists).

## 5. (C) Intrabar audit — TP1 vs stop ordering (Mike's question)

**Simulator semantics (from `run_study13.py::gen_candidates_censored`, source-provable):**

1. Entry fills at the **next bar's Open** after the signal bar; a candidate whose entry Open is at/below its initial stop is rejected (gap rule).
2. On each bar while in trade: the TP1 flag is set if the bar's **High ≥ TP1** — checked **before** that bar's exit evaluation. Once set, the runner stop trails at max(previous runner, Close − 2.5·ATR) using that bar's Close.
3. Exits evaluate on the bar's **Close**: Close < runner stop → "stop" exit; Close < EMA55 (or bear-trend condition) → "ema55-break". The fill is the **next bar's Open**. The exit value for TP1 trades is a synthetic 50/50 blend of the TP1 leg and the exit leg.
4. **There is no intrabar stop order in the model.** The initial stop and the trailing runner bind only through bar closes. Intrabar lows through the stop level do not, by construction, exit a trade.

**Census on the recorded trades (187 taken closed; bars verified 191/191 on entry opens):**

| Question | Count |
|---|---|
| Same-4H-bar dual touch (TP1 first touched on a bar whose Low also ≤ initial stop) | **0** |
| Dual touch resolvable at 1h grain / still undetermined at 1h grain | 0 / **0** |
| Simulator credited TP1 and exited on the same bar | 0 |
| TP1-flag inconsistencies vs reconstructed bars | 0 |
| **Trades with an intrabar Low through the initial stop before TP1 was first touched (or during the hold if TP1 never came)** | **87 of 187 (46.5%)** |

**Answer to the question as asked:** in the recorded DEV trades, price never touched TP1 and the initial stop inside the same bar — the same-bar ordering ambiguity Mike asked about **did not occur** (0 dual-touch bars at 4H grain, hence 0 UNDETERMINED at 1h grain). Simulated fill assumptions are therefore not load-bearing for TP1-vs-stop ordering in this dataset.

**The intrabar assumption that IS load-bearing is the close-based stop.** 87 trades printed through their initial stop intrabar and were held by the close-based rule. Their aggregate outcome under the simulator: **−83.8852R net, 10 positive**. The 100 trades that never breached intrabar: **+116.3725R net, 80 positive**. None of the top-5 winners is in the breach set. Of the breach set, 10 trades recovered to positive closes, including 3 that finished ≥ +2R (RKLB, ARM, F; +10.0902R combined under simulator accounting).

Bounded interpretation (NOT a portfolio counterfactual): crude single-trade arithmetic — a resting hard stop at the initial level exits all 87 near −1R each (≈ −87R before costs), versus −83.8852R realized under the close-based rule, but forfeits the 10 recoveries. The two conventions differ by an amount small relative to either total, the arithmetic ignores displacement, re-entry, heat and sequencing, and its sign is not robust. **Whether the close-based stop helped or hurt is UNRESOLVED on this evidence** — what is resolved is that the assumption is material (46.5% of trades touched it) and invisible in the ledger until the bars are examined. Separated per the governing instruction: everything in this paragraph is simulator-assumption analysis, not observed market-path proof; the observed facts are the counts and sums above.

## 6. (D) Selection / skip analysis (with the accepted caveats)

Closed candidates 586. Hindsight-defined "exceptional" candidates (standalone simulated gross ≥ +2.0R): **80** — taken 24, skipped_rank 43, skipped_risk 8, skipped_gate 5.

This is reported **under the counter-read corrections, which are accepted**: the 24/80 figure is NOT a test of preferential identification (the class is defined by hindsight standalone outcomes; both denominators condition on generated candidates; a skipped trade cannot be substituted into the portfolio without displacement and risk-budget effects; skipped outcomes are standalone simulations, not portfolio counterfactuals). The near-full-book observation from the opening position (55 of 56 skipped-exceptional at a DERIVED 4–5 open positions) stands as capacity **context** only — rank, sector-cap and heat are distinct mechanisms and the recorded telemetry cannot apportion cause among them. **Full-universe trend capture is UNIDENTIFIABLE from the recorded data**: candidates exist only for names that generated signals, and no telemetry records trends that never signaled.

## 7. (E) Data-availability matrix (final)

| Field / quantity | Status |
|---|---|
| Symbol, sector, signal/entry/exit times, entry/stop/TP1 prices, exit_synth, hold_bars | MEASURED (recorded, pinned ledger) |
| RS at signal (20-bar return minus SPY) | MEASURED — the ONLY recorded decision-time feature |
| tp1_hit flag, exit-reason label, gross/net R (0/4/25 bps) | MEASURED (simulator outputs, recorded) |
| Disposition (taken / skipped_rank / skipped_risk / skipped_gate) | MEASURED (recorded) |
| Entry = next-bar Open; gap rejection; TP1 on High before close-exit check; exits on Close, fill next Open; 50/50 TP1 blend; no intrabar stop; no slippage beyond bps views | SIMULATOR-ASSUMED (source-provable) |
| Intrabar path at 1h resolution | PRESENT in pinned captures (used in §5); sub-1h path ABSENT |
| Signal grade; market-gate state; trendScore; SessionVWAP; rel-vol | ABSENT from the ledger |
| Rank margin / slot-free flag at skip time | ABSENT (open-count DERIVED from entry/exit times) |
| Fill/slippage records; share counts / heat per trade | ABSENT |
| Trends that never generated a candidate | ABSENT by construction (census INCOMPLETE for them) |

## 8. Hypotheses (each with counterexamples and an uncertainty rating; none is a conclusion, none licenses a rule change)

- **H1 — The payoff hinge is reaching TP1, not entry selection.** In-sample this is a perfect descriptive separator (§2). As a forward claim it is a HYPOTHESIS with HIGH uncertainty: TP1 reach is path-selected and may simply proxy a favorable regime (2026 carries +29.1105R of the +32.4873R total). Counterexample pressure: 3 TP1 trades still netted negative-to-small on the ema55 path (+1.7962R over 3), and 5 of 92 TP1-stop trades were negative despite the blend.
- **H2 — SEMIS regime cluster.** 4 of 5 winners are SEMIS. HYPOTHESIS, LOW confidence: 37 of the other 182 taken trades were also SEMIS, including RS-matched losers (§4). Distinguishing observation (per counter-read): future preregistered descriptive sector-stratified payoff/skew under the unchanged strategy — no subgroup promotion, no thresholds.
- **H3 — "Exit-stack edge."** CORRECTED per counter-read: hypothesis only. Stop-path profitability may be a consequence of rare favorable price paths rather than a property of the exit rules; no counterfactual exit comparison exists in the admitted evidence.
- **H4 — Close-based stop materiality.** The assumption is demonstrably material (87/187 trades) and its aggregate sign is UNRESOLVED (§5). Any future treatment must be preregistered and tested out-of-sample; DEV cannot price it.
- **H5 — Capacity/displacement.** Context only (§6). Trend capture: **UNIDENTIFIABLE** on current telemetry.
- **H6 — Liquidity-sweep footprint on ema55-break exits.** Definitions PROPOSED in the scope ACK (bridge 53c599a): for each of the 26 taken ema55-break exits — DEPTH = max % excursion of Low below the exit bar's EMA55 line over the next 3 bars; RECLAIM = bars until first Close back above EMA55; NEW HIGH = any High in the remaining window above the max High of the 10 bars before the exit-decision bar; classes SWEEP-SHAPED (reclaim ≤ 2, new high, depth ≤ 1.0%) / GENUINE-BREAK (no reclaim in 5, or depth > 2.0%) / INTERMEDIATE. **Status: NOT RUN — awaiting ChatGPT concurrence on the desk.** If concurrence lands, the classification runs under these exact definitions as a supplement; if not, this section is the frozen proposal. Footprint labels only; OHLCV cannot prove intent.

## 9. The exchange, folded in (attributed)

**Agreements:** (i) The §B principle (comment 6391746367): payoff concentration is neither PASS nor FAIL for a trend system; frozen numeric gates unchanged. (ii) All five counter-read corrections (ChatGPT, 1792891329.772059) — descriptive-not-causal exit attribution; capture rate is not a test; near-full-book is context not cause; SEMIS is a regime hypothesis; "exit-stack edge" demoted to hypothesis — are ACCEPTED and applied throughout this memo (Muse). (iii) Mike's intrabar question is answerable from pinned artifacts, and the answer is §5: the ambiguity he named never occurred in the recorded trades; the material intrabar assumption is a different one (close-based stops).

**Unresolved:** (a) H6 concurrence — procedural, pending on the desk. (b) The substantive question the whole anatomy serves — genuine trend-capture edge vs five lucky trades — remains OPEN by design: both explanations fit DEV, and only the preregistered out-of-sample / prospective procedure can separate them (all parties agreed; FAIL verdict preserved, holdout sealed).

**What would change Muse's read (restated from the opening position):** out-of-sample/prospective payoff shape — positive skew with positive after-cost expectancy across a non-bull regime — and/or a capture rate materially above the base take rate on preregistered telemetry that records rank margins and slot state at skip time.

## 10. Disposition

-23 is CLOSED as a diagnostic. No rule changes are proposed or implied. The DEV run remains labeled EQUITIES-ONLY DEV EXPLORATORY / NOT A VALIDATED EDGE.

— Muse
