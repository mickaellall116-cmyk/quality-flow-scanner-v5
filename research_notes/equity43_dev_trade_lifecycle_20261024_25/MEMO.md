# -25 — Expanded trade-lifecycle investigation of the 66 oversized losses

**Status:** descriptive forensic research only. Pinned records only; NO new simulations
or backtests; NO tuning; NO holdout access; NO vendor calls; NO external data.
Production PAUSED; the -22 feed pilot is untouched. Strategy frozen; C1 verdict FAIL
(October) unchanged. Every conclusion is labeled **PROVEN** (from pinned artifacts) /
**SUGGESTED** (descriptive pattern, hypothesis only) / **UNKNOWN** (not recoverable).

**Governing texts:** ChatGPT framing A (Slack TS 1792895678.832769, BUY→EXIT causal
forensics, 6 items); ChatGPT framing B (Slack TS 1792895871.932849, complete lifecycle
incl. post-exit BUY/re-entry); counter-read TS 1792895318.584839 (point 1 resolved in
§A5); Part B counter-read + the four scope proposals (Slack 1792896269.649719) as
amended by the scope-amendment note (bridge b05f7f1, Slack TS 1792896398.563589).

**Guardrail (restated from -24, binding here):** no per-trade "what would have saved
it" scoring is performed anywhere in this package. Prevention appears only as frozen
exploratory hypotheses with winner collateral. The register is evidence fields only.

**Sources (pinned):** -13 `trade_ledger.json` @521980a (sha256 267e794c…, re-verified
byte-identical) + `results.json` (42b05ce3…); -13 code `run_study13.py` (package
`equity43_dev_order_censor_20261023_13`); engine `pine_backtest.py` (stage pin
874d2a9b…); -23 census/labels (`census_output.json` 4e2e0263…, `ordering_labels.json`,
MEMO/SUPPLEMENT incl. provenance closure ab3f565); -24 `register66.json` +
`forensics_out.json` (f980f90). ALL evidence is the **offline successor-engine
simulator** over pinned Twelve Data captures. No live fill exists in any artifact.

**Population basis.** All figures use the 4bps C1 stack view (`taken_4bps` /
`disposition_4bps_c1`), the basis of record for -13/-14/-23/-24. Disclosed: the gross
view selects 188 closed trades and the 25bps view 185; views are never mixed.

## §0 — Populations reconciled (PROVEN)

- 590 candidates = 191 taken + 326 skipped_rank + 45 skipped_risk + 28 skipped_gate.
- 191 taken = 187 closed + 4 censored (CRM/MRNA/PFE/SHOP — all taken, terminal-open).
- 187 closed = 90 winners (gross > 0) + 97 losers; 97 = **66 oversized (gross < −1R)**
  + 31 ordinary (−1R ≤ gross < 0). The 66 sum **−92.0847R gross** — ties -23/-24
  exactly. Cross-check vs -24 `register66.json`: max per-trade gross deviation 0.0.
- Boundary disclosure (-24, unchanged): AMZN 2026-07-20 (gross −0.9948 / net@4bps
  −1.0082) sits between the gross and net bases; it is NOT in the 66. The net basis
  would select 67.

---

# PART A — Causal decomposition (framing A)

## §A1 — Exact semantics, cited to source (PROVEN)

All line numbers are from the pinned -13 package files.

