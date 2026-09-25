# ERD v0.1 — Preregistration Amendment 1

**Status: DRAFT — completed per Mike's directive 2026-09-25. NOT frozen until Mike's explicit approval. No ERD performance data may be generated before re-freeze.**

**Authority.** This amendment responds to the blind pre-validation audit of ERD v0.1 performed by Claude (independent external auditor), verdict **NOT READY**, relayed via Mike on 2026-09-25. Mike concurred with the verdict and directed adoption of Claude's findings with the fifteen clarifications below, which are the operative specification. Per the disagreement protocol: Claude's original finding is preserved unchanged (filed separately); the study was not silently modified; this amendment is the recorded protocol change; no further testing occurs until it is frozen.

**Preservation.** The original frozen preregistration (`new_system/DESIGN.md`, frozen 2026-09-25) is unchanged. Claude's audit is filed separately and unchanged. Where this amendment conflicts with the original preregistration, the amendment governs. Nothing outside this amendment changes.

**Scope note.** ERD v0.1 has no development sample: every parameter below is fixed a priori, so the entire post-data-gate history is the validation sample. "PASS" always refers to validation evidence, never development data.

**Delegated choices.** Items marked **[DELEGATED — frozen on approval]** are choices Mike explicitly left to be fixed before running data. They are frozen when he approves this amendment.

---

## 1. EVENT CLOCK — REQUIRED

No arbitrary 4:00am cutoff. Event timing uses actual U.S. regular-session hours (NYSE calendar; early-close days honored at their actual close):

- Release **before that day's regular-session open** on trading day D → **S = D**.
- Release **during that day's regular session** [open, actual close] → **EXCLUDE**.
- Release **after that day's actual regular-session close** on trading day D → **S = next trading session**.
- Release on a **weekend or NYSE holiday** → **S = next NYSE trading session**.
- **Missing, ambiguous, or vendor-imputed timing → EXCLUDE.** Only explicit, validated timing information may qualify an event.
- If the vendor timing code (BTO/DTM/AMC) disagrees with the timestamp-derived bucket → **ambiguous → EXCLUDE**.
- A timestamp exactly at the regular-session close is treated as during-session → **EXCLUDE** (deterministic boundary; the interval [open, actual close] is closed).

