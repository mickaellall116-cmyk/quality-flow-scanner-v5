"""Adversarial parity suite — EQUITY43-CORRECTED-FWD-v1 candidate observer.

QF-EQUITY43-CORRECTED-FORWARD-PARITY-BUILD-20261023-15. ALL inputs are
synthetic invented prices over REAL pinned session-table dates. The suite
proves, against the pinned -13 successor engine used as the reference
implementation:

  T01-T07  corrected grid formation (full / early-close), holiday refusal,
           DST in both directions (wall-anchored bins, correct UTC
           instants), legacy 06:30-grid rejection, phantom post-close
           exclusion;
  T08-T11  fail-closed data refusal: price-moving zero-volume poison with
           one-symbol isolation, missing-hour session gap, late-bar
           no-backfill, duplicate / out-of-order rejection;
  T12      streaming observer == batch reference: identical 4H bars and
           identical candidate events (identity, terms, exit reason,
           censoring) over a 299-bar invented series with closed trades
           and a terminal censored position;
  T13      as-of SPY benchmark: identical to the -09 fork construction,
           and a mutation of the unfinished day's close is invisible to
           decision-time RS (the B1 property) while the midnight
           construction leaks it;
  T14      portfolio cross-implementation parity on a contested
           multi-symbol scenario: identical dispositions at gross / 4bps /
           25bps incl. rank and sector-gate skips, and identical outcomes
           when the observer's feed order is permuted (canonical order);
  T15      restart / idempotency: snapshot + journal resume mid-feed
           reproduces the uninterrupted journal byte-for-byte; re-feeding
           a processed bar is refused as DUPLICATE;
  T16      journal integrity: intact verifies; a tampered record and a
           truncated journal are both detected against the external
           anchor;
  T17      PAUSED sentinel gate: an armed observer with the sentinel
           present emits zero decision events (all WITHHELD); without it,
           decisions flow;
  T18      terminal censoring: the censored candidate enters selection,
           is marked at the last completed bar close, and has NO exit
           event, NO exit price and NO fabricated cash flow.

Exit 0 iff every test passes. Prints one line per test + SUMMARY.
"""
import hashlib
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
STAGE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else \
    os.path.abspath(os.path.join(PKG, "..", ".."))
for p in (STAGE, os.path.join(STAGE, "engine_successor"),
          os.path.join(STAGE, "engine_successor", "pine_stack"),
          os.path.join(STAGE, "engine_successor", "pine_ranking"),
          os.path.join(STAGE, "engine_successor", "pine_exposure"),
          os.path.join(STAGE, "engine_successor", "pine_signal_quality"),
          os.path.join(PKG, "observer")):
    sys.path.insert(0, p)

import pandas as pd  # noqa: E402

import fwd_observer as fo  # noqa: E402
import asof_benchmark  # noqa: E402
import pine_backtest as pb  # noqa: E402
import pine_stack as st  # noqa: E402
import scanner_rules as sr  # noqa: E402
from pine_ranking import compute_features  # noqa: E402
from pine_exposure import SECTOR  # noqa: E402
from pine_signal_quality import bench_ret  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "ref13", os.path.join(STAGE, "reference_run_study13.py"))
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)

ET = "America/New_York"
TABLE_JSON = json.load(open(os.path.join(STAGE, "session_table.json")))
FULL_TABLE = fo.SessionTable(TABLE_JSON)
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}", flush=True)


def subset_table(dates):
    return fo.SessionTable({"sessions": [s for s in TABLE_JSON["sessions"]
                                         if s["date"] in dates]})


def session_starts(date):
    sess = {s["date"]: s for s in TABLE_JSON["sessions"]}[date]
    close = int(sess["close"][:2]) * 60 + int(sess["close"][3:5])
    out, mins = [], 570
    while mins < close:
        out.append(f"{mins // 60:02d}:{mins % 60:02d}")
        mins += 60
    return out


def flat_rows(date, price=100.0, vol=1000.0, skip=(), extra=()):
    rows = [{"datetime": f"{date} {s}:00", "open": price, "high": price,
             "low": price, "close": price, "volume": vol}
            for s in session_starts(date) if s not in skip]
    rows.extend(extra)
    return sorted(rows, key=lambda r: r["datetime"])


