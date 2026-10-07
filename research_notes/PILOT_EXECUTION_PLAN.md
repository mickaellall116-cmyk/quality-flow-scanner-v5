# Twelve Data Pilot — Frozen Execution Plan v4

**Date:** 2026-10-07
**Version:** v4 (supersedes v3, 2026-10-07)
**Status:** FROZEN PLAN — vendor execution HOLD per ChatGPT 6037625281/6037842097.
Offline repair (harness v2 + 25/25 tests) complete; see `research_notes/pilot_harness/`.
Execution authorized by Mike 2026-10-06 ("just run if chat says") conditional
on ChatGPT spec clearance; no redundant approval will be requested.
**Spec:** `research_notes/DATA_FEED_SAMPLE_EVAL_SPEC_20261006.md` (with [A1]–[A6], [B1]–[B7], plus v2/v3/v4 spec revisions).
**Credential:** `custom.twelvedata` (Secure Vault). No key value in any public evidence.

> This plan is documentation only. No vendor call executes until ChatGPT
> clears the amended spec. When execution is authorized, this exact plan
> runs unmodified; any deviation requires a new versioned plan.

## Changelog v3 → v4 (ChatGPT harness review 6037842097 — bounded offline repair)

ChatGPT probed the v3 harness and found 4 implementation counterexamples.
One bounded offline repair authorized and completed:

| # | Counterexample | Repair |
|---|----------------|--------|
| R1 | `validate(empty_df)` → PASS, days_validated=0 (missing sessions undetectable) | **validate_input.py v2:** request window (`--window-start/--window-end`) MANDATORY; expected sessions enumerated over the whole range. Closed day + 0 bars → PASS (verified closed, V8a). Open day + 0 bars → FAIL (missing retrieval, V8b). Empty frame + open window → FAIL (V8c). |
| R2 | Explicit `interval_end` column with +2h ends ignored; V7 passed | **V9 interval-end contract:** supplied vendor ends compared against expected boundaries (next start / session close); mismatch → FAIL. Without the column, UNKNOWN vendor contract scope is preserved, never manufactured. **V10 OHLCV schema** added (finite, H≥max(O,C), L≤min(O,C), V≥0). |
| R3 | `construct_4h()`/CLI bypass `validate()`; July 3 emitted bars via fallback; 09:30 bin emitted at 10:00; silent tz localization | **ONE mandatory entrypoint** `pilot_build.py`: source-verify → validate (window+contract+schema) → construct, no bypass. **construct_4h.py v2:** 16:00 fallback REMOVED (raises); `as_of` MANDATORY — constituent end ≤ as-of, only completed bins emitted; tz-naive input refused (explicit `--assume-tz` policy only). Early-close bin close = min(13:30, session_close). |
| R4 | `CreditLimiter(8,800)` allowed 8 credits at t=0 + 9th at t=7.5s | **rate_limiter.py v2:** rolling 60-second window (not token bucket); oversized requests refused; persistent daily accounting (JSON sidecar, restart-safe); fake-clock injectable. ChatGPT's probe now returns REFUSED. |

**Tests:** 25/25 passing (`tests/run_all.py` → `tests/synthetic_test_output.txt`):
T01–T13 legacy (upgraded to `pilot_build.py`, T09/T10 now assert pinned OHLCV values) +
R01–R08 regression (all four counterexamples + limiter properties + README path fix).
**C4:** per ChatGPT 6037842097, private-storage correction stands but the
post-termination deletion deadline does not establish permitted retention
duration → C4 marked **MISSING** (was BOUNDED). Do NOT claim all blockers resolved.

## Changelog v2 → v3 (ChatGPT read-back 6037625281, 6 blockers)