*(Clarification 2026-09-25 per ChatGPT final review: fixed 09:30/16:00 ET wording replaced with that day's actual regular-session open/close so NYSE early-close days are handled correctly — e.g., a 13:30 ET release after a 13:00 ET close is AMC/next-session, not DTM/excluded. Specification clarification only; no performance data involved.)*

**Intrinio/Zacks fields (semantics to be verified at build):** `actual_reported_date`, `actual_reported_time` (both in ET), and the timing code (BTO = before open, DTM = during market, AMC = after close). The build must document the exact API endpoint, field names, and code semantics from Intrinio's documentation in the build log **before** the data gate; any deviation from the assumed semantics triggers a new preregistration amendment, not a silent fix.

**Unit test required:** synthetic events at 08:59, 09:30, 12:00, 15:59, 16:01 ET and on a Saturday must map to the buckets above exactly — **plus at least one early-close-day case** (e.g., 13:00 ET close: 08:59 → S=D; 12:59 → EXCLUDE; 13:00 → EXCLUDE; 13:01 → next session).

---

## 2. REACTION CALCULATION — REQUIRED

Signal normalization and trading P&L are strictly separated.

**SIGNAL (reaction):**
- Reaction = (adjusted close_S / adjusted close_prior − 1) − (SPY adjusted close_S / SPY adjusted close_prior − 1), where "adjusted" is the **PIT-safe total-return (split- and dividend-adjusted) series**, and adjustments may only reflect corporate actions with ex-date ≤ S. This neutralizes mechanical ex-dividend/split moves so they cannot masquerade as earnings reactions.
- "Prior close" = regular-session close of the trading session immediately before S.
- The +3% qualification threshold applies to this market-adjusted total-return reaction.

**TRADING P&L:**
- **Executable market prices only** for entry, stop, and exit. Synthetic adjusted prices are never fills.
- **Cash dividends:** credited only when the simulated position was actually entitled — ex-dividend date strictly after the entry date and on or before the exit date.
- **Splits:** share count and cost basis adjust to preserve economic position value exactly; no P&L is created or destroyed by the split event itself.

---

## 3. AMC PRIOR CLOSE — REQUIRED

For an AMC release on day D: **S = next trading session; reaction start price = D regular-session close.** This is directly encoded (not derived) and covered by a dedicated unit test asserting that no S−1 off-by-one is possible (synthetic AMC event on D must produce start = D close, S = D+1 session).

---

## 4. HALTS / NON-EXECUTABLE ENTRIES — REQUIRED

Deterministic handling, defined before testing. No assumed fill may occur while the security is halted or otherwise non-tradable.

- **Halt detection (daily-data implementation, documented at build before the run):** a session is non-executable for an order if there is no valid opening print (open null/zero) or an exchange halt flag is present on the vendor's daily record. Exact vendor fields recorded in the build log.
- **Entry:** if S+1 has no executable open, the event is logged as a **non-executable entry**. No chasing, no later entry, no assumed fill.
- **During hold:** sessions without executable data are carried; any triggered stop or scheduled exit executes at the **next executable open**.
- **Scheduled exit day (S+10) halted →** exit at the next executable open.
- Every affected event is logged individually. Events are never silently dropped.
- The research report separately shows: **(a)** qualifying events, **(b)** executable entries, **(c)** excluded/non-executable entries, with counts and the event list for (c).

---

## 5. ATR — REQUIRED DEFINITION

**[DELEGATED — frozen on approval]** ATR(14), Wilder's convention:

- Window: the 14 sessions ending at **S close, including S**. No E-day information enters ATR (E-day = announcement day only matters via §1–§3; ATR uses ≤ S).
- True range on the **adjusted (total-return) OHLC series**: TR_t = max(H_t − L_t, |H_t − C_{t−1}|, |L_t − C_{t−1}|).
- Wilder's smoothing (1/14), seeded with the mean of the first 14 TRs available in history, iterated forward through S. Only sessions ≤ S are used.
- **Adjustment convention:** adjusted series as in §2. The ATR is converted to executable points for stop placement via the S-close adjustment ratio: ATR_exec = ATR_adj × (executable close_S / adjusted close_S).
- The catastrophic stop = entry executable price − 2 × ATR_exec. Gap-through-stop fills are realistic: if the session low gaps below the stop, the fill is the executable open (worse than the stop), never the stop price.

---

## 6. DELISTINGS / ACQUISITIONS — REQUIRED

A position is never silently removed because data disappears. Every such event is flagged in the decision packet.

- **Cash acquisition** effective during the hold → exit at the **actual consideration per share** on the effective date. If consideration data is unavailable, exit at the last tradable primary-exchange close and flag as fallback.
- **Stock/mixed acquisition** → exit at the published consideration value at close if available, else last primary-exchange close; flagged.
- **Delisting to OTC / other venue (still trading)** → exit at the last primary-exchange close; flagged.
- **Bankruptcy / liquidation / wipeout with no realizable proceeds** → **conservative terminal treatment: −100% of position value**; flagged.
- Fallback treatments are reported as a separate count; results are also shown excluding fallback-treated events as a diagnostic.

---

## 7. SECURITY TYPES — REQUIRED

ERD is frozen as a **U.S. primary-listed common-operating-company** strategy. Excluded before testing:

- ADR/ADS, preferred stock, ETFs/ETNs, closed-end funds, warrants/units, shell/SPAC instruments, **REITs**.

Classification must be **PIT-correct**: the security-type/exchange record as of the event quarter from the securities master (exact vendor fields documented at build). Today's classification is never applied retroactively.

---

## 8. IPO / CORPORATE-ID RULES — REQUIRED

- A stock cannot enter the quarterly universe until it has the **full 20 completed sessions** required for the liquidity calculation: for quarter Q, the 20 trading sessions ending the day before Q starts must all be present with valid primary-listing data. Fewer than 20 → not in Q's universe.
- Ticker changes, mergers, and spinoffs map through a **permanent security identifier** (vendor security master ID), never ticker alone. Exact ID field documented at build.

---

## 9. PORTFOLIO RANKING — REQUIRED

- **Primary (frozen): reaction-magnitude ranking.** When eligible entries exceed available slots/heat on a session, admit in descending order of §2 reaction magnitude.
- **Full portfolio replay is mandatory** for the primary rule.
- **Diagnostic comparator replays** (same machinery, same costs, reported side-by-side): **first-eligible** (by event date/time order), **random-eligible** (seeded RNG; **[DELEGATED — frozen on approval]** seed = 20260925), **inverse reaction magnitude**.
- Diagnostics are diagnostics. They must not be used to select whichever performs best, and **no ranking rule may be changed after results.**

---

## 10. PORTFOLIO HEAT — REQUIRED DEFINITION

**[DELEGATED — frozen on approval]** The 5% heat limit uses **mark-to-stop current risk**, applied identically throughout the entire test:

- At each session close, for each open position: current risk = max(0, (close − stop) × shares).
- Heat = Σ current risk / current equity. A new entry is blocked if post-entry heat would exceed 5%.
- **Sizing (frozen, per original preregistration):** risk **1% of current equity per trade**; shares = floor(0.01 × equity_at_entry / (entry − stop_exec)); **position value capped at 25% of equity** (single-name concentration guard).
- **Starting equity: $75,000** (house baseline, per original preregistration).
- **Max 6 concurrent positions (frozen house rule, per original preregistration §4.5/§4.7).** Overflow governed by the §9 ranking. *(Correction 2026-09-25: the amendment as first drafted specified 10; the frozen DESIGN.md explicitly specifies 6 — reverted without reference to any performance data, none of which exists.)*

---

## 11. PLACEBO — REVISED

Claude's matching proposal is **revised**: do NOT match random pseudo-events on realized same-day gap or volatility (outcome-conditioning risk).

- Same PIT quarterly symbol universe as real ERD.
- Pseudo-event dates: random non-earnings dates per symbol, **≥10 trading sessions from any earnings announcement** of that symbol.
- **Match calendar regime where practical:** pseudo-dates stratified by calendar quarter to mirror the real event distribution.
- **Match only ex-ante information:** prior 20-session volatility and dollar-volume decile, measured strictly before the pseudo-event.
- Apply the **exact same +3% market-adjusted reaction test** (§2) and the **identical entry/exit/portfolio machinery** (§§4–10).
- **2,000 placebo replications**; test statistic = net expectancy (R/trade) at 50bps. **[DELEGATED — frozen on approval]**
- **Kill criterion K3:** real ERD expectancy must exceed the **95th percentile** of the placebo expectancy distribution.

---

## 12. QUANTITATIVE KILL CRITERIA — FROZEN BEFORE DATA

PASS refers to **validation evidence only**. There is no development sample. Any single K-criterion failure kills ERD v0.1 (a mechanism change becomes ERD v0.2 or another separately preregistered hypothesis — never a rescue of v0.1). Thresholds are never invented or modified after seeing results.

| ID | Criterion | Frozen threshold | Evidence |
|----|-----------|-----------------|----------|
| K1 | Net expectancy @ 50bps round-trip | **≥ +0.10 R/trade** (ChatGPT economic floor, adopted) | validation |
| K2 | Cost sensitivity | **> 0 R/trade @ 75bps** round-trip; full 25/50/75/100bps ladder reported | validation |
| K3 | Placebo | real expectancy > **95th percentile** of 2,000-replicate placebo distribution (§11) | validation |
| K4 | Trade concentration | expectancy **excluding the top 5 trades** ≥ +0.05 R/trade @ 50bps **[DELEGATED]** | validation |
| K5 | Symbol concentration | no single ticker > **30%** of total validation R **[DELEGATED]** | validation |
| K6 | Time concentration | no single quarter > **40%** of total R; no single year > **50%** of total R **[DELEGATED]** | validation |
| K7 | Cross-period stability | expectancy **> 0 in each chronological half** @ 50bps — halves defined by the immutable rule below | validation |
| K8 | Block bootstrap | 10,000 replicates, blocks = calendar quarters: **95% CI lower bound on mean R/trade > 0** @ 50bps **[DELEGATED]** | validation |
| K9 | Independent sample size | **≥ 300 executable trades spanning ≥ 24 distinct quarters** **[DELEGATED]** | validation |
| K10 | Reporting completeness | full economic results preserved (expectancy, PF, win rate, max DD, streaks, year/quarter splits); no result hidden | validation |

**Chronological halves rule (K7) — frozen, mechanical, no data-dependent choices.** Let W_start = the first day of the first calendar quarter in which the §15 earnings-calendar coverage gate (≥90%) is satisfied, and W_end = the last day of the most recent complete calendar quarter at build time. The boundary B = the calendar date of W_start + (W_end − W_start)/2 (day granularity; time-of-day discarded). First half = qualifying events with S < B; second half = events with S ≥ B. B is computed at build time from pre-performance facts (coverage-gate outcome and calendar only) and recorded in TEST_LEDGER.md **before** any performance computation begins. The rule is frozen here; B is never adjusted after observing event density or performance.

---

## 13. MULTIPLE TESTING — REQUIRED

- A permanent test ledger is maintained at `new_system/TEST_LEDGER.md`: every test/perturbation run is recorded with date, hypothesis, what varied, and verdict.
- Parameter perturbations count as **robustness checks only** when **all** hold: mechanism unchanged, universe unchanged, validation period unchanged, and the **full sensitivity surface is reported** (no cherry-picked cells).
- The best perturbation cell is never promoted into the strategy.
- Any mechanism change becomes **ERD v0.2** or another separately preregistered hypothesis.

---

## 14. DECISION PACKET

Adopted expanded schema (constructed from the fields enumerated in the freeze directive; reconciled against the filed Claude audit if any field is absent there). **One row per qualifying event**, sufficient for an independent implementation to reconstruct the full study:

`event_id, ticker, perm_security_id, announcement_date, announced_time_et, timing_code, timing_source, S_date, prior_close_date, reaction_start_price_adj, S_close_adj, spy_prior_adj, spy_S_adj, reaction_net, qualifies_YN, disqualify_reason, universe_quarter, security_type, eligible_YN, ineligibility_reason, entry_date, entry_price_exec, shares, risk_dollars_1R, atr14_exec_points, stop_price_exec, reaction_rank, slot_admitted_YN, heat_at_entry, exit_date, exit_price_exec, exit_reason, dividends_credited, costs_paid, realized_R, corporate_action_flags, halt_flags, delisting_treatment, notes`

---

## 15. DATA GATE

After this amendment is frozen, and **before any ERD performance number is calculated or revealed**:

1. Run the **50-event Intrinio/Zacks timing-integrity audit**: random sample of 50 qualifying events, stratified to include ≥10 BMO, ≥10 AMC, spanning ≥8 distinct calendar years. For each event, verify `actual_reported_date`, `actual_reported_time`, and the timing bucket against primary sources (company IR press release, Business Wire/PR Newswire/newswire timestamp). Record the source document per event in the audit log.
2. **Pass criteria:** ≥48/50 exact date+bucket matches; zero evidence of systematic revision patterns (e.g., vendor backfilling announced dates); coverage ≥90% (events with valid timing classification ÷ universe-member-quarters, averaged over the study window).
3. **If the gate fails:** stop, report the failure, ERD halts. No substitute earnings calendar without a new preregistration amendment.
4. The audit log (50 rows + sources + verdict) is committed to the repo **before** any performance work begins.

---

## Freeze attestation

- [ ] Mike's explicit approval (date): _______________
- [ ] SHA-256 of frozen `new_system/DESIGN.md` (original preregistration, unchanged): recorded below at freeze
- [ ] SHA-256 of this amendment at freeze: recorded below at freeze
- [ ] GitHub commit of both documents: _______________
- [ ] Confirmation: no ERD performance results were generated before re-freeze (verified 2026-09-25 — `new_system/` contains only `DESIGN.md`; no ERD engine, trade, or results files exist anywhere in the workspace)
- [x] Claude's blind pre-validation audit filed verbatim and unchanged as: `new_system/audits/erd-v0.1-prevalidation-audit-claude.md` (commit 5c7599b327514f5a2111c52406cb448119730ad9, verified resolving on main 2026-09-25)

**Status after freeze: NOT READY → READY FOR DATA** (integrity audit first, then performance work).

## Checksums (tamper-evident: SHA-256 of this document's content *above* this section, so the values below never invalidate themselves)

- `DESIGN.md` (original frozen preregistration — unchanged): `b5876e02056e0485150d05d67ee2c56f7c15152c76f63ba09118c19056d27059`
- This amendment, content above this section (as corrected 2026-09-25: max 6 positions restored, 25% single-name cap and $75k equity restored, K7 chronological-halves rule defined, §1 early-close-day clarification per ChatGPT final review, Claude audit filed): `15bf05ff70f3e8363fcb553f8ff7427bff7133abca6dd698bc8a918e1cb966ea`
- `TEST_LEDGER.md` (full file): `38f6191742fca71068c4211ce19f190e51ad92301c07a89801465005ce50b455`
- Verify: `awk '/^## Checksums/{exit} {print}' erd-v0.1-preregistration-amendment-1.md | sha256sum`
