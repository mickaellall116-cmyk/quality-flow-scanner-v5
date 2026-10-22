#!/usr/bin/env python3
"""
test_constructor_guard.py — SYNTHETIC FIXTURES for the H3b candidate
guard (task -84, Part A) wrapping a byte-copy of the PINNED
constructor.

The copy under test is guard/construct_4h_fixture_copy.py (extracted
byte-for-byte for -82 from research_notes/pilot_harness/construct_4h.py
at origin/main); this suite REFUSES to run if its SHA-256 differs from
the pin d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd.
Neither the pinned constructor nor the copy is modified; the guard is
new isolated candidate code (guard/constructor_guard.py).

Fixtures (fixture bars/builders follow -82's T1/T3 construction so the
T3 merge case is the SAME input -82 recorded):
  G1  the -82 T3 duplicated-bar input must now REFUSE with the named
      error, deterministically (identical message on repeat runs).
  G2  a CONFLICTING duplicate (same timestamp, different OHLCV) must
      also REFUSE.
  G3  clean input through the guard must be BYTE-IDENTICAL to the
      unguarded path (no behavior change on valid data).
  G4  the -82 T1 index-equality assertion holds through the guard;
      a wrong expected index raises (negative control: the assertion
      is live).
  G5  warnings-as-errors clean through the guard (engagement control
      included, as in -82 T2).
  G6  fail-closed AT the boundary: on duplicated input the wrapped
      constructor is never invoked (spy module records zero calls).

Session closes are supplied via the constructor's session_closes
override for every fixture date, so no calendar library is consulted.
"""
import hashlib
import importlib.util
import sys
import warnings
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
COPY = HERE / "construct_4h_fixture_copy.py"
PIN = "d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd"
NY = "America/New_York"

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


FULL = [("2024-01-02", 16 * 60), ("2024-01-03", 16 * 60)]
EARLY = [("2024-07-03", 13 * 60)]  # 13:00 early close (fixture calendar)


def build_1h():
    rows = []
    price = 100.0
    for day_s, close_min in FULL + EARLY:
        day = pd.Timestamp(day_s, tz=NY)
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
EXPECTED_INDEX = [
    pd.Timestamp("2024-01-02 09:30", tz=NY), pd.Timestamp("2024-01-02 13:30", tz=NY),
    pd.Timestamp("2024-01-03 09:30", tz=NY), pd.Timestamp("2024-01-03 13:30", tz=NY),
    pd.Timestamp("2024-07-03 09:30", tz=NY),
]
DUP_TS = pd.Timestamp("2024-01-02 10:30", tz=NY)


def t3_dup_input(df):
    """The exact -82 T3 input: one duplicated 1H bar, deterministically shuffled."""
    return pd.concat([df, df.loc[[DUP_TS]]]).sample(frac=1.0, random_state=7)


def main():
    mod = load_constructor()
    print(f"constructor copy pin verified: {PIN[:12]}…")
    df = build_1h()
    closes = session_closes()
    kw = dict(session_closes=closes, as_of=AS_OF)

    # Unguarded reference (the -82 behavior baseline).
    ref = mod.construct_4h(df, "FIXTURE", **kw)
    ref_sha = hashlib.sha256(ref.to_csv().encode()).hexdigest()
    dup_df = t3_dup_input(df)
    merged = mod.construct_4h(dup_df, "FIXTURE", **kw)
    merged_vol = merged.loc[pd.Timestamp("2024-01-02 09:30", tz=NY), "Volume"]
    print(f"unguarded T3 reference: 09:30 bin Volume={merged_vol} "
          f"(the -82 silent-merge value; single-copy expectation 406)")

    # G1 — the -82 T3 input must now REFUSE, deterministically.
    msgs = []
    for _ in range(2):
        try:
            guard.guarded_construct_4h(mod, dup_df, "FIXTURE", **kw)
            msgs.append(None)
        except guard.DuplicateTimestampError as e:
            msgs.append(str(e))
    case("G1_t3_input_refused", msgs[0] is not None and msgs[1] is not None,
         f"error: {msgs[0]}")
    case("G1_refusal_named_error",
         msgs[0] is not None and guard.DUPLICATE_CODE in msgs[0]
         and str(DUP_TS) in msgs[0])
    case("G1_refusal_deterministic", msgs[0] is not None and msgs[0] == msgs[1])

    # G2 — a conflicting duplicate (different values, same timestamp) refuses too.
    conflict_row = df.loc[[DUP_TS]].copy()
    conflict_row.loc[:, ["Open", "High", "Low", "Close", "Volume"]] = \
        [999.0, 1000.0, 998.0, 999.5, 777]
    df_conflict = pd.concat([df, conflict_row])
    g2_msg = None
    try:
        guard.guarded_construct_4h(mod, df_conflict, "FIXTURE", **kw)
    except guard.DuplicateTimestampError as e:
        g2_msg = str(e)
    case("G2_conflicting_duplicate_refused", g2_msg is not None, f"error: {g2_msg}")

    # G3 — clean input: guarded output byte-identical to unguarded.
    guarded = guard.guarded_construct_4h(mod, df, "FIXTURE", **kw)
    guarded_sha = hashlib.sha256(guarded.to_csv().encode()).hexdigest()
    case("G3_clean_byte_identical", guarded_sha == ref_sha,
         f"guarded {guarded_sha[:16]} vs unguarded {ref_sha[:16]}")
    case("G3_clean_frame_equal", guarded.equals(ref))

    # G4 — index equality through the guard + negative control.
    case("G4_index_equality_through_guard",
         guard.assert_index_equality(guarded, EXPECTED_INDEX) is True)
    wrong = EXPECTED_INDEX[:-1]  # drop the early-close bar
    g4_raised = False
    try:
        guard.assert_index_equality(guarded, wrong)
    except guard.IndexMismatchError:
        g4_raised = True
    case("G4_index_assertion_live_negative_control", g4_raised)

    # G5 — warnings-as-errors through the guard, with engagement control.
    control_raised = False
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        try:
            warnings.warn("engagement probe", UserWarning)
        except UserWarning:
            control_raised = True
    case("G5_filter_engaged_control", control_raised)
    g5_ok, g5_err = True, ""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            out5 = guard.guarded_construct_4h(mod, df, "FIXTURE", **kw)
        g5_ok = list(out5.index) == EXPECTED_INDEX
    except Warning as w:
        g5_ok, g5_err = False, f"{type(w).__name__}: {w}"
    case("G5_warnings_as_errors_through_guard", g5_ok, g5_err)

    # G6 — fail-closed at the boundary: constructor never invoked on bad input.
    class Spy:
        def __init__(self, inner):
            self.inner = inner
            self.calls = 0

        def construct_4h(self, *a, **k):
            self.calls += 1
            return self.inner.construct_4h(*a, **k)

    spy = Spy(mod)
    g6_raised = False
    try:
        guard.guarded_construct_4h(spy, dup_df, "FIXTURE", **kw)
    except guard.DuplicateTimestampError:
        g6_raised = True
    case("G6_constructor_not_invoked_on_refusal", g6_raised and spy.calls == 0,
         f"spy calls={spy.calls}")
    ok_out = guard.guarded_construct_4h(spy, df, "FIXTURE", **kw)
    case("G6_spy_clean_path_invokes_once", spy.calls == 1
         and hashlib.sha256(ok_out.to_csv().encode()).hexdigest() == ref_sha)

    n_pass = sum(1 for _, ok in RESULTS if ok)
    print(f"\n{n_pass}/{len(RESULTS)} checks passed")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
