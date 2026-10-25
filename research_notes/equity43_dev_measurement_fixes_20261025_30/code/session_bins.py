"""Pinned session-table bin resolution (30 successor, shared).

QF-EQUITY43-DEV-MEASUREMENT-FIXES-20261025-30 — successor of the 29r
module of the same name, extended per ChatGPT's -29r verdict (Slack
TS 1792941227.393299) P8 calendar-horizon HOLD: the pinned base table
ends 2026-10-16 and every later bin lookup failed closed, so the
prospective journal could not accept the Oct 26-30 pilot week or any
later forward record. This successor keeps the base table
byte-untouched and its loader unchanged (`load_pinned_table`), and
adds a second, separately versioned artifact — the session-table
EXTENSION (2026-10-19..2027-12-31, built from the NYSE published
calendar by code/build_session_extension.py, sha256 d2fa788d…) —
loaded alongside it by `load_union_table()`. The union refuses
duplicate dates across the two artifacts, and any date in NEITHER
artifact still fails closed: there is no extrapolation past
2027-12-31 and no arithmetic session generation anywhere.

---

Original 29r documentation follows.

Pinned session-table bin resolution (29r repair, shared).

QF-EQUITY43-DEV-MEASUREMENT-FIXES-20261025-29r.

ChatGPT's independent -29 verdict (Slack TS 1792935577.054259) held P1
and P8 on session-time causality: both modules derived bar completion
by +4h arithmetic (09:30->13:30, 13:30->17:30), but the equity grid is
session-aware — bins are 09:30->13:30 and 13:30->16:00 ET, with
calendar-specific early closes. This module is the single source of
bin truth for the repaired modules: every bin start / bin end is
resolved through the PINNED adopted session table, never through
duration arithmetic.

Pinned table: the adopted qualified calendar of record,
XNYS_SESSION_TABLE_751_UNION (751 sessions, 2023-10-19..2026-10-16),
committed at research_notes/equity43_feed_source_review_20261024_22/
bundle/calendar/session_table_751_qualified.json, sha256
00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f.
The hash is verified on every load; a missing, altered, or ambiguous
table is a hard failure (fail-closed), as is any bin lookup for a
session or bin start the table does not contain (early closes and DST
transitions resolve through the table's own open/close rows and the
America/New_York zone rules — never through arithmetic).

Bin convention (adopted calendar convention):
  * bin 1: session open (09:30 ET) -> min(13:30, session close)
  * bin 2: 13:30 ET -> session close, present only when the session
    close is later than 13:30 (absent on 13:00 early-close sessions,
    whose single bin is 09:30 -> 13:00).
This matches the recorded DEV grid exactly: all 524 DEV sessions'
bars resolve, and the five DEV early-close sessions carry exactly the
single 09:30 bar.
"""
import hashlib
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

PINNED_TABLE_SHA256 = \
    "00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f"
_DEFAULT_REL = os.path.join(
    "research_notes", "equity43_feed_source_review_20261024_22",
    "bundle", "calendar", "session_table_751_qualified.json")

EXTENSION_TABLE_SHA256 = \
    "d2fa788d70f2c8677ca49b9e0201940586c051b9227f815b8d2da55b1e5d3a2f"
_EXTENSION_REL = os.path.join(
    "research_notes", "equity43_dev_measurement_fixes_20261025_30",
    "artifacts", "session_table_extension_2027.json")


class SessionTableError(ValueError):
    pass


def _repo_root():
    # code/ -> <pkg>/ -> research_notes/ -> repo root
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


def default_table_path():
    return os.environ.get("QF_SESSION_TABLE_PATH",
                          os.path.join(_repo_root(), _DEFAULT_REL))


