"""Pine V3.6 exit-fix study — Step 3 out-of-sample validation.

Pre-specified in PINE_EXIT_FIX_SPEC.md. Validates baseline + fixA + fixB
(fixC excluded: exploratory maxDD 42.9% > 40% cap) on 2022 4H bars.

Universe: v6_short_v2/cache/d4h_2022_*.pkl (12 symbols, guaranteed) plus
pine_exit_fix/cache_2022/d4h_2022_*.pkl (best-effort extension). Coverage is
documented in the output JSON.

Rules: signals with signal_time >= 2022-01-01 only (indicators warmed on
2021-09+ headroom); trades open at data end are liquidated at the last
available close (reason "eod"), same rule for all variants.

Adoption rule (pre-specified): a fix is ADOPTED only if it beats baseline
expectancy_net_r at 4bps with max_drawdown_pct <= 40%. Otherwise: no fix.

Local-only research. No existing files modified.
"""

import glob
import json
import os
import sys
import traceback
from datetime import datetime, timezone

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))  # repo root: pine_backtest
import pine_backtest as pb
import pine_exit_fix as pf

OUT_JSON = os.path.join(HERE, "pine_exit_fix_validate.json")
CACHE_OLD = os.path.join(os.path.dirname(HERE), "v6_short_v2", "cache")
CACHE_NEW = os.path.join(HERE, "cache_2022")

MODES = ["baseline", "fixA", "fixB"]
CUTOFF = pd.Timestamp("2022-01-01", tz="UTC")


def gen_variant_trades_2022(sym, df, mode):
    trades = []
    skipped_gap = skipped_early = 0
    n = len(df)
    i = pb.WARMUP
    in_trade = False
    pos = None
    while i < n - 1:
        if not in_trade:
            if df.index[i] >= CUTOFF and pb.pine_buy_signal(df, i):
                sig = df.iloc[i]
                entry = float(df["Open"].iloc[i + 1])
                stop0 = float(sig["Close"] - sig["atr"] * pf.SL_MULT[mode])
                if entry <= stop0:
                    skipped_gap += 1
                    i += 1
                    continue
                in_trade = True
                pos = {"symbol": sym, "entry": entry, "stop": stop0,
                       "tp1": entry + float(sig["atr"]) * pb.TP_ATR,
                       "tp_hit": False, "runner": stop0, "mfe_r": 0.0,
                       "entry_idx": i + 1,
                       "entry_time": df.index[i + 1],
                       "signal_time": df.index[i].isoformat()}
                i += 1
                continue
            if df.index[i] < CUTOFF and pb.pine_buy_signal(df, i):
                skipped_early += 1
            i += 1
            continue
        done, reason, exit_px, exit_idx, exit_time = pf.manage(pos, df, i, n, mode)
        if done:
            trades.append(pf.finalize(pos, exit_px, exit_idx, exit_time, reason))
            in_trade = False
        i += 1
    if in_trade:
        # end-of-data liquidation at last close, same rule for all variants
        exit_px = float(df["Close"].iloc[-1])
        trades.append(pf.finalize(pos, exit_px, n - 1, df.index[-1], "eod"))
    return trades, skipped_gap, skipped_early


def run_variant(mode, data):
    all_trades, closes, skipped = [], {}, 0
    for sym, df in data.items():
        tr, sg, _ = gen_variant_trades_2022(sym, df, mode)
        all_trades.extend(tr)
        closes[sym] = df["Close"]
        skipped += sg
    all_trades.sort(key=lambda t: t["entry_time"])
    rows = []
    for cost_name, cost in pb.COSTS.items():
        port = pb.simulate_portfolio(all_trades, closes, cost, pb.RISK_PCT)
        rows.append(pb.summarize(f"PINE_V36_exitfix_val2022:{mode}",
                                 all_trades, port, skipped, cost_name))
    return rows


def main():
    paths = {}
    for d in (CACHE_OLD, CACHE_NEW):
        if not os.path.isdir(d):
            continue
        for p in glob.glob(os.path.join(d, "d4h_2022_*.pkl")):
            sym = os.path.basename(p)[len("d4h_2022_"):-len(".pkl")]
            if sym not in pb.UNIVERSE_X:
                print(f"  [skip] {sym}: not in UX51", flush=True)
                continue
            paths[sym] = p  # new cache wins on collision (same builder)
    print(f"found {len(paths)} 2022 symbols: {sorted(paths)}", flush=True)

    data = {}
    for sym, p in sorted(paths.items()):
        df = pd.read_pickle(p)
        if "Volume" not in df.columns or df["Volume"].isna().all():
            print(f"  [warn] no volume for {sym}, skipping", flush=True)
            continue
        data[sym] = pb.add_pine_indicators(df)
    print(f"  {len(data)} symbols ready", flush=True)
    for sym, df in data.items():
        print(f"    {sym}: {df.index[0].date()} -> {df.index[-1].date()} "
              f"({len(df)} bars)", flush=True)

    results = {"notes": [
        "OOS validation, pre-specified in PINE_EXIT_FIX_SPEC.md.",
        "Signals >= 2022-01-01 only; EOD liquidation at last close for all.",
        "fixC excluded (exploratory maxDD 42.9% > 40% cap).",
        "Adoption: beat baseline expectancy at 4bps with maxDD <= 40%, else no fix.",
    ], "symbols": sorted(data.keys()), "variants": {}}

    for mode in MODES:
        print(f"== variant {mode} ==", flush=True)
        rows = run_variant(mode, data)
        results["variants"][mode] = {"runs": rows}
        for r in rows:
            print(f"  [{r['cost']}] n={r['trades']} win={r['win_rate_pct']}% "
                  f"exp={r['expectancy_net_r']}R PF={r['profit_factor']} "
                  f"ret={r['total_return_pct']}% dd={r['max_drawdown_pct']}% "
                  f"hold={r['avg_hold_bars']} tp1={r['tp1_hit_rate_pct']}% "
                  f"reasons={r['exit_reasons']}", flush=True)
        with open(OUT_JSON, "w") as f:
            json.dump(results, f, indent=1, default=str)
        print(f"  wrote {OUT_JSON}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
