# Research Idea Backlog — Lane 2 (hypothesis generation only)

**Status 2026-09-24 (Mike's directive): PARKED — all items below are parked until further notice.**
**Lane 2 is narrowed to ONE active test: the laggard-veto risk-control test**
(pre-registered at `selection_edge/laggard_veto_prereg.md`; run log to be filed under
`selection_edge/`). Nothing else in this backlog is authorized for testing.
**Rule:** No PASS/FAIL declarations, no production recommendations, no testing against the old distorted framework.
Each entry: hypothesis / mechanism / reason noticed / test sketch / pre-registered gates.
Per-study backlogs already logged (not duplicated here): 5 items in `pine_lonewolf_protocol/README.md`,
3 items in `pine_adx_protocol/README.md`.

---

## H1 — The isolated-entry penalty

**Hypothesis:** Entries that fire with no other signals open and no other signals on the same bar ("isolated") underperform entries accompanied by concurrent signals — and the relationship may be hump-shaped (some company good, extreme crowding bad).

**Mechanism:** A structural breakout that fires alone in a quiet tape is more likely an idiosyncratic single-name spike (news, squeeze) that mean-reverts. A breakout accompanied by simultaneous signals across names rides a broad risk bid — market participation confirms the move instead of leaving the trade to prove itself alone. At the extreme, very crowded bars may mark late-stage breadth thrusts (per the ADX backlog note), so both tails are pre-registered.

**Reason noticed:** Independence audit: heavy-overlap trades averaged **+0.83R**; isolated trades averaged **−0.95R**. Same-entry-bar pairs correlate (r=0.26). P11 found 6–10-signal crowded bars ran +0.379R. The edge lives in accompanied episodes.

**Test sketch (on corrected framework):** For each entry, count (a) other open positions at entry, (b) other eligible signals on the same bar. Pre-register buckets: 0 / 1–2 / 3–5 / 6+ accompanied. Compare expectancy per bucket. Perturb bucket edges ±1. Same population, dev/val split, all costs.

**Gates:** PASS if accompanied buckets beat isolated by ≥+0.10R pooled AND the ordering holds on validation AND survives costs/LOSO. MAYBE if directionally consistent but concentrated. FAIL if isolated ≥ accompanied, or the effect is one year.

---

## H2 — Shakeout-clip diagnostic (do the early forward stops mean anything?)

**Hypothesis:** A large share of Mode B resting-stop exits are intrabar touches on bars whose close stayed above the stop — liquidity-hunt shakeouts, not genuine breakdowns — and those trades drift up afterward.

**Mechanism:** The research baseline used close-evaluated exits (tolerant of intrabar dips); live Mode B uses a resting stop. The audit's conservative replay showed 91% of trades touched the stop intrabar on a bar that closed above it, and the resting stop clipped eventual winners (worst single-trade delta −9.7R, mean −0.14R). The forward test's first 4 closed trades all stopped out (−1.000R, worst MAE −1.865R) — this diagnostic tells us whether those were signal failure or execution tax.

**Reason noticed:** Execution audit §2 + forward scoreboard (4 early stopped-out trades).

**Test sketch (diagnostic only, not an exit change):** On the corrected framework, split every stopped trade into "close would have stopped too" vs "intrabar-touch-only." Compare 10-bar forward drift after exit for the two groups, plus MAE distribution. No rule change proposed.

**Gates:** Informative (not PASS/FAIL) if intrabar-only stops drift ≥+0.3R over 10 bars vs ≤0 for close-confirmed stops — that quantifies the shakeout tax live Mode B is paying. If no drift difference, the early forward stops were signal failure, not execution.

---

## H3 — The 30-bar timeout truncates the fat tail

**Hypothesis:** The 30-bar maximum hold binds almost exclusively on winners and leaves meaningful MFE uncaptured.

**Mechanism:** Time-based exits assume edge decays with holding time. But this system's P&L is 10 trades (99.9% of total) — sustained multi-week trends. A clock that fires while the trend is intact converts a fat-tail harvester into a capped one. The timeout is a calendar rule applied to a price phenomenon.

**Reason noticed:** Execution audit: 43/237 trades (18%) were held >30 bars; those trades total **+113.9R** in the baseline. The absent timeout binds on winners.

**Test sketch (diagnostic only):** On the corrected framework (which implements the timeout), for every timeout-exited trade record MFE-at-timeout vs realized exit R, and 10/20-bar drift after timeout. Report total R left on the table and what share of portfolio P&L it represents.

**Gates:** Informative. If timeout trades leave ≥15% of their MFE uncaptured in aggregate AND drift after timeout is positive, queue ONE pre-registered exit experiment at the checkpoint (per mandate P15 rules). Otherwise the timeout stays.

---

## H4 — Profit Protect opportunity cost

**Hypothesis:** Profit Protect (arms at +1R, exits at next-bar open) systematically taxes the handful of fat-tail trades that pay for the whole system.

**Mechanism:** PP encodes loss aversion as a rule: it locks ~+1R before a reversal in chop, but in rally episodes it converts unlimited upside into a forced exit at the next open. Since 10 trades carry ~100% of P&L, capping even one of them at +1R-ish instead of +6–9R is a first-order expectancy event. The research baseline never implemented PP at all, so its cost has never been measured.

**Reason noticed:** Execution audit §1 rows 6–7 (PP absent from all research); concentration audit (top-10 = 99.9% of P&L).

**Test sketch (diagnostic only):** On the corrected framework with faithful Mode B, decompose expectancy into PP-armed-exited vs never-armed trades. For armed trades, record MFE-after-arm vs realized exit. Report PP's expectancy contribution split by regime/episode.

**Gates:** Informative. If armed trades' MFE-after-arm exceeds realized by ≥+0.5R/trade in rally episodes, PP is a rally-episode tax worth one pre-registered experiment at the checkpoint. If PP saves more in chop than it costs in rallies, it stays untouched.

---

## H5 — Episode density as a forward-health metric (not a filter)

**Hypothesis:** Signals-per-month (episode density) predicts subsequent expectancy regime — a quiet tape means chop-carry losses, a dense tape means rally-episode harvesting. Useful as a live dashboard metric, NOT as an entry filter.

**Mechanism:** The edge appears almost exclusively in crowded bull episodes (heavy-overlap +0.83R vs isolated −0.95R; best 3 months = 83.7% of P&L; 2026 with no rally months ran −0.242R). In chop the system pays false-breakout carry; in rallies it harvests. P4 already killed regime *filters*, so this is deliberately not a filter — it's how Mike reads whether the forward test is in a harvestable tape.

**Reason noticed:** 2026 ran −0.242R (n=60); concentration audit ("a year without rally months is a losing year").

**Test sketch:** On the corrected framework, regress monthly expectancy on trailing signals-per-month and concurrent-signal rate. Pre-register the metric definition before looking. Then publish it on the forward scoreboard as context (e.g. "tape density: low — expect chop-carry").

**Gates:** Useful if the correlation is directionally stable across years (no optimization of the density threshold). Not a PASS/FAIL edge — a monitoring instrument.

---

## H6 — Heat-skip paper tracking (is the heat cap protective or just return-reducing?)

**Hypothesis:** The 5% heat cap's skipped trades are knowable and measurable — and skipping them has cost more than it saved.

**Mechanism:** The heat cap is a risk control, not a return enhancer. The portfolio replay showed 54 heat-skipped trades averaging **+0.108R** (mildly positive); skipping them cost 5.85R of total capture. But that was one history — the forward test can measure it live with zero backtest risk.

**Reason noticed:** Portfolio audit §2 (skip decomposition); production uses 6 slots + 5% heat (≈5 effective slots).

**Test sketch (live diagnostic, no backtest):** Log every heat-skipped signal on the forward test with entry/stop/TP1 and paper-track it to the standard exit. Monthly: report skipped-vs-taken expectancy. Pre-register now; the data accumulates on its own.

**Gates:** Informative. If skipped trades run ≥+0.15R over 30+ skips, the heat cap is a material return drag worth re-examining at the verdict (e.g. heat measured on open risk vs planned risk). If skipped ≤ 0, the cap earns its keep.

---

## H7 — Tie-break dispersion (uncontrolled degree of freedom)

**Hypothesis:** When multiple signals tie on the same bar, the backtest's implicit ordering (watchlist loop order — an undocumented code artifact) moves results enough to matter, which would prove the framework has an uncontrolled degree of freedom.

**Mechanism:** There is no economic reason QQQ should be evaluated before BBAI on a tied bar. If perturbing the tie-break changes expectancy materially, then every crowded-bar result (including ADX's) is partly an artifact of loop order, and the framework needs a deterministic, pre-registered tie-break before any ranking study is trusted.

**Reason noticed:** Portfolio audit §1: ties fall back to WATCHLIST loop order; ranking sims amended their spec just to reproduce it.

**Test sketch (framework hygiene):** On the corrected framework, rerun with tie-breaks: alphabetical / reverse-watchlist / random-seeded ×5 / signal-strength-desc. Report expectancy dispersion across orderings.

**Gates:** If dispersion ≥0.03R, FAIL the framework on this point — mandate a deterministic tie-break (pre-registered, e.g. signal-strength-desc then alphabetical) and re-run affected studies. If <0.01R, note and move on.

---

## H8 — The thin-name cost mirage

**Hypothesis:** After realistic per-symbol spreads, the thin names' apparent contribution shrinks disproportionately — flat 25bps subsidizes illiquid names and distorts where the edge appears to live.

**Mechanism:** Effective spread is a per-trade tax scaling with illiquidity. The cost audit's Corwin-Schultz upper bounds: ONDS 73bps, ASTX 77bps, BBAI 46bps, RKLB 38bps vs QQQ 7.5bps per one-way leg — while studies deduct 25bps once per trade (~12.5bps/leg). ONDS/ASTX/BBAI trades may start ~0.2R in the hole before the signal is even evaluated.

**Reason noticed:** Execution audit §3b (per-symbol spread table; "thin names likely cost 2–6× the flat assumption").

**Test sketch:** On the corrected framework, apply per-symbol spread costs (pre-registered estimator, e.g. Corwin-Schultz, reported as a range given its upward bias) and re-rank expectancy by symbol/liquidity tier. No filter proposed — this is measurement.

**Gates:** Informative. If ≥2 thin names flip negative after realistic spreads, the honest baseline must carry per-symbol costs and any future universe construction must include a liquidity screen as a *cost* input, not an edge.

---

## H9 — ADX selection edge vs contest size

**Hypothesis:** ADX's ranking edge grows with the number of candidates on the bar — ranking a 7-horse field is skill, ranking a 3-horse field is mostly noise.

**Mechanism:** Selection edge is a function of choice-set size. With 2–3 candidates, even perfect ranking adds little over random; with 6+ candidates, skipping the worst 4 is where the R comes from. The ADX MAYBE rests on 21 contests of mixed sizes — pooling them may hide that the edge is real-but-narrow (large contests only).

**Reason noticed:** ADX protocol: 21 genuine crowded bars, selection edge +0.651R pooled; concentration (2025 = 112.7% of differential).

**Test sketch (on corrected framework):** Bucket crowded bars by candidate count (pre-registered: 3 / 4–5 / 6+). Report SELECTION EDGE per bucket with bootstrap. Same population, no re-tuning of ADX.

**Gates:** PASS if 6+ bucket edge ≥+0.4R with bootstrap ≥90% > 0 AND smaller buckets ≥0 (no reversal). MAYBE if only the large bucket works (narrows the claim honestly). FAIL if edge is flat or inverts with contest size.

---

## H10 — Episode-clustered risk budgeting

**Hypothesis:** Sizing 1% risk per trade overstates diversification — 5 simultaneous entries in one market episode are ~5% risk on a single market call, and capping risk per episode-cluster beats per-trade sizing on risk-adjusted return.

**Mechanism:** Effective n ≈ 83, not 237; trades sharing >75% of holding correlate at r=0.74. The 1%-per-trade rule was written for independent bets, but the portfolio is ~18–21 episodes. Risk should be budgeted where the independence actually lives.

**Reason noticed:** Independence audit (overlap correlations, 18–21 time episodes, SEs understated 1.7×).

**Test sketch (on corrected framework):** Cluster entries into episodes (pre-registered: overlap-graph components). Compare baseline sizing vs episode-capped sizing (e.g. total open risk per episode-cluster ≤2%, pre-registered). Report expectancy, max DD, return/DD. One pre-registered variant only — no search.

**Gates:** PASS if return/maxDD improves ≥15% with expectancy within ±0.03R of baseline (risk efficiency, not return chasing). MAYBE if DD improves but expectancy slips. FAIL if it costs expectancy without proportional DD relief. (Fits Mike's approved position-sizing research lane.)

---

## H11 — Sector-RS slope: rotation timing vs participation level

**Hypothesis:** Entries where the *sector's* 20-bar RS slope is turning up (positive inflection) outperform entries where sector RS is flat/negative — distinct from lone-wolf, which is about the *level* of sector participation.

**Mechanism:** Lone-wolf asks "is the sector participating?" (level ≤ 0 → block). This asks "is institutional rotation *arriving*?" — a stock breaking out just as its sector's relative strength inflects upward catches the rotation wave; a stock breaking out into flat sector RS is picking a local top with no bid behind it. Level and slope are different market phenomena (participation vs rotation timing).

**Reason noticed:** The 10 trades carrying 99.9% of P&L all occurred in rally episodes where sectors were turning up; retained lone-wolf winners ran further (MFE 3.07R vs 2.37R) — what distinguishes a winner that runs from one that doesn't may be the sector bid arriving underneath it.

**Test sketch (on corrected framework, full 12-step protocol as its own hypothesis):** Pre-register: sector 20-bar RS slope (linear fit) > 0 vs ≤ 0 at entry, strict PIT. Compare expectancy of the two groups on the same signal population. Perturb 15/20/25. Dev/val, costs, LOSO, bootstrap, concentration.

**Gates:** Standard protocol gates. PASS only if positive across validation, costs, nearby slopes, and symbol removal. Explicitly NOT a lone-wolf variant — if it fails, it fails on its own.

---

*Logged 2026-09-24 (Lane 2). No backtesting performed. No verdicts declared. All await the corrected baseline.*

## H12 — Prior-week volume-profile auction structure on 4H signals (Mike's spec, 2026-09-24)

**Hypothesis:** 4H long signals behave differently depending on where entry occurs relative to the PRIOR WEEK's volume profile.

**Mechanism:** High-volume areas represent prior price acceptance and may slow price movement. Low-volume areas represent thin participation and may allow faster traversal. The question is whether this provides useful information for entries, targets, or trade ranking. Use ONLY prior-week information available before the current week begins.

**Reason noticed:** IG reel from @pipsbeyondborders on Volume Profile setup (prior-day profile → current session, forex/intraday framing). Reframed by Mike to prior-WEEK structure on 4H to match the Quality Flow system.

**Test sketch (on corrected framework — canonical PIT Mode B baseline, once available):**
For every V5.4 long signal, calculate from the completed prior week: POC, VAH, VAL, nearest high-volume node, nearest low-volume node, and distance from entry to each level in ATR units. Classify each signal BEFORE looking at results:
1. Entry below VAL
2. Entry between VAL and POC
3. Entry near POC
4. Entry between POC and VAH
5. Entry above VAH
6. Entry immediately below a high-volume node
7. Entry immediately below a low-volume area

Primary questions:
A. Do signals entering directly into a prior-week high-volume zone have lower expectancy?
B. Do signals entering into/through a low-volume zone reach TP1 faster or produce higher MFE?
C. Does prior-week POC act as resistance for long entries approaching from below?
D. Does being above prior-week VAH identify stronger continuation setups?

Do NOT create a filter initially. First report descriptive results: trade count, expectancy, PF, win rate, MFE, MAE, time to TP1, max DD contribution. Use predeclared ATR-normalized proximity buckets (within 0.25 / 0.25–0.50 / 0.50–1.00 / >1.00 ATR) — no searching dozens of thresholds. Compare against shuffled/profile-placebo levels to test whether real volume-profile levels carry more information than arbitrary horizontal levels.

**Gates:** PASS / MAYBE / FAIL per the 12-step protocol. The initial goal is NOT to add Volume Profile to V5.4 — it is to determine whether prior-week auction structure contains incremental information beyond the current Quality Flow signal (e.g. maybe POC is useless but low-volume zones predict faster MFE, or above-VAH is the real continuation edge). Discover what matters before inventing a rule.

---

*Logged 2026-09-24 (Lane 2). No backtesting performed. No verdicts declared. All await the corrected baseline.*
