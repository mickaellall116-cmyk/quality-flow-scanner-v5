# -23 Closeout Supplement — evidence-linked (per ChatGPT counter-read, Slack TS 1792892214.575159)

Supplement to the -23 DEEP memo (`MEMO.md`, package commit `0581bf8`). Scope: exactly the six points of the counter-read. No strategy changes, no new performance runs, no backtests, no vendor calls, no counterfactual simulation, no hypothetical hard-stop P&L. Holdout SEALED; C1 FAIL frozen; production PAUSED untouched; pilot untouched.

**Evidence base (pinned, unchanged):** -13 `trade_ledger.json` sha256 `267e794c284a409d7d9b6d8e1056c452976b59746062e9e18c5664b74c003b`; -13 `results.json` sha256 `42b05ce3…`; simulator source `-13 run_study13.py` (`gen_candidates_censored`) and `pine_backtest.py` / successor `pine_stack.py`; the memo §5 intrabar census artifact (`deep2.py` output: per-trade breach membership, dual-touch and same-bar lists). All figures below are recomputed from the ledger by `supplement.py` (this package) and tie to -13/-14. **All counts are over the 187 taken CLOSED trades only**; the 4 censored positions are excluded from every figure (§5).

---

## 1. Stop semantics — the initial stop is a close-triggered signal threshold (VERIFIED from source)

**Clarification, stated plainly:** in this model the initial stop is **a close-triggered signal threshold, not a resting hard stop order and not a loss cap.** No order rests at the stop price. A trade exits only when a 4H bar **closes** below the threshold; the fill is the **next bar's Open**. Losses beyond −1R are a designed-in consequence of that construction, not an execution error (§3: realized 66 times in 187 closed trades, worst −3.1113R gross).

Source anchors (`run_study13.py::gen_candidates_censored`):
- Initial stop set once at signal time: `stop0 = signal Close − atr × SL_ATR` (SL_ATR = 1.5, `pine_backtest.py:66`), line 516. Entry fills at the next bar's Open, line 515; a candidate whose entry Open ≤ stop is rejected at generation (gap rule).
- Each in-trade bar reads `lo, hi, close` (line 532). **The bar's Low is never referenced by any exit condition** in the function — intrabar prints through the stop cannot exit a trade, by construction.
- The only stop exit test is `close < pos["runner"]` (line 539), where `runner` starts at the initial stop and trails only after TP1 (§4). The trend exit is `close < e55` or the bear condition (line 541). Fill: next bar's Open (line 545).

**(a) R denominator / position sizing — VERIFIED, both use the planned stop width.**
- R is defined against the initial stop: `risk_frac = (entry − stop) / entry` (line 550; identical recomputation in `pine_backtest._outcome`, `pine_backtest.py:215`). `pos["stop"]` never mutates during the trade; the trailing `runner` is a separate variable, so realized R is always measured against the **planned** width.
- Sizing spends that width: `risk_dollars = RISK_PCT × marked equity` (RISK_PCT = 0.01, `pine_backtest.py:56`), `size = risk_dollars / risk_frac` (`pine_backtest.py:260–263`; successor stack identical: `pine_stack.py` successor copy, lines 142–145). Planned dollar loss at the threshold = 1% of equity at admission, by construction.

**(b) Portfolio heat — VERIFIED: PLANNED, not realized.**
- The admission gate sums the **entry-time** `risk_dollars` of open positions: `open_risk = Σ risk_dollars / equity` (`pine_backtest.py:253`), refusing admission when `open_risk + risk_pct > MAX_PORTFOLIO_RISK` (0.05, `pine_backtest.py:58`; concurrency cap 5, line 57).
- `risk_dollars` is fixed at admission from the planned stop width and is **never re-measured** — neither engine updates it when a fill gaps through the stop or when the runner trails. Realized gap exposure therefore never appears in the heat figure: heat measures planned exposure only, and a portfolio can realize more loss than its heat ever showed (in this ledger, 66 trades realized beyond their planned −1R).

## 2. The 87 pre-TP1 low breaches — what the artifacts do and do not contain

Membership and outcomes are recorded (ledger ⨝ memo §5 breach set, keyed by symbol + entry time). VERIFIED counts:

| Breach set (n=87) | n | Net R @4bps | Gross positive | Net positive |
|---|---|---|---|---|
| Later reached TP1 | 10 | **+18.0417** | 10 | 10 |
| Never reached TP1 | 77 | **−101.9269** | 0 | 0 |
| **Total** | **87** | **−83.8852** | **10** | **10** |

- **Recovery structure:** every breach trade that finished positive is in the reached-TP1 subset — the same 10 recoveries named in the memo (3 at ≥ +2R net: RKLB +4.4126, ARM +3.1416, F +2.5360; the remaining 7 between +0.4799 and +1.8460). No breach trade recovered to positive without reaching TP1. Exit routes within the breach set: stop 78, ema55-break 9 (TP1 subset: stop 9, ema55-break 1).
- Contrast set (never breached, n=100): TP1 reached 85, net +116.3725R, 80 positive.

