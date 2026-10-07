# Twelve Data Pilot — Frozen Execution Plan

**Date:** 2026-10-07
**Status:** FROZEN PLAN — awaiting ChatGPT spec read-back + Mike's standing authorization (granted 2026-10-06, conditional on spec clearance).
**Spec:** `research_notes/DATA_FEED_SAMPLE_EVAL_SPEC_20261006.md` (with [A1]–[A6], [B1]–[B7]).
**Credential:** `custom.twelvedata` (Secure Vault). No key value in any public evidence.

> This plan is documentation only. No vendor call executes until ChatGPT
> clears the amended spec. When execution is authorized, this exact plan
> runs unmodified; any deviation requires a new versioned plan.

---

## 1. Symbol list (20, frozen)

| # | Symbol | Role | Rationale |
|---|--------|------|-----------|
| 1 | AAPL | Large-cap baseline + dividend + split history | Liquid reference; 4:1 split 2020-08-28 in retained 4H cache range |
| 2 | MSFT | Large-cap baseline + dividend | Liquid reference; regular dividends for C3 |
| 3 | NVDA | Large-cap baseline + split | 10:1 split 2024-06-07 — primary C3 split test |
| 4 | AMD | Large-cap baseline | Liquid reference |
| 5 | TSLA | Large-cap baseline + split | 3:1 split 2022-08-24 — secondary C3 split test |
| 6 | META | Large-cap baseline | Liquid reference |
| 7 | GOOGL | Large-cap baseline | Liquid reference |
| 8 | QQQ | ETF baseline | ETF session behavior; NASDAQ-100 proxy |
| 9 | PLTR | Watchlist | Mike's watchlist; active name |
| 10 | HOOD | Watchlist | Mike's watchlist |
| 11 | ANET | Watchlist | Mike's watchlist |
| 12 | SMCI | Watchlist | Mike's watchlist; volatile |
| 13 | SOFI | Watchlist | Mike's watchlist |
| 14 | RKLB | Watchlist | Mike's watchlist; space thesis |
| 15 | NIO | Watchlist | Mike's watchlist |
| 16 | BBAI | Low-liquidity | Thin prints; IEX-vs-consolidated scope test [B1](iv) |
| 17 | ONDS | Low-liquidity | Thin prints; scope test |
| 18 | DRAM | Low-liquidity | Thin prints; scope test |
| 19 | SPCX | Recent IPO edge case | IPO Jun 2026; short history; tests depth limits |
| 20 | [DELISTED-TBD] | Delisted | **To be selected.** If no delisted symbol with retrievable 1H history is available on either feed, record as C5 scope limitation explicitly — do not substitute a listed symbol silently. |

---

## 2. Sample dates and lookback/warmup

### 2a. Parity window (C1, C2 — all 20 symbols)
- **Evaluation window:** 2026-09-08 (Mon) → 2026-10-06 (Tue). 20 trading days.
- **Warmup:** 50 1H bars preceding 2026-09-08 → pull from **2026-08-25**.
  Per [B2], indicator state must be defined before the first evaluated bar.
- **Rationale:** Recent window overlapping the forward-test period; both feeds
  should have complete coverage; includes no holidays (Labor Day Sep 7 is
  before window start).

### 2b. Adjustment windows (C3 — NVDA, TSLA, AAPL, MSFT only)
- **NVDA:** 2024-05-20 → 2024-06-21. Covers 10:1 split ex-date 2024-06-07.
- **TSLA:** 2022-08-10 → 2022-09-09. Covers 3:1 split ex-date 2022-08-24.
- **AAPL/MSFT:** 2026-09-08 → 2026-10-06 (parity window; dividends in-window
  if declared, otherwise dividend testing deferred with explicit note).
- Warmup: 50 1H bars before each window start.

### 2c. DST/early-close spot checks (C1)
- **Fall-back 2025:** 2026-11-01 window (1 week: 2026-10-26 → 2026-11-06) on
  AAPL, QQQ — verifies 25-hour day handling. **Note:** this window is in the
  future relative to pilot start; if unavailable, use 2025-11-02 week
  (2025-10-27 → 2025-11-07) retrospectively.
