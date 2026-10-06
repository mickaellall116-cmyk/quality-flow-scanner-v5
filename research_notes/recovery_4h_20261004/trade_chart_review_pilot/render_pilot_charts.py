#!/usr/bin/env python3
"""
Pilot trade-chart evidence review renderer (REV 2 — ChatGPT read-back corrections).

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
  charts/<TRADE_ID>_<SYM>.svg   (text-safe, remotely readable)
  tables/<TRADE_ID>_<SYM>_source_rows.csv

CSV schema (REV 2):
  - row_kind, trade_id, ledger_row_index on EVERY row (deterministic anchor;
    ledger (symbol, entry_time) pairs are unique across all 240 trades).
  - event_timestamp_et / event_timestamp_utc / price as separate explicit
    columns (no timestamp/price overloading).
  - candle_end_time_et: derived as candle_start + 4h (the 4h grid interval is a
    recorded property of the retained pickles). UNAVAILABLE for non-bar rows.
  - gap rows cite the CANONICAL shard-reconstructed trade_intersection.json
    SHA-256 (02608fd4...), with an explicit note mapping the local pretty-print
    hash (a457e7a1...) to it.
  - system_engine_version, equity_session_boundary, intended_entry_price,
    target_tp1_price: UNAVAILABLE — not present in retained evidence; never
    inferred.
  - pinned_source_commit: b18a010d3d0393744428403e24bd4a59eb481ae2 on every row.

Usage:
  python3 render_pilot_charts.py [--out DIR]
"""
import argparse, csv, glob, hashlib, json, os, sys
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
PINNED_COMMIT = "b18a010d3d0393744428403e24bd4a59eb481ae2"
INTER_CANONICAL_SHA256 = "02608fd49331e5d795ac678440c7d9792f74d577eeb454d7bd68686b234fd872"
INTER_PRETTY_SHA256 = "a457e7a10845650eeb2b4be6c7a2b0ca02c91dff2667f5a4687b4e8b6b460684"
UNAVAIL = "UNAVAILABLE"

