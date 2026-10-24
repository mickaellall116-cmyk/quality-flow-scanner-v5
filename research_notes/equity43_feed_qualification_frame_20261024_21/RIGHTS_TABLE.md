# RIGHTS DECISION TABLE — Gate A
## QF-EQUITY43-FEED-QUALIFICATION-FRAME-20261024-21 r1

Documentary determination only, from the sources in SOURCES.md (fetched
2026-10-24). **No vendor call was made and no permission is inferred anywhere:
anything the documents do not establish is labeled UNRESOLVED or
REQUIRES_CONFIRMATION.** This table states what the documents say; it is not a
legal conclusion and it clears nothing by itself.

Intended use under examination (from the governing proposal): prospective
1-hour U.S.-equity OHLCV collection for the 43-name S1 scope — private,
non-display, automated, research / paper-observation use; raw-byte capture and
retention for restricted internal audit/replay, including processing by
private AI agents acting for the account holder.

Account fact (established from the program record, not from the account):
the tier actually held is the **free tier — Basic, 800 credits/day**.

Label key: **ESTABLISHED** = the quoted document text settles the cell.
**UNRESOLVED** = the fetched documents are silent or ambiguous.
**REQUIRES_CONFIRMATION** = the cell cannot be settled from documents and is
named as an explicit question for the provider (see §3).

---

## 1. Free tier actually held (Basic)

