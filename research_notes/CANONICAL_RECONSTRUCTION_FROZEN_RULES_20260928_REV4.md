# Canonical Reconstruction — FROZEN RULES rev 4 (DRAFT)

**Date:** 2026-09-28
**Status:** DRAFT rev 4 — addresses the Claude-audit reconciliation + rev-4 mandate
(issue #1, comment `5876792377`, 2026-09-28T19:16:58Z). **Patched 2026-09-28
per Mike's four redlines (issue #1); still DRAFT, no sign-off yet.**
Pending: ChatGPT re-audit → Claude re-audit → Mike final sign-off.
**NO BUILD AUTHORIZED YET.**
**Owner:** Mike
**Supersedes:** rev 3 (`CANONICAL_RECONSTRUCTION_FROZEN_RULES_20260928.md`,
commit `60776c3`), which **failed the Claude independent audit** and returned
to DRAFT. Rev 2/3 history retained for the record; neither is operative.

## §0. What this exercise is (reframed per Claude audit)

This is an **unblinded replication** producing a **reconstructed canonical
replica** — not a "sealed-oracle" reconstruction. The Claude audit's
stop-level finding is accepted: the mandatory source documents
(`PORTFOLIO.md`, `REBASELINE.md`, and prior revs' §3) already disclose the
historical path and results, so no claim of investigator blinding is made or
implied. The word "sealed" no longer appears as a blinding claim anywhere in
this spec.

What replaces blinding is **process control** (§9):
no historical outcome may choose among frozen resolutions; comparators are
examined only after code hash-lock and Run 1; any mismatch is a finding, never
tuning permission; reruns follow the §10 protocol. The comparator file's
SHA-256 (§15) is an **integrity commitment** to that file's bytes, not a
blinding device.

Original-machine recovery remains **cancelled** per Mike's directive
2026-09-28. Whatever the rebuild produces is labeled **reconstructed
canonical replica**, never "recovered original."

---

## §1. Frozen source anchor + provenance controls

- Specification set (only these six docs are canonical spec):
  `canonical_baseline/ENGINE.md`, `LONEWOLF_RERUN.md`, `PIT_FEATURES.md`,
  `PORTFOLIO.md`, `REBASELINE.md`, `UNIVERSE.md`.
- Repository tree anchor for candidate-pool sources: commit
  `de01ff70a13e680c5468ae5e6e81177c981832e0` (parent of first canonical-doc
  commit `e77bb16`). Do NOT source symbols from current main.
- **Untracked-file quarantine (process control).** Local untracked files under
  `canonical_baseline/` (`simlib.py`, `modeb_engine.py`, `run_portfolio.py`,
  `canonical_trades.json`, `portfolio_results.json`, data pickles, etc.) are
  **not** canonical spec and must **not** be opened, read, or consulted for
  any implementation choice. Their provenance is unverified; consulting them
  would be outcome-targeting through another channel and would also violate
  Mike's "never present a reconstruction as the record" directive. The six
  docs plus this frozen spec are the only implementation sources.
- **Live-code provenance for the transcribed signal logic (§2).** The six
  docs cite the live V5.4 implementation with file:line references. Tracked
  live files (`scanner_rules.py`, `masterscanner_api.py`) are pinned to the
  verifiable support commit `48579180d21fda07339fa9305d30828bffef0bc3`
  (latest commit touching both files; the `dac44624` citation in the first
  rev-4 draft was invalid and is withdrawn). `v54_engine.py` /
  `v54_rules.py` are **not** committed in the repo, so no commit ref exists
  for them; the version pin is `V54_RULE_VERSION = "2026-09-15-v54"`.
  **The transcription in §2 is the authoritative freeze.** Transcribed logic
  sourced from the uncommitted wrapper/grader files is labeled
  **JUDGMENT / reconstructed transcription — not recovered fact**
  (per-subsection basis notes in §2). Nothing in this work modifies any live
  file; V5.4 production stays frozen.

---

## §2. Signal generator — FROZEN (B1)

The canonical baseline's signals are the frozen V5.4 classifier
(`v54_engine.v54_classify`, rule version `2026-09-15-v54`), all grades A/B/C,
strict PIT, no scores in any decision path (PORTFOLIO.md). The complete logic
is transcribed here so the rebuild does not depend on any uncommitted file.

### §2.1 Historical adapter + decision/cycle-time semantics

- **Decision points.** For each universe symbol, every **completed** 4H bar
  close inside the symbol's eligible window is a signal-evaluation point
  (the backtest analog of live hourly cycles, which score the last completed
  bar each cycle — PIT_FEATURES.md).
- **Evaluation at decision point T (bar `i` close).** Run the full pipeline
  below on 4H bars `[0..i]` only, plus daily/weekly/15m context as of T per
  §4 and §2.8. A signal is **complete at signal-bar close**; its stamped
  timestamp is the bar-close wall time: **13:30 / 16:00 ET**, or **13:00 ET**
  on NYSE early-close days (A5). The fill price (next completed bar's open)
  is unknowable at signal time.
- **Forming-bar exclusion.** No 4H bar with `bar_close_at > T` may be read by
  any feature, indicator, or exit rule (`scanner_rules.py:86-88`).
- **Fill.** Paper entry fills at the **next completed 4H bar's open** after
  the signal bar; skipped if `entry ≤ stop` at fill time (gap-through-stop
  invalidation — PIT_FEATURES.md, ENGINE.md assumption 2). Pending-entry
  fills re-check `entry > stop` at fill; invalidated pendings release slot +
  heat (A2/A6).
- **Signal price on the record** = signal-bar close.

### §2.2 Indicator math (all causal, closed bars only)

On 4H OHLCV (`masterscanner_api.add_indicators`):
- `EMA(l) = Close.ewm(span=l, adjust=False).mean()`; l ∈ {9, 21, 55, 200}.
- `ATR(14)`: true range = max(High−Low, |High−Close₁|, |Low−Close₁|);
  Wilder smoothing `ewm(alpha=1/14, adjust=False)`.
- `ADX(14)`: Wilder +DM/−DM smoothed `ewm(alpha=1/14, adjust=False)`,
  DX = 100·|+DI−(−DI)| / (|+DI| + |−DI|) (0/0 → NaN), then
  `ADX = DX.ewm(alpha=1/14, adjust=False)`.
- `VOL_BASE` = Volume.rolling(50).mean().
- `VWAP` = session VWAP when present, else 50-bar rolling
  `(typical×vol).sum()/vol.sum()`, typical = (High+Low+Close)/3.
- `rvol = Volume / VOL_BASE` (0 if VOL_BASE ≤ 0).
- Triggers read index `i` (and `i−1` for crosses) only — never `i+1`.
- Constants: `FAST_EMA=21, SLOW_EMA=55, TREND_EMA=200, ACCEL_EMA=9`;
  `ADX_LEN=14, ATR_LEN=14, ATR_BASE_LEN=50, VOL_BASE_LEN=50, VWAP_LEN=50`;
  `ADX_MIN=18` (trigger-level), `HOT_ADX=30`,
  `PULLBACK_NEAR_EMA_PCT=2.5`, `HOT_EXTENSION_PCT=6.0`,
  `BUY_ZONE_ATR_WIDTH=0.45`, `STOP_ZONE_ATR_BUFFER=0.65`,
  `TP_ZONE_ATR_EXTENSION=2.50`, `MIN_ADX=20.0` (V5.4 hard gate).
  Basis: DERIVABLE (transcribed from the tracked
  `masterscanner_api.add_indicators` and helpers at commit 48579180, the
  files the six docs cite).

### §2.3 Structural contract — pure setup triggers

With `price=Close[i]`, `e9/e21/e55/e200` as above, `adx=ADX[i]`:
- `trend_bull = price > e200`
- `ema_bull = e21 > e55`
- `fresh_buy = (e21[i] > e55[i]) and (e21[i-1] ≤ e55[i-1]) and trend_bull`
  (EMA21/55 bull cross)
- `early_buy = trend_bull and (e9>e21) and e21 rising and e9 rising and
  price > e21 and e21 ≤ e55×1.015` (state only — never entry-eligible)
- `pullback_buy = trend_bull and ema_bull and price ≥ e21 and
  |safe_pct(price,e21)| ≤ 2.5 and adx ≥ 18`,
  where `safe_pct(a,b) = 0 if b==0/NaN else (a−b)/b×100`
- `exit_signal = (price < e55) or (e21[i] < e55[i] and e21[i-1] ≥ e55[i-1])`
  (price under EMA55, or EMA21/55 bear cross)
- State: `EXIT` if exit_signal; `BUY` if fresh_buy; `PULLBACK BUY` if
  pullback_buy; `EARLY BUY` if early_buy; else `NEUTRAL`.
- Protection: `EXIT` if exit_signal; `LOCK GAINS` if hot/extended
  (`hot = trend_bull and ema_bull and adx ≥ 30 and extension ≥ 6.0`,
  `extension = safe_pct(price, e21)`); `SAFE` iff
  `trend_bull and ema_bull and price ≥ e21 and above_vwap`;
  `WARNING` iff `trend_bull and price < e21 and price > e55`; else `WARNING`.
- **Entry `YES` iff** `state ∈ {BUY, PULLBACK BUY}` **and**
  `protection == "SAFE"` **and** `above_vwap` **and** `in_zone`,
  where `in_zone = (zone_low ≤ price ≤ zone_high)`,
  `zone_low = max(0, e21 − ATR×0.45)`, `zone_high = e21 + ATR×0.45`.
  Basis: JUDGMENT — reconstructed transcription of the uncommitted
  `v54_engine.v54_classify` / `_pure_setup_triggers` (not recovered fact;
  no commit ref exists). Cross-checked against the six docs, which name
  this function as the signal source (PORTFOLIO.md) and describe its
  behavior; no score appears in any condition — see §10/B9.

### §2.4 Hard gates (eligibility)

`v54_hard_gates_pass`: the §2.3 structural contract
(`entry=="YES"`, `protection=="SAFE"`, `state ∈ {BUY, PULLBACK BUY}`,
`above_vwap is True`, price inside buy zone —
`scanner_rules.is_structural_candidate`) **plus** `ADX ≥ 20.0` evaluated at
signal bar `i`, never revised. Rows failing the gates are recorded as
ineligible (grade None) — they are not signals. Basis: JUDGMENT —
reconstructed transcription of the uncommitted `v54_rules.v54_hard_gates_pass`
(not recovered fact); the structural contract it wraps is in the tracked
`scanner_rules.is_structural_candidate` (commit 48579180), and the ADX ≥ 20
gate plus ineligible→None recording are in the frozen handoff spec
(2026-09-15).

### §2.5 Stop / TP1 levels

`stop, tp1 = trade_levels(zone_low, zone_high, ATR)`:
- `stop = max(0.0, zone_low − ATR × 0.65)`
- `tp1 = zone_high + ATR × 2.50`
Computed from **signal-bar** values only, never revised (PIT_FEATURES
rule 5). Basis: EXPLICIT (`scanner_rules.trade_levels`).

### §2.6 Grading inputs (actually used) + grade map

Grading consumes only these context fields — never raw dataframes
(`v54_rules.v54_grade`):
- `daily_trend`, `weekly_trend` ∈ {confirmed, not_confirmed, unknown}
  (§2.8).
- `market_gate` ∈ {BLOCK, CAUTION, CONFIRM, UNKNOWN} (§2.7).
- **Not grading inputs:** 15m confirmation and premarket — observational
  only, recorded on the signal record, never gating or grading (frozen
  spec; `v54_rules.py` docstring). No auxiliary input vetoes a signal:
  MTF/daily/weekly/15m/premarket/market-gate are grading context only.
  The only gates are §2.4.
- Grade map: hard gates fail → ineligible (None). Else
  `fully_confirmed = (daily==confirmed and weekly==confirmed) or
  gate==CONFIRM` → **B** (CONFIRMED). Else `context_known =
  daily≠unknown and weekly≠unknown and gate≠UNKNOWN` false → **C**
  (OBSERVATION). Else → **A** (EARLY). The handoff's "weaker" (as distinct
  from "unknown") has no deterministic definition and currently grades A —
  flagged, not invented (standing memory 2026-09-15).
  Basis: JUDGMENT — reconstructed transcription of the uncommitted
  `v54_rules.v54_grade` (not recovered fact); the A/B/C map, the grading-only
  role of MTF/market-gate context, and the observational-only status of
  15m/premarket are in the frozen handoff spec.

### §2.7 Market gate computation (grading context)

On QQQ closed 4H bars at decision time T (timestamped, never backfilled —
PIT_FEATURES rule 7; morning-cycle staleness is correct behavior):
- `score = 35×(Close>EMA200) + 35×(EMA21>EMA55) + 15×(EMA21 rising) +
  15×(Close>EMA21)` (max 100).
- `_session_return = safe_pct(last closed bar Close, prior date's last
  closed bar Close)` for QQQ and SPY.
- `gate = BLOCK` if `qqq_ret ≤ −0.75` or
  (`qqq_ret ≤ −0.40` and `spy_ret ≤ −0.40`); `CAUTION` if `qqq_ret < 0` or
  `spy_ret < 0` or `score < 75`; else `CONFIRM`.
- `regime = RISK-ON (score≥75) / CAUTIOUS (≥50) / RISK-OFF`.
- If QQQ history < 205 bars: `regime UNKNOWN, gate BLOCK`.
  (In the 2023-10→2026-09 window QQQ has full history; this is a corner
  rule.) Basis: DERIVABLE (`masterscanner_api.get_market_regime`).

### §2.8 MTF trend states (grading context)

`confirmed | not_confirmed | unknown` per timeframe (`v54_engine._v54_trend_state`):
- Drop the unfinished bar first (`closed_higher_timeframe`): today's daily
  bar before 16:00 ET; the unfinished weekly bar (week ends Friday 16:00 ET).
- `df` None/empty or < 205 completed bars → `unknown`.
- Else `confirmed` iff `Close > EMA200 and EMA21 > EMA55 and EMA21 rising`
  (EMAs = `ewm(span, adjust=False)` on timeframe closes); else
  `not_confirmed`.
- `unknown` can never yield A or B: with hard gates passed it yields **C**
  (§2.6). Missing auxiliary input is **never gating** — it is grading
  context only (B6 resolved).
  Basis: mixed. `closed_higher_timeframe`, `timeframe_trend_confirmed`, and
  the 205-bar rule: EXPLICIT (tracked `scanner_rules.py:217-260`, commit
  48579180). The confirmed/not_confirmed/unknown labeling wrapper:
  JUDGMENT — reconstructed transcription of the uncommitted
  `v54_engine._v54_trend_state` (not recovered fact).

---

## §3. Warmup / first signal-eligible bar — FROZEN (B2)

- **Indicator seeding horizon.** Indicators are computed causally from each
  symbol's series start (series begins at `effective_4h_from`,
  UNIVERSE.md). `ewm(adjust=False)` needs no explicit seed bars; the
  `min_bars` gate below provides stability. Warmup bars are for indicator
  seeding only, never for signal evaluation (PIT_FEATURES rule 6).
- **Per-symbol minimum.** `v54_classify` returns None unless the 4H frame
  holds `min_bars = max(TREND_EMA, ATR_BASE_LEN, VOL_BASE_LEN, VWAP_LEN) + 5
  = 205` bars. The first signal-eligible bar index is therefore the 205th
  4H bar of the symbol's own series (0-indexed 204).
- **First eligible bar (operational).** For each symbol, the first bar at
  which a signal may be evaluated is the earliest 4H bar satisfying ALL of:
  (a) ≥205 bars of that symbol's 4H history exist through it;
  (b) its timestamp ≥ universe `eligible_from` (UNIVERSE.md);
  (c) its timestamp ≥ `effective_4h_from` (coverage_report.json).
- **ARM / new-listing ambiguity — RESOLVED.** The 30-trading-day
  (≈60 4H bars) post-listing rule governs *universe eligibility*
  (UNIVERSE.md step 5); the 205-bar rule governs *signal eligibility*.
  Both apply; the later binds. For ARM (4H series starts 2023-10-26 per the
  Yahoo 1H cap): the binding constraint is the 205-bar warmup, so ARM's
  first signal-eligible bar is its 205th 4H bar (≈ late March 2024), not
  30 trading days after its 2023-09-14 IPO. Same logic for all 11 admitted
  new listings (BMNR, CRWV, DRAM, GEV, GLXY, NBIS, RDDT, SNDK, SPCX, TEM).
  Basis: DERIVABLE (`v54_classify` min_bars + UNIVERSE.md eligibility).

---

## §4. Daily-bar availability — FROZEN (B3)

- A daily bar dated D becomes **available** at the actual regular-session
  close: **16:00 ET** (or **13:00 ET** on NYSE early-close days). Midnight
  date labels are never availability timestamps.
- At decision point T, usable daily bars are those with date < T.date(),
  plus date == T.date() only if T ≥ that date's session close.
  Consequences (PIT_FEATURES rule 2): a 13:30-close signal bar uses
  **yesterday's** daily bar as the latest daily input; a 16:00-close signal
  bar may use today's (session complete); a 13:00 early-close signal bar
  may use today's.
- Applies to every daily-resolution input: rs_top2 SPY leg, MTF daily
  trend, regime join, sector work. Basis: EXPLICIT (PIT_FEATURES rules 2, 8).

---

## §5. Layer-1 comparator — PRE-RUN structural/specification checks (visible)

Unchanged in substance from rev 3 (these invariants depend only on inputs
and construction rules, never on running the backtest):

### Universe / data
- Candidate pool: **272** names exact.
- Rankable in 2023-06-30→2023-09-30 ADDV window: **229** exact; unrankable: **43** exact.
- Top-120 cutoff: #120 DVN ≈ $375.7M/day, #121 DAL ≈ $373.2M/day (±2% on dollar values; identities exact).
- Post-cutoff listing candidates: **15**; admitted **11** (ARM, BMNR, CRWV, DRAM, GEV, GLXY, NBIS, RDDT, SNDK, SPCX, TEM); rejected **4** (CORZ, NNE, RBRK, UMAC) — identities exact.
- Final universe: **131** exact.
- 4H cache target: **137** symbols = 131 universe + 6 overlay outsiders (identities from docs).
- Effective 4H history ≈ 2023-10-26→2026-09-24 (start within ±5 trading days; any divergence recorded with cause).
- Session labels 09:30 / 13:30 ET; exactly one bar on NYSE early-close days.
- **Known Yahoo missing-bar exceptions** (documented, not calendar errors):
  single 4H bar on full trading days **2026-01-30** and **2026-02-02**
  (market-wide 1H gap, visible in AAPL); early-close single-bar days
  2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24, 2025-07-03, 2025-11-28,
  2025-12-24 (UNIVERSE.md).
- **Mixed return bases recorded:** rs_top2 symbol leg uses 4H closes from
  split-adjusted (not dividend-adjusted) intraday bars; the SPY daily leg
  uses split- **and** dividend-adjusted daily closes (AdjClose/Close
  scaling). The resulting small systematic basis difference is a known,
  frozen imperfection — not a defect to "fix" mid-run.
- **Headline gap convention: `realistic_gaps=False`** (live-faithful:
  stop filled AT the stop on gap-through bars — optimistic, quantified at
  ≈ −0.04R vs realistic; TP1 filled AT the TP1 level on gap-through —
  conservative. ENGINE.md assumptions 5–8.)

### Rule parameters (not outcomes)
- Max concurrent open positions: **6** (rule parameter, PORTFOLIO.md).

---

## §6. Layer-2 comparator — POST-RUN checks (unblinded)

The historical outcomes below live in
`research_notes/CANONICAL_RECONSTRUCTION_SEALED_ORACLE_20260928.json`.
The builder works **unblinded** (§0): the file's SHA-256 (§15) is an
integrity commitment to its bytes, not a blinding device. It is opened
only **after** the implementation semantics are frozen (§2–§4, §7–§8),
the code is hash-locked (§10), Run 1 completes, and Layer-1 (§5) passes —
not to preserve blinding (impossible here) but to enforce the
no-targeting process order: semantics first, comparison after.

Frozen tolerances (all must be met; any miss is a finding, never tuning
permission):
- Backtest decision counts: raw candidates **4,127** exact; skip funnel **622**
  busy / **744** slot-rank / **2,387** heat / **374** accepted exact; max concurrent
  **6** exact; open at sample end **6** exact.
- Headline E: −0.0013 ± 0.05 R/trade; win 39.8% ± 3pp; PF 1.00 ± 0.10.
- Max DD: −40.7R ± 10R; total return negative and |return| < 5%.
- Cost ladder strictly decreasing in cost (25bps E > 50bps E > 75bps E > 100bps E),
  each rung within ±0.05R of documented value.
- Year splits: 2024 E < 0 < 2025 E and 2024 E < 0 < 2026 E; each within ±0.10R.
- Concentration: ≥6 of the 10 documented top-trade identities appear in the
  rebuild's top-15 trades by R.
- 14-name overlay: n = 151 exact; E within ±0.10R of +0.4489; PF within ±0.15.

---

## §7. The seven ambiguities — FROZEN (reconciled per Claude audit)

Basis codes: EXPLICIT = pinned by surviving docs; DERIVABLE = follows from an
explicit rule with no meaningful discretion; JUDGMENT = frozen choice, recorded
as such, never revisited after the run.

### A1. Heat numerator after partial TP1 — FROZEN
`heat_dollars = Σ_pending(750) + Σ_open(actual_risk_dollars)`,
`heat = heat_dollars / E_mark(T)`, where for an open position
`actual_risk_dollars = remaining_shares × (entry − stop)` and `E_mark(T)` is
the §7/A6 snapshot. After the 50% TP1 scale-out, the position contributes
only its runner's risk. Odd-share split (B4): `tp1_shares = shares // 2`
(floor), `runner_shares = shares − tp1_shares`; the runner's remaining risk
uses `runner_shares`.
Basis: JUDGMENT (relabeled per ChatGPT 18:31Z; odd-share floor-split frozen
here per Claude B4).

### A2. Pending-entry reservation — FROZEN
An accepted signal reserves one slot and its $750 planned risk in heat from
the decision timestamp (signal-bar close) until fill or invalidation. A
pending entry makes its symbol busy. A new signal on a pending symbol is
busy-skipped. **Reservation→actual transition (B4):** at fill, the $750
reservation converts to actual risk `shares × (entry_fill − stop)`; any
difference is released back to heat capacity immediately. Pending entries
from prior bars already occupy slot + heat before the A3 batch.
Basis: JUDGMENT.

### A3. Same-timestamp evaluation sequence — FROZEN
At each signal-bar close, process that bar's candidate batch in this order:
1. Drop busy symbols (open or pending).
2. If survivors exceed free slots, rank by rs_top2 and keep the top-N by
   (rs_top2 desc, signal timestamp, symbol asc).
3. Heat check in that same rank order, first-fit: accept candidate k iff
   `(heat_dollars + 750) / E_mark(T) ≤ 0.05`; the rest are heat-skipped.
   Heat arithmetic is unambiguous: dollar sums over dollar equity, compared
   `≤ 5%` (Claude reconciliation).
Pending entries from prior bars already occupy their slot and heat before step 1.
Basis: JUDGMENT (relabeled per ChatGPT 18:31Z).

### A4. rs_top2 benchmark formula — FROZEN
`rs_top2 = (symbol 20-bar 4H return) − (SPY 20-bar daily return)`, where:
- symbol leg = `Close4H[i] / Close4H[i−20] − 1` over the 20 closed 4H bars
  ending at signal bar `i` (strict PIT — no bar with timestamp > signal-bar
  close);
- SPY leg = return over the **20 completed SPY daily bars** ending at the
  last completed daily SPY bar with timestamp ≤ signal-bar close per §4
  (strict PIT; daily-bar availability by session close, not midnight label).
Ranked at signal bar `i`. Signals with fewer than 20 closed 4H bars are
unrankable and sort last. Ties broken by signal timestamp, then symbol asc.
Entry unaffected (next-bar open).
**Relabeled JUDGMENT per Claude reconciliation** (was "EXPLICIT in prose" in
rev 3): the surviving docs admit conflicting readings — PIT_FEATURES
pins the symbol leg (20 closed 4H bars) and the SPY-leg *endpoint* (last
completed daily bar ≤ signal-bar close), but the 20-daily-bar *lookback*
is a frozen choice, and the live path's own RS (20 closed 4H bars vs QQQ,
score use only) is a different definition that must not be mixed in
(PIT_FEATURES rule 11). The formula above is kept unless a stronger
surviving source appears.
Basis: JUDGMENT.