def make_observer(symbols, table=FULL_TABLE, **kw):
    tmp = tempfile.mkdtemp(prefix="fwdobs_")
    j = fo.Journal(os.path.join(tmp, "journal.jsonl"),
                   os.path.join(tmp, "anchor.json"))
    return fo.ForwardObserver(table, j, pb, symbols, **kw), j, tmp


def feed_all(obs, rows_by_symbol):
    merged = []
    for sym, rows in rows_by_symbol.items():
        merged.extend((r["datetime"], sym, r) for r in rows)
    merged.sort(key=lambda x: (x[0], x[1]))
    events = []
    for _, sym, r in merged:
        events.extend(obs.ingest(sym, r))
    events.extend(obs.flush())
    return events


# ------------------------------------------------------- synthetic series
def trend_targets(sessions, drop_rate=0.990, drop_from=250, drop_to=262):
    """Deterministic invented 4H target bars: bull run with pullbacks,
    a sharp drop (stop exits), then a recovery that ends mid-trade."""
    def close_at(k):
        if k < drop_from:
            base = 100 * 1.0045 ** k
            if k % 16 in (13, 14):
                base *= 0.982 ** (k % 16 - 12)
            return base
        peak = 100 * 1.0045 ** (drop_from - 1)
        if k < drop_to:
            return peak * drop_rate ** (k - drop_from + 1)
        return peak * drop_rate ** (drop_to - drop_from) \
            * 1.006 ** (k - drop_to + 1)
    targets, k, prev = [], 0, 99.5
    for s in sessions:
        nb = 1 if s["close"] == "13:00" else 2
        for bi in range(nb):
            c = close_at(k)
            targets.append({"date": s["date"],
                            "bstart": "09:30" if bi == 0 else "13:30",
                            "O": prev, "H": max(prev, c) * 1.0015,
                            "L": min(prev, c) * 0.9985, "C": c,
                            "V": 2.0e6 if k % 2 == 0 else 1.2e6})
            prev = c
            k += 1
    return targets


def expand_targets(targets):
    rows = []
    for t in targets:
        memb = [s for s in session_starts(t["date"])
                if (s < "13:30") == (t["bstart"] == "09:30")]
        m = len(memb)
        O, C, H, L, V = t["O"], t["C"], t["H"], t["L"], t["V"]
        closes = [O * (C / O) ** ((j + 1) / m) for j in range(m)]
        opens = [O] + closes[:-1]
        highs = [max(opens[j], closes[j]) for j in range(m)]
        lows = [min(opens[j], closes[j]) for j in range(m)]
        highs[0] = H
        lows[-1] = L
        for j in range(m):
            rows.append({"datetime": f"{t['date']} {memb[j]}:00",
                         "open": opens[j], "high": highs[j],
                         "low": lows[j], "close": closes[j],
                         "volume": V / m})
    return sorted(rows, key=lambda r: r["datetime"])


def batch_reference(symbol, rows):
    """The -13 batch construction on the same invented bytes."""
    idx = pd.DatetimeIndex([pd.Timestamp(r["datetime"]) for r in rows]) \
        .tz_localize(ET)
    frame = pd.DataFrame([{"Open": r["open"], "High": r["high"],
                           "Low": r["low"], "Close": r["close"],
                           "Volume": r["volume"]} for r in rows], index=idx)
    bars = sr.resample_closed_4h_session_anchored(
        frame, symbol, now=pd.Timestamp("2100-01-01", tz=ET))
    data = pb.add_pine_indicators(bars)
    tr, cens, sg = ref.gen_candidates_censored(symbol, data)
    return bars, tr + cens, sg


def decision_fields(rec):
    return {"symbol": rec["symbol"], "signal_idx": rec["signal_idx"],
            "entry": rec["entry"], "stop": rec["stop"], "tp1": rec["tp1"],
            "tp1_hit": rec["tp1_hit"],
            "entry_time": str(rec["entry_time"]),
            "signal_time": rec["signal_time"],
            "censored": bool(rec.get("censored")),
            "exit_time": (None if rec["exit_time"] is None
                          else str(rec["exit_time"])),
            "reason": rec["reason"], "hold_bars": rec["hold_bars"]}