| # | Question | Determination | Documented basis (verbatim) |
|---|----------|---------------|------------------------------|
| F1 | Automated API access / polling | **ESTABLISHED — permitted within rate limits** | S1 §1: "'API Rate Limits' means the maximum number of API requests permitted within a specified time period based on your Subscription Tier." S1 §2.3(h) prohibits only tools used "to exceed API Rate Limits or create excessive load". S2: Basic = 8 credits/minute, 800 credits/day. S5: `/time_series` "API credits cost: 1 per symbol". |
| F2 | Use is non-display, automated, private research | **ESTABLISHED as a use category; tier grant UNRESOLVED → Q1** | S1 §1: "'Non-Display Use' means any use of Data that does not involve displaying the Data to natural persons." S1 §2.2(d): customer may "Use Data for Non-Display Use **only as permitted by your subscription tier**". S4 FAQ 3 describes the default US feed as "providing accurate pricing and representative market liquidity for analytics and **non-display use**". No fetched tier document states the Basic tier's non-display permission explicitly. |
| F3 | Use matches "Internal Use" | **ESTABLISHED (definitional match)** | S1 §1: "'Internal Use' means use solely for Customer's internal business purposes and not for redistribution or external commercial purposes." S1 §2.2(a): customer may "Access, receive, process, and **store Data solely for Internal Use**". The intended use involves no external display and no redistribution. |
| F4 | Free-tier use is non-commercial | **REQUIRES_CONFIRMATION → Q2** | S1 §2.3(l): customer shall not "Use Free Tier data for commercial purposes". S1 §5.6(a): "Free Trial limited to evaluation purposes only." The documents do not define whether a private individual's pre-commercial research program is "commercial", nor whether the held Basic plan is a perpetual free tier or a "Free Trial" in S1's sense. |
| F5 | Retention / archival of retrieved bars during the term | **UNRESOLVED → Q3** | S1 §2.2(a) licenses storing Data for Internal Use (F3). But S1 §2.3(g): customer shall not "Store or cache Data beyond **permitted timeframes specified in the Documentation**". No permitted timeframe was found anywhere in the fetched Documentation (S5 searched). The documents therefore license storage but do not state for how long raw bars may be kept. |
| F6 | Retention after cancellation / termination | **ESTABLISHED — deletion required** | S1 §12.5: "Upon termination: (a) All access rights cease immediately; (b) **Customer must delete all Data**; (c) Fees remain due and payable; (d) Survival provisions continue." |
| F7 | Exchange-data rights for US equities (default feed) | **ESTABLISHED for the default feed; consolidated feed REQUIRES_CONFIRMATION → Q4** | S4: "Every Twelve Data subscription plan includes access to real-time US stock market data by default… Pricing data is sourced from venues that do not require additional licensing. These venues collectively represent approximately **5% of total US trading volume**". S4: "No additional exchange fees are required to access the default feed." S4: consolidated/all-exchange coverage requires contacting Twelve Data "to arrange licensed access to full-market data". S1 §3.1: Third-Party Data access "may require" additional provider agreements, exchange-fee payment, and compliance with provider restrictions. |
| F8 | Intraday 1h bar provenance (which venues source `time_series` 1h bars) | **UNRESOLVED → Q5** | S4 distinguishes the real-time default feed (~5% of volume) from historical/EOD data, which "covers 100% of total US trading volume, aggregated from every stock exchange" (S4, Historical and end-of-day data). The fetched documents do not state which sourcing applies to intraday 1h bars returned prospectively by `/time_series`. |
| F9 | Redistribution / external display | **ESTABLISHED — not permitted; not part of the intended use** | S1 §2.2(e): redistribution/external display "only if and as expressly authorized by a Redistribution Rights Add-On or separate written agreement". S1 §2.3(b) mirrors this. S4: the same, via Redistribution Rights Add-Ons. Attribution is required when data is displayed/redistributed externally (S4 FAQ 5). |
| F10 | Restricted internal audit / replay | **ESTABLISHED within Internal Use; raw-bar replay retention inherits F5** | Replay of stored bars inside the customer's own systems is processing of Data for Internal Use under S1 §2.2(a) (F3). Its lawfulness over time inherits the F5 retention gap (Q3), including whether journal/replay artifacts that embed raw bars are "Data" for §2.3(g)/§12.5(b) purposes. |
| F11 | Sharing with private AI agents | **UNRESOLVED → Q6** | S1 §1: "'Authorized User' means all of Customer's employees, contractors, and **computerized systems expressly authorized by Customer** to use the Platform." The text covers the customer's own computerized systems. The fetched documents do not address processing of Data by third-party-hosted AI services acting as the customer's agents, nor whether transmitting Data to such a service is disclosure/redistribution under §2.3(b) or §7. |
| F12 | Published REST candle availability delay | **UNRESOLVED → Q5** | No delay figure (including the 0.3–2 minute figure cited in the handoff) appears in S1–S5 as fetched 2026-10-24. Vendor documentation is a reference, not a measurement; the figure is UNVERIFIED in this frame. |
| F13 | Quota / billing for this use | **ESTABLISHED** | S2: Basic — 800 API credits/day daily limit; 8 credits/minute. S5: `/time_series` costs 1 credit per symbol per request; `/api_usage` costs 1 credit per request. S1 §5.2: usage-based fees are tracked and billed monthly on paid tiers; the free tier has no fees in the fetched documents. |

### What F5/F6 say about the program's existing retention pattern

The program already holds Twelve Data–captured bytes in the private
`qf-data-archive` repository (append-only captures + SHA256SUMS, from the
equities capture work of 2026-10-23). Stated precisely, and without legal
conclusions beyond the documents: S1 §2.2(a) licenses **storing** Data for
Internal Use; S1 §2.3(g) prohibits storing beyond "permitted timeframes
specified in the Documentation", and **no such timeframe appears in the
fetched Documentation**; S1 §12.5(b) requires deleting **all Data** upon
termination. The documents as fetched therefore neither state a permitted
archival duration for the existing archive nor carve it out of the
termination-deletion duty. This is confirmation question Q3 — it is the
single most consequential open cell in this table, because it covers both
the existing archive and any prospective measurement archive.

---

## 2. Published tiers above the free tier

Documented differences relevant to this use (S3, S4, S5). Per-plan prices are
not stated here: they were not legible in the fetched S2 text.

