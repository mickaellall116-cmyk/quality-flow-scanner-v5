#!/usr/bin/env python3
"""
constructor_guard.py — CANDIDATE guard v3: fail-closed guard for the
pinned 4H constructor boundary (task -93; extends the -89 v2 /
repair -91 candidate, whose design line is: -86 F3, extending the
-84 H3b candidate).

STATUS: isolated candidate module. NOT part of the pinned route, NOT
integrated, NOT adopted. It wraps a constructor module exposing
construct_4h(...) — in this package, the pin-verified byte-copy of
the pinned constructor (guard/construct_4h_fixture_copy.py, sha256
d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd…).

PROVENANCE: this file is the successor of -84's
guard/constructor_guard.py (sha256 ee403f9a…, GUARD_VERSION
"h3b-candidate-1"). The v1 API and refusal semantics are preserved
verbatim; v2 ADDS three refusal classes. The -84 suite is carried
into this package unchanged as the regression floor and passes
against this module (see ../TEST_EVIDENCE.md).

WHY V2 (Claude's -82 re-review HOLD, via -86 F3): duplicate safety
alone is not enough. The pinned constructor sorts its input
(sort_index) and converts any tz-aware index to America/New_York
(tz_convert) — two more silent-repair classes at the same boundary:

  - NON-MONOTONIC input is silently re-ordered by the constructor's
    sort, exactly the silent-repair class of the duplicate merge.
  - A FIXED-OFFSET or wrong-zone index is silently converted: a
    vendor stamping wall times at UTC-05:00 year-round produces
    bars that shift by one hour across the spring-forward boundary.
    Pinned regression record (V2-3, pandas 2.2.3): the unguarded
    constructor completes that input with NO warning (warnings-as-
    errors does not trip) and emits silently mis-binned bars — the
    failure class of the 2023-10-03 candle incident, at the input
    boundary. Only a boundary refusal defends it.

REFUSAL CLASSES (fail-closed, deterministic; check order is part of
the contract — duplicates first, so the -84 floor's expectations
hold verbatim):
  input, BEFORE the constructor is invoked:
    1. CONSTRUCTOR_GUARD_DUPLICATE_TIMESTAMP  (v1, unchanged)
    2. CONSTRUCTOR_GUARD_TIMEZONE             (naive / fixed-offset /
                                               any zone != America/New_York)
    3. CONSTRUCTOR_GUARD_NON_MONOTONIC        (index not strictly
                                               increasing)
    3b. CONSTRUCTOR_GUARD_INDEX_MISMATCH      (REPAIR -91, 2026-10-21,
                                               ChatGPT review blocker 2:
                                               the -82 H1 exact index
                                               equality was DEFINED in
                                               this module but never
                                               INVOKED by the wrapper,
                                               so a shifted / dropped /
                                               off-grid stamp sequence
                                               passed. The guarded path
                                               now derives the exact
                                               ordered expected 1H index
                                               from the session table
                                               (session_closes) and
                                               enforces it as a
                                               mandatory step; a missing
                                               session table refuses
                                               fail-closed — the step
                                               cannot be skipped.)
  output, AFTER construction:
    4. CONSTRUCTOR_GUARD_DUPLICATE_TIMESTAMP  (v1 post-check)
    5. CONSTRUCTOR_GUARD_VOLUME_CONSERVATION  (whole-frame law: every
       output bin's Volume == the sum of its constituent input
       volumes, and the output total == the constructed-span input
       total; the expectation is computed by an independent shadow
       binning of the guarded input, so a constituent dropped or
       altered between the guard's pre-check and aggregation is
       caught — fixture V2-6)

The guard changes behavior ONLY on invalid input: for valid input
the guarded path returns the constructor's output unmodified
(proven byte-identical by -84 G3, re-proven through v2 by V2-5).

Adoption is NOT this module's decision: adopting guard v2 means a
successor constructor pin + a successor route manifest + the full
re-proof sequence (see ../SPEC_GUARD_V2.md and ../ADOPTION_NOTES.md;
GO G3-v2, Mike). Editing the pinned constructor in place is
forbidden — the pin IS the evidence chain.

V3 ADDITIONS (task -93, from Claude's -92 review HOLD on guard
v2/-91 — Issue #1 comment 6343957169). The v2/-91 refusal classes,
check order, and clean-path byte-identity are preserved; v3 ADDS
three refusal classes and one provenance binding, all
pre-construction:

  6. CONSTRUCTOR_GUARD_NONFINITE — any NaN or ±inf in Open / High /
     Low / Close / Volume refuses. In v2 the constructor's dropna
     silently discarded NaN-OHLC rows and the volume-conservation
     shadow mirrored that exclusion, so a vendor placeholder NaN
     row passed the guarded boundary and vanished. The checker
     classifies the same row a completeness defect (NAN_VALUE);
     v3 aligns the boundary with the checker: nonfinite input
     refuses here, the constructor is never invoked, and the
     shadow's dropna mirror becomes unreachable on guarded input.
  7. CONSTRUCTOR_GUARD_INTERVAL_END — when the input carries an
     `interval_end` column, every bar's stated end must be a grid
     end for its bar (the next grid start; for the session's final
     bar, the session close or the nominal next hour — the two
     conventions in evidence, see _grid_derived_ends). v2 consumed
     stated ends for the shadow without validating them, so a
     truncated or stretched end (e.g. a 3-of-4-hour bin whose last
     bar claims the bin end) was taken on trust. A stated end that
     is not a grid end refuses.
  8. CONSTRUCTOR_GUARD_CALENDAR_BINDING — the session table is the
     guard's ground truth for exact-index and interval-end
     derivation, but v2 accepted it from the caller unbound. v3
     provides `calendar_sha256()` (canonical hash of the table);
     when the caller supplies `expected_calendar_sha256`, the
     guard recomputes and refuses on mismatch, before construction.
     The adoption pin (G3-v3) is expected to make the expected-hash
     argument mandatory at the route level; the candidate keeps it
     optional so the v2/-91 call contract is not silently broken.

GUARD_VERSION is bumped to a unique v3 string (Claude's -92
pin-minting condition). Consequence, disclosed: the -89 v2 suite's
single version-string assertion belongs to the v2 pin and is not
carried into v3's suite; every behavioral check of the prior
suites is re-proven against the pristine prior modules (regression)
and the floor behaviors are re-proven against this module by the
v3 suite (see ../TEST_EVIDENCE.md).
"""