def first_sessions(n=150):
    return [s for s in TABLE_JSON["sessions"]
            if s["date"] >= "2023-10-19"][:n]


# ------------------------------------------------------------------- tests
def t01_grid_full():
    obs, j, _ = make_observer(["AAA"], subset_table({"2024-03-07"}))
    rows = flat_rows("2024-03-07", price=50.0, vol=700.0)
    rows[0] = {**rows[0], "open": 49.0, "high": 51.0, "low": 48.5,
               "close": 50.5}
    evs = feed_all(obs, {"AAA": rows})
    bars = [e["bar"] for e in evs if e["type"] == "BAR"]
    ok = len(bars) == 2 \
        and [b["ts"].strftime("%H:%M") for b in bars] == ["09:30", "13:30"] \
        and [b["decision_instant"].strftime("%H:%M") for b in bars] == \
            ["13:30", "16:00"] \
        and bars[0]["Open"] == 49.0 and bars[0]["High"] == 51.0 \
        and bars[0]["Low"] == 48.5 and bars[0]["Close"] == 50.0 \
        and bars[0]["Volume"] == 2800.0 and bars[1]["Volume"] == 2100.0
    check("T01_grid_full_session", ok,
          f"bars={len(bars)} starts={[b['ts'].strftime('%H:%M') for b in bars]}")


def t02_grid_early_close():
    obs, j, _ = make_observer(["AAA"], subset_table({"2024-11-29"}))
    evs = feed_all(obs, {"AAA": flat_rows("2024-11-29")})
    bars = [e["bar"] for e in evs if e["type"] == "BAR"]
    ok = len(bars) == 1 and bars[0]["ts"].strftime("%H:%M") == "09:30" \
        and bars[0]["decision_instant"].strftime("%H:%M") == "13:00"
    check("T02_grid_early_close", ok, f"bars={len(bars)}")


def t03_holiday_refused():
    obs, j, _ = make_observer(["AAA"], FULL_TABLE)
    holiday = [{"datetime": f"2024-11-28 {s}:00", "open": 100.0,
                "high": 100.0, "low": 100.0, "close": 100.0,
                "volume": 1000.0}
               for s in ("09:30", "10:30", "11:30", "12:30", "13:30",
                         "14:30", "15:30")]
    evs = feed_all(obs, {"AAA": holiday})
    rej = [e for e in evs if e["type"] == "REJECTED"]
    bars = [e for e in evs if e["type"] == "BAR"]
    check("T03_holiday_refused",
          len(rej) == 7 and all(e["class"] == fo.REJ_UNKNOWN_SESSION
                                for e in rej) and not bars,
          f"rejected={len(rej)} bars={len(bars)}")


def t04_dst_spring():
    tbl = subset_table({"2024-03-08", "2024-03-11"})
    obs, j, _ = make_observer(["AAA"], tbl)
    evs = feed_all(obs, {"AAA": flat_rows("2024-03-08")
                         + flat_rows("2024-03-11")})
    bars = [e["bar"] for e in evs if e["type"] == "BAR"]
    off = [b["ts"].utcoffset().total_seconds() / 3600 for b in bars]
    dec_utc = [b["decision_instant"].tz_convert("UTC").strftime("%H:%M")
               for b in bars if b["ts"].strftime("%H:%M") == "09:30"]
    check("T04_dst_spring_forward",
          off == [-5.0, -5.0, -4.0, -4.0] and dec_utc == ["18:30", "17:30"],
          f"offsets={off} first-bin decision UTC={dec_utc}")


def t05_dst_fall():
    tbl = subset_table({"2024-11-01", "2024-11-04"})
    obs, j, _ = make_observer(["AAA"], tbl)
    evs = feed_all(obs, {"AAA": flat_rows("2024-11-01")
                         + flat_rows("2024-11-04")})
    bars = [e["bar"] for e in evs if e["type"] == "BAR"]
    off = [b["ts"].utcoffset().total_seconds() / 3600 for b in bars]
    dec_utc = [b["decision_instant"].tz_convert("UTC").strftime("%H:%M")
               for b in bars if b["ts"].strftime("%H:%M") == "09:30"]
    check("T05_dst_fall_back",
          off == [-4.0, -4.0, -5.0, -5.0] and dec_utc == ["17:30", "18:30"],
          f"offsets={off} first-bin decision UTC={dec_utc}")