- **Early close:** 2026-07-03 (Fri, July 3 observed) on AAPL, QQQ — verifies
  single 09:30-bar sessions, no fabricated 13:30 bar.
- **Spring-forward 2026:** 2026-03-08 week (2026-03-02 → 2026-03-13) on AAPL,
  QQQ — verifies 23-hour day handling.

---

## 3. Pull parameters (frozen)

### Twelve Data (candidate)
| Parameter | 1H pull (primary) | 4H pull (diagnostic only) |
|-----------|-------------------|---------------------------|
| Endpoint | `/time_series` | `/time_series` |
| `symbol` | per symbol above | per symbol above |
| `interval` | `1h` | `4h` |
| `timezone` | `America/New_York` | `America/New_York` |
| `outputsize` | `5000` (max) | `5000` (max) |
| `start_date` / `end_date` | per §2 windows | per §2 windows |
| Auth | `?apikey=` via `custom.twelvedata` | same |

**[B6]:** Native 4H is **diagnostic only** — compared against our deterministic
1H→4H construction, never used as qualified input. C1 requires our own
session construction from documented 1H intervals.

### Yahoo (comparator — prospective capture)
| Parameter | Value |
|-----------|-------|
| Method | `yfinance`, `interval="1h"` |
| Timezone | Exchange-local (America/New_York), verified per pull |
| Windows | Same as §2 (parity + adjustment + DST/early-close) |

**[B7] comparator disclosure:** No retained Yahoo **1H** inputs exist.
Retained cache (`backtest_cache/v3/h4_*.pkl`) is **4H on the defective grid**
(08:30/12:30 labels) — usable only as a coarse session-structure reference,
**not** as a 1H comparator. The 1H comparator is therefore **prospective
capture**: fresh Yahoo 1H pulled at pilot time, documented with request/receipt
timestamps per [B3]. Both feeds are current-pull; neither has a retention
advantage in this comparison. This is explicitly **not** presented as
overlapping retained cache.

### Corporate actions (C3)
- Twelve Data: documented corporate-action endpoint (per [B5], separate
  endpoint acceptable). Record endpoint name, action-list version/as-of,
  retrieval timestamp.
- Yahoo: `yfinance` actions (splits/dividends) for the same windows.
- **Lock:** adjustment basis (raw vs adjusted) per endpoint + action-list
  version before comparison. Per [B5], no same-response packaging required.

---

## 4. Rate budget (free tier: 800/day)

| Day | Calls | Credits |
|-----|-------|---------|
| Day 1 | 20 × 1H pulls | 20 |
| Day 1 | 20 × 4H pulls (diagnostic) | 20 |
| Day 1 | 20 × symbol metadata | 20 |
| Day 2 | 20 × corporate-action pulls | 20 |
| Day 2 | Yahoo 1H comparator (no Twelve Data cost) | 0 |
| Day 2 | Retry buffer (generous) | 40 |
| Day 7 | Re-pull 20 × 1H (revision snapshot T+7d) | 20 |
| Day 30 | Re-pull 20 × 1H (revision snapshot T+30d) | 20 |
| **Peak day total** | | **≤ 100** |

**Headroom:** 700/day unused on peak day. All calls paced ≥ 8 seconds apart
to respect the 8/minute limit. **[B6]:** budget includes metadata, actions,
retries, and re-pulls — the table above is the complete accounting.

---

## 5. Decision gates per symbol

Each symbol is evaluated independently against C1–C4. **Any hard fail on any
gate disqualifies the feed for that use** (pilot is per-symbol; a feed may
pass for liquid large-caps and fail for low-liquidity names — that is a
finding, not a contradiction).