| # | Blocker | Change |
|---|---------|--------|
| 1 | Runnable harness missing; wrong SHA in signal command | **NEW:** `research_notes/pilot_harness/` — isolated offline harness with `construct_4h.py`, `validate_input.py`, `rate_limiter.py`, `synthetic_data.py`, `verify_sources.py`, `warmup_math.py`, pinned `requirements.txt`, 15/15 synthetic tests passing. **SHA CORRECTED:** `pilot_decision.py --source-sha` now `447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5` (was the incorrect `447a9a13d0b7…`). |
| 2 | WARMUP=215 ≠ EMA200 convergence | **DOCUMENTED:** seed weight after 215 updates = 11.65% (`warmup_math.py`). **RULE:** decision-impact checks (C2 BUY/NO re-runs) are INSUFFICIENT EVIDENCE unless a separately pinned initialization/sensitivity rule supports them. Acquisition/session checks proceed. |
| 3 | No straddling-interval rejection in archival | **NEW:** `validate_input.py` fail-closed validator (V1–V7) runs BEFORE construction; rejects straddles, closed-day bars, missing constituents, unknown calendar dates (no 16:00 fallback). Synthetic tests T06–T08 confirm rejection. |
| 4 | C4 retention entitlement missing | **ANALYZED:** Twelve Data Terms §2.2(a) permits internal-use storage; §2.3(g) caps at "permitted timeframes specified in the Documentation" (none specified); §16.1 limits to subscription duration; §16.2 requires deletion within 30 days of termination. **RULE:** raw vendor payloads stored PRIVATELY, never published; only manifests/code/summaries published. Indefinite immutable retention: INSUFFICIENT (unchanged). |
| 5 | 8-second spacing insufficient for 2-credit requests | **NEW:** `rate_limiter.py` credit-weighted token-bucket design (8 cr/min, 800/day cap, fail-closed refusal). Exact endpoint weights named with entitlement evidence BEFORE execution — no assumed weights. |
| 6 | Authorization citation is Muse's restatement | **CITED:** memory/2026-10-06.md:1240 — "Mike authorized the 20-symbol Twelve Data pilot to run as soon as ChatGPT clears the revised spec. No need to come back for separate approval." Conditional scope preserved; no redundant approval requested. |

## Changelog v1 → v2 (ChatGPT execution-packet corrections, 6030775964)

| # | Correction | Change |
|---|-----------|--------|
| 1 | Symbols | [DELISTED-TBD] replaced with documented TWTR delisting + frozen fallback rule; DRAM reclassified (Cboe BZX ETF, not low-liquidity); SPCX identity verified |
| 2 | Calendar/actions | July 3 2026 corrected to full-holiday CLOSED-day test; early close moved to documented Nov 28 2025; DST windows retrospective only; NVDA split Jun 10 2024; TSLA split Aug 25 2022; AAPL dividend ex-date Aug 10 2026 pinned |
| 3 | Warmup | 215 4H bars (not 50 1H rows); EMA200/ATR/ADX initialization and convergence rule pinned from archival pine_backtest.py |
| 4 | Source identity | Construction routine, source commit, dependency versions, runnable commands, and 1H interval spec pinned |
| 5 | C4 retention | Twelve Data Terms §2.2(a)/§2.3(g) cited; indefinite retention NOT evidenced → C4 INSUFFICIENT for retained-history path; pilot scoped as bounded prospective screen |
| 6 | Credential safety | Request logging sanitized; apikey values never in evidence |
| 7 | B amendments | Phantom-cache wording removed; hard-fail language triaged per [B1]; outcomes restricted to three verdicts |
| 8 | Authorization | Mike's exact authorization record cited with conditional scope |

---

## 0. Prerequisite matrix (v4 — corrected per ChatGPT 6037842097)

