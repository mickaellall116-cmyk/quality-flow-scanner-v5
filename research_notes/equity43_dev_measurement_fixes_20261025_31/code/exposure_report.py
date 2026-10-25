"""P6 — Leverage / exposure reporting, FULL-GRID successor (-31).

QF-EQUITY43-DEV-MEASUREMENT-FIXES-20261025-31.

Bounded repair of the -30 P6 artifact under ChatGPT's independent
-30 verdict (Slack thread TS 1792945625.327969, 2026-10-25 12:27
ET): P8/P2/P3/P9 PASS (bounded); P6 HOLD. The -30 code's own
reporting contract (exposure_report.py:13-19) requires exposure at
each event timestamp, but its compute_exposure() sampled the
distinct ENTRY times only. Exit and equity-mark timestamps were
omitted: a loss realized at an exit reduces the equity denominator
while other positions remain open, so entry-only sampling can miss
the true peak and distort the mean and the maximum single-position
share. The -30 figures (peak gross 2.7859x, mean 1.18x) are
therefore not qualified as the run-level exposure statistics.

This successor changes the SAMPLING ONLY. Position reconstruction
(entry notionals from the -13 ledger's entry/stop + the frozen
sizing rule, risk_dollars = 1% x equity at entry, equity taken from
the committed -29r all-bar equity series; sizing bases A/B) is the
-30 reconstruction verbatim, and the superseded entry-only figures
embedded in the emitted artifact are reproduced by executing the
pinned -30 module itself (sha256 asserted before import).

SAMPLING GRID (the repair): the full committed equity/event grid —
the union of
  * every position entry timestamp,
  * every position exit timestamp (censored positions run to the
    terminal mark, as in -30), and
  * every timestamp of the committed -29r all-bar equity series
    (the repaired, session-table-binned series).
On the DEV record every entry and exit timestamp is also a series
timestamp, so the union is the series' 964 distinct timestamps
(173 entry, 148 exit, 63 coincident entry+exit).

COINCIDENT-TIMESTAMP CONVENTION (stated per the verdict):
POST-EVENT. At any grid timestamp t the sample is taken after all
events stamped at t are applied:
  * a position is open at t iff entry_time <= t < exit_time — an
    exit stamped at t is CLOSED, an entry stamped at t is OPEN;
  * equity at t is the last mark of the committed series at or
    before t IN COMMITTED ORDER. Where a bar_close mark and an
    event mark share a timestamp, the event mark is later in
    committed order, so equity at t is the post-event marked
    equity (realized exit P&L stamped at t included).
Disclosure: the -30 sampling equity (eq_le over value-sorted mark
tuples) resolved coincident timestamps to the LARGER of the two
mark values, an artifact of tuple sorting; the artifact's
convention_bridge block isolates that tie-break's effect from the
grid effect so the total delta decomposes exactly.

DECLARED LIMIT (retained from -30, verbatim in substance):
notionals are the FULL entry notionals held until exit_time: after
a TP1 partial the runner is half size, and TP1 timing is not
carried in the ledger, so the intra-hold exposure path is an upper
bound and the exact path is UNVERIFIABLE from the record. The grid
repair makes the SAMPLED peak the peak over the full committed
grid; it remains a sampled statistic of that upper-bound path.
"""
import hashlib
import importlib.util
import json
import os
from bisect import bisect_left, bisect_right
from datetime import datetime

RISK_PCT = 0.01  # frozen: pine_backtest RISK_PCT
PRED_PKG = "equity43_dev_measurement_fixes_20261025_30"
PRED_EXPOSURE_SHA256 = ("f219f34248112048c4d4c5af4908fc4a6a33f2c8f9bcee"
                        "44f7ce87fb262cf248")


def entry_notional(entry, stop, equity_at_entry):
    """Frozen sizing: size = risk_dollars / (entry - stop) with
    risk_dollars = RISK_PCT x equity; notional = size x entry.
    (Identical to -30.)"""
    risk_frac = (entry - stop) / entry
    if risk_frac <= 0:
        raise ValueError("non-positive risk fraction")
    return (RISK_PCT * equity_at_entry) / risk_frac


