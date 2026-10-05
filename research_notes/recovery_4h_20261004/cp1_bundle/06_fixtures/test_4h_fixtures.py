"""Phase A fixtures + byte-identity proofs for the 4H recovery pre-run package.

Target under test: scanner_rules.resample_closed_4h_session_anchored
(candidate canonical 4H constructor).

Task 1 — DST/session fixtures on synthetic 1H data (items 1-11).
Task 2 — byte-identity proofs (comparisons a, b, c).

Constraints: synthetic data only (no network); the only real data touched is
the existing local backtest_cache/v3/h4_*.pkl for comparison (b). No
production code is modified — this module is test-only.

Run:  python3 test_4h_fixtures.py
      pytest test_4h_fixtures.py   (test_* functions)
"""

import ast
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from scanner_rules import resample_closed_4h_session_anchored as anchored  # noqa: E402

NY = "America/New_York"
UTC = "UTC"
FIXTURE_DIR = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# Synthetic 1H builders
# --------------------------------------------------------------------------

def make_1h_sessions(days, n_rows=7, start="09:30", tz=NY, seed_base=100.0):
    """Build deterministic synthetic 1H OHLCV rows, tz-aware, labeled at bar open.

    days: list of 'YYYY-MM-DD' session dates.
    Each day: n_rows hourly rows starting at `start` local time.
    OHLCV is a deterministic function of (day_index, row_index) so expected
    bars can be hand-computed: Open=base+i, High=Open+0.6, Low=Open-0.4,
    Close=Open+0.2, Volume=1000+i*10 (int64, day-invariant so overlapping
    windows produce identical rows for identical dates).
    """
    frames = []
    for di, d in enumerate(days):
        idx = pd.date_range(f"{d} {start}", periods=n_rows, freq="1h", tz=tz)
        n = len(idx)
        i = np.arange(n, dtype=float)
        base = seed_base + di * 10.0
        o = base + i
        frames.append(pd.DataFrame({
            "Open": o,
            "High": o + 0.6,
            "Low": o - 0.4,
            "Close": o + 0.2,
            "Volume": (1000 + i * 10).astype("int64"),
        }, index=idx))
    out = pd.concat(frames).sort_index()
    out.index.name = None
    return out


def empty_1h(tz=NY):
    return pd.DataFrame(
        {"Open": [], "High": [], "Low": [], "Close": [], "Volume": []},
        index=pd.DatetimeIndex([], tz=tz, name=None),
    ).astype({"Open": "float64", "High": "float64", "Low": "float64",
              "Close": "float64", "Volume": "int64"})


def expected_bar(rows):
    """Hand-computed 4H bar from a frame of 1H rows (Open first, H max, L min,
    C last, V sum)."""
    return {
        "Open": float(rows["Open"].iloc[0]),
        "High": float(rows["High"].max()),
        "Low": float(rows["Low"].min()),
        "Close": float(rows["Close"].iloc[-1]),
        "Volume": int(rows["Volume"].sum()),
    }


def expected_session_vwap(rows):
    """Hand-computed cumulative session VWAP at the last row of `rows`."""
    typical = (rows["High"] + rows["Low"] + rows["Close"]) / 3.0
    pv = (typical * rows["Volume"]).cumsum()
    vol = rows["Volume"].cumsum()
    return float((pv / vol).iloc[-1])


def assert_bar(bars, label, exp):
    row = bars.loc[label]
    for col, val in exp.items():
        got = row[col]
        assert got == val, f"bar {label} {col}: got {got}, expected {val}"


def frame_hash(df):
    h = hashlib.sha256()
    h.update(pd.util.hash_pandas_object(df, index=True).values.tobytes())
    h.update(str(df.index.tz).encode())
    h.update(",".join(df.columns).encode())
    return h.hexdigest()


def now_et(s):
    return pd.Timestamp(s, tz=NY)


# --------------------------------------------------------------------------
# Task 1 — fixtures
# --------------------------------------------------------------------------

