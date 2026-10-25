#!/usr/bin/env python3
"""-24 FAILURE FORENSICS on the 66 oversized losses of the -13 DEV run.

Offline, recorded artifacts only:
  -13 trade_ledger.json (sha256 267e794c...) — all trade fields
  -23 ordering_labels.json — breach membership (CONFIRMED_STOP_FIRST)
  -23 intrabar pre_breach list — cross-check of breach membership

THE SET: closed taken trades, gross_r < -1.0 (the -23 supplement's basis).
Trait thresholds are PREDECLARED from the full 187 taken-closed set
(medians), never tuned to the 66. Prevention traits are HYPOTHESES ONLY;
every trait carries collateral counts (winners overall + top-5).
"""
import json, statistics
from collections import Counter, defaultdict
from datetime import datetime

LEDGER = "/tmp/anat/trade_ledger.json"
LABELS = ("/home/hatch/workspace/qf_anat_stage/wt/research_notes/"
          "equity43_dev_winner_anatomy_20261024_23/ordering_labels.json")
INTRABAR = "/tmp/anat/intrabar.json"

L = json.load(open(LEDGER))
taken = [t for t in L if t.get("taken_4bps") and not t.get("censored")]
assert len(taken) == 187, len(taken)

lab = json.load(open(LABELS))
label_of = {}
for t in lab["trades"]:
    label_of[(t["symbol"], t["entry_time"], t["signal_idx"])] = t["label"]
ib = json.load(open(INTRABAR))
pre_breach = {(s, d) for s, d in ib["pre_breach"]}

def key(t):
    return (t["symbol"], t["entry_time"][:16], t["signal_idx"])

def breached(t):
    return label_of.get(key(t)) == "CONFIRMED_STOP_FIRST"

# cross-check breach membership: labels vs intrabar list (entry-date keyed)
mismatch = 0
for t in taken:
    in_ib = (t["symbol"], t["entry_time"][:16]) in pre_breach
    if in_ib != breached(t):
        mismatch += 1

THE66 = [t for t in taken if t["gross_r"] < -1.0]
WIN = [t for t in taken if t["gross_r"] > 0]
TOP5 = sorted(taken, key=lambda t: -t["gross_r"])[:5]
LOSERS_ALL = [t for t in taken if t["gross_r"] < 0]

out = {}
out["reconciliation"] = {
    "n_taken_closed": len(taken),
    "n_66": len(THE66),
    "sum_gross_66": round(sum(t["gross_r"] for t in THE66), 4),
    "supplement_figure": -92.0847,
    "reasons_66": dict(Counter(t["reason"] for t in THE66)),
    "tp1_hit_66": sum(1 for t in THE66 if t["tp1_hit"]),
    "n_winners_gross": len(WIN),
    "n_losers_all": len(LOSERS_ALL),
    "top5_symbols": [t["symbol"] for t in TOP5],
    "top5_sum_gross": round(sum(t["gross_r"] for t in TOP5), 4),
    "breach_label_vs_intrabar_mismatches": mismatch,
    "boundary_trade_net_only": [
        {"symbol": t["symbol"], "entry": t["entry_time"][:10],
         "gross": t["gross_r"], "net4": t["net_r_4bps"]}
        for t in taken if t["net_r_4bps"] < -1.0 and t["gross_r"] >= -1.0],
}

# ---- derived slot state at entry (DERIVED: from recorded entry/exit times)
def open_before(t):
    n = 0
    for o in taken:
        if o is t:
            continue
        if o["entry_time"] < t["entry_time"] and (
                o["exit_time"] is None or o["exit_time"] > t["entry_time"]):
            n += 1
    return n

for t in taken:
    t["_open_before"] = open_before(t)

# ---- exit-date clustering
by_exit_date = defaultdict(list)
for t in THE66:
    by_exit_date[t["exit_time"][:10]].append(t)
clusters = {d: v for d, v in by_exit_date.items() if len(v) >= 2}
all_exit_by_date = defaultdict(list)
for t in taken:
    all_exit_by_date[t["exit_time"][:10]].append(t)
out["exit_clustering"] = {
    "distinct_exit_dates_66": len(by_exit_date),
    "exits_per_date_hist": dict(Counter(len(v) for v in by_exit_date.values())),
    "max_cooccurring": max(len(v) for v in by_exit_date.values()),
    "n_in_multi_exit_dates": sum(len(v) for v in clusters.values()),
    "cluster_dates": [
        {"date": d, "weekday": datetime.fromisoformat(d).strftime("%a"),
         "n_66": len(v), "sum_gross_66": round(sum(t["gross_r"] for t in v), 4),
         "symbols": [t["symbol"] for t in v],
         "all_taken_exits_that_date": len(all_exit_by_date[d]),
         "all_taken_exit_gross_that_date":
             round(sum(t["gross_r"] for t in all_exit_by_date[d]), 4)}
        for d, v in sorted(clusters.items())],
}

