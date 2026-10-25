# QF-EQUITY43-DEV-FAILURE-FORENSICS-20261024-24 — Failure forensics on the 66 oversized losses

DIAGNOSTIC ONLY. Mike's direction (chat 2026-10-24 22:19 ET): investigate every way the 66 failed and why, and what maybe could have prevented it. Companion to the CLOSED -23 anatomy (memo 0581bf8, supplement 1a05fa7). All figures recomputed by `forensics66.py` from the pinned -13 ledger (`trade_ledger.json` sha256 267e794c…) and the -23 ordering labels; per-trade register in `register66.json`, full machine output in `forensics_out.json`.

**THE GUARDRAIL (restated, and obeyed throughout):** WHY they failed = diagnosis, run fully below. WHAT WOULD HAVE PREVENTED IT = HYPOTHESES ONLY — written down, frozen, explicitly UNTESTED, never adopted or recommended from this dataset (standing adverse-evidence rule: never tune the losing period away). Every candidate prevention trait carries a collateral count — how many winning trades (all winners, and the top-5 separately) share the trait in the same data. A filter that would have blocked the winners is reported as such, not as a fix.

## §0 The set, reconciled

Closed taken trades with gross R < −1.0 (the -23 supplement's basis): **66 trades, combined −92.0847R gross — ties to the supplement exactly, zero residual.** 64 stop-route + 2 ema55-break; 0 reached TP1. Comparison sets: 187 taken closed; 90 gross winners (+148.3489R gross); top-5 = SNOW/INTC/AMD/QCOM/LRCX (+30.7093R gross; -14's +30.6600R figure is the net basis). Definitional disclosure: one boundary trade (AMZN 2026-07-20, gross −0.9948 / net@4bps −1.0082) sits between the gross and net bases and is NOT in the 66 (on the net basis the set would be 67). Breach-label vs intrabar-artifact membership cross-check: 0 mismatches.

## §1 Why they failed — the mechanism (from -23, confirmed per-trade here)

