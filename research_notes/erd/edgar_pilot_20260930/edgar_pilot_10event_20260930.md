# EDGAR 10-event feasibility pilot — FINAL REPORT

**Date:** 2026-09-30 (evening ET)
**Authority:** Mike-authorized, ChatGPT-gated pilot (relayed 2026-09-30 ~16:33 ET).
**Question under test (ChatGPT revised design):** does the contemporaneous SEC EDGAR Item 2.02 8-K
and/or its Exhibit 99.1 press release contain an EXPLICIT announcement/release datetime (date +
time-of-day, timezone determinable from the source itself) sufficient for the frozen BTO/DTM/AMC
bucket classification — EDGAR as immutable evidence container, NOT as announcement clock
(per ChatGPT HOLD ruling on the as-written amendment).
**Scope guardrails honored:** read-only; no purchases/payments; no ERD performance data generated;
no frozen artifacts (V5.4, ERD, F7, canonical) modified; no formal amendment drafted.

## Verdict: UNDETERMINED — 0/10 events scorable (environmental access failure)

SEC EDGAR document content is unreachable from this environment (SEC WAF blocks this VM's egress;
details below). **No event could be scored CLEAN or UNVERIFIABLE against the frozen criteria,
because no 8-K document or exhibit text could be retrieved for any of the 10 events.** The
feasibility rate is therefore UNDETERMINED, not 0% — this is an infrastructure failure, not a
finding about the EDGAR-container design. Nothing in this pilot supports or undermines the
revised design; the gate question remains unanswered.

**Recommendation: STOP — do not draft the formal amendment on this evidence.** Re-run the pull
phase from an unblocked network (or via SEC bulk submissions data / a licensed feed) reusing the
frozen prospective selection rule, seeded draw, and CIKs documented here. The design work below is
complete and reusable; only the retrieval step failed.

## 1. Prospective selection rule (written BEFORE any draw or EDGAR pull)

Full text: `edgar_pilot_selection_rule_20260930.md` (same directory). Summary:

- **Frame (pilot-only labeled proxy):** 30 Dow components enumerated from dow-jones-djia.com
  May-2026 tables: AAPL, AMGN, AMZN, AXP, BA, CAT, CRM, CSCO, CVX, DIS, GS, HD, HON, IBM, JNJ,
  JPM, KO, MCD, MMM, MRK, MSFT, NKE, NVDA, PG, SHW, TRV, UNH, V, VZ, WMT.
  **Large-cap caveat:** mega-cap IR operations are a best case; exhibit quality here may overstate
  feasibility for the broader §4.2 universe.
- **Event:** the regular quarterly earnings release announced during calendar quarter Q of year Y
  = the chronologically FIRST 8-K with Item 2.02 filed during calendar Q of Y. NO-FILING (no
  Item 2.02 8-K in window) stays in the denominator as UNVERIFIABLE — no redraws.
- **Draw:** `random.Random(20260930)`, single stream; 10 distinct years from `range(2012, 2026)`;
  per year in draw order, `rng.choice` of ticker then quarter. Fixed denominator 10, no
  substitutions (mirrors frozen §1.5).
- **Scoring:** CLEAN iff the 8-K and/or Exhibit 99.1 establishes an explicit announcement datetime
  sufficient for BTO/DTM/AMC classification (during-session → EXCLUDE; exactly at close →
  EXCLUDE). Otherwise UNVERIFIABLE (date-only, no time, timezone indeterminable, exhibit missing
  or unretrievable, unresolvable conflicts). SEC accepted datetime = metadata only, NEVER the
  announcement clock. No inference, no guessing.

## 2. Seeded draw results (executed before any EDGAR pull; draw order preserved)