def _repo_root():
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


def load_predecessor():
    """Import the pinned -30 exposure module (hash asserted first;
    fail closed on mismatch). Used to reproduce the SUPERSEDED
    entry-only figures with the exact code that produced them."""
    path = os.path.join(_repo_root(), "research_notes", PRED_PKG,
                        "code", "exposure_report.py")
    digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
    if digest != PRED_EXPOSURE_SHA256:
        raise ValueError(f"predecessor pin mismatch: {digest}")
    spec = importlib.util.spec_from_file_location(
        "exposure_report_30", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def committed_order_equity(marks):
    """marks: [(ts, value)] in COMMITTED (file) order. Returns
    (eq, distinct_ts): eq(t) = value of the last mark in committed
    order with timestamp <= t (at coincident timestamps, the later
    mark in committed order — the event mark); raises ValueError
    if no mark exists at or before t (fail closed)."""
    last = {}
    for ts, v in marks:
        last[ts] = v
    dts = sorted(last)
    vals = [last[t] for t in dts]

    def eq(t):
        i = bisect_right(dts, t) - 1
        if i < 0:
            raise ValueError(f"no equity mark at or before {t}")
        return vals[i]

    return eq, dts


def build_grid(positions, mark_timestamps):
    """The full committed grid: sorted union of entry timestamps,
    exit timestamps, and every equity-series timestamp."""
    grid = set(mark_timestamps)
    for p in positions:
        grid.add(p["entry_time"])
        grid.add(p["exit_time"])
    return sorted(grid)


def compute_exposure_grid(positions, eq, grid, entry_ts, exit_ts):
    """Sample exposure on the given grid under the POST-EVENT
    convention: a position is open at t iff entry_time <= t <
    exit_time; equity is eq(t). Returns the run summary with the
    peak and max-single-share rows identified by timestamp class.
    Pure function — fixtures pin it exactly."""
    rows = []
    for t in grid:
        openp = [p for p in positions
                 if p["entry_time"] <= t < p["exit_time"]]
        e = eq(t)
        gross = sum(abs(p["notional"]) for p in openp) / e
        net = sum(p["notional"] for p in openp) / e
        share = max((abs(p["notional"]) / e for p in openp),
                    default=0.0)
        classes = []
        if t in entry_ts:
            classes.append("entry")
        if t in exit_ts:
            classes.append("exit")
        classes.append("series")
        rows.append({"t": t, "open": len(openp), "gross": gross,
                     "net": net, "max_single_share": share,
                     "classes": classes})
    if not rows:
        return {"samples": 0, "peak_gross": 0.0, "mean_gross": 0.0,
                "peak_net": 0.0, "max_single_share": 0.0, "rows": []}
    peak = max(rows, key=lambda r: r["gross"])
    share_row = max(rows, key=lambda r: r["max_single_share"])
    return {
        "samples": len(rows),
        "peak_gross": peak["gross"],
        "peak_gross_at": peak["t"],
        "peak_gross_at_classes": peak["classes"],
        "peak_open": peak["open"],
        "mean_gross": sum(r["gross"] for r in rows) / len(rows),
        "peak_net": max(r["net"] for r in rows),
        "max_single_share": share_row["max_single_share"],
        "max_single_share_at": share_row["t"],
        "max_single_share_at_classes": share_row["classes"],
        "max_concurrent": max(r["open"] for r in rows),
        "rows": rows,
    }


def _load_inputs():
    root = _repo_root()
    ledger = json.load(open(os.path.join(
        root, "research_notes", "equity43_dev_order_censor_20261023_13",
        "trade_ledger.json")))
    series = json.load(open(os.path.join(
        root, "research_notes",
        "equity43_dev_measurement_fixes_20261025_29r", "artifacts",
        "equity_series_allbar.json")))["4bps"]
    return ledger, series


def dev_application():
    """Reconstruct the DEV (4bps C1 view) exposure report on the
    full committed grid. Returns the regenerated artifact dict."""
    ledger, series = _load_inputs()
    # -30 reconstruction, verbatim: marks value-sorted as tuples for
    # the SIZING bases (this ordering is part of the pinned -30
    # sizing basis and is not what the repair changes).
    marks_sorted = sorted((datetime.fromisoformat(t), v)
                          for t, v, _k in series)
    mt = [t for t, _v in marks_sorted]
    mv = [v for _t, v in marks_sorted]
    terminal = mt[-1]

    def eq_le(ts):
        i = bisect_right(mt, ts) - 1
        return mv[i] if i >= 0 else None

    def eq_ge(ts):
        i = bisect_left(mt, ts)
        return mv[i] if i < len(mv) else None

    base = []
    for r in ledger:
        if not r["taken_4bps"]:
            continue
        base.append({
            "symbol": r["symbol"], "signal_idx": r["signal_idx"],
            "entry_time": datetime.fromisoformat(r["entry_time"]),
            "exit_time": (datetime.fromisoformat(r["exit_time"])
                          if r["exit_time"] else terminal),
            "entry": r["entry"], "stop": r["stop"],
            "censored": bool(r["censored"])})

    # Sampling equity: committed order (the repair's convention).
    marks_co = [(datetime.fromisoformat(t), v) for t, v, _k in series]
    eq_grid, series_ts = committed_order_equity(marks_co)
    entry_ts = {p["entry_time"] for p in base}
    exit_ts = {p["exit_time"] for p in base if not p["censored"]}
    grid = build_grid(base, series_ts)

    def sized(eq_for_entry):
        pos = []
        for p in base:
            q = dict(p)
            q["notional"] = entry_notional(
                p["entry"], p["stop"], eq_for_entry(p["entry_time"]))
            pos.append(q)
        return pos

    def summarize(rep):
        return {
            "peak_gross": rep["peak_gross"],
            "peak_gross_at": rep["peak_gross_at"].isoformat(),
            "peak_gross_at_classes": rep["peak_gross_at_classes"],
            "peak_open": rep["peak_open"],
            "mean_gross": rep["mean_gross"],
            "peak_net": rep["peak_net"],
            "max_single_share": rep["max_single_share"],
            "max_single_share_at":
                rep["max_single_share_at"].isoformat(),
            "max_single_share_at_classes":
                rep["max_single_share_at_classes"],
            "max_concurrent": rep["max_concurrent"],
            "samples": rep["samples"]}

    corrected = {}
    bridge = {}
    for eqf, label in ((eq_le, "A_last_mark_le_entry"),
                       (eq_ge, "B_first_mark_ge_entry")):
        pos = sized(eqf)
        rep = compute_exposure_grid(pos, eq_grid, grid,
                                    entry_ts, exit_ts)
        corrected[label] = summarize(rep)
        if label.startswith("A"):
            entry_grid = sorted(entry_ts)
            rep_e = compute_exposure_grid(pos, eq_grid, entry_grid,
                                          entry_ts, exit_ts)
            bridge = {"grid": "entry timestamps only",
                      "equity": "committed-order (this successor)",
                      "basis": label,
                      "peak_gross": rep_e["peak_gross"],
                      "mean_gross": rep_e["mean_gross"],
                      "max_single_share": rep_e["max_single_share"],
                      "samples": rep_e["samples"]}

    flat_level = mv[0]
    pos_flat = []
    for p in base:
        q = dict(p)
        q["notional"] = entry_notional(p["entry"], p["stop"],
                                       flat_level)
        pos_flat.append(q)
    rep_flat = compute_exposure_grid(
        pos_flat, lambda t: flat_level, grid, entry_ts, exit_ts)
    flat = {"level": flat_level,
            "peak_gross": rep_flat["peak_gross"],
            "peak_gross_at": rep_flat["peak_gross_at"].isoformat(),
            "mean_gross": rep_flat["mean_gross"],
            "max_single_share": rep_flat["max_single_share"],
            "samples": rep_flat["samples"],
            "recorded_proxy": "2.83x (-27 §2.6 reconstruction of "
                              "Claude's ~2.8x draft figure)"}

    # Superseded figures, reproduced by the pinned -30 module.
    pred = load_predecessor()
    sup = pred.dev_application()

    out = {
        "artifact": "P6 exposure report — REGENERATED (-31) under "
                    "the -30 verdict's bounded P6 repair",
        "view": "4bps C1 (DEV, exploratory — not edge evidence)",
        "positions": len(base),
        "sampling": {
            "grid": "full committed equity/event grid: union of "
                    "entry timestamps, exit timestamps, and every "
                    "timestamp of the committed -29r all-bar "
                    "equity series (repaired, session-table-"
                    "binned)",
            "grid_timestamps": len(grid),
            "entry_timestamps": len(entry_ts),
            "exit_timestamps": len(exit_ts),
            "series_timestamps": len(series_ts),
            "coincident_entry_exit_timestamps":
                len(entry_ts & exit_ts),
            "convention": "POST-EVENT at coincident timestamps: "
                          "open at t iff entry_time <= t < "
                          "exit_time (exit stamped at t is "
                          "closed, entry stamped at t is open); "
                          "equity at t is the last committed-"
                          "series mark at or before t in "
                          "committed order (the event mark where "
                          "a bar_close and an event mark share "
                          "the timestamp).",
        },
        "corrected_full_grid": {
            "basis": corrected,
            "flat_equity_crosscheck": flat,
        },
        "convention_bridge": bridge,
        "superseded_entry_only": {
            "status": "SUPERSEDED by the -30 verdict (P6 HOLD): "
                      "entry-only sampling; not qualified as the "
                      "run-level exposure statistics",
            "source": "-30 artifacts/exposure_dev.json (commit "
                      "d077532), reproduced in this run by "
                      "executing the pinned -30 exposure_report.py "
                      f"(sha256 {PRED_EXPOSURE_SHA256})",
            "basis": sup["basis"],
            "flat_equity_crosscheck": sup["flat_equity_crosscheck"],
        },
        "largest_entry_notional": sup["largest_entry_notional"],
        "declared_limits": [
            "Full entry notional is held until exit_time: after a "
            "TP1 partial the runner is half size, TP1 timing is "
            "not in the ledger, so the intra-hold exposure path "
            "is an UPPER BOUND; the exact path is UNVERIFIABLE "
            "from the committed record.",
            "Equity at entry (sizing) is taken from the committed "
            "-29r all-bar equity series (basis A: last mark <= "
            "entry; basis B: first mark >= entry); the two bases "
            "bound the simulator's own event-time marked equity. "
            "Sampling equity follows the stated committed-order "
            "post-event convention.",
            "Samples are the full committed grid (entry + exit + "
            "every equity-series timestamp), replacing the -30 "
            "artifact's entry-event-timestamps-only sampling, "
            "which the -30 verdict held unqualified.",
            "Heat (planned risk / equity, capped at 5%) is a "
            "different quantity and is never reported here as "
            "exposure.",
        ],
    }
    return out


def main():
    art = dev_application()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "artifacts", "exposure_dev.json")
    with open(out, "w") as f:
        json.dump(art, f, indent=1)
        f.write("\n")
    print(f"WROTE {out}")
    for k, v in art["corrected_full_grid"]["basis"].items():
        print(k, "peak", round(v["peak_gross"], 4),
              "at", v["peak_gross_at"], v["peak_gross_at_classes"],
              "mean", round(v["mean_gross"], 4),
              "max_single", round(v["max_single_share"], 4),
              "samples", v["samples"])
    for k, v in art["superseded_entry_only"]["basis"].items():
        print("SUPERSEDED", k, "peak", round(v["peak_gross"], 4),
              "mean", round(v["mean_gross"], 4),
              "max_single", round(v["max_single_share"], 4),
              "samples", v["samples"])
    b = art["convention_bridge"]
    print("bridge entry-only/committed-order peak",
          round(b["peak_gross"], 4), "mean",
          round(b["mean_gross"], 4), "max_single",
          round(b["max_single_share"], 4))
    print("flat cross-check peak",
          round(art["corrected_full_grid"]
                ["flat_equity_crosscheck"]["peak_gross"], 4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