def test_01_spring_forward():
    """Spring-forward DST transition: 2026-03-08 (Sunday). Fri 2026-03-06 is
    EST (-05:00), Mon 2026-03-09 is EDT (-04:00). Bars must land on
    09:30/13:30 wall-clock both days."""
    days = ["2026-03-06", "2026-03-09"]
    df = make_1h_sessions(days)
    bars = anchored(df, "TEST", now=now_et("2026-03-10 12:00"))
    exp_idx = pd.DatetimeIndex([
        "2026-03-06 09:30-05:00", "2026-03-06 13:30-05:00",
        "2026-03-09 09:30-04:00", "2026-03-09 13:30-04:00",
    ], tz=NY, name=None)
    pd.testing.assert_index_equal(bars.index, exp_idx)
    assert len(bars) == 4
    rows = df
    assert_bar(bars, exp_idx[0], expected_bar(rows.iloc[0:4]))
    assert_bar(bars, exp_idx[1], expected_bar(rows.iloc[4:7]))
    assert_bar(bars, exp_idx[2], expected_bar(rows.iloc[7:11]))
    assert_bar(bars, exp_idx[3], expected_bar(rows.iloc[11:14]))
    assert str(bars.index.tz) == NY


def test_02_fall_back():
    """Fall-back DST transition: 2026-11-01 (Sunday). Fri 2026-10-30 is EDT
    (-04:00), Mon 2026-11-02 is EST (-05:00). Same 09:30/13:30 verification."""
    days = ["2026-10-30", "2026-11-02"]
    df = make_1h_sessions(days)
    bars = anchored(df, "TEST", now=now_et("2026-11-03 12:00"))
    exp_idx = pd.DatetimeIndex([
        "2026-10-30 09:30-04:00", "2026-10-30 13:30-04:00",
        "2026-11-02 09:30-05:00", "2026-11-02 13:30-05:00",
    ], tz=NY, name=None)
    pd.testing.assert_index_equal(bars.index, exp_idx)
    assert len(bars) == 4
    assert_bar(bars, exp_idx[0], expected_bar(df.iloc[0:4]))
    assert_bar(bars, exp_idx[1], expected_bar(df.iloc[4:7]))
    assert_bar(bars, exp_idx[2], expected_bar(df.iloc[7:11]))
    assert_bar(bars, exp_idx[3], expected_bar(df.iloc[11:14]))
    assert str(bars.index.tz) == NY


def test_03_normal_day():
    """Full session -> exactly 2 bars (09:30, 13:30) with correct OHLCV."""
    df = make_1h_sessions(["2026-10-02"])
    bars = anchored(df, "TEST", now=now_et("2026-10-03 12:00"))
    exp_idx = pd.DatetimeIndex(["2026-10-02 09:30-04:00",
                                "2026-10-02 13:30-04:00"], tz=NY, name=None)
    pd.testing.assert_index_equal(bars.index, exp_idx)
    assert len(bars) == 2
    assert_bar(bars, exp_idx[0], expected_bar(df.iloc[0:4]))
    assert_bar(bars, exp_idx[1], expected_bar(df.iloc[4:7]))
    # SessionVWAP spot check: last value of the morning bar = cumulative VWAP
    # over that session's rows up to 12:30.
    got = float(bars.loc[exp_idx[0], "SessionVWAP"])
    exp = expected_session_vwap(df.iloc[0:4])
    assert got == exp, f"SessionVWAP {got} != {exp}"
    assert bars.attrs["last_bar_start_at"] == "2026-10-02T13:30:00-04:00"
    assert bars.attrs["last_bar_close_at"] == "2026-10-02T16:00:00-04:00"


def test_04_half_day():
    """2026-11-27 (13:00 close per XNYS) -> exactly 1 bar; last_bar_close_at
    = 13:00-05:00."""
    df = make_1h_sessions(["2026-11-27"], n_rows=4)  # 09:30..12:30 only
    bars = anchored(df, "TEST", now=now_et("2026-11-27 18:00"))
    exp_idx = pd.DatetimeIndex(["2026-11-27 09:30-05:00"], tz=NY, name=None)
    pd.testing.assert_index_equal(bars.index, exp_idx)
    assert len(bars) == 1
    assert_bar(bars, exp_idx[0], expected_bar(df))
    assert bars.attrs["last_bar_start_at"] == "2026-11-27T09:30:00-05:00"
    assert bars.attrs["last_bar_close_at"] == "2026-11-27T13:00:00-05:00"


