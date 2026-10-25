"""P6 — Leverage / exposure reporting (semantic pin, -30).

QF-EQUITY43-DEV-MEASUREMENT-FIXES-20261025-30.

Implements the reporting specification written in -27 §2.6 (the P6
answer converted by -28 R20): the frozen system has NO notional or
cash cap — the only caps are count (MAX_CONCURRENT = 5) and planned
heat (5%) — and position notional = risk_dollars / risk_frac scales
inversely with stop width, unbounded by any equity fraction. Heat is
therefore never reported as, or equated with, leverage or exposure.
Every results template reports, per the spec:

  * per position: entry notional (size x entry);
  * per event timestamp: gross exposure = sum |open notional| /
    equity, and net exposure likewise signed (this system is
    long-only, so the two coincide on the DEV record — the code
    keeps them distinct);
  * per run: peak gross exposure, mean gross exposure, and the
    maximum single-position share (largest open notional / equity).

`compute_exposure()` is the pinned computation; the battery's
fixtures verify it against hand-computed values exactly. The DEV
application below reconstructs entry notionals from the committed
artifacts ONLY (the -13 ledger's entry/stop + the frozen sizing
rule, risk_dollars = 1% x equity at entry, with equity taken from
the committed -29r all-bar equity series) and declares its basis
and limits in the emitted artifact:

  * equity-at-entry basis A: last series mark <= entry_time;
    basis B (sensitivity): first mark >= entry_time;
  * a flat-equity cross-check reproduces the ~2.83x proxy figure
    recorded in -27 §2.6 / Claude's draft (~2.8x);
  * notionals are the FULL entry notionals held until exit_time:
    after a TP1 partial the runner is half size, and TP1 timing is
    not carried in the ledger, so the intra-hold path is an upper
    bound and the exact path is UNVERIFIABLE from the record;
  * samples are the run's entry event timestamps; censored
    positions are open through the terminal mark.
"""
import json
import os
from bisect import bisect_left, bisect_right
from datetime import datetime

RISK_PCT = 0.01  # frozen: pine_backtest RISK_PCT


def entry_notional(entry, stop, equity_at_entry):
    """Frozen sizing: size = risk_dollars / (entry - stop) with
    risk_dollars = RISK_PCT x equity; notional = size x entry."""
    risk_frac = (entry - stop) / entry
    if risk_frac <= 0:
        raise ValueError("non-positive risk fraction")
    return (RISK_PCT * equity_at_entry) / risk_frac


def compute_exposure(positions, equity_at):
    """positions: [{entry_time, exit_time, notional}] (datetimes,
    notional > 0, long-only). equity_at: ts -> equity (> 0).
    Samples at the sorted distinct entry times; a position is open
    at t iff entry_time <= t < exit_time. Returns the spec's run
    summary. Pure function — fixtures pin it exactly."""
    samples = sorted({p["entry_time"] for p in positions})
    rows = []
    for t in samples:
        openp = [p for p in positions
                 if p["entry_time"] <= t < p["exit_time"]]
        eq = equity_at(t)
        gross = sum(abs(p["notional"]) for p in openp) / eq
        net = sum(p["notional"] for p in openp) / eq
        share = max((abs(p["notional"]) / eq for p in openp),
                    default=0.0)
        rows.append({"t": t, "open": len(openp), "gross": gross,
                     "net": net, "max_single_share": share})
    if not rows:
        return {"samples": 0, "peak_gross": 0.0, "mean_gross": 0.0,
                "peak_net": 0.0, "max_single_share": 0.0, "rows": []}
    peak = max(rows, key=lambda r: r["gross"])
    return {
        "samples": len(rows),
        "peak_gross": peak["gross"],
        "peak_gross_at": peak["t"],
        "mean_gross": sum(r["gross"] for r in rows) / len(rows),
        "peak_net": max(r["net"] for r in rows),
        "max_single_share": max(r["max_single_share"] for r in rows),
        "max_concurrent": max(r["open"] for r in rows),
        "rows": rows,
    }


def _repo_root():
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


