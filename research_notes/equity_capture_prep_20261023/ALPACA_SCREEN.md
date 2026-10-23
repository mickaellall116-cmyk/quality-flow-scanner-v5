# ALPACA SECOND-SOURCE SCREEN — QF equity-capture prep, 2026-10-23

## DOCUMENTATION ONLY — no account created, no API call, no download

**Verdict: HOLD — single blocker `LICENSE_NOT_AFFIRMATIVE`
(classification UNPROVEN).** The technical offering passes every
documented requirement; the license battery fails at test (a), the
same failure class as Kraken (-07) and the same wall as Tiingo and
Coinbase (-06): **no instrument read affirmatively permits
retention of the data in an immutable research archive.** Tests
(b) and (c) found no offending clause (recorded absent, not
waived). Cure path in §5. The SMCI sample card in
`SMCI_RESOLUTION.md` is therefore gated on a screen pass that has
**not** occurred, plus a separate GO.

Method: official Alpaca documentation, FAQ, plan page, terms, and
support pages read as text on 2026-10-23. FACT / INFERENCE /
UNTESTED separated throughout. The claims under test are from
ChatGPT's lead, Issue #1 comment `6373305319` (2026-10-23).

---

## 1. Claims under test — disposition

| # | Claim (comment 6373305319) | Disposition |
|---|---|---|
| C1 | Historical consolidated SIP stock bars with `end` ≥15 min old may be queried **without a paid subscription** | **CONFIRMED (FACT)** — FAQ, verbatim §2.1 |
| C2 | Free Basic lists stocks history **since 2016** | **CONFIRMED (FACT)** — plan page, verbatim §2.2 |
| C3 | Alpaca crypto bars may incorporate quote-midpoint prices at zero volume → not a frozen crypto fix | **NOT RE-TESTED here** (equities-only prep; the lead's caution stands and crypto stays parked) |

## 2. Technical offering (FACT, official docs)

### 2.1 Historical SIP without subscription — FAQ verbatim

Source: Market Data FAQ, `docs.alpaca.markets/us/docs/market-data-faq`
(retrieved 2026-10-23):

> "All the latest endpoints (including the snapshot endpoint),
> require a subscription to be used with the SIP feed. **For
> historical queries, the `end` parameter must be at least 15
> minutes old to query SIP data without a subscription.**"

> "if you get a message like `subscription does not permit querying
> recent SIP data` … for example to query any SIP trades or quotes
> in the last 15 minutes, you need the Algo Trader Plus
> subscription"

The FAQ's worked example queries `feed=sip` historical bars on a
free account and contrasts SIP volume (51,861,083 shares, 535,134
trades for AAPL 2023-09-29) with IEX-only volume (923,134) — the
feed is the consolidated tape, not the free live IEX feed.

### 2.2 Plans / free tier — plan page verbatim

Source: About Market Data API,
`docs.alpaca.markets/us/docs/about-market-data-api` (page updated
2026-10-06; retrieved 2026-10-23), Trading API plans table:

| | Basic | Algo Trader Plus |
|---|---|---|
| Pricing | Free | $99 / month |
| Historical data timeframe | **Since 2016** | Since 2016 |
| Historical data limitation* | **latest 15 minutes** | no restriction |
| Historical API calls | **200 / min** | 10,000 / min |

> "Our data sources are directly fed by the CTA (Consolidated Tape
> Association) … and the UTP … stream … encompassing 100% of
> market volume."

Both QF windows (HO 2023-10-19→2024-09-15; DEV 2024-09-16→2026-10-16)
sit entirely inside "since 2016" and entirely older than 15
minutes. **No paid tier is needed for the technical offering, and
none is proposed** (a subscription purchase would be a separate
Mike decision under the hard gates regardless).

### 2.3 Bars contract — 1h, volume, adjustment, pagination

- **Timeframe:** `1Hour` supported (timeframes `1Min`–`59Min`,
  `1Hour`–`23Hour`, `1Day`, …) — Alpaca learn/reference docs.
- **Fields per bar:** `t` (timestamp), `o/h/l/c`, **`v` (volume)**,
  `n` (trade count), `vw` (VWAP) — FAQ worked example. Volume is
  present by construction: bars are aggregated from SIP trades
  under CTS/UTP bar-update rules (FAQ: "Minute and daily bars are
  aggregated from trades. … The timestamp of the bar is the left
  side of the interval" — i.e. **bar-open stamps**, UTC ISO).
- **Split adjustment:** the bars request carries an `adjustment`
  parameter with documented values **`raw`, `split`, `dividend`,
  `all`** (default `raw`). FACT: a split-adjusted basis equivalent
  in intent to the frozen `adjust=splits` basis is requestable —
  but it must be pinned explicitly, because Alpaca's default is
  `raw` (Twelve Data's default was `splits`; the request forms are
  NOT interchangeable). Whether Alpaca's split adjustment is
  byte-equivalent in convention to TD's is **UNTESTED** (a sample
  settles it; see the card in `SMCI_RESOLUTION.md`).
- **Pagination/limits:** `limit` 1–10,000 per page with
  `next_page_token` pagination. A full HO leg (1,583 bars) or DEV
  leg (3,653 bars) is a single page each — the 39-name manifest
  equivalent would be ~78 calls, trivially inside 200 calls/min.
- **Symbol continuity:** historical endpoints carry an `asof`
  parameter linking pre/post-rename data (FAQ, FB→META example) —
  relevant to GOOGL/MELI-class continuity questions; noted, not
  needed for the SMCI card.

**Technical verdict: PASS on documentation.** 1h SIP bars with
volume, split adjustment, 2016 reach, and free-tier limits all
cover the QF equity requirement with wide margin.

## 3. License battery (the battery that decided Tiingo / Coinbase / Kraken)

Governing instruments identified: (i) **Alpaca Terms and
Conditions** (Alpaca Securities LLC / AlpacaDB — governs use of the
website, API, and Content; read in full, 2026-10-23); (ii) **Alpaca
Securities Customer Agreement** §30 "Use of Market Data" (current
version V24.2026.05, files.alpaca.markets disclosures library);
(iii) Alpaca support policy pages. Exchange subscriber agreements
(NASDAQ OMX Global Subscriber Agreement; NYSE Market Data Display
Services Agreement) are **incorporated by reference** in the
Customer Agreement — see UNTESTED, §4.

### Test (a) — affirmative permission to retain data in an immutable research archive: **FAILS — NOT AFFIRMATIVE**

Operative clauses:

- T&C, "Personal and Non-Commercial Usage": *"you agree to use
  the Services and Content solely for your own personal and
  non-commercial purposes. Should you wish to use the Services and
  Content for any other purposes … you shall provide Alpaca with
  30 days advance written notice…"*
- T&C, Content clause: *"Content is provided exclusively for
  personal and noncommercial access and use. **No part of the
  Service or Content may be copied, reproduced, republished,
  uploaded, posted, publicly displayed, encoded, translated,
  transmitted or distributed in any way** (including 'mirroring')
  to any other computer, server, web site or other medium for
  publication or distribution or for any commercial enterprise,
  **without Alpaca's express prior written consent.**"*
  Market data is expressly within "Content" (T&C definition,
  item (3)).
- Customer Agreement §30: *"I agree **not to reproduce,
  distribute, sell or commercially exploit the market data in any
  manner without written consent from Alpaca**."*
- Support policy (`alpaca.markets/support/redistribute-alpaca-api`):
  *"Unfortunately, you cannot redistribute Alpaca API data."*

**No clause in any instrument read affirmatively permits
retention/storage of market data in a persistent research
archive** — internal, non-redistributed archival retention is
simply never granted; reproduction of Content is barred absent
written consent. Per the standing battery standard (Kraken -07:
a limited grant + silence on archival = NOT AFFIRMATIVE), test
(a) fails. Classification **UNPROVEN**: the instruments do not
address internal archival retention expressly, so this is absence
of permission, not an express prohibition of internal storage —
but the battery requires an affirmative grant, and there is none.

### Test (b) — clause barring validation / benchmark / algorithm use absent consent: **NONE FOUND (absent, not waived)**

No Coinbase-§3.5-type clause — nothing barring use of the data to
validate, benchmark, or improve an algorithm, agent, or automated
system — exists in the T&C or in Customer Agreement §30 as read.
Alpaca's own learn material affirmatively markets the historical
endpoints for backtesting (*"Backtest trading strategies using
minute-level to monthly aggregates"* — learn article; marketing
copy, **not** a license grant, recorded as context only). The
T&C's personal/non-commercial frame still bounds the use (test
(a)'s instrument), and the incorporated exchange agreements were
not read in full text (§4) — so (b) is recorded **absent in the
instruments read**, expressly not waived.

### Test (c) — deletion-on-termination clause: **NONE FOUND**

The T&C termination clause (read in full) permits Alpaca to
terminate/suspend access at any time with or without cause and is
silent on data already obtained — **no requirement to delete
market data on termination** (contrast Massive, whose terms
require deletion at termination and were a stated reason for its
rejection in comment 6373305319). Recorded as no clause found in
the instrument read, not as a retention permission.

## 4. UNTESTED (expressly)

- The exchange subscriber agreements incorporated by reference
  (NASDAQ OMX Global Subscriber Agreement; NYSE Market Data
  Display Services Agreement) were **not read in full text** in
  this screen. Whether CTA/UTP **non-display use** categories
  impose separate obligations on algorithmic consumption of
  historical SIP data obtained under a Basic account is **not
  addressed anywhere in Alpaca's own documentation read** and is
  UNTESTED.
- Byte-level behavior of `feed=sip` + `adjustment=split` on real
  SMCI April-2024 bars (volume presence on the 19 TD-defect stamps;
  bar-phase alignment to the XNYS 09:30/13:30/16:00 grid;
  split-convention equivalence vs TD) — UNTESTED by design; that
  is exactly what the gated sample card would settle.
- Whether a free Basic account must be a funded brokerage account,
  and any identity/verification prerequisites for API keys —
  account mechanics, not reached (no account created).

## 5. Cure path (recorded, not pursued)

Both governing instruments name the same mechanism: **Alpaca's
express prior written consent** (T&C) / **written consent**
(Customer Agreement §30). A written consent covering internal
immutable archival retention + personal algorithmic-research use
of historical SIP bars would, on re-screen, be the affirmative
grant test (a) requires. Asking for it is an outward contact and a
Mike decision; nothing was contacted in this screen.

## 6. Bottom line

Technically the strongest second source yet documented for the
equity route (consolidated SIP, volume by construction, split
adjustment, 2016 reach, free). Legally it stops at the same gate
as every no-cost route before it: **LICENSE_NOT_AFFIRMATIVE**.
The SMCI sample card (`SMCI_RESOLUTION.md`) stays NOT-EXECUTED
behind (i) this screen passing on re-screen after a cure, and
(ii) a separate GO.

— Muse