### A5. Early-close availability timestamp — FROZEN
The single 09:30 bar on NYSE early-close days becomes available at **13:00 ET**
actual (session-local close). Signals evaluated on it carry bar-close timestamp
13:00 ET. **Recorded alternative:** a live half-day 13:30 stamping
interpretation exists in the clock-convention discussion; it is **rejected**
in favor of the 13:00 exchange-close convention (NYSE calendar semantics).
Basis: JUDGMENT.

### A6. Marked-equity / event ordering — FROZEN (completed per B5)

**At each 4H bar close** (bar `i` completes at timestamp T), process in this order:
1. Finalize the Mode B engine for bar `i` — all intrabar events (stop, TP1,
   Profit-Protect arming, timeout scheduling) are engine-internal; each leg's
   cost deducted immediately at its event. **Exits realized in bar `i` free
   the symbol's busy status for the same-T signal batch below** (B5 — frozen
   explicitly: a close exit does free same-T busy).
2. **Snapshot:** `E_mark(T) = cash(T) + Σ_open(shares × close_i)`, where
   `cash(T)` starts at $75,000 and reflects every fill and every leg-cost
   deducted through bar `i`'s close. This snapshot is the heat denominator
   for every decision stamped T and is never recomputed within T.
   **Missing-bar rule (frozen 2026-09-28):** a symbol with no bar at T
   receives **no Mode-B processing at T** — no stop/TP1/Profit-Protect/EXIT
   evaluation, no signal detection, and its 30-bar timeout clock does not
   increment (`bars_held` counts processed bars only; entry bar = #1 per
   ENGINE.md). The stale last-available close is used **only** for the
   equity-marking snapshot `E_mark(T)` (flagged stale in outputs); it never
   generates fills, signals, or timeout progress. A missing bar never blocks
   the run.
