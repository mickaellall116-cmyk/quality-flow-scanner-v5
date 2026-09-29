"""Diagnostic: attribute baseline signals to entry modes."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import pine_backtest as pb


def mode_flags(df, i):
    r = df.iloc[i]
    rp = df.iloc[i - 1]
    if pd.isna(r["e200"]) or pd.isna(r["atr_base"]) or pd.isna(r["adx"]):
        return (False, False, False)
    close, vol = r["Close"], r["Volume"]
    volume_ok = vol > r["vol_ma"]
    safe = not (close > r["e9"] + r["atr"] * pb.HOT_ATR)
    trend_bull = r["e21"] > r["e55"] and close > r["e200"]
    strong_trend = r["adx"] > 20 and r["atr_ratio"] > 0.85
    score = (r["e9"] > r["e21"]) + (r["e21"] > r["e55"]) + (close > r["e200"]) \
        + (r["adx"] > 25) + (r["atr_ratio"] > 1)
    breakout = close > df["High"].iloc[i - pb.BREAKOUT_BARS:i].max()
    ready_prev = rp["Close"] < rp["e21"] and rp["Close"] > rp["e55"] \
        and rp["e21"] > rp["e55"] and rp["atr_ratio"] > 0.85
    confirmed = close > r["e21"] and r["e21"] > r["e55"] and close > r["e200"] \
        and score >= 4 and volume_ok and safe
    breakout_buy = trend_bull and strong_trend and breakout and volume_ok and safe
    ready_buy = ready_prev and close > r["e21"] and score >= 3 and volume_ok and safe
    return (bool(confirmed), bool(breakout_buy), bool(ready_buy))


from collections import Counter
cnt = Counter()
sig_total = 0
for sym in pb.UNIVERSE_X:
    df = pd.read_pickle(os.path.join(pb.CACHE, f"h4_{sym}.pkl"))
    df = pb.add_pine_indicators(df)
    for i in range(pb.WARMUP, len(df)):
        c, b, rdy = mode_flags(df, i)
        if c or b or rdy:
            sig_total += 1
            key = tuple(n for n, f in zip(("C", "B", "R"), (c, b, rdy)) if f)
            cnt["+".join(key)] += 1
print("total signal bars:", sig_total)
for k, v in cnt.most_common():
    print(f"  {k}: {v}")
