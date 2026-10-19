# NYSE historical core-hours rule proof — QF-NYSE-HISTORICAL-CORE-HOURS-RULE-PROOF-20261019-33 r1

**Verdict: `HISTORICAL_CORE_HOURS_PROVEN`**

Spec: Issue #1 comment `6260259437` (accepts -32 as
`DATED_CALENDAR_RECOVERY_ACCEPTED__HISTORICAL_CORE_HOURS_HOLD`; cap ≤20 min, one
capture pass, repair 0 min; elapsed ~6 min). Frozen interval
[2024-09-16, 2026-10-16]; this package addresses only the unresolved block
2024-09-16..2025-12-31 and supersedes -32's coverage conclusion for the
core-hours field **by reference only** — the -31 (commit `5d2060b`) and -32
(commit `d307439`) packages are preserved unedited.

## The proof (two pinned artifacts; full pins in the package PROOF_RECEIPT.json)

1. **Both boundaries, in-force rule definition, mid-block.**
   SEC Release No. 34-103356, File No. SR-NYSE-2025-21 (NYSE LLC filing of
   Jun 17, 2025; notice dated Jun 30, 2025; immediately effective), official SEC
   copy hosted in NYSE's own rule-filings archive, footnote 42:
   > "The term 'Core Trading Hours' is defined in Rule 1.1(d) to mean the hours
   > of 9:30 a.m. Eastern Time through 4:00 p.m. Eastern Time or such other
   > hours as may be determined by the Exchange from time to time."
   The definition is stated as current rule text in a filing whose subject is
   unrelated halt-rule amendments (its Rule 1.1 changes are conforming), and the
   same filing describes the Core Trading Session as starting at 9:30 a.m.
   (current Rule 123D(f) discussion). 270,121 B,
   sha256 `5f0263f767a7e9b387ded9e7cd4132f9dc20e6e2762196d23aaab14912034e58`.

2. **Operative use at block start.** NYSE Regulatory Memo RM-24-12
   (Sep 13, 2024; expiration day Sep 20, 2024, inside the block), issued by NYSE
   Regulation: the cited rules "are applicable every day"; the Closing Auction
   Imbalance Freeze Time is "10 minutes before the scheduled end of Core
   Trading Hours. See NYSE Rule 7.35(a)(8)"; deadlines are "applicable to days
   for which the scheduled end of Core Trading Hours is 4 p.m.", citing NYSE
   Rule 7.34(a)(2)(B) for the end of Core Trading Hours. 166,801 B,
   sha256 `305fab2e09c33969f1928a3d57c26a20e99496327ac6ae3bd974927b7f0eb982`.

Temporal applicability is per spec item 3's second route: two dated in-period
official documents whose rule citations (Rules 1.1(d), 7.34(a)(2)(B), 7.35(a)(8))
and unchanged terms jointly cover the block. No current undated page was treated
as historical proof. Sibling-exchange definitions (NYSE Arca Rule 1.1, NYSE
American Rule 1.1E — same 9:30–4:00 wording) were located but deliberately
**not** used: they do not prove NYSE cash-equity hours.

## Exceptions and prohibitions

Exceptions to the 09:30–16:00 session are exactly the -32-pinned dated closures
and 13:00 ET early closes (incl. Jan 9, 2025 Carter closure); not re-derived.
No `XNYS_SESSION_SCHEDULE_V2` generated; no environment built/installed; no
calendar libraries run; no market/OHLC/timestamp data; no holdout access; no
performance/backtests; no strategy work; no production/live/ledger writes; no
vendor/TD calls; no credentials or spending; no Issue #9 work. Public
unauthenticated GETs only. Handed off for independent review only.

Package: `research_notes/nyse_historical_core_hours_proof_20261019_33/`
(`PROOF_RECEIPT.json`, `GAP_MATRIX.md`, `FETCH_LOG.txt`, `raw/` bytes + headers
+ text extractions, `SHA256_MANIFEST.txt`).
