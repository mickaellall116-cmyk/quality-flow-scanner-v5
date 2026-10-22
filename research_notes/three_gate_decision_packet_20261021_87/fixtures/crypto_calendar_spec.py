#!/usr/bin/env python3
"""
crypto_calendar_spec.py — Gate 1 (task -87) PROPOSED reference
implementation of the UX51 crypto continuous calendar, per Mike's
Option A ruling (freeze commit 2705c02): the 7 crypto pairs
(BTC-USD, ETH-USD, SOL-USD, DOGE-USD, AVAX-USD, LINK-USD, XRP-USD)
run on a separately specified continuous calendar. THIS IS A SPEC
CANDIDATE — not adopted, not integrated; adoption is Gate 1's GO.

SPEC (the rules this module implements, stated so the fixture tests
are readable as the specification):

  S-C1 SESSION. A crypto "session" is one America/New_York calendar
       date. EVERY date is a session (24/7 market): no closures, no
       early closes, no weekends off.
  S-C2 BINS. Each session date D carries six 4H bins whose ET
       wall-clock starts are 09:30, 13:30, 17:30, 21:30 on D and
       01:30, 05:30 on D+1. The session spans [D 09:30 ET, D+1 09:30
       ET). Bin 0 therefore opens at exactly the XNYS session open
       and bin 1 at exactly the XNYS second-bin open (13:30 ET) on
       every date, in both EST and EDT.
  S-C3 ASSIGNMENT. An hourly bar belongs to the bin containing its
       bar-open instant. Bins are half-open wall-clock intervals;
       assignment is computed on ET wall time, so the two DST
       transition sessions absorb the missing/repeated hour in an
       overnight bin: a spring-forward session has 23 hourly bars,
       a fall-back session 25, and in each case exactly ONE overnight
       bin deviates from 4 constituents (3 resp. 5) while the
       daytime bins 0 and 1 always hold exactly 4. WHICH overnight
       bin absorbs the hour depends on the vendor's bar-stamp phase:
       with :30-phase stamps (the phase the equity track's bars
       carry, -63 F4) the [01:30, 05:30) bin absorbs it in both
       transitions; with :00-phase stamps the fall-back repeat lands
       in [21:30, 01:30) instead. The capture manifest must pin the
       phase (see KNOWN LIMITATION); the session totals and the
       09:30/13:30 anchors are phase-invariant.
  S-C4 LABELS. A bin is labeled by its ET wall-clock start
       (date, "HH:MM") on the session date for bins 0-3 and on D+1
       for bins 4-5, matching the equity constructor's convention of
       labeling a bin by its opening wall time (09:30 / 13:30).
  S-C5 ISOLATION. Crypto bars NEVER enter the XNYS session
       constructor (construct_4h, pin d47e8df1...): that constructor
       raises on non-session dates by design (v2 R3a), and crypto
       bars exist on every date. Crypto construction is a separate
       path under this spec; the two calendars meet only at
       portfolio-level joins keyed on bin-start labels (S-C6).
  S-C6 ALIGNMENT. Cross-asset alignment is defined at bin-start
       labels 09:30 / 13:30 ET only. The equity second bin CLOSES at
       16:00 (13:00 early-close) while crypto bin 1 runs to 17:30;
       joins must key on bin starts, never on bin closes. DST:
       crypto has no DST of its own — the ET anchoring imports the
       ET clock's DST, so bin-start UTC instants shift by one hour
       across transitions exactly as the equity bins' do, and the
       two tracks never drift apart at the 09:30/13:30 anchors.

KNOWN LIMITATION (disclosed, not hidden): with vendor hourly bars
stamped on the hour (the record pins bar-open stamps for equities,
-63 F4; crypto stamp granularity is UNCONFIRMED in the record), a
:30-anchored bin contains the four bar-opens strictly inside it
(e.g. bin 0 holds the 10:00, 11:00, 12:00, 13:00 opens). Price action
in [09:30, 10:00) lives inside the 09:00 bar, which belongs to the
prior bin. The capture manifest must pin the vendor's crypto bar
stamps; if they are :30-stamped the limitation vanishes. This spec
does not silently re-stamp bars.

Stdlib only (zoneinfo). Offline.
"""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
BIN_STARTS = [time(9, 30), time(13, 30), time(17, 30), time(21, 30),
              time(1, 30), time(5, 30)]  # last two fall on D+1


def session_date_of(local_dt):
    """ET local datetime -> the session date that owns it (S-C1/S-C2)."""
    if local_dt.time() >= time(9, 30):
        return local_dt.date()
    return local_dt.date() - timedelta(days=1)


def bin_index_of(local_dt):
    """ET local datetime -> bin index 0..5 within its session (S-C2/S-C3)."""
    mins = local_dt.hour * 60 + local_dt.minute
    # minutes since session start (09:30 wall clock), wrapping overnight
    rel = (mins - 570) % 1440
    return rel // 240


def assign_bar(open_instant_utc):
    """UTC instant of a bar open -> (session_date, bin_index, label)."""
    local = open_instant_utc.astimezone(NY)
    sd = session_date_of(local)
    bi = bin_index_of(local)
    label_time = BIN_STARTS[bi]
    label_date = sd if bi < 4 else sd + timedelta(days=1)
    return sd, bi, (label_date.isoformat(), f"{label_time.hour:02d}:{label_time.minute:02d}")


def hourly_bars(start_utc, end_utc):
    """Yield hourly bar-open instants in [start_utc, end_utc)."""
    t = start_utc
    while t < end_utc:
        yield t
        t += timedelta(hours=1)


def session_span_utc(session_date):
    """[start, end) UTC instants of a session (S-C2)."""
    start_local = datetime.combine(session_date, time(9, 30), tzinfo=NY)
    end_local = datetime.combine(session_date + timedelta(days=1), time(9, 30), tzinfo=NY)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)