| # | Ticker | Year | Q | Window | CIK |
|---|--------|------|---|--------|-----|
| 1 | MMM | 2019 | Q3 | 2019-07-01 → 2019-09-30 | 66740 |
| 2 | JNJ | 2018 | Q4 | 2018-10-01 → 2018-12-31 | 200406 |
| 3 | AAPL | 2022 | Q1 | 2022-01-01 → 2022-03-31 | 320193 |
| 4 | JPM | 2015 | Q1 | 2015-01-01 → 2015-03-31 | 19617 |
| 5 | CAT | 2016 | Q3 | 2016-07-01 → 2016-09-30 | 18230 |
| 6 | AMZN | 2020 | Q4 | 2020-10-01 → 2020-12-31 | 1018724 |
| 7 | NKE | 2024 | Q3 | 2024-07-01 → 2024-09-30 | 320187 |
| 8 | TRV | 2025 | Q1 | 2025-01-01 → 2025-03-31 | 86312 |
| 9 | TRV | 2012 | Q4 | 2012-10-01 → 2012-12-31 | 86312 |
| 10 | VZ | 2017 | Q1 | 2017-01-01 → 2017-03-31 | 732712 |

10 distinct years. CIKs sourced from `https://www.sec.gov/files/company_tickers.json` (retrieved
successfully). No eligibility gaps: all 30 frame names are continuous SEC filers across 2012–2025;
§7 security-type exclusions do not apply.

## 3. Access barrier (what was tried, exact outcomes)

All attempts made evening of 2026-09-30 ET, polite spacing, descriptive research User-Agent.

| # | Target | Method | Result |
|---|--------|--------|--------|
| 1 | `https://www.sec.gov/files/company_tickers.json` | curl/urllib | **403** (curl blocked from the start) |
| 2 | same URL | browser text-fetch | **200** — CIKs obtained |
| 3 | `https://www.sec.gov/Archives/edgar/data/320193/` (AAPL dir listing) | browser text-fetch | **200** — accession list + last-modified dates obtained |
| 4 | `https://data.sec.gov/submissions/CIK0000320193.json` | browser text-fetch | **403** |
| 5 | `https://www.sec.gov/cgi-bin/browse-edgar?...` (AAPL 8-K browse) | browser text-fetch | **403** |
| 6 | `https://www.sec.gov/Archives/edgar/data/320193/000032019322000006/index.json` | browser text-fetch | **403** |
| 7 | `https://www.sec.gov/Archives/edgar/data/320193/000032019322000006/` (filing index) | browser text-fetch | **403** |
| 8 | `https://www.sec.gov/Archives/edgar/daily-index/2022/QTR1/master.20220127.idx` | browser text-fetch | **403** |
| 9 | 5-minute quiet period, then curl canary re-test of #1 | curl | **403** (not transient rate-limiting) |
| 10 | `https://www.sec.gov/Archives/edgar/data/66740/` (MMM dir listing) | browser text-fetch | **403** (previously-working path shape now denied) |
| 11 | Wayback: filing-index snapshot via `web.archive.org/web/2022/...` | browser text-fetch | **500** empty response, 3 attempts |
| 12 | Wayback availability API `archive.org/wayback/available` | browser text-fetch | **200** — snapshot confirmed to exist |
| 13 | Wayback raw `.../20260123154625id_/...` playback | browser text-fetch | **500** empty response, 3 attempts |
| 14 | `archive.org/advancedsearch.php` for accession `000032019322000006` | browser text-fetch | **200**, 0 results |