| Prereq | Status | Exact resolution |
|--------|--------|------------------|
| Symbol list frozen (20) | ✅ COMPLETED | §1; TWTR documented; DRAM reclassified; SPCX verified |
| Calendar/action identities pinned | ✅ COMPLETED | §2; all dates verified against NYSE calendar / issuer press releases |
| Warmup rule pinned | ⚠️ QUALIFIED | §2d; 215 4H bars from archival WARMUP=215. Seed weight 11.65% — EMA200 NOT converged. Acquisition/session checks proceed; decision-impact checks (C2) = INSUFFICIENT EVIDENCE unless separately pinned init rule supports them |
| Source identity pinned | ✅ COMPLETED | §4; archival blob SHAs; pine_backtest.py `447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5` |
| Runnable harness published (v2) | ✅ COMPLETED | `research_notes/pilot_harness/` v2: `pilot_build.py` (mandatory entrypoint), `construct_4h.py` v2 (no fallback, as-of), `validate_input.py` v2 (window V8, interval-end V9, OHLCV V10), 25/25 tests passing |
| Fail-closed input validator (v2) | ✅ COMPLETED | V1–V10; request-window enumeration; missing open-day sessions rejected; interval-end contract enforced; no silent localization |
| 1H interval spec | ✅ COMPLETED | §4; expected starts, partial-bar handling |
| C4 retention evidence | ❌ MISSING | Per ChatGPT 6037842097: private-storage correction stands, but post-termination deletion deadline ≠ permitted retention duration. No bounded retention entitlement evidenced. Do NOT claim resolved. |
| Rate limiter (rolling-window v2) | ✅ COMPLETED (design) | `rate_limiter.py` v2: rolling 60s window, persistent daily accounting, oversized refusal, fake-clock tested. Exact endpoint weights TBD with entitlement evidence before execution |
| Credential safety | ✅ COMPLETED | §6; sanitized logging |
| Authorization record | ✅ COMPLETED | memory/2026-10-06.md:1240 (resolvable); conditional scope preserved |
| ChatGPT spec clearance | ⏳ PENDING | Vendor execution HOLD until cleared |
| Mike authorization | ✅ COMPLETED | 2026-10-06 conditional; no redundant approval |

**Narrower prospective screen (if a leg cannot be satisfied):** If TWTR 1H is
unavailable on either feed at execution, the delisted leg is recorded as C5
INSUFFICIENT and the pilot proceeds at 19 symbols per the frozen fallback
rule (§1). If Twelve Data 1H history does not extend to the warmup start
(~2026-04-01), the decision-impact leg is marked INSUFFICIENT and the pilot
proceeds as acquisition/session checks only (§2d).

---

## 1. Symbol list (20, frozen)

| # | Symbol | Exchange | Role | Rationale |
|---|--------|----------|------|-----------|
| 1 | AAPL | NASDAQ | Large-cap baseline + dividend | Liquid reference; $0.27 dividend ex-date 2026-08-10 in C3 window |
| 2 | MSFT | NASDAQ | Large-cap baseline + dividend | Liquid reference |
| 3 | NVDA | NASDAQ | Large-cap baseline + split | 10:1 split; split-adjusted trading began 2024-06-10 — primary C3 split test |
| 4 | AMD | NASDAQ | Large-cap baseline | Liquid reference |
| 5 | TSLA | NASDAQ | Large-cap baseline + split | 3:1 split; split-adjusted trading began 2022-08-25 — secondary C3 split test |
| 6 | META | NASDAQ | Large-cap baseline | Liquid reference |
| 7 | GOOGL | NASDAQ | Large-cap baseline | Liquid reference |
| 8 | QQQ | NASDAQ | ETF baseline | ETF session behavior; NASDAQ-100 proxy |
| 9 | PLTR | NASDAQ | Watchlist | Mike's watchlist; active name |
| 10 | HOOD | NASDAQ | Watchlist | Mike's watchlist |
| 11 | ANET | NYSE | Watchlist | Mike's watchlist |
| 12 | SMCI | NASDAQ | Watchlist | Mike's watchlist; volatile |
| 13 | SOFI | NASDAQ | Watchlist | Mike's watchlist |
| 14 | RKLB | NYSE | Watchlist | Mike's watchlist; space thesis |
| 15 | NIO | NYSE | Watchlist | Mike's watchlist |
| 16 | BBAI | NYSE | Low-liquidity | Thin prints; IEX-vs-consolidated scope test [B1](iv) |
| 17 | ONDS | NASDAQ | Low-liquidity | Thin prints; scope test |
| 18 | DRAM | Cboe BZX | Recent-launch ETF edge case | **CORRECTED v2:** Roundhill Memory ETF (not a low-liquidity stock); launched Apr 2026; ~$26B AUM; tests short-history depth limits |
| 19 | SPCX | NASDAQ | Recent IPO edge case | **VERIFIED v2:** Space Exploration Technologies Corp., Nasdaq Global Select; IPO Jun 12 2026 at $135; short history; tests depth limits |
| 20 | TWTR | NYSE (delisted) | Delisted | **PINNED v2:** Twitter, Inc.; delisted 2022-11-08 following acquisition; tests C5 delisted-history coverage |

