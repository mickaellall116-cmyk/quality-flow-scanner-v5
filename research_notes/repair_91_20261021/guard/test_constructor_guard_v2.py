#!/usr/bin/env python3
"""
test_constructor_guard_v2.py — SYNTHETIC FIXTURES for the guard v2
candidate (task -89; design -86 F3), extending -84's H3b suite.

Structure:
  FLOOR — -84's test_constructor_guard.py (byte-copy in this
          directory, sha256 06029fd2…) is executed UNCHANGED as a
          subprocess. Because this directory's constructor_guard.py
          IS the v2 candidate, the floor's 12 cases run against v2:
          v1 behavior is the regression floor.
  V2-1  two swapped 1h bars -> NON_MONOTONIC refusal, spy silent.
  V2-2  naive index -> TIMEZONE refusal, spy silent.
  V2-3  fixed-offset (-05:00) index spanning 2024-03-10 (DST) ->
        TIMEZONE refusal, spy silent; AND the unguarded behavior is
        asserted against the PINNED pandas-2.2.3 record established
        at this package's build: the unguarded constructor completes
        under warnings-as-errors with NO warning and emits silently
        mis-binned bars (2024-03-11 bins 303/312 vs the NY-true
        406/315; output csv sha256 pinned below). If a future
        environment changes that behavior, this case fails loudly —
        that is its purpose.
  V2-4  wrong-zone (UTC) index -> TIMEZONE refusal, spy silent.
  V2-5  the -82 T1 sessions through v2: conservation identities hold
        per bin and in total (406/315 per full day, 406 early-close,
        total 1848); guarded output byte-identical to the unguarded
        path AND to the -84 clean case (csv sha prefix 077e0c6b81509624,
        recorded in -84 TEST_EVIDENCE G3).
  V2-6  sabotage control: a wrapper drops one constituent bar
        between the guard's pre-check and aggregation ->
        VOLUME_CONSERVATION refusal naming the bin (expected 406,
        got 304); the constructor WAS invoked (post-check refusal).

The constructor under test is the pin-verified byte-copy
(construct_4h_fixture_copy.py, sha256 d47e8df1…); neither it nor the
pinned original is modified. Session closes are supplied via the
session_closes override for every fixture date, so no calendar
library is consulted.
"""
import hashlib
import importlib.util
import subprocess
import sys
import warnings
from datetime import timezone, timedelta
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
COPY = HERE / "construct_4h_fixture_copy.py"
PIN = "d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd"
NY = "America/New_York"

# Pinned unguarded behavior record for V2-3 (pandas 2.2.3, established
# empirically at -89 build time; see ../TEST_EVIDENCE.md).
V23_UNGUARDED_CSV_SHA = ("90cc21e7efdbec9ad7aae6008b2982a031b41f88e8e"
                         "dbda7e33c7b87e7f32f6b")
V84_CLEAN_SHA_PREFIX = "077e0c6b81509624"  # -84 TEST_EVIDENCE, G3

sys.path.insert(0, str(HERE))
import constructor_guard as guard  # noqa: E402

RESULTS = []


