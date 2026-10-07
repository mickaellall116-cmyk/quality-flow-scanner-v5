# Resampler Grid Mechanism — Corrected (2026-10-07)

**Supersedes the mechanism in** `RESAMPLER_XNYS_EVIDENCE.md` §2 ("Why they
differ"), per ChatGPT amendment 6028744990.
**Fixture:** `resampler_grid_fixture.py` (all assertions pass; synthetic
tz-aware 1H data, no market-data download, unchanged legacy
`resample_closed_4h`).

## The correction

The 2026-10-06 document claimed the two label sets differed because "the live
download window started on a different date, so the UTC-midnight anchor fell on
a different phase." ChatGPT correctly objected: with `origin='start_day'`,
merely changing the first date **cannot** shift a 4-hour grid phase — one day
is six 4-hour periods, so a UTC-midnight anchor is date-invariant. That
objection is valid **for a UTC anchor**. The error in the old document was
assuming the anchor is midnight UTC. It is not.

## The real mechanism (with exact evidence)

pandas `origin='start_day'` anchors to **midnight in the index's timezone**,
not midnight UTC. The 1H input from `yf.download` is tz-aware
`America/New_York`. Therefore:

| First 1H day's DST regime | `origin='start_day'` (UTC value) | + `offset='9h30min'` | UTC-fixed grid |
|---------------------------|----------------------------------|----------------------|----------------|
| EDT (e.g. 2026-09-15) | 2026-09-15 00:00 EDT = **04:00 UTC** | 13:30 UTC | 13:30/17:30/21:30/01:30/05:30/09:30 UTC |
| EST (e.g. 2026-01-15) | 2026-01-15 00:00 EST = **05:00 UTC** | 14:30 UTC | 14:30/18:30/22:30/02:30/06:30/10:30 UTC |

Midnight EST and midnight EDT differ by **1 hour in UTC**. So the first
date's DST *regime* (not the date itself) shifts the UTC grid phase by 1h.
ChatGPT's "six periods per day" invariance holds *within* a regime (proven by
the fixture: three different EDT first-dates give the identical grid); the
phase step happens only when the anchor crosses the DST boundary.

The grid is then UTC-fixed. Daylight-saving time moves the **ET labels**:

- **SET A — cache (EDT-anchored, 13:30 UTC grid):** in EST, the session bins
  are [13:30,17:30) and [17:30,21:30) UTC = [08:30,12:30) and [12:30,16:30)
  EST → labels **08:30/12:30**. (In EDT the same grid labels 09:30/13:30 —
  correct by luck.) Matches `byte_identity_report.md:82-84` (332 bars at
  13:30/17:30 UTC).
- **SET B — live (EST-anchored, 14:30 UTC grid):** in EDT, the bins fall at
  06:30/10:30/14:30/18:30/22:30/02:30 local. Regular-session 1H data
  (09:30–16:00 ET) lands in **[06:30,10:30)**, [10:30,14:30), [14:30,18:30) →
  labels **06:30/10:30/14:30**, **three bars per day** instead of two. Matches
  the 116 live signal bars in `v54_forward/forward_test.jsonl`.

**Live-window anchor evidence:** `build_affected_cohort_archive.py` documents
that `yf.download(1h, start="2026-01-15")` + unchanged `resample_closed_4h`
reproduces the live 06:30/10:30/14:30 grid **bar-for-bar identical** to the
`period="180d"` live construction (503 overlapping VEEV bars, 2026-10-03).
2026-01-15 is in EST — the EST-anchored case above. (Why `period="180d"`
also anchored in EST is a yfinance window-quirk not further investigated;
the pinned `start="2026-01-15"` reproduction is the verified anchor.)

## What the old document got wrong, precisely

| Old claim | Correction |
|-----------|------------|
| "UTC-midnight anchor fell on a different phase" | Anchor is **ET-midnight**, not UTC-midnight (`scanner_rules.py:128`, pandas 2.1.4 semantics, proven by fixture) |
| "A different first-download date → a different anchor" | A different first-download date **within one DST regime** → identical grid (fixture PASS). Only the regime matters. |
| Implied the docstring proves the mechanism | The docstring (`scanner_rules.py:99-101`) *asserts* the 06:30 outcome but does not derive it. This document derives it from the fixture; the docstring is corroboration, not proof. |

## Boundaries (unchanged)

- The **live 1H input bytes** were not retained; only the derived 4H signal
  bars in `forward_test.jsonl` and the pinned archive construction remain.
  Any claim requiring live 1H byte content is **UNVERIFIABLE**.
- The fixture uses the **current** `scanner_rules.py` Version A
  (`7db282dd…`), byte-identical to the manifest pin. The legacy function is
  frozen; the fixture does not modify it.
- `RESAMPLER_XNYS_EVIDENCE.md` §§1, 3–7 stand as written; only §2's
  mechanism is superseded by this document.