3. **New-signal batch evaluation:** run signal detection on completed bar `i`,
   then the A3 batch competition (busy → rank → heat first-fit) using
   `E_mark(T)` and slots freed by exits realized in bar `i`; pending entries
   from prior bars already occupy slot + heat.
4. Accepted signals become pending entries (reserve slot + $750 heat) stamped T.

**At each 4H bar open** (bar `i+1`):
1. Engine-scheduled fills execute first (e.g. armed Profit-Protect exits),
   symbol-asc; each leg's cost deducted immediately.
2. Pending-entry fills execute in rank order; re-check the entry > stop
   invalidation at fill time. Entry-leg cost deducted immediately. Invalidated
   pendings release their slot + heat reservation.
3. No equity marking at opens (marks happen only at closes, step 2 above).

Costs are deducted at the leg's event, never batched or deferred.
**Gap-above-target accounting (B5):** entry bar opens at/above TP1 →
immediate close at entry price, `blended_r = 0.0`, `bars_held = 0`, reason
`GAP_ABOVE_TARGET` (ENGINE.md); both legs' costs deducted (entry full-size
leg + exit full-size leg = 2 leg-equivalents → `cost_$ = bps × entry
notional`).
Basis: JUDGMENT (explicit close/open split + `E_mark(T)` snapshot frozen per
ChatGPT 18:31Z; B5 completions frozen here per Claude).