import pandas as pd

GUARD_VERSION = "guard-v3-candidate-1"
DUPLICATE_CODE = "CONSTRUCTOR_GUARD_DUPLICATE_TIMESTAMP"
INDEX_MISMATCH_CODE = "CONSTRUCTOR_GUARD_INDEX_MISMATCH"
NON_MONOTONIC_CODE = "CONSTRUCTOR_GUARD_NON_MONOTONIC"
TIMEZONE_CODE = "CONSTRUCTOR_GUARD_TIMEZONE"
VOLUME_CONSERVATION_CODE = "CONSTRUCTOR_GUARD_VOLUME_CONSERVATION"
NONFINITE_CODE = "CONSTRUCTOR_GUARD_NONFINITE"
INTERVAL_END_CODE = "CONSTRUCTOR_GUARD_INTERVAL_END"
CALENDAR_BINDING_CODE = "CONSTRUCTOR_GUARD_CALENDAR_BINDING"

OHLCV_COLUMNS = ("Open", "High", "Low", "Close", "Volume")

REQUIRED_TZ = "America/New_York"
NY = REQUIRED_TZ
SESSION_OPEN_MIN = 9 * 60 + 30          # 09:30 → 570 (constructor's grid)
FIRST_BIN_CUTOFF_MIN = 13 * 60 + 30     # 13:30 → 810 (constructor's grid)


# ---------------------------------------------------------------- v1 core

