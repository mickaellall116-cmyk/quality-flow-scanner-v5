"""F7-REV protocol analysis: monotonicity, dev/val, walk-forward, costs,
concentration, bootstrap>=5000, LOSO. Pre-registered gates in REPORT.md."""
import json, warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
DIR = "/home/hatch/workspace/quality-flow-scanner-v5/selection_edge/phase2_fundamentals"
df = pd.read_json(f"{DIR}/factor_values.json")
df["signal_date"] = pd.to_datetime(df["signal_date"])
rng = np.random.default_rng(20260924)
out = {}

def summ(d, col="r50"):
    x = d[col].to_numpy()
    return {"n": int(len(x)), "mean": round(float(x.mean()), 4),
            "winrate": round(float((x > 0).mean()), 4),
            "total": round(float(x.sum()), 2)}

# --- full-sample buckets ---
out["full"] = {b: summ(df[df.bucket == b]) for b in ["top", "mid", "bottom"]}
f = out["full"]
out["monotonic_full"] = bool(f["top"]["mean"] > f["mid"]["mean"] > f["bottom"]["mean"])
out["top_minus_bottom"] = round(f["top"]["mean"] - f["bottom"]["mean"], 4)

# --- costs ---
out["costs"] = {c: {b: summ(df[df.bucket == b], c)["mean"]
                    for b in ["top", "mid", "bottom"]}
                for c in ["r25", "r50", "r75", "r100"]}

# --- dev / val ---
dev = df[df.signal_date < "2025-01-01"]
val = df[df.signal_date >= "2025-01-01"]
out["dev"] = {b: summ(dev[dev.bucket == b]) for b in ["top", "mid", "bottom"]}
out["val"] = {b: summ(val[val.bucket == b]) for b in ["top", "mid", "bottom"]}
out["monotonic_dev"] = bool(out["dev"]["top"]["mean"] > out["dev"]["mid"]["mean"] > out["dev"]["bottom"]["mean"])
out["monotonic_val"] = bool(out["val"]["top"]["mean"] > out["val"]["mid"]["mean"] > out["val"]["bottom"]["mean"])

# --- year splits ---
out["years"] = {}
for y in [2024, 2025, 2026]:
    yd = df[df.signal_date.dt.year == y]
    out["years"][str(y)] = {b: summ(yd[yd.bucket == b]) for b in ["top", "mid", "bottom"]}

# --- walk-forward 12mo train / 6mo test ---
wf = []
starts = pd.to_datetime(["2023-10-01", "2024-04-01", "2024-10-01", "2025-04-01"])
for s in starts:
    tr_end, te_end = s + pd.DateOffset(months=12), s + pd.DateOffset(months=18)
    trd = df[(df.signal_date >= s) & (df.signal_date < tr_end)]
    ted = df[(df.signal_date >= tr_end) & (df.signal_date < te_end)]
    # gate: did monotonicity hold in train?
    tm = {b: trd[trd.bucket == b]["r50"].mean() for b in ["top", "mid", "bottom"]}
    gate = tm["top"] > tm["mid"] > tm["bottom"]
    te = {b: summ(ted[ted.bucket == b]) for b in ["top", "mid", "bottom"]}
    wf.append({"train": f"{s.date()}..{(tr_end - pd.Timedelta(days=1)).date()}",
               "test": f"{tr_end.date()}..{(te_end - pd.Timedelta(days=1)).date()}",
               "train_monotonic": bool(gate),
               "test_top_mean": te["top"]["mean"], "test_n_top": te["top"]["n"],
               "test_mid_mean": te["mid"]["mean"], "test_bot_mean": te["bottom"]["mean"]})
out["walkforward"] = wf

# --- concentration: top bucket ---
topd = df[df.bucket == "top"]
by_sym = topd.groupby("symbol")["r50"].agg(["sum", "count"]).sort_values("sum", ascending=False)
out["concentration_top"] = {
    "top_symbol": by_sym.index[0], "top_symbol_sum": round(float(by_sym.iloc[0]["sum"]), 2),
    "top_symbol_share": round(float(by_sym.iloc[0]["sum"] / topd["r50"].sum()), 3) if topd["r50"].sum() != 0 else None,
    "top3_share": round(float(by_sym.head(3)["sum"].sum() / topd["r50"].sum()), 3) if topd["r50"].sum() != 0 else None,
    "n_symbols": int(by_sym.shape[0]),
}
# top-10 trades share
srt = topd.sort_values("r50", ascending=False)
out["concentration_top"]["top10_trades_share"] = round(
    float(srt.head(10)["r50"].sum() / topd["r50"].sum()), 3) if topd["r50"].sum() != 0 else None

# --- bootstrap 5000: top-bottom spread & top>0 ---
B = 5000
topx, botx = topd["r50"].to_numpy(), df[df.bucket == "bottom"]["r50"].to_numpy()
sp = np.empty(B); tp = np.empty(B)
for i in range(B):
    sp[i] = rng.choice(topx, len(topx), replace=True).mean() - rng.choice(botx, len(botx), replace=True).mean()
    tp[i] = rng.choice(topx, len(topx), replace=True).mean()
out["bootstrap"] = {
    "B": B,
    "P_spread_gt_0": round(float((sp > 0).mean()), 4),
    "P_top_gt_0": round(float((tp > 0).mean()), 4),
    "spread_ci95": [round(float(np.quantile(sp, 0.025)), 4), round(float(np.quantile(sp, 0.975)), 4)],
    "top_ci95": [round(float(np.quantile(tp, 0.025)), 4), round(float(np.quantile(tp, 0.975)), 4)],
}

# --- LOSO on top bucket ---
base_top = f["top"]["mean"]
base_spread = out["top_minus_bottom"]
loso = []
for sym, g in topd.groupby("symbol"):
    rest = topd[topd.symbol != sym]
    if len(rest) == 0:
        continue
    tm = rest["r50"].mean()
    spr = tm - df[(df.bucket == "bottom") & (df.symbol != sym)]["r50"].mean()
    loso.append({"symbol": sym, "n_removed": int(len(g)),
                 "top_mean_ex": round(float(tm), 4),
                 "spread_ex": round(float(spr), 4)})
loso = sorted(loso, key=lambda r: r["top_mean_ex"])
out["loso"] = {"base_top_mean": base_top, "base_spread": base_spread,
               "worst": loso[0], "best": loso[-1],
               "n_symbol_flips_top_sign": int(sum(1 for r in loso if (r["top_mean_ex"] > 0) != (base_top > 0))),
               "n_symbol_flips_spread_sign": int(sum(1 for r in loso if (r["spread_ex"] > 0) != (base_spread > 0)))}

json.dump(out, open(f"{DIR}/factor_results.json", "w"), indent=1)
print(json.dumps(out, indent=1)[:4000])
