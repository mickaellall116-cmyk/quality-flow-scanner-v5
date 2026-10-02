# EDGAR 10-Event Feasibility Pilot — Frozen Package

**Package ID:** `edgar-pilot-10event-20260930`
**Sealed:** 2026-09-30 (evening ET)
**Authority:** Mike-authorized pilot; ChatGPT-gated design; Mike's directive 2026-09-30: package the frozen pilot, keep HOLD.
**Status: HOLD — sealed, not parked.**

## 1. What this package is

The 2026-09-30 pilot tested whether contemporaneous SEC EDGAR Item 2.02 8-Ks and/or Exhibit 99.1
press releases contain an EXPLICIT announcement datetime sufficient for the frozen BTO/DTM/AMC
bucket classification — EDGAR as immutable evidence container, NOT as announcement clock
(per ChatGPT's HOLD on the as-written amendment).

The pilot did not fail. Data acquisition failed: SEC's WAF blocked this VM's egress, so 0/10
events could be scored. The verdict is **UNDETERMINED** — there is no evidence for or against
the hypothesis, and nothing in the pilot supports or undermines the revised design.

This package freezes everything a future runner needs to execute the retrieval + scoring run
from an unblocked network. **The runner may only retrieve and score. They must not reinterpret
the sample: no redraws, no replacements, no substitutions, no cherry-picking.**

## 2. The ten frozen events

| Event ID | # | Ticker | CIK | Drawn window (calendar) |
|---|---|---|---|---|
| EDGAR-PILOT-01 | 1 | MMM | 66740 | 2019-07-01 → 2019-09-30 |
| EDGAR-PILOT-02 | 2 | JNJ | 200406 | 2018-10-01 → 2018-12-31 |
| EDGAR-PILOT-03 | 3 | AAPL | 320193 | 2022-01-01 → 2022-03-31 |
| EDGAR-PILOT-04 | 4 | JPM | 19617 | 2015-01-01 → 2015-03-31 |
| EDGAR-PILOT-05 | 5 | CAT | 18230 | 2016-07-01 → 2016-09-30 |
| EDGAR-PILOT-06 | 6 | AMZN | 1018724 | 2020-10-01 → 2020-12-31 |
| EDGAR-PILOT-07 | 7 | NKE | 320187 | 2024-07-01 → 2024-09-30 |
| EDGAR-PILOT-08 | 8 | TRV | 86312 | 2025-01-01 → 2025-03-31 |
| EDGAR-PILOT-09 | 9 | TRV | 86312 | 2012-10-01 → 2012-12-31 |
| EDGAR-PILOT-10 | 10 | VZ | 732712 | 2017-01-01 → 2017-03-31 |

Machine-readable copy: `events.json`. Draw order preserved. Fixed denominator 10.

## 3. Frozen selection seed and rule

- **Seed:** `20260930`. RNG: Python `random.Random(20260930)`, single stream, no reseeding.
- **Draw:** 10 distinct years via `rng.sample(range(2012, 2026), 10)`, draw order preserved.
  Per year in draw order: `ticker = rng.choice(sorted(30-name frame))`,
  `quarter = rng.choice([1, 2, 3, 4])`.
- **Frame (pilot-only labeled proxy):** AAPL, AMGN, AMZN, AXP, BA, CAT, CRM, CSCO, CVX, DIS,
  GS, HD, HON, IBM, JNJ, JPM, KO, MCD, MMM, MRK, MSFT, NKE, NVDA, PG, SHW, TRV, UNH, V, VZ, WMT
  (Dow components from dow-jones-djia.com May-2026 tables). Large-cap caveat: mega-cap IR
  operations are a best case; exhibit quality may overstate feasibility for the broader universe.
- **Event definition (frozen):** the chronologically FIRST 8-K with Item 2.02 filed during the
  drawn calendar quarter (filingDate within [window_start, window_end]). Tie-break: earlier
  filed wins. If none: record NO-FILING — stays in the denominator as UNVERIFIABLE, no redraw.
- Full prospective text (written before any draw or pull): `selection_rule_frozen.md`.

## 4. Required SEC fields (retrieval checklist per event)

1. CIK directory listing `https://www.sec.gov/Archives/edgar/data/{CIK}/` — accession numbers
   with last-modified dates.
2. Candidate accessions with last-modified inside the drawn window (inclusive).
3. Each candidate's filing index (`{...}/{accession}/index.json` or index.htm) — form type,
   document filenames, items reported.
4. The selected 8-K document (first 8-K containing Item 2.02 in the window).
5. Its Exhibit 99.1 press release (filename from the filing index exhibit table; if several
   99.x exhibits exist, use the one referenced by the Item 2.02 disclosure and record the name).
6. SEC accepted datetime (from the filing index) — **metadata only, never the announcement clock**.

## 5. Accession / document-selection rules

1. Enumerate accessions with last-modified in the drawn window.
2. Open each accession's filing index in chronological last-modified order.
3. Select the first whose form type is 8-K AND whose reported items include 2.02.
4. Open its Exhibit 99.1.
5. **Prohibited:** substituting a newswire or IR-site copy for the filed exhibit; using the SEC
   accepted datetime as the announcement time; redrawing or replacing any event; scoring from
   memory or inference.

## 6. Extraction rules

From the 8-K and/or Exhibit 99.1, extract:

- **Announcement datetime:** explicit date + time-of-day, with the timezone determinable from
  the source itself (dateline, explicit tz stamp, wire header). Record a verbatim quote.
- **Fiscal identity:** the fiscal period the earnings cover, as stated in the filing/exhibit
  (e.g. "FY2019 Q3, quarter ended 2019-09-30").
- **SEC accepted datetime:** metadata only.

**Scoring (frozen):**

- **CLEAN** iff the 8-K and/or Exhibit 99.1 establishes an explicit announcement datetime
  sufficient to classify BTO/DTM/AMC under Amendment 1 §1 (that day's actual NYSE open/close;
  during-session → EXCLUDE; exactly at close → EXCLUDE).
- **UNVERIFIABLE** otherwise: date-only, no time, timezone indeterminable from the source,
  exhibit missing or unretrievable, unresolvable conflicts.
- Per frozen item05 rule 5: timezone not determinable from the source → AMBIGUOUS/FAIL
  (= UNVERIFIABLE here).
- No inference, no guessing.

## 7. Fiscal-quarter identity wording (RESOLVED per Mike, 2026-09-30)

Mike's approved rule:

- **Fiscal quarter = the accounting identity** — which earnings report it is
  (e.g. "FY2026 Q1 identifies which earnings report it is").
- **Announcement timestamp = the market-event identity** — when the information reached
  the market.
- **Calendar quarter = derived metadata only**, not the event anchor.

**How this applies to this pilot (no reinterpretation):** the wording governs IDENTIFICATION
and REPORTING, not selection. The runner still selects the chronologically first Item 2.02
8-K in the drawn calendar window (§5). The fiscal identity is then read from that filing and
reported as the accounting identity; the announcement timestamp from the filing/exhibit is
the market-event identity; the drawn calendar window is recorded as derived metadata.
The runner must NOT substitute a different filing on fiscal-quarter grounds.

**Worked boundary case — EDGAR-PILOT-07 (NKE, window 2024-07-01 → 2024-09-30):** NKE's
fiscal Q4 FY2024 release was announced 2024-06-27 (before the window) and its fiscal Q1
FY2025 release on 2024-10-01 (after the window). EXPECTED outcome: NO-FILING →
UNVERIFIABLE — to be CONFIRMED from the accession list, not pre-scored here. The adjacent
releases must not be substituted; that would be reinterpreting the sample.

**Carried forward (not decided here):** for the future 50-event formal amendment, consider
anchoring the draw on fiscal quarters. The 10 pilot events stand as drawn regardless.

## 8. Expected output schema

`output_schema.json` (JSON Schema, draft 2020-12). One object per event with `selection`,
`extraction`, `score`, `score_rationale`, plus a `summary` (clean / unverifiable / scorable /
feasibility_rate) and an overall `verdict`. The runner records the package manifest hash they
used.

## 9. Runner constraints

- Reuse this package unchanged. Retrieve and score only.
- Polite SEC access: descriptive research User-Agent, ≤10 requests/second.
- If SEC access is blocked from the runner's environment: report UNDETERMINED with the access
  evidence (endpoints tried, response codes). Do NOT score from proxies or memory.
- No amendment drafting, no ERD performance data, no changes to any frozen artifact
  (V5.4, ERD v0.1, F7, canonical). Read-only with respect to the research record.

## 10. Hashes

SHA-256 manifest: `MANIFEST.sha256` (this package's files plus the three 2026-09-30 source
files it was built from). Verify before running: `sha256sum -c MANIFEST.sha256`.