def t06_legacy_grid_rejected():
    obs, j, _ = make_observer(["AAA"], subset_table({"2024-03-07"}))
    legacy = [{"datetime": f"2024-03-07 {s}:00", "open": 1.0, "high": 1.0,
               "low": 1.0, "close": 1.0, "volume": 10.0}
              for s in ("06:30", "10:30", "14:30")]
    evs = feed_all(obs, {"AAA": legacy})
    rej = [e for e in evs if e["type"] == "REJECTED"]
    bars = [e for e in evs if e["type"] == "BAR"]
    check("T06_legacy_grid_rejected",
          any(e["class"] == fo.REJ_OFF_GRID for e in rej) and not bars,
          f"rejected={[(e['stamp'][11:16], e['class']) for e in rej]} "
          f"bars={len(bars)}")


def t07_phantom_postclose():
    obs, j, _ = make_observer(["AAA"], subset_table({"2024-11-29"}))
    rows = flat_rows("2024-11-29") + [
        {"datetime": "2024-11-29 15:30:00", "open": 101.0, "high": 101.0,
         "low": 101.0, "close": 101.0, "volume": 5.0}]
    evs = feed_all(obs, {"AAA": rows})
    excl = [e for e in evs if e["type"] == "EXCLUDED_POSTCLOSE"]
    bars = [e["bar"] for e in evs if e["type"] == "BAR"]
    check("T07_phantom_postclose_excluded",
          len(excl) == 1 and len(bars) == 1
          and bars[0]["Close"] == 100.0,
          f"excluded={len(excl)} bars={len(bars)}")


def t08_poison_isolation():
    tbl = subset_table({"2024-03-07"})
    obs, j, _ = make_observer(["AAA", "BBB"], tbl)
    bad = flat_rows("2024-03-07")
    bad[1] = {**bad[1], "open": 100.0, "high": 105.0, "low": 99.0,
              "close": 104.0, "volume": 0.0}
    evs = feed_all(obs, {"AAA": bad, "BBB": flat_rows("2024-03-07")})
    rej = [e for e in evs if e["type"] == "REJECTED"
           and e["class"] == fo.POISON_VOLUME]
    bars_a = [e for e in evs if e["type"] == "BAR" and e["symbol"] == "AAA"]
    bars_b = [e for e in evs if e["type"] == "BAR" and e["symbol"] == "BBB"]
    check("T08_poison_volume_isolation",
          len(rej) == 1 and not bars_a and len(bars_b) == 2
          and not obs.candidates(),
          f"poison={len(rej)} AAA bars={len(bars_a)} BBB bars={len(bars_b)}")


def t09_missing_hour_gap():
    obs, j, _ = make_observer(["AAA"],
                              subset_table({"2024-03-07", "2024-03-08"}))
    rows = flat_rows("2024-03-07", skip=("11:30",)) \
        + flat_rows("2024-03-08")
    evs = feed_all(obs, {"AAA": rows})
    inc = [e for e in evs if e["type"] == "SESSION_INCOMPLETE"]
    bars = [e["bar"] for e in evs if e["type"] == "BAR"]
    check("T09_missing_hour_gap",
          len(inc) == 1 and inc[0]["missing"] == ["11:30"]
          and len(bars) == 2
          and all(b["ts"].strftime("%Y-%m-%d") == "2024-03-08"
                  for b in bars),
          f"incomplete={len(inc)} bars={len(bars)}")


def t10_late_bar_no_backfill():
    obs, j, _ = make_observer(["AAA"], subset_table({"2024-03-07"}))
    feed_all(obs, {"AAA": flat_rows("2024-03-07", skip=("11:30",))})
    late = obs.ingest("AAA", {"datetime": "2024-03-07 11:30:00",
                              "open": 100.0, "high": 100.0, "low": 100.0,
                              "close": 100.0, "volume": 1000.0})
    rej = [e for e in late if e["type"] == "REJECTED"]
    check("T10_late_bar_no_backfill",
          len(rej) == 1 and rej[0]["class"] == fo.REJ_LATE_BAR
          and not obs.bars["AAA"],
          f"late class={[e['class'] for e in rej]} bars={len(obs.bars['AAA'])}")


