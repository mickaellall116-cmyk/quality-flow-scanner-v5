Bug: the function applies a fixed UTC-5 offset (Eastern Standard Time) all year. US Eastern observes daylight saving time: from the second Sunday of March to the first Sunday of November the offset is UTC-4 (EDT). The function is therefore one hour early for roughly eight months of the year.

Concrete example: input datetime(2026, 7, 1, 14:00, UTC). The function returns 09:00. The correct Eastern wall-clock time is 10:00 (EDT). (In winter it happens to be right: 2026-01-15 14:00 UTC returns 09:00, which is correct EST.)

Corrected implementation:

from datetime import datetime
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")

def to_eastern(utc_dt):
    """Convert an aware UTC datetime to US Eastern wall-clock time (naive)."""
    return utc_dt.astimezone(EASTERN).replace(tzinfo=None)