# ---- timing
def wd(ts):
    return datetime.fromisoformat(ts[:10]).strftime("%a")

out["timing"] = {
    "entry_weekday_66": dict(Counter(wd(t["entry_time"]) for t in THE66)),
    "exit_weekday_66": dict(Counter(wd(t["exit_time"]) for t in THE66)),
    "exit_weekday_win": dict(Counter(wd(t["exit_time"]) for t in WIN)),
    "hold_bars_66": {"median": statistics.median(t["hold_bars"] for t in THE66),
                     "min": min(t["hold_bars"] for t in THE66),
                     "max": max(t["hold_bars"] for t in THE66),
                     "le2": sum(1 for t in THE66 if t["hold_bars"] <= 2),
                     "le4": sum(1 for t in THE66 if t["hold_bars"] <= 4),
                     "le10": sum(1 for t in THE66 if t["hold_bars"] <= 10)},
    "hold_bars_win_median": statistics.median(t["hold_bars"] for t in WIN),
    "entry_year_66": dict(Counter(t["entry_time"][:4] for t in THE66)),
    "entry_year_win": dict(Counter(t["entry_time"][:4] for t in WIN)),
    "entry_month_66": dict(sorted(Counter(t["entry_time"][:7] for t in THE66).items())),
}

# ---- concentration
sym66 = Counter(t["symbol"] for t in THE66)
out["concentration"] = {
    "sectors_66": dict(Counter(t["sector"] for t in THE66)),
    "sectors_win": dict(Counter(t["sector"] for t in WIN)),
    "sectors_all": dict(Counter(t["sector"] for t in taken)),
    "repeat_symbols_66": {s: c for s, c in sym66.most_common() if c >= 2},
    "distinct_symbols_66": len(sym66),
    "sum_gross_by_symbol_66": {s: round(sum(t["gross_r"] for t in THE66
                                             if t["symbol"] == s), 4)
                               for s, c in sym66.most_common() if c >= 2},
}

# ---- path
out["path"] = {
    "breached_66": sum(1 for t in THE66 if breached(t)),
    "breached_win": sum(1 for t in WIN if breached(t)),
    "open_before_66": dict(Counter(t["_open_before"] for t in THE66)),
    "open_before_win": dict(Counter(t["_open_before"] for t in WIN)),
    "rs_66": {"median": round(statistics.median(t["rs"] for t in THE66), 4),
              "min": round(min(t["rs"] for t in THE66), 4),
              "max": round(max(t["rs"] for t in THE66), 4)},
    "rs_win_median": round(statistics.median(t["rs"] for t in WIN), 4),
    "rs_all_median": round(statistics.median(t["rs"] for t in taken), 4),
}

# ---- collateral table: predeclared traits
med_rs = statistics.median(t["rs"] for t in taken)
med_risk = statistics.median((t["entry"] - t["stop"]) / t["entry"] for t in taken)
med_tp1r = statistics.median((t["tp1"] - t["entry"]) / (t["entry"] - t["stop"])
                             for t in taken)
repeat_syms = {s for s, c in sym66.items() if c >= 2}
cluster_dates = set(clusters.keys())

