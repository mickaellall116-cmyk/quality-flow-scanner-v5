# GATE 1 — CALENDAR ADOPTION (task -87)

**Status: PROPOSED — not adopted.** Adoption requires Mike's GO in
the exact form at §5. Dependency position: first of three gates.

## 1. PROPOSED RULING (freeze text, ready to sign)

> **CALENDAR ADOPTION — CORRECTED BASELINE (Gate 1).**
> (1) The artifact `XNYS_SESSION_SCHEDULE_CANDIDATE_EXTENSION_20261021_81.json`
> (sha256 `8d659dde9ccb51b9d86d6c45759abceb6ccd90ad7fa49e7478b13c2dc153a0a2`,
> 227 sessions, coverage 2023-10-19 → 2024-09-15, exactly two 13:00
> early closes: 2023-11-24 and 2024-07-03) is ADOPTED as the qualified
> XNYS session schedule for its coverage window, companion to
> `XNYS_SESSION_SCHEDULE_V2` (sha256
> `3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88`,
> 524 sessions, 2024-09-16 → 2026-10-16). The qualified calendar for
> the corrected baseline is the disjoint union of the two artifacts:
> **751 sessions (744 regular + 7 early-close)**, abutting at
> 2024-09-13 / 2024-09-16 with no overlap and no gap.
> (2) **Disposition CH-1 (carried assumption).** Sessions in the
> extension carry open 09:30 / close 16:00 (13:00 on the two named
> early closes) under the -34 contract's session definition — the
> same convention the qualified -35 artifact embodies. It is
> recorded that **no in-era dated proof of 09:30–16:00 core hours
> for calendar 2023 exists in the record**: the Dec-21-2022 ICE
> release enumerates 2023 closures and early closings but nowhere
> states core hours, and the only core-hours proofs (-33 chain:
> NYSE Rule 1.1(d), SEC filing Jun 2025; RM-24-12 dated 2024-09-13)
> are dated at/after the window and were not back-projected under
> the lane's -32 standard. CH-1 is therefore carried as a DISCLOSED
> ASSUMPTION, named in every readout that uses pre-2024 sessions.
> CH-1 is retired by any one of: (a) an in-era (dated ≤ 2023-12-31)
> NYSE/ICE or SEC document stating 2023 core hours; (b) a pre-2024
> archived capture of the NYSE hours page; (c) a qualified vendor
> session-metadata attestation for 2023. If evidence CONTRADICTING
> CH-1 appears, every readout using 2023 sessions enters the -86 A4
> invalidation registry and is marked INVALIDATED pending
> re-derivation. The alternative to this clause is HOLD (do not
> adopt until retiring evidence exists); HOLD is named here and NOT
> recommended — the closure/early-close enumeration (the
> classification the constructor actually consumes) is fully
> evidenced in-era, and no in-era core-hours source is known to
> exist, so HOLD parks the holdout window indefinitely over the one
> fact the -35 era proves by unbroken continuity on both sides.
> (3) **Crypto continuous calendar.** For the 7 UX51 crypto pairs
> (BTC-USD, ETH-USD, SOL-USD, DOGE-USD, AVAX-USD, LINK-USD,
> XRP-USD), the calendar contract is specification **S-C1…S-C6**
> (§4 below), adopted as the Option A calendar contract per the
> universe freeze (commit `2705c02`). Crypto bars never enter the
> XNYS session constructor.
> (4) This adoption changes no other pin, verdict, or gate. It does
> not authorize any capture, vendor call, or run.

## 2. Evidence (every claim pinned)

| Claim | Evidence |
|---|---|
| Candidate artifact + hash | `research_notes/nyse_calendar_2023_evidence_20261021_81/XNYS_SESSION_SCHEDULE_CANDIDATE_EXTENSION_20261021_81.json`, package commit `9c59ea1`; sha256 `8d659dde…` recomputed in fixture V1 |
| Source instrument | NYSE Group/ICE release Dec 21, 2022 (in-era, prospective); HTML sha `4323bad7…`, PDF sha `8092099c…`; archived `qf-data-archive` commit `58ad260`, re-fetch verified 5/5 (-81 CAPTURE_MEMO) |
| Full-window coverage | -81 REAUDIT_MEMO + REAUDIT_RESULT.json: Segment A 50 sessions, Segment B 177, total 227; no indeterminate date |
| Segment B basis | Pinned Nov-10-2023 ICE release 2024 column (closures 01-01, 01-15, 02-19, 03-29, 05-27, 06-19, 07-04, 09-02; early close 2024-07-03), corroborated identically by the -81 artifact's 2024 column |
| -35 qualified artifact | `XNYS_SESSION_SCHEDULE_V2.json`, sha `3358f2d9…`, 524 sessions, -35 r2 (commit `9c62e25`), parity 48/48 |
| Union arithmetic | Fixture V7/V7b (this package): disjoint, abutting, union = 751; early closes total 7 (2 extension + 5 in V2 span: 2024-11-29, 2024-12-24, 2025-07-03, 2025-11-28, 2025-12-24) — matches the -85 plan's 744 + 7 |
| Core-hours sub-gap | -81 REAUDIT_MEMO §"Core-hours sub-gap": REMAINS OPEN; -33 chain dated at/after window |
| Independent verification | `fixtures/verify_calendar_candidate.py` — regenerates the session list from weekday enumeration minus the instruments' closure sets and compares byte-set equality with the candidate (V3), plus shape/boundary/segment checks: **13/13 PASS** (`fixtures/output_verify_calendar_candidate.txt`) |
| Crypto spec behavior | `fixtures/crypto_calendar_spec.py` + `test_crypto_calendar_spec.py`: **8/8 PASS** (`fixtures/output_test_crypto_calendar_spec.txt`) |
| Constructor isolation basis | `construct_4h` (pin `d47e8df1…`, `research_notes/pilot_harness/construct_4h.py`): session bins [09:30, 13:30) / [13:30, close), early-close single [09:30, 13:00) bin; v2 R3a — raises on unknown/closed dates, no 16:00 fallback |