def dev_application():
    """Reconstruct the DEV (4bps C1 view) exposure report from the
    committed artifacts. Returns the artifact dict."""
    root = _repo_root()
    ledger = json.load(open(os.path.join(
        root, "research_notes", "equity43_dev_order_censor_20261023_13",
        "trade_ledger.json")))
    series = json.load(open(os.path.join(
        root, "research_notes",
        "equity43_dev_measurement_fixes_20261025_29r", "artifacts",
        "equity_series_allbar.json")))["4bps"]
    marks = sorted((datetime.fromisoformat(t), v) for t, v, _k in series)
    mt = [t for t, _v in marks]
    mv = [v for _t, v in marks]
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

    def run(eq_for_entry, label):
        pos = []
        for p in base:
            q = dict(p)
            q["notional"] = entry_notional(
                p["entry"], p["stop"], eq_for_entry(p["entry_time"]))
            pos.append(q)
        rep = compute_exposure(
            pos, lambda t: eq_le(t) if eq_le(t) else eq_for_entry(t))
        return label, rep, pos

    out = {"view": "4bps C1 (DEV, exploratory — not edge evidence)",
           "positions": len(base),
           "basis": {}}
    for eqf, label in ((eq_le, "A_last_mark_le_entry"),
                       (eq_ge, "B_first_mark_ge_entry")):
        _l, rep, pos = run(eqf, label)
        out["basis"][label] = {
            "peak_gross": rep["peak_gross"],
            "peak_gross_at": rep["peak_gross_at"].isoformat(),
            "mean_gross": rep["mean_gross"],
            "peak_net": rep["peak_net"],
            "max_single_share": rep["max_single_share"],
            "max_concurrent": rep["max_concurrent"],
            "samples": rep["samples"]}
    flat_level = mv[0]
    pos_flat = []
    for p in base:
        q = dict(p)
        q["notional"] = entry_notional(p["entry"], p["stop"], flat_level)
        pos_flat.append(q)
    rep_flat = compute_exposure(pos_flat, lambda t: flat_level)
    out["flat_equity_crosscheck"] = {
        "level": flat_level, "peak_gross": rep_flat["peak_gross"],
        "mean_gross": rep_flat["mean_gross"],
        "recorded_proxy": "2.83x (-27 §2.6 reconstruction of "
                          "Claude's ~2.8x draft figure)"}
    biggest = max(base, key=lambda p: entry_notional(
        p["entry"], p["stop"], eq_le(p["entry_time"])))
    out["largest_entry_notional"] = {
        "symbol": biggest["symbol"],
        "notional": entry_notional(biggest["entry"], biggest["stop"],
                                   eq_le(biggest["entry_time"])),
        "equity_at_entry": eq_le(biggest["entry_time"]),
        "risk_frac": (biggest["entry"] - biggest["stop"])
        / biggest["entry"]}
    out["declared_limits"] = [
        "Full entry notional is held until exit_time: after a TP1 "
        "partial the runner is half size, TP1 timing is not in the "
        "ledger, so the intra-hold exposure path is an UPPER BOUND; "
        "the exact path is UNVERIFIABLE from the committed record.",
        "Equity at entry is taken from the committed -29r all-bar "
        "equity series (basis A: last mark <= entry; basis B: first "
        "mark >= entry); the two bases bound the simulator's own "
        "event-time marked equity.",
        "Samples are entry event timestamps only (the spec's "
        "per-event-timestamp reporting on the recorded event grid).",
        "Heat (planned risk / equity, capped at 5%) is a different "
        "quantity and is never reported here as exposure.",
    ]
    return out


def main():
    art = dev_application()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "artifacts", "exposure_dev.json")
    with open(out, "w") as f:
        json.dump(art, f, indent=1)
        f.write("\n")
    print(f"WROTE {out}")
    for k, v in art["basis"].items():
        print(k, "peak", round(v["peak_gross"], 4),
              "mean", round(v["mean_gross"], 4),
              "max_single", round(v["max_single_share"], 4))
    print("flat cross-check peak",
          round(art["flat_equity_crosscheck"]["peak_gross"], 4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
