# P10 Audit — Data Rights / Session Tables / Adjustment Handling

**Date:** 2026-10-26. **Precondition:** P10 (§3) — freeze-path item, checklist C2. **Status:** audit record produced; independent review remains ChatGPT's.
**Method:** record-only. Every position below cites evidence already on record (committed packages, the vendor correspondence of record, governance decisions). No vendor was contacted, no data was purchased or downloaded, and no holdout-window data was accessed for this audit.

---

## 1. Rights position per data source

### 1.1 Twelve Data — the only route that has produced qualifying bytes

**What the program holds.** Raw 1h bars captured 2026-10-23 under the frozen capture manifest (labelled `CAPTURED_G1_G6_CANDIDATE_G4_UNADOPTED` — candidate bytes, never QUALIFIED): DEV set 43/44 equities clean (SMCI never captured); both-window set 19/44 holdout-clean. Raw bytes live **only** in the private repo `qf-data-archive` (append-only, SHA256SUMS, re-fetch-verified) and locally — never in the public scanner repo. Account tier actually held: **Basic (free), 800 credits/day, 8 credits/minute**.

**Documentary position (frame -21, commit `c2b58d7`, RIGHTS_TABLE.md — from Twelve Data's own published Terms/pricing/docs, fetched 2026-10-24):**

- ESTABLISHED: automated API access within rate limits; storage licensed "solely for Internal Use" (Terms §2.2(a)); the intended use (private, non-display, no redistribution) matches the Internal Use definition; redistribution/external display barred absent an add-on (§2.2(e)); the default US feed carries no additional exchange licensing (~5% of US volume; EOD/consolidated sourcing is 100%).
- ESTABLISHED, adverse: **on termination, all Data must be deleted** (§12.5(b)).
- UNRESOLVED in the documents: the Basic tier's express non-display grant (Q1), whether a private individual's research program is "commercial" under the free-tier bar §2.3(l) (Q2), and the retention/archival timeframe behind §2.3(g)'s "permitted timeframes specified in the Documentation" — **no such timeframe appears in the published Documentation** (Q3). No tier in the fetched documents, free or paid, grants an express archival right.
- UNRESOLVED: intraday 1h bar provenance (default ~5% venues vs consolidated) and any published availability-delay figure (Q5); third-party-hosted AI-agent processing as "Authorized User" (Q6). Program practice is stricter than the open question: **raw data stays in the private environment; external AI services receive derived results only** (decided 2026-10-24).

**Vendor correspondence (the governing layer, supersedes the AI-assistant answers where they differ):**

- Inquiry Q1–Q6 emailed to support@twelvedata.com 2026-10-24 (thread `1a16e539bce6f334`). The first answers came from Twelve Data's AI assistant ("Dooz"): Basic permits internal non-display evaluation/development processing and storage; private research/paper use is non-commercial; storage during the subscription with deletion within 30 days after its end; raw data must not be shared with external AI services.
- **Staff reply (Artemis, 2026-10-25T20:55:03Z, Gmail id `1a174d86fc89c552`, same thread) — the governing source:** Basic's non-display permission covers **evaluation/integration**; **ongoing research analytics beyond one-off evaluation require Grow**; storage is permitted while the subscription is active; **all raw data — including private archives and replay journals — must be deleted within 30 days after the subscription/account ends**; a continuous research archive/replay workflow has Grow as its practical minimum.
- **Determination recorded 2026-10-26 (Mike's directive):** the frozen five-stock feed-measurement pilot (-22; NVDA/TSLA/AAPL/SPY/MELI × 5 sessions) is **API/feed evaluation** within Basic's permission, on three stated conditions: it stays exactly as frozen (feed measurement only — timestamps, coverage, revision behaviour), its captures are never used for strategy research or replay, and the determination dies if the use expands. Posted to Slack #qualityflowscaner (TS `1793043021.036639`) for ChatGPT adjudication; the pilot remained tripwire-held, with zero calls made, pending that adjudication and the daemon/quota verification.

**Conclusions — Twelve Data.**
1. The existing `qf-data-archive` holdings sit in the Q3 gap: storage for Internal Use is licensed, no archival duration is granted anywhere in the documents, and the staff-confirmed duty is deletion of **all** raw data within 30 days after the subscription ends. The archive is lawful to hold **during** the active subscription on the record as it stands; it carries a standing deletion duty if the subscription ends, and no document converts it into a permanent archive.
2. Prospective **ongoing research analytics / continuous archive-replay on Basic is not permitted** on the governing (staff) reading. Any Tier 4 collection route on Twelve Data therefore needs either a tier whose terms cover the use (Grow minimum per the staff reply, purchase = Mike's hard gate) or a different qualified route. Feed **evaluation** (the -22 pilot) is permitted as scoped above.
3. Intraday provenance and delay remain UNVERIFIED from documents (Q5) — which is precisely what the -22 measurement pilot exists to establish empirically.

### 1.2 Yahoo Finance

- Role: the historical workhorse (original DEV lineage; prospective V5.4 forward-test cycles under fail-closed guards) and the proposed clean-capture source for a corrected baseline (readiness map, 2026-10-15).
- Position: free web/API access with **no archival or persistence grant**; the D1 4H cache (52 files, 75,311 bars) was git-ignored local-only storage and was **destroyed in a VM replacement** — its per-file SHA256 pins survive in the CP1 forensic bundle, its bytes do not. Held Yahoo sets that remain are diagnostic-only (watchlist universe, adjustment policy unpinned). Known operational defects on record: silent bar revisions (2026-10-01 AAPL rewrite → V3.6 halt), multi-day degraded refresh cycles, ~730-day 1H reachback, tier LIMITED (not PIT-clean).
- **Conclusion:** usable as an operational feed under the existing guards; **not** a qualified archival source for preregistration evidence. Nothing in this audit relies on Yahoo bytes for a frozen pin.

### 1.3 Tiingo

- Held: EOD set, 444 symbols, ~1.54M rows (2009 → 2026-09-30), raw + adjusted fields both present (policy-ambiguous); a degraded-mode observer role in the forward stack (fills Yahoo gaps on degraded cycles only, never touches forward-test state).
- Position: **terms HOLD** — the free terms do not grant the persistence this program requires, and the held set is daily-only against a 1h→4h contract. ~380 MB held locally, **nothing deleted** (deletion is Mike's decision; Muse's standing recommendation is delete via plan-first, undecided as of this audit).
- **Conclusion:** not a qualified source for preregistration evidence; remains fail-closed HOLD.

### 1.4 Coinbase / Kraken / Alpaca (crypto route — parked under equities-first)

- These were screened for the crypto leg of the universe (7 pairs), which is **parked** (Mike, 2026-10-23: equities first; the full-51 test is sequenced, not abandoned). Outcome on record for each: **no persistence grant** — Coinbase blocked on terms, Kraken's licence is not affirmative without written permission, Alpaca's terms are personal-use only. No qualifying crypto bytes exist from any route (Twelve Data crypto lacks volume and uses calendar-day anchors).
- **Conclusion:** no crypto data source is qualified; no crypto evidence enters the v1.0 freeze. Reopening any of these is a new adjudication, and a purchase (e.g. Tardis.dev, named as a possibility only) is Mike's hard gate — nothing was authorized.

### 1.5 Purchased-licence routes (Databento, Tardis.dev, Intrinio/Zacks)

Named in the record as the only routes that would grant archival rights outright (pay-per-GB / subscription). **No purchase has been made or authorized**; Mike declined Intrinio/Zacks ($950/mo) for the ERD timing audit. They are recorded here so the freeze record shows the gap is a purchasing decision, not an oversight.

### 1.6 Rights summary

| Source | Qualifying bytes? | Persistence position | v1.0 status |
|---|---|---|---|
| Twelve Data (Basic) | Yes — candidate captures, private archive only | Storage during active subscription; delete-all within 30 days after end (staff-confirmed); ongoing research analytics require Grow | DEV evidence basis (Tier 1); Tier 4 route needs its own adjudication/tier decision |
| Yahoo | No (diagnostic only) | No grant; D1 destroyed | Not evidence |
| Tiingo | No | Terms HOLD; daily-only held set | Not evidence; deletion decision open (Mike) |
| Coinbase / Kraken / Alpaca | No | No persistence grant (crypto screens) | Parked with the crypto route |
| Databento / Tardis / Intrinio-Zacks | Not acquired | Would grant archival rights | Purchase = Mike's hard gate; not authorized |

**Zero private vendor exposure:** raw vendor bytes exist only in the private `qf-data-archive` repo and local stores. The public scanner repo carries hashes, manifests, schemas, counts and derived/sanitized artifacts only (the -22 source-review packages were sanitized under exactly this rule; the P7b inventory's bar-level content was committed to the private archive only, public side schema/counts only).

---

## 2. Session-table provenance

### 2.1 Adopted calendar of record — 751 sessions

- Artifact: `session_table_751_qualified.json`, calendar_version `XNYS-751-UNION-20261021`, sha256 **`00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f`** (recomputed and matched in this audit — see P11).
- Composition (declared inside the artifact): `XNYS_SESSION_SCHEDULE_V2` (524 sessions, 2024-09-16 → 2026-10-16) ∪ `XNYS_SESSION_SCHEDULE_CANDIDATE_EXTENSION_20261021_81` (227 sessions, 2023-10-19 → 2024-09-15), union adopted 2026-10-21 (Mike's calendar adoption: the 751-session union is the qualified calendar of record; crypto sits on a separately specified continuous calendar and enters no equity session table).
- Range: 2023-10-19 → 2026-10-16; every row carries open 09:30 / close 16:00 or a named early close. The table is the single binning authority for the measurement layer (-29r replaced all +4h arithmetic with table bin-ends; dates outside the table fail closed).

### 2.2 CH-1 — the historical core-hours assumption

- CH-1 was carried as a **disclosed assumption**: that historical NYSE core hours are 09:30–16:00 ET across the table's span (2023 core-hours documentation was initially missing).
- **Resolved:** package -33 (2026-10-19) returned verdict `HISTORICAL_CORE_HOURS_PROVEN` — SEC Release No. 34-103356 (File No. SR-NYSE-2025-21), footnote 42, states NYSE Rule 1.1(d)'s definition of Core Trading Hours as 9:30 a.m.–4:00 p.m. ET in rule text in force across the relevant block (2024-09-16..2025-12-31 addressed directly; -31/-32 packages preserved unedited). CH-1 is therefore recorded in v1.0 as **proven with its evidence cited**, not as a silent assumption; the disclosure stays in the record because the proof post-dates the table's adoption.

### 2.3 Versioned extension through 2027 — 303 sessions

- Artifact: `session_table_extension_2027.json`, calendar_version `XNYS-EXT-2027-20261025`, sha256 **`d2fa788d70f2c8677ca49b9e0201940586c051b9227f815b8d2da55b1e5d3a2f`** (recomputed and matched in this audit), delivered by -30 (commit `d077532`). The base table is byte-untouched by the extension.
- Construction (explicit, `build_session_extension.py`): weekdays in 2026-10-19 → 2027-12-31 minus 12 named, dated NYSE closures (incl. Good Friday 2027-03-26 and the observed Juneteenth / Independence Day / Christmas closures); close 13:00 on the 3 named early closes (2026-11-27, 2026-12-24, 2027-11-26), 16:00 otherwise. Sources: NYSE Group press release 2025-12-23 (2026–2028 holiday/early-closing calendar) and the NYSE Holiday Closures PDF, read 2026-10-25.
- Qualification cross-checks (recorded in the artifact, re-run by the -30 verifier): **X1** the same construction with historical closure lists reproduces the adopted 751 table exactly, including its one ad-hoc closure (2025-01-09, national mourning); **X2** exchange_calendars 4.13.2 XNYS agrees on all 256 sessions inside its coverage; **X3** published counts (251 sessions in 2027; 52 in the 2026 tail; exactly 3 early closes); **X4** continuity and disjointness at the seam.
- **Disclosure:** exchange_calendars' precomputed coverage ends 2027-10-25, so the 2027-10-26 → 12-31 tail rests on the NYSE lists + X1/X3, not on the library cross-check. Dates past 2027-12-31 fail closed by design; any further extension is a new versioned artifact.

### 2.4 Union loader

`load_union_table()` (-30 successor `session_bins.py`): 1,054 sessions, 2023-10-19 → 2027-12-31; duplicate dates across the two artifacts are refused; the telemetry layer resolves all bins through the union. This union is the session basis pinned for v1.0 (P11).

---

## 3. Split / dividend adjustment handling

1. **One basis per comparison, never mixed** — the standing acquisition rule (TD adapter preflight, 2026-10-13, item P7). Acquisition legs on Twelve Data are **`adjust=splits`** (the endpoint's default; the parameter domain is all / splits / dividends / none). On the splits basis, prices are split-adjusted and **dividend drops remain in prices** — verified behaviourally in the preflight's ADJ windows: NVDA across the 2024-06-10 split and TSLA across the 2022-08-25 split (split-adjusted start dates), AAPL across a dividend window (the dividend drop stays in the series, comparator pulled on the same basis). No corporate-action endpoint is in any manifest, and none may be added without entitlement evidence named in advance.
2. **DEV evidence basis.** The -13 DEV run and everything downstream of it (ledgers, measurement packages, EXP-14B) ran on the Oct 23 Twelve Data captures taken under that manifest discipline — splits-adjusted, dividends unadjusted. Every DEV figure in the preregistration is on this single basis.
3. **Yahoo basis kept separate.** Yahoo acquisition policy in the record is `auto_adjust=False` with a frozen split-exclusion protocol — a different adjustment basis from the TD splits-adjusted bytes. The two bases are never mixed in one comparison, and no frozen pin in v1.0 derives from Yahoo bytes (§1.2).
4. **What the strategy model does not do (§8):** financing, borrow, **dividends** and taxes are not modelled; no dividend adjustment is applied anywhere in the frozen pipeline, and TP1/stop/ATR arithmetic runs on the splits-adjusted series as captured. The benchmark (SPY daily) follows the same captured basis under the P3 as-of rule (bars stamped at session completion 16:00 ET; selection at 09:30/13:30 on day D uses D−1's completed session).
5. **Restatement discipline (§8 two-stage rule):** the per-fill cost restatement (§8) is a new ledger version with its own hashes; it changes cost accounting only — it does not re-adjust prices, and no parity claim crosses between the frozen-convention and restated versions.

---

## 4. Audit conclusions

1. **Rights:** exactly one source (Twelve Data) has produced qualifying bytes, and its governing staff terms bound the program to: private storage during an active subscription, a delete-all duty within 30 days after the subscription ends, Grow as the minimum tier for ongoing research analytics / continuous archive-replay, and raw bytes never leaving the private environment. The v1.0 freeze is consistent with those bounds for Tier 1 (existing DEV evidence); **no Tier 4 collection route is rights-qualified yet** — that remains a separate adjudication (and, on the TD route, a tier decision at Mike's desk).
2. **Sessions:** the 751-session adopted table + versioned 303-session extension (union 1,054) are fully provenanced, hash-pinned, and cross-checked (X1–X4); CH-1 is proven, with the proof's provenance disclosed.
3. **Adjustments:** a single declared basis (TD `adjust=splits`; dividends unadjusted and unmodelled) covers all frozen evidence; the Yahoo basis is segregated and carries no frozen pin.

— Muse (production lane; independent review: ChatGPT, checklist C2)
