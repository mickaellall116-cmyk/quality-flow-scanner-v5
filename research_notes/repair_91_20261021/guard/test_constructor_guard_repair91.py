#!/usr/bin/env python3
"""
test_constructor_guard_repair91.py — REPAIR -91 FIX 2 sabotage suite.

The -84/-89 guard DEFINED the -82 H1 exact index equality
(assert_index_equality) but guarded_construct_4h never invoked it,
so a shifted / dropped / off-grid stamp sequence — monotonic,
duplicate-free, correctly zoned — passed the guard untouched.
These fixtures prove the repaired path enforces the exact ordered
expected index (derived from the session table) as a mandatory
step, before the constructor is invoked (spy-verified).
"""
import hashlib
import importlib.util
import sys
import warnings
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


def expect_refusal(name, fn, spy, code=None):
    msg = None
    try:
        fn()
    except Exception as e:  # noqa: BLE001 - any guard refusal class
        msg = str(e)
    ok = msg is not None and spy.calls == 0
    if code is not None:
        ok = ok and code in msg
    case(name, ok, f"msg={msg} spy={spy.calls}")
    return msg


def main():
    mod = load_constructor()
    print(f"constructor copy pin verified: {PIN[:12]}…")
    df = build()
    kw = dict(session_closes=closes(), as_of=AS_OF)

    # R91-G1 permuted index (two stamps swapped) -> refused, spy 0;
    # and the equality step itself names it (direct invocation).
    order = list(range(len(df)))
    i1 = df.index.get_loc(pd.Timestamp("2024-01-02 10:30", tz=NY))
    i2 = df.index.get_loc(pd.Timestamp("2024-01-02 11:30", tz=NY))
    order[i1], order[i2] = order[i2], order[i1]
    df_swap = df.iloc[order]
    spy = Spy(mod)
    expect_refusal("R91_G1_permuted_refused_spy0",
                   lambda: guard.guarded_construct_4h(
                       spy, df_swap, "FIXTURE", **kw), spy)
    try:
        guard.assert_expected_index(df_swap, closes())
        case("R91_G1_equality_step_names_permutation", False, "no raise")
    except guard.IndexMismatchError as e:
        case("R91_G1_equality_step_names_permutation",
             guard.INDEX_MISMATCH_CODE in str(e), str(e))

    # R91-G2 all stamps shifted +1h (monotonic, dup-free) -> INDEX_MISMATCH
    df_shift = df.copy()
    df_shift.index = df_shift.index + pd.Timedelta(hours=1)
    spy = Spy(mod)
    expect_refusal("R91_G2_shifted_refused_index_mismatch",
                   lambda: guard.guarded_construct_4h(
                       spy, df_shift, "FIXTURE", **kw), spy,
                   code=guard.INDEX_MISMATCH_CODE)

    # R91-G3 one stamp dropped -> INDEX_MISMATCH
    df_drop = df.drop(pd.Timestamp("2024-01-02 11:30", tz=NY))
    spy = Spy(mod)
    expect_refusal("R91_G3_dropped_stamp_refused_index_mismatch",
                   lambda: guard.guarded_construct_4h(
                       spy, df_drop, "FIXTURE", **kw), spy,
                   code=guard.INDEX_MISMATCH_CODE)

    # R91-G4 off-grid stamp substituted in-order (10:30 -> 10:45;
    # monotonicity survives, only exact-index enforcement catches it)
    idx = list(df.index)
    idx[i1] = pd.Timestamp("2024-01-02 10:45", tz=NY)
    df_off = df.copy()
    df_off.index = pd.DatetimeIndex(idx)
    spy = Spy(mod)
    expect_refusal("R91_G4_offgrid_refused_index_mismatch",
                   lambda: guard.guarded_construct_4h(
                       spy, df_off, "FIXTURE", **kw), spy,
                   code=guard.INDEX_MISMATCH_CODE)

    # R91-G5 no session table -> fail-closed refusal (step not skippable)
    spy = Spy(mod)
    expect_refusal("R91_G5_no_session_table_refused",
                   lambda: guard.guarded_construct_4h(
                       spy, df, "FIXTURE", as_of=AS_OF), spy,
                   code=guard.INDEX_MISMATCH_CODE)

    # R91-G6 clean path: byte-identical to unguarded, spy invoked once
    spy = Spy(mod)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        guarded = guard.guarded_construct_4h(spy, df, "FIXTURE", **kw)
        unguarded = mod.construct_4h(df, "FIXTURE", **kw)
    case("R91_G6_clean_byte_identical",
         guarded.to_csv().encode() == unguarded.to_csv().encode())
    case("R91_G6_clean_spy_invoked_once", spy.calls == 1,
         f"spy={spy.calls}")

    n = sum(1 for _, ok in RESULTS if ok)
    print(f"\n{n}/{len(RESULTS)} checks passed")
    return 0 if n == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
