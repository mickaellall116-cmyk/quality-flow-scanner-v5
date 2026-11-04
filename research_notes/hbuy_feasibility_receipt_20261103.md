# FEASIBILITY RECEIPT — Large Historical H-BUY Event Study (2026-11-03)

**Question put to this receipt:** can the proposed signal-only event study of the frozen
Quality Flow BUY signal (few hundred point-in-time names, several years of 4H
session-anchored bars, capture starting 108 sessions before the evaluation window,
SPY included, matched non-BUY baseline, horizons 5/10/20 bars with 10 primary,
de-clustered events) meet its three frozen floors — **≥200 de-clustered events,
≥20 symbols, ≥30 non-overlapping 20-session blocks** — and on what data route,
at what price?

**Method:** numbers only. No vendor API calls were made and no data was captured.
Stage A figures come from the run's own artifacts (`~/workspace/tier3_stagea_run/`).
Session arithmetic uses an NYSE calendar (weekdays minus NYSE full closures,
incl. the 2025-01-09 special closure) that **reproduces the program's pinned
session counts exactly** (227 sessions for 2023-10-19→2024-09-13; 524 for
2024-09-16→2026-10-16; 751 total). Prices/depths are from public vendor pages
read 2026-11-03 or from dated public re-reads of those pages (Oct–Aug 2026);
anything not verified that way is labelled **UNVERIFIED** or **ESTIMATE**.

---

## 1. BLOCK MATH — what 30 blocks actually costs in calendar time

| Component | Sessions |
|---|---|
| Indicator warmup (215 bars ≈ 108 sessions at 2 session-anchored 4H bars/day) | 108 |
| Evaluation span for the block floor (30 blocks × 20 sessions) | 600 |
| **Total capture span required** | **708** |

- NYSE sessions per calendar year (computed): 2024 = 252, 2025 = 250, 2026 = 251.
  **708 sessions ≈ 2.81 calendar years of bars.**
- **Window ending 2026-11-03 (today):** capture must run **2024-01-09 → 2026-11-03**.
  Warmup segment 2024-01-09 → 2024-06-12; evaluation segment 2024-06-13 → 2026-11-03.
- **Window ending at the Alpaca free-history limit:** the affirmed free scope
  (Section 3a) reaches back 2 years, i.e. to **2024-11-04**. Sessions available
  2024-11-04 → 2026-11-03 = **501 — 207 sessions (≈10 months) short of the 708
  required.** A full 708-session window starting at the free limit would not end
  until **2027-09-01**: the free route cannot complete the floored design from
  historical data at all, at any end date before then.
- Free-route yield inside its limit, ending today: 501 total − 108 warmup =
  **393 effective sessions = 19 full 20-session blocks** (+13 spare sessions).

For reference, Stage A's sealed window carried 227 total sessions and only
109 effective — ≈5 blocks. That is the entire reason the block floor exists.

## 2. EVENT-RATE FEASIBILITY — the 200-event floor is not the constraint

Stage A realized accrual (results.json census + ledgers, verified):
190 raw fires → 28 de-clustered → **27 cohort events** (1 dropped by the window
rule) → 20 matched-retained, over 11 names × 109 effective sessions
= 1,199 name-sessions.

- Cohort-event rate: 27 / 1,199 = **0.02252 events per name-session**
- Matched-retained rate (what powers the primary endpoint): 20 / 1,199 = **0.01668**

Projected de-clustered cohort events (matched-retained in parentheses):

| Universe | 400 eff. sessions | 600 eff. sessions | 393 eff. sessions (free route) |
|---|---|---|---|
| 100 names | 901 (667) | 1,351 (1,001) | 885 (656) |
| 200 names | 1,802 (1,334) | 2,702 (2,002) | 1,770 (1,311) |
| 300 names | 2,702 (2,002) | 4,053 (3,003) | 2,655 (1,967) |

- Minimum universe that clears 200 cohort events: **23 names** at 400 sessions;
  **15 names** at 600 sessions.
- Sensitivity: Stage A's 11 names were top-liquidity picks, so a broader universe
  will fire less per name. At **half** the Stage A rate, 100 names × 400 sessions
  still yields ≈450 events; at a **quarter** of the rate, ≈225 — still above 200.

**Verdict: the event floor clears comfortably in every cell, including the free
route.** The symbol floor (≥20) clears trivially at any proposed universe size.
The block floor (Section 1) is the only binding constraint, exactly as Claude
framed it.

## 3. ROUTES TABLE

Blocks = full post-warmup 20-session blocks achievable for a 708-session design
ending 2026-11-03. Capacity = can the route pull ~300 names × 708 sessions of
1h bars (aggregated to 4H) in one capture exercise.

