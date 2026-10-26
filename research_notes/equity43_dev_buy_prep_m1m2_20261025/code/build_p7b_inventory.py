"""P7b — outcome-blind every-observed-bar inventory for the DEV domain.

QF preregistration v0.3 preparatory package M1 (governing: Issue #1
comment 6405097569, Claude Final-Gate verdict relay; comment 6401471382
HOLD 1). Builds an inventory of EVERY observed 4H bar for the 43 DEV
symbols from the existing committed DEV capture bytes only (the -13
stage assets: archive_clone namespaces td_pilot_20261023 +
td_capture_equity39_continue_20261023, admitted and resampled by the
frozen run_study13 phase2/phase4 path, indicators by the frozen
engine_successor pine_backtest.add_pine_indicators). No new data is
fetched; no returns are computed; no forward-looking field is emitted.

Per bar: symbol, bar index, timestamp, session date + ordinal (adopted
751-session table, DEV subset of 524 sessions), session bin start
(09:30 / 13:30), Close, ATR(14), ATR% (= atr / Close), EMA21, EMA55,
EMA200 (null where the frozen indicator is NaN), the frozen
pine_buy_signal flag, and whether the bar lies in the generator
evaluation domain (idx in [WARMUP=215, n-2]).

The fire flags inside the generator domain are reconciled against the
committed P7 all-fire journal (-29, commit 539e0a9): the (symbol,
signal_idx) sets must be identical (2,892 fires).

Outputs:
  --out       inventory JSONL (one object per bar) — placed in the
              private qf-data-archive, hash-pinned in the summary;
  --summary   coverage/count/reconciliation JSON (public artifact).
"""
import argparse
import hashlib
import json
import os
import sys

DEFAULT_HOME = os.path.expanduser("~/workspace/qf_fix29_stage/home")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage-home", default=DEFAULT_HOME)
    ap.add_argument("--journal", required=True,
                    help="committed allfire_journal.json (reconciliation)")
    ap.add_argument("--journal-summary", required=True,
                    help="committed allfire_summary.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--summary", required=True)
    args = ap.parse_args()

    home = args.stage_home
    os.chdir(home)
    sys.path.insert(0, home)
    pylibs = os.path.expanduser("~/workspace/qf_td17_stage/pylibs")
    if os.path.isdir(pylibs):
        sys.path.insert(0, pylibs)

    import run_study13 as drv
    import pine_backtest as pb

    child = json.load(open(os.path.join(home, "child_manifest.json")))
    symbols43 = drv.PILOT + [l["symbol"] for l in child["legs"]
                             if l["window"] == "W_DEV"]
    assert len(symbols43) == 43, len(symbols43)

    table, dev_sessions = drv.load_session_table()
    admitted = drv.phase2(table, dev_sessions, symbols43)
    if drv.failures:
        print("STOP phase2:", drv.failures)
        return 2
    bars = drv.phase4(admitted, dev_sessions, symbols43)
    if drv.failures:
        print("STOP phase4:", drv.failures)
        return 2

    session_ord = {s["date"]: k for k, s in enumerate(dev_sessions)}

    # ---- reconciliation target: committed P7 journal -------------------
    journal = json.load(open(args.journal))
    jsum = json.load(open(args.journal_summary))
    journal_fires = {(r["symbol"], int(r["signal_idx"])) for r in journal}
    print(f"journal fires: {len(journal_fires)}; summary: {jsum}")

    rows_out = []
    per_symbol = {}
    inv_fires = set()
    for sym in symbols43:
        df = pb.add_pine_indicators(bars[sym])
        n = len(df)
        miss = {"atr": 0, "atr_pct": 0, "ema21": 0, "ema55": 0, "ema200": 0}
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
                inv_fires.add((sym, i))
            rows_out.append({
                "symbol": sym, "idx": i, "ts": ts.isoformat(),
                "session_date": ts.strftime("%Y-%m-%d"),
                "session_ordinal": session_ord[ts.strftime("%Y-%m-%d")],
                "bin": bin_start, "close": close, "atr": atr,
                "atr_pct": atr_pct, "ema21": e21, "ema55": e55,
                "ema200": e200, "signal": sig, "in_generator_domain": in_dom,
            })
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

    only_journal = journal_fires - inv_fires
    only_inv = inv_fires - journal_fires
    recon = {
        "journal_fires": len(journal_fires),
        "inventory_domain_fires": len(inv_fires),
        "symmetric_difference": len(only_journal) + len(only_inv),
        "only_in_journal": sorted(only_journal)[:10],
        "only_in_inventory": sorted(only_inv)[:10],
        "journal_class_partition_committed": jsum,
        "reconciled": not only_journal and not only_inv,
    }

    with open(args.out, "w") as f:
        for row in rows_out:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    inv_sha = sha256_file(args.out)

    # ---- input pins ------------------------------------------------------
    raw_pins = {}
    for sym in symbols43:
        ns = drv.NSP if sym in drv.PILOT else drv.NS11
        raw_pins[sym] = sha256_file(os.path.join(ns, "raw", f"{sym}__DEV.json"))
    pins = {
        "session_table_json": sha256_file(os.path.join(home, "session_table.json")),
        "run_study13_py": sha256_file(os.path.join(home, "run_study13.py")),
        "pine_backtest_py_engine_successor": sha256_file(
            os.path.join(home, "engine_successor", "pine_backtest.py")),
        "allfire_journal_json": sha256_file(args.journal),
        "allfire_summary_json": sha256_file(args.journal_summary),
        "raw_dev_capture_sha256_by_symbol": raw_pins,
    }

    summary = {
        "artifact": "P7b every-observed-bar inventory (DEV, 43 symbols)",
        "schema": {
            "symbol": "str", "idx": "int (0-based bar index in the symbol's "
            "frozen 4H DEV series)", "ts": "ISO bar-open timestamp (ET)",
            "session_date": "YYYY-MM-DD", "session_ordinal": "int, position "
            "in the 524-session DEV subset of the adopted 751-session table",
            "bin": "session bin start, '09:30' or '13:30'",
            "close": "float", "atr": "float|null (frozen ATR(14))",
            "atr_pct": "float|null (= atr/close)",
            "ema21": "float|null", "ema55": "float|null",
            "ema200": "float|null",
            "signal": "bool, frozen pine_buy_signal on the completed bar",
            "in_generator_domain": "bool, WARMUP(215) <= idx <= n-2",
        },
        "field_provenance": "Close/ATR/EMA from the frozen pipeline only "
        "(phase2 admission -> phase4 session-anchored 4H resample -> "
        "add_pine_indicators); nulls are the frozen indicators' own NaN "
        "warmup, never filled or invented.",
        "symbols": 43, "total_bars": len(rows_out),
        "dev_sessions": len(dev_sessions),
        "per_symbol": per_symbol,
        "reconciliation_vs_committed_p7_journal": recon,
        "inventory_file": os.path.basename(args.out),
        "inventory_sha256": inv_sha,
        "input_pins": pins,
        "outcome_blind": "No forward returns, no trade outcomes, no group "
        "differences are computed or emitted by this builder.",
    }
    with open(args.summary, "w") as f:
        json.dump(summary, f, indent=1, sort_keys=True)
    print("RECONCILED:", recon["reconciled"], "| total bars:",
          len(rows_out), "| inventory sha:", inv_sha)
    return 0 if recon["reconciled"] else 2


if __name__ == "__main__":
    sys.exit(main())
