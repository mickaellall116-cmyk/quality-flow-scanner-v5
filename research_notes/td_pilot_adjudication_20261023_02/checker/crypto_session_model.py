#!/usr/bin/env python3
"""
crypto_session_model.py — task -94: source-faithful session model
for the UX51 crypto continuous calendar, implementing the ADOPTED
S-C1…S-C6 spec (Gate 1, three-gate freeze a126ce5; reference
implementation -87 fixtures/crypto_calendar_spec.py, commit 186aa0a).

This module exists because checker v3 (task -93) encoded a
DIFFERENT, midnight-anchored crypto session ([00:00 ET, 24:00 ET),
24 hardcoded hourly starts). ChatGPT's -94 review (Issue #1
comment 6353306848) held that candidate for crypto: the adopted
session is [D 09:30 ET, D+1 09:30 ET), and its DST behavior follows
from that anchor — 23 elapsed 1h bars across the spring transition,
25 across the fall transition, 24 ordinarily.

Rules implemented (S-C1/S-C2/S-C3, restated from the adopted spec):
  SESSION  — a crypto session is one America/New_York calendar
             date D; every date is a session (24/7 market). The
             session SPANS the half-open interval of absolute time
             [D 09:30 ET, D+1 09:30 ET).
  BARS     — expected hourly bar-open instants are the UTC instants
             start + k*1h for k = 0..N-1 inside the span, where
             N = elapsed hours of the span: 23 on the session whose
             overnight contains the spring-forward transition
             (e.g. D = 2024-03-09), 25 on the fall-back session
             (e.g. D = 2024-11-02), 24 otherwise. The duplicated
             fall wall hour (01:00 EST vs 01:00 EDT) is TWO distinct
             UTC instants, not a duplicate timestamp; the spring
             nonexistent wall hour (02:00 ET on transition night)
             is not a bar and not a missing bar.
  ASSIGN   — a bar-open instant belongs to session D iff, in ET
             wall time, it is >= 09:30 on D or < 09:30 on D+1
             (S-C3: assignment is computed on ET wall time; this is
             equivalent to the half-open UTC span test and both are
             asserted in the test suite).

Stdlib only (zoneinfo). Offline. No vendor data, no captures.
"""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
SESSION_OPEN = time(9, 30)


def session_span_utc(session_date: date):
    """[start, end) UTC instants of session `session_date` (S-C2)."""
    start_local = datetime.combine(session_date, SESSION_OPEN, tzinfo=NY)
    end_local = datetime.combine(session_date + timedelta(days=1),
                                 SESSION_OPEN, tzinfo=NY)
    return start_local.astimezone(timezone.utc), \
        end_local.astimezone(timezone.utc)


def expected_bar_count(session_date: date) -> int:
    """Elapsed 1h bars in the session span: 23 / 24 / 25."""
    start, end = session_span_utc(session_date)
    return int((end - start) / timedelta(hours=1))


def expected_bar_instants_utc(session_date: date):
    """Ordered UTC instants of the session's expected 1h bar opens."""
    start, end = session_span_utc(session_date)
    out = []
    t = start
    while t < end:
        out.append(t)
        t += timedelta(hours=1)
    return out


def session_date_of_instant(instant_utc: datetime) -> date:
    """Session date owning a bar-open instant (S-C3, ET wall time)."""
    local = instant_utc.astimezone(NY)
    if local.time() >= SESSION_OPEN:
        return local.date()
    return local.date() - timedelta(days=1)
