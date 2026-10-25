# -27 — FINAL technical review + measurement-fix work on Claude's Pre-Registration Draft (v0.2 as relayed) — checklist, evidence, and redlines for v0.3

**Date:** 2026-10-25 (ET). **Lane:** Muse, single dispatch.
**Governing texts:** ChatGPT action request, Slack TS 1792900907.855189 (Oct 25 00:01 ET); ChatGPT page-anchored redlines on the draft, Slack TS 1792900539.201259; Claude's agreement + second EXIT study proposal as relayed, Slack TS 1792900628.618089; Muse counter-position, Slack TS 1792900716.543899 (bridge 77f828c).
**Evidence pin:** blind-review packet at repo commit 555ebb1 (ZIP sha256 2ef1e8c3…); all source citations below are to the packet copies, whose sha256 values are in the packet MANIFEST.json and were re-verified for this review (14/14 match, §6).

## 0. Access disclosure — read this first

Claude's draft — v0.2 (23 pp.) per the action request; v0.1 (19 pp.) per ChatGPT's earlier message — is **NOT accessible to this lane**. Searched 2026-10-25 ~00:28 ET: the Slack desk (full recent history), Issue #1 (all pages via the public API; latest comment 6393039363), the repo and bridge thread (0 occurrences of the draft title), and workspace staging (no candidate PDF). The claude.ai artifact link resolves to a sign-in wall from this environment. **No page of the draft has been read by Muse.** An explicit file/export request is posted on both channels (Slack ACK TS 1792902479.533589; bridge ACK 2fe628f).

Consequences, applied mechanically:

- Every checklist item whose object is the draft's own text (hypothesis wordings H-BUY / H-EXIT / H-SYS, the tier structure, §7A/7B/7C, the §9 contamination-audit text, the power section, the GO/NO-GO criteria) is **BLOCKED (access)** — §1, block C.
- The measurement-fix items P1–P11 are defined in the action request itself and in tonight's verified findings (-23/-25/-26), so they proceed on source and ledger evidence that is on the record.
- All redlines in §5 are labeled by provenance: **[GPT-relay]** = ChatGPT's page-anchored redlines; **[Claude-relay]** = Claude's positions as relayed; **[Muse]** = my counter-position; **[EVIDENCE]** = decided by source/ledger verification in this review or -23/-25/-26. Relay-based redlines must be re-verified against the real pages when the PDF lands; nothing here claims otherwise.

## 1. Checklist — DONE / IN PROGRESS / BLOCKED

No ETAs are invented. Each blocked item states exactly what it waits on.

### Block A — measurement-fix items executed (authorized layer: documentation / measurement-spec / parity-analysis on recorded artifacts)

