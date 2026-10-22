#!/usr/bin/env python3
"""
test_constructor_guard_v3.py — task -93 guard v3 suite.

Proves the three v3 additions from Claude's -92 HOLD (Issue #1
comment 6343957169): NONFINITE refusal (incl. placeholder NaN rows
and the shadow-NaN alignment), INTERVAL_END grid exactness (incl.
the truncated 3-of-4 bin), and CALENDAR_BINDING (calendar SHA
binding) — plus the preserved floor behaviors (clean path
byte-identical, spy discipline). The -84/-89/-91 suites re-run
against their pristine modules as regressions (see
../TEST_EVIDENCE.md); this suite runs only against the v3 module
in this directory.
"""
import hashlib
import importlib.util
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import constructor_guard as guard  # noqa: E402

NY = "America/New_York"
PIN = "d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd"
RESULTS = []


def case(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name, detail if not cond else "")


def load_constructor():
    raw = (HERE / "construct_4h_fixture_copy.py").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PIN, "constructor pin drift"
    spec = importlib.util.spec_from_file_location(
        "ctor_copy", HERE / "construct_4h_fixture_copy.py")
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

    def __getattr__(self, name):
        return getattr(self.inner, name)


DAYS = ["2024-01-02", "2024-01-03"]


def build():
    rows = []
    price = 100.0
    for d in DAYS:
        day = pd.Timestamp(d, tz=NY)
        for k in range(7):
            m = 570 + 60 * k
            ts = day + pd.Timedelta(minutes=m)
            end = day + pd.Timedelta(minutes=m + 60)
            o = price
            c = price + 0.10
            rows.append((ts, o, max(o, c) + 0.05, min(o, c) - 0.05, c,
                         100 + k, end))
            price = c
    df = pd.DataFrame(rows, columns=["ts", "Open", "High", "Low", "Close",
                                     "Volume", "interval_end"])
    return df.set_index("ts")


def closes():
    out = {}
    for d in DAYS:
        t = pd.Timestamp(d, tz=NY)
        out[t.normalize()] = t + pd.Timedelta(minutes=16 * 60)
    return out


AS_OF = pd.Timestamp("2024-01-04 17:00", tz=NY)


def expect_refusal(name, fn, spy, code):
    msg = None
    try:
        fn()
    except Exception as e:  # noqa: BLE001 - any guard refusal class
        msg = str(e)
    ok = msg is not None and spy.calls == 0 and code in msg
    case(name, ok, f"msg={msg} spy={spy.calls}")
    return msg


