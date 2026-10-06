#!/usr/bin/env python3
"""
Pilot trade-chart evidence review renderer.

READ-ONLY: reuses existing CP1 artifacts only. No fresh data fetch, no
holdout access, no frozen-system changes, no performance computation.

Reads:
  ../cp1_followup/trade_intersection.json   (pilot selection + gap refs)
  ../cp1_bundle/02_c1_ledger/c1_240_trade_ledger.json  (entry/stop/exit facts)
  ../cp1_followup/audit_52symbol.json       (shifted/absent slot evidence)
  ../../../backtest_cache/v3/h4_<SYM>.pkl    (retained defective-grid bars)
  pilot_selection.json                       (this review's selection)

Writes (into this directory):
  charts/<TRADE_ID>_<SYM>.png
  tables/<TRADE_ID>_<SYM>_source_rows.csv

Usage:
  python3 render_pilot_charts.py [--out DIR]
"""
import argparse, csv, hashlib, json, os, sys
from datetime import datetime, timedelta, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FOLLOWUP = os.path.normpath(os.path.join(HERE, "..", "cp1_followup"))
BUNDLE = os.path.normpath(os.path.join(HERE, "..", "cp1_bundle"))
CACHE = os.path.normpath(os.path.join(HERE, "..", "..", "..", "backtest_cache", "v3"))

NY = "America/New_York"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    with open(path) as f:
        return json.load(f)


def norm_ts(s):
    return str(s).replace("T", " ").strip()