**Frozen fallback rule (§1):** If TWTR 1H is unavailable on either feed at
execution time, the delisted leg is recorded as **C5 INSUFFICIENT** and the
pilot proceeds at **19 symbols**. This is a frozen decision rule, not a
deviation — no plan revision required.

**Ticker identity note:** SPCX verified via multiple 2026 sources (Nasdaq
Global Select Market; IPO pricing Jun 11, first trading Jun 12, 2026).
DRAM verified as Roundhill Memory ETF, Cboe BZX Exchange — its v1
"low-liquidity" classification was factually wrong and is corrected above.
No ticker identity or IPO history is assumed; all identities verified
against public sources before freezing.

---

## 2. Sample dates and lookback/warmup

### 2a. Parity window (C1, C2 — all 20 symbols)
- **Evaluation window:** 2026-09-08 (Mon) → 2026-10-06 (Tue). 20 trading days.
- **Warmup:** 215 4H bars preceding 2026-09-08 (see §2d). 1H acquisition
  starts **2026-04-01** to guarantee coverage with margin.
- **Rationale:** Recent window overlapping the forward-test period; both feeds
  should have complete coverage; includes no holidays (Labor Day Sep 7 is
  before window start).

### 2b. Adjustment windows (C3)
- **NVDA split:** 2024-05-20 → 2024-06-21. Covers 10:1 split; **split-adjusted
  trading began 2024-06-10** (corrected v2; not 06-07).
- **TSLA split:** 2022-08-10 → 2022-09-09. Covers 3:1 split; **split-adjusted
  trading began 2022-08-25** (corrected v2; not 08-24).
- **AAPL dividend:** 2026-07-27 → 2026-08-24. Covers **$0.27/share quarterly
  dividend, ex-date 2026-08-10** (pinned v2; verified via FXEmpire/MarketBeat).
- **MSFT:** dividend leg covered via AAPL event; no separate window.
- Warmup: 215 4H bars before each window start (see §2d).

### 2c. DST/early-close/closed-day spot checks (C1)
- **Spring-forward 2026 (retrospective):** week of 2026-03-09 → 2026-03-13
  (DST began Sun 2026-03-08) on AAPL, QQQ. Compare trading sessions with
  correct UTC offsets (EDT = UTC-4). **No Sunday sessions exist for US
  equities** — the check is on Mon–Fri bar counts and labels.
- **Fall-back 2025 (retrospective):** week of 2025-11-03 → 2025-11-07
  (DST ended Sun 2025-11-02) on AAPL, QQQ. Same method; EST = UTC-5.
- **Early close (documented):** 2025-11-28 (Fri, day after Thanksgiving) on
  AAPL, QQQ — verifies 1:00 PM ET close produces shortened session, no
  fabricated bars after close.
- **Full holiday (CLOSED-day test):** 2026-07-03 (Fri; July 4 observed, NYSE
  closed) on AAPL, QQQ — **expects zero bars**; any bar emitted = hard fail.
  (Corrected v2: July 3 2026 is a full holiday, not an early close.)

### 2d. Warmup rule (corrected v2)

**Warmup is 215 bars in the evaluated indicator timeframe (4H), not 50 raw
1H rows.** Pinned from archival `pine_backtest.py`
(SHA-256 `447a9a13…`, blob `9f195dbf…`):

| Component | Lookback | Initialization |
|-----------|----------|----------------|
| EMA9/21/55/200 | 9/21/55/200 | pandas `ewm(span=l, adjust=False)`, seeded from first close |
| ATR(14) | 14 | Wilder's RMA: `ewm(alpha=1/14, adjust=False)` on true range |
| ATR baseline | 50 | `atr.rolling(50).mean()` — requires 50 converged ATR values |
| ADX(14) | 14 | Wilder's smoothing on directional movement |
| Volume MA | 20 | `rolling(20).mean()` |
| **Decision start** | **i = 215** | `WARMUP = 215`; `pine_buy_signal` returns False if e200/atr_base/adx is NaN |