| Element | Semantics | Source |
|---|---|---|
| Signal | `pine_buy_signal(df, i)` evaluated on the **completed** bar i (variants: confirmed / breakout_buy / ready_buy; score = 0–5 integer count of conditions). ADX thresholds (20/25) and atr_ratio are inside the signal definition — but per-candidate ADX **values** were never persisted (see §A6). | `pine_backtest.py:109–134`, `:54–66` |
| Entry | Next bar's Open. The entry bar itself is then managed. | `run_study13.py:515`; `pine_backtest.py:138,165–167` |
| Gap guard | If entry ≤ initial stop, the candidate is skipped (`skipped_gap`), never traded. | `run_study13.py:517–520` |
| Initial stop | `stop0 = signal Close − 1.5·ATR` (SL_ATR 1.5), set once, never widened. It is a **close-triggered threshold**, not a resting intrabar order: the bar Low is read (`:532`) but used by NO exit condition (supplement-verified). | `run_study13.py:516,532,539` |
| TP1 | `tp1 = entry + 2.0·ATR_signal` (TP_ATR 2.0). Modeled as an intrabar **limit**: bar High ≥ tp1 sets `tp1_hit`. Realized as a **50% partial**: blended R = 0.5·r1 + 0.5·r2 when hit, where r1 is priced at the exact limit price from `tp1` only and r2 is the runner leg; the blended exit is a single synthetic price `exit_synth = entry·(1 + r_blend·risk_frac)`. | `run_study13.py:523,533–534,551–556`; Pine-truth comment `pine_backtest.py:165–167` |
| Runner after TP1 | `runner = max(runner, Close − 2.5·ATR)` at each bar close (TRAIL_ATR 2.5), only after `tp1_hit`; before TP1 the runner IS the initial stop. Never lowered. | `run_study13.py:524,535–536` |
| Exit precedence (per bar) | (1) TP1 High test; (2) runner update; (3) stop test `Close < runner` → reason `stop`; (4) else EMA55 test `Close < e55` or trend_bear (`e21 < e55` and `Close < e200`) → `ema55-break` / `ema55-bear`. Stop wins over EMA55 on the same bar. | `run_study13.py:533–542` |
| Exit fill | Next bar's Open. Terminal exception: if the exit decision lands on the final bar, the fill is that bar's Close. | `run_study13.py:545–549` |
| Time exit | **None exists** in any of the three generator implementations (`run_study13.gen_candidates_censored`, `pine_ranking.gen_candidates`, `pine_backtest.gen_pine_trades`). The 30-bar max hold belongs to the frozen V5.4 production spec, NOT to this DEV simulator. | source inspection, all three |
| Sizing / heat | R denominator and sizing both use the **planned** width: `risk_frac = (entry − stop0)/entry` against the never-mutating initial stop; `size = risk_dollars / risk_frac` at 1% risk. Admission gate: max 5 concurrent, portfolio planned-risk cap 0.05; heat is measured at admission on planned widths and never re-measured after gap-through fills. | `run_study13.py:550`; `pine_backtest.py:57–58,215,253,260–263,281–289` |

**Simulator vs live scanner (PROVEN as a statement about the artifacts).** Every
figure in this memo describes the offline simulator. The live scanner stack (V3.7
watcher / V5.4 forward harness) shares the `pine_buy_signal` family and papers
entries at next-bar open in its own engine; its decision parity with this simulator
was established separately (-16) for the forward stack. No fill generated by any live
engine exists in the pinned record for these 187 trades, and nothing here is evidence
about live execution.

## §A2 — Decomposition of the 64 stop-route losses (framing A item 2)

The 64 = stop-route, no-TP1 members of the 66 (all labeled CONFIRMED_STOP_FIRST).
For a no-TP1 trade, `exit_synth` IS the recorded next-open fill, so the decomposition
below is exact arithmetic on persisted fields, not estimation.

| Component | Value | Status |
|---|---|---|
| Planned component (−1R × 64, definitional) | −64.0000R | PROVEN |
| Realized gross sum of the 64 | −89.9850R | PROVEN (ties §0) |
| **Combined fill-below-threshold overshoot** (fill vs the stop threshold, in R) | **25.9850R** total; median 0.2951R; max 2.1113R | PROVEN |
| — of which: trigger-bar close excursion below the threshold | — | **NOT_RECOVERABLE** |
| — of which: trigger-close → next-open gap | — | **NOT_RECOVERABLE** |

The overshoot identity was verified per trade: overshoot ≡ (stop0 − fill)/(entry −
stop0) equals the recorded excess beyond −1R to a max error of 5.0e-05 (rounding).
So the 25.9850R is provably "the fill printed below the threshold the close-based
test used" — but the split between the decision bar's own close and the overnight/
next-bar gap **cannot be recovered**: the exit-decision bar's Close is not a ledger
field and appears in no committed derived artifact (confirmed here independently of
the -23 supplement, which established the same). It is not inferred and not
vendor-backfilled. Recovering it prospectively is telemetry item T3 (§A6).

## §A3 — The 2 EMA55-route losses, stop interaction separated (framing A item 3)