def test_05_holiday():
    """2026-12-25 (Friday, market closed) -> zero bars, empty frame."""
    df = empty_1h()
    bars = anchored(df, "TEST", now=now_et("2026-12-26 12:00"))
    assert len(bars) == 0
    assert bars.empty


def test_06_every_slot_five_day_week():
    """Both 09:30 and 13:30 slots appear on every day of a 5-day week."""
    days = ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09"]
    df = make_1h_sessions(days)
    bars = anchored(df, "TEST", now=now_et("2026-10-10 12:00"))
    assert len(bars) == 10, f"expected 10 bars, got {len(bars)}"
    local = bars.index.tz_convert(NY)
    for d in days:
        day_bars = local[local.normalize() == pd.Timestamp(d, tz=NY)]
        slots = sorted((t.hour, t.minute) for t in day_bars)
        assert slots == [(9, 30), (13, 30)], f"{d}: {slots}"


def test_07_missing_mid_session_bars():
    """Drop 11:30/12:30 rows -> bars still correct from present rows."""
    df = make_1h_sessions(["2026-10-02"])
    keep = [t for t in df.index
            if (t.hour, t.minute) not in ((11, 30), (12, 30))]
    df = df.loc[keep]
    bars = anchored(df, "TEST", now=now_et("2026-10-03 12:00"))
    assert len(bars) == 2
    exp_idx = pd.DatetimeIndex(["2026-10-02 09:30-04:00",
                                "2026-10-02 13:30-04:00"], tz=NY, name=None)
    pd.testing.assert_index_equal(bars.index, exp_idx)
    assert_bar(bars, exp_idx[0], expected_bar(df.iloc[0:2]))  # 09:30, 10:30
    assert_bar(bars, exp_idx[1], expected_bar(df.iloc[2:5]))  # 13:30..15:30


def test_08_forming_bar_exclusion():
    """now inside the afternoon bar (15:00) -> only the morning bar."""
    df = make_1h_sessions(["2026-10-02"])
    bars = anchored(df, "TEST", now=now_et("2026-10-02 15:00"))
    exp_idx = pd.DatetimeIndex(["2026-10-02 09:30-04:00"], tz=NY, name=None)
    pd.testing.assert_index_equal(bars.index, exp_idx)
    assert len(bars) == 1
    assert_bar(bars, exp_idx[0], expected_bar(df.iloc[0:4]))
    assert bars.attrs["last_bar_close_at"] == "2026-10-02T13:30:00-04:00"


def test_09_future_row_truncation():
    """Rows after `now` are dropped BEFORE binning (causal cutoff).

    NOTE: with the forming-bar exclusion in place, truncation can never change
    a *returned closed* bar (any bin holding a future row is forming and gets
    dropped regardless), so this fixture asserts the code path as an
    equivalence: full-data@now == pre-truncated-data@now. Truncation is
    defense-in-depth, verified here as an invariant.
    """
    df = make_1h_sessions(["2026-10-02"])
    now = now_et("2026-10-02 14:00")
    full = anchored(df, "TEST", now=now)
    truncated = anchored(df[df.index <= now], "TEST", now=now)
    pd.testing.assert_frame_equal(full, truncated)
    # Morning bar is closed and fully specified by its 4 rows.
    exp_idx = pd.DatetimeIndex(["2026-10-02 09:30-04:00"], tz=NY, name=None)
    pd.testing.assert_index_equal(full.index, exp_idx)
    assert_bar(full, exp_idx[0], expected_bar(df.iloc[0:4]))