**Convergence analysis (added v3, blocker 2):** The archival `ema()` uses
pandas `ewm(span=200, adjust=False)`, which seeds from the first observation
with `alpha = 2/201`. After n updates the seed weight is `(199/201)^n`.
At n=215: **11.65%** — the EMA200 is NOT stabilized (see
`research_notes/pilot_harness/warmup_math.py`; 10% threshold needs 231
updates, 5% needs 300, 1% needs 461). **Do not claim convergence from the
warmup count.** WARMUP=215 is the archival convention for decision-start
indexing, not a convergence proof.

**Frozen pilot rule (v3):**
- **Acquisition/session checks (C1)** — bar counts, labels, DST weeks,
  early-close, closed-day — proceed with the 215-bar 4H warmup. These do not
  depend on EMA convergence.
- **Decision-impact checks (C2)** — BUY/NO re-runs through frozen
  `pine_buy_signal` — are **INSUFFICIENT EVIDENCE** unless a separately
  pinned initialization/sensitivity rule and enough decision-timeframe
  history support them. Identical insufficient history on both feeds does
  not make state defined.
- No new performance experiment is authorized.

**Acquisition:** 215 4H sessions ≈ 72–108 trading days. 1H pulls start
**2026-04-01** for the Sep-08 parity window (margin included). If Twelve Data
1H history does not extend to the warmup start for a symbol, the
decision-impact check for that symbol is marked **INSUFFICIENT** and the
pilot records acquisition/session checks only — separated per correction 3,
no performance computed.

---

## 3. Pull parameters (frozen)

### Twelve Data (candidate)
| Parameter | 1H pull (primary) | 4H pull (diagnostic only) |
|-----------|-------------------|---------------------------|
| Endpoint | `/time_series` | `/time_series` |
| `symbol` | per §1 | per §1 |
| `interval` | `1h` | `4h` |
| `timezone` | `America/New_York` | `America/New_York` |
| `outputsize` | `5000` (max) | `5000` (max) |
| `start_date` / `end_date` | per §2 windows | per §2 windows |
| Auth | via `custom.twelvedata` (Secure Vault) | same |

**[B6]:** Native 4H is **diagnostic only** — compared against our deterministic
1H→4H construction, never used as qualified input. C1 requires our own
session construction from documented 1H intervals.

### 1H interval specification (added v2)

Twelve Data `1h` bars in `America/New_York`, labeled at interval start:

| Session type | Expected 1H starts (ET) | Partial-bar handling |
|--------------|------------------------|---------------------|
| Regular (09:30–16:00) | 09:30, 10:30, 11:30, 12:30, 13:30, 14:30, 15:30 | 15:30 bar covers 15:30–16:00 (30-min partial); recorded as-is, flagged `partial=true` |
| Early close (09:30–13:00) | 09:30, 10:30, 11:30, 12:30 | 12:30 bar covers 12:30–13:00 (30-min partial); flagged `partial=true` |
| Closed day | (none) | Zero bars expected; any bar = hard fail |

**Our 4H construction** (`resample_closed_4h_session_anchored`, archival
scanner_rules.py line 149): bins assigned explicitly from local session time:
[09:30–13:30) → labeled `09:30`; [13:30–16:00) → labeled `13:30` (shortened
closing-session bar). Early-close day: single [09:30–13:00) bin → labeled
`09:30`; no 13:30 bar fabricated. **Straddling intervals** (a 1H bar whose
[ start, end ) crosses a 4H bin boundary due to vendor timestamp error) are
**rejected** — recorded as a C1 hard fail, not silently assigned. Finer-grain
(15m) qualification may be proposed as a follow-up; not in this pilot.

### Yahoo (comparator — prospective capture)
| Parameter | Value |
|-----------|-------|
| Method | `yfinance`, `interval="1h"` |
| Timezone | Exchange-local (America/New_York), verified per pull |
| Windows | Same as §2 (parity + adjustment + DST/early-close/closed-day) |

**[B7] comparator disclosure:** No retained Yahoo **1H** inputs exist.
Retained cache (`backtest_cache/v3/h4_*.pkl`) is **4H on the defective grid**
(08:30/12:30 labels) — usable only as a coarse session-structure reference,
**not** as a 1H comparator. The 1H comparator is therefore **prospective
capture**: fresh Yahoo 1H pulled at pilot time, documented with request/receipt
timestamps per [B3]. Both feeds are current-pull; neither has a retention
advantage in this comparison. This is explicitly **not** presented as
overlapping retained cache.

