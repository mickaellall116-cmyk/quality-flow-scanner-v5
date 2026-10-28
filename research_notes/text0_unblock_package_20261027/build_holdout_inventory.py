"""Holdout inventory builder — outcome-blind every-observed-bar
inventory for the SEALED HOLDOUT window (Text 0 unblock package,
2026-10-27).

Successor of the DEV P7b builder
(research_notes/equity43_dev_buy_prep_m1m2_20261025/code/
build_p7b_inventory.py, sha256 f01b3afc...), whose output is the
pinned DEV inventory (sha256 a6bbd19a...). This builder emits the
identical row schema for the holdout domain consumed by
exp14_buy_corr3.py:

  Per bar: symbol, bar index, timestamp, session date + ordinal
  (adopted 751-session table, HOLDOUT subset of 227 sessions,
  2023-10-19..2024-09-15), session bin start (09:30 / 13:30),
  Close, ATR(14), ATR% (= atr / Close), EMA21, EMA55, EMA200 (null
  where the frozen indicator is NaN), the frozen pine_buy_signal
  flag, and whether the bar lies in the generator evaluation domain
  (idx in [WARMUP=215, n-2]).

Pipeline identity with P7b is by construction and by test:
  - admission re-implements, line for line in substance, the frozen
    run_study13.phase2 admission gates (session-table expected
    starts; meta check; finite/positive values; duplicate stamps;
    excluded stamps only in the generic early-close post-close
    class; admitted set exactly the expected set; zero admitted
    price-moving zero-volume bars), parameterized by window and
    file suffix instead of phase2's compiled-in DEV bindings;
  - the 4H resample is the frozen phase4 itself
    (scanner_rules.resample_closed_4h_session_anchored plus the
    aggregation/grid parity checks), with phase4's compiled-in
    EXPECTED_BARS_4H temporarily set to the count computed from
    the window's session subset (for DEV that computed count IS
    1043, asserted in dev-validate mode - the pinned constant is
    not changed on disk anywhere);
  - indicators and signals come only from the frozen engine
    (pine_backtest.add_pine_indicators / pine_buy_signal).

Modes:
  --mode dev-validate : build the DEV domain (43 symbols) with this
      code path and compare the emitted rows, byte for byte,
      against the pinned P7b inventory. This is the builder's
      end-to-end correctness evidence. (--symbols may restrict the
      comparison to a subset; the build itself is per-symbol
      independent, exactly as in P7b.)
  --mode holdout      : build the holdout inventory for the 30
      manifest symbols (Tier 2 + Tier 3) from the committed capture
      bytes. THIS MODE READS SEALED-WINDOW DATA and is latched: it
      refuses unless TEXT0_SESSION_AUTHORIZED=1 is set in the
      environment, which only the authorized Text 0 session (two
      people, logged, pins verified) may set. It is never run by
      this package's test suite.
  --mode synthetic    : holdout parameterization against fabricated
      fixture captures + a fabricated mini session table (test
      suite only; --raw-dir and --fixture-table required).

No data is fetched in any mode; no returns are computed; no
forward-looking field is emitted. Outputs: inventory JSONL (placed
in the private archive environment by the session; its SHA-256 and
the domain fire census are what complete the corr3 binding
manifest at staging) and a public summary JSON (counts, pins,
coverage - the same disclosure class as the P7b summary).
"""
import argparse
import hashlib
import json
import os
import sys

