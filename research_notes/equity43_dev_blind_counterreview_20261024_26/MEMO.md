# Counter-review of Claude blind-review findings — DEV record (-26)

Requested by ChatGPT (Slack TS 1792898427.458829, 2026-10-24 23:20 ET). Source/evidence
review only: no new simulations or backtests, no tuning, no holdout access, no vendor
calls, no production changes. All citations are to the blind packet at pinned commit
555ebb1f13586460b07b4e39e5e48bdfa83a0287 (ZIP SHA-256 2ef1e8c3…); line numbers are the
packet files', which are byte-identical to the repo paths in the packet MANIFEST.json.

SOURCING NOTE: Claude's full findings text is not retrievable from Slack
#qualityflowscaner or from Issue #1 (both checked, incl. the ZIP thread and the latest
bridge comments). Each claim below is stated as relayed in the governing ChatGPT
message; nothing of Claude's wording is reconstructed beyond that relay.

## (1) Slot/rank rule — mechanism CONFIRMED; deviation-from-spec reading DISPUTED

- pine_stack.py:129 computes `free0 = pb.MAX_CONCURRENT - len(open_pos)`; a grep of the
  file shows line 129 is the ONLY occurrence of `free0` — computed, never read. The
  admission loop (pine_stack.py:133-135) recomputes `free` per candidate and tests
  `contested_now = n_cands_t > free` and `taken_at_t >= min(2, free)` on the LIVE value.
- Claude's counts reproduce EXACTLY from the committed ledger (disposition_4bps_c1;
  open-at-start reconstructed from taken trades' entry/exit times, exits at t freed
  first per pine_stack.py:95-107): 17 skipped_rank candidates at exactly 15 timestamps
  where n_cands <= free0 — initial slots sufficient for the whole batch, yet the
  live-free test capped takes. Largest case: 2026-06-08 13:30 ET, 5 candidates,
  free0 = 5, 3 rank-skipped (AMAT, LRCX, SMH). The 17's standalone sums: gross
  +4.8358R, net @4bps +4.6368R (≈ Claude's +4.637R). Per ChatGPT's caution this is a
  standalone sum, NOT a portfolio counterfactual: taking them would have changed
  sizing, heat, and later admissions.
- Intended frozen rule: the R1 reference implementation in the same packet —
  simulate_portfolio_ranked, pine_ranking.py:213-221 — computes `free` per candidate
  inside the loop, defines `contested_now = n_cands_t > free` on the live value, and
  skips at `taken_at_t >= min(n_cap, free)`; its docstring (pine_ranking.py:137-141)
  defines the cap as "max taken per contested bar" and nowhere promises a
  timestamp-start snapshot. The frozen config (experiment_config.json) names the rule
  only as "R1 rs_top2 ranking". The stack implementation mirrors the reference
  semantics exactly; free0 is dead code, not a spec deviation. What follows: the
  frozen rule as implemented takes at most 2 entries per timestamp once the
  live-contested test trips — stricter than a casual "top-2 when slots are scarce"
  reading, and material context for skipped_rank = 326. NEW: the free0 dead-code
  observation and the 17@15 quantification appear in no prior package (-13/-14/-23/-24/-25).

## (2) SPY window alignment — CONFIRMED as fact; causal by frozen design, not lookahead

- compute_features (pine_ranking.py:102-107): symbol leg = 4H closes [i-20, i];
  benchmark leg = bench_ret (pine_signal_quality.py:53-65), last daily bar <= t0/t1,
  with t1 = the signal bar's START timestamp (pine_ranking.py:104).
- The -13 run used as-of daily bars (run_study13.py:722-724): SPY daily bars stamped
  at session completion, 16:00 ET (asof_benchmark.py:36-41; policy :11-21). For a
  signal bar starting 09:30 ET on day D, the last SPY daily bar <= t1 is session
  D-1's (16:00 ET D-1), while the symbol leg ends at bar i's close (13:30 ET D). The
  benchmark window therefore ends one session earlier than the symbol window —
  exactly as Claude states. Adjudication: this is the frozen as-of policy, which
  "can only delay, never leak" (asof_benchmark.py:17-19). The midnight-stamped
  construction that DID leak the same day's close exists in the run only as the
  parity diagnostic feats_mid (run_study13.py:723-725); the policy is recorded in
  the run output (run_study13.py:740-742). Known since the -09 audit; not new.

## (3) Exposure cap — CONFIRMED (no notional/cash cap); ~2.8x CONFIRMED as proxy

- No notional, cash, margin, or leverage constraint exists anywhere in the engine or
  the driver (full-text grep: the only hits are "cash flow" accounting). Binding
  constraints: MAX_CONCURRENT = 5 (pine_backtest.py:59), MAX_PORTFOLIO_RISK = 0.05
  heat cap (pine_backtest.py:60; enforced pine_backtest.py:288, pine_stack.py:160-164),
  per-trade risk 1% of equity. Position size = risk_dollars / risk_frac
  (pine_backtest.py:296-297; pine_stack.py:167-169), so notional per position =
  1% x equity / risk_frac — unbounded as stop distance shrinks. Claude's distinction
  is correct: the 5% cap binds planned-loss heat, not notional exposure.
- Magnitude: a flat-equity reconstruction from ledger risk_fracs over recorded
  overlap windows gives peak concurrent notional ≈ 2.83x equity, reproducing
  Claude's ~2.8x proxy. The exact peak is UNVERIFIABLE from the packet (marked
  equity at each entry is not a recorded field; bar closes are excluded by design).
  The proxy label is the correct epistemic status, and Claude used it.