def is_shifted_label(ts):
    """Derived overlay: defective-grid equity label during EST.

    The retained h4 pickles anchor 4h bins at fixed UTC times; during EST
    (UTC-5) the session bars are labeled 08:30/12:30 ET instead of the
    session-correct 09:30/13:30 ET. This is a DERIVED classification from
    the audit evidence, not a recorded field.
    """
    ts_ny = ts.tz_convert(NY)
    # EST = UTC-5; label hour 8 or 12 with -05:00 offset => shifted
    return ts_ny.utcoffset() == timedelta(hours=-5) and ts_ny.hour in (8, 12)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=HERE)
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    charts_dir = os.path.join(out, "charts")
    tables_dir = os.path.join(out, "tables")
    os.makedirs(charts_dir, exist_ok=True)
    os.makedirs(tables_dir, exist_ok=True)

    selection = load_json(os.path.join(out, "pilot_selection.json"))
    inter = load_json(os.path.join(FOLLOWUP, "trade_intersection.json"))
    itrades = {t["trade_id"]: t for t in inter["trades"]}
    ledger = load_json(os.path.join(BUNDLE, "02_c1_ledger", "c1_240_trade_ledger.json"))
    audit = load_json(os.path.join(FOLLOWUP, "audit_52symbol.json"))
    audit_by_sym = {s["symbol"]: s for s in audit["symbols"]}

    manifest_rows = []
    for sel in selection["selected"]:
        tid, sym = sel["trade_id"], sel["symbol"]
        it = itrades[tid]
        et = norm_ts(it["entry_time"])
        lrow = next(
            t for t in ledger["trades"]
            if t["symbol"] == sym and norm_ts(t["entry_time"]) == et
        )
        arec = audit_by_sym[sym]
        pkl_path = os.path.join(CACHE, f"h4_{sym}.pkl")
        pkl_hash = sha256_file(pkl_path)
        df = pd.read_pickle(pkl_path)
        if df.index.tz is None:
            df.index = df.index.tz_localize(NY)
        else:
            df.index = df.index.tz_convert(NY)

        signal_t = pd.Timestamp(it["signal_time"]).tz_convert(NY)
        entry_t = pd.Timestamp(it["entry_time"]).tz_convert(NY)
        exit_t = pd.Timestamp(it["exit_time"]).tz_convert(NY)

        # Window: 3 bars before signal, 3 bars after exit (bounded by data)
        win_start = signal_t - timedelta(hours=16)
        win_end = exit_t + timedelta(hours=16)
        w = df.loc[win_start:win_end].copy()

        # ---- source-row table ----
        csv_path = os.path.join(tables_dir, f"{tid}_{sym}_source_rows.csv")
        with open(csv_path, "w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow([
                "row_kind", "timestamp_ny", "timestamp_utc", "open", "high",
                "low", "close", "volume", "label_status", "in_holding_window",
                "source_file", "source_sha256", "source_row_index",
                "ledger_field", "ledger_value", "ledger_exit_reason",
            ])
            for i, (ts, row) in enumerate(w.iterrows()):
                ts_utc = ts.tz_convert("UTC")
                shifted = is_shifted_label(ts)
                status = "SHIFTED_LABEL(derived)" if shifted else "CORRECT_LABEL(derived)"
                in_hold = entry_t <= ts <= exit_t
                wr.writerow([
                    "retained_bar", ts.isoformat(), ts_utc.isoformat(),
                    row["Open"], row["High"], row["Low"], row["Close"],
                    row["Volume"], status, in_hold,
                    os.path.basename(pkl_path), pkl_hash,
                    df.index.get_loc(ts), "", "", "",
                ])
            # Event rows: recorded ledger/intersection facts
            events = [
                ("signal", signal_t, "", it["signal_time"], "signal_time"),
                ("entry", entry_t, lrow["entry"], lrow["entry_time"], "entry"),
                ("initial_stop", entry_t, lrow["stop"], "", "stop"),
                ("exit", exit_t, lrow["exit"], lrow["exit_time"], "exit"),
            ]
            for kind, ts, val, raw, field in events:
                wr.writerow([
                    f"event:{kind}", ts.isoformat(), ts.tz_convert("UTC").isoformat(),
                    "", "", "", val, "", "", entry_t <= ts <= exit_t,
                    "c1_240_trade_ledger.json", sha256_file(os.path.join(
                        BUNDLE, "02_c1_ledger", "c1_240_trade_ledger.json")),
                    "", field, raw if raw else val, lrow["exit_reason"],
                ])
            # Gap refs (audit facts, from intersection record)
            for gr in it.get("gap_refs", []):
                wr.writerow([
                    "audit_gap_ref", "", "", "", "", "", "", "", "", "",
                    "trade_intersection.json",
                    sha256_file(os.path.join(FOLLOWUP, "trade_intersection.json")),
                    "", "gap_refs", gr, "",
                ])

        # ---- chart ----
        # figsize (12,6) dpi=130: balances readability against the GitHub MCP
        # connector's ~128KB single-argument limit (raw-text upload).
        fig, ax = plt.subplots(figsize=(12, 6))
        xs = mdates.date2num(w.index.to_pydatetime())
        width = 0.12
        up = w["Close"] >= w["Open"]
        for i, (ts, row) in enumerate(w.iterrows()):
            x = xs[i]
            shifted = is_shifted_label(ts)
            body_color = "#d62728" if not up.iloc[i] else "#2ca02c"
            edge = "#ff7f0e" if shifted else "black"   # orange edge = shifted label (derived)
            lw = 2.0 if shifted else 0.8
            ax.plot([x, x], [row["Low"], row["High"]], color="black", lw=0.8)
            ax.add_patch(plt.Rectangle(
                (x - width / 2, min(row["Open"], row["Close"])),
                width, abs(row["Close"] - row["Open"]) or 1e-9,
                facecolor=body_color, edgecolor=edge, lw=lw, zorder=3))

        # Recorded facts (ledger / intersection)
        ax.axvline(mdates.date2num(signal_t.to_pydatetime()), color="blue",
                   ls="--", lw=1.2, label="signal (recorded)")
        ax.axvline(mdates.date2num(entry_t.to_pydatetime()), color="green",
                   ls="-", lw=1.5, label="entry (recorded)")
        ax.axvline(mdates.date2num(exit_t.to_pydatetime()), color="red",
                   ls="-", lw=1.5, label="exit (recorded)")
        ax.axhline(lrow["entry"], color="green", ls=":", lw=1.0)
        ax.axhline(lrow["stop"], color="red", ls=":", lw=1.0,
                   label=f"entry {lrow['entry']} / stop {lrow['stop']} (recorded)")

        # Gap annotations (audit facts) — dates only, no interpolation
        for gi, gr in enumerate(it.get("gap_refs", [])):
            ax.text(0.98, 0.94 - 0.05 * gi,
                    f"AUDIT GAP: {gr}", transform=ax.transAxes,
                    fontsize=9, color="darkred", weight="bold", ha="right",
                    bbox=dict(facecolor="mistyrose", alpha=0.8))

        # Shifted-window annotation (derived)
        n_shifted = sum(1 for ts in w.index if is_shifted_label(ts))
        ax.text(0.98, 0.02,
                f"orange-edged bars: shifted labels (derived, n={n_shifted})\n"
                f"1H constituents: UNAVAILABLE (no 1h pickles retained)",
                transform=ax.transAxes, fontsize=8, ha="right",
                bbox=dict(facecolor="wheat", alpha=0.8))

        ax.set_title(
            f"{tid} {sym} ({it['asset_class']}) — retained h4 bars, defective grid as stored\n"
            f"signal {signal_t} | entry {entry_t} | exit {exit_t} ({lrow['exit_reason']})",
            fontsize=11)
        ax.set_ylabel("price")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M ET"))
        ax2labels = [f"{t.tz_convert('UTC').strftime('%H:%M')}Z"
                     for t in w.index[::max(1, len(w) // 12)]]
        fig.text(0.5, 0.01,
                 "x-axis: America/New_York candle-start labels (as stored); "
                 "UTC equivalents shown sparsely: " + ", ".join(ax2labels[:6]),
                 ha="center", fontsize=7, style="italic")
        ax.legend(loc="upper left", fontsize=8)
        fig.tight_layout(rect=[0, 0.03, 1, 1])
        png_path = os.path.join(charts_dir, f"{tid}_{sym}.png")
        # dpi=150: dpi=110 triggers an Agg subpixel rasterization artifact
        # (spurious gray box) in matplotlib 3.6.3; 130+ is clean.
        # Palette-32: keeps PNGs small enough for the GitHub MCP connector's
        # ~128KB single-argument limit (raw text upload, no base64).
        import io as _io
        from PIL import Image as _Image
        _buf = _io.BytesIO()
        fig.savefig(_buf, dpi=130, format="png")
        plt.close(fig)
        _buf.seek(0)
        _img = _Image.open(_buf).convert(
            "P", palette=_Image.ADAPTIVE, colors=32)
        _img.save(png_path, format="PNG", optimize=True)

        for p in (png_path, csv_path):
            manifest_rows.append((p, sha256_file(p)))
        print(f"rendered {tid} {sym}: {len(w)} bars, {n_shifted} shifted-labeled")

    man_path = os.path.join(out, "SHA256_MANIFEST.txt")
    with open(man_path, "w") as f:
        for p, h in sorted(manifest_rows):
            f.write(f"{h}  {os.path.relpath(p, out)}\n")
    print("manifest:", man_path)


if __name__ == "__main__":
    main()