**Pattern:** SEC's WAF (Akamai) denies this VM's egress for essentially all EDGAR content paths —
curl is blocked outright (TLS/UA fingerprint), and the browser path was denied for
`data.sec.gov`, `/cgi-bin/*`, per-accession `/Archives/edgar/data/{cik}/{accession}/*`,
`/Archives/edgar/daily-index/*`, and eventually the CIK-level directory listings themselves
(#10 denied a path shape that succeeded once in #3). The single #3 success plus the #2 success
were the only SEC content retrieved. A 5-minute full-quiet canary (#9) confirmed the block is
persistent, not a momentary rate limit. No retry loops were run against denied endpoints; no
bypass techniques were used.

**Consequence:** no filing index could be opened (→ form type unknown, exhibit filenames unknown),
no 8-K document or Exhibit 99.1 text could be retrieved for any event. Scoring is impossible.

## 4. Per-event status

| # | Event | Status | Evidence retrieved |
|---|-------|--------|-------------------|
| 1 | MMM 2019Q3 | UNSCORABLE | none (dir listing 403) |
| 2 | JNJ 2018Q4 | UNSCORABLE | none (not attempted — path already denied) |
| 3 | AAPL 2022Q1 | UNSCORABLE | Candidate accessions from the one successful dir listing (form types UNCONFIRMED): `000032019322000006` (last-modified 2022-01-27 16:30:36), `000032019322000007` (2022-01-27 18:00:58), `000121465922001295` (2022-01-28 13:57:04), `000137773922000005` (2022-01-26 18:36:54). Late-January window only — Feb/Mar 2022 not scanned. The first (Apple's own filing-agent prefix, filed the afternoon of the Jan 27, 2022 earnings day) is the natural first candidate for the Item 2.02 8-K, but this is NOT confirmed. |
| 4 | JPM 2015Q1 | UNSCORABLE | none |
| 5 | CAT 2016Q3 | UNSCORABLE | none |
| 6 | AMZN 2020Q4 | UNSCORABLE | none |
| 7 | NKE 2024Q3 | UNSCORABLE | none |
| 8 | TRV 2025Q1 | UNSCORABLE | none |
| 9 | TRV 2012Q4 | UNSCORABLE | none |
| 10 | VZ 2017Q1 | UNSCORABLE | none |

Feasibility rate: **UNDETERMINED (0/10 scorable)**. No CLEAN / UNVERIFIABLE verdicts issued —
issuing them without the documents would be fabrication.

## 5. What this means for the gate (ChatGPT's revised design)

- ChatGPT's HOLD on the as-written amendment ("announcement datetime = SEC accepted datetime" is
  indefensible) stands untouched; this pilot was designed to test the REVISED design (EDGAR as
  immutable evidence container, datetime from the filing/exhibit itself).
- The revised design is **untested, not failed**. The blocker is this environment's SEC access,
  not exhibit content. Per ChatGPT's own stop-rule (stop rather than bending ERD around the data),
  the correct move is to re-run the pull phase where EDGAR is reachable, not to weaken the design
  or substitute proxy sources (e.g., newswire copies were deliberately NOT used — the pilot tests
  the EDGAR container, and a newswire timestamp is not the filed exhibit).
- **Design observation for the formal amendment (no amendment drafted):** the calendar-quarter
  event definition interacts with non-calendar fiscal years — e.g., NKE's regular release for the
  quarter ending Aug 31, 2024 was announced 2024-10-01, outside drawn calendar 2024Q3, which would
  make event #7 a NO-FILING → UNVERIFIABLE under the prospective rule. The formal amendment should
  decide explicitly whether the event anchor is announcement-calendar-quarter or fiscal-quarter.

## 6. Re-run checklist (for whoever has unblocked SEC access)

1. Reuse `edgar_pilot_selection_rule_20260930.md` unchanged (prospective rule + seed 20260930 +
   draw table in §2 above). Do NOT redraw.
2. For each event: list accessions with last-modified in the window from
   `https://www.sec.gov/Archives/edgar/data/{cik}/`; open each accession's filing index;
   take the chronologically first 8-K containing Item 2.02; open its Exhibit 99.1.
3. Score per §1 criteria; record accepted datetime as metadata only.
4. Write the feasibility table + recommendation (proceed to formal amendment draft vs stop).
5. Resolve the NKE-style fiscal/calendar anchor question before drafting.

## Files

- `edgar_pilot_selection_rule_20260930.md` — prospective rule (pre-draw, pre-pull).
- `edgar_pilot_working_20260930.md` — working notes from the attempt.
- This report: `edgar_pilot_10event_20260930.md`.

No frozen artifacts were read for modification or modified. No ERD performance data was produced.
No formal amendment was drafted. No purchases, payments, or signups occurred.