TRAITS = {
    "breach_member (stop threshold touched intrabar pre-exit)":
        lambda t: breached(t),
    "entered_as_5th_position (open_before==4, DERIVED)":
        lambda t: t["_open_before"] == 4,
    "entered_with_3plus_open (open_before>=3, DERIVED)":
        lambda t: t["_open_before"] >= 3,
    "rs_below_187_median":
        lambda t: t["rs"] < med_rs,
    "rs_above_187_median":
        lambda t: t["rs"] >= med_rs,
    "sector_SEMIS":
        lambda t: t["sector"] == "SEMIS",
    "entry_year_2025":
        lambda t: t["entry_time"][:4] == "2025",
    "entry_year_2026":
        lambda t: t["entry_time"][:4] == "2026",
    "exit_on_multi_exit_date (cluster member)":
        lambda t: t["exit_time"][:10] in cluster_dates,
    "failed_fast (hold_bars<=4)":
        lambda t: t["hold_bars"] <= 4,
    "narrow_planned_stop (risk_frac below 187 median)":
        lambda t: (t["entry"] - t["stop"]) / t["entry"] < med_risk,
    "far_tp1 (tp1 R-multiple above 187 median)":
        lambda t: (t["tp1"] - t["entry"]) / (t["entry"] - t["stop"]) > med_tp1r,
    "repeat_offender_symbol (>=2 appearances in the 66)":
        lambda t: t["symbol"] in repeat_syms,
    "entered_Friday":
        lambda t: wd(t["entry_time"]) == "Fri",
    "exited_Monday":
        lambda t: wd(t["exit_time"]) == "Mon",
}
coll = {}
for name, f in TRAITS.items():
    c66 = [t for t in THE66 if f(t)]
    cw = [t for t in WIN if f(t)]
    c5 = [t for t in TOP5 if f(t)]
    coll[name] = {
        "n_66": len(c66), "share_66": round(len(c66) / len(THE66), 3),
        "gross_66": round(sum(t["gross_r"] for t in c66), 4),
        "winners_with_trait": len(cw),
        "winner_gross_with_trait": round(sum(t["gross_r"] for t in cw), 4),
        "top5_with_trait": len(c5),
        "top5_symbols_with_trait": [t["symbol"] for t in c5],
    }
out["collateral"] = coll
out["medians_187"] = {"rs": round(med_rs, 4), "risk_frac": round(med_risk, 5),
                      "tp1_r_multiple": round(med_tp1r, 3)}

# ---- rs quartile bands (thresholds from the full 187 taken set)
rs_sorted = sorted(t["rs"] for t in taken)
q1, q3 = rs_sorted[len(rs_sorted) // 4], rs_sorted[3 * len(rs_sorted) // 4]
def rs_band(t):
    if t["rs"] < q1:
        return "Q1_lowest"
    if t["rs"] >= q3:
        return "Q4_highest"
    return "Q2_Q3_mid"
out["rs_bands"] = {
    "q1_cut": round(q1, 4), "median": round(med_rs, 4), "q3_cut": round(q3, 4),
    "66": dict(Counter(rs_band(t) for t in THE66)),
    "win": dict(Counter(rs_band(t) for t in WIN)),
    "all": dict(Counter(rs_band(t) for t in taken)),
    "top5_bands": [rs_band(t) for t in TOP5],
    "gross_by_band_66": {b: round(sum(t["gross_r"] for t in THE66
                                      if rs_band(t) == b), 4)
                         for b in ("Q1_lowest", "Q2_Q3_mid", "Q4_highest")},
    "gross_by_band_win": {b: round(sum(t["gross_r"] for t in WIN
                                       if rs_band(t) == b), 4)
                          for b in ("Q1_lowest", "Q2_Q3_mid", "Q4_highest")},
}

# features actually interrogated (multiple-comparisons disclosure)
out["features_compared"] = [
    "exit_date_clustering", "entry_weekday", "exit_weekday", "hold_bars",
    "entry_year", "entry_month", "sector", "symbol_repetition",
    "breach_membership", "slot_state_at_entry_DERIVED", "rs_median_split",
    "rs_quartile_bands", "planned_stop_width", "tp1_r_multiple",
    "entry_weekday_friday", "exit_weekday_monday", "exit_route",
]
out["not_recoverable"] = [
    "ADX at signal (not persisted in any pinned -13/-14/-23 artifact)",
    "trend readings / trendScore at signal (not persisted)",
    "VWAP relation at signal (not persisted)",
    "relative volume at signal (not persisted)",
    "EMA geometry at signal (not persisted)",
    "market-gate state at entry (not recorded)",
    "per-date SPY / market state series (not a recorded field)",
    "earnings dates (not recorded; external fetch forbidden by framing)",
    "closest approach to TP1 / MAE / duration under threshold (bar paths not persisted)",
    "trigger-close vs next-open gap split of the overshoot (per -23 supplement)",
]

# per-trade register of the 66 (for the memo appendix)
out["register66"] = [
    {"symbol": t["symbol"], "sector": t["sector"],
     "entry": t["entry_time"][:10], "exit": t["exit_time"][:10],
     "hold_bars": t["hold_bars"], "reason": t["reason"],
     "gross": t["gross_r"], "rs": round(t["rs"], 4),
     "breached": breached(t), "open_before": t["_open_before"]}
    for t in sorted(THE66, key=lambda t: t["exit_time"])]

print(json.dumps(out, indent=1))
