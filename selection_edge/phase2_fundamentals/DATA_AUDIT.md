# DATA_AUDIT.md — Phase 2, Family 7: Fundamental Momentum

**Date:** 2026-09-24 · **Worker D.** Research only; nothing frozen touched.
**Scope:** 131-name canonical PIT universe, Oct 2023 – Sep 2026. The 14 blinded
names (QQQ, SMCI, PLTR, ANET, SOFI, RKLB, ONDS, DRAM, SPCX, ASTX, BBAI, NIO,
HOOD, AMD) are masked out of the audit set: **113** working names (131 − 14 −
4 ETFs: SPY, QQQ, IWM, DIA-class — ETFs have no earnings/analyst coverage).

**Question audited:** can any *fundamental* series be retrieved with strict
point-in-time integrity (a value may only be used at times when it was
actually knowable), at ≥70% universe-quarter coverage?

---

## Candidate series

### A. Quarterly revenue / EPS growth — UNTESTABLE (coverage fails)

- **Source:** `yfinance.Ticker.quarterly_income_stmt` (Total Revenue row).
- **Finding (25-name deterministic stride sample):** only **5 quarterly
  columns** of history per name — ~5 quarters, not the 12 quarters in the
  window. In-window revenue quarters per name: **5/12 (~42%)**, all in
  2025–2026. The dev window (Oct 2023–Dec 2024) is essentially uncovered.
- **PIT availability rule (if it had coverage):** a quarter's numbers usable
  from its earnings announcement date (matched via earnings_dates), +1
  trading day if announced after the close.
- **Leakage risks (additional):** yfinance financials are as-currently-
  published — restatements are baked in, so a "reported" Q3-2023 revenue
  number pulled today may differ from what was reported then. Quarter-end
  columns must be matched to announcement dates across varying fiscal
  calendars (fragile). Neither risk is quantifiable from this source.
- **Verdict:** FAILS the 70% coverage gate. Revenue/EPS growth factor
  **untestable** on this source over this window.

### B. EPS estimate revisions with revision timestamps — UNTESTABLE (no source)

- `yfinance.get_earnings_dates()` returns **one** "EPS Estimate" value per
  historical quarter — a snapshot (presumably the pre-announcement
  consensus), with **no revision history and no timestamps**. There is no
  way to compute "net EPS revisions in trailing 63 trading days" from it.
- Other accessible sources checked: Nasdaq earnings-calendar API
  (near-term only, no history); Alpha Vantage EARNINGS_CALENDAR
  (upcoming only); FMP (requires API key — not available); yfinance has no
  estimate-revision endpoint.
- **Verdict:** UNTESTABLE as specified. Not proxied with price action.

### C. Analyst rating revisions with timestamps — TESTABLE ✓

- **Source:** `yfinance.Ticker.get_upgrades_downgrades()` — every analyst
  action with `GradeDate` (date + time), Firm, FromGrade, ToGrade, Action
  ∈ {up, down, main, init}, back to ~2017 for large caps.
- **Coverage:** **113/113 names** have in-window events; **0 errors**;
  min **8** events/name, median **162**, mean 192.5. In-window totals:
  **866 up / 785 down** actions. Coverage is effectively 100% — far above
  the 70% gate. (A revision-time series, so "universe-quarter coverage" is
  not the binding concept: any signal date has a computable trailing
  63-trading-day count for every name.)
- **PIT availability rule:** an action with GradeDate *d* is usable for a
  signal whose as-of date (last completed daily bar ≤ signal-bar close)
  is ≥ *d*. Strictly timestamped — no announcement-date inference needed,
  no restatement risk.
- **Leakage risks:** none identified. The series is an event log, not a
  backfilled state. Minor: intra-day timing of an action vs the daily
  as-of is coarse at daily resolution — conservative (action counts only
  once its date is completed), accepted.
- **Design note:** this is analyst *rating* revisions, not *EPS estimate*
  revisions (B is unavailable). It is the closest clean-PIT realization
  of F7's "positive net EPS revisions in trailing 63 trading days"
  construction, and matches F7's mechanism verbatim ("analysts revising
  up means the numbers are improving"). The substitution is explicit and
  was pre-registered before any result was computed.

### D. Earnings announcement dates — TESTABLE (fallback, not chosen)

- **Source:** `yfinance.get_earnings_dates(limit=16)` — index is the
  announcement datetime in America/New_York (e.g. TSLA 2024-10-23
  16:00 ET), with Reported EPS / EPS Estimate / Surprise(%).
- **Coverage:** 20-name deterministic sample: 19/20 names have **12/12**
  announced quarters in window; NBIS (2024 listing) has 7/12. Mean
  **11.7/12 ≈ 98%** — clears the 70% gate. (Full 113-name census was
  superseded by this sample; raw file `audit_earnings_raw.json` may be
  partial.)
- **PIT availability rule:** announcement usable from its date; +1 trading
  day if announced at/after 16:00 ET. Historical "EPS Estimate" per quarter
  is a single snapshot of unknown vintage — **not verifiable as the
  time-of-announcement consensus**; do not use it in factors.
- **Not chosen** because C is the more direct fundamental-revisions
  series; D (post-earnings drift) is price reaction to news, weaker match
  to F7's mechanism. Documented here as the honest fallback.

---

## Decision

**TESTABLE via series C.** ≥70% coverage met (100%). One factor
pre-registered below, in REPORT.md, before any results are computed.

**Explicitly rejected:** quarterly revenue/EPS growth (coverage 42%, dev
window uncovered, restatement leakage); EPS estimate revisions with
timestamps (no accessible source); proxying fundamentals with price action
(not done — that would be families 1–6's territory).
