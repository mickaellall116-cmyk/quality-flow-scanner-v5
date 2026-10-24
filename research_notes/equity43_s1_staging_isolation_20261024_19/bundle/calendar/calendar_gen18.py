#!/usr/bin/env python3
"""QF-EQUITY43-S1-CALENDAR-EXTENSION-20261024-18 — deterministic XNYS
session generator (research-only candidate).

Pure-stdlib rule implementation of the NYSE (XNYS) session calendar:
no calendar library, no network, no runtime dependency beyond the
Python standard library and the pinned system tzdata (used only by
the verification layer for UTC-instant proofs, never by generation).

Generation is date-rule arithmetic only:
  * sessions are Monday..Friday dates not in the holiday set;
  * regular close 16:00 ET, early close 13:00 ET on the early-close set;
  * open is always 09:30 ET.

Holiday rules (closure date = observed date):
  New Year's Day   Jan 1; Sun -> Mon Jan 2. NYSE EXCEPTION: when Jan 1
                   falls on a Saturday there is NO Friday Dec 31
                   observance — Dec 31 remains a regular session
                   (NYSE practice, e.g. Fri 2021-12-31 was a full
                   session; both pinned library calendars agree —
                   caught by the -18 three-way cross-check on
                   2027-12-31, where the generic federal observance
                   rule used in r1 of this generator was wrong).
  MLK Day          3rd Monday of January
  Presidents Day   3rd Monday of February
  Good Friday      Friday before Easter Sunday (Gregorian computus)
  Memorial Day     last Monday of May
  Juneteenth       Jun 19; Sat -> Fri Jun 18, Sun -> Mon Jun 20
  Independence Day Jul 4; Sat -> Fri Jul 3, Sun -> Mon Jul 5
  Labor Day        1st Monday of September
  Thanksgiving     4th Thursday of November
  Christmas Day    Dec 25; Sat -> Fri Dec 24, Sun -> Mon Dec 26

Early-close rules (13:00 ET):
  * the Friday after Thanksgiving;
  * Jul 3 when it is a session day and Jul 4 falls Tue..Fri
    (Jul 4 Sat -> Jul 3 is the observed holiday; Jul 4 Sun -> Jul 3 is
    a Saturday and Jul 2 Fri is a REGULAR session);
  * Dec 24 when it is a session day and Dec 25 falls Tue..Fri
    (Dec 25 Sat -> Dec 24 is the observed holiday; Dec 25 Sun ->
    Dec 26 is the observed holiday and Dec 23 Fri is regular;
    Dec 25 Mon -> Dec 24 is a Sunday).

Emergency / unscheduled closures are NOT guessed: dates outside the
qualified range that are not produced by these rules fail closed in
the consumer (unknown session -> rejection), per the task contract.
The single historical special closure inside the qualified range is
encoded explicitly in SPECIAL_CLOSURES as a named fact of record (it
is present in the pinned adopted table and in both pinned library
calendars); no future special closure is or can be encoded.
"""
import json
from datetime import date, timedelta

OPEN = "09:30"
CLOSE_REGULAR = "16:00"
CLOSE_EARLY = "13:00"


def _nth_weekday(year, month, weekday, n):
    """n-th (1-based) weekday (Mon=0) of the month."""
    d = date(year, month, 1)
    delta = (weekday - d.weekday()) % 7
    return d + timedelta(days=delta + 7 * (n - 1))


def _last_weekday(year, month, weekday):
    if month == 12:
        d = date(year, 12, 31)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _easter(year):
    """Gregorian computus (Anonymous Gregorian algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def _observed(d):
    """Weekend-observance shift: Sat -> Fri before, Sun -> Mon after."""
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def _new_years_observed(year):
    """NYSE New Year's Day observance: Sun Jan 1 -> Mon Jan 2; Sat
    Jan 1 -> NO weekday observance (Dec 31 stays a session)."""
    d = date(year, 1, 1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d  # Mon..Fri: the day itself; Sat: itself (not a session)


def holidays(year):
    """All XNYS closure dates whose observance falls in `year`."""
    out = set()
    out.add(_new_years_observed(year))
    out.add(_new_years_observed(year + 1))
    out.add(_nth_weekday(year, 1, 0, 3))          # MLK
    out.add(_nth_weekday(year, 2, 0, 3))          # Presidents
    out.add(_easter(year) - timedelta(days=2))    # Good Friday
    out.add(_last_weekday(year, 5, 0))            # Memorial
    out.add(_observed(date(year, 6, 19)))         # Juneteenth
    out.add(_observed(date(year, 7, 4)))          # Independence
    out.add(_nth_weekday(year, 9, 0, 1))          # Labor
    out.add(_nth_weekday(year, 11, 3, 4))         # Thanksgiving
    out.add(_observed(date(year, 12, 25)))        # Christmas
    return {d for d in out if d.year == year}


def early_closes(year):
    """All 13:00-ET early-close dates in `year`."""
    out = set()
    out.add(_nth_weekday(year, 11, 3, 4) + timedelta(days=1))  # Fri after Thxg
    jul4 = date(year, 7, 4)
    if jul4.weekday() in (1, 2, 3, 4):            # Tue..Fri
        out.add(date(year, 7, 3))
    dec25 = date(year, 12, 25)
    if dec25.weekday() in (1, 2, 3, 4):           # Tue..Fri
        out.add(date(year, 12, 24))
    return out


# Historical special closures inside the qualified range (facts of
# record, present in the pinned adopted table): 2025-01-09 — NYSE
# closed for the national day of mourning for President Jimmy Carter.
SPECIAL_CLOSURES = {date(2025, 1, 9)}


def generate(start, end):
    """Session rows [{date, open, close}] for start <= d <= end."""
    rows = []
    hol = set(SPECIAL_CLOSURES)
    ec = set()
    for y in range(start.year - 1, end.year + 2):
        hol |= holidays(y)
        ec |= early_closes(y)
    d = start
    while d <= end:
        if d.weekday() < 5 and d not in hol:
            rows.append({"date": d.isoformat(), "open": OPEN,
                         "close": CLOSE_EARLY if d in ec else CLOSE_REGULAR})
        d += timedelta(days=1)
    return rows


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = generate(date.fromisoformat(a.start), date.fromisoformat(a.end))
    dates = [r["date"] for r in rows]
    assert dates == sorted(dates) and len(set(dates)) == len(dates)
    blob = (json.dumps(rows, separators=(",", ":"), ensure_ascii=True)
            + "\n").encode("utf-8")
    with open(a.out, "wb") as f:
        f.write(blob)
    print(f"generator=calendar_gen18 window={a.start}..{a.end} "
          f"sessions={len(rows)}")


if __name__ == "__main__":
    main()