class DuplicateTimestampError(ValueError):
    """Raised when a frame index contains duplicated timestamps."""

    code = DUPLICATE_CODE

    def __init__(self, stage, duplicates, total):
        self.stage = stage
        self.duplicates = [str(d) for d in duplicates]
        self.total = total
        super().__init__(
            f"{DUPLICATE_CODE}: stage={stage} "
            f"duplicated_timestamp_count={total} "
            f"duplicated_timestamps={self.duplicates}"
        )


class IndexMismatchError(ValueError):
    """Raised when a constructed frame's index != the expected index."""

    code = INDEX_MISMATCH_CODE

    def __init__(self, got, expected, detail=""):
        self.got = [str(t) for t in got]
        self.expected = [str(t) for t in expected]
        msg = f"{INDEX_MISMATCH_CODE}: got={self.got} expected={self.expected}"
        if detail:
            msg = f"{INDEX_MISMATCH_CODE}: {detail} | {msg}"
        super().__init__(msg)


def find_duplicate_timestamps(index):
    """Duplicated labels in first-appearance order (deterministic)."""
    seen = set()
    dup_seen = set()
    dups = []
    for label in index:
        if label in seen and label not in dup_seen:
            dup_seen.add(label)
            dups.append(label)
        seen.add(label)
    return dups


def count_duplicated_rows(index):
    """Number of rows whose label is duplicated (all copies counted)."""
    if len(index) == 0:
        return 0
    mask = index.duplicated(keep=False)
    return int(mask.sum())


def assert_no_duplicate_timestamps(index, *, stage):
    """Raise DuplicateTimestampError if the index has any duplicates."""
    dups = find_duplicate_timestamps(index)
    if dups:
        raise DuplicateTimestampError(stage, dups, count_duplicated_rows(index))
    return 0


def assert_index_equality(frame, expected_index):
    """The -82 H1 assertion as a callable: exact index equality."""
    got = list(frame.index)
    expected = list(expected_index)
    if got != expected:
        raise IndexMismatchError(got, expected)
    return True


# ------------------------------------------- repair -91: expected index