def test_10_exact_1330_boundary():
    """A 1H row stamped exactly 13:30 belongs to the afternoon bar
    (closed-left)."""
    df = make_1h_sessions(["2026-10-02"])
    bars = anchored(df, "TEST", now=now_et("2026-10-03 12:00"))
    morn = pd.Timestamp("2026-10-02 09:30-04:00", tz=NY)
    aft = pd.Timestamp("2026-10-02 13:30-04:00", tz=NY)
    assert bars.loc[aft, "Open"] == float(df.loc[pd.Timestamp(
        "2026-10-02 13:30-04:00", tz=NY), "Open"])
    assert bars.loc[morn, "Close"] == float(df.loc[pd.Timestamp(
        "2026-10-02 12:30-04:00", tz=NY), "Close"])
    # Afternoon bar spans exactly the 13:30/14:30/15:30 rows.
    assert_bar(bars, aft, expected_bar(df.iloc[4:7]))


def test_11_crypto_utc_bins():
    """'-USD' symbol -> 00/04/08/12/16/20 UTC bins, no session logic."""
    df = make_1h_sessions(["2026-10-02"], n_rows=24, start="00:00", tz=UTC)
    now = pd.Timestamp("2026-10-03 12:00", tz=UTC)
    bars = anchored(df, "BTC-USD", now=now)
    exp_idx = pd.DatetimeIndex(
        [f"2026-10-02 {h:02d}:00+00:00" for h in (0, 4, 8, 12, 16, 20)],
        tz=UTC, name=None)
    pd.testing.assert_index_equal(bars.index, exp_idx)
    assert len(bars) == 6
    for k, h in enumerate((0, 4, 8, 12, 16, 20)):
        assert_bar(bars, exp_idx[k], expected_bar(df.iloc[k * 4:(k + 1) * 4]))
    assert "SessionVWAP" not in bars.columns
    assert bars.attrs["last_bar_start_at"] == "2026-10-02T20:00:00+00:00"
    assert bars.attrs["last_bar_close_at"] == "2026-10-03T00:00:00+00:00"


# --------------------------------------------------------------------------
# Task 2 — byte-identity proofs
# --------------------------------------------------------------------------

def _load_fetch4h_resample():
    """Load ONLY the per-day-origin resample_4h from
    canonical_baseline/scripts/fetch_4h.py via AST (avoids importing the
    script's module-level network/fetch code). Test-only."""
    path = REPO / "canonical_baseline" / "scripts" / "fetch_4h.py"
    src = path.read_text()
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "resample_4h")
    ns = {"pd": pd, "AGG": {"Open": "first", "High": "max", "Low": "min",
                            "Close": "last", "Volume": "sum"}}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), "exec"), ns)
    return ns["resample_4h"]


def _compare_frames(name, a, b, cols):
    """Return dict describing OHLCV+index comparison on `cols`."""
    result = {"name": name, "n_a": len(a), "n_b": len(b)}
    try:
        pd.testing.assert_frame_equal(a[cols].sort_index(), b[cols].sort_index(),
                                      check_exact=True)
        result["identical"] = True
    except AssertionError as e:
        result["identical"] = False
        result["diff"] = str(e)[:2000]
    return result


def comparison_a_session_anchored_vs_fetch4h():
    """(a) Session-anchored (standalone) vs per-day-origin resample_4h from
    canonical_baseline/scripts/fetch_4h.py, from IDENTICAL synthetic 1H
    inputs. All bars closed (now after session end) so the anchored path's
    forming-bar exclusion is a no-op."""
    resample_4h = _load_fetch4h_resample()
    days = pd.bdate_range("2026-08-24", "2026-09-04").strftime("%Y-%m-%d").tolist()
    df = make_1h_sessions(days, seed_base=200.0)
    now = now_et("2026-09-05 12:00")
    a = anchored(df, "TEST", now=now)
    b = resample_4h(df)
    cols = ["Open", "High", "Low", "Close", "Volume"]
    cmp = _compare_frames("a: anchored vs fetch_4h resample_4h", a, b, cols)
    deltas = []
    # Column-set delta: SessionVWAP exists only on the anchored side.
    only_a = [c for c in a.columns if c not in b.columns]
    only_b = [c for c in b.columns if c not in a.columns]
    if only_a:
        deltas.append(f"columns only in session-anchored: {only_a}")
    if only_b:
        deltas.append(f"columns only in fetch_4h resample_4h: {only_b}")
    # Attr delta.
    if a.attrs != b.attrs:
        deltas.append(f"attrs differ: anchored={a.attrs} fetch_4h={b.attrs}")
    # Known semantic deltas that do NOT fire on this complete synthetic input:
    # - fetch_4h drops only NaN-Close rows; anchored requires all of OHLC
    #   (no NaNs here -> no-op).
    # - fetch_4h has no forming-bar exclusion / no causal cutoff (all bars
    #   closed here -> no-op).
    cmp["deltas"] = deltas
    cmp["input_hash"] = frame_hash(df)
    cmp["n_input_rows"] = len(df)
    return cmp


