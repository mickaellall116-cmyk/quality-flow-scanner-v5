#!/usr/bin/env python3
"""
test_constructor_hardening.py — SYNTHETIC FIXTURES against a byte-copy
of the PINNED constructor (task -82, item 5).

The copy under test is fixtures/construct_4h_fixture_copy.py, extracted
byte-for-byte from research_notes/pilot_harness/construct_4h.py at
origin/main; this suite REFUSES to run if its SHA-256 differs from the
recorded pin d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd.
The pinned constructor itself is never modified; nothing here is
production code or a production change.

Fixtures:
  T1 INDEX-EQUALITY — constructed 4H frame index must equal the
     expected session-bar index EXACTLY (full sessions -> 09:30+13:30;
     a 13:00 early-close session -> 09:30 only), with aggregation
     spot-checks (Open=first, Volume=sum).
  T2 WARNINGS-AS-ERRORS — the T1 construction must complete under
     warnings.simplefilter('error'); a control probe proves the
     filter is actually engaged.
  T3 DUPLICATE TIMESTAMPS — a duplicated 1H bar must be rejected or
     handled DETERMINISTICALLY: two runs must agree exactly (same
     exception type, or byte-identical output). The observed behavior
     (rejected vs silently merged) is recorded verbatim in the output;
     the hardening spec (../05_CONSTRUCTOR_HARDENING_SPEC.md) states
     the requirement this evidence supports.

Session closes are supplied via the constructor's session_closes
override for every fixture date, so no calendar library is consulted
and the fixture calendar is pinned by this file.
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


def main():
    mod = load_constructor()
    print(f"constructor copy pin verified: {PIN[:12]}…")
    df = build_1h()
    closes = session_closes()

    # T1 — index equality + aggregation.
    bars = mod.construct_4h(df, "FIXTURE", session_closes=closes, as_of=AS_OF)
    case("T1_index_equality", list(bars.index) == EXPECTED_INDEX,
         f"got {[str(t) for t in bars.index]}")
    first = bars.loc[pd.Timestamp("2024-01-02 09:30", tz=NY)]
    exp_open = df.loc[pd.Timestamp("2024-01-02 09:30", tz=NY), "Open"]
    exp_vol = df.loc[[pd.Timestamp(f"2024-01-02 {h}", tz=NY)
                      for h in ["09:30", "10:30", "11:30", "12:30"]], "Volume"].sum()
    case("T1_aggregation", first["Open"] == exp_open and first["Volume"] == exp_vol,
         f"open {first['Open']} vs {exp_open}; vol {first['Volume']} vs {exp_vol}")
    case("T1_early_close_single_bar",
         pd.Timestamp("2024-07-03 13:30", tz=NY) not in bars.index
         and pd.Timestamp("2024-07-03 09:30", tz=NY) in bars.index)

    # T2 — warnings-as-errors, with an engagement control.
    control_raised = False
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        try:
            warnings.warn("engagement probe", UserWarning)
        except UserWarning:
            control_raised = True
    case("T2_filter_engaged_control", control_raised)
    t2_ok, t2_err = True, ""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            bars2 = mod.construct_4h(df, "FIXTURE", session_closes=closes, as_of=AS_OF)
        t2_ok = list(bars2.index) == EXPECTED_INDEX
    except Warning as w:  # a warning raised as error = fixture failure, recorded
        t2_ok, t2_err = False, f"{type(w).__name__}: {w}"
    case("T2_warnings_as_errors_construction", t2_ok, t2_err)

    # T3 — duplicate timestamps: deterministic reject-or-handle.
    dup_ts = pd.Timestamp("2024-01-02 10:30", tz=NY)
    df_dup = pd.concat([df, df.loc[[dup_ts]]]).sample(frac=1.0, random_state=7)

    def run_once():
        try:
            out = mod.construct_4h(df_dup, "FIXTURE", session_closes=closes, as_of=AS_OF)
            return ("frame", hashlib.sha256(out.to_csv().encode()).hexdigest(), out)
        except Exception as e:  # noqa: BLE001 — behavior recording is the point
            return ("raise", type(e).__name__, None)

    kind1, dig1, out1 = run_once()
    kind2, dig2, _ = run_once()
    case("T3_deterministic", kind1 == kind2 and dig1 == dig2,
         f"run1={kind1}/{str(dig1)[:16]} run2={kind2}/{str(dig2)[:16]}")
    if kind1 == "raise":
        print(f"T3_BEHAVIOR: constructor REJECTS duplicates ({dig1})")
        case("T3_behavior_recorded", True, "rejected")
    else:
        bin_vol = out1.loc[pd.Timestamp("2024-01-02 09:30", tz=NY), "Volume"]
        print(f"T3_BEHAVIOR: constructor does NOT reject duplicates; "
              f"duplicated bar is silently merged (09:30 bin Volume={bin_vol} "
              f"vs single-copy expectation {exp_vol})")
        case("T3_behavior_recorded", True,
             f"merged; bin volume {bin_vol} vs {exp_vol} (double-counted)")

    n_pass = sum(1 for _, ok in RESULTS if ok)
    print(f"\n{n_pass}/{len(RESULTS)} checks passed")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