## 3. Unresolved risks (stated plainly)

- **CH-1 is an assumption, not evidence.** If 2023 core hours differed
  on any date (no indication they did), 1h→4H construction for that
  date would be wrong and readouts would need A4 invalidation. The
  risk is accepted knowingly under the ruling, or not at all (HOLD).
- **Crypto bar-stamp phase is UNCONFIRMED.** The record pins bar-open
  stamps for the equity track (-63 F4); no captured crypto bar exists
  yet. The spec is phase-tolerant for session totals and anchors, but
  WHICH overnight bin absorbs a DST hour is phase-dependent (S-C3),
  and the [09:30, 10:00) attribution limitation (spec docstring)
  applies at :00 phase. The capture manifest must pin the phase from
  the pilot bytes before Phase-1.
- **Crypto vendor coverage is untested.** No crypto capture has ever
  run; per-symbol availability/depth on Twelve Data is unknown until
  the -85 pilot. The calendar contract does not depend on it, but the
  capture plan's ≈42-request crypto estimate does.
- **Cross-calendar portfolio semantics are NOT frozen by this gate.**
  ChatGPT's Option A ruling (Slack TS 1792629597.038219) requires
  explicit cross-calendar signal alignment, benchmark, exposure/
  ranking, and risk-cap semantics before any combined baseline. This
  gate freezes the calendar layer those semantics must respect —
  alignment at bin-start labels 09:30/13:30 ET only (S-C6); SPY
  remains the equity track's benchmark artifact; crypto has no
  session benchmark. The portfolio-semantics freeze itself belongs
  to the R1–R5 + A1–A4 package (-86 F2, GO G2-extended) and must
  land before any combined run. Nothing in this gate should be read
  as freezing them by implication.

## 4. The crypto continuous-calendar specification (S-C1…S-C6)

Full text lives in the reference implementation's docstring
(`fixtures/crypto_calendar_spec.py`), which is the specification;
the tests are its executable reading. Summary:

- **S-C1 Session:** one America/New_York calendar date; EVERY date
  is a session (24/7) — no closures, no early closes. The holdout
  span alone is 333 crypto session dates vs 227 XNYS sessions.
- **S-C2 Bins:** six 4H bins per session, ET wall-clock starts 09:30,
  13:30, 17:30, 21:30 (on D) and 01:30, 05:30 (on D+1); the session
  spans [D 09:30 ET, D+1 09:30 ET). Bin 0 opens at the XNYS open and
  bin 1 at the XNYS second-bin open on every date of the year.
- **S-C3 Assignment:** a bar belongs to the bin containing its
  bar-open instant (half-open wall-clock intervals). DST sessions
  total 23 (spring) / 25 (fall) hourly bars; exactly one overnight
  bin deviates from 4 constituents; daytime bins 0/1 always hold 4;
  the absorbing bin is stamp-phase-dependent (disclosed in S-C3).
- **S-C4 Labels:** bins labeled by ET wall-clock start (date, HH:MM),
  matching the equity constructor's label-by-open convention.
- **S-C5 Isolation:** crypto bars never enter `construct_4h` (it
  raises on non-session dates by design); crypto construction is a
  separate path; the calendars meet only at portfolio joins.
- **S-C6 Alignment:** joins key on bin-START labels (09:30 / 13:30
  ET), never bin closes (equity bin 1 closes 16:00 / 13:00; crypto
  bin 1 runs to 17:30). Crypto has no DST of its own — ET anchoring
  imports ET's DST, so both tracks' anchor instants shift together
  and never drift apart at the anchors.

## 5. Minimal tests + the GO

Executed (this package): calendar verification **13/13** (pin,
regeneration set-equality, early-close exactness, boundary abutment,
751 union, segment counts, no-Dec-2023-early-close); crypto spec
**8/8** (normal/DST session shapes, phase-invariance of totals,
anchor alignment in EST and EDT, 333-date span, XNYS isolation).
SPECIFIED_NOT_RUN: none for this gate. (Construction of real crypto
bars is capture-stage work, not a calendar-adoption test.)

> **GO — Gate 1:** "Adopt the -81 candidate extension (sha256
> 8d659dde…) as the qualified companion to XNYS_SESSION_SCHEDULE_V2,
> with core-hours assumption CH-1 carried and disclosed, and adopt
> the crypto continuous-calendar specification S-C1…S-C6 as the
> Option A calendar contract." — This GO adopts calendars only.