def t11_duplicate_out_of_order():
    obs, j, _ = make_observer(["AAA"], subset_table({"2024-03-07"}))
    r0 = flat_rows("2024-03-07")
    obs.ingest("AAA", r0[0])
    dup = obs.ingest("AAA", r0[0])
    obs.ingest("AAA", r0[2])
    ooo = obs.ingest("AAA", r0[1])
    classes = [e["class"] for e in dup + ooo if e["type"] == "REJECTED"]
    check("T11_duplicate_out_of_order",
          classes == [fo.REJ_DUPLICATE, fo.REJ_OUT_OF_ORDER],
          f"classes={classes}")


def _trend_run(symbols_offsets):
    """symbols_offsets: {symbol: (drop_rate, drop_from, drop_to)} ->
    (observer, batch candidates per symbol, observer bars per symbol,
     batch bars per symbol)"""
    sessions = first_sessions(150)
    rows_by, batch = {}, {}
    for sym, (dr, df_, dt_) in symbols_offsets.items():
        rows = expand_targets(trend_targets(sessions, dr, df_, dt_))
        rows_by[sym] = rows
        batch[sym] = batch_reference(sym, rows)
    obs, j, _ = make_observer(list(symbols_offsets))
    feed_all(obs, rows_by)
    return obs, batch, j


def t12_streaming_vs_batch():
    obs, batch, _ = _trend_run({"TEST": (0.990, 250, 262)})
    bars_b, cands_b, sg_b = batch["TEST"]
    bars_o = obs.bars_frame("TEST")
    bars_ok = len(bars_o) == len(bars_b) and bars_o.index.equals(bars_b.index) \
        and all((bars_o[c].to_numpy() == bars_b[c].to_numpy()).all()
                for c in ("Open", "High", "Low", "Close", "Volume")) \
        and (bars_o["SessionVWAP"] - bars_b["SessionVWAP"]).abs().max() < 1e-9
    obs_c = sorted((decision_fields(r) for r in obs.candidates()),
                   key=lambda r: (r["symbol"], r["signal_idx"]))
    ref_c = sorted((decision_fields(r) for r in cands_b),
                   key=lambda r: (r["symbol"], r["signal_idx"]))
    same = len(obs_c) == len(ref_c) and all(
        a == b for a, b in zip(obs_c, ref_c))
    closed = [r for r in ref_c if not r["censored"]]
    cens = [r for r in ref_c if r["censored"]]
    sg_o = sum(m.skipped_gap for m in obs.machines.values())
    check("T12_streaming_vs_batch_candidates",
          bars_ok and same and len(closed) >= 1 and len(cens) == 1
          and sg_o == sg_b,
          f"bars_ok={bars_ok} candidates obs={len(obs_c)} ref={len(ref_c)} "
          f"closed={len(closed)} censored={len(cens)} identical={same}")


def t13_asof_benchmark():
    sessions = first_sessions(40)
    rows = expand_targets(trend_targets(sessions))
    idx = pd.DatetimeIndex([pd.Timestamp(r["datetime"]) for r in rows]) \
        .tz_localize(ET)
    frame = pd.DataFrame([{"Open": r["open"], "High": r["high"],
                           "Low": r["low"], "Close": r["close"],
                           "Volume": r["volume"]} for r in rows], index=idx)
    bench_asof = asof_benchmark.build_daily_asof(frame)
    bench_mid = asof_benchmark.build_daily_midnight(frame)
    d = sessions[25]["date"]
    t1 = pd.Timestamp(f"{d} 13:30").tz_localize(ET).tz_convert("UTC")
    t0 = pd.Timestamp(f"{sessions[5]['date']} 13:30").tz_localize(ET) \
        .tz_convert("UTC")
    base_asof = bench_ret(bench_asof, t0, t1)
    base_mid = bench_ret(bench_mid, t0, t1)
    # mutate the unfinished day's close x40 in the raw frame
    mut = frame.copy()
    day = mut.index.strftime("%Y-%m-%d") == d
    mut.loc[day, "Close"] = mut.loc[day, "Close"] * 40
    mut_asof = bench_ret(asof_benchmark.build_daily_asof(mut), t0, t1)
    mut_mid = bench_ret(asof_benchmark.build_daily_midnight(mut), t0, t1)
    check("T13_asof_spy_no_same_day_leak",
          base_asof == mut_asof and base_mid != mut_mid,
          f"asof {base_asof} -> {mut_asof} under mutation; midnight "
          f"{base_mid} -> {mut_mid}")