| Trade | Entry → exit | Gross | Hold | rs | Label | Fill vs stop0 |
|---|---|---|---|---|---|---|
| ASTS | 2025-02-26 13:30 → 2025-02-28 09:30 | −1.0837R | 3 bars | −0.0052 | SIMULATOR_ASSUMED | −0.0837R |
| SOFI | 2025-10-15 13:30 → 2025-10-17 09:30 | −1.0160R | 3 bars | +0.0709 | SIMULATOR_ASSUMED | −0.0160R |

PROVEN: in both trades the exit fired on the EMA55 trend condition. By the §A1
precedence, the stop test (`Close < runner`) was evaluated first on the decision bar
and did **not** fire; the SIMULATOR_ASSUMED label certifies neither threshold was
touched intrabar before the exit bar. Their fills printed only 0.0837R / 0.0160R
below the stop level — i.e., these are **not** stop-overshoot cases. Their excess
beyond −1R is the small distance the next-open fill happened to print under a
never-triggered threshold; the dominant component is the planned −1R width itself,
reached via a trend exit. The 66's overshoot therefore decomposes as: 64 stop-route
trades carrying 25.9850R of fill-below-threshold overshoot, plus 2 EMA55 trades
carrying 0.0997R of incidental sub-threshold fill — different mechanisms, reported
separately throughout.

## §A4 — Time-to-failure and excursions, with winner denominators (framing A item 4)

Hold duration in bars (persisted field; PROVEN):

| Group | n | Median hold | ≤2 bars | ≤4 | ≤10 | Max |
|---|---|---|---|---|---|---|
| The 66 | 66 | 4.5 | 15 (22.7%) | 33 (50.0%) | 57 (86.4%) | — all ended by bar 30 |
| Ordinary losers | 31 | 6 | 7 (22.6%) | 13 (41.9%) | 24 (77.4%) | 34 |
| Winners | 90 | 22 | 0 | 0 | 10 (11.1%) | 139 |

Threshold excursions at the persisted-field level (labels from the closure-verified
census; PROVEN):

| Group | TP1 reached | STOP_FIRST | TP1_FIRST | SIMULATOR_ASSUMED | Breach-then-TP1 |
|---|---|---|---|---|---|
| The 66 | 0/66 | 64 | 0 | 2 | 0 |
| Ordinary losers | 5/31 | 13 | 5 | 13 | 0 |
| Winners | 90/90 | 10 | 80 | 0 | 10 |

The 10 breach-then-TP1 winners are exactly the -23 supplement's recovered set
(10 positive, +18.0417R net). **Full adverse/favorable excursion (MAE/MFE in price
terms), duration under threshold, breach counts per trade, and time-to-TP1 are
NOT_RECOVERABLE** — bar paths are not persisted fields (telemetry T4). The
threshold-touch table above is the persisted-field substitute and is labeled as such.

**Can signal quality be distinguished from execution on this record?** Partly, and
the boundary is exact: the execution-side component is fully quantified (§A2:
25.9850R of fill-below-threshold on the 64, +0.0997R incidental on the EMA55 pair).
The entry-side component is **not separable** from path variation on recorded fields:
the only persisted decision-time feature is `rs`, which does not separate the 66
from winners (-24: medians 0.0489 vs 0.0677, quartile bands overlapping; 32 of the
66 fired above the 187 median). Whether these entries were distinguishable ex ante
is **UNKNOWN** — that is precisely the telemetry gap (T1), not a finding.

## §A5 — Item 5 reconciliation (counter-read TS 1792895318.584839 point 1)