def expected_index_from_sessions(session_closes):
    """The exact ordered 1H bar-stamp sequence a frame must carry,
    derived from the session table: for each session date (sorted),
    hourly starts at 09:30 while start < session close — the same
    grid the volume-conservation shadow uses."""
    out = []
    for day in sorted(session_closes):
        close = session_closes[day]
        close_min = int((close - day).total_seconds() // 60)
        m = SESSION_OPEN_MIN
        while m < close_min:
            out.append(day + pd.Timedelta(minutes=m))
            m += 60
    return out


def assert_expected_index(frame, session_closes, *, stage="input_1h"):
    """REPAIR -91: mandatory exact-index enforcement in the guarded
    path. The frame's index must equal, exactly and in order, the
    expected sequence derived from the session table. No session
    table -> cannot verify -> fail-closed refusal (the step is not
    optional and cannot be silently skipped)."""
    if not session_closes:
        raise IndexMismatchError(
            [], [],
            detail="cannot verify: session_closes (the session "
                   "table) is required for exact-index enforcement")
    expected = expected_index_from_sessions(session_closes)
    got = list(frame.index)
    if got != expected:
        raise IndexMismatchError(got, expected)
    return True


# ------------------------------------------------------- v2: timezone class

class TimezoneError(ValueError):
    """Raised when the input index is not tz-aware America/New_York."""

    code = TIMEZONE_CODE

    def __init__(self, stage, found):
        self.stage = stage
        self.found = found
        super().__init__(
            f"{TIMEZONE_CODE}: stage={stage} "
            f"required_tz={REQUIRED_TZ} found_tz={found}"
        )


def _tz_name(tz):
    """Deterministic name for a tzinfo: zoneinfo key, pytz zone, or str."""
    if tz is None:
        return None
    key = getattr(tz, "key", None)          # zoneinfo.ZoneInfo
    if key:
        return str(key)
    zone = getattr(tz, "zone", None)        # pytz timezone
    if zone:
        return str(zone)
    return str(tz)                          # e.g. 'UTC-05:00', 'UTC', tzfile path


def assert_timezone(index, *, stage="input_1h"):
    """The index must be tz-aware America/New_York — the chain's
    declared input basis. A naive index has no basis; a fixed offset
    cannot represent EST/EDT transitions; any other zone is converted
    silently by the constructor. All three refuse here."""
    name = _tz_name(getattr(index, "tz", None))
    if name is None or not (name == REQUIRED_TZ
                            or name.endswith("/" + REQUIRED_TZ)):
        raise TimezoneError(stage, name if name is not None else "NAIVE")
    return True


# ----------------------------------------------------- v2: monotonic class

class NonMonotonicError(ValueError):
    """Raised when the input index is not strictly increasing."""

    code = NON_MONOTONIC_CODE

    def __init__(self, stage, position, prev, cur):
        self.stage = stage
        self.position = position
        self.prev = str(prev)
        self.cur = str(cur)
        super().__init__(
            f"{NON_MONOTONIC_CODE}: stage={stage} "
            f"first_violation_at_row={position} prev={self.prev} cur={self.cur}"
        )


def assert_monotonic_increasing(index, *, stage="input_1h"):
    """Strictly increasing, row by row. (Duplicates are already
    refused by the earlier check; equality here would still refuse.)"""
    prev = None
    for i, cur in enumerate(index):
        if prev is not None and not (prev < cur):
            raise NonMonotonicError(stage, i, prev, cur)
        prev = cur
    return True


# ------------------------------------------------- v3: nonfinite class

class NonfiniteError(ValueError):
    """Raised when any OHLCV value is NaN or ±inf (v3)."""

    code = NONFINITE_CODE

    def __init__(self, stage, counts, first):
        self.stage = stage
        self.counts = counts
        self.first = first
        super().__init__(
            f"{NONFINITE_CODE}: stage={stage} "
            f"nonfinite_counts={counts} first={first}"
        )


def assert_finite_ohlcv(frame, *, stage="input_1h"):
    """V3: every OHLCV value must be finite. A missing OHLCV column
    is a cannot-verify refusal under the same code — the guard does
    not guess at a frame it cannot fully inspect. Placeholder NaN
    rows refuse here; they never reach the constructor's dropna."""
    counts = {}
    first = None
    for col in OHLCV_COLUMNS:
        if col not in frame.columns:
            raise NonfiniteError(
                stage, {}, f"cannot verify: column {col} absent")
        vals = pd.to_numeric(frame[col], errors="coerce")
        bad = ~vals.map(lambda x: x == x and abs(x) != float("inf"))
        n = int(bad.sum())
        if n:
            counts[col] = n
            if first is None:
                pos = int(bad.to_numpy().argmax())
                first = f"{col}@{frame.index[pos]}"
    if counts:
        raise NonfiniteError(stage, counts, first)
    return True


# ----------------------------------------------- v3: interval-end class

class IntervalEndError(ValueError):
    """Raised when a stated interval_end disagrees with the
    grid-derived end for its bar (v3)."""

    code = INTERVAL_END_CODE

    def __init__(self, stage, mismatches, total, detail=""):
        self.stage = stage
        self.mismatches = mismatches
        self.total = total
        msg = (f"{INTERVAL_END_CODE}: stage={stage} "
               f"mismatch_count={total} mismatches={mismatches}")
        if detail:
            msg = f"{INTERVAL_END_CODE}: {detail} | {msg}"
        super().__init__(msg)


def _grid_derived_ends(frame, closes):
    """Per-bar ALLOWED grid ends (NY): the set of interval_end
    values the session grid permits for that bar. For a non-final
    bar the only grid end is the next grid start (= start + 60m).
    For the session's final bar, two conventions are in evidence in
    this chain and both are grid ends: the session close (the
    constructor's own derivation caps there) and the nominal next
    hour (start + 60m; the convention every prior fixture and the
    vendor's nominal-hour stamps use). Anything else — a truncated
    end, an end stretched past the nominal hour, an off-grid end —
    is not a grid end and refuses. (Adjudication may tighten the
    final-bar set to the close only; disclosed in ../SPEC_93.md.)
    Off-grid bars are a cannot-verify IntervalEndError."""
    local = frame.index.tz_convert(NY)
    allowed = []
    for ts in local:
        d = ts.normalize()
        if d not in closes:
            raise IntervalEndError(
                "input_1h", [], 0,
                detail=f"cannot verify: no session close for {d.date()}")
        close_min = int((closes[d] - d).total_seconds() // 60)
        starts = []
        m = SESSION_OPEN_MIN
        while m < close_min:
            starts.append(m)
            m += 60
        minute = ts.hour * 60 + ts.minute
        if minute not in starts:
            raise IntervalEndError(
                "input_1h", [], 0,
                detail=f"cannot verify: bar {ts} is off the session grid")
        nxt = starts.index(minute) + 1
        if nxt < len(starts):
            allowed.append([d + pd.Timedelta(minutes=starts[nxt])])
        else:
            allowed.append([closes[d], ts + pd.Timedelta(minutes=60)])
    return allowed


def assert_interval_end_exactness(constructor_module, frame, *,
                                  session_closes=None, stage="input_1h"):
    """V3: if the frame carries an `interval_end` column, every
    stated end must equal the grid-derived end exactly. Truncated
    ends (a bar claiming an early end) and stretched ends (a
    partial bin's last bar claiming the bin end) both refuse. No
    interval_end column -> no-op (the derivation path is unchanged
    from v2)."""
    cols_lower = {c.lower(): c for c in frame.columns}
    if "interval_end" not in cols_lower:
        return True
    stated = pd.to_datetime(frame[cols_lower["interval_end"]])
    if stated.dt.tz is None:
        raise IntervalEndError(
            stage, [], 0, detail="cannot verify: interval_end is tz-naive")
    stated = stated.dt.tz_convert(NY)
    closes = _resolve_closes(constructor_module, frame.index, session_closes)
    allowed = _grid_derived_ends(frame, closes)
    mismatches = []
    for ts, got_end, ok_ends in zip(frame.index, stated, allowed):
        if pd.Timestamp(got_end) not in [pd.Timestamp(e) for e in ok_ends]:
            mismatches.append(
                {"bar": str(ts), "stated_end": str(got_end),
                 "grid_ends": [str(e) for e in ok_ends]})
    if mismatches:
        raise IntervalEndError(stage, mismatches[:5], len(mismatches))
    return True


# -------------------------------------------- v3: calendar SHA binding

class CalendarBindingError(ValueError):
    """Raised when the session table's canonical hash != the
    caller-pinned expected hash (v3)."""

    code = CALENDAR_BINDING_CODE

    def __init__(self, got, expected):
        self.got = got
        self.expected = expected
        super().__init__(
            f"{CALENDAR_BINDING_CODE}: session-table sha256 got={got} "
            f"expected={expected}"
        )


def calendar_sha256(session_closes):
    """Canonical sha256 of a session table ({NY-midnight Timestamp:
    NY-aware close Timestamp}): one line per session, sorted by
    date, `YYYY-MM-DD|<close as UTC ISO-8601>`, LF-joined with a
    trailing LF, UTF-8. Deterministic across processes and dict
    orderings; any added / dropped / moved session changes it."""
    import hashlib
    lines = []
    for day in sorted(session_closes):
        close_utc = pd.Timestamp(session_closes[day]).tz_convert("UTC")
        lines.append(f"{pd.Timestamp(day).date().isoformat()}|"
                     f"{close_utc.isoformat()}")
    blob = ("\n".join(lines) + "\n").encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def assert_calendar_binding(session_closes, expected_calendar_sha256, *,
                            stage="input_1h"):
    """V3: when an expected calendar hash is supplied, the session
    table must hash to it exactly. A missing table with a supplied
    expectation is a cannot-verify refusal (fail-closed)."""
    if expected_calendar_sha256 is None:
        return True
    if not session_closes:
        raise CalendarBindingError(
            None, expected_calendar_sha256)
    got = calendar_sha256(session_closes)
    if got != expected_calendar_sha256:
        raise CalendarBindingError(got, expected_calendar_sha256)
    return True


# ------------------------------------------- v2: volume-conservation class

class VolumeConservationError(ValueError):
    """Raised when constructed volumes != constituent input volumes,
    or when the guard cannot compute the expectation (fail-closed)."""

    code = VOLUME_CONSERVATION_CODE

    def __init__(self, mismatches, detail=""):
        self.mismatches = mismatches
        super().__init__(
            f"{VOLUME_CONSERVATION_CODE}: {detail} "
            f"mismatches={mismatches}"
        )


def _resolve_closes(constructor_module, frame_index, session_closes):
    """Per-date session closes for the shadow binning, mirroring the
    constructor's own precedence: explicit session_closes override,
    else the constructor module's calendar lookup. Missing either way
    is a fail-closed cannot-verify."""
    local = frame_index.tz_convert(NY)
    closes = {}
    for d in pd.DatetimeIndex(local.normalize().unique()):
        if session_closes and d in session_closes:
            closes[d] = session_closes[d]
        elif hasattr(constructor_module, "session_close_et"):
            closes[d] = constructor_module.session_close_et(d)
        else:
            raise VolumeConservationError(
                {}, detail=f"cannot verify: no session close for {d.date()}")
    return closes


def _constituent_ends(frame, closes, validated_ends):
    """Interval ends with the constructor's precedence:
    validated_ends → 'interval_end' column → session-grid derivation
    (hourly starts from 09:30 while start < close; a bar's end is the
    next grid start, else the session close)."""
    if validated_ends is not None:
        missing = [ts for ts in frame.index if ts not in validated_ends.index]
        if missing:
            raise VolumeConservationError(
                {}, detail=f"cannot verify: validated_ends missing for "
                           f"{len(missing)} bars")
        return validated_ends.loc[frame.index].dt.tz_convert(NY)
    cols_lower = {c.lower(): c for c in frame.columns}
    if "interval_end" in cols_lower:
        ends = pd.to_datetime(frame[cols_lower["interval_end"]])
        if ends.dt.tz is None:
            raise VolumeConservationError(
                {}, detail="cannot verify: interval_end is tz-naive")
        return ends.dt.tz_convert(NY)
    local = frame.index.tz_convert(NY)
    ends = []
    for ts in local:
        d = ts.normalize()
        close_min = int((closes[d] - d).total_seconds() // 60)
        starts = []
        m = SESSION_OPEN_MIN
        while m < close_min:
            starts.append(m)
            m += 60
        minute = ts.hour * 60 + ts.minute
        if minute not in starts:
            raise VolumeConservationError(
                {}, detail=f"cannot verify: bar {ts} is off the session grid")
        nxt = starts.index(minute) + 1
        end_min = starts[nxt] if nxt < len(starts) else close_min
        ends.append(d + pd.Timedelta(minutes=end_min))
    return pd.Series(ends, index=frame.index)


def expected_bin_volumes(constructor_module, frame, *,
                         session_closes=None, as_of=None,
                         validated_ends=None):
    """Independent shadow binning of the guarded input: returns
    ({bin_label: constituent volume sum}, total). Mirrors the pinned
    constructor's documented semantics — in-session filter, as-of
    constituent cutoff, explicit [09:30,13:30)/[13:30,close) bins,
    completed-bin emission, OHLC-dropna row exclusion — tracking
    Volume only. This is a verification shadow, not a second
    constructor: any divergence from the real output is a refusal."""
    if as_of is None:
        raise VolumeConservationError(
            {}, detail="cannot verify: as_of is required")
    as_of_ny = pd.Timestamp(as_of).tz_convert(NY)
    closes = _resolve_closes(constructor_module, frame.index, session_closes)
    cends = _constituent_ends(frame, closes, validated_ends)

    local = frame.index.tz_convert(NY)
    per_bin = {}
    total = 0.0
    bin_close = {}
    for pos, ts in enumerate(local):
        d = ts.normalize()
        minute = ts.hour * 60 + ts.minute
        close_min = int((closes[d] - d).total_seconds() // 60)
        if not (SESSION_OPEN_MIN <= minute < close_min):
            continue                                    # out of session
        if not (cends.iloc[pos] <= as_of_ny):
            continue                                    # as-of cutoff
        row = frame.iloc[pos]
        if row[["Open", "High", "Low", "Close"]].isna().any():
            continue                     # constructor's dropna exclusion
        label = d + pd.Timedelta(
            minutes=SESSION_OPEN_MIN if minute < FIRST_BIN_CUTOFF_MIN
            else FIRST_BIN_CUTOFF_MIN)
        if label not in bin_close:
            if minute < FIRST_BIN_CUTOFF_MIN:
                bin_close[label] = min(
                    d + pd.Timedelta(minutes=FIRST_BIN_CUTOFF_MIN), closes[d])
            else:
                bin_close[label] = closes[d]
        if not (bin_close[label] <= as_of_ny):
            continue                                    # incomplete bin
        per_bin[label] = per_bin.get(label, 0.0) + float(row["Volume"])
        total += float(row["Volume"])
    return per_bin, total


def assert_volume_conservation(constructor_module, frame_in, frame_out, *,
                               session_closes=None, as_of=None,
                               validated_ends=None):
    """Post-construction whole-frame law: per-bin output Volume ==
    the shadow expectation for that bin, no missing or extra bins,
    and Σ output == Σ constructed-span input. Any divergence raises
    VolumeConservationError naming every offending bin."""
    expected, exp_total = expected_bin_volumes(
        constructor_module, frame_in, session_closes=session_closes,
        as_of=as_of, validated_ends=validated_ends)
    got = {}
    for ts, row in frame_out.iterrows():
        got[pd.Timestamp(ts)] = float(row["Volume"])
    mismatches = {}
    for label, exp in expected.items():
        if label not in got:
            mismatches[str(label)] = {"expected": exp, "got": None}
        elif got[label] != exp:
            mismatches[str(label)] = {"expected": exp, "got": got[label]}
    for label, val in got.items():
        if label not in expected:
            mismatches[str(label)] = {"expected": None, "got": val}
    got_total = sum(got.values())
    if got_total != exp_total:
        mismatches["__total__"] = {"expected": exp_total, "got": got_total}
    if mismatches:
        raise VolumeConservationError(mismatches,
                                      detail="constructed volumes diverge "
                                             "from constituent input volumes")
    return {"per_bin": expected, "total": exp_total}


# ---------------------------------------------------------------- the guard

def guarded_construct_4h(constructor_module, frame, *args, **kwargs):
    """
    Fail-closed wrapper around a constructor module's construct_4h.

    Pre-checks (constructor never invoked on refusal):
      duplicate timestamps → timezone basis → strictly monotonic →
      finite OHLCV (v3) → exact expected index (repair -91,
      mandatory; derived from the session_closes session table) →
      interval_end exactness (v3; only when the frame carries an
      interval_end column) → calendar SHA binding (v3; only when
      the caller supplies expected_calendar_sha256).
    Post-checks: output duplicate-free, then whole-frame volume
    conservation against a shadow binning of the guarded input.
    On valid input the constructor's output is returned unmodified.
    """
    expected_calendar_sha256 = kwargs.pop("expected_calendar_sha256", None)
    assert_no_duplicate_timestamps(frame.index, stage="input_1h")
    assert_timezone(frame.index, stage="input_1h")
    assert_monotonic_increasing(frame.index, stage="input_1h")
    assert_finite_ohlcv(frame, stage="input_1h")
    assert_expected_index(frame, kwargs.get("session_closes"),
                          stage="input_1h")
    assert_interval_end_exactness(
        constructor_module, frame,
        session_closes=kwargs.get("session_closes"), stage="input_1h")
    assert_calendar_binding(kwargs.get("session_closes"),
                            expected_calendar_sha256,
                            stage="input_1h")
    out = constructor_module.construct_4h(frame, *args, **kwargs)
    assert_no_duplicate_timestamps(out.index, stage="output_4h")
    assert_volume_conservation(
        constructor_module, frame, out,
        session_closes=kwargs.get("session_closes"),
        as_of=kwargs.get("as_of"),
        validated_ends=kwargs.get("validated_ends"))
    return out