def _portfolio_pipeline(obs, symbols, bench_rows_symbol="SPY"):
    data = {s: pb.add_pine_indicators(obs.bars_frame(s)) for s in symbols}
    closes = {s: data[s]["Close"] for s in symbols}
    bench = {"SPY": obs.benchmark_asof(bench_rows_symbol)}
    cands = sorted(obs.candidates(),
                   key=lambda t: (t["symbol"], t["signal_idx"]))
    feats = compute_features(cands, data, bench)
    st.rs = {id(tr): feats[i]["rs"] for i, tr in enumerate(cands)}
    cutoff = max(obs.bars_frame(s).index[-1] for s in symbols) \
        + pd.Timedelta(hours=4)
    pb.COSTS.setdefault("gross", 0.0)
    out = {}
    for view in ("gross", "4bps", "25bps"):
        port = st.simulate_stack(cands, closes, pb.COSTS[view], True, True,
                                 False, SECTOR, cutoff=cutoff)
        out[view] = {
            "disp": {i: v for i, v in port["disposition"].items()},
            "taken": sorted(port["taken"]),
            "terminal": sorted(x["symbol"] for x in port["terminal_open"]),
            "skips": (port["skipped_rank"], port["skipped_gate"],
                      port["skipped_cap"], port["skipped_risk"])}
    return out, cands


def _batch_pipeline(rows_by, symbols):
    data, closes, all_c = {}, {}, []
    bench_frames = {}
    for sym in symbols:
        bars, cands, _ = batch_reference(sym, rows_by[sym])
        data[sym] = pb.add_pine_indicators(bars)
        closes[sym] = data[sym]["Close"]
        all_c.extend(cands)
        idx = pd.DatetimeIndex([pd.Timestamp(r["datetime"])
                                for r in rows_by[sym]]).tz_localize(ET)
        bench_frames[sym] = pd.DataFrame(
            [{"Open": r["open"], "High": r["high"], "Low": r["low"],
              "Close": r["close"], "Volume": r["volume"]}
             for r in rows_by[sym]], index=idx)
    bench = {"SPY": asof_benchmark.build_daily_asof(bench_frames["SPY"])}
    cands = sorted(all_c, key=lambda t: (t["symbol"], t["signal_idx"]))
    feats = compute_features(cands, data, bench)
    st.rs = {id(tr): feats[i]["rs"] for i, tr in enumerate(cands)}
    cutoff = max(data[s].index[-1] for s in symbols) + pd.Timedelta(hours=4)
    pb.COSTS.setdefault("gross", 0.0)
    out = {}
    for view in ("gross", "4bps", "25bps"):
        port = st.simulate_stack(cands, closes, pb.COSTS[view], True, True,
                                 False, SECTOR, cutoff=cutoff)
        out[view] = {
            "disp": {i: v for i, v in port["disposition"].items()},
            "taken": sorted(port["taken"]),
            "terminal": sorted(x["symbol"] for x in port["terminal_open"]),
            "skips": (port["skipped_rank"], port["skipped_gate"],
                      port["skipped_cap"], port["skipped_risk"])}
    return out, cands


