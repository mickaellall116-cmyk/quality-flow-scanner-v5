# Feed Gates Evidence Table — 2026-10-07

**Task:** QF-NEXT-20261007-01 item 3 (ChatGPT 6048657174). Design/record only — no API calls, no acquisition.
**Standing rule:** A recommendation is NOT acquisition clearance. TD pilot remains HOLD on entitlements, retention, exact packet — no requests.

| Gate | Exact official document / account evidence | What it proves | Missing facts | Next bounded action |
|---|---|---|---|---|
| **P1 — Endpoint-credit entitlements (Twelve Data, Route 1)** | Twelve Data public pricing/docs (free tier: 8 credits/min, 800 credits/day cited in pilot plan). **No account-level entitlement evidence on file.** | Proves the *advertised* free-tier rate envelope only. Does not prove the exact endpoint weights for the endpoints the pilot would call. | Per-endpoint credit weights for `time_series` (1H) on the free tier, from an official source or the authenticated account dashboard. | Bounded lookup: check official docs/account page for endpoint weights. If unresolvable by 2026-10-21 → pause Route 1 (per memo §6 ceiling). No vendor calls for data until P4 clears. |
| **P2 — Free-tier 1H history to 2026-04-01 (Twelve Data, Route 1)** | None — no vendor calls made (standing HOLD). | Nothing yet. | Whether free-tier 1H history reaches 2026-04-01 for all 20 pilot symbols. | Resolve only inside an authorized pilot run after P1+P3+P4 clear. If history is short → degrade to acquisition/session checks per memo stop table. |
| **P3 — Retention qualification (Twelve Data Terms, Route 1)** | Twelve Data Terms (https://twelvedata.com/terms, updated Jan 1 2026): §2.2(a) permits internal-use storage; §2.3(g) caps storage at "permitted timeframes specified in the Documentation" (none specified in public terms); §16.1 limits use to subscription duration; §16.2 requires deletion within 30 days of termination. | Proves: internal storage is permitted in principle; retention is bounded by documentation/subscription terms. | Tier-specific retention qualification for the free tier — NOT established in the public terms. Whether immutable research retention of pilot outputs is permitted. | Bounded analysis: check Documentation for "permitted timeframes"; if absent → record UNKNOWN/HOLD, scope pilot as bounded prospective screen only, no indefinite retention. Ceiling 2026-10-21. |
| **P6 — Vendor-terms check (Route 3 prospective capture)** | None — vendor not yet selected; check NOT STARTED. | Nothing yet. | The selected vendor's terms on: (a) retention scope and duration, (b) coverage of the signal universe, (c) outage/degradation behavior under fail-closed handling. | Select candidate vendor → read its terms for (a)(b)(c) → record. If any prerequisite unresolvable → UNKNOWN/HOLD; do not start an indefinite qualification cycle. |
| **P8 — Retrospective five-criteria (Route 2-hist)** | N/A — NOT PROPOSED. | N/A. | N/A. | No historical study. Route 2-hist is not an active evidence path (Yahoo revision behavior disqualifies re-pulled history). |

**Notes:**
- P4 (ChatGPT pilot-packet spec clearance) and P5 (C1 stack pinning) are review/mapping gates, not feed gates — tracked in the memo §5 table, not duplicated here.
- P7 (realized signal rate) is a timeline assumption (~10/wk), not a feed gate.
- All evidence above is document-read or recorded HOLD — zero vendor API calls made in this handoff.