| Item | Status | Evidence |
|---|---|---|
| P1 (spec + verification) | **DONE** | §2.1: all-bar MTM specification written; event-sampled marking verified from source in BOTH simulators |
| P2 rank semantics | **DONE** | §2.2: semantics written from frozen source, incl. the free0 finding |
| P3 SPY-asof | **DONE** | §2.3: documented from asof_benchmark.py |
| P5 cost convention | **DONE** | §2.5: frozen convention characterized from source; prospective convention specified; DEV comparison untouched |
| P6 leverage/exposure reporting | **DONE** | §2.6: reporting specification; source facts pinned |
| P7 plan | **DONE** | §2.7: two-universe plan; execution blocked (Block B) |
| P8 telemetry plan | **DONE** | §2.8: instrumentation plan (Mike's full-state journal + T1–T6) |
| P9 ledger parity (4bps C1 view) | **DONE — parity exact** | §3: recomputation from the committed ledger matches results.json on every headline figure |
| P10 data audit | **DONE** | §6.1 |
| P11 version audit | **DONE** | §6.2 |

### Block B — proposed changes, NOT executed (frozen-source / behavior layer; Mike's hard gate)

| Item | Status | Waits on |
|---|---|---|
| P4 stop-docstring edit in pine_backtest.py | **BLOCKED — proposal delivered** (§2.4, exact erratum text + diff intent) | Mike GO for a frozen-source documentation edit + re-pin of the file in any future packet |
| P1 in-simulator all-bar MTM implementation | **BLOCKED — proposal delivered** (§2.1) | Adjudication of the spec + Mike GO (accounting-layer code change in the frozen successor source) |
| P7 unsuppressed (all-fire) generation pass | **BLOCKED — plan delivered** (§2.7) | Separate GO: it is a code change plus a generation run; neither is authorized in this lane |
| P9 25bps-view parity | **BLOCKED — gap named** (§3) | A committed per-cost-view ledger/taken set; producing one is a run artifact, not authorized here |

### Block C — PDF-dependent review areas

| Area | Status | Waits on |
|---|---|---|
| H-BUY / H-EXIT / H-SYS texts; tiers; §7A/7B/7C; §9 audit text; power section; GO/NO-GO criteria; 6-month forward timeline language | **BLOCKED (access)** | The v0.2 PDF (and v0.1 if distinct) posted to the repo/bridge or pasted in full. The file/export request is posted; no review of unread text is claimed. Redlines §5 stand against the relayed summaries only. |

## 2. Per-item evidence

### 2.1 P1 — Bar-by-bar MTM drawdown

**Verification (source, packet pin).** Both simulators mark equity only at event timestamps:

- `pine_stack.py:72`: `times = sorted(set(entries_by_t) | set(exits_by_t))` — the equity loop iterates entry/exit event times only; marking and peak/DD update occur inside that loop.
- `pine_backtest.py:308-316`: the successor's `marked_equity(t)` / curve / `max_dd` update runs over the same event-time set.

Therefore the DEV **24.61% max drawdown is an event-sampled LOWER BOUND** on the all-bar marked drawdown (-26 item 5, re-verified here). The all-bar figure is **UNVERIFIABLE from the packet** (no bar series is committed) and is **not** recomputed in this lane: re-marking positions bar-by-bar requires the price bars and an equity-path re-execution, which is outside ledger arithmetic.

**Specification (for the fix, prospective).** (i) Equity is marked at every admitted 4H bar close on the union calendar of the run's symbols. (ii) At each bar close t: equity(t) = realized cash + Σ over open positions of size × close(t), with TP1-hit positions valued under the frozen blended-exit convention. (iii) Max drawdown is computed on that all-bar series; the event-sampled series is retained as a cross-check and the invariant all-bar DD ≥ event-sampled DD is asserted. (iv) Every results template carries the caveat sentence verbatim until the fix lands: "Drawdown is event-sampled and is a lower bound on all-bar marked drawdown." (v) Implementation is confined to the accounting layer (the `marked_equity` call sites and the time grid); no signal, ranking, or exit logic changes. (vi) Verification fixture: a synthetic position whose intra-event excursion exceeds both neighboring event marks — current code reports the smaller event-sampled DD (fail-before); fixed code reports the excursion (pass-after).

**Proposal status:** implementation in the frozen successor source is Block B.

### 2.2 P2 — Rank semantics, written from frozen source

Authoritative behavior (packet pin):

- Candidate processing order is the config-pinned canonical key **(symbol, signal_idx) ascending** (results.json `experiment_config.candidate_processing_order`; -17 contract).
- At each event timestamp, `pine_stack.py:129` computes `free0 = MAX_CONCURRENT − len(open_pos)` — and **never reads it again** (grep: single occurrence in the file). It is dead code.
- The operative value is **live per-candidate**: `pine_stack.py:133` recomputes `free = MAX_CONCURRENT − len(open_pos)` inside the candidate loop; `:134` sets `contested_now = n_cands_t > free` on that live value; `:135` applies the rank cap `taken_at_t >= min(2, free)` at contested timestamps (rs_top2: top-2 by 20-bar return minus SPY per contested timestamp).
- The R1 reference implementation agrees: `pine_ranking.py:213-221` computes `free` per-candidate in-loop and defines contested on the live value; its docstring (`:137-141`) promises entries "taken in rank order" with ranking engaging "only at contested timestamps" — no timestamp-start snapshot rule exists in either the implementation or the reference (-26 item 1: implementation == reference; the deviation claim is DISPUTED, the dead-code fact is CONFIRMED).
- Downstream gates in order: rank cap → `free <= 0` → skipped_cap; sector cap → skipped_gate; portfolio heat (5% cap) → skipped_risk. Ledger dispositions reproduce exactly: taken 191 / skipped_rank 326 / skipped_risk 45 / skipped_gate 28 (§3).

**Spec sentence for v0.3:** "Ranking engages per candidate against live portfolio state; a timestamp is contested for a candidate when the number of candidates at that timestamp exceeds the live free slots; at most min(2, live free) candidates are taken per contested timestamp. No timestamp-start slot snapshot is used." Any draft text implying a `free0`-style snapshot is wrong against both sources.

### 2.3 P3 — SPY benchmark as-of rule, documented

`asof_benchmark.py:31` stamps daily benchmark bars at **16:00 ET** on the session date (`SESSION_CLOSE = 16:00`); the module policy (`:14-19`) states early-close sessions are also stamped 16:00 — "conservative (later, never earlier), so the policy can **only delay, never leak**." With completion-stamped bars, the unchanged frozen selection rule (last index ≤ t) is causally correct: at 09:30 or 13:30 ET on day D it selects day D−1's completed session. Consequence, already established in -09/-26 item 2: the benchmark leg of the 20-bar relative-strength window ends **one session before** the symbol leg — a known, causal-by-design one-session delay, not lookahead. v0.3 must state the rule in exactly these terms wherever rs / benchmark matching is specified, including the §5 matched-baseline construction.

### 2.4 P4 — Stop docstring contradiction: erratum proposal (NOT executed)

**Contradiction (source).** `pine_backtest.py:18` (module docstring): "exits: intrabar stop (stop-first on ties), TP1, close<EMA55 or trendBear". The same file's own comment at `:166-168` states the truth: "Pine truth: TP1 is a real intrabar LIMIT order; the 'stop'/trail/EMA55 exits are all close-evaluated -> market exit at NEXT bar open. (The script never passes a stop= to strategy.exit.)" The code agrees with the comment: TP1 fills intrabar at the limit when the bar High reaches it (`:171-173`); the stop test is `close < pos["runner"]` (`:179-181`); fills are at the next bar's open (`:186-190`). The packet README is clean; the fault is in the simulator source docstring only (-26 item 4).

**Exact erratum text proposed** (docstring-only; zero behavior change):

- Replace line 18's exit clause with: "exits: TP1 is an intrabar LIMIT order (fills at the limit when the bar High reaches it, 50%); the stop/trail and EMA55/trend-bear exits are CLOSE-evaluated (close < runner; close < EMA55 or trend-bear) and fill at the NEXT bar open. There is no intrabar stop and no stop-first tie rule."
- Clarify line 16: "TP1 = fill + ATR*2.0" → "TP1 = entry fill + ATR*2.0", where entry fill is the next bar's open (code: `pine_backtest.py:157`, `tp1 = entry + atr * TP_ATR`; identically `pine_ranking.py:44`). This also settles the §7 E0 anchor question from source: **the TP1 anchor is the entry fill**, and Claude's relayed "TP1 = fill + 2 ATR" and the frozen "entry + 2.0·ATR" are the same anchor, because entry is defined as the fill. E0 fidelity on this point is CONFIRMED from source; the draft must still state the anchor explicitly (redline R3).

**Diff intent:** two docstring lines in one file; no executable line changes; the file's sha256 changes, so any future packet/manifest must re-pin it. Execution waits on Mike's GO (Block B).

### 2.5 P5 — Cost convention

**Frozen DEV convention, from source.** `pine_backtest.py:214-218` (`_outcome`): `net_ret = gross_ret − cost`, applied **once per trade**, with cost ∈ {0.0004, 0.0025} (`COSTS`, `:60`). In words: DEV's "25bps" is a **single flat charge of 25bps of entry notional per round trip** — not per fill, not on exit notional, not split 12.5/12.5. Claude's §8 concern [GPT-relay] is therefore well-aimed at any draft text that describes DEV costs as per-fill: per-fill on traded notional is **not equivalent** whenever exit price ≠ entry price (and TP1 partial fills trade a different notional again).

**Specification (prospective, declared, DEV comparison untouched).** "Transaction cost is charged per fill on the actual traded notional of that fill: cost_fill = bps × |fill price × shares filled|. Round-trip cost is the sum over fills. The DEV record's flat per-trade convention is retained as the DEV comparison basis and is never silently restated; any result under the per-fill convention is a new computation under a new convention label." The 25bps stress leg is KEPT under this declaration (counter-position). Note the interaction with P9: changing the convention changes every net R, so a byte-identical-ledger parity claim can only ever apply to the frozen convention (redline R6, §3).

### 2.6 P6 — Leverage / exposure reporting

**Source facts.** No notional or cash cap exists anywhere in the frozen source. The only caps are count and heat: `pine_backtest.py:57-60` — `MAX_CONCURRENT = 5`, `MAX_PORTFOLIO_RISK = 0.05`, `RISK_PCT = 0.01`. Position size = `risk_dollars / risk_frac` (`pine_stack.py:296-297` region; `pine_backtest.py` `_outcome` risk_frac = (entry − stop)/entry), so notional scales inversely with stop width and is unbounded by any equity fraction. Heat (Σ planned risk / equity) is **not** leverage (-26 item 3: CONFIRMED; Claude's ~2.8x proxy reproduced as 2.83x under a flat-equity reconstruction; exact peak UNVERIFIABLE from the packet).

**Reporting specification (prospective, every results template).** Per position: entry notional (size × entry). Per event timestamp: gross exposure = Σ|open notional| / equity; net exposure likewise signed. Per run: peak gross exposure, mean gross exposure, and the notional path's maximum single-position share — reported **alongside, never instead of,** heat. Any draft sentence equating the 5% heat cap with a leverage or exposure bound is struck (redline R20 area; §5 R-list).

### 2.7 P7 — Unsuppressed signals: plan; execution blocked

**Fact.** Candidate generation is serialized per symbol (`pine_ranking.py:28-47`; `pine_backtest.py:144-165` generation loop): a standalone trade occupies its symbol until its standalone exit, taken or skipped; the ledger contains 0 overlapping same-symbol intervals in 590 (-26 item 6). **The 590 are non-overlapping standalone candidates, not all signal fires.** Every rate computed on the 590 carries this qualifier (-25/-26 discipline).

**Plan.** Two named universes, kept distinct in every document: (U1) **standalone-candidate universe** — the 590, available now, inference bounded by suppression; (U2) **all-fire universe** — every signal fire including suppressed ones; requires a generation-only pass with same-symbol suppression disabled, in a research fork, journaling full signal-time state per §2.8. U2 is **specified-but-unpopulated** until a separate GO authorizes the code change and the generation run. No draft text may imply all-fire coverage it does not have (redline R14).

### 2.8 P8 — Telemetry instrumentation plan

Prospective requirement, adopted by Mike (bridge 9087bf0) and consistent with the -25 §A6 keys T1–T6: at **every** candidate fire, taken or not, the journal records the full signal-time state — ADX and trend readings, EMA geometry, price-vs-VWAP relation, relative volume, market-gate state — plus every price level (signal close, ATR, stop threshold, TP1), the portfolio state at fire (open count, heat, sector counts), the disposition and its reason, and at any exit the trigger bar's close and the fill price. Storage is append-only under the capture-receipt discipline. Retro-DEV cannot satisfy this: those fields are NOT_RECOVERABLE for the DEV record and must be labeled as such wherever a draft implies DEV can supply them (redline R17). The plan is documentation; building the journal belongs to the S1/shadow lane, whose launch is separately gated.

## 3. P9 — Ledger parity proof (ledger arithmetic only) + the 25bps gap

Recomputed from the committed `trade_ledger.json` (sha256 267e794c…) and diffed against `results.json` (sha256 42b05ce3…), P5_run 4bps row. Recomputation script retained in the lane workpapers.

| Figure | Ledger recomputation | results.json | Verdict |
|---|---|---|---|
| Candidates | 590 | 590 | exact |
| Dispositions (4bps C1) | taken 191 / skipped_rank 326 / skipped_risk 45 / skipped_gate 28 | taken 191; skipped_max_positions 326; skipped_max_risk 45 | exact (naming differs) |
| Closed taken | 187 | 187 | exact |
| Terminal censored taken | 4 — CRM, MRNA, PFE, SHOP | 4, same inventory | exact |
| Net R @4bps, sum / mean | +32.4873R / +0.17373R | expectancy 0.174 (rounded) | exact |
| Profit factor @4bps | 1.283 | 1.28 | exact |
| Win rate @4bps | 48.1% | 48.1% | exact |
| Avg hold | 16.7 bars | 16.7 | exact |
| Top-5 share of net | +30.6600R = 94.3753% | record states 94.37% | consistent (94.37 vs 94.38 is intermediate-rounding, not a discrepancy) |
| Max drawdown | not ledger-recomputable (needs closes + stack marking) | 24.61% | carried as reported; source-verified event-sampled lower bound (§2.1) |

**The 25bps gap (NEW, material to the draft).** results.json's 25bps row reports **185 trades @ 0.108** (established record figure: +0.10751R). The committed ledger carries only the 4bps-C1 dispositions, plus a per-trade `net_r_25bps` value for each 4bps-taken trade; recomputing that column over the 4bps taken set gives **187 trades @ +0.10753R** — a different taken set and a different mean. The 25bps stack evidently selected its own taken set (costs feed the heat/risk path), and that set is **not committed**. Consequences: (i) parity is proven for the 4bps C1 view only; (ii) any v0.3 claim of a "byte-identical 590 ledger" must be scoped to the frozen 4bps convention, and (iii) under a changed §8 convention (§2.5) the ledger's R values change by construction — the parity claim and the cost-convention change cannot both apply to the same ledger. v0.3 must either commit per-cost-view ledgers or scope the claim (redline R19). Producing the missing ledger is a run artifact — Block B, not executed here.

## 4. ChatGPT's six flagged v0.2 ambiguities — disposition

1. **P9 byte-identical ledger vs changed cost convention** — RESOLVED as a matter of logic + evidence (§3): the parity claim is scoped to the frozen convention; a changed convention yields a new ledger, and the 25bps view already demonstrates taken-set divergence.
2. **Stage A pooling Tier 2/3 while Tier 2 possibly contaminated** — NOT resolvable without the §9 audit outcome and the PDF text; redline R10 makes pooling conditional on the exposure audit, not on possession.
3. **H-SYS "mean per closed trade" with censored open positions** — the frozen -13 treatment is on record (results.json `censoring_treatment`: censored taken positions are valued in equity at the as-of mark, excluded from closed-trade R; no R fabricated). v0.3 must declare which estimand H-SYS uses; mixing equity-inclusive returns with closed-trade means is incoherent (redline R11). PDF text itself: BLOCKED (access).
4. **7C differing trade lists; per-trade mean vs portfolio return** — redline R12; the DEV record itself shows the two diverge (per-trade mean +0.17373R vs total return +42.44% on the 4bps row). Text-level check: BLOCKED (access).
5. **Minimum 6-month forward timeline** — the power arithmetic governs (counter-position): at DEV accrual (~90 taken trades/yr; ~150/yr at the most generous reading), 6 months yields ~45–75 trades against a requirement of ≈870 independent trades (≈1,340 under the frozen Holm family) for a d≈0.095 effect — a 6-month leg cannot confirm by significance and must be labeled accrual/exploratory with INCONCLUSIVE pre-committed as an expected outcome (redline R2).
6. **Bootstrap blocks and dependence** — redline R13: the frozen inference contract specifies **20-session** circular blocks, 10,000 SplitMix64 reps; 20-bar blocks (≈3.3 sessions) sit well inside the dependence range of overlapping multi-day holds (DEV avg hold 16.7 bars).

## 5. Redlines for v0.3 (headline list)

- **R1 [GPT-relay + Claude-relay + Muse]** §11 PASS: with L>0 ∧ point estimate ≥ δ, a PASS asserts only "consistent with an effect ≥ δ" — label it exactly that ("positive; minimum effect not established"), per the frozen contract's semantics (economic gate primary; a p-value never rescues a failed economic gate). No promotion language from an underpowered PASS. Final claim wording is Mike's fork.
- **R2 [Muse]** Power honesty: attach the arithmetic (n≈870 unadjusted / ≈1,340 Holm-family for d≈0.095 at 80% power; holdout ≈85 trades → ~14% power; DEV accrual ~90/yr). Strike any confirmatory-significance promise on near-term samples; rewrite the forward-timeline language (12-month in v0.1-relay; 6-month minimum in v0.2-relay) to accrual terms with INCONCLUSIVE pre-committed as expected.
- **R3 [EVIDENCE]** §7 E0 fidelity pin: stop = signal Close − 1.5·ATR, close-triggered, fill next open; TP1 = **entry fill** + 2.0·ATR priced at the limit (anchors proven identical from source, §2.4). Label E0 an isolation study, not H-SYS. Carry Claude's caveat [Claude-relay]: the original Pine recomputes TP1 live, and de-clustered unsuppressed events are not the strategy candidate set — the second, candidate-set EXIT study needs its own paired-entry estimand, specified separately from full strategy replay (exit changes alter subsequent signals).
- **R4 [GPT-relay]** H-EXIT-3: predeclare the sign (E3−E0 or E0−E3) and the null before freeze; an unsigned paired endpoint is unfalsifiable.
- **R5 [GPT-relay + Claude-relay]** E2 conservative TP1 fill is a **robustness** leg, not a superiority test; state which multiplicity family it sits in; it must not consume the superiority Holm family as an improvement claim.
- **R6 [EVIDENCE]** §8 cost convention: declare per-fill on actual traded notional prospectively; never describe the DEV record as per-fill (it is a single flat per-trade charge on entry notional, §2.5); scope all ledger-parity claims to the frozen convention.
- **R7 [GPT-relay]** §6 "FAIL-incapable": strike or qualify — a CI half-width argument bounds detection of small effects; a large negative effect can still FAIL.
- **R8 [GPT-relay + EVIDENCE]** §5 matched baseline: validate the surviving pool size and the selection the ±30-session / no-nearby-signal matching induces BEFORE freeze; matching uses the causal as-of benchmark rule (§2.3 — 16:00 ET stamp; delay, never leak).
- **R9 [GPT-relay + Muse]** §9 contamination: possession/coverage is not use. The exposure audit must enumerate what was actually touched — dates, data, and rules (2022 studies, the old 4H cache, the nine ranking variants before rs_top2). Anything actually used in selection is exploratory-class forever. Holdout eligibility is Mike's governance ruling only (open fork).
- **R10 [GPT-relay]** Stage A pooling: no pooling of Tier 2/3 while Tier 2's status under R9 is unresolved; the pooling rule names the audit outcome as a precondition.
- **R11 [Muse]** H-SYS estimand: declare the censoring treatment for open positions (the -13 successor rule is the on-record precedent, §4.3); closed-trade means and equity-inclusive returns are different estimands and are never mixed in one endpoint.
- **R12 [GPT-relay]** §7C: one frozen trade list per comparison; per-trade mean R and portfolio return are reported side by side, never substituted; differing lists across legs are reconciled or the comparison is struck.
- **R13 [Muse]** Bootstrap: 20-**session** circular blocks per the frozen inference contract (10,000 SplitMix64 reps), or a published dependence diagnostic justifying shorter blocks.
- **R14 [Muse + EVIDENCE]** Two-universe honesty (§2.7): U1 standalone-candidate (590, available, suppression qualifier on every rate) vs U2 all-fire (specified-but-unpopulated until the regeneration GO).
- **R15 [Muse]** Horizon primacy: the 10-bar horizon was visible alongside DEV's ~17-bar average hold; either predeclare primacy on structural grounds independent of DEV outcomes, or Holm-control 5/10/20 and drop "primary."
- **R16 [EVIDENCE]** Measurement caveat mandatory (§2.1): every results template states the DEV 24.61% drawdown is an event-sampled lower bound; the all-bar figure is UNVERIFIABLE from the packet.
- **R17 [EVIDENCE]** Telemetry (§2.8): the full-state journal is prospective; retro-DEV fields are NOT_RECOVERABLE and are labeled so wherever the draft implies otherwise.
- **R18 [Muse]** Placeholder numbers: 0.10 ATR drift floor — derive from the matched-baseline drift distribution or strike (a drift floor is horizon-dependent). 0.10R paired EXIT floor — conditional keep only with a published pre-freeze paired-SD estimate showing it is at/above the 80%-power detectable effect at attainable pair counts. 0.05R — strike unless its endpoint is named in the full text. 25bps — keep as the stress leg under R6's declaration.
- **R19 [EVIDENCE — NEW]** Per-view ledgers (§3): commit the taken set for each cost view, or scope every parity claim to the 4bps C1 view; the committed ledger cannot reproduce the 25bps headline (185 vs 187 taken).
- **R20 [EVIDENCE]** Rank + exposure semantics (§§2.2, 2.6): state rank semantics as implemented and referenced (live per-candidate free; no snapshot rule); never equate the 5% heat cap with a leverage/exposure bound; notional reporting per the P6 spec.

## 6. P10 / P11 — data & version audit (from committed records)

### 6.1 P10 — data audit

- Packet integrity: all 14 packet files re-hashed for this review — **14/14 match MANIFEST.json** at pin 555ebb1.
- Ledger/results pins: trade_ledger.json sha256 267e794c…; results.json sha256 42b05ce3… — both match the -13 record.
- Config pin: experiment_config canonical sha256 87b8285a… — identical in the packet manifest and inside results.json.
- Capture provenance (results.json P1_chains): child root committed == recomputed (c5628652…), parent root committed == recomputed (ca498920…); 54 child chain receipts verified; 23 legs without receipts were quarantined at capture time (recorded, not silently admitted). P2 adjudication per-symbol gates (calendar admission, completeness, phantom exclusion, schema hygiene) recorded true for admitted legs.
- Calendar of record: session_table.json sha256 00c5555c… (the adopted 751-session table) is the P0 pin inside results.json.
- Known data limitations carried forward: names are CAPTURED_G1_G6_CANDIDATE_G4_UNADOPTED, never QUALIFIED; the Apr 4–22 2024 zero-volume window defect sits in the holdout window (sealed, untouched by this lane).

### 6.2 P11 — version audit

- Engine pins (results.json P0_pins) match the packet file hashes exactly: successor pine_backtest.py 874d2a9b…; pine_stack.py 8d4a964f…; asof_benchmark.py f0f4582c…; pine_ranking.py 77afae0d…; pine_signal_quality.py b1b39ee8…; pine_exposure.py 9f646161…; scanner_rules.py 62aa743a…; run_study13.py 4962e30d… (packet manifest).
- Provenance chain is recorded in full: engine_orig → -09 fork → -13 successor, each pinned in P0_pins; the -13 config states strategy source files are byte-identical to the -12 pins and deltas are confined to simulator accounting + the driver-level canonical order.
- Production state at run time is recorded in P0_pins: PAUSE_NEW_ENTRIES present, RESUME_NEW_ENTRIES absent — the DEV run executed under the pause, consistent with the standing state.
- The one version-hygiene defect on record is documentation, not code: the pine_backtest.py:18 docstring (§2.4, Block B proposal).

## 7. Bounds and forks

Bounds held: no performance runs or backtests; no strategy re-execution; no holdout access; no vendor calls; no tuning; no production or frozen-source edits (the two code-layer items are proposals, §1 Block B); the -22 pilot untouched; DEV labeled exploratory throughout; the 2026-10-03 forward FAIL stands as adverse evidence, unmodified.

Open forks for Mike (from the counter-position, unchanged): (1) holdout eligibility under the §9 exposure audit (R9); (2) the §11 PASS claim wording (R1); (3) confirmation-vehicle realism (R2). Precise GO requests outstanding: P4 docstring edit; P1 in-simulator implementation; P7 all-fire generation pass. Each is a separate, named decision — nothing in this memo executes them.

— Muse