| Route | Usable history depth | Blocks | Name capacity | Delisted / PIT universe | Rights basis for our use | Cost |
|---|---|---|---|---|---|---|
| **(a) Alpaca free (affirmed scope)** | **2 years** of 1h bars (support ticket 386185, 2026-11-02). Alpaca's docs list archive history "since 2016" and the Tier-3 capture did in fact pull Oct-2023 bars — but the affirmed basis is 2 years / 11 names, so depth beyond it is not counted | **19** ✗ | Fine (200 calls/min; Tier-3 capture used 109 calls for 11 names) | No PIT-universe product; universe = today's listings (delisted names effectively unavailable) | Support reply affirms private, personal storage for the asked scope — ruled SUPPORT_SCOPE_AFFIRMATIVE / **FORMAL_CONSENT_UNCERTAIN** (reply was AI-generated; not a formal waiver of the consent clause) | **$0** |
| **(b) Alpaca Algo Trader Plus** | Since 2016 (vendor docs, updated 2026-10-06) | **30** ✓ | Fine (10,000 calls/min) | Same as (a) — no PIT universe | Storage rights for a ~300-name study: **UNVERIFIED** — the Nov-2 affirmation covers the free-plan scope asked and does not extend to this | **$99/mo** (verified, alpaca.markets docs) |
| **(c) Twelve Data Grow** | ~20–30 years | **30** ✓ | Fine (Grow floor SKU 55 credits/min, no daily cap; this pull ≈ 300–600 credits ≈ ≤11 min) | Partial delisted coverage, no PIT-universe product; delisted intraday depth **UNVERIFIED** | TD's written reply of 2026-10-25: Basic is one-off evaluation only, ongoing research requires Grow → Grow is the rights-clean TD tier. **Data-quality flag (Lane C, 2026-11-03): TD revised 140/140 pilot bars after first publication; the feed is NOT team-qualified.** A one-shot historical pull takes one consistent current-final value set, but the flag stands | **from $29/mo** (Grow SKUs $29/$49/$79 by credits/min, per twelvedata.com/pricing.md ladder) |
| **(d) Databento (pay-as-you-go)** | Consolidated OHLCV (EQUS.MINI) from **2023-03-28** → covers the 2024-01-09 window start with room to spare (a 708-session window can end as early as ≈2026-01 and still fit) | **30** ✓ | No practical cap for this size (batch download) | **Yes — best in table with (e):** point-in-time symbology/instrument definitions; delisted securities remain in the archive, so a universe can be defined as of the window start | Purchased historical data under Databento's standard license (internal research use; data retained after purchase) | **≈0.08 GB for the exact pull** (300 names × 708 sessions × 7 hourly bars = 1,486,800 bars) → **ESTIMATE $1–10** at published per-GB ranges (exact EQUS.MINI ohlcv-1h rate **UNVERIFIED**); **$0 out-of-pocket** under the standard **$125 new-account credit** (verified on databento.com) |
| **(e) Polygon / Massive** | Stocks **Starter: 5 years**; Developer 10y; Advanced 20y+ | **30** ✓ (Starter suffices) | Unlimited calls on paid tiers | **Yes:** delisted tickers served; historical ticker reference supports a PIT-style universe | Individual plans licensed for personal, non-business use — fits this research | **Starter $29 for one month** (verified: $29/$79/$199 ladder, multiple Oct-2026 reads of massive.com/pricing) |
| **(f) Tiingo (key held)** | IEX **intraday from Aug 2017**; EOD to 1962 (not usable — study needs 1h) | **30 by session count — but see caveat** | Power: 100,000 req/day — fine. (Held key's tier: **UNVERIFIED**) | EOD covers delisted; intraday (IEX) coverage of since-delisted names is partial | Power = personal, internal-use license | $0 marginal if the held key's tier includes intraday (**UNVERIFIED**); otherwise **Power $30/mo** |
| **(g) Yahoo** | 1h chart history ≈ 2 years max | ≈19 ceiling ✗ | n/a | **No** — delisted tickers return nothing; PIT impossible | None — unofficial API; terms do not license bulk collection/storage | $0 — **UNQUALIFIED** (see below) |

Route caveats that matter:

- **(f) Tiingo fails on bar definition, not depth.** Its intraday bars are
  **IEX-exchange-only** (~2–3% of consolidated volume). The frozen signal's bars
  are consolidated-tape bars; on thinner names, hourly IEX bars gap, and the
  09:30/13:30 session-anchored 4H construction would silently degrade. Session
  counts pass; parity with the frozen bar definition does not.
- **(g) Yahoo is unqualified, briefly:** delisted names return no data
  (survivorship by construction), 1h depth caps at ~2 years, there is no license
  for this use, and the team's own history on Yahoo-derived bars includes a
  destroyed cache with a permanent provenance gap and the 2026-10-03
  session-anchor failure. Not reconsidered here.
- **(a) vs (b):** paying Alpaca $99 buys rate limits and real-time SIP, neither
  of which this study needs, and does not by itself cure the consent caveat for
  the expanded scope. It is the most expensive way to buy depth on this list.

## 4. THE UNTOUCHED UNIVERSE — exclusions and a $0 build

### 4.1 The exclusion lists (73 entries across three lists; 54 unique symbols)

**DEV 43** (frozen C1 DEV run `QF-EQUITY43-DEV-ORDER-CENSOR-20261023-13`;
= UX51 equities minus SMCI, pre-declared; source: dev_edge_assessment_20261103.md
+ exclusion_universes.json):
AAPL, AMAT, AMD, AMZN, APP, ARKK, ARM, ASTS, AVGO, COIN, CRM, CRWD, DDOG, F,
GOOGL, HOOD, INTC, IWM, LRCX, LUNR, MELI, META, MRNA, MSFT, MSTR, MU, NET, NFLX,
NIO, NU, NVDA, PFE, PLTR, PYPL, QCOM, RKLB, SHOP, SMH, SNOW, SOFI, SPY, TSLA, XLF

**Tier-2 19** (B1 defect census: the holdout-clean names of the 44 UX51 equities —
25 names excluded by the census: the 23 quarantined legs in
s9_contamination_audit_20261026/evidence/quarantine_census.json, plus PLTR and
SMCI; cross-checked leg-by-leg against the capture qualification record,
"19/44 holdout-clean"):
AAPL, AMD, AMZN, ARKK, ARM, AVGO, COIN, IWM, LUNR, META, MSFT, NFLX, NIO, NVDA,
SHOP, SMH, SPY, TSLA, XLF

**Tier-3 11** (Stage A verdict legs; frozen list in tier3_list.json, GOOG removed
mechanically before the run):
AAOI, ACN, BABA, BE, BLK, COF, CRDO, IREN, MPWR, SPOT, TWLO

**Precision note (read before using the count):** the three lists total
**73 entries, but the Tier-2 19 are a subset of the DEV 43** (same symbols —
Tier 2 was their holdout-window role, supplementary under the §9 Partly
outcome), and Tier-3 is disjoint. **The operative exclusion set is 54 unique
symbols** (43 + 11). Excluding all 54 is what "untouched" requires; quoting
"73 names" as a unique count would overstate it. One adjacent flag: **SMCI**
sits outside all three lists (pre-declared out of DEV; census-defective; pilot
step-1) yet was touched by the census/pilot process — adding it (55 unique)
costs nothing and closes the gap.

Note SPY is inside the DEV 43: it is excluded *as a study symbol* and is
captured separately as the benchmark input, as the design specifies.

### 4.2 Building a few-hundred-name untouched universe for $0

Concrete recipe (same pattern as the frozen Tier-3 rule):

1. Download the exchange-published listing files — NASDAQ's `nasdaqlisted.txt`
   and `otherlisted.txt` (free, dated, the exact sources the Tier-3 rule used;
   hashes recorded in tier3_list.json).
2. Filter mechanically: common stocks only, plain tickers (no units/rights/
   preferred/test issues), the Tier-3 rule's eligibility screens.
3. Delete the 54 excluded symbols (55 with SMCI) and the 7 UX51 crypto pairs
   (equities-first sequencing).
4. Take a seeded mechanical slice (record the seed; e.g. every k-th name after a
   seeded shuffle) to the target size — ~300 names is comfortably available
   (the Tier-3 funnel left 797 names passing its liquidity screen before any
   slicing).

**Survivorship caveat, stated per route:** listing files describe the market
**as of today**. Names delisted before today never appear, so on routes (a),
(b), (c), (f) the universe is "as of 2026-11-03," not as of the window start —
levels will be survivorship-flattered. The matched baseline is drawn from the
**same** universe, so that bias enters both arms and partially cancels in the
paired excess; it does not cancel for names that delisted *during* the window
after signalling. On routes (d) and (e) the same recipe can instead be run
against the vendor's point-in-time reference (as-of window start, delisted
names restored), which removes most of the caveat — one more reason the
decision in Section 5 lands where it does.

