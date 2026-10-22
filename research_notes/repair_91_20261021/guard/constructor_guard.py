#!/usr/bin/env python3
"""
constructor_guard.py — CANDIDATE guard v2: fail-closed guard for the
pinned 4H constructor boundary (task -89; design: -86 F3, extending
the -84 H3b candidate).

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
"""

import pandas as pd

GUARD_VERSION = "guard-v2-candidate-1"
DUPLICATE_CODE = "CONSTRUCTOR_GUARD_DUPLICATE_TIMESTAMP"
INDEX_MISMATCH_CODE = "CONSTRUCTOR_GUARD_INDEX_MISMATCH"
NON_MONOTONIC_CODE = "CONSTRUCTOR_GUARD_NON_MONOTONIC"
TIMEZONE_CODE = "CONSTRUCTOR_GUARD_TIMEZONE"
VOLUME_CONSERVATION_CODE = "CONSTRUCTOR_GUARD_VOLUME_CONSERVATION"

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
      exact expected index (repair -91, mandatory; derived from the
      session_closes session table).
    Post-checks: output duplicate-free, then whole-frame volume
    conservation against a shadow binning of the guarded input.
    On valid input the constructor's output is returned unmodified.
    """
    assert_no_duplicate_timestamps(frame.index, stage="input_1h")
    assert_timezone(frame.index, stage="input_1h")
    assert_monotonic_increasing(frame.index, stage="input_1h")
    assert_expected_index(frame, kwargs.get("session_closes"),
                          stage="input_1h")
    out = constructor_module.construct_4h(frame, *args, **kwargs)
    assert_no_duplicate_timestamps(out.index, stage="output_4h")
    assert_volume_conservation(
        constructor_module, frame, out,
        session_closes=kwargs.get("session_closes"),
        as_of=kwargs.get("as_of"),
        validated_ends=kwargs.get("validated_ends"))
    return out