### A7. Rounding / P&L / costs outside Mode B — FROZEN (completed per B4)
- No intermediate rounding. `shares = floor(750 / (entry − stop))` (integer).
  `shares == 0` (stop wider than $750 risk) → signal skipped, logged as
  `zero-share skip`; no trade. (Entry ≤ stop → invalid skip, §2.1.)
- Dollar P&L is computed from **full-precision (unrounded) prices** and
  actual share counts. R multiples round to 4dp and dollars to 2dp **only
  at write time** (ENGINE.md `_round4` convention; live stores raw while open).
- **Net-R / cost denominator (B4):** `cost_$ = (bps/2) × Σ leg notionals`
  (entry = full-size leg at entry price; TP1 = half-size leg at TP1 price;
  runner = half-size leg — or full-size leg if no TP1 — at runner exit
  price; PORTFOLIO.md). `R_net(trade) = (gross_$_pnl − cost_$) /
  planned_risk_$`, where `planned_risk_$ = shares × (entry − stop)`.
  Headline expectancy E = mean `R_net` over accepted trades.
- Blended-R convention (gross): full-position exits report R on the full
  position; post-TP1 runner exits report
  `(tp1_shares×R(tp1) + runner_shares×R(runner_exit)) / shares`
  (ENGINE.md §2, generalized to the B4 odd-share split).
