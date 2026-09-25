"""
ERD v0.1 -- frozen event clock.

Implements section 1 of erd-v0.1-preregistration-amendment-1.md EXACTLY.
Generates zero performance data: it maps one release timestamp to
(S | EXCLUDE) only. No prices, no returns, no backtests.

The day's ACTUAL regular-session open/close are INPUTS (NYSE calendar lookup
is out of scope for this module -- the caller supplies them, honoring early
closes). All datetimes/times are America/New_York (ET); naive datetimes are
treated as ET.

Frozen rules (Amendment section 1, lines 17-31):
  - Release before that day's regular-session open on trading day D -> S = D.
  - Release during that day's regular session [open, actual close] -> EXCLUDE.
    The interval is CLOSED: a timestamp exactly at the open or exactly at the
    actual close counts as during-session -> EXCLUDE.
  - Release after that day's actual regular-session close on trading day D
    -> S = next trading session.
  - Release on a weekend or NYSE holiday -> S = next NYSE trading session.
  - Missing, ambiguous, or vendor-imputed timing -> EXCLUDE.
  - Vendor timing code (BTO/DTM/AMC) disagreeing with the timestamp-derived
    bucket -> ambiguous -> EXCLUDE.
"""

from datetime import datetime, date, time

BMO = "BMO"
DTM = "DTM"
AMC = "AMC"
EXCLUDE = "EXCLUDE"

_CODE_TO_BUCKET = {"BTO": BMO, "DTM": DTM, "AMC": AMC}


def classify_release(release_dt, session_open, session_close,
                     next_session, vendor_code=None, is_trading_day=True):
    """Classify one earnings-release timestamp under the frozen event clock.

    Args:
        release_dt: datetime of the release in ET (naive datetimes are
            treated as ET; tz-aware datetimes use their ET wall time), or
            None when timing is missing.
        session_open, session_close: time objects giving the ACTUAL
            regular-session open/close in ET for the release date (early
            closes honored, e.g. time(13, 0)). None when the date is not a
            trading day.
        next_session: date of the next NYSE trading session AFTER the
            release date. The caller resolves the NYSE calendar.
        vendor_code: "BTO" | "DTM" | "AMC" | None (Intrinio/Zacks timing code).
        is_trading_day: False for weekends and NYSE holidays.

    Returns:
        ("S", s_date): the reaction session date.
        ("EXCLUDE", reason): excluded per the frozen clock; reason is a
            short machine-readable string naming the rule that fired.
    """
    # Missing timing (or a bare date with no time) -> EXCLUDE. Never imputed.
    if release_dt is None or not isinstance(release_dt, datetime):
        return (EXCLUDE, "missing timing")

    if vendor_code is not None and vendor_code not in _CODE_TO_BUCKET:
        return (EXCLUDE, "unknown vendor code -> ambiguous")

    # Weekend / NYSE holiday -> next NYSE trading session.
    if not is_trading_day or session_open is None or session_close is None:
        return ("S", next_session)

    t = release_dt.time()
    if t.tzinfo is not None:
        # Compare ET wall time against the ET session times.
        t = t.replace(tzinfo=None)

    # Closed interval [open, actual close]: exact open and exact close are DTM.
    if t < session_open:
        ts_bucket = BMO
    elif t <= session_close:
        ts_bucket = DTM
    else:
        ts_bucket = AMC

    # Frozen rule: code vs timestamp disagreement -> ambiguous -> EXCLUDE.
    if vendor_code is not None and _CODE_TO_BUCKET[vendor_code] != ts_bucket:
        return (EXCLUDE, "vendor code disagrees with timestamp bucket -> ambiguous")

    if ts_bucket == BMO:
        return ("S", release_dt.date())
    if ts_bucket == DTM:
        return (EXCLUDE, "during regular session [open, close]")
    return ("S", next_session)