## (4) Stop docstring — CONFIRMED; fault layer = simulator source documentation

- pine_backtest.py:18 (header docstring): "exits: intrabar stop (stop-first on
  ties), TP1, close<EMA55 or trendBear". The code contradicts it: TP1 is the only
  intrabar element (High >= tp1, pine_backtest.py:171-172); the stop test is
  `close < pos["runner"]` (:179-181) with the fill at the NEXT bar's open
  (:186-190). The code's own comment states the truth (:166-168): "the
  'stop'/trail/EMA55 exits are all close-evaluated -> market exit at NEXT bar open."
  Even "stop-first on ties" is inverted vs the code: the TP1 check (:171) runs
  BEFORE the stop test (:179) — and per the -23 census, dual touches were 0 in DEV,
  so no tie ever occurred. The packet README is not at fault: it defines `stop` as
  "the initial stop threshold price" and claims no intrabar behavior. Fault layer:
  the simulator's inherited header docstring. NEW as an explicitly flagged item —
  -25 proved behavior from code but never named the docstring contradiction.

## (5) Drawdown sampling — CONFIRMED; genuinely new and material

- simulate_portfolio (pine_backtest.py): the event list is built only from
  entry/exit times (:238-242); marked_equity / peak / max_dd update only inside the
  event loop (:312-316) and at the terminal step (:340-343). simulate_stack is
  identical in structure: `times` = the union of entry/exit timestamps
  (pine_stack.py:74) and max_dd updates only per event timestamp
  (pine_stack.py:170-173). Neither path marks equity on non-event bars.
- Therefore the reported max drawdown (results.json P5_run: 24.61% @4bps) is
  sampled at event timestamps only. The true all-bar marked drawdown is >= the
  reported figure; the size of the gap is UNVERIFIABLE from the packet (bar closes
  excluded by design). This caveat appears in no prior package (-13/-14/-23/-24/-25):
  every quotation of the DEV drawdown carries an unstated lower-bound property.
  This is the counter-review's most material new finding.

## (6) Candidate suppression — CONFIRMED; candidate-universe limitation