### Corporate actions (C3)
- Twelve Data: documented corporate-action endpoint. Record endpoint name,
  action-list version/as-of, retrieval timestamp. **Weight: TBD with
  entitlement evidence before execution** (v3's unverified 2-credit
  assumption withdrawn per blocker 5 standing rule; the rolling-window
  limiter takes weights as explicit parameters).
- Yahoo: `yfinance` actions (splits/dividends) for the same windows.
- **Lock:** adjustment basis (raw vs adjusted) per endpoint + action-list
  version before comparison. Per [B5], no same-response packaging required.

---

## 4. Source identity (added v2)

| Artifact | Identity |
|----------|----------|
| Pilot plan | This file, v2, commit pinned at push time |
| Spec | `research_notes/DATA_FEED_SAMPLE_EVAL_SPEC_20261006.md` (amended) |
| 4H construction | `resample_closed_4h_session_anchored`, archival scanner_rules.py (SHA-256 `7db282dd…`, blob `087dd3a5…`), lines 149–267 |
| Signal logic | `pine_buy_signal`, archival pine_backtest.py (SHA-256 `447a9a13…`, blob `9f195dbf…`), WARMUP=215 |
| Repo commit | `5b5ff2a9817c88565b839adcd3109a5ae3216452` (2026-10-07) |
| Python deps | `pandas` (resample/ewm), `pandas_market_calendars` (NYSE calendar for session-close handling), `yfinance` (comparator) — versions pinned at execution in `pilot_env.txt` |
| NYSE calendar | `pandas_market_calendars`, `XNYS` exchange; early-close/holiday schedule from library + https://www.nyse.com/trade/hours-calendars |

**Runnable commands (v4 — the harness is published, not authored at execution):**
```bash
# Cleared entrypoint (research_notes/pilot_harness/): verify → validate → construct
cd research_notes/pilot_harness
python3 pilot_build.py --input 1h.csv --symbol AAPL \
  --window-start 2026-09-08 --window-end 2026-09-08 \
  --as-of 2026-09-08T16:00:00-04:00 \
  --out /tmp/aapl_4h.csv --verify-sources
# Regression suite (25/25)
python3 tests/run_all.py
# Limiter demo (fake clock, no network)
python3 rate_limiter.py --demo
```
(`pilot_pull.py` / `pilot_parity.py` for vendor acquisition remain authored at
execution time from the pinned sources below; `--source-sha` flags assert byte
identity before running. No vendor call executes until ChatGPT clears the spec.)

---

## 5. Rate budget (free tier: 800/day)

| Day | Calls | Credits |
|-----|-------|---------|
| Day 1 | 20 × 1H pulls (parity + warmup, outputsize=5000) | 20 |
| Day 1 | 20 × 4H pulls (diagnostic) | 20 |
| Day 1 | 20 × symbol metadata | 20 |
| Day 1 | Warmup pagination (if outputsize cap hit on long windows) | 20 |
| Day 2 | 20 × corporate-action pulls (2 credits each — corrected v2) | 40 |
| Day 2 | Yahoo 1H comparator (no Twelve Data cost) | 0 |
| Day 2 | Adjustment-window 1H pulls (NVDA/TSLA/AAPL extra windows) | 12 |
| Day 2 | DST/early-close/closed-day spot pulls (AAPL, QQQ × 4 windows × 1H) | 8 |
| Day 2 | Retry buffer | 40 |
| Day 7 | Re-pull 20 × 1H (revision snapshot T+7d) | 20 |
| Day 30 | Re-pull 20 × 1H (revision snapshot T+30d) | 20 |
| **Peak day total** | | **≤ 220** |

**Headroom:** ~580/day unused on peak day.

**Credit-weighted limiter (added v3, blocker 5):** Eight-second spacing alone
is INSUFFICIENT — a 2-credit request every 8 seconds consumes 15 credits/min
against an 8/min budget. The pilot uses the token-bucket limiter in
`research_notes/pilot_harness/rate_limiter.py`: each request declares its
credit weight BEFORE execution; the bucket refills at 8 credits/60s; requests
block until their full weight is available; a hard 800/day cap refuses
(fail-closed, not queues) once reached. **Exact endpoint credit weights are
named with entitlement evidence BEFORE execution** — the v2 assumption of
2 credits per action call was unverified and is withdrawn. Budget counts every
symbol × window × interval request, metadata/action endpoint weights,
warmup pagination, spot checks, retries, and T+7/T+30 re-pulls.