**The two claims.**
- Claim A (Muse's Oct 24 chat summary to Mike): "three of the five biggest winners
  dipped through the [initial stop] line first."
- Committed -23 evidence: "None of the top-5 winners is in the breach set"
  (MEMO.md line 99 of the -23 package).

**Definitions fixed first (from committed artifacts).** "Breach" in the census =
a bar Low ≤ the trade's **initial** stop (signal Close − 1.5·ATR, never raised) on a
bar **strictly before** the TP1-touch bar (`deep2.py:74`). Labels: CONFIRMED_TP1_FIRST
= TP1 touched with no prior breach. Post-TP1 price action is measured against the
raised runner, not the initial line.

**The committed record (PROVEN).** All five top winners by net@4bps — SNOW +8.0874,
INTC +6.4172, AMD +5.9181, QCOM +5.3470, LRCX +4.8903 — are labeled
CONFIRMED_TP1_FIRST in `ordering_labels.json`: none crossed the initial stop before
TP1. The closure-verified census confirms the 87 breach keys equal the
CONFIRMED_STOP_FIRST key set exactly; no top-5 winner is among them.

**Where the "3" actually lives (PROVEN).** Of the 87 STOP_FIRST trades, 10 finished
positive and exactly 3 finished ≥ +2R net: **RKLB +4.4126** (entry 2026-04-30),
**ARM +3.1416** (2026-03-31), **F +2.5360** (2026-05-15). None is a top-5 winner.

**Post-TP1 crossings of the original line: UNKNOWN.** No committed artifact ever
tested post-TP1 bars against the initial stop (`deep2.py` never evaluates them), so
no claim either way is made. Economically the question is moot for exits: after TP1
the binding threshold is the raised runner.

> **RESOLVED TRUTH: 0 of the top-5 winners crossed the initial stop before TP1. The
> "3" belongs to the breach set's ≥ +2R recoveries (RKLB / ARM / F). Claim A is
> incorrect.** It arose in Muse's own Oct 24 chat summary to Mike, which transposed
> the breach-set recovery count onto the top-5. That chat statement is retracted and
> replaced by this section. (A related chat statement — that the stop design's
> patience is what let winners recover — survives only in the weaker, supported
> form: 10 STOP_FIRST trades, ARM/F/RKLB among them, recovered to positive after
> crossing the initial stop pre-TP1; whether a hard stop would have changed their
> outcomes is a counterfactual this record does not contain.)

## §A6 — Minimal prospective telemetry spec (framing A item 6)

Adopting ChatGPT's counter-read field list (-24 thread, TS 1792895199.248829) as the
baseline, plus the -25 additions. Each register UNKNOWN is bound to exactly one key.

| Key | Record | Answers |
|---|---|---|
| T1 | Signal state at fire: every entry-predicate value + threshold + margin; ADX/DI; trendScore; VWAP distance; rel-volume; EMA states; rs and benchmark as-of; signal grade; gate reasons | §A4 entry-side separability; -24 H-F1 (ADX) |
| T2 | Admission state: slot count, sector occupancy, planned heat before/after, rank margin vs the last admitted candidate | capacity/rank questions; §B5 mechanics |
| T3 | Exit-decision bar OHLC + the threshold values in force on that bar (runner, EMA55) | §A2 overshoot split (trigger-close vs gap) |
| T4 | Bar-level threshold events during each trade: first TP1/stop touch bar ids, breach count, duration under threshold, MAE/MFE | §A4 excursion table; shakeout questions |
| T5 | Geometry series: entry, initial stop, TP1, runner value per bar | stop-definition audits |
| T6 | Execution records: order / acknowledgment / fill price + timestamp, per leg | any fill claim |
| — | Deterministic input hashes; completed bars only, never unfinished | reproducibility (all) |

**Fills cannot be established by feed-only observation (PROVEN as a structural
statement).** A market feed carries the market's prints, not the account's
executions; the -22 pilot measures bar arrival/finalization, not fills. Any future
fill claim requires separately authorized paper execution with order records (T6)
plus stated spread/slippage assumptions; the shadow cohort (S1) as designed is
signal-only and produces no T6 records.

---

# PART B — Post-exit lifecycle and re-entry (framing B + counter-read rulings)

## §B1 — Method: whole-book evaluation (ruling 1)

Per-loss "subsequent candidate" lists double-count: one later candidate is
"subsequent" to every earlier same-symbol loss (459 per-row views). The corrected
unit is the **book-level distinct set**: every candidate whose signal time follows
at least one of the 66 exits **in its own symbol**, counted **once**, and
**single-assigned** to the most recent prior 66-exit in that symbol (its anchor;
carried per-candidate in the register as `assigned_anchor_66_entry_time`).
Dispositions (`taken` / `skipped_rank` / `skipped_risk` / `skipped_gate`) are the
pinned simulation's whole-book outcomes — rank, sector and heat decisions taken
against the entire book at that moment — and are interpreted only as such, never as
per-symbol judgments. Skipped candidates' outcomes are standalone simulations,
**not** portfolio counterfactuals; that label applies everywhere below.

## §B2 — Candidate accounting (ruling 2, first half)

| Set | n |
|---|---|
| Distinct post-exit candidates after the 66 | **256** |
| — taken (incl. 4 censored) | 108 |
| — taken, closed | 104 |
| — skipped (rank 119 / risk 19 / gate 10) | 148 |

Reconciliation against the counter-read's **258**: the count was re-derived under
every convention the artifacts support — strict timestamp comparison 256;
non-strict (≥) 257; anchor set on the gross view (69 trades) 256; on the net view
(67 trades) 256. **A residual of 1–2 candidates vs 258 is NOT RECONCILED under any
tested convention and is named here rather than smoothed**; the boundary convention
accounts for at most +1. The counter-read's substantive point stands independently
of the residual: a first-subsequent-only view would carry 66 candidates and drop
192 of 258 (190 of the reproduced 256). **No such truncation is used anywhere in
this memo — all 256 enter the composition test.**

## §B3 — Composition test: does the post-exit set differ from the loss set? (ruling 2)

Recorded fields only; the all-candidate population is the base-rate comparator
(the 66 are 100% taken by construction, so disposition comparisons run against
the book, not against the 66).

| Field | The 66 | Post-exit set (256) | All 590 |
|---|---|---|---|
| Taken rate | 66/66 (by construction) | 108/256 = 42.2% | 191/590 = 32.4% |
| FINTECH share | 13/66 = 19.7% | 31/256 = 12.1% | 63/590 = 10.7% |
| SEMIS share | 13/66 = 19.7% | 66/256 = 25.8% | 142/590 = 24.1% |
| rs median | 0.0489 | 0.0509 | 0.0402 |
| TP1 rate (standalone/taken as recorded) | 0/66 = 0% | skipped 47.3% / taken 51.9% | 47.1% (of 586 closed) |
| Exit-reason mix (taken) | stop 64 / ema55 2 | stop 87 / ema55 17 | — |

**PROVEN (descriptive):** on every recorded composition field, the post-exit set
resembles the general candidate population, not the loss set — its TP1 rate, rs
median and sector mix sit at book base rates. It differs from the 66 exactly on the
fields the 66 were *selected* on (0% TP1, oversized loss, all-taken). There is no
recorded sense in which the names that stopped out kept generating a distinct,
loss-like candidate stream afterward. **SUGGESTED only:** the FINTECH share
normalizing from 19.7% (the 66) to 12.1% (post-exit) is consistent with -24's H-F2
being a window/selection artifact rather than a persistent symbol property; with
17 features interrogated on 66 events in -24, this stays a frozen hypothesis.

## §B4 — What the book actually did next (book-level outcomes)

- Taken after the 66 (distinct, closed): **104 trades, +11.7679R gross, 51 winners,
  TP1 rate 51.9%** (+0.113R/trade).
- Skipped after the 66: 148 candidates, standalone gross sum **+27.788R**
  (**standalone simulations — not portfolio outcomes**; the book did not take them,
  mostly on rank: 119 of 148).
- Per-row views (superseded, for continuity with the register): subsequent taken
  trades viewed with multiplicity summed +1.8584R over 194 views — the difference
  from the distinct figure is pure assignment multiplicity (heavily-followed symbols
  like LRCX/MELI contribute the same later trades to many rows) and is why the
  distinct set is the unit of record.

Interpretation guardrail: these aggregates describe what the frozen system did next
in those symbols inside this DEV window. They are **not** an evaluation of a
"re-enter after stop-out" strategy, and no such strategy is proposed.

## §B5 — Winner-side baseline (proposal 1)

Identical construction anchored on the 90 winners' exits: **346 distinct
candidates**; 106 taken closed, **+23.0728R gross, 51 winners, TP1 rate 50.9%**
(+0.218R/trade); 236 skipped, standalone +12.8351R; taken rate 110/346 = 31.8%.

**SUGGESTED (mechanical reading, not an edge claim):** the post-stop-out taken rate
(42.2%) exceeds both the book base rate (32.4%) and the post-winner rate (31.8%).
A stop-out frees its slot after a median 4.5 bars; a winner occupies its slot for a
median 22 bars, and same-symbol candidates generated while the book is full are
rank/heat-skipped at higher rates. Slot availability is sufficient to explain the
gap on recorded fields; telemetry T2 would settle it prospectively (hypothesis
H-L1, frozen). Per-trade taken means after stop-outs (+0.113R) vs after winners
(+0.218R) are both within the book's ordinary variation and are **not** evidence
that either anchor class predicts the next trade.

## §B6 — The 5 with no subsequent candidate: censoring, not absence of recovery

5 of the 66 have no subsequent same-symbol candidate in the record: ASTS (exit
2026-06-05, 132 days of follow-up), LRCX (2026-07-02, 105d), ARM (2026-10-08, 7d),
AMZN (2026-10-14, 1d), NU (2026-09-11, 34d). **PROVEN (classification):** these are
exactly short-follow-up cases — the DEV record ends 2026-10-16 — and no 66-trade
with a longer follow-up window lacks a subsequent candidate. "No subsequent
candidate" means **no recorded re-signal inside the window**; whether those names
recovered afterward is **UNKNOWN** and unknowable from this record. This is the
distinction framing B required: missing post-exit record ≠ evidence of no recovery.

## §B7 — Worked examples

**(1) LRCX, the required case (framing B).** The Feb 24–25 2025 stop-out is row 1 of
the register: signal 2025-02-24, exit 2025-02-25, gross −1.3534R, no TP1,
CONFIRMED_STOP_FIRST. The symbol's full recorded lifecycle afterward (16 further
candidates): taken May 27 2025 −1.5806R; taken Aug 14 2025 −2.4831R; taken Dec 15
2025 −1.3502R; **taken Dec 18 2025 +4.8989R gross (+4.8903 net) — the #5 winner of
the whole book, TP1 hit, protected-stop exit after 60 bars**; taken Feb 6 2026
+0.6897R; taken Jun 25 2026 +0.5111R; taken Jul 1 2026 −1.4754R (itself a member of
the 66 — and the register's one LRCX row with no subsequent candidate, 105 days of
censored follow-up). Interleaved skipped candidates include standalone winners the
book never took (Jun 6 2025 +2.7765R, Sep 24 2025 +2.4954R, both TP1-hit, both
skipped on rank). One symbol produced repeated oversized losses AND a top-5 winner
AND skipped winners — the whole distribution, in one name. Any per-symbol story
told from one slice of this timeline is selection, not analysis.