## 5. THE ONE DECISION, PRICED

**Option 1 — PAY FOR DEPTH (all three floors met).**
Cheapest floor-meeting route: **Databento, pay-as-you-go** — the exact pull is
≈0.08 GB, i.e. **$0 out-of-pocket under the standard $125 new-account credit**
(ESTIMATE $1–10 at list rates if the credit is not used; exact per-GB rate for
this schema UNVERIFIED). It meets ≥200 events (projected 2,702 at 300
names/600 sessions), ≥20 symbols, and the full **30 blocks**, and it is one of
only two routes where the point-in-time/delisted universe is actually
constructible. Cheapest fully flat-price-verified alternative: **Massive
(Polygon) Stocks Starter, $29 for one month**, same floors met, same PIT
support. (Twelve Data Grow also starts at $29/mo and meets the session floors,
but carries the team's Lane C feed-qualification flag; Alpaca Plus meets them
at $99/mo with its expanded-use rights UNVERIFIED.)

**Option 2 — FREE TWO YEARS (Alpaca, affirmed scope only).**
**$0.** Exact yield: 501 sessions available (2024-11-04 → 2026-11-03),
393 post-warmup, **19 full 20-session blocks**. Event floor still clears by a
wide margin (≈885 cohort events at 100 names) and the symbol floor clears
trivially — but the **block floor (30) is UNMET and must be labeled UNMET in
advance**, before any result is seen, exactly as Claude's framing requires.
A floored run on this route cannot exist before a window ending ≈2027-09-01.

*Nothing else is pending. The addendum work (Task A) proceeds from existing
ledgers regardless of which option is picked.*