def comparison_b_cached_h4_grid_audit():
    """(b) Session-anchored grid vs backtest_cache/v3/h4_*.pkl.

    The cache was built from real Yahoo 1H (not available here), so a
    bar-by-bar value replay is impossible. What IS verifiable without the 1H
    inputs: every cached bar label must sit on the session-anchored grid
    (09:30/13:30 ET per trading day for equities; 00/04/08/12/16/20 UTC for
    crypto). Any legacy-grid label (e.g. 06:30/10:30/14:30) would be a delta.
    """
    out = {"name": "b: cached h4 grid audit", "symbols": {}}
    for sym in ("AAPL", "BTC-USD"):
        path = REPO / "backtest_cache" / "v3" / f"h4_{sym}.pkl"
        h4 = pd.read_pickle(path)
        is_crypto = sym.upper().endswith("-USD")
        utc = h4.index.tz_convert(UTC)
        local = h4.index.tz_convert(NY)
        if is_crypto:
            # Crypto grid is UTC-anchored; wall-clock (NY) labels legitimately
            # shift with DST, so only the UTC slot set is meaningful.
            ok_utc_slots = {(h, 0) for h in (0, 4, 8, 12, 16, 20)}
            ok_local_slots = {(t.hour, t.minute) for t in local}  # any
        else:
            ok_utc_slots = None  # session grid is wall-clock, not UTC-fixed
            ok_local_slots = {(9, 30), (13, 30)}
        bad_utc = ([str(t) for t in utc
                    if (t.hour, t.minute) not in ok_utc_slots]
                   if ok_utc_slots else [])
        bad_local = [str(t) for t in local
                     if (t.hour, t.minute) not in ok_local_slots]
        per_day = local.normalize().value_counts()
        # Local-label regimes (detects DST wall-clock shifts of a UTC-fixed
        # grid): consecutive date runs sharing the same slot set.
        df = pd.DataFrame(
            {"slot": [(t.hour, t.minute) for t in local]}, index=local)
        day_slots = df.groupby(df.index.date)["slot"].apply(
            lambda s: tuple(sorted(set(s))))
        regimes = []
        for _, grp in day_slots.groupby((day_slots != day_slots.shift()).cumsum()):
            regimes.append({"from": str(grp.index[0]), "to": str(grp.index[-1]),
                            "slots": list(grp.iloc[0]), "days": len(grp)})
        single_bar_days = sorted(str(d) for d, n in per_day.items() if n == 1)
        out["symbols"][sym] = {
            "bars": len(h4),
            "first": str(local[0]),
            "last": str(local[-1]),
            "utc_slots_observed": sorted(
                set((t.hour, t.minute) for t in utc)),
            "n_off_utc_grid": len(bad_utc),
            "n_off_session_grid_local": len(bad_local),
            "off_session_grid_local_sample": bad_local[:8],
            "local_label_regimes": regimes,
            "single_bar_days": single_bar_days,
            "columns": list(h4.columns),
            "has_attrs": bool(h4.attrs),
        }
    out["grid_aligned"] = all(
        v["n_off_session_grid_local"] == 0 for v in out["symbols"].values())
    return out