---

## 6. What gets recorded (per pull)

Per [B3], every vendor request records:
1. **Request time** (UTC, our clock, millisecond precision)
2. **Receipt time** (UTC, when last byte arrived)
3. **Raw response bytes** (stored immutable, SHA-256 logged)
4. **Request parameters** (endpoint, symbol, interval, timezone, outputsize,
   date range — **sanitized: apikey/auth values REMOVED, never the exact
   credential-bearing query string**)
5. **HTTP status and headers** (scrubbed of auth tokens; including any
   rate-limit headers)
6. **Per-bar six-field record:** label, interval end, availability
   (`UNKNOWN` if vendor does not provide), revision time (`UNKNOWN` if
   absent), request time, receipt time.

**No fabricated metadata.** Any field the vendor does not supply is recorded
as `UNKNOWN`, never inferred. **No secrets in evidence** — raw market-data
payloads are independently hashable and preserved; credentials never appear
in stored requests, logs, or error URLs.

All raw responses are hash-anchored (SHA-256) and retained immutably per the
never-rewrite discipline for the pilot's bounded 30-day window (see C4 note
in §0). Detectable vendor changes trigger versioned quarantine per [B4].

---

## 7. Decision gates per symbol

Each symbol is evaluated independently against C1–C4. Discrepancies are
**triaged per [B1]** — only bucket (i) (candidate-feed discrepancy on clean
comparator data) is chargeable to the candidate feed. Bucket (iv)
(source-scope differences) is recorded as an open scope difference, not a
failure. **No automatic blame assignment.**

### C1 — Session construction
- [ ] 1H bar count matches expected session hours for the window (±0).
- [ ] Our 1H→4H construction produces 09:30/13:30 ET labels (no 06:30/10:30).
- [ ] DST weeks: correct bar counts on transition weeks (retrospective).
- [ ] Early-close day (2025-11-28): shortened session, no fabricated bars.
- [ ] Closed day (2026-07-03): zero bars.
- [ ] **FAIL** on chargeable session-slot mismatch (bucket i only).

### C2 — Bar integrity and revisions
- [ ] No silently filled gaps (missing 1H bars observable).
- [ ] OHLC within 0.2% of Yahoo comparator (triage band per [B2]).
- [ ] Volume within 2% on consolidated scope; reported-not-gated on IEX.
- [ ] **Decision-impact check** [B2]: all matched inputs (including
      within-band) re-run through frozen signal logic with **215-bar 4H
      warmup**; any BUY/NO flip is a **material discrepancy requiring
      source/scope adjudication** — not automatic proof the candidate is
      wrong. Affected downstream bars traced.
- [ ] Discrepancies triaged to [B1] buckets (i)–(iv).
- [ ] T+7d and T+30d re-pulls diffed; any change = revision event, triaged
      per [B1] (an unversioned upstream correction is a fact about the
      vendor, not an automatic disqualification — [B4]).
- [ ] Revision behavior marked: versioned / silent / **UNPROVEN** [B4].

### C3 — Adjustment rules
- [ ] Corporate-action contract documented (ex-date convention, split volume
      scaling, dividend yield threshold, spinoff handling).
- [ ] Frozen local `apply_adjustment()` reproduces vendor adjusted output
      on split/dividend corpus (NVDA Jun 10 2024, TSLA Aug 25 2022, AAPL
      dividend Aug 10 2026).
- [ ] Action-list version pinned per [B5].
- [ ] **FAIL** if adjustment math opaque or irreproducible.