def main():
    mod = load_constructor()
    print(f"constructor copy pin verified: {PIN[:12]}…")
    print(f"guard version: {guard.GUARD_VERSION}")
    df = build()
    kw = dict(session_closes=closes(), as_of=AS_OF)

    case("V3_G0_version_string",
         guard.GUARD_VERSION == "guard-v3-candidate-1",
         guard.GUARD_VERSION)

    # Clean path with calendar binding satisfied: byte-identical to
    # the unguarded constructor, spy invoked exactly once.
    good_sha = guard.calendar_sha256(closes())
    spy = Spy(mod)
    out = guard.guarded_construct_4h(
        spy, df, "FIXTURE", expected_calendar_sha256=good_sha, **kw)
    raw = mod.construct_4h(df, "FIXTURE", **kw)
    case("V3_G1_clean_bound_byte_identical",
         spy.calls == 1 and out.equals(raw))

    # NONFINITE: NaN Close.
    bad = df.copy()
    bad.iloc[3, bad.columns.get_loc("Close")] = float("nan")
    spy = Spy(mod)
    expect_refusal("V3_G2_nan_close_refused",
                   lambda: guard.guarded_construct_4h(spy, bad, "FIXTURE", **kw),
                   spy, guard.NONFINITE_CODE)

    # NONFINITE: NaN Volume.
    bad = df.copy()
    bad.iloc[5, bad.columns.get_loc("Volume")] = float("nan")
    spy = Spy(mod)
    expect_refusal("V3_G3_nan_volume_refused",
                   lambda: guard.guarded_construct_4h(spy, bad, "FIXTURE", **kw),
                   spy, guard.NONFINITE_CODE)

    # NONFINITE: +inf High.
    bad = df.copy()
    bad.iloc[0, bad.columns.get_loc("High")] = float("inf")
    spy = Spy(mod)
    expect_refusal("V3_G4_inf_high_refused",
                   lambda: guard.guarded_construct_4h(spy, bad, "FIXTURE", **kw),
                   spy, guard.NONFINITE_CODE)

    # NONFINITE: placeholder row — a grid stamp whose OHLCV are all
    # NaN (the vendor placeholder shape). v2 passed this through to
    # the constructor's dropna; v3 refuses at the boundary.
    bad = df.copy()
    last = len(bad) - 1
    for col in ("Open", "High", "Low", "Close", "Volume"):
        bad.iloc[last, bad.columns.get_loc(col)] = float("nan")
    spy = Spy(mod)
    expect_refusal("V3_G5_placeholder_nan_row_refused",
                   lambda: guard.guarded_construct_4h(spy, bad, "FIXTURE", **kw),
                   spy, guard.NONFINITE_CODE)

    # Shadow-NaN alignment, both halves proven: (a) the v2 shadow
    # mirror EXCLUDES the placeholder row's session-mates silently
    # (its binning skips the NaN row — the divergence); (b) the v3
    # guarded path refuses the same frame (G5). Here: (a) only.
    per_bin, total = guard.expected_bin_volumes(
        mod, bad, session_closes=closes(), as_of=AS_OF)
    clean_bin, clean_total = guard.expected_bin_volumes(
        mod, df, session_closes=closes(), as_of=AS_OF)
    case("V3_G6_shadow_excludes_nan_row_silently",
         total < clean_total and per_bin != clean_bin,
         f"shadow_total={total} clean_total={clean_total}")

    # INTERVAL_END: the fixture convention (start+60m everywhere,
    # final bar 16:30) is a grid end for every bar -> exactness OK.
    case("V3_G7_interval_end_nominal_convention_ok",
         guard.assert_interval_end_exactness(mod, df,
                                             session_closes=closes()))

    # INTERVAL_END: final bar stamped at the session close (16:00)
    # is the other grid convention -> OK.
    alt = df.copy()
    ends = list(alt["interval_end"])
    for pos, ts in enumerate(alt.index):
        if ts.hour == 15 and ts.minute == 30:
            ends[pos] = ts.normalize() + pd.Timedelta(minutes=16 * 60)
    alt["interval_end"] = ends
    case("V3_G8_interval_end_close_convention_ok",
         guard.assert_interval_end_exactness(mod, alt,
                                             session_closes=closes()))

    # INTERVAL_END: one mid-session bar's end truncated by 30m.
    bad = df.copy()
    ends = list(bad["interval_end"])
    ends[2] = ends[2] - pd.Timedelta(minutes=30)
    bad["interval_end"] = ends
    spy = Spy(mod)
    expect_refusal("V3_G9_interval_end_truncated_refused",
                   lambda: guard.guarded_construct_4h(spy, bad, "FIXTURE", **kw),
                   spy, guard.INTERVAL_END_CODE)

    # INTERVAL_END, the truncated 3-of-4 bin: day-1's 12:30 bar is
    # absent and the 11:30 bar's stated end is stretched to the bin
    # end 13:30, claiming a complete bin. The exactness assert names
    # it directly; the wrapper refuses it too (spy 0).
    trunc = df.drop(pd.Timestamp("2024-01-02 12:30", tz=NY))
    ends = list(trunc["interval_end"])
    pos = list(trunc.index).index(pd.Timestamp("2024-01-02 11:30", tz=NY))
    ends[pos] = pd.Timestamp("2024-01-02 13:30", tz=NY)
    trunc["interval_end"] = ends
    try:
        guard.assert_interval_end_exactness(mod, trunc,
                                            session_closes=closes())
        case("V3_G10a_truncated_3of4_bin_named", False, "no raise")
    except guard.IntervalEndError as e:
        case("V3_G10a_truncated_3of4_bin_named",
             guard.INTERVAL_END_CODE in str(e), str(e))
    spy = Spy(mod)
    msg = None
    try:
        guard.guarded_construct_4h(spy, trunc, "FIXTURE", **kw)
    except Exception as e:  # noqa: BLE001
        msg = str(e)
    case("V3_G10b_truncated_3of4_bin_wrapper_refused",
         msg is not None and spy.calls == 0, f"msg={msg} spy={spy.calls}")

    # CALENDAR_BINDING: wrong expected hash (table intact) refuses
    # at the binding step, spy 0.
    spy = Spy(mod)
    expect_refusal("V3_G11_calendar_binding_wrong_sha_refused",
                   lambda: guard.guarded_construct_4h(
                       spy, df, "FIXTURE",
                       expected_calendar_sha256="0" * 64, **kw),
                   spy, guard.CALENDAR_BINDING_CODE)

    # CALENDAR_BINDING: a tampered table (one close moved) does not
    # hash to the true table's pin — binding layer names it directly.
    tampered = closes()
    k0 = sorted(tampered)[0]
    tampered[k0] = tampered[k0] - pd.Timedelta(hours=1)
    try:
        guard.assert_calendar_binding(tampered, good_sha)
        case("V3_G12_calendar_binding_tamper_named", False, "no raise")
    except guard.CalendarBindingError as e:
        case("V3_G12_calendar_binding_tamper_named",
             guard.CALENDAR_BINDING_CODE in str(e), str(e))

    # CALENDAR_BINDING: hash is order-insensitive and
    # content-sensitive (deterministic pin semantics).
    shuffled = dict(reversed(list(closes().items())))
    extended = closes()
    t = pd.Timestamp("2024-01-04", tz=NY)
    extended[t.normalize()] = t + pd.Timedelta(minutes=16 * 60)
    case("V3_G13_calendar_sha_deterministic",
         guard.calendar_sha256(shuffled) == good_sha
         and guard.calendar_sha256(extended) != good_sha)

    # No interval_end column: the v3 exactness step is a no-op, as
    # in v2. (A full wrapper run on a column-less frame is not
    # possible against this fixture copy: the pinned constructor's
    # own derivation path imports validate_input, which the fixture
    # copy does not carry — that is why every chain fixture supplies
    # explicit interval_end. Asserted here at the guard layer.)
    bare = df.drop(columns=["interval_end"])
    case("V3_G14_no_interval_end_column_noop",
         guard.assert_interval_end_exactness(mod, bare,
                                             session_closes=closes()))

    n_pass = sum(1 for _, ok in RESULTS if ok)
    print(f"{n_pass}/{len(RESULTS)} checks passed")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