**(2) CRM — rule-picked counter-example (proposal 3).** Frozen rule: the largest
recorded re-entry loss after a stop-out, chosen mechanically from the distinct set.
CRM's anchor stop-out: entry 2025-05-14, exit 2025-05-23, −1.1761R. The re-entry:
signal 2026-01-06 09:30, taken, exit 2026-01-13, **−3.1113R gross — the largest
single loss in the entire 187** — 10 bars, no TP1, rs −0.0088, and its overshoot
(2.1113R) is the maximum in the 64 of §A2. The LRCX case shows re-entry eventually
paying; the CRM case shows the same mechanism producing the book's worst trade.
Both are in the record; neither generalizes alone.

**(3) MELI — the repeat member.** MELI contributes 5 of the 66 (Feb, Jun, Sep,
Oct/Nov 2025, Aug 2026). Between its stop-outs the book also took an ordinary loss
(Mar 2025, −0.3641R) and a winner (Jul 2026, +0.8836R, TP1 hit), and skipped a
standalone +2.4782R winner on rank (Apr 2025). MELI is the clearest single-symbol
refutation of "the symbol was the problem": same name, every outcome class.

**(4) ASTS — the EMA55 pair member.** Its Feb 26 2025 ema55-break trade is one of
the two §A3 cases. ASTS adds two more members of the 66 (Mar and Jun 2025), a
skipped standalone +3.8427R winner (Sep 2025, rank), a taken winner (Dec 2025,
+0.4433R), another member of the 66 (Dec 2025, −1.1625R), a risk-skipped standalone
+2.2620R (Dec 30 2025), and a final member of the 66 in Jun 2026 (−1.8401R) whose
132-day follow-up with no re-signal is §B6 censoring, not a verdict on the name.