Basis: JUDGMENT.

---

## §8. Scanner EXIT — FROZEN (B7)

- **Definition.** `exit_signal = (Close_i < EMA55_i) or
  (EMA21_i < EMA55_i and EMA21_{i-1} ≥ EMA55_{i-1})`
  (price under EMA55, or EMA21/55 bear cross — §2.3).
- **Price input:** 4H close of the completed bar `i`.
- **EMA construction/seeding:** `ewm(span, adjust=False)` on 4H closes,
  causal from the symbol's series start; the §3 205-bar gate covers
  seeding stability (55-bar EMA needs no separate warmup rule).
- **Bar timing:** evaluated at completed-bar close; the scanner EXIT sets a
  pending exit **only if Profit Protect is already armed**; the pending exit
  fills at the **next bar's open** and takes precedence over stop/TP1/EXIT
  evaluation on the fill bar (ENGINE.md assumptions 9, 13).
- In `classify`, `exit_signal` also sets protection/state EXIT, but the
  backtest consumes scanner EXIT **only** through the PP-armed pending-exit
  path above.
  Basis: EXPLICIT (ENGINE.md §1/§3; the `_pure_setup_triggers` phrasing is a
  JUDGMENT reconstructed transcription per §2.3).

---

## §9. No-targeting + unblinded-replication process controls (owner directive)

