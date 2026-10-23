#!/usr/bin/env python3
"""
coinbase_15m_adapter.py — task -06 candidate (OFFLINE, synthetic only).

Aggregates Coinbase-Exchange-shaped 15-minute candles into the frozen
S-C 4H crypto bins. Input rows are Coinbase candle arrays in the
documented field order [time, low, high, open, close, volume], where
`time` is the bucket-start epoch second (UTC). No network access; this
module consumes in-memory arrays only.

Frozen target contract (adopted S-C1...S-C6, three-gate freeze
a126ce5; reference model -94 crypto_session_model.py sha 248442f1...):
  SESSION - one America/New_York calendar date D; span is the half-open
            absolute interval [D 09:30 ET, D+1 09:30 ET).
  BINS    - six bins per session opening 09:30 / 13:30 / 17:30 /
            21:30 / 01:30 / 05:30 ET WALL time. Bin boundaries are the
            UTC instants OF those wall times (the 01:30 open is the
            first, fold=0, occurrence), so exactly one bin -- the
            overnight 01:30 bin, which contains the 02:00 transition --
            absorbs DST: it holds 12 (spring, 3 elapsed h) or 20
            (fall, 5 elapsed h) 15m bars instead of 16. NOTE: bins are
            WALL-anchored, not elapsed-anchored: six 4-elapsed-hour
            offsets from the session open would put the extra/missing
            hour in the 05:30 bin on transition sessions and overhang
            the span on spring sessions. Membership and durations are
            still computed on absolute UTC instants (the -94 F-2
            failure class is wall-clock SUBTRACTION, not wall-defined
            boundaries resolved to instants).
  ASSIGN  - a bar-open instant belongs to session D iff its ET wall
            time is >= 09:30 on D or < 09:30 on D+1 (S-C3).

Honest aggregation: a 4H bin is composed ONLY of whole 15m bars whose
instants lie inside it. open = first bar's open, high = max, low = min,
close = last bar's close, volume = sum, all ordered by UTC instant.
No bar is split, no stamp is shifted, no label is fabricated.

Fail-closed refusals (AdapterRefusal):
  SCHEMA        - row not a 6-field array; non-numeric/non-finite
                  field; volume absent or null (the TD crypto defect);
                  negative volume.
  MISALIGNED    - bucket start not on the 900s UTC grid.
  DUPLICATE     - two rows for one instant with conflicting values
                  (exact-identical overlap rows are deduped).
  OUT_OF_SPAN   - a bar outside the declared [span_start, span_end).
  GAP           - under require_complete, a 15m instant inside the
                  span has no bar, or a bin is short of its expected
                  bar count for any reason other than the terminal
                  partial-bin allowance.
Anomalies (returned, not refused): a zero-volume bar with nonzero
OHLC range is classed ZERO_VOLUME_NONFLAT (the SMCI/TD class); the
bar is still aggregated honestly.

Stdlib only (zoneinfo). Deterministic.
"""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
SESSION_OPEN = time(9, 30)
BAR_SECONDS = 900
BIN_HOURS = 4


class AdapterRefusal(Exception):
    def __init__(self, code, detail):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


# --- frozen S-C session model (restated from -94; UTC instants only) ---

def session_span_utc(session_date: date):
    start_local = datetime.combine(session_date, SESSION_OPEN, tzinfo=NY)
    end_local = datetime.combine(session_date + timedelta(days=1),
                                 SESSION_OPEN, tzinfo=NY)
    return start_local.astimezone(timezone.utc), \
        end_local.astimezone(timezone.utc)


def session_date_of_instant(instant_utc: datetime) -> date:
    local = instant_utc.astimezone(NY)
    if local.time() >= SESSION_OPEN:
        return local.date()
    return local.date() - timedelta(days=1)


def expected_15m_count(session_date: date) -> int:
    start, end = session_span_utc(session_date)
    return int((end - start) / timedelta(seconds=BAR_SECONDS))


# --- input validation ---

def _parse_rows(rows):
    """Return {epoch: (low, high, open, close, volume)} after validation."""
    bars = {}
    for i, row in enumerate(rows):
        if not isinstance(row, (list, tuple)) or len(row) != 6:
            raise AdapterRefusal(
                "SCHEMA", f"row {i}: expected 6-field candle array, "
                          f"got {type(row).__name__} len="
                          f"{len(row) if hasattr(row, '__len__') else '?'}")
        t, low, high, open_, close, volume = row
        if volume is None:
            raise AdapterRefusal(
                "SCHEMA", f"row {i}: volume field absent/null")
        for name, v in (("time", t), ("low", low), ("high", high),
                        ("open", open_), ("close", close),
                        ("volume", volume)):
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise AdapterRefusal(
                    "SCHEMA", f"row {i}: field {name} not numeric: {v!r}")
            if v != v or v in (float("inf"), float("-inf")):
                raise AdapterRefusal(
                    "SCHEMA", f"row {i}: field {name} non-finite: {v!r}")
        if int(t) != t:
            raise AdapterRefusal(
                "SCHEMA", f"row {i}: time not an integer epoch: {t!r}")
        t = int(t)
        if t % BAR_SECONDS != 0:
            raise AdapterRefusal(
                "MISALIGNED", f"row {i}: bucket start {t} not on the "
                              f"900s UTC grid")
        if volume < 0:
            raise AdapterRefusal(
                "SCHEMA", f"row {i}: negative volume {volume!r}")
        vals = (float(low), float(high), float(open_), float(close),
                float(volume))
        if t in bars:
            if bars[t] != vals:
                raise AdapterRefusal(
                    "DUPLICATE", f"instant {t}: conflicting rows for "
                                 f"one bucket start")
            continue  # exact-identical overlap row: dedupe
        bars[t] = vals
    return bars


