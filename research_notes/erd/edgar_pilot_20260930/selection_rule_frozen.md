# EDGAR 10-event feasibility pilot — PROSPECTIVE SELECTION RULE

**Written BEFORE any draw or EDGAR pull. 2026-09-30.**
**Authority:** Mike-authorized, ChatGPT-gated pilot (relayed 2026-09-30 ~16:33 ET).
**Purpose:** test whether SEC EDGAR Item 2.02 8-Ks + Exhibit 99.1 press releases contain EXPLICIT
announcement/release datetimes sufficient for the frozen BTO/DTM/AMC bucket classification —
EDGAR as immutable evidence container, NOT as announcement clock (per ChatGPT HOLD ruling).

## Pilot frame (labeled proxy, not the frozen universe)

The frozen ERD §4.2 universe is a mechanical quarterly rule (U.S. common stocks, ≥$5 close,
20-session median dollar volume ≥$5M, PIT-reconstituted) — not an enumerable fixed list. For this
10-event feasibility pilot only, the frame is fixed prospectively as the 30 Dow Jones Industrial
Average components enumerated from dow-jones-djia.com May-2026 component tables (a fixed public
list, documented here):

AAPL, AMGN, AMZN, AXP, BA, CAT, CRM, CSCO, CVX, DIS, GS, HD, HON, IBM, JNJ, JPM, KO, MCD, MMM,
MRK, MSFT, NKE, NVDA, PG, SHW, TRV, UNH, V, VZ, WMT

All 30 are U.S. primary-listed common operating companies and continuous SEC filers across the
full 2012–2025 window (no eligibility gaps; §7 security-type exclusions do not apply to any of
them). **Large-cap caveat:** all 30 are mega-cap names with professional IR operations; exhibit
format quality here is a best case and may overstate feasibility for the broader §4.2 universe.
This caveat is carried into the final report.

## Event definition

For a drawn (ticker, calendar quarter Q of year Y): the event is the company's regular quarterly
earnings release announced during calendar quarter Q of year Y. Identification rule: the
chronologically FIRST 8-K with Item 2.02 filed during calendar quarter Q of year Y
(filingDate in [Q-start, Q-end]). Tie-break (prospective): if two Item 2.02 8-Ks fall in the same
quarter, take the earlier filed; if none, the draw is recorded as NO-FILING (stays in denominator
as UNVERIFIABLE — no redraw). Expected to never trigger for these names.

## Draw mechanics (fixed, seeded, no human choice)

- RNG: Python `random.Random(20260930)`, single stream, no reseeding.
- `years = rng.sample(range(2012, 2026), 10)` → 10 distinct years, draw order preserved.
- For each year in draw order: `ticker = rng.choice(sorted(frame))`, `q = rng.choice([1,2,3,4])`.
- Fixed denominator 10. No redraws, no replacements, no cherry-picking — mirroring frozen §1.5.

## Scoring (ChatGPT revised design, strict)

- **CLEAN** iff the contemporaneous 8-K and/or Exhibit 99.1 establishes an EXPLICIT
  announcement/release datetime — date + time-of-day, timezone determinable from the source itself —
  sufficient to classify BTO/DTM/AMC under Amendment 1 §1 (that day's actual NYSE open/close;
  during-session → EXCLUDE; exactly at close → EXCLUDE).
- **UNVERIFIABLE** otherwise: date-only, no time, timezone indeterminable, exhibit missing or
  unretrievable, conflicting times unresolvable by the frozen rule.
- The SEC **accepted datetime is recorded as metadata only** (evidence container) and is NEVER used
  as the announcement clock. No inference, no guessing, no replacement events.
- Per frozen item05 rule 5: if the source timezone cannot be determined from the source itself →
  AMBIGUOUS/FAIL (= UNVERIFIABLE here).