def t14_portfolio_cross_impl():
    sessions = first_sessions(150)
    # SPY: gentle path (benchmark + its own candidates); NVDA & AMD:
    # identical cloned paths (RS tie -> canonical order decides); MU:
    # same path shifted 6 bars later (sector gate contends); MSFT:
    # gentle-decline path (different sector).
    specs = {"SPY": (0.9965, 250, 262), "NVDA": (0.990, 250, 262),
             "AMD": (0.990, 250, 262), "MU": (0.990, 256, 268),
             "MSFT": (0.9965, 250, 262)}
    rows_by, batch_c = {}, {}
    for sym, (dr, df_, dt_) in specs.items():
        rows = expand_targets(trend_targets(sessions, dr, df_, dt_))
        rows_by[sym] = rows
    symbols = list(specs)
    obs, j, _ = make_observer(symbols)
    feed_all(obs, rows_by)
    out_o, cands_o = _portfolio_pipeline(obs, symbols)
    out_b, cands_b = _batch_pipeline(rows_by, symbols)
    same_c = [decision_fields(r) for r in cands_o] == \
        [decision_fields(r) for r in cands_b]
    same = same_c and all(out_o[v] == out_b[v] for v in out_o)
    skips = out_o["4bps"]["skips"]
    # input-order invariance: feed the observer in reverse symbol order
    obs2, j2, _ = make_observer(symbols)
    merged = []
    for sym in reversed(symbols):
        merged.extend((r["datetime"], sym, r) for r in rows_by[sym])
    merged.sort(key=lambda x: x[0])
    for _, sym, r in merged:
        obs2.ingest(sym, r)
    obs2.flush()
    out_o2, _ = _portfolio_pipeline(obs2, symbols)
    inv = all(out_o2[v] == out_o[v] for v in out_o)
    check("T14_portfolio_cross_impl_gates",
          same and inv and skips[0] + skips[1] + skips[2] + skips[3] > 0,
          f"candidates identical={same_c} dispositions identical={same} "
          f"order-invariant={inv} 4bps skips rank/gate/cap/risk={skips}")


def t15_restart_idempotency():
    sessions = first_sessions(150)
    rows = expand_targets(trend_targets(sessions, 0.990, 250, 262))
    # run A: uninterrupted (with the same duplicate probe as run B,
    # applied at the identical point: after the full feed, before flush)
    obs_a, ja, tmp_a = make_observer(["TEST"])
    for r in rows:
        obs_a.ingest("TEST", r)
    dup_a = obs_a.ingest("TEST", rows[-1])
    dup_a_rej = [e for e in dup_a if e["type"] == "REJECTED"
                 and e["class"] == fo.REJ_DUPLICATE]
    obs_a.flush()
    ja.anchor("final")
    ja.close()
    sha_a = hashlib.sha256(open(ja.journal_path, "rb").read()).hexdigest()
    cands_a = [decision_fields(r) for r in obs_a.candidates()]
    # run B: snapshot mid-feed, restore, continue
    obs_b, jb, tmp_b = make_observer(["TEST"])
    half = len(rows) // 2
    for r in rows[:half]:
        obs_b.ingest("TEST", r)
    jb.anchor("mid")
    snap = os.path.join(tmp_b, "snapshot.json")
    obs_b.snapshot(snap)
    jb.close()
    jb2 = fo.Journal.resume(jb.journal_path, jb.anchor_path)
    obs_b2 = fo.ForwardObserver.restore(
        snap, FULL_TABLE, jb2, pb, ["TEST"])
    for r in rows[half:]:
        obs_b2.ingest("TEST", r)
    dup_b = obs_b2.ingest("TEST", rows[-1])
    dup_rej = [e for e in dup_b if e["type"] == "REJECTED"
               and e["class"] == fo.REJ_DUPLICATE]
    obs_b2.flush()
    jb2.anchor("final")
    jb2.close()
    sha_b = hashlib.sha256(open(jb2.journal_path, "rb").read()).hexdigest()
    cands_b = [decision_fields(r) for r in obs_b2.candidates()]
    check("T15_restart_idempotency",
          sha_a == sha_b and cands_a == cands_b and len(dup_rej) == 1
          and len(dup_a_rej) == 1,
          f"journal sha equal={sha_a == sha_b} candidates equal="
          f"{cands_a == cands_b} duplicate refused after restore="
          f"{len(dup_rej)}")


def t16_journal_tamper():
    obs, j, tmp = make_observer(["AAA"], subset_table({"2024-03-07"}))
    feed_all(obs, {"AAA": flat_rows("2024-03-07")})
    j.anchor("seal")
    j.close()
    ok_intact, _ = fo.Journal.verify(j.journal_path, j.anchor_path)
    raw = open(j.journal_path).read().splitlines()
    tampered = list(raw)
    rec = json.loads(tampered[1])
    rec["payload"] = {"forged": True}
    tampered[1] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    p2 = os.path.join(tmp, "tampered.jsonl")
    open(p2, "w").write("\n".join(tampered) + "\n")
    ok_tamper, _ = fo.Journal.verify(p2, j.anchor_path)
    p3 = os.path.join(tmp, "truncated.jsonl")
    open(p3, "w").write("\n".join(raw[:-1]) + "\n")
    ok_trunc, _ = fo.Journal.verify(p3, j.anchor_path)
    check("T16_journal_tamper_detected",
          ok_intact and not ok_tamper and not ok_trunc,
          f"intact={ok_intact} tampered={ok_tamper} truncated={ok_trunc}")