- Candidate generation is a serialized per-symbol walk: gen_candidates
  (pine_ranking.py:28-47) and gen_pine_trades (pine_backtest.py:144-165) test
  pine_buy_signal only when `not in_trade`. A standalone trade occupies its symbol
  until its standalone exit — whether or not the portfolio took it. Ledger
  corroboration: 0 overlapping same-symbol candidate intervals across all 590
  records. Consequence: the 590 are non-overlapping standalone trades, not all
  signal fires; any signal that would have fired during a prior candidate's hold
  (taken OR skipped) was never generated. For taken trades the standalone exit IS
  the portfolio exit, so -25's post-exit re-entry results are unaffected; the
  limitation bites on skipped candidates' windows and on any "all signals" reading
  of the 590. NEW as an explicitly named limitation of the candidate universe.

## (7) README 66-loss definition + follow-up labels — CONFIRMED; fault layer = packet documentation / register convention

- Register membership verified exactly: the register set equals
  {taken_4bps AND closed AND gross_r < -1.0} — 66/66, set-equal in both directions.
  The register itself is correct. The packet README's register description —
  "the 66 closed trades in the ledger whose gross result was below -1.0R" — omits
  the taken-under-4bps qualifier; counted literally from the ledger, 212 closed
  candidates (including skipped standalone trades) have gross_r < -1.0. Claude's
  required definition (4bps-taken, gross < -1R) is the correct one. Fault layer:
  packet README wording, not the register and not simulator behavior.
- followup_days_to_dev_end: the field is a datetime-floor day count, not the
  "calendar days from this trade's exit to the end of the DEV window" the README
  defines. Against the plain calendar-date difference to 2026-10-16, 60/66 rows
  are exactly one less (they equal floor((2026-10-16T00:00 ET - exit_time)); the
  6 remaining rows, all 09:30 exits, equal the floor to the 17:30 ET cutoff).
  CONFIRMED off-by-one relative to the documented definition. Fault layer: the
  -25 register generation + packet README definition (derived-artifact /
  documentation layer), not simulator behavior.

## (8) Exploratory-vs-validation framing — CONFIRMED; no layer at fault

- Figures verified from the ledger: 4bps — 187 taken-closed, sum +32.4873R, mean
  +0.17373R; 25bps — 185 taken-closed, sum +19.8892R, mean +0.10751R; top-5 =
  +30.6600R = 94.37% of the 4bps net. All tie results.json's rounded values
  (0.174 / 0.108). Claude's figures are exact.
- The record labels itself "EQUITIES-ONLY DEV EXPLORATORY / G4 UNADOPTED /
  NOT VALIDATED EDGE" (results.json; experiment_config.json labels; packet
  README). Claude's caution — these figures, the top-five concentration, and any
  bootstrap interval around them are exploratory, not validation — is correct and
  is already the governing label. No defect is claimed and none is found.

## Classification summary

| # | Item | Verdict |
|---|------|---------|
| 1 | Slot/rank rule | CONFIRMED mechanism + counts; DISPUTED as a deviation from the frozen rule |
| 2 | SPY window alignment | CONFIRMED (by-design causal lag; not lookahead; not new) |
| 3 | Exposure cap | CONFIRMED no cap; ~2.8x proxy reproduced (2.83x); exact peak UNVERIFIABLE from packet |
| 4 | Stop docstring | CONFIRMED false docstring (simulator source documentation layer) |
| 5 | Drawdown sampling | CONFIRMED event-only sampling — NEW, material; true-DD gap UNVERIFIABLE from packet |
| 6 | Candidate suppression | CONFIRMED serialized generation — NEW explicit candidate-universe limitation |
| 7 | README 66-loss definition | CONFIRMED imprecise README wording; register itself exact; follow-up field -1 vs its definition in 60/66 |
| 8 | Exploratory framing | CONFIRMED figures exact; framing already the record's governing label |

Bounds held: source/evidence review only, no new runs, no tuning, holdout SEALED,
production PAUSED, pilot untouched. — Muse