**NOT_RECOVERABLE from the artifacts** (the saved intrabar artifact persists breach *membership* only — one (symbol, entry-time) pair per trade — and the ledger records no per-bar path):
- Maximum adverse excursion per trade — **NOT_RECOVERABLE** (requires the per-bar Low path; not persisted).
- Number of breaches per trade — **NOT_RECOVERABLE** (only ≥1 membership persisted).
- Duration under the threshold (bars with Low/Close below the stop) — **NOT_RECOVERABLE**.
- Per-breach close-vs-stop sequence and per-breach gap exposure — **NOT_RECOVERABLE**.

These are marked, not reconstructed: per the supplement's governing instruction they are not re-derived from vendor bars, and **no hypothetical hard-stop P&L is computed** — the memo §5's bounded single-trade arithmetic is not repeated or extended here.

## 3. The 66 losses below −1R — mechanism reconciliation (VERIFIED, per-trade)

Population: 97 gross losers among the 187; 66 with gross R < −1.0 (52 below −1.1; worst −3.1113); the other 31 sit in [−1.0, 0). Decomposition by recorded exit route and TP1 state — exhaustive, no remainder:

| Mechanism | n | Gross R sum | Excess beyond −1R |
|---|---|---|---|
| Stop route, TP1 never reached | 64 | −89.9850 | 25.9850 |
| ema55-break route, TP1 never reached | 2 | −2.0997 | 0.0997 |
| Any route with TP1 reached | **0** | — | — |
| **Total** | **66** | **−92.0847** | **26.0847** |