def t17_sentinel_gate():
    sessions = first_sessions(150)
    rows = expand_targets(trend_targets(sessions, 0.990, 250, 262))
    tmp = tempfile.mkdtemp(prefix="fwdsent_")
    sentinel = os.path.join(tmp, "PAUSE_NEW_ENTRIES")
    open(sentinel, "w").write("paused")
    obs, j, _ = make_observer(["TEST"], FULL_TABLE,
                              sentinel_path=sentinel, armed=True)
    feed_all(obs, {"TEST": rows})
    withheld = sum(1 for r in j.records if r["type"] == "WITHHELD_PAUSED")
    blocked = len(obs.decision_events) == 0 and withheld > 0
    os.remove(sentinel)
    obs2, j2, _ = make_observer(["TEST"], FULL_TABLE,
                                sentinel_path=sentinel, armed=True)
    feed_all(obs2, {"TEST": rows})
    check("T17_paused_sentinel_gate",
          blocked and len(obs2.decision_events) > 0,
          f"withheld={withheld} decisions while paused="
          f"{len(obs.decision_events)}, after resume="
          f"{len(obs2.decision_events)}")


def t18_terminal_censoring():
    obs, batch, _ = _trend_run({"TEST": (0.990, 250, 262)})
    bars_b, cands_b, _ = batch["TEST"]
    cens = [r for r in obs.candidates() if r.get("censored")]
    closed_events = [e for e in obs.decision_events
                     if e["type"] == "TRADE_CLOSED"
                     and cens and e["signal_idx"] == cens[0]["signal_idx"]]
    data = {"TEST": pb.add_pine_indicators(obs.bars_frame("TEST"))}
    closes = {"TEST": data["TEST"]["Close"]}
    cands = sorted(obs.candidates(),
                   key=lambda t: (t["symbol"], t["signal_idx"]))
    feats = compute_features(cands, data, {"SPY": obs.benchmark_asof("SPY")}
                             if "SPY" in obs.feeds else {})
    st.rs = {id(tr): feats[i]["rs"] for i, tr in enumerate(cands)}
    cutoff = obs.bars_frame("TEST").index[-1] + pd.Timedelta(hours=4)
    port = st.simulate_stack(cands, closes, pb.COSTS["4bps"], True, False,
                             False, SECTOR, cutoff=cutoff)
    term = {x["symbol"]: x for x in port["terminal_open"]}
    last_close = float(bars_b["Close"].iloc[-1])
    t = term.get("TEST")
    ok = len(cens) == 1 and not closed_events and t is not None \
        and abs(t["mark"] - last_close) < 1e-9 \
        and t.get("exit") is None and "cash_flow" not in t
    check("T18_terminal_censoring_mark",
          ok, f"censored={len(cens)} terminal mark="
          f"{None if t is None else t['mark']} last completed close="
          f"{last_close} fabricated exit events={len(closed_events)}")


def main():
    for fn in (t01_grid_full, t02_grid_early_close, t03_holiday_refused,
               t04_dst_spring, t05_dst_fall, t06_legacy_grid_rejected,
               t07_phantom_postclose, t08_poison_isolation,
               t09_missing_hour_gap, t10_late_bar_no_backfill,
               t11_duplicate_out_of_order, t12_streaming_vs_batch,
               t13_asof_benchmark, t14_portfolio_cross_impl,
               t15_restart_idempotency, t16_journal_tamper,
               t17_sentinel_gate, t18_terminal_censoring):
        try:
            fn()
        except Exception as e:  # a raising test is a failing test
            import traceback
            traceback.print_exc()
            check(fn.__name__, False, f"raised {type(e).__name__}: {e}")
    n_ok = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"SUMMARY {n_ok}/{len(RESULTS)} tests passed")
    return 0 if n_ok == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