DEFAULT_HOME = os.path.expanduser("~/workspace/qf_fix29_stage/home")
SESSION_TABLE_SHA256 = (
    "00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def expected_starts(session):
    """Identical to run_study13.expected_starts (frozen)."""
    close_h, close_m = map(int, session["close"].split(":"))
    starts, mins = [], 9 * 60 + 30
    while mins < close_h * 60 + close_m:
        starts.append(f"{mins // 60:02d}:{mins % 60:02d}")
        mins += 60
    return starts


def admit_symbol(pd, np, raw_path, expected, sessions_by_date):
    """The frozen phase2 admission gates, parameterized. Returns
    (DataFrame, leg_record) or (None, leg_record) on gate failure.
    `expected` is the {(date, HH:MM)} set for the window subset."""
    raw = json.load(open(raw_path))
    meta = raw["meta"]
    leg = {"meta_exchange_timezone": meta.get("exchange_timezone"),
           "meta_interval": meta.get("interval")}
    if meta.get("exchange_timezone") != "America/New_York" \
            or meta.get("interval") != "1h":
        leg["failure"] = f"meta mismatch {meta}"
        return None, leg
    rows = raw["values"]
    leg["raw_rows"] = len(rows)
    seen, admitted, excluded = {}, [], []
    for r in rows:
        try:
            ts = pd.Timestamp(r["datetime"])
            o, h, l, c = (float(r[k])
                          for k in ("open", "high", "low", "close"))
            v = float(r["volume"])
        except Exception:
            leg["failure"] = "unparseable row"
            return None, leg
        if not all(np.isfinite(x) for x in (o, h, l, c, v)):
            leg["failure"] = f"non-finite value at {r['datetime']}"
            return None, leg
        if min(o, h, l, c) <= 0 or v < 0:
            leg["failure"] = ("non-positive price / negative volume "
                              f"at {r['datetime']}")
            return None, leg
        key = (r["datetime"][:10], r["datetime"][11:16])
        if key in seen:
            leg["failure"] = f"duplicate stamp {r['datetime']}"
            return None, leg
        seen[key] = True
        rec = {"ts": ts, "Open": o, "High": h, "Low": l, "Close": c,
               "Volume": v}
        if key in expected:
            admitted.append(rec)
        else:
            excluded.append({"datetime": r["datetime"], "open": o,
                             "high": h, "low": l, "close": c,
                             "volume": v})
    bad_class = []
    for e in excluded:
        sess = sessions_by_date.get(e["datetime"][:10])
        if sess is None or sess["close"] != "13:00" \
                or e["datetime"][11:16] < sess["close"]:
            bad_class.append(e["datetime"])
    leg["excluded_outside_generic_early_close_class"] = bad_class
    if bad_class:
        leg["failure"] = ("excluded stamps outside the generic "
                          f"early-close class: {bad_class}")
        return None, leg
    stamps = {(a["ts"].strftime("%Y-%m-%d"), a["ts"].strftime("%H:%M"))
              for a in admitted}
    zv = [a for a in admitted if a["Volume"] == 0]
    zv_moving = [a for a in zv
                 if not (a["Open"] == a["High"] == a["Low"]
                         == a["Close"])]
    leg["admitted_rows"] = len(admitted)
    leg["zero_volume_admitted"] = len(zv)
    leg["zero_volume_price_moving"] = len(zv_moving)
    gates = {"G-2_calendar_admission": stamps == set(expected)
             and len(admitted) == len(expected),
             "G-3_completeness_exact": len(admitted) == len(expected),
             "G-4_phantom_exclusion_generic": not bad_class,
             "G-5_volume_completeness": len(zv_moving) == 0,
             "G-6_schema_instant_hygiene": len(seen) == len(rows)}
    leg["gates"] = gates
    if not all(gates.values()):
        leg["failure"] = f"gate failure {gates}"
        return None, leg
    idx = pd.DatetimeIndex([a["ts"] for a in admitted]).tz_localize(
        "America/New_York")
    if not idx.is_monotonic_increasing:
        leg["failure"] = "admitted stamps not strictly increasing"
        return None, leg
    df = pd.DataFrame(
        [{k: a[k] for k in ("Open", "High", "Low", "Close", "Volume")}
         for a in admitted], index=idx)
    return df, leg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True,
                    choices=("dev-validate", "holdout", "synthetic"))
    ap.add_argument("--stage-home", default=DEFAULT_HOME)
    ap.add_argument("--manifest",
                    help="binding manifest (holdout/synthetic modes)")
    ap.add_argument("--symbols",
                    help="comma list override (dev-validate subset)")
    ap.add_argument("--raw-dir",
                    help="single raw-capture dir (synthetic mode)")
    ap.add_argument("--fixture-table", action="store_true",
                    help="permit a non-pinned session table "
                         "(synthetic fixtures only)")
    ap.add_argument("--session-table",
                    help="session table path (default: stage home)")
    ap.add_argument("--reference-inventory",
                    help="pinned P7b inventory (dev-validate)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--summary", required=True)
    args = ap.parse_args()

    if args.mode == "holdout" \
            and os.environ.get("TEXT0_SESSION_AUTHORIZED") != "1":
        print("STOP: holdout mode reads sealed-window capture bytes "
              "and is latched to the authorized Text 0 session "
              "(TEXT0_SESSION_AUTHORIZED=1 not set). Refusing.")
        return 2

    home = args.stage_home
    os.chdir(home)
    sys.path.insert(0, home)
    sys.path.insert(0, os.path.join(home, "engine_successor"))
    pylibs = os.path.expanduser("~/workspace/qf_td17_stage/pylibs")
    if os.path.isdir(pylibs):
        sys.path.insert(0, pylibs)

    import numpy as np
    import pandas as pd
    import run_study13 as drv
    import pine_backtest as pb

    # ---- window + symbols -------------------------------------------
    if args.mode == "dev-validate":
        win_start, win_end, suffix = "2024-09-16", "2026-10-16", "DEV"
        child = json.load(open(os.path.join(home, "child_manifest.json")))
        symbols = drv.PILOT + [l["symbol"] for l in child["legs"]
                               if l["window"] == "W_DEV"]
        assert len(symbols) == 43, len(symbols)
        if args.symbols:
            symbols = [s.strip() for s in args.symbols.split(",")]
    else:
        if not args.manifest:
            print("STOP: --manifest is required in this mode")
            return 2
        manifest = json.load(open(args.manifest))
        win_start = manifest["window_start"]
        win_end = manifest["window_end"]
        suffix = "HO"
        symbols = (list(manifest["tiers"]["tier2"])
                   + list(manifest["tiers"]["tier3"]))
        if args.symbols:
            symbols = [s.strip() for s in args.symbols.split(",")]

    # ---- session subset ----------------------------------------------
    table_path = args.session_table or os.path.join(
        home, "session_table.json")
    table_sha = sha256_file(table_path)
    if not args.fixture_table and table_sha != SESSION_TABLE_SHA256:
        print(f"STOP: session table sha256 {table_sha} != pinned "
              f"{SESSION_TABLE_SHA256}")
        return 2
    table = json.load(open(table_path))
    subset = [s for s in table["sessions"]
              if win_start <= s["date"] <= win_end]
    sessions_by_date = {s["date"]: s for s in table["sessions"]}
    session_ord = {s["date"]: k for k, s in enumerate(subset)}
    expected = {}
    for s in subset:
        for st in expected_starts(s):
            expected[(s["date"], st)] = True
    early = sum(1 for s in subset if s["close"] == "13:00")
    expected_bars = 2 * len(subset) - early
    print(f"window {win_start}..{win_end}: sessions {len(subset)}, "
          f"expected admitted {len(expected)}, expected 4H bars "
          f"{expected_bars} (early closes {early})")
    if args.mode == "dev-validate":
        assert len(subset) == 524 and len(expected) == 3653 \
            and expected_bars == 1043, (
                len(subset), len(expected), expected_bars)

    # ---- admission ----------------------------------------------------
    admitted, legs, raw_pins = {}, {}, {}
    for sym in symbols:
        if args.raw_dir:
            raw_path = os.path.join(args.raw_dir, f"{sym}__{suffix}.json")
        else:
            ns = drv.NSP if sym in drv.PILOT else drv.NS11
            raw_path = os.path.join(ns, "raw", f"{sym}__{suffix}.json")
        raw_pins[sym] = sha256_file(raw_path)
        df, leg = admit_symbol(pd, np, raw_path, expected,
                               sessions_by_date)
        legs[sym] = leg
        if df is None:
            print(f"STOP admission {sym}: {leg.get('failure')}")
            return 2
        admitted[sym] = df
        print(f"ADM {sym}: admitted {leg['admitted_rows']} "
              f"zv {leg['zero_volume_admitted']}/"
              f"{leg['zero_volume_price_moving']} moving", flush=True)

    # ---- frozen resample (phase4; bar-count expectation computed) ----
    saved = drv.EXPECTED_BARS_4H
    drv.EXPECTED_BARS_4H = expected_bars
    try:
        bars = drv.phase4(admitted, subset, symbols)
    finally:
        drv.EXPECTED_BARS_4H = saved
    if drv.failures:
        print("STOP phase4:", drv.failures)
        return 2

    # ---- rows (identical construction to the P7b builder) ------------
    rows_out, per_symbol, census_fires = [], {}, 0
    for sym in symbols:
        df = pb.add_pine_indicators(bars[sym])
        n = len(df)
        miss = {"atr": 0, "atr_pct": 0, "ema21": 0, "ema55": 0,
                "ema200": 0}
        miss_dom = dict(miss)
        bins = {"09:30": 0, "13:30": 0}
        fires_dom = 0
        for i in range(n):
            r = df.iloc[i]
            ts = df.index[i]
            close = float(r["Close"])
            atr = None if r["atr"] != r["atr"] else float(r["atr"])
            e21 = None if r["e21"] != r["e21"] else float(r["e21"])
            e55 = None if r["e55"] != r["e55"] else float(r["e55"])
            e200 = None if r["e200"] != r["e200"] else float(r["e200"])
            atr_pct = (atr / close) if atr is not None else None
            in_dom = pb.WARMUP <= i <= n - 2
            sig = bool(pb.pine_buy_signal(df, i)) if i >= 1 else False
            vals = {"atr": atr, "atr_pct": atr_pct, "ema21": e21,
                    "ema55": e55, "ema200": e200}
            for k, v in vals.items():
                if v is None:
                    miss[k] += 1
                    if in_dom:
                        miss_dom[k] += 1
            bin_start = ts.strftime("%H:%M")
            if bin_start in bins:
                bins[bin_start] += 1
            if in_dom and sig:
                fires_dom += 1
            rows_out.append({
                "symbol": sym, "idx": i, "ts": ts.isoformat(),
                "session_date": ts.strftime("%Y-%m-%d"),
                "session_ordinal": session_ord[ts.strftime("%Y-%m-%d")],
                "bin": bin_start, "close": close, "atr": atr,
                "atr_pct": atr_pct, "ema21": e21, "ema55": e55,
                "ema200": e200, "signal": sig,
                "in_generator_domain": in_dom,
            })
        census_fires += fires_dom
        per_symbol[sym] = {
            "bars": n, "first_ts": df.index[0].isoformat(),
            "last_ts": df.index[-1].isoformat(),
            "domain_bars": sum(1 for i in range(n)
                               if pb.WARMUP <= i <= n - 2),
            "bin_counts": bins, "fires_in_domain": fires_dom,
            "missing_fields_full_series": miss,
            "missing_fields_generator_domain": miss_dom,
        }
        print(f"INV {sym}: bars {n} fires_domain {fires_dom} "
              f"missing_dom {miss_dom}", flush=True)

    with open(args.out, "w") as f:
        for row in rows_out:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    inv_sha = sha256_file(args.out)

    validation = None
    if args.mode == "dev-validate":
        if not args.reference_inventory:
            print("STOP: dev-validate requires --reference-inventory")
            return 2
        ref_sha = sha256_file(args.reference_inventory)
        ref = {}
        for line in open(args.reference_inventory):
            r = json.loads(line)
            ref.setdefault(r["symbol"], []).append(r)
        mine = {}
        for r in rows_out:
            mine.setdefault(r["symbol"], []).append(r)
        mism = {s: (len(mine.get(s, [])), len(ref.get(s, [])))
                for s in symbols
                if json.dumps(mine.get(s, []), sort_keys=True)
                != json.dumps(ref.get(s, []), sort_keys=True)}
        validation = {
            "reference_inventory_sha256": ref_sha,
            "symbols_compared": symbols,
            "rows_compared": sum(len(mine[s]) for s in symbols),
            "mismatched_symbols": mism,
            "byte_exact_per_symbol": not mism,
        }
        print("DEV-VALIDATE:", validation)

    pins = {
        "session_table_json": table_sha,
        "run_study13_py": sha256_file(os.path.join(home,
                                                   "run_study13.py")),
        "pine_backtest_py_engine_successor": sha256_file(os.path.join(
            home, "engine_successor", "pine_backtest.py")),
        "raw_capture_sha256_by_symbol": raw_pins,
    }
    if args.mode != "dev-validate":
        pins["binding_manifest_sha256"] = sha256_file(args.manifest)
    summary = {
        "artifact": f"{args.mode} every-observed-bar inventory "
                    f"({win_start}..{win_end})",
        "schema": {
            "symbol": "str", "idx": "int (0-based bar index in the "
            "symbol's frozen 4H series)", "ts": "ISO bar-open "
            "timestamp (ET)", "session_date": "YYYY-MM-DD",
            "session_ordinal": "int, position in the window subset "
            "of the adopted 751-session table",
            "bin": "session bin start, '09:30' or '13:30'",
            "close": "float", "atr": "float|null (frozen ATR(14))",
            "atr_pct": "float|null (= atr/close)",
            "ema21": "float|null", "ema55": "float|null",
            "ema200": "float|null",
            "signal": "bool, frozen pine_buy_signal on the completed bar",
            "in_generator_domain": "bool, WARMUP(215) <= idx <= n-2",
        },
        "field_provenance": "Close/ATR/EMA from the frozen pipeline "
        "only (admission per the frozen phase2 gates -> phase4 "
        "session-anchored 4H resample -> add_pine_indicators); "
        "nulls are the frozen indicators' own NaN warmup, never "
        "filled or invented.",
        "window": [win_start, win_end], "sessions": len(subset),
        "symbols": symbols, "total_bars": len(rows_out),
        "census_fires_in_generator_domain": census_fires,
        "per_symbol": per_symbol, "admission_legs": legs,
        "inventory_file": os.path.basename(args.out),
        "inventory_sha256": inv_sha,
        "input_pins": pins,
        "dev_validation": validation,
        "outcome_blind": "No forward returns, no trade outcomes, no "
        "group differences are computed or emitted by this builder.",
    }
    with open(args.summary, "w") as f:
        json.dump(summary, f, indent=1, sort_keys=True)
    print(f"INVENTORY sha256: {inv_sha} | bars {len(rows_out)} | "
          f"census fires {census_fires}")
    if validation is not None and not validation["byte_exact_per_symbol"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