# --- aggregation ---

def aggregate(rows, span_start_utc: datetime, span_end_utc: datetime,
              require_complete=True, allow_partial_terminal=False):
    """Aggregate Coinbase-shaped 15m rows over [span_start, span_end).

    Returns (bins, anomalies). Each bin is a dict:
      {session_date, bin_open_utc (ISO), bin_open_et (ISO), open, high,
       low, close, volume, n_bars, expected_bars, partial}
    Bins are the frozen S-C bins: [session_start + k*4h) in absolute
    time, k = 0..5, clipped to the span. A bin whose span-clipped
    window ends before its natural end is 'partial' and is emitted
    only when allow_partial_terminal is set.
    """
    if span_start_utc.tzinfo is None or span_end_utc.tzinfo is None:
        raise AdapterRefusal("SCHEMA", "span bounds must be tz-aware UTC")
    bars = _parse_rows(rows)
    span_start = int(span_start_utc.timestamp())
    span_end = int(span_end_utc.timestamp())

    anomalies = []
    by_instant = {}
    for t, (low, high, open_, close, volume) in bars.items():
        if t < span_start or t >= span_end:
            raise AdapterRefusal(
                "OUT_OF_SPAN", f"bar {t} outside declared span "
                               f"[{span_start}, {span_end})")
        by_instant[t] = (low, high, open_, close, volume)
        if volume == 0.0 and high > low:
            anomalies.append({
                "class": "ZERO_VOLUME_NONFLAT",
                "instant_utc": datetime.fromtimestamp(
                    t, timezone.utc).isoformat(),
            })

    if require_complete:
        expected = set(range(span_start, span_end, BAR_SECONDS))
        missing = sorted(expected - set(by_instant))
        if missing:
            raise AdapterRefusal(
                "GAP", f"{len(missing)} expected 15m instant(s) missing "
                       f"inside span; first: {missing[0]}")

    # Session dates intersecting the span, from the S-C assignment rule.
    first_date = session_date_of_instant(span_start_utc)
    last_date = session_date_of_instant(
        span_end_utc - timedelta(seconds=1))
    bin_opens_wall = [time(9, 30), time(13, 30), time(17, 30),
                      time(21, 30), time(1, 30), time(5, 30)]
    bins = []
    d = first_date
    while d <= last_date:
        s_start, s_end = session_span_utc(d)
        # Wall-anchored bin boundaries as UTC instants. Opens 0-3 fall
        # on date d; opens 4-5 (01:30 / 05:30) on date d+1. fold=0: the
        # 01:30 open on a fall-back night is the FIRST occurrence; the
        # repeated 01:30 wall hour is an interior bar of that bin.
        opens = []
        for k, w in enumerate(bin_opens_wall):
            odate = d if k < 4 else d + timedelta(days=1)
            opens.append(datetime.combine(odate, w, tzinfo=NY)
                         .astimezone(timezone.utc))
        opens.append(s_end)
        assert opens[0] == s_start and all(
            opens[i] < opens[i + 1] for i in range(6)), \
            f"session {d}: bin opens not strictly increasing"
        for k in range(6):
            b_start = opens[k]
            b_end = opens[k + 1]
            lo = max(b_start, span_start_utc)
            hi = min(b_end, span_end_utc)
            if lo >= hi:
                continue
            instants = [t for t in range(int(lo.timestamp()),
                                         int(hi.timestamp()),
                                         BAR_SECONDS)
                        if t in by_instant]
            if not instants:
                if require_complete:
                    raise AdapterRefusal(
                        "GAP", f"session {d} bin {k}: no bars in window")
                continue
            instants.sort()
            expected_bars = int((hi - lo) / timedelta(seconds=BAR_SECONDS))
            partial = hi < b_end or lo > b_start
            if partial and not allow_partial_terminal:
                raise AdapterRefusal(
                    "GAP", f"session {d} bin {k}: span clips the bin "
                           f"(partial terminal bin not allowed)")
            if require_complete and len(instants) != expected_bars:
                raise AdapterRefusal(
                    "GAP", f"session {d} bin {k}: {len(instants)} bars, "
                           f"expected {expected_bars}")
            seq = [by_instant[t] for t in instants]
            bins.append({
                "session_date": d.isoformat(),
                "bin_open_utc": datetime.fromtimestamp(
                    instants[0], timezone.utc).isoformat(),
                "bin_open_et": datetime.fromtimestamp(
                    instants[0], timezone.utc).astimezone(NY).isoformat(),
                "open": seq[0][2],
                "high": max(s[1] for s in seq),
                "low": min(s[0] for s in seq),
                "close": seq[-1][3],
                "volume": sum(s[4] for s in seq),
                "n_bars": len(instants),
                "expected_bars": expected_bars,
                "partial": partial,
            })
        d += timedelta(days=1)
    return bins, anomalies