CSV_COLUMNS = [
    "row_kind", "trade_id", "ledger_row_index",
    "event_timestamp_et", "event_timestamp_utc", "candle_end_time_et",
    "price", "open", "high", "low", "close", "volume",
    "label_status", "in_holding_window", "equity_session_boundary",
    "intended_entry_price", "recorded_fill_price",
    "target_tp1_price", "target_stop_price",
    "system_engine_version", "pinned_source_commit",
    "source_file", "source_sha256", "source_sha_note", "source_row_index",
    "ledger_field", "ledger_value", "ledger_exit_reason",
]


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
    ledger_path = os.path.join(BUNDLE, "02_c1_ledger", "c1_240_trade_ledger.json")
    ledger = load_json(ledger_path)
    ledger_sha = sha256_file(ledger_path)
    audit = load_json(os.path.join(FOLLOWUP, "audit_52symbol.json"))
    audit_by_sym = {s["symbol"]: s for s in audit["symbols"]}

    # Deterministic ledger anchor: (symbol, entry_time) pairs are unique
    # across all 240 ledger trades (verified). Resolve once, record the
    # integer row index on every CSV row.
    def ledger_row(sym, entry_time):
        et = norm_ts(entry_time)
        matches = [i for i, t in enumerate(ledger["trades"])
                   if t["symbol"] == sym and norm_ts(t["entry_time"]) == et]
        assert len(matches) == 1, f"non-unique ledger match for {sym} {et}: {matches}"
        return matches[0]

    gap_sha_note = (
        "canonical shard-reconstructed SHA-256 of trade_intersection.json; "
        f"local pretty-print copy SHA-256 {INTER_PRETTY_SHA256} is "
        "content-identical (see cp1_followup/README.md shard reassembly)"
    )

    for sel in selection["selected"]:
        tid, sym = sel["trade_id"], sel["symbol"]
        it = itrades[tid]
        li = ledger_row(sym, it["entry_time"])
        lrow = ledger["trades"][li]
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

        # ---- source-row table (REV 2 schema) ----
        csv_path = os.path.join(tables_dir, f"{tid}_{sym}_source_rows.csv")
        with open(csv_path, "w", newline="") as f:
            # lineterminator="\n": CRLF would be normalized on upload, breaking
            # byte-parity verification. LF throughout.
            wr = csv.writer(f, lineterminator="\n")
            wr.writerow(CSV_COLUMNS)

            def base_row(kind):
                return {
                    "row_kind": kind, "trade_id": tid, "ledger_row_index": li,
                    "pinned_source_commit": PINNED_COMMIT,
                    "system_engine_version": UNAVAIL,
                    "ledger_exit_reason": lrow["exit_reason"],
                }

            for ts, row in w.iterrows():
                ts_utc = ts.tz_convert("UTC")
                shifted = is_shifted_label(ts)
                status = "SHIFTED_LABEL(derived)" if shifted else "CORRECT_LABEL(derived)"
                r = base_row("retained_bar")
                r.update({
                    "event_timestamp_et": ts.isoformat(),
                    "event_timestamp_utc": ts_utc.isoformat(),
                    # Derived: 4h grid interval is a recorded property of the
                    # retained pickles; end = start + 4h (arithmetic, not inference).
                    "candle_end_time_et": (ts + timedelta(hours=4)).isoformat(),
                    "price": UNAVAIL,
                    "open": row["Open"], "high": row["High"],
                    "low": row["Low"], "close": row["Close"],
                    "volume": row["Volume"],
                    "label_status": status,
                    "in_holding_window": entry_t <= ts <= exit_t,
                    "equity_session_boundary": UNAVAIL,
                    "intended_entry_price": UNAVAIL,
                    "recorded_fill_price": UNAVAIL,
                    "target_tp1_price": UNAVAIL,
                    "target_stop_price": UNAVAIL,
                    "source_file": os.path.basename(pkl_path),
                    "source_sha256": pkl_hash,
                    "source_sha_note": "",
                    "source_row_index": df.index.get_loc(ts),
                    "ledger_field": "", "ledger_value": "",
                })
                wr.writerow([r.get(c, "") for c in CSV_COLUMNS])

            # Event rows: recorded ledger/intersection facts, each carrying the
            # anchored trade_id and deterministic ledger row index.
            events = [
                # (kind, ts, price, ledger_field, ledger_value)
                ("event:signal", signal_t, UNAVAIL, "signal_time", it["signal_time"]),
                ("event:entry", entry_t, lrow["entry"], "entry", lrow["entry_time"]),
                ("event:initial_stop", entry_t, lrow["stop"], "stop", lrow["stop"]),
                ("event:exit", exit_t, lrow["exit"], "exit", lrow["exit_time"]),
            ]
            for kind, ts, price, field, raw in events:
                r = base_row(kind)
                r.update({
                    "event_timestamp_et": ts.isoformat(),
                    "event_timestamp_utc": ts.tz_convert("UTC").isoformat(),
                    "candle_end_time_et": UNAVAIL,
                    "price": price,
                    "open": "", "high": "", "low": "", "close": "", "volume": "",
                    "label_status": "", "in_holding_window": entry_t <= ts <= exit_t,
                    "equity_session_boundary": UNAVAIL,
                    "intended_entry_price": UNAVAIL,
                    # The ledger records a single entry price (the backtest's
                    # recorded fill). No separate "intended entry" exists in
                    # retained evidence.
                    "recorded_fill_price": lrow["entry"] if kind == "event:entry" else UNAVAIL,
                    # Ledger carries tp1_hit (bool) only; no TP1 price target.
                    "target_tp1_price": UNAVAIL,
                    "target_stop_price": lrow["stop"] if kind in ("event:entry", "event:initial_stop") else UNAVAIL,
                    "source_file": os.path.basename(ledger_path),
                    "source_sha256": ledger_sha,
                    "source_sha_note": "",
                    "source_row_index": "",
                    "ledger_field": field,
                    "ledger_value": raw,
                })
                wr.writerow([r.get(c, "") for c in CSV_COLUMNS])

            # Gap refs (audit facts, from intersection record). Cited against
            # the CANONICAL shard-reconstructed hash, with the pretty-print
            # mapping note — never the local-only pretty-print hash alone.
            for gr in it.get("gap_refs", []):
                r = base_row("audit_gap_ref")
                r.update({
                    "event_timestamp_et": "", "event_timestamp_utc": "",
                    "candle_end_time_et": UNAVAIL,
                    "price": UNAVAIL,
                    "open": "", "high": "", "low": "", "close": "", "volume": "",
                    "label_status": "", "in_holding_window": "",
                    "equity_session_boundary": UNAVAIL,
                    "intended_entry_price": UNAVAIL,
                    "recorded_fill_price": UNAVAIL,
                    "target_tp1_price": UNAVAIL,
                    "target_stop_price": UNAVAIL,
                    "source_file": "trade_intersection.json",
                    "source_sha256": INTER_CANONICAL_SHA256,
                    "source_sha_note": gap_sha_note,
                    "source_row_index": "",
                    "ledger_field": "gap_refs",
                    "ledger_value": gr,
                })
                wr.writerow([r.get(c, "") for c in CSV_COLUMNS])

        # ---- chart (PNG + SVG) ----
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

        # SVG first (text-safe: matplotlib SVG backend emits <text> elements;
        # self-contained; remotely readable).
        svg_path = os.path.join(charts_dir, f"{tid}_{sym}.svg")
        with matplotlib.rc_context({"svg.fonttype": "none"}):
            fig.savefig(svg_path, format="svg")

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

        print(f"rendered {tid} {sym}: {len(w)} bars, {n_shifted} shifted-labeled, "
              f"ledger_row={li}")

    # ---- manifest: every file in the output dir (2c) ----
    man_path = os.path.join(out, "SHA256_MANIFEST.txt")
    manifest_files = []
    for pat in ("charts/*", "tables/*", "README.md", "pilot_selection.json",
                "render_pilot_charts.py", "SHA256_MANIFEST.txt"):
        manifest_files.extend(sorted(glob.glob(os.path.join(out, pat))))
    with open(man_path, "w") as f:
        for p in manifest_files:
            rel = os.path.relpath(p, out)
            if rel == "SHA256_MANIFEST.txt":
                continue  # self-hash excluded; listed last with placeholder
            f.write(f"{sha256_file(p)}  {rel}\n")
    print("manifest:", man_path)


if __name__ == "__main__":
    main()
