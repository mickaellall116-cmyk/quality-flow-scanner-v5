# QF-KRAKEN-CRYPTO-LICENSE-SCREEN-20261023-07 r1 — Kraken OHLCVT license screen

**Verdict: HOLD — single blocker: `LICENSE_NOT_AFFIRMATIVE` (classification UNPROVEN).**
No pilot card is returned (the task's step-4 gate requires license AND all-seven
native-USD mapping affirmative; the license test fails first). OFFLINE documentation
screen only: no Kraken/API calls, no asset/data downloads, no credentials, no adapter.
Coinbase remains PARKED (`TERMS_USE_PROHIBITED_UNLESS_CONSENT`, comment 6373059121);
Binance Vision not worked here (separately scoped USDT-basis fallback).

## 1. The offering (FACT — official page, pinned)

Source: Kraken Support, "Downloadable historical OHLCVT (Open, High, Low, Close,
Volume, Trades) data", **Last updated: October 12, 2026**
(support.kraken.com/articles/360047124832 — retrieved as text 2026-10-23).

- Full-history CSVs per currency pair, "from the beginning of each market up to the
  present"; complete build covers each pair's first trade through **2026-06-30**, plus
  quarterly incremental ZIPs (2026Q1/Q2/Q3 published).
- Intervals in every ZIP: **1, 5, 15, 30, 60, 240, 720, 1440 minutes** — both 15m and
  a native 30m exist, so :30 S-C composability is not granularity-blocked.
- Row format: `timestamp, open, high, low, close, volume, trades` — **volume present**
  (plus trade count). No header row.
- Published integrity: per-part SHA256 sums file + full-archive SHA256
  (`bc273e90…` as printed on the page) and a `MANIFEST.json` per archive.
- Page text (FACT about the page; NOT treated as a license grant): files "can be
  viewed in a text editor, used in code, converted into other formats (such as JSON,
  XML, etc.) or imported into a graphical charting application."
- Static-file distribution → no API rate limit applies to this route (the API OHLC
  equivalent is documented on the same page as limited in retrievable amount).

## 2. License screen (FACT clauses; classification per program fail-closed rule)

Governing instrument identified: **Kraken.com Global Terms of Service, Last Updated
19 October 2026** (kraken.com/legal/global-terms; the US-resident instrument per
kraken.com/legal). The download page carries no license text of its own.

Operative clause — §8 "Content; Feedback" / **Our Content**:

> "We or our licensors own (1) our services and Platforms, (2) all content,
> materials, software, and trademarks found on them, (3) the selection and
> arrangement of them, and (4) all intellectual property rights in them
> (collectively, 'Our Content'). So long as you comply with these Terms, you are
> permitted to use our services, and Our Content made available to you as part of
> our services, **but only for your own benefit. We can take away this permission at
> any time for any reason. You do not have or acquire any rights to Our Content
> beyond the limited, revocable permission in the previous sentence. If you wish to
> use Our Content for any other purpose you must seek prior permission to do so by
> contacting marketdata@kraken.com.**"

Supporting restrictions — §9 (Restrictions), verbatim items:

> "use any web scraping, web harvesting, or data extraction methods to extract any
> data from Our Content" — prohibited.
> "access or use Our Content to build or support products or services competitive
> to our products or services" — prohibited.
> "develop any third-party applications that interact with Our Content without our
> prior written consent" — prohibited.