| Tier family | Documented provisions relevant to the intended use |
|-------------|------------------------------------------------------|
| Individual — Grow | Named in S3 as an individual plan "intended strictly for personal or internal use". No non-display, caching, or retention provision specific to Grow appears in the fetched documents → same F5/F11 gaps as Basic unless the vendor confirms otherwise. |
| Individual — Pro | S3: "The Pro plan allows programmatic API use for internal AI assistants". S5: `prepost` (pre/post-market) is "Only for the Pro plan (individual) and Venture plan (business) and above" — not needed for the regular-session 1h scope. |
| Individual — Ultra | Named in S3/S5 (e.g., FIGI parameter access). No use-rights provision beyond the individual-plan framing in the fetched documents. |
| Business — Venture | S3: business plans "allow the use of data for commercial display and internal usage, subject to exchange licensing requirements". S3: "the Venture plan permits temporary caching and portfolio calculations". "Temporary caching" is the only caching grant named in the fetched documents — its duration is not defined there → Q3 applies to it as well. |
| Business — Enterprise / Enterprise+ | S3: same business-plan framing as Venture. S4: redistribution and white-label delivery exist only via Add-Ons / separate agreements at this level. No archival-retention grant appears in the fetched documents. |

No tier in the fetched documents grants an express **archival** right or a
retention period. Moving up a tier changes commercial/display rights and
quotas; on the fetched documents it does **not** by itself resolve F5 (Q3),
F8, or F12.

---

## 3. Questions requiring provider confirmation in writing

Addressed to Twelve Data (support@twelvedata.com / sales@twelvedata.com per
S1 §2.4, §14.8). Each must be answered before the measurement protocol in
this package may be executed on the corresponding tier.

- **Q1 (non-display grant, Basic):** Does the Basic (free) tier permit
  Non-Display Use of U.S.-equity `/time_series` 1h data within the meaning of
  Terms §2.2(d), or is non-display permission limited to named paid tiers?
- **Q2 (free-tier status and commercial bar):** Is the held Basic plan a
  perpetual free tier or a "Free Trial" under Terms §5.6? Does a private
  individual's non-commercial research / paper-observation program fall
  outside §2.3(l)'s bar on commercial use of Free Tier data?
- **Q3 (retention/archival — covers the existing archive):** What is the
  "permitted timeframe" for storing/caching Data referenced by Terms
  §2.3(g)? Is archival retention of raw 1h bars in a private repository for
  audit/replay permitted during the subscription term, and does the
  §12.5(b) delete-all-Data duty on termination extend to such archives and
  to replay journals that embed raw bars?
- **Q4 (exchange/provider terms for the default US feed):** Do any
  Third-Party Provider or exchange terms — separate agreements, fees,
  professional/non-professional declarations, or reporting/audit duties
  beyond Terms §3.3 and §11.3 — attach to non-display internal use of the
  default U.S. feed?
- **Q5 (bar provenance and availability delay):** (i) Are prospective
  intraday 1h bars from `/time_series` sourced from the ~5%-of-volume
  default venues described in the US-equities support article, or from the
  consolidated sourcing described there for historical/EOD data?
  (ii) What is the documented typical delay between a 1h candle's close and
  its availability via REST, and where is it published? (The 0.3–2 minute
  figure could not be located in the published terms/pricing/docs/support
  pages fetched 2026-10-24.)
- **Q6 (AI-agent processing):** Are AI agents acting on the customer's
  behalf "Authorized Users" (Terms §1, "computerized systems expressly
  authorized by Customer") for restricted internal audit/replay, including
  where the agent runs on third-party-hosted AI infrastructure? Does
  transmitting Data to such an agent constitute disclosure or redistribution
  under §2.3(b)/§7?

---

## 4. Gate A outcome label

**RIGHTS_TABLE_DELIVERED — rights NOT cleared.** On the fetched documents,
automated within-limits API access, Internal Use storage, the default US
feed's licensing posture, the no-redistribution boundary, and the
termination-deletion duty are ESTABLISHED. The cells that decide whether
prospective measurement may run — Basic-tier non-display grant (Q1),
free-tier status/commercial bar (Q2), retention/archival duration (Q3) —
are UNRESOLVED in the documents and REQUIRE provider confirmation. Under
Gate A's own stop rule ("if rights remain ambiguous, STOP and present the
precise question"), Gate B execution waits for written answers to Q1–Q3 at
minimum; Q4–Q6 are recorded with it.
