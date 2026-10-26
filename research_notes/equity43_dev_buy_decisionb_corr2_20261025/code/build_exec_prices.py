"""EXP-14 execution-only price input — next-bar open prices (DEV).

Decision B (Mike, 2026-10-25; bridge commit 243df1a), implementation
item (a): Claude prohibited open fields in the outcome-blind P7b
inventory, so the section-5 endpoint's entry price (open of bar i+1)
must come from a SEPARATE, private, execution-only price input. This
builder derives that input from the SAME committed DEV capture bytes
and the SAME frozen pipeline that produced the P7b inventory (the -13
stage assets admitted and resampled by the frozen run_study13
phase2/phase4 path). No new data is fetched. The P7b inventory is NOT
amended by this builder — it is read, hash-checked, and used only as
the alignment reference.

Alignment proof (fail-closed): for every one of the 44,849 bars, the
pipeline frame's timestamp must equal the pinned inventory row's ts
and its Close must equal the inventory row's close exactly. Any
mismatch aborts the build with no output file written. The emitted
file therefore provably prices the same bar series the inventory
describes.

Output rows (JSONL): symbol, idx, ts, open — the open of EVERY
observed bar (the endpoint reads open[i+1] from it at execution time).
Placement: PRIVATE qf-data-archive ONLY (research_inventory/
exp14_exec_prices_20261025/), beside the P7b inventory. The public
package publishes the descriptor (hash / counts / schema / alignment
result) only — no prices.

This builder computes no returns and reads no outcomes.
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
    ap.add_argument("--inventory", required=True,
                    help="pinned P7b inventory JSONL (private archive)")
    ap.add_argument("--inventory-sha", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--summary", required=True)
    args = ap.parse_args()

    got = sha256_file(args.inventory)
    if got != args.inventory_sha:
        print(f"STOP: inventory sha256 {got} != pinned "
              f"{args.inventory_sha}")
        return 2

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

    inv = {}
    with open(args.inventory) as f:
        for line in f:
            row = json.loads(line)
            inv.setdefault(row["symbol"], []).append(row)
    for rows in inv.values():
        rows.sort(key=lambda r: r["idx"])
    if sorted(inv) != sorted(symbols43):
        print("STOP: inventory symbol set != the 43 DEV symbols")
        return 2

    table, dev_sessions = drv.load_session_table()
    admitted = drv.phase2(table, dev_sessions, symbols43)
    if drv.failures:
        print("STOP phase2:", drv.failures)
        return 2
    bars = drv.phase4(admitted, dev_sessions, symbols43)
    if drv.failures:
        print("STOP phase4:", drv.failures)
        return 2

    rows_out = []
    per_symbol = {}
    compared = 0
    ts_mismatch = []
    close_mismatch = []
    nan_open = []
    for sym in symbols43:
        df = pb.add_pine_indicators(bars[sym])
        inv_rows = inv[sym]
        if len(df) != len(inv_rows):
            print(f"STOP: {sym} pipeline bars {len(df)} != inventory "
                  f"rows {len(inv_rows)}")
            return 2
        for i in range(len(df)):
            r = df.iloc[i]
            ts = df.index[i].isoformat()
            irow = inv_rows[i]
            compared += 1
            if ts != irow["ts"]:
                ts_mismatch.append((sym, i, ts, irow["ts"]))
            close = float(r["Close"])
            if close != irow["close"]:
                close_mismatch.append((sym, i, close, irow["close"]))
            open_ = r["Open"]
            if open_ != open_:  # NaN
                nan_open.append((sym, i))
                open_f = None
            else:
                open_f = float(open_)
            rows_out.append({"symbol": sym, "idx": i, "ts": ts,
                             "open": open_f})
        per_symbol[sym] = {"bars": len(df),
                           "first_ts": df.index[0].isoformat(),
                           "last_ts": df.index[-1].isoformat()}
        print(f"EXEC {sym}: bars {len(df)}", flush=True)

    if ts_mismatch or close_mismatch or nan_open:
        print("STOP: alignment failed — "
              f"ts mismatches {len(ts_mismatch)} {ts_mismatch[:5]}, "
              f"close mismatches {len(close_mismatch)} "
              f"{close_mismatch[:5]}, NaN opens {len(nan_open)} "
              f"{nan_open[:5]}")
        return 2

    tmp_out = args.out + ".tmp"
    with open(tmp_out, "w") as f:
        for row in rows_out:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    os.replace(tmp_out, args.out)
    out_sha = sha256_file(args.out)

    raw_pins = {}
    for sym in symbols43:
        ns = drv.NSP if sym in drv.PILOT else drv.NS11
        raw_pins[sym] = sha256_file(os.path.join(ns, "raw",
                                                 f"{sym}__DEV.json"))
    summary = {
        "artifact": "EXP-14 execution-only price input (DEV, 43 symbols) "
                    "— next-bar open prices for the section-5 endpoint",
        "decision_basis": "Decision B (Mike, 2026-10-25), item (a): "
                          "separate private execution-only price input; "
                          "the outcome-blind P7b inventory is NOT "
                          "amended and carries no open field",
        "schema": {
            "symbol": "str", "idx": "int (0-based bar index in the "
                      "symbol's frozen 4H DEV series — the same index "
                      "space as the P7b inventory)",
            "ts": "ISO bar-open timestamp (ET)",
            "open": "float, the bar's open price from the same "
                    "committed DEV capture bytes / frozen pipeline "
                    "that produced the P7b inventory",
        },
        "symbols": 43, "total_bars": len(rows_out),
        "per_symbol": per_symbol,
        "alignment_vs_pinned_p7b_inventory": {
            "inventory_sha256": args.inventory_sha,
            "bars_compared": compared,
            "ts_mismatches": 0,
            "close_mismatches": 0,
            "nan_opens": 0,
            "result": "every pipeline bar's ts and Close equals the "
                      "pinned inventory row at the same (symbol, idx) "
                      "— the price input prices the identical series",
        },
        "input_pins": {
            "p7b_inventory_sha256": args.inventory_sha,
            "session_table_json": sha256_file(
                os.path.join(home, "session_table.json")),
            "run_study13_py": sha256_file(
                os.path.join(home, "run_study13.py")),
            "pine_backtest_py_engine_successor": sha256_file(
                os.path.join(home, "engine_successor",
                             "pine_backtest.py")),
            "raw_dev_capture_sha256_by_symbol": raw_pins,
        },
        "exec_prices_file": os.path.basename(args.out),
        "exec_prices_sha256": out_sha,
        "placement": "PRIVATE qf-data-archive ONLY — "
                     "research_inventory/exp14_exec_prices_20261025/; "
                     "the public package publishes this descriptor "
                     "(hash/counts/schema/alignment) and no prices",
        "outcome_blind": "This builder emits prices only — no returns, "
                         "no outcomes, no group differences.",
    }
    with open(args.summary, "w") as f:
        json.dump(summary, f, indent=1, sort_keys=True)
    print("ALIGNED:", compared, "bars | exec prices sha:", out_sha)
    return 0


if __name__ == "__main__":
    sys.exit(main())