**(5) AMZN — pure censoring.** The Oct 14 2026 member of the 66 (gross −1.1471R)
exited one day before the record ends. Its register row has an empty subsequent
list and a 1-day follow-up: the correct reading is "no observation window," full
stop. (The other AMZN oversized loss, Oct 2025 −2.0488R, was followed by taken
trades netting +2.15R in Dec 2025–Jan 2026 and a +5.08R standalone winner skipped
on rank in Jun 2026 — in the register.)

## §B8 — Recurring patterns, labeled

| # | Statement | Label |
|---|---|---|
| 1 | The 64 stop-route losses decompose exactly into planned −64.0000R + 25.9850R fill-below-threshold overshoot; the EMA55 pair's excess is a different, incidental mechanism (0.0997R). | PROVEN |
| 2 | The overshoot's split into trigger-close excursion vs next-open gap is not in the record. | UNKNOWN (×64 trades) |
| 3 | 0 of the top-5 winners crossed the initial stop pre-TP1; the "3" is RKLB/ARM/F from the breach set. The contrary chat claim is retracted (§A5). | PROVEN |
| 4 | Post-exit candidates are compositionally ordinary (book base rates on all recorded fields); the loss set's distinctiveness is outcome-selected, not a persistent stream property. | PROVEN (descriptive) |
| 5 | Re-entries after stop-outs, as the book actually took them: 104 trades, +11.7679R, 51 winners — mildly positive in aggregate inside this window; NOT a strategy evaluation. | PROVEN (descriptive) |
| 6 | Post-stop-out taken-rate elevation (42.2% vs 31.8% post-winner) is explainable by slot mechanics alone. | SUGGESTED → frozen H-L1 |
| 7 | FINTECH share normalizes post-exit (19.7% → 12.1%), consistent with H-F2 being selection/window artifact. | SUGGESTED (H-F2 unchanged) |
| 8 | The 5 no-re-signal rows are right-censoring (follow-up ≤132d, two ≤7d); recovery after the window is unknowable here. | PROVEN (classification) / UNKNOWN (recovery) |
| 9 | Signal quality vs execution is separable only on the execution side; entry-side distinguishability needs T1 telemetry that was never recorded. | PROVEN (boundary) / UNKNOWN (entry side) |
| 10 | No recorded entry-time field separates the 66 — not rs, slot state, geometry, sector, weekday, or year (-24, re-verified here). ADX at fire was never persisted. | PROVEN (recorded fields) / UNKNOWN (unrecorded) |