class SessionTable:
    """Session rows -> bin (start, end) instants, fail-closed."""

    def __init__(self, sessions):
        self._by_date = {}
        for row in sessions:
            d = row["date"]
            if d in self._by_date:
                raise SessionTableError(
                    f"ambiguous session table: duplicate row for {d}")
            self._by_date[d] = row
        self._bins_cache = {}

    @classmethod
    def from_sessions(cls, sessions):
        return cls(sessions)

    def __len__(self):
        return len(self._by_date)

    def bins_for_date(self, date_str):
        """[(bin_start, bin_end)] as aware ET datetimes for a session
        date ('YYYY-MM-DD'). Raises SessionTableError if the date is
        not a session in the table."""
        if date_str in self._bins_cache:
            return self._bins_cache[date_str]
        row = self._by_date.get(date_str)
        if row is None:
            raise SessionTableError(
                f"session {date_str} absent from pinned session table "
                f"(fail-closed: no bin resolution by arithmetic)")
        y, m, d = (int(x) for x in date_str.split("-"))
        oh, om = (int(x) for x in row["open"].split(":"))
        ch, cm = (int(x) for x in row["close"].split(":"))
        open_dt = datetime(y, m, d, oh, om, tzinfo=ET)
        close_dt = datetime(y, m, d, ch, cm, tzinfo=ET)
        mid = datetime(y, m, d, 13, 30, tzinfo=ET)
        bins = [(open_dt, min(mid, close_dt))]
        if close_dt > mid:
            bins.append((mid, close_dt))
        self._bins_cache[date_str] = bins
        return bins

    def _local(self, ts):
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts.tzinfo is None:
            raise SessionTableError(
                f"naive timestamp {ts!r} refused: bin resolution "
                f"requires a tz-aware instant")
        return ts.astimezone(ET)

    def bin_end(self, bin_start_ts):
        """The pinned bin_end instant for a bar whose start is
        bin_start_ts (any tz-aware representation). Fail-closed:
        raises SessionTableError unless bin_start_ts is exactly a
        table bin start."""
        local = self._local(bin_start_ts)
        date_str = local.date().isoformat()
        for start, end in self.bins_for_date(date_str):
            if local == start:
                return end
        raise SessionTableError(
            f"{local.isoformat()} is not a bin start in the pinned "
            f"session table for {date_str} (fail-closed)")

    def is_bin_start(self, ts):
        try:
            self.bin_end(ts)
            return True
        except SessionTableError:
            return False

    def next_bin_start(self, bin_start_ts):
        """Start of the bin immediately following the bin that starts
        at bin_start_ts (= that bin's end, or the next session's open
        when the bin is the session's last). Fail-closed on unknown
        bins and at the table's end."""
        end = self.bin_end(bin_start_ts)
        date_str = end.astimezone(ET).date().isoformat()
        for start, _e in self.bins_for_date(date_str):
            if end == start:
                return end
        # `end` is a session close: the next bin starts at the next
        # session's open.
        dates = sorted(self._by_date)
        i = dates.index(date_str)
        if i + 1 >= len(dates):
            raise SessionTableError(
                f"no session after {date_str} in pinned table "
                f"(fail-closed)")
        return self.bins_for_date(dates[i + 1])[0][0]


def _load_sessions(path, sha256, label):
    if not os.path.exists(path):
        raise SessionTableError(f"{label} missing: {path}")
    raw = open(path, "rb").read()
    h = hashlib.sha256(raw).hexdigest()
    if h != sha256:
        raise SessionTableError(
            f"{label} hash mismatch: {h} != {sha256} (fail-closed)")
    doc = json.loads(raw)
    sessions = doc.get("sessions")
    if not isinstance(sessions, list) or not sessions:
        raise SessionTableError(f"{label} has no sessions")
    return doc, sessions


def load_pinned_table(path=None):
    """Load the pinned session table, verifying its sha256. Any
    absence, hash mismatch, or structural defect is fail-closed."""
    _doc, sessions = _load_sessions(
        path or default_table_path(), PINNED_TABLE_SHA256,
        "pinned session table")
    return SessionTable(sessions)


def default_extension_path():
    return os.environ.get("QF_SESSION_TABLE_EXT_PATH",
                          os.path.join(_repo_root(), _EXTENSION_REL))


def _load_extension_sessions(path=None):
    doc, sessions = _load_sessions(
        path or default_extension_path(), EXTENSION_TABLE_SHA256,
        "session-table extension")
    if doc.get("artifact") != "XNYS_SESSION_TABLE_EXTENSION_2027":
        raise SessionTableError(
            "session-table extension artifact id mismatch "
            f"({doc.get('artifact')!r}) (fail-closed)")
    ext = doc.get("extends") or {}
    if ext.get("sha256") != PINNED_TABLE_SHA256:
        raise SessionTableError(
            "session-table extension does not extend the pinned "
            "base table (extends.sha256 mismatch) (fail-closed)")
    return sessions


def load_extension_table(path=None):
    """Load the versioned session-table extension, verifying its
    sha256 and its declared parentage (it must extend THIS pinned
    base table). Fail-closed on any defect."""
    return SessionTable(_load_extension_sessions(path))


def load_union_table(base_path=None, extension_path=None):
    """The prospective calendar of record: the pinned base table
    (751 sessions, 2023-10-19..2026-10-16) PLUS the versioned
    extension (303 sessions, 2026-10-19..2027-12-31), each
    hash-verified. A date present in both artifacts is ambiguous and
    refused (the SessionTable constructor rejects duplicates); a
    date in neither still fails closed at lookup. No session is
    generated or extrapolated."""
    _d1, base_sessions = _load_sessions(
        base_path or default_table_path(), PINNED_TABLE_SHA256,
        "pinned session table")
    ext_sessions = _load_extension_sessions(extension_path)
    # The SessionTable constructor refuses duplicate dates, so an
    # overlap between base and extension is refused here.
    return SessionTable(base_sessions + ext_sessions)


# Convenience for tests: bin duration is NOT a constant of the
# repaired system (4h / 2.5h / 3.5h all occur); nothing in the repaired
# modules may consume a duration in place of a table bin_end.
def bin_duration(bin_start_ts, table=None):
    table = table or load_pinned_table()
    start = table._local(bin_start_ts)
    return table.bin_end(bin_start_ts) - start


__all__ = ["ET", "PINNED_TABLE_SHA256", "EXTENSION_TABLE_SHA256",
           "SessionTable", "SessionTableError", "load_pinned_table",
           "load_extension_table", "load_union_table",
           "default_table_path", "default_extension_path",
           "bin_duration"]