The 66 are the close-confirmed exit stack working exactly as coded, on trades that never reached TP1: 64 of 66 (97%) are CONFIRMED_STOP_FIRST — the stop threshold was touched intrabar and the close-trigger/next-open fill printed below the line (supplement: the below-stop distances sum to 25.9849R, arithmetically identical to the group's excess beyond −1R). The remaining 2 are ema55-break exits (trend-condition trigger; the stop plays no part). No other mechanism contributes. That is the whole causal chain the recorded data supports; everything below is shape, not additional cause.

## §2 Exit-date clustering — the "bad mornings" question, answered

Mike's hypothesis was that oversized losses cluster on shared gap mornings. **In its strong form, the recorded data does not support it:**

- 66 exits fall on **57 distinct exit dates** across 20 months; the maximum on any single date is **2**.
- 9 dates carry a pair of the 66 (18 trades, −24.2909R combined); the worst single date is 2026-07-02 (LRCX + SMH, −3.1707R). No date holds 3 or more; no morning accounts for a book-wide event.
- Pair-dates are not one-sided days in the full ledger either: on 3 of the 9 dates, other taken trades also exited, partly offsetting (e.g. 2025-10-17: 3 taken exits, all-trades gross −0.1865 vs the pair's −2.2220).

The overshoot is per-trade and spread out — 66 separate executions of the same mechanism, not a handful of catastrophic mornings. (Per-date market state cannot be layered on top: no benchmark series is a recorded field in these artifacts — NOT_RECOVERABLE, §7.)

## §3 Timing — they died fast; that is shape, not a separable cause

- Hold bars: the 66 median **4.5 bars**; 15 exited within ≤2 bars, 33 (50%) within ≤4 bars, 57 within ≤10. Winners' median hold is 22 bars.
- This is near-mechanical under this exit stack (a stop-route exit requires an early adverse close; a TP1-then-runner winner requires time), so it is reported as the failure *shape*, NOT as evidence that "cutting losers faster" would help — that counterfactual is the exit-convention question already covered by -23, and no hard-stop P&L is computed here.
- Weekdays: entries spread Mon 17 / Tue 16 / Thu 14 / Wed 12 / Fri 7 — Friday entries are UNDER-represented among the 66 (winners: 17 Friday entries). Exits: Friday-heavy (22/66) vs winners 24/90 — proportionally similar (33% vs 27%); Monday exits rare in both (6 vs 16). No weekday pattern separates.
- Entry regime: 37 of the 66 entered in 2025, 29 in 2026; winners split 44/46. Failures are spread across every entry month (1–5 per month, no month dominates).

## §4 Entry-time features — what the recorded fields say

**rs (the only persisted signal-time indicator): no separation.** Medians — the 66: 0.0489; winners: 0.0677; all taken: 0.0573. Quartile bands (cuts from the 187): the 66 fall 19 / 29 / 18 across low/mid/high bands vs base counts 46 / 94 / 47 — within noise of base rate in every band. 32 of the 66 fired with rs ABOVE the 187 median — the same half of the rs range that contains **all five** top winners. Any rs threshold that removes a meaningful share of the 66 removes winners at the same rate.

**Slot state at entry (DERIVED from recorded entry/exit times): no separation.** Entered as the 5th position (4 already open): 23/66 (34.8%) vs 31/90 winners (34.4%) — identical. Entered with ≥3 already open: 39/66 (59%) vs 59/90 winners (66%). Collateral is decisive: SNOW (a top-5 winner) entered as the 5th position; 4 of the top-5 entered with ≥3 positions open. A book-full entry block would have blocked 31 winners (+52.3230R gross) to avoid 23 of the 66 (−32.7434R) — and it is a hypothesis about admission, not a finding (see §6, H-F4: collateral-rejected in-sample).

**Planned geometry: no separation.** Narrow planned stop (risk fraction below the 187 median): 34/66 vs 39/90 winners, 1 top-5. Far TP1 (planned TP1 R-multiple above median): 36/66 vs 39/90 winners, 4 of the top-5. Both traits sit at base rate in both sets.

## §5 Concentration — sectors and repeat symbols

Per-sector (taken / in the 66 / winners / gross of the 66 / gross of winners):

| sector | taken | in 66 | winners | gross 66 | gross win |
|---|---|---|---|---|---|
| FINTECH | 21 | **13 (62% of sector)** | 6 | −17.2632 | +6.4393 |
| CONSUMER | 39 | 14 (36%) | 15 | −18.9992 | +20.4242 |
| SEMIS | 41 | 13 (32%) | 23 | −19.3626 | +49.4953 |
| ETF | 22 | 8 (36%) | 10 | −11.9257 | +11.7998 |
| SPACE | 17 | 7 (41%) | 7 | −8.8294 | +10.6285 |
| AI_SOFTWARE | 26 | 7 (27%) | 16 | −10.4808 | +31.9726 |
| HEALTHCARE | 14 | 3 (21%) | 8 | −4.0158 | +11.5577 |
| CRYPTO | 7 | 1 (14%) | 5 | −1.2080 | +6.0315 |

- **FINTECH is the one real tilt:** 13 of its 21 trades are in the 66, only 6 won, and it is the only sector net-negative overall (−11.9677R gross across all 21 trades). Registered as a hypothesis with collateral in §6 (H-F2) — with 17 features interrogated on 66 events (§8), a tilt of this size can arise by chance; it is not a cause.
- SEMIS supplied the most failure R (−19.3626) but at base rate (32% of its trades) and simultaneously 23 winners and 4 of the top-5. A semis block is collateral-nonsense in this data.
- **Repeat symbols:** 53/66 (80%) sit in 19 symbols appearing ≥2 times in the 66; worst: LRCX 5 (−8.2427R), MELI 5 (−7.2874R), ASTS 5 (−6.4901R), F 4 (−6.3261R), XLF 3 (−5.4292R). Collateral kills the obvious reading: **LRCX is also a top-5 winner** (+4.8903R net on a separate trade) and AMD (2 appearances in the 66) is the #3 winner overall. The same names produce both tails — symbol blocking would have blocked the winners (H-F6).

## §6 Prevention-hypothesis register — FROZEN, UNTESTED, none adopted or recommended

Each entry: the candidate prevention, its in-sample coverage of the 66, and its in-sample collateral. In-sample collateral is shown so a future out-of-sample test can be designed honestly; nothing here is evidence any of these would work forward.

- **H-F1 — ADX band at fire (Mike, 2026-10-24 22:21 ET).** Hypothesis: signals fired in weak-trend/chop ADX bands (or exhausted high-ADX bands) fail oversized at higher rate. **NOT EVALUABLE on this dataset: ADX at signal was never persisted in any pinned -13/-14/-23 artifact** (§7). Registered as a named hypothesis for out-of-sample adjudication only. Telemetry requirement (future shadow cohort): log the full indicator state — including ADX — at every candidate fire, taken or not.
- **H-F2 — FINTECH failure tilt.** Candidate: sector-level admission or sizing treatment for FINTECH. Coverage in-sample: 13/66 (−17.2632R). Collateral: 6 FINTECH winners (+6.4393R gross) blocked; sector total is −11.9677R so even a perfect in-sample block nets positive in-sample — which is exactly why it must not be adopted from this dataset: it is the single most overfit-shaped observation in this package (one sector, 21 trades, chosen because it is extreme). UNTESTED.
- **H-F3 — Shared-morning gap clustering.** Interrogated descriptively in §2 and **not supported in strong form** (max 2 of the 66 per exit date, 57 distinct dates). Registered as an answered-negative within this dataset; a book-level gap-exposure cap has no in-sample basis here. (Heat measuring planned-not-realized exposure remains a -23 accounting observation, separate from this hypothesis.)
- **H-F4 — Book-full / slot-state admission block.** Coverage: 23/66 at open_before=4 (−32.7434R). Collateral: 31 winners (+52.3230R), including top-5 SNOW; at ≥3 open, 4 of the top-5. **Collateral-rejected in-sample** — recorded so it is not re-proposed as a fix; any future test must be out-of-sample and preregistered.
- **H-F5 — rs-band filter.** Coverage: at most 34/66 (below-median half). Collateral: 38 winners below median (+50.9967R); all top-5 above median alongside 32 of the 66. No band separates (§4). **Collateral-rejected in-sample** as a filter; rs remains a recorded feature for the frozen validation design, unchanged.
- **H-F6 — Repeat-offender symbol block.** Coverage: 53/66 (−74.9356R). Collateral: 44 winners (+67.3122R) trade the same 19 symbols, including top-5 LRCX and AMD. **Collateral-rejected in-sample.**
- **H-F7 — Narrow-stop / far-TP1 geometry screen.** Both traits at base rate in failures and winners alike (§4); top-5 collateral on both. **No in-sample basis**; registered as answered-negative.

## §7 NOT_RECOVERABLE — stated, never reconstructed

Checked exhaustively across every pinned -13/-14/-23 artifact (ledger, results, attribution state, ordering labels, intrabar census): the ONLY per-candidate signal-time indicator persisted is `rs`. NOT_RECOVERABLE: **ADX at signal; trend readings/trendScore at signal; VWAP relation at signal; relative volume at signal; EMA geometry at signal** (the engine computes indicators from bars, but per-candidate state was never persisted, and reconstructing it from vendor bars is forbidden by the framing and by the derived-only rights model); market-gate state at entry; per-date SPY/market-state series; earnings dates (not recorded; external fetch forbidden); closest approach to TP1 / MAE / duration under the stop threshold (bar paths not persisted); the trigger-close vs next-open split of the 25.9849R overshoot (trigger-bar close not a persisted field, per -23 supplement).

Telemetry requirements carried forward for the future shadow cohort (recording requirements, not strategy changes): (1) full indicator state at every candidate fire, taken or not — including ADX; (2) trigger-bar close persisted for every exit; (3) per-bar path summaries sufficient for MAE and TP1-approach (or journal-only replay payloads, as in the -17 design).

## §8 Multiple-comparisons discipline

17 features were interrogated against the 66: exit-date clustering, entry weekday, exit weekday, hold duration, entry year, entry month, sector, symbol repetition, breach membership, slot state at entry (DERIVED), rs median split, rs quartile bands, planned stop width, TP1 R-multiple, Friday entry, Monday exit, exit route. With 66 events and 17 looks, apparent tilts are expected by chance; the largest deviation found (FINTECH, §5) is therefore presented strictly as a hypothesis with its base rate and collateral attached. **No feature in this package is presented as "the cause" of the 66.** The only causal statement the data supports is the mechanism in §1, which was established by -23 from source, not by correlation here.

## §9 Bounds

Offline, recorded artifacts only. No new strategy runs or backtests; no vendor calls; no external data; no rule changes and no recommendations; holdout SEALED; C1 FAIL frozen; production PAUSED and the -22 pilot untouched. Diagnosis + frozen hypothesis register only.

— Muse