- The old 143-trade C1 numbers (+0.337R/trade, +52.25%, ~31.63% DD) are
  **banned from validation** — compromised selected-sample evidence (numpy
  boolean trendScore bug, owner ruling 2026-09-28). They must not appear as
  targets, gates, or tie-breakers anywhere in the rebuild.
- The numpy-boolean trendScore bug must NOT be reintroduced. Canonical V5 is
  the V5.4 structural-contract path (no scores), per REBASELINE/PORTFOLIO.
  Gate D proves its absence (§10).
- **No historical outcome — Layer-1 or Layer-2 — was used to choose among
  the §7 resolutions.** Each records its basis. If a basis is later shown
  wrong by a surviving document, the correction is recorded as a finding;
  the run is not re-tuned.
- **Untracked-file quarantine** (§1): no implementation choice may be
  sourced from, or validated against, the untracked
  `canonical_baseline/` implementation/data files.
- **Comparator discipline:** the §6 comparator file is opened only after
  semantics are frozen (§2–§4, §7–§8), code is hash-locked (§10), Run 1
  completes, and Layer-1 passes. Any mismatch analysis cannot change
  implementation semantics unless it maps to a pre-existing frozen rule
  and independent review approves the fix (B8).

---

## §10. Bug-fix / rerun governance + Gate-D trendScore-absence test

