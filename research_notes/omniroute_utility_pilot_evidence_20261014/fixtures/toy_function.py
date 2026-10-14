from datetime import datetime, timedelta, timezone

EASTERN_STANDARD_OFFSET = timedelta(hours=-5)


def to_eastern(utc_dt):
    """Convert an aware UTC datetime to US Eastern wall-clock time (naive)."""
    return (utc_dt + EASTERN_STANDARD_OFFSET).replace(tzinfo=None)
