# RESULT — QF-EQUITY43-FEED-QUALIFICATION-FRAME-20261024-21 r1

**FRAME ONLY — documentation and protocol design. Zero measurement.**
Governing text: Issue #1 comment 6385330881 (PROPOSAL — QF-EQUITY43
prospective-1h feed qualification, FRAME ONLY; NOT EXECUTION GO).
Endorsed by Mike in chat 2026-10-24 10:23 ET: permission to measure data
is not permission to resume trading; no live measurement has started.
Slack ACK 1792851843.532569; bridge ACK and this RESULT are on the bridge.

## What was delivered

1. **RIGHTS_TABLE.md (Gate A)** — a rights decision table built solely
   from Twelve Data's published documents (SOURCES.md: Terms of Use last
   updated 2026-01-01; pricing; two support articles; API docs — all
   fetched 2026-10-24, quoted verbatim with section numbers).
   - Free-tier table: 13 cells — **6 ESTABLISHED outright** (automated
     within-limits API access; Internal Use definitional match;
     delete-all-Data on termination; no-redistribution boundary;
     internal audit/replay within Internal Use; quota/billing),
     **2 ESTABLISHED in part with a confirmation rider** (non-display
     category; default-feed exchange posture), **4 UNRESOLVED**
     (retention duration; intraday bar provenance; AI-agent sharing;
     published delay figure), **1 REQUIRES_CONFIRMATION outright**
     (free-tier status vs the commercial-use bar).
   - **6 named confirmation questions (Q1–Q6)** for the provider,
     verbatim in RIGHTS_TABLE §3. The decisive ones: Q1 Basic-tier
     non-display grant; Q2 free-tier status/commercial bar; Q3 the
     §2.3(g) "permitted timeframe" for storage — which also covers the
     program's existing `qf-data-archive` retention pattern, stated
     precisely in the table without legal conclusions.
   - Tiers above free are tabulated separately; on the fetched documents
     no tier grants an express archival right, so upgrading alone does
     not close Q3.
   - The handoff's "typical REST candle delay 0.3–2 minutes" figure
     could **not** be located in the fetched official documentation; it
     is labeled UNVERIFIED and carried as Q5(ii), not as a fact.
   - **Gate A outcome: RIGHTS_TABLE_DELIVERED — rights NOT cleared.**
     Under Gate A's own stop rule, Gate B execution waits for written
     answers to at least Q1–Q3.
2. **MEASUREMENT_PROTOCOL.md (Gate B)** — a frozen design, not executed:
   5-symbol pilot (NVDA/TSLA/AAPL/SPY + lowest-DEV-volume name pinned at
   GO), 5 sessions, poll ladder +60s/+180s/+420s + finalization +1800s,
   next-session revision re-poll; worst case 149 credits/day, **hard
   pilot cap 800 credits total**; isolated read-only staging namespace
   under the -19 r2 bundle pins; raw payloads + receipt hashes to the
   private archive only; adapter parity on the exact captured bytes with
   a stop-at-first-semantic-mismatch rule; verdict labels
   LATENCY_MEASURED/UNMEASURED, COVERAGE, REVISION_CENSUS,
   ADAPTER_PARITY_PASS/FAIL/UNMEASURED, CREDIT_USAGE_MEASURED. The
   43-name expansion arithmetic is stated honestly: the full ladder is
   1,204 credits/day > the free tier's 800, so expansion needs a
   rights-cleared paid tier or the pinned reduced ladder (649/day cap).
   The protocol authorizes nothing; §9 lists what Mike's separate
   measurement GO must pin, after rights clearance.
3. **G4_NOTE.md (Gate C)** — one section: genuine source-attested
   positive controls from real captures under the frozen -20 criteria
   only; no manufactured offline controls, no new rule variants; G4
   remains HOLD.

## Bounds

No vendor API calls, no credits spent, no account access, no capture or
measurement, no holdout reads, no performance figures, no production
change, no adoption, no launch/T0. Only published documentation pages
were fetched. Production PAUSED, re-proved at package time: harness
`ce7c902c…`, `PAUSE_NEW_ENTRIES` present (`3f4b7811…`),
`RESUME_NEW_ENTRIES` absent — identical to the pre-run record. All prior
packages untouched. S1 remains PREP_READY / LAUNCH_HOLD with hold
reasons unchanged (G4_VBASIS_UNADOPTED, FEED_RIGHTS_UNQUALIFIED —
this frame is the determination step for that reason, not its removal —
T0_AUTHORITY_ABSENT).