**B8 — replaces "execute once":**
1. Before Run 1: SHA-256 hash-lock this frozen spec, the six docs, all
   rebuild code, and the cache manifest. Record the hashes in the run log.
2. Exactly one locked Run 1 per stage; outputs written once.
3. Any post-Run-1 code change must (a) cite the frozen rule/invariant it
   restores, (b) be independently reviewed (ChatGPT or Claude) **before**
   any rerun, and (c) leave both Run 1 and rerun outputs retained and
   reported. **No result-driven semantic changes**: a change motivated by
   a Layer-2 miss is forbidden unless it maps to a pre-existing frozen
   rule and passes (b).
4. A failed gate stops the rebuild (record cause; do not adjust rules to
   force a pass).

**B9 — Gate D (runs before the portfolio sim): the rebuild must prove the
historical numpy trendScore bug / score-based mirror logic is absent:**
- **D1 (static):** the rebuilt signal module contains no reference to
  legacy per-symbol score fields — `trendScore`, `rank_score`, or per-symbol
  `score` — in any entry-decision path (mechanical grep assertion over the
  rebuild tree; such fields may exist as logged-only columns, never as
  conditions). **Carve-out:** the market-regime score (§2.7 — the QQQ
  0–100 score used only for BLOCK/CAUTION/CONFIRM gate computation, a
  grading-context input) is a legitimate frozen input and is explicitly
  excluded from this ban.
