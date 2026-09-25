# ERD v0.1 — Earnings Reaction Drift (Design Draft, revised)

**Status: FROZEN PRE-REGISTRATION (Mike's approval, 2026-09-25). No code written. No backtest run. No production touch. V5.4 frozen and untouched. This document is not edited during validation; any deviation is logged as a deviation.**

Author: research design track, 2026-09-24/25
Revised per Mike's 2026-09-25 review: *"revise before freezing — the timing bug and imported laggard veto are the two things I would definitely not let through."*
Mandate: Mike, 2026-09-24 — *"The new system should not be 'V5.4 plus more filters.' Treat it as a fresh candidate and, when ready, run through the exact audit gauntlet that exposed V5.4's weaknesses."*

---

## 1. Mandate and non-goals

- **V5.4 = finish measuring.** Frozen; paper forward test to the ~50-signal (late Oct 2026) and ~100-signal (late Nov 2026) checkpoints, judged against ~0R.
- **Lane 2 = one risk-control test, now complete.** The laggard-veto study returned FAIL (2026-09-25): it does not qualify for a forward overlay. It is NOT imported into this design — a fresh architecture contains no V5.4 post-mortem parts.
- **New system = this document.** A fresh candidate architecture, designed from scratch, validated brutally later — or killed.
- This design must never become "V5.4 plus more filters." Section 5 proves the break explicitly.

---

## 2. Grounding: what the V5.4 post-mortem taught us

Every design choice below traces to a specific finding. Nothing here is stylistic.

| Post-mortem finding | Design consequence in ERD v0.1 |
|---|---|
| Honest baseline −0.0013R/trade; old +0.239R was mostly the hindsight-picked 14-name watchlist (+0.449R on those names alone). The edge was in the names, not the entries. | Universe is broad, mechanical, and reconstituted on pre-registered rules. No hand-picked list anywhere in the pipeline. No watchlist as a target set, ever. |
| Audit FAIL: universe integrity (survivorship/selection bias). | ERD defines its OWN quarterly point-in-time universe (§4.2): US common stocks, $5 price / $5M dollar-volume rules, dead/delisted included while listed. It does not inherit V5.4's 131 names (acceptable for a labeled pilot only, never as definitive validation). |
| Audit FAIL: trade independence. Effective sample ≈ 7 chained market episodes. | No signal-throwing "episode budget" (it discards correlated observations without making the rest independent). Dependence is handled honestly: earnings-week/season **block bootstrap** (§7.8), episode-level statistics alongside trade-level, leave-one-quarter/season-out kill gates. |
| Audit FAIL: execution realism (gap-through-stop filled at stop = optimistic). | Conservative-by-construction execution: entries at next-session open only; stops filled at the *worse* of stop price vs. open on gaps; delisted mid-hold exits use actual delisting returns or deliberately conservative treatment — never "last available price" assumed achievable. Written into the spec, not added later. |
| Audit FAIL: multiple-testing bias. | Fully pre-registered frozen parameters (§4.7). Perturbation ranges declared *now* as robustness checks, never as tuning dials. One dev window, one val window, no re-tuning. |
| Audit FAIL: profit concentration (best 10 trades = +58.5R of ≈ −0.5R total). | Concentration is a **kill criterion** (§8), not a footnote. |
| Costs: −0.131R drag at 50 bps round trip. | 50 bps baseline; must survive 25/50/75/100 bps sweep. |
| Slot/heat competition changes which trades get taken. | Exact portfolio replay with slot competition; rank rule pre-registered; take-all comparison required. |
| Laggard-veto risk-control test: FAIL (2026-09-25). | Excluded from this architecture entirely. A fresh system contains no V5.4 parts. |
| Clean PIT fundamental/analyst data unavailable (correctly skipped, not proxied). | Price/volume/dates only. "Surprise" is not claimed — see §4.1. |

---

## 3. Design principles

1. **Mechanism first, parameters last.** Every rule must have an economic reason written down before it has a number.
2. **PIT-clean by construction.** If a datum's point-in-time availability can't be established, the rule that needs it doesn't exist.
3. **Few moving parts.** Parameters fit in one table (§4.7). Anything that doesn't fit doesn't ship.
4. **Pessimistic execution is part of the spec**, not a sensitivity column.
5. **Pre-registered or it didn't happen.** Dev/val split, placebos, kill criteria — all frozen before any backtest.
6. **Designed to be killed.** Section 8 lists the exact conditions under which this system dies. A design without kill criteria is a marketing document.
7. **Test the bare event first.** v0.1 is the minimal system (§4). Modifiers (volume, gap cap, timing splits) are recorded for analysis and investigated only if the bare event survives. If the bare event fails, we kill it — we don't decorate it.

---

## 4. Primary architecture: ERD v0.1 (Earnings Reaction Drift)

### 4.1 Mechanism — and an honesty correction

This system does **not** trade classic PEAD. Without actual EPS expectations data, a +3% price move is an **earnings-announcement reaction**, not an accounting earnings surprise. The honest name is **Earnings Reaction Drift (ERD)**: buy the morning after a positive announcement-day price reaction and hold a fixed window, on the hypothesis that the market underreacts to the news and the reaction direction drifts further over the next one to three weeks.

Literature prior (tempered, per Mike's review):

- Classic PEAD is well established historically — Bernard & Thomas is the foundational evidence.
- Modern U.S. evidence is much less comforting: Martineau argues PEAD largely disappeared in modern markets, particularly in larger stocks; a 2025 *Journal of Financial Economics* study reports post-announcement trading behavior consistent with efficient price formation after 2016; a 2026 U.S. study finds the apparent 60-day drift is absorbed by expected-return components after factor adjustment.
- Continuation can still exist **conditionally** — e.g., recent NBER work links it to retail contrarian trading after large surprises.

So ERD is worth testing, but the literature does **not** guarantee an edge. The prior is neutral-to-skeptical, and the kill criteria (§8) are set accordingly. If the bare event system fails, we kill it.

Deliberate asymmetry: long-only (per standing evidence closing the short path), positive reactions only. The sign placebo (§7.6) trades negative-reaction names long with identical rules — it must come back ≤ 0R, or the mechanism is falsified.

### 4.2 Universe — ERD defines its own, PIT-clean

- **Base set:** U.S. common stocks, reconstituted **quarterly** on the first trading session of Jan/Apr/Jul/Oct, using only data available *as of that date*: close ≥ **$5**, 20-session median dollar volume ≥ **$5M**. Dead/delisted/acquired names included while listed, per the PIT dataset.
- **Not inherited:** V5.4's 131-name set (defined with information available as of **2023-09-30**) is acceptable for a *labeled pilot* only — it is not definitive validation of ERD.
- **Reporting overlay:** the old 14-name watchlist may appear *only* as a post-hoc reporting overlay, never in rule construction. (Expectation from the post-mortem: it will look better there. That proves nothing and changes nothing.)
- **Coverage gate:** if earnings date+time coverage is < 90% of name-quarters in the base set, that is a *finding*, not a license to expand the universe ad hoc. Expansion would require a new pre-registered rule, not a judgment call.

### 4.3 Entry — exact specification (the bare event)

**Event clock (BMO/AMC timing required — the v0.1 draft's timing bug is fixed here).**
Earnings calendar data must expose actual report date, report time, and BMO/DTM/AMC classification (Intrinio/Zacks-style; source documented per §4.8):

- **BMO** (before market open) → reaction session **S** = announcement day.
- **AMC** (after market close) → **S** = next trading day.
- **During-market** → **excluded from v0.1** (no reliable intraday timestamps; revisiting requires a pre-registered amendment, not a judgment call).

**Reaction return** (announcement reaction, not "surprise"): `(S close / prior close − 1)` minus SPY's same-session return. Require **≥ +3%**. The single correctly-timed session replaces the draft's two-session window, which could mix unrelated pre-announcement movement into the supposed reaction.

**Entry**: market-on-open of **S+1**. One position per name per earnings event; no re-entry on the same event.

**Explicitly NOT in v0.1** (recorded for analysis only, never gating):
- Volume confirmation (record S dollar volume vs 20-session median; investigate only if the bare event survives — higher attention does not obviously imply more drift, and some literature associates delayed reaction with *lower* attention).
- Gap cap (record event-return magnitude; the "+15% means repricing is complete" assumption is unproven — test only as a post-hoc modifier on a surviving system).
- Laggard veto (failed its own test; not a V5.4 part in a fresh architecture).
- Market gate, ADX, FVG, EMA structure, grades, or any V5.x component.

### 4.4 Exits and risk

- **Time stop**: exit at the **close of E+9**, where E = S+1 (10 sessions held). The drift window is the thesis; when it expires, the position expires. No extensions, no discretion.
- **Catastrophic stop**: **2.0× ATR(14)** (measured at S close) below the entry price. If a session's low touches the stop, fill at **min(open, stop)** — the pessimistic gap convention, written into the spec.
- **No profit target. No trailing stop. No early exit for any reason** except the catastrophic stop.
- **Corporate actions mid-hold**: standard split/dividend adjustment. If halted or delisted mid-hold: exit at the **actual delisting return** where available; otherwise apply a deliberately **conservative** treatment, documented per case. Never assume the last available price was achievable.

### 4.5 Portfolio construction (plumbing, not signal)

- Starting equity **$75,000** (house baseline, matches the V5.4 replay).
- **Risk per trade: 1% of equity**, sized on the catastrophic-stop distance. Position value capped at 25% of equity (single-name concentration guard).
- **Max 6 concurrent positions. Total heat ≈ 5%** of equity at risk (same house limits — comparability).
- **No episode budget.** Dependence is handled by the block bootstrap (§7.8) and episode-level reporting, not by discarding signals.
- **Slot competition**: if candidates exceed free slots on a session, rank by reaction magnitude (descending) and take the top; the rest are dropped, not queued. A **take-all comparison** (no slot cap) is a required validation output.
- Cash earns nothing. No leverage, no margin.

### 4.6 Sizing

Mechanical: `shares = floor(0.01 × equity / (entry − stop))`, subject to the 25%-of-equity position cap and the slot/heat limits above. No grade-based sizing, no discretion.

### 4.7 Frozen parameter table

| Parameter | Frozen value | Robustness range (declared now; check, never tune) |
|---|---|---|
| Reaction threshold (market-adj. single-session) | ≥ +3% | +2% / +4% |
| Entry timing | open of S+1 | fixed |
| Hold | 10 sessions, exit at close | 5 / 15 sessions |
| Catastrophic stop | 2.0× ATR(14) | 1.5× / 2.5× |
| Max positions / heat / risk | 6 / ~5% / 1% | fixed (house rules) |
| Slot rank | reaction magnitude desc | take-all comparison required |

**Analysis-only fields** (recorded per trade, never gating v0.1): S dollar volume vs 20-session median; event-return magnitude; BMO vs AMC split; earnings-season cohort. These exist so a *surviving* system can be investigated — not so a failing one can be rescued.

If the system needs any value outside these ranges to survive validation, it dies (§8.9).

### 4.8 Data requirements — PIT-available only

- **Daily OHLCV + universe: Norgate US Stocks Platinum or Diamond** (first choice) — explicitly includes listed and delisted U.S. stocks and is designed for survivorship-bias-free historical testing; U.S. listed/delisted coverage described as essentially complete from late 1992 onward. **Fallback: Intrinio EOD** — adjusted daily OHLCV, historical prices back to roughly 1996 for many securities, securities database includes delisted names. Split/dividend-adjusted, as-traded.
- **Earnings announcement calendar with report-time classification: Intrinio / Zacks EPS Surprises** — explicitly provides `actual_reported_date`, `actual_reported_time`, and BTO/DTM/AMC codes, exactly what the §4.3 event clock requires. **Integrity gate**: random sample of 50 dates verified against contemporary press releases/company IR, *including time-of-day*. Any systematic revision pattern → halt before results (§8.8).
- **Frozen no-substitution rule**: if Intrinio coverage is incomplete, or the ≥90% coverage gate or the integrity gate fails, ERD **halts** per this pre-registration. No substituting another earnings-calendar source mid-study. No patching the dataset afterward.
- **SPY daily** for market adjustment.
- **Explicitly not required and not used**: analyst estimates beyond the calendar's timing fields, fundamentals, intraday data, options flow, news sentiment, alternative data.

---

## 5. Why this is not "V5.4 plus more filters"

Mike's independent repo teardown confirms the break: the public scanner stacks market gate, ADX, relative volume, R/R, MTF confirmation, 15-minute confirmation, VWAP, and buy-zone geometry. ERD contains **none** of that. No FVG. No ADX. No EMA structure. No laggard veto. No volume filter. No gap cap. No market gate. No episode budget. No grades. No AI observer.

| Dimension | V5.4 | ERD v0.1 |
|---|---|---|
| Trigger | 4H structural chart pattern + ADX ≥ 20 gate | Scheduled corporate event + announcement-reaction |
| Entry timing | Signal bar / next-bar mechanics | Fixed: open of S+1, always |
| Exit philosophy | TP1 scale-out, Profit Protect arming, structural stop, 30-bar cap | 10-session time stop + catastrophic stop only; no targets |
| Universe philosophy | 250 frozen watchlist cohorts (hand-assembled) | Own quarterly PIT reconstitution; no hand-picked names |
| Selection | RS top-2 ranking (winner-picking) | Reaction-magnitude slot rank only |
| Grading/overlays | A/B/C grades, AI Observer, market gate | None |
| Timeframe/data | 4H bars | Daily bars + earnings calendar with BMO/AMC timing |
| Thesis | Entry geometry + momentum alignment | Post-announcement underreaction to a scheduled information event |

Shared house rules (1% risk, 6 positions, ~5% heat, long-only) are portfolio plumbing, not strategy DNA. Everything that makes V5.4 *V5.4* is absent.

---

## 6. Alternate directions (ranked)

**Alt 1 — Volatility-expansion breakout (runner-up).**
Pure price/volume: enter on close outside the 20-session range with ATR expansion, fixed 10-session hold, 2× ATR catastrophic stop, same risk plumbing and own PIT universe (no episode budget). *Why second:* no earnings-date dependency (simpler data, fewer leakage vectors), but the mechanism is weaker — breakout momentum overlaps V5.4's domain, and the selection study found 52-week-high proximity had no signal. Fallback if earnings date+time PIT integrity proves unobtainable.

**Alt 2 — Index-only regime trend system (ranked last).**
Trade QQQ alone: long when above its 200-day with a 10-day breakout trigger, fixed time-boxed holds, same risk plumbing. *Why last:* eliminates universe-integrity risk by construction and is the most honest about sample size — but a single instrument over three years is a tiny sample. Better kept as a benchmark than a candidate.

The primary was chosen because it has the strongest independent mechanism (scheduled information event + documented underreaction literature), the cleanest break from V5.4, and price-data-only inputs — while its main risk (earnings date+time PIT integrity) is fenced by an explicit pre-registered gate.

---

## 7. Pre-registered validation plan — the audit gauntlet

To be run only after this design is approved, as a separate pre-registered study. No tuning between dev and val. Any protocol deviation is documented and counts against the system.

### 7.1 Universe & data integrity
- ERD's own quarterly PIT universe per §4.2 (incl. dead/delisted while listed). A 131-name pilot run is acceptable *labeled as a pilot*, not as definitive validation.
- Earnings date+time spot-check: 50 random events vs contemporary press/IR, verifying time-of-day classification. Systematic revision → halt (§8.8).
- Coverage report: % of name-quarters with usable date+time; < 90% is a finding, not an expansion license.

### 7.2 Execution realism
- Entries: market-on-open of S+1, no intraday timing benefit.
- Stops: fill at min(open, stop) on gap-through. Written into the replay, not a sensitivity.
- Delisted mid-hold: actual delisting return or documented conservative treatment.
- No same-bar optimism anywhere; corporate-action handling documented.

### 7.3 Costs
- Baseline 50 bps round trip; full sweep at 25/50/75/100 bps. Must be positive at 50 and survive 100 (§8).

### 7.4 Portfolio replay
- $75k equity, 1% risk/trade, max 6 positions, ~5% heat, 25% single-name cap, pre-registered slot rank — exact replay, plus the required take-all comparison. No episode budget.

### 7.5 Splits and walk-forward
- Dev: Oct 2023–Dec 2024. Val: Jan 2025–Sep 2026 (same split as the V5.4 rebaseline, for comparability).
- Rolling walk-forward: 12-month estimation / 6-month evaluation, stepped quarterly (respects earnings seasonality).
- Year splits and earnings-season splits (Jan/Feb, Apr/May, Jul/Aug, Oct/Nov cohorts reported separately).
- Episode-level statistics alongside trade-level (trades are not independent; report both).

### 7.6 Placebos
1. **Random-date placebo**: identical filters on randomly chosen non-event sessions, same portfolio replay. Real result must clear the **95th percentile** of the placebo distribution (strengthened per Mike's review — 75th was too weak after V5.4).
2. **Sign placebo**: negative-reaction names traded long with identical rules — must come back ≤ 0R (mechanism check: the edge should live in the reaction sign).
3. **Shuffled-label placebo**: reaction magnitudes randomly reassigned across events; edge should vanish.

### 7.7 Concentration and robustness
- Top 5% of trades' share of total R (kill if > 60%).
- Leave-one-symbol-out, leave-one-quarter-out, leave-one-earnings-season-out.
- Declared perturbation ranges (§4.7): sign flip or > 50% expectancy decay across ranges = kill.
- Median trade, win rate, PF, max losing streak, maxDD reported — economic effects, not just statistics.

### 7.8 Bootstrap
- ≥ 5,000 trade resamples **and** earnings-week/season **block bootstrap** (resample earnings seasons, not just trades — the dependence-aware version). No episode budget needed because dependence is modeled, not discarded.

### 7.9 Reporting
- Failed checks reported as plainly as passed ones. Full trade list preserved. The frozen spec in this document is never edited during validation; any deviation is logged as a deviation.

---

## 8. Kill criteria — any one kills it

1. **Val-period expectancy ≤ 0R at 50 bps** → dead.
2. **Real result below the 95th percentile** of the random-date placebo distribution → dead (indistinguishable from noise; bar raised per Mike's review).
3. **Top 5% of trades contribute > 60% of total R** → dead (concentration — the V5.4 disease).
4. **Sign flip or > 50% expectancy decay** across any declared robustness range → dead (knife-edge).
5. **Negative walk-forward majority** → dead.
6. **Negative in 2 of 3 calendar years** → dead.
7. **Dev passes / val fails** → dead. No re-tuning, no second val window, no "adjusted" parameters.
8. **Earnings date+time PIT integrity fails** the spot-check gate, or coverage falls below 90% → halt before results; dead until clean data exists. **No mid-study source substitution**: if the locked Intrinio source fails the gate, the halt stands — the dataset is not patched afterward.
9. **Needs any parameter outside §4.7 ranges to survive** → dead (post-hoc tuning is disqualification, not iteration).
10. **Sign placebo (negative-reaction longs) comes back positive** → mechanism falsified → dead.

A kill is a kill. Killed systems don't get "one more tweak." Findings go in the log; the design track moves to Alt 1.

---

## 9. Open questions — all resolved at freeze (2026-09-25)

1. ~~Earnings date+time source~~ — **Locked: Intrinio / Zacks EPS Surprises** (`actual_reported_date`, `actual_reported_time`, BTO/DTM/AMC codes).
2. ~~Daily-bar history depth / vendor~~ — **Locked: Norgate US Stocks Platinum or Diamond** (first choice; listed+delisted, essentially complete from late 1992); **fallback: Intrinio EOD** (~1996+, includes delisted).
3. ~~Universe: 131-set vs own rule~~ — **Decided by Mike (2026-09-25):** ERD defines its own quarterly PIT universe ($5 price / $5M dollar-volume); the 131-set is pilot-only.
4. ~~Lab-only confirmation~~ — **Confirmed by Mike (2026-09-25):** zero production integration, zero V5.4 changes, no forward-test resources. ERD stays an isolated research candidate until it survives the full gauntlet.

---

## 10. Status and next step

- **Now:** FROZEN as the pre-registration (Mike's approval, 2026-09-25). No further edits except logged deviations during validation.
- **Next:** validation begins once the locked data sources (Intrinio/Zacks EPS Surprises, Norgate or Intrinio EOD) are actually available in the lab.
- **V5.4, Lane 2, and production are untouched by everything in this file.**