### C4 — Snapshot retention
- [ ] License clause permitting immutable retention quoted by section.
- [ ] **v3 analysis (blocker 4)** — Twelve Data Terms of Use
      (https://twelvedata.com/terms, last updated 2026-01-01):
      - §2.2(a): license to "access, receive, process, and store Data solely
        for Internal Use" — internal storage IS permitted during the
        subscription.
      - §2.3(g): prohibits storing/caching "beyond permitted timeframes
        specified in the Documentation" — the public Documentation specifies
        NO retention durations (verified 2026-10-07); no bounded entitlement
        is evidenced there.
      - §16.1: "Customer may retain Data only: (a) For duration permitted by
        subscription; (b) As required for regulatory compliance; (c) Subject
        to any Third-Party Provider restrictions."
      - §16.2: "Upon termination or expiration: (a) All Data must be deleted
        within 30 days."
      - §2.2(e)/§2.4: redistribution or external display requires a
        Redistribution Rights Add-On or separate agreement — **raw vendor
        payloads and reconstructible bar CSVs MUST NOT be published**.
- [ ] **Frozen rule (v3):** raw vendor payloads are stored PRIVATELY
      (local immutable store, never pushed to GitHub or any public surface);
      ONLY manifests (hashes, request/receipt timestamps, sanitized params),
      code, and summaries are published. The pilot's bounded 30-day window
      plus §16.2's 30-day post-termination deletion define the maximum
      retention envelope. **Indefinite immutable retention: INSUFFICIENT
      EVIDENCE** (unchanged from v2).

### Verdicts (restricted — correction 7)

Per-symbol and feed-level outcomes are exactly one of:
- **SUITABLE FOR NEXT VALIDATION STAGE** — passes C1–C4 chargeable gates;
  may proceed to deeper validation (not production).
- **UNSUITABLE** — fails a chargeable hard gate.
- **INSUFFICIENT EVIDENCE** — a leg could not be tested (e.g., TWTR
  unavailable, warmup history short, retention unproven).

**Never:** feed qualification, production clearance, or a safety claim from
this screen. The initial result does not wait for T+7/T+30 and does not
claim revision stability.

---

## 8. HOLD boundaries (explicit)

This pilot plan **does not authorize**:
- [ ] Any vendor API call before ChatGPT clears the amended spec
- [ ] Any spending (paid tier, overages, or otherwise)
- [ ] Feed switching in any production or forward-test path
- [ ] CP2 execution (R1 or R2)
- [ ] Holdout access for any purpose (split/dividend sample selection uses
      research-visible windows only)
- [ ] Performance computation or aggregation on pilot data
- [ ] Publication of the API key or any credential value
- [ ] Any change to frozen strategy code or the forward-test harness

**Standing authorization (v3, blocker 6 — resolvable record):**
`memory/2026-10-06.md:1240` — "Mike authorized the 20-symbol Twelve Data
pilot to run as soon as ChatGPT clears the revised spec. No need to come back
for separate approval." In chat on 2026-10-06, Mike's words were "just run if
chat says." **Conditional scope:** (a) ChatGPT must clear the amended spec
first; (b) the pilot runs exactly as frozen in this plan; (c) free tier only,
no spend; (d) any deviation requires a new versioned plan and
re-authorization. This is the authorization record; no redundant approval is
requested or required. Distinction: the chat quote is Mike's stated
authorization; the memory line is the contemporaneous written record.

---

## 9. Deliverables (on execution)

1. `pilot_raw/` — hash-anchored raw responses, **PRIVATE local immutable store
   ONLY** (v3, blocker 4: Terms §2.2(e)/§2.4 prohibit publishing raw vendor
   payloads; never pushed to GitHub)
2. `pilot_parity.csv` — per-symbol, per-bar parity vs Yahoo comparator
   (publishable: derived comparison, not reconstructible raw data)
3. `pilot_gates.md` — per-symbol C1–C4 pass/fail with evidence links and
   [B1] triage buckets
4. `pilot_decision_impact.csv` — within-band and breach re-runs with
   215-bar 4H warmup and downstream-bar tracing (**only where the
   decision-impact leg is not INSUFFICIENT per §2d**)
5. `pilot_revisions.md` — T+7d/T+30d diff results, revision behavior verdict
6. `pilot_verdict.md` — per-symbol summary with restricted verdicts
   (SUITABLE FOR NEXT VALIDATION STAGE / UNSUITABLE / INSUFFICIENT EVIDENCE)

Items 2–6 published to `research_notes/` via git push, remote-verified
byte-identical before claiming completion. Item 1 never leaves the private
store.