def case(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")


def load_constructor():
    digest = hashlib.sha256(COPY.read_bytes()).hexdigest()
    if digest != PIN:
        print(f"FATAL: fixture copy sha256 {digest} != pin {PIN}; refusing to run")
        sys.exit(2)
    spec = importlib.util.spec_from_file_location("construct_4h_fixture_copy", COPY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Spy:
    def __init__(self, inner):
        self.inner = inner
        self.calls = 0

    def construct_4h(self, *a, **k):
        self.calls += 1
        return self.inner.construct_4h(*a, **k)


# ------------------------------------------------------- -84 fixture family

FULL = [("2024-01-02", 16 * 60), ("2024-01-03", 16 * 60)]
EARLY = [("2024-07-03", 13 * 60)]


def build_1h(tz=NY):
    """The -84 builder (-84 test_constructor_guard.py, build_1h),
    parametrized only by the index tz so V2-2/V2-4 can stamp the same
    wall times naive / in UTC."""
    rows = []
    price = 100.0
    for day_s, close_min in FULL + EARLY:
        day = pd.Timestamp(day_s, tz=tz) if tz else pd.Timestamp(day_s)
        starts = []
        m = 570
        while m < close_min:
            starts.append(m)
            m += 60
        for i, m in enumerate(starts):
            ts = day + pd.Timedelta(minutes=m)
            end_min = m + 60 if m + 60 <= close_min else close_min
            end = day + pd.Timedelta(minutes=end_min)
            o = price
            c = price + 0.10
            rows.append((ts, o, max(o, c) + 0.05, min(o, c) - 0.05, c,
                         100 + i, end))
            price = c
    df = pd.DataFrame(rows, columns=["ts", "Open", "High", "Low", "Close",
                                     "Volume", "interval_end"])
    return df.set_index("ts")


def session_closes():
    out = {}
    for day_s, close_min in FULL + EARLY:
        d = pd.Timestamp(day_s, tz=NY)
        out[d.normalize()] = d + pd.Timedelta(minutes=close_min)
    return out


AS_OF = pd.Timestamp("2024-07-03 17:00", tz=NY)

# ------------------------------------------------------- V2-3 fixture family

FIXED = timezone(timedelta(hours=-5))
DST_DAYS = ["2024-03-08", "2024-03-11"]  # Fri (EST) / Mon (EDT)


def build_fixed_offset():
    """Wall-clock 09:30..15:30 stamps at a FIXED -05:00 offset across
    the 2024-03-10 spring-forward boundary (the vendor failure class:
    correct on Fri, one hour stale on Mon)."""
    rows = []
    price = 100.0
    for day_s in DST_DAYS:
        day = pd.Timestamp(day_s)
        for k in range(7):
            m = 570 + 60 * k
            ts = (day + pd.Timedelta(minutes=m)).replace(tzinfo=FIXED)
            end = (day + pd.Timedelta(minutes=m + 60)).replace(tzinfo=FIXED)
            o = price
            c = price + 0.10
            rows.append((pd.Timestamp(ts), o, max(o, c) + 0.05,
                         min(o, c) - 0.05, c, 100 + k, pd.Timestamp(end)))
            price = c
    df = pd.DataFrame(rows, columns=["ts", "Open", "High", "Low", "Close",
                                     "Volume", "interval_end"])
    return df.set_index("ts")


def dst_closes():
    out = {}
    for day_s in DST_DAYS:
        d = pd.Timestamp(day_s, tz=NY)
        out[d.normalize()] = d + pd.Timedelta(minutes=16 * 60)
    return out


DST_AS_OF = pd.Timestamp("2024-03-12 17:00", tz=NY)


def expect_refusal(name, exc_type, code, fn, spy=None):
    msg = None
    try:
        fn()
    except exc_type as e:
        msg = str(e)
    except Exception as e:  # wrong refusal class is a failure, loudly
        case(name, False, f"wrong exception {type(e).__name__}: {e}")
        return None
    ok = msg is not None and code in msg
    if spy is not None:
        ok = ok and spy.calls == 0
    case(name, ok, f"error: {msg}" + (f" spy calls={spy.calls}" if spy else ""))
    return msg


def main():
    mod = load_constructor()
    print(f"constructor copy pin verified: {PIN[:12]}…")
    print(f"guard version: {guard.GUARD_VERSION}")

    # ---- version / code-stability anchors
    case("V2_version_anchor",
         guard.GUARD_VERSION == "guard-v2-candidate-1"
         and guard.DUPLICATE_CODE == "CONSTRUCTOR_GUARD_DUPLICATE_TIMESTAMP"
         and guard.NON_MONOTONIC_CODE == "CONSTRUCTOR_GUARD_NON_MONOTONIC"
         and guard.TIMEZONE_CODE == "CONSTRUCTOR_GUARD_TIMEZONE"
         and guard.VOLUME_CONSERVATION_CODE
         == "CONSTRUCTOR_GUARD_VOLUME_CONSERVATION")

    # ---- FLOOR: -84's 12 cases, unchanged, against the v2 module
    floor = subprocess.run(
        [sys.executable, str(HERE / "test_constructor_guard.py")],
        cwd=str(HERE), capture_output=True, text=True)
    sys.stdout.write(floor.stdout)
    if floor.returncode != 0:
        sys.stdout.write(floor.stderr)
    case("V2_floor_subprocess_exit0", floor.returncode == 0,
         f"rc={floor.returncode}")
    case("V2_floor_12_of_12", "12/12 checks passed" in floor.stdout)

    closes = session_closes()
    kw = dict(session_closes=closes, as_of=AS_OF)
    df = build_1h()

    # ---- V2-1 swapped bars -> NON_MONOTONIC, spy silent
    i1 = df.index.get_loc(pd.Timestamp("2024-01-02 10:30", tz=NY))
    i2 = df.index.get_loc(pd.Timestamp("2024-01-02 11:30", tz=NY))
    order = list(range(len(df)))
    order[i1], order[i2] = order[i2], order[i1]
    df_swap = df.iloc[order]
    spy = Spy(mod)
    msg = expect_refusal("V2_1_swapped_bars_non_monotonic",
                         guard.NonMonotonicError, guard.NON_MONOTONIC_CODE,
                         lambda: guard.guarded_construct_4h(
                             spy, df_swap, "FIXTURE", **kw), spy)
    if msg is not None:
        case("V2_1_refusal_names_first_violation",
             "2024-01-02 11:30" in msg and "2024-01-02 10:30" in msg, msg)

    # ---- V2-2 naive index -> TIMEZONE, spy silent
    spy = Spy(mod)
    expect_refusal("V2_2_naive_index_timezone",
                   guard.TimezoneError, guard.TIMEZONE_CODE,
                   lambda: guard.guarded_construct_4h(
                       spy, build_1h(tz=None), "FIXTURE", **kw), spy)

    # ---- V2-4 wrong-zone (UTC) index -> TIMEZONE, spy silent
    spy = Spy(mod)
    expect_refusal("V2_4_utc_index_timezone",
                   guard.TimezoneError, guard.TIMEZONE_CODE,
                   lambda: guard.guarded_construct_4h(
                       spy, build_1h(tz="UTC"), "FIXTURE", **kw), spy)

    # ---- V2-3 fixed-offset across DST -> TIMEZONE; unguarded record pinned
    df_fixed = build_fixed_offset()
    kw_dst = dict(session_closes=dst_closes(), as_of=DST_AS_OF)
    spy = Spy(mod)
    expect_refusal("V2_3_fixed_offset_timezone",
                   guard.TimezoneError, guard.TIMEZONE_CODE,
                   lambda: guard.guarded_construct_4h(
                       spy, df_fixed, "FIXTURE", **kw_dst), spy)
    unguarded_err = ""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            out_fixed = mod.construct_4h(df_fixed, "FIXTURE", **kw_dst)
        sha_fixed = hashlib.sha256(out_fixed.to_csv().encode()).hexdigest()
        mar11 = out_fixed.loc["2024-03-11"]
        vols = [int(mar11.iloc[0]["Volume"]), int(mar11.iloc[1]["Volume"])]
        case("V2_3_unguarded_silent_misalignment_pinned",
             sha_fixed == V23_UNGUARDED_CSV_SHA and vols == [303, 312],
             f"unguarded csv sha {sha_fixed[:16]}… 2024-03-11 bins {vols} "
             f"(NY-true would be [406, 315]; no warning raised)")
    except Warning as w:
        case("V2_3_unguarded_silent_misalignment_pinned", False,
             f"unguarded path raised a warning, contradicting the pinned "
             f"record: {type(w).__name__}: {w}")
    except Exception as e:
        case("V2_3_unguarded_silent_misalignment_pinned", False,
             f"unguarded path raised {type(e).__name__}: {e}")

    # ---- V2-5 conservation identities + byte-identity on the T1 sessions
    guarded = guard.guarded_construct_4h(mod, df, "FIXTURE", **kw)
    ref = mod.construct_4h(df, "FIXTURE", **kw)
    g_sha = hashlib.sha256(guarded.to_csv().encode()).hexdigest()
    case("V2_5_guarded_byte_identical_to_unguarded",
         g_sha == hashlib.sha256(ref.to_csv().encode()).hexdigest())
    case("V2_5_matches_84_clean_case", g_sha.startswith(V84_CLEAN_SHA_PREFIX),
         f"guarded csv sha {g_sha[:16]}…")
    cons = guard.assert_volume_conservation(mod, df, guarded, **kw)
    exp_bins = {
        pd.Timestamp("2024-01-02 09:30", tz=NY): 406.0,
        pd.Timestamp("2024-01-02 13:30", tz=NY): 315.0,
        pd.Timestamp("2024-01-03 09:30", tz=NY): 406.0,
        pd.Timestamp("2024-01-03 13:30", tz=NY): 315.0,
        pd.Timestamp("2024-07-03 09:30", tz=NY): 406.0,
    }
    case("V2_5_conservation_per_bin", cons["per_bin"] == exp_bins,
         f"per_bin={ {str(k): v for k, v in cons['per_bin'].items()} }")
    case("V2_5_conservation_total", cons["total"] == 1848.0,
         f"total={cons['total']}")

    # ---- V2-6 sabotage: constituent dropped after the guard's pre-check
    class Saboteur:
        def __init__(self, inner):
            self.inner = inner
            self.calls = 0

        def construct_4h(self, frame, *a, **k):
            self.calls += 1
            dropped = frame.drop(
                pd.Timestamp("2024-01-02 11:30", tz=NY))
            return self.inner.construct_4h(dropped, *a, **k)

    sab = Saboteur(mod)
    msg = None
    try:
        guard.guarded_construct_4h(sab, df, "FIXTURE", **kw)
    except guard.VolumeConservationError as e:
        msg = str(e)
    case("V2_6_sabotage_volume_conservation_refusal",
         msg is not None and guard.VOLUME_CONSERVATION_CODE in msg
         and sab.calls == 1,
         f"error: {msg} saboteur calls={sab.calls}")
    if msg is not None:
        case("V2_6_refusal_names_bin_and_values",
             "2024-01-02 09:30" in msg and "406" in msg and "304" in msg, msg)

    n_pass = sum(1 for _, ok in RESULTS if ok)
    print(f"\n{n_pass}/{len(RESULTS)} checks passed")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