### C1 — Session construction
- [ ] 1H bar count matches expected session hours for the window (±0).
- [ ] Our 1H→4H construction produces 09:30/13:30 ET labels (no 06:30/10:30).
- [ ] DST weeks: correct bar counts on 23h/25h days.
- [ ] Early-close day: single 09:30 bar, no fabricated 13:30 bar.
- [ ] **FAIL** on any session-slot mismatch vs expected (hard fail per [A2]).

### C2 — Bar integrity and revisions
- [ ] No silently filled gaps (missing 1H bars observable).
- [ ] OHLC within 0.2% of Yahoo comparator (triage band per [B2]).
- [ ] Volume within 2% on consolidated scope; reported-not-gated on IEX.
- [ ] **Decision-impact check** [B2]: all matched inputs (including
      within-band) re-run through frozen signal logic with 50-bar warmup;
      any BUY/NO flip = hard fail; affected downstream bars traced.
- [ ] Discrepancies triaged to [B1] buckets (i)–(iv). Bucket (iv)
      recorded as scope difference, not failure.
- [ ] T+7d and T+30d re-pulls diffed; any change = revision event.
- [ ] Revision behavior marked: versioned / silent / **UNPROVEN** [B4].

### C3 — Adjustment rules
- [ ] Corporate-action contract documented (ex-date convention, split volume
      scaling, dividend yield threshold, spinoff handling).
- [ ] Frozen local `apply_adjustment()` reproduces vendor adjusted output
      on split/dividend corpus (NVDA Jun 2024, TSLA Aug 2022).
- [ ] Action-list version pinned per [B5].
- [ ] **FAIL** if adjustment math opaque or irreproducible.

### C4 — Snapshot retention
- [ ] License clause permitting immutable retention quoted by section.
- [ ] **FAIL** if no retention right (disqualified for retained-history path).

---

## 6. What gets recorded (per pull)

Per [B3], every vendor request records:
1. **Request time** (UTC, our clock, millisecond precision)
2. **Receipt time** (UTC, when last byte arrived)
3. **Raw response bytes** (stored immutable, SHA-256 logged)
4. **Request parameters** (endpoint, symbol, interval, timezone, outputsize,
   date range — exact query string)
5. **HTTP status and headers** (including any rate-limit headers)
6. **Per-bar six-field record:** label, interval end, availability
   (`UNKNOWN` if vendor does not provide), revision time (`UNKNOWN` if
   absent), request time, receipt time.

**No fabricated metadata.** Any field the vendor does not supply is recorded
as `UNKNOWN`, never inferred.

All raw responses are hash-anchored (SHA-256) and retained immutably per the
never-rewrite discipline. Detectable vendor changes trigger versioned
quarantine per [B4].

---

## 7. HOLD boundaries (explicit)

This pilot plan **does not authorize**:
- [ ] Any vendor API call before ChatGPT clears the amended spec
- [ ] Any spending (paid tier, overages, or otherwise)
- [ ] Feed switching in any production or forward-test path
- [ ] CP2 execution (R1 or R2)
- [ ] Holdout access for any purpose (per [B5], split/dividend sample
      selection uses research-visible windows only)
- [ ] Performance computation or aggregation on pilot data
- [ ] Publication of the API key or any credential value
- [ ] Any change to frozen strategy code or the forward-test harness

**Standing authorization (Mike 2026-10-06):** Run this exact frozen plan when
ChatGPT clears the amended spec. No second approval needed. Any deviation
from this plan requires a new versioned plan and re-authorization.

---

## 8. Deliverables (on execution)

1. `pilot_raw/` — hash-anchored raw responses (immutable)
2. `pilot_parity.csv` — per-symbol, per-bar parity vs Yahoo comparator
3. `pilot_gates.md` — per-symbol C1–C4 pass/fail with evidence links
4. `pilot_decision_impact.csv` — within-band and breach re-runs with
   warmup and downstream-bar tracing
5. `pilot_revisions.md` — T+7d/T+30d diff results, revision behavior verdict
6. `pilot_verdict.md` — per-symbol qualification summary; feed-level
   recommendation (if any)

All deliverables published to `research_notes/` via git push, remote-verified
byte-identical before claiming completion.