Test (a) — **persistence/archival**: No clause affirmatively permits storing or
archiving the data into an immutable research archive. The only grant is a
*limited, revocable* permission ("only for your own benefit"; revocable "at any time
for any reason"); rights beyond it require prior permission via
marketdata@kraken.com. **NOT AFFIRMATIVE → fails the gate.**
(An internal immutable archive for personal research is arguably "own benefit" —
that reading is INFERENCE, and this screen does not adopt it; permission is not
inferred from the download page or from silence, same discipline as Coinbase/-06.)

Test (b) — **algorithm-validation bar**: No Coinbase-§3.5-type clause was found in
the Global Terms: no express bar on using data to validate/benchmark/improve an
algorithm, agent, or automated system (full-text searched 2026-10-23; no separate
Market Data license annex exists in the instrument). FACT: absent, not waived —
moot under this gate because test (a) already fails.

**Classification: UNPROVEN** (not PROHIBITED — no express bar on the research use
itself; not AFFIRMATIVE — no archival right granted). The permission route is the
same shape as Coinbase's: prior written permission from the venue
(marketdata@kraken.com) covering internal immutable archival for personal
algorithmic research is the only documented cure.

## 3. Seven-pair native-USD mapping (documentation only; no endpoint called)

Source: Kraken API documentation, "Get Tradable Asset Pairs" (docs.kraken.com,
updated 2026-10-22). Documented convention (FACT): pair keys use internal
`X`/`Z`-prefixed names (e.g. `XXBTZUSD`, quote asset `ZUSD` = USD), `altname` drops
the prefixes (`XBTUSD`), `wsname` is slash form (`XBT/USD`); with `assetVersion=1`
pair keys are display form (`BTC/USD`). BTC/USD is exemplified verbatim in the doc
(`XXBTZUSD`, quote `ZUSD`, status online) — **native USD, no stablecoin quote.**

| Frozen ID | Kraken internal pair (documented convention) | Quote |
|---|---|---|
| BTC-USD | XXBTZUSD (doc-exemplified) | ZUSD (USD) |
| ETH-USD | XETHZUSD | ZUSD (USD) |
| SOL-USD | SOLUSD | ZUSD (USD) |
| DOGE-USD | XXDGZUSD (asset code XDG) | ZUSD (USD) |
| AVAX-USD | AVAXUSD | ZUSD (USD) |
| LINK-USD | LINKUSD | ZUSD (USD) |
| XRP-USD | XXRPZUSD | ZUSD (USD) |

Status: convention DOCUMENTED; BTC pair doc-exemplified; the remaining six are
INFERENCE from the documented naming convention + asset codes — per-pair live
existence is UNTESTED (endpoint calls were prohibited in this screen). No
stablecoin-quoted substitute was used for any pair. This mapping result is NOT
relied on for a pilot card because the license gate already failed.

## 4. Missing-candle semantics (FACT) + admissible policy choices (not implemented)

FACT (pinned page, verbatim substance): "OHLCVT data only includes entries for
intervals when trades happened, so any missing candlesticks indicate that no trades
occurred during those intervals"; "Only intervals in which trades occurred are
included (gaps are not zero-filled)." This conflicts with the frozen exact-grid GAP
rule exactly as Coinbase's no-tick rule does.

Admissible policy choices for later adjudication (stated only; nothing implemented,
nothing filled):
- **P1 (fail-closed, current rules unchanged):** absent interval = GAP → any
  pair/window containing a no-trade 15m interval fails completeness; route unusable
  wherever it fires.
- **P2 (governed amendment):** pre-registered checker amendment distinguishing a
  documented no-trade interval from missing data, frozen before any bytes are
  judged — a freeze-record change through the normal process, never a local waiver.
- **P3 (scope change):** drop crypto from the baseline (Path B, equities-only) —
  already a separate governed decision for Mike.
Inadmissible: zero-fill / forward-fill / silent omission (authorized nowhere).

## 5. Gate result

- License: **UNPROVEN** (single blocker `LICENSE_NOT_AFFIRMATIVE`) — pilot card
  withheld per task step 4.
- Frozen UX51 unchanged; TD equity route unaffected; program TD total unchanged
  (24); zero credits; zero downloads; PAUSED production pins identical before/after
  (re-verified at package close); no shadow launch.
- Cure path, if the desk chooses to pursue it: written permission from
  marketdata@kraken.com covering (i) retention in an internal immutable research
  archive and (ii) personal non-production algorithmic-research use — then re-screen
  and adjudicate §4 policy (P1/P2) before any pilot card.