**Frozen hypotheses carried or opened (none tested here, none asserted):**
H-F1 (ADX/signal-internal state at fire differs for oversized losers — needs T1);
H-F2 (FINTECH tilt — -24 definitions frozen, prospective evaluation only);
H-L1 (post-stop-out taken-rate elevation is slot-availability mechanics — needs T2).
No rule change is proposed by this memo. Candidate prevention ideas remain
hypotheses until a prospective cohort with T1–T6 telemetry exists.

## Register

`register_lifecycle66.json` — 66/66 rows, evidence fields only: identity, sector,
signal/entry/exit times, entry/stop/TP1 geometry, tp1_hit, rs, exit price (synthetic
model price), reason, hold, gross and net@4bps R, ordering label, planned −1R,
overshoot (stop-route rows) or the separated note (EMA55 rows), follow-up days, the
full subsequent-candidate list with each candidate's single-assignment anchor, and
per-row `unknowns` — one named missing record per UNKNOWN, bound to its telemetry
key (§A6). Machine outputs: `lifecycle_out.json`, `lifecycle_v2_out.json`; scripts
`lifecycle.py`, `lifecycle_v2.py`, `register_v2.py`. Hashes in `SHA256_MANIFEST.txt`.

## NOT_RECOVERABLE inventory (per part)

**Part A (4 classes):** (1) trigger-close vs next-open-gap split — all 64 stop-route
trades; (2) bar-path excursions (MAE/MFE, duration under threshold, breaches/trade,
closest TP1 approach) — all 66; (3) TP1-touch-bar timing — all 66 (boolean only);
(4) any live/executable fill record — all 66 (none exists).
**Part B (3 classes):** (1) post-window recovery for the 5 censored rows;
(2) portfolio counterfactuals for the 148 skipped post-exit candidates (standalone
simulations only); (3) market/benchmark state on re-entry dates (no benchmark series
persisted). Plus the §B2 residual: 1–2 candidates vs the counter-read's 258,
unreconciled under every tested convention and named, not smoothed.

— Muse. Posted for independent counter-review. Production PAUSED, holdout SEALED,
pilot untouched, S1/G4 holds unchanged.