- **D2 (behavioral):** entry YES/NO decisions are invariant to legacy
  score perturbation — re-run signal generation with all logged legacy
  per-symbol score fields randomized/shuffled; the accepted-signal set must
  be byte-identical. The market-regime score is excluded from the
  perturbation (frozen grading-context input, not an entry input).
- **D3 (bug-class):** all trigger conditions coerce numpy scalars with
  explicit `bool()` on scalar comparisons; no bare numpy boolean arrays
  appear in conditionals (the historical bug class: numpy-boolean
  `trendScore` silently altering entry selection).
- Gate D must pass before any portfolio simulation may run.

---

## §11. Provenance / data rules

- Daily cache: yfinance, window 2023-06-01→2026-09-24, `auto_adjust=False`,
  OHLC scaled by AdjClose/Close, raw Volume, America/New_York.
- 4H cache: yfinance 1H source, regular US session only, explicit per-session
  wall-clock aggregation (09:30–13:30, 13:30–16:00 ET), OHLCV first/max/min/last/sum,
  session-local DST-safe construction, one bar on early closes. Do NOT reuse the
  production `resample_closed_4h` global-resample behavior.
- Every cache file: SHA-256 + fetch timestamp logged; no hand edits, ever.
- Deterministic order everywhere: timestamp asc, then symbol asc. No dict-order
  or thread-order dependence.
- Rebuild stages A→G in plan order; gates A–F must pass in sequence; a failed
  gate stops the rebuild (record cause; do not adjust rules to force a pass).
- 31 Mode B synthetic unit tests (ENGINE.md) recreated and passing before the
  engine may be called (Gate C), in addition to Gate D (§10).

---

## §12. Post-run procedure (unblinded)

1. Execute the hash-locked rebuild; write outputs once.
2. Check Layer-1 (§5). Any miss: record as a finding with cause; stop — do
   not proceed to Layer-2, do not tune.
3. Verify the comparator-file hash (§15), open it, check Layer-2 (§6). Any
   miss: finding, not tuning permission.
4. If Yahoo data revisions explain a miss, label the result **non-exact**
   (data-drifted), never loosen a tolerance afterward.
5. Whatever passes is labeled **reconstructed canonical replica** from an
   **unblinded replication**.

---

## §13. Narrow Phase-0 procedural amendment (pre-authorized text)

In `research_notes/CANONICAL_QF_VALIDATION_PREREG_20260928.md`, Phase 0,
replace:
> "The reproduced headline must reconcile trade-by-trade to the published baseline."
with:
> "Phase 0 reconciles against the frozen multi-invariant comparator in
> `CANONICAL_RECONSTRUCTION_FROZEN_RULES_20260928_REV4.md` (§5 pre-run, §6
> post-run). Exact trade-by-trade reconciliation is required only if an
> original trade ledger becomes available. The rebuild result is labeled a
> reconstructed canonical replica from an unblinded replication, not a
> recovered original."

This amendment changes no trading rule, threshold, dataset, or performance gate.
Apply it when (not before) Claude + ChatGPT + Mike approve this frozen spec.

---

## §14. Remaining gates — DO NOT BUILD until all clear

1. ChatGPT adversarial re-audit of the patched rev 4.
2. Claude independent re-audit of the patched rev 4 (Mike relays the rev-4
   audit package).
3. Mike's explicit final sign-off on the frozen spec.
4. The §13 amendment applied to the validation prereg.

Build starts only after 1–4. Any material finding returns this document to DRAFT.

---

## §15. Freeze attestation + comparator commitment

- [ ] ChatGPT re-audit: PASS on patched rev 4
- [ ] Claude re-audit: READY (no unresolved material ambiguity)
- [ ] Mike final sign-off
- [ ] §13 amendment applied to validation prereg
- [ ] Code + spec + cache-manifest SHA-256 hash-lock recorded before Run 1

Comparator-file integrity commitment (NOT a blinding device):
SHA-256: `90962b798e3f442bb4df854fd34fc823c564a4a003753b3590a0cca89e7fc61a`
File: `research_notes/CANONICAL_RECONSTRUCTION_SEALED_ORACLE_20260928.json`