- **The 64 (stop route):** for a no-TP1 stop exit the recorded `exit_synth` *is* the fill (next-bar Open; no blend). In **all 64** the fill printed **below the initial stop** (verified per trade from the ledger). The fill's distance below the stop, in R, sums to **25.9849R** (median 0.3093R, max 2.1113R) — arithmetically identical to the group's excess beyond −1R (25.9850R, rounding), which cross-validates the decomposition. What that overshoot consists of per trade — how much was the trigger bar's Close already below the stop (close-trigger overshoot) versus the gap from that Close to the next bar's Open — is **NOT_RECOVERABLE**: the trigger bar's Close is not a persisted field in the ledger or the intrabar artifact. **These 64 are therefore NOT labeled "gap losses."** The evidenced statement is narrower: close-triggered exit, fill below the stop in every case, combined overshoot 25.9849R, split unknown.
- **The 2 (ema55-break route):** their exit trigger was the trend condition (Close < EMA55), in which the stop plays no part at all. Their losses (−1.0160R, −1.0837R) exceed −1R because the close-based trend exit fired only after price had already travelled past the planned stop distance, plus the next-open fill. A distinct mechanism from the stop route; not gap losses either.
- **No other route contributes:** zero TP1-reached trades appear among the 66 (a TP1 trade's blended exit held every one of the 5 negative TP1 trades above −1R gross), and no ema55-bear exits exist in the 187 (recorded reasons are only `stop` ×161 and `ema55-break` ×26).

## 4. TP1 / close ordering — source-confirmed

Source: `run_study13.py` lines 532–555, one bar iteration, in order: (i) TP1 flag test `hi >= tp1` (line 533); (ii) runner trail update if TP1 set (line 536); (iii) exit tests on Close (lines 539/541); (iv) fill at next bar's Open (line 545).

- **TP1 is credited BEFORE a close-triggered exit in the same bar.** If a bar's High touches TP1 and its Close triggers an exit, the trade is recorded as TP1-reached and its exit value includes the TP1 leg. **VERIFIED from source.**
- **The TP1 fill uses the limit price.** The credited TP1 return is `r1 = (tp1 − entry)/entry/risk_frac` (lines 550–554) — a function of the TP1 price only, never of the touch bar's High, Open, or any gap through the level. A gap over TP1 earns exactly the limit, no more. **VERIFIED from source.**
- **Next-open timing and partial realization.** The runner leg always fills at the next bar's Open after the triggering Close; that timing does not re-price the TP1 leg (fixed at the limit in the 50/50 blend, `exit_synth`, line 555). Timing matters at exactly one boundary: TP1 credit depends on the touch occurring on or before the exit-decision bar — a touch one bar later would earn no TP1 leg at all. Two source-construction facts bound the recorded evidence: the simulator evaluates the **entry bar itself** as an in-trade bar, so TP1 can be credited from the entry bar's High even though the entry filled at that bar's Open (SIMULATOR-ASSUMED semantics); and TP1 first touched **on the exit-decision bar** is credited the same way.
- **Uncertain-path count: 0 ordering-uncertain paths among the 187** — same-bar dual touches 0 (§6) and recorded TP1-first-touch-on-decision-bar with a stop exit = 0 (memo §5 `sim_samebar`). Two counts are **NOT_RECOVERABLE** from the saved artifacts (touch-bar index was not persisted): TP1 first touched on the exit-decision bar for the 3 ema55-route TP1 trades, and TP1 first touched on the entry bar. Neither affects the ordering verdict: both are resolved by the same source rule (TP1 test precedes exit tests), so they are semantics, not ambiguity.

## 5. Arithmetic validation — all figures tie (VERIFIED; no discrepancies)

| Check | Result |
|---|---|
| Breach split | **−83.8852R** (87-trade subgroup total) + **+116.3725R** (100-trade subgroup total) = **+32.4873R** = taken-closed net @4bps — exact (gross: −82.7710 + 117.6164 = +34.8454 ✓). Notation corrected 2026-10-24 in the provenance closure: the subgroup figures are totals, not per-trade values; the earlier "87 × / 100 ×" multiplication notation was misleading. |
| Never-TP1 vs losers | Never reached TP1: **92**, every one negative on both gross and net. Losers: **97** on gross and **97** on net. 97 = 92 never-TP1 + **5** TP1-reached negatives (identical 5 on both bases). Positives: 90 net, all TP1-reached; TP1 reached total 95 = 90 + 5 ✓ |
| Censored | Exactly **4** — CRM, MRNA, PFE, SHOP — all taken, all terminal-open; excluded from the 187 and from every figure in the memo and this supplement |
| Loss tail | 97 gross losers; 66 below −1.0R; 52 below −1.1R; worst −3.1113R — all as stated in the memo §3 |

No figure failed to tie; nothing was smoothed. All 187 are reported strictly as closed-only throughout.

## 6. Ordering classification — concurred labels applied (thresholds, not orders)

**ChatGPT's two notes, carried verbatim in substance:** (1) these labels refer to **trigger/price thresholds, NOT an intrabar stop order — no intrabar stop order exists in this model** (the stop binds only through bar closes, §1); "first" describes which *price threshold was touched first on the recorded 4H path*, nothing about order execution. (2) The **0 dual touches are DISTINCT from the 87 low breaches and are not merged with them**: a dual touch means both thresholds touched inside one bar; a low breach means the stop threshold was touched on a bar strictly before TP1's first touch (or TP1 never came). The sets are disjoint by construction.

Classification rule (frozen by the memo's §5 census + this concurrence; nothing added): a trade is STOP_FIRST if the recorded path printed Low ≤ initial stop on a bar strictly before the first TP1-touch bar (or TP1 was never touched); TP1_FIRST if TP1 was touched with no such earlier breach; SIMULATOR_ASSUMED if neither threshold was ever touched intrabar before the exit — the exit was then produced entirely by the close-based rule and no threshold ordering is observable; SAME_BAR_AMBIGUOUS if both thresholds were touched inside one 4H bar and the 1h path cannot order them; INSUFFICIENT_EVIDENCE if the trade could not be walked against verified bars.

| Label | n | Net R @4bps | Basis |
|---|---|---|---|
| CONFIRMED_STOP_FIRST | **87** | −83.8852 | memo §5 breach set |
| CONFIRMED_TP1_FIRST | **85** | +127.9676 | TP1 touched, no prior breach (100 − 15) |
| SIMULATOR_ASSUMED | **15** | −11.5951 | neither threshold touched; close-rule exit only (all 15 negative; the non-breach half of the 92 never-TP1) |
| SAME_BAR_AMBIGUOUS | **0** | — | dual-touch bars: 0 at 4H, 0 unresolved at 1h |
| INSUFFICIENT_EVIDENCE | **0** | — | bars verified 191/191 on entry opens; 187/187 walked |
| **Total** | **187** | **+32.4873** | ties §5 ✓ |

Per-trade labels: `ordering_labels.json` (this package). Post-TP1, the binding threshold becomes the trailing runner; these labels order TP1 against the **initial** stop only, which is the question the concurrence covers. No classification beyond this is made — in particular, the memo §8/H6 sweep-footprint proposal for the 26 ema55-break exits remains a separate, unrun classification and is not folded into these labels.

---

## Disposition

All six counter-read points are answered from pinned artifacts and source. Items that the artifacts cannot support are marked NOT_RECOVERABLE (§2: MAE, breaches-per-trade, duration under threshold, per-breach close/gap split; §3: trigger-close vs gap split of the 25.9849R overshoot; §4: two touch-bar counts) rather than reconstructed. -23 remains CLOSED as a diagnostic; the FAIL verdict, the sealed holdout, and all frozen gates are untouched. No rule changes are proposed or implied.

— Muse

## Correction note (2026-10-24, provenance closure)

Per ChatGPT's independent review (Issue #1 comment 6392280376): the §5 breach-split row previously wrote the subgroup totals with multiplication notation ("87 × −83.8852R + 100 × +116.3725R"), implying per-trade values. The figures are subgroup TOTALS and now read **−83.8852 + 116.3725 = 32.4873R**. No figure changed. The same closure commits the derived-only provenance witness for the path census (input_inventory.json, census_output.json, closure_verify.py, PROVENANCE_CLOSURE.md in this package).
