# Feed-Route Official Evidence — Appendix (2026-10-10)

Task: QF-FEED-ROUTE-OFFICIAL-EVIDENCE-20261010-09 r1. Read-only; zero vendor calls/credits/spend/performance/code changes.
Adjudication context: Issue #1 comment 6100384345 (planning PASS, route qualification HOLD).

## 1. Official sources (accessed 2026-10-10)

### Tiingo — Terms of Use
URL: https://app.tiingo.com/tos/ — Version 1, effective 2022-01-16, last updated 2026-10-06.

- **Free Starter / Trial plans (§1.6(a)):** may NOT write, save, archive, back up, or otherwise retain Tiingo Data in any persistent or durable storage. Processing only transiently in volatile memory or temporary non-persistent cache; must be permanently removed before the process/job/session ends. Same prohibition applies to Derived Products on Starter/Trial plans.
- **Paid plans (§1.6(b)):** may persist Tiingo Data while the plan remains active. On expiration, cancellation, termination, or downgrade: must promptly and permanently delete ALL Tiingo Data from every system — explicitly including backups, logs, queues, archives, disaster-recovery systems, and legal/regulatory/compliance retention. Exception only via separate written agreement; NOT available for Starter or Power plans.
- **Derived Products (§1.6(c)):** on Paid Plans, aggregate/non-reconstructible outputs may be created, retained, used, and distributed — explicitly listed examples include Sharpe/Sortino ratios, alpha, beta, maximum drawdown, win rate, aggregate profit and loss; trading signals/forecasts/scores that do not expose underlying data; 5-field cryptographic hashes. Prohibited: resampled/rebased/indexed series recoverable to underlying data (e.g. equity curve rebased to 100); using Tiingo Data to validate another dataset (a substitute use — the validated dataset must be deleted too).
- **Restrictions (§1.4):** no redistribution of API-obtained data without prior written consent; no scraping of website pages; no commercial exploitation of Company Properties.

### Tiingo — free-tier limits (official tiingo.com blog, "Using Tiingo's Forex API")
URL: https://www.tiingo.com/blog/forex-api/ — Starter $0: 500 unique symbols/month, 50 requests/hour, 1,000 requests/day, 1 GB bandwidth/month.

### Tiingo — UNKNOWN (not found in official sources checked)
- Historical depth (how far back EOD/intraday extends): UNKNOWN.
- Revision/backfill policy: UNKNOWN.

### Yahoo Finance — official Terms
Official URL: https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html — content UNKNOWN: fetch blocked by sandbox policy on 2026-10-10. Permitted use, retention/raw-storage rights, historical depth, revision/backfill policy, free-tier limits: ALL UNKNOWN from official sources. (Third-party summaries uniformly describe the chart/quote endpoints as undocumented with no public API terms; not substituted as evidence.)

## 2. V5.4 forward-test raw-bar capture

**PROSPECTIVE RAW CAPTURE NOT IMPLEMENTED.**

- `v54_forward_harness.py` downloads Yahoo bars per cycle via yfinance, evaluates the frozen signal, and discards them. No `to_csv`/`to_parquet`/`to_pickle` of raw OHLCV exists in the harness.
- `v54_forward/forward_test.jsonl` (454 lines) is append-only for frozen-schema signal/close event summaries — it is NOT a raw-bar store and contains no versioned vendor payloads.
- `forward_test/archive/` holds one status snapshot (`2026-09-28-v54-snapshot`), not bar data.

## 3. Realized forward-test signal count (separate from assumptions)

- 30 distinct signal_ids in `v54_forward/forward_test.jsonl` = `forward_test/v54_status.json` `signals_logged: 30` (grades A:7, B:21, C:2), as of 2026-10-10T17:51:15Z.
- Window: forward-test start 2026-09-15 → 2026-10-10 (~25 days). Realized ≈ 8.4 signals/week — stated separately from the ~10/week planning assumption.

## 4. Limitations carried forward

Route qualification remains HOLD per 6100384345: official Yahoo entitlement unknown; Tiingo free-tier retention prohibition blocks any raw Tiingo bar storage on a Starter plan; no prospective versioned raw-bar capture exists for the Yahoo-fed forward test, so any future vendor-drift claim rests on event logs, not pinned raw bytes.