def comparison_c_window_invariance():
    """(c) Two download-window lengths (30d vs 180d of synthetic 1H, same end
    date) through session-anchored -> byte-identical bars (the legacy
    origin='start_day' defect made the grid depend on window start)."""
    end = pd.Timestamp("2026-09-30")
    days_180 = pd.bdate_range(end=end, periods=180).strftime("%Y-%m-%d").tolist()
    days_30 = days_180[-30:]
    df_180 = make_1h_sessions(days_180, seed_base=300.0)
    # Identical values on overlapping days: seed depends on day index, so the
    # 30d slice reuses the same per-day seeds as days 150..179 of the 180d run.
    df_30 = make_1h_sessions(days_30, seed_base=300.0 + (len(days_180) - 30) * 10.0)
    now = now_et("2026-10-01 12:00")
    a = anchored(df_180, "TEST", now=now)
    b = anchored(df_30, "TEST", now=now)
    overlap = b.index
    cmp = _compare_frames("c: 180d vs 30d window", a.loc[overlap], b,
                          list(a.columns))
    # Attrs byte-identity too.
    cmp["attrs_identical"] = (a.attrs == b.attrs)
    cmp["input_hash_180d"] = frame_hash(df_180)
    cmp["input_hash_30d"] = frame_hash(df_30)
    return cmp


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

FIXTURES = [
    ("1 spring-forward DST", test_01_spring_forward),
    ("2 fall-back DST", test_02_fall_back),
    ("3 normal day", test_03_normal_day),
    ("4 half-day 13:00 close", test_04_half_day),
    ("5 holiday", test_05_holiday),
    ("6 every slot 5-day week", test_06_every_slot_five_day_week),
    ("7 missing mid-session bars", test_07_missing_mid_session_bars),
    ("8 forming-bar exclusion", test_08_forming_bar_exclusion),
    ("9 future-row truncation", test_09_future_row_truncation),
    ("10 exact 13:30 boundary", test_10_exact_1330_boundary),
    ("11 crypto UTC bins", test_11_crypto_utc_bins),
]


def run_all():
    results = {"fixtures": [], "comparisons": {}}
    for name, fn in FIXTURES:
        try:
            fn()
            results["fixtures"].append({"name": name, "pass": True})
        except Exception as e:  # noqa: BLE001
            results["fixtures"].append(
                {"name": name, "pass": False, "error": f"{type(e).__name__}: {e}"})
    for key, fn in (("a", comparison_a_session_anchored_vs_fetch4h),
                    ("b", comparison_b_cached_h4_grid_audit),
                    ("c", comparison_c_window_invariance)):
        try:
            results["comparisons"][key] = fn()
            results["comparisons"][key]["ran"] = True
        except Exception as e:  # noqa: BLE001
            results["comparisons"][key] = {
                "ran": False, "error": f"{type(e).__name__}: {e}"}
    return results


if __name__ == "__main__":
    import json
    res = run_all()
    n_pass = sum(1 for f in res["fixtures"] if f["pass"])
    print(f"fixtures: {n_pass}/{len(res['fixtures'])} passed")
    for f in res["fixtures"]:
        status = "PASS" if f["pass"] else "FAIL"
        print(f"  [{status}] {f['name']}"
              + ("" if f["pass"] else f" -- {f['error']}"))
    for key in ("a", "b", "c"):
        c = res["comparisons"][key]
        if not c.get("ran"):
            print(f"comparison {key}: ERROR -- {c['error']}")
            continue
        if key == "a":
            print(f"comparison a: identical_OHLCV_index={c['identical']} "
                  f"bars={c['n_a']}/{c['n_b']} deltas={c['deltas']}")
            if not c["identical"]:
                print("  DIFF:", c.get("diff"))
        elif key == "b":
            print(f"comparison b: grid_aligned={c['grid_aligned']}")
            for s, v in c["symbols"].items():
                print(f"  {s}: bars={v['bars']} {v['first']}..{v['last']} "
                      f"off_session_grid={v['n_off_session_grid_local']} "
                      f"utc_slots={v['utc_slots_observed']} "
                      f"single_bar_days={v['single_bar_days']}")
                for r in v["local_label_regimes"]:
                    print(f"    regime {r['from']}..{r['to']}: slots={r['slots']} ({r['days']}d)")
        elif key == "c":
            print(f"comparison c: identical={c['identical']} "
                  f"attrs_identical={c['attrs_identical']}")
            if not c["identical"]:
                print("  DIFF:", c.get("diff"))
    (FIXTURE_DIR / "phase_a_results.json").write_text(json.dumps(res, indent=1,
                                                                 default=str))
    print("wrote phase_a_results.json")
