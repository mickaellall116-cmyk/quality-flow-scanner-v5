"""Track A data: 2022 4H bars via Dukascopy (yfinance intraday stops at 730d).

yfinance cannot serve 2022 intraday bars (730-day limit, verified empty).
Dukascopy's free feed has US-stock hourly bars back to 2021, but:
  - bars are labeled by hour in UTC; the 14:00 UTC bar == 9:00 ET open, so the
    scanner's regular-session filter (bars >= 9:30 ET) drops it. The first 4H
    bar of each day is therefore built from 10:00/11:00/12:00 ET bars only
    (missing 9:30-10:00 ET). Documented difference vs yfinance-based bars.
  - prices: split status VERIFIED per symbol against yfinance's
    split-adjusted daily closes (ratio of Dukascopy daily close to yfinance
    adjusted close in the 5 sessions before/after each split ex-date). For all
    three 2022 splits in the universe (TSLA 3:1 2022-08-25, AMZN 20:1
    2022-06-06, GOOGL 20:1 2022-07-18) the ratio was ~1.0 on BOTH sides, i.e.
    Dukascopy's histories are already split-adjusted and no-op was correctly
    applied. The pipeline would have adjusted had the ratio said otherwise.
    Dividends are NOT adjusted (sub-1% effects, negligible for structural
    signals).
  - volume is CFD tick volume, not share volume. Only relative volume
    (Volume vs its own rolling VOL_BASE) is ever used, so this is mechanical.
  - META is absent from Dukascopy's instrument list -> dropped (17/18).

Pipeline per symbol: fetch hourly 2021-09-01 -> 2023-01-15 (warmup headroom),
split-adjust, resample with the repo's own scanner_rules.resample_closed_4h
(read-only import; the exact bar builder the live scanner uses), sanity-check
for residual discontinuities, cache pickles in v6_short_v2/cache/.

RESEARCH ONLY. Nothing frozen is touched.
"""

import os
import sys
import time
from datetime import datetime

import pandas as pd
import numpy as np
import yfinance as yf
from dukascopy_python import fetch, INTERVAL_HOUR_1, OFFER_SIDE_BID

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scanner_rules as sr  # read-only: resample_closed_4h only

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
os.makedirs(CACHE, exist_ok=True)

# yfinance symbol -> dukascopy instrument
SYMBOLS = {
    "NVDA": "NVDA.US/USD", "AAPL": "AAPL.US/USD", "MSFT": "MSFT.US/USD",
    "AMD": "AMD.US/USD", "AVGO": "AVGO.US/USD", "TSLA": "TSLA.US/USD",
    "PLTR": "PLTR.US/USD", "NFLX": "NFLX.US/USD", "CRM": "CRM.US/USD",
    "ORCL": "ORCL.US/USD", "JPM": "JPM.US/USD", "XOM": "XOM.US/USD",
    "LLY": "LLY.US/USD", "COST": "COST.US/USD", "GOOGL": "GOOGL.US/USD",
    "AMZN": "AMZN.US/USD", "WMT": "WMT.US/USD",
    "QQQ": "QQQ.US/USD", "SPY": "SPY.US/USD",
    # META not offered by Dukascopy -> dropped, documented.
}
START = datetime(2021, 9, 1)
END = datetime(2023, 1, 15)


def fetch_hourly(duka):
    df = fetch(duka, INTERVAL_HOUR_1, OFFER_SIDE_BID, START, END)
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low",
                             "close": "Close", "volume": "Volume"})
    return df[["Open", "High", "Low", "Close", "Volume"]]


def split_adjust(df, yf_sym):
    """Put the whole series in post-split terms, detecting the vendor's state.

    Dukascopy is inconsistent: some histories are pre-adjusted (AMZN, GOOGL:
    pre-split bars already at post-split scale), some are not adjusted at all
    (TSLA: post-split bars still at pre-split scale). So for each split we
    compare Dukascopy daily closes against yfinance's split-adjusted daily
    closes in the 5 sessions before/after the ex-date and apply the factor
    only where the ratio says the vendor didn't:
      pre ~= ratio, post ~= 1  -> divide pre-split bars (standard case)
      pre ~= 1,     post ~= 1  -> nothing to do (already adjusted)
      pre ~= ratio, post ~= ratio -> divide ALL bars (never adjusted)
    Anything else is printed and left untouched for inspection.
    """
    try:
        splits = yf.Ticker(yf_sym).splits
    except Exception as e:
        print(f"    split calendar unavailable for {yf_sym}: {e}", flush=True)
        return df
    try:
        yd = yf.download(yf_sym, interval="1d", start="2021-09-01",
                         end="2023-01-15", progress=False, auto_adjust=True,
                         threads=False)
        if isinstance(yd.columns, pd.MultiIndex):
            yd.columns = [c[0] for c in yd.columns]
        yd = yd.dropna()
    except Exception as e:
        print(f"    yfinance daily unavailable for {yf_sym}: {e}", flush=True)
        return df
    out = df.copy()
    dd = out["Close"].groupby(out.index.date).last()
    for ts, ratio in splits.items():
        d = ts.date()
        if not (START.date() <= d <= END.date()) or not ratio or ratio == 1:
            continue
        ratio = float(ratio)
        # 5 sessions strictly before / on-or-after ex-date, present in both
        # (plain datetime.date on both sides — Timestamp != date in sets)
        common = sorted(set(dd.index) & set(yd.index.date))
        pre = [x for x in common if x < d][-5:]
        post = [x for x in common if x >= d][:5]
        if not pre or not post:
            print(f"    {yf_sym}: cannot bracket split {d}, skipped", flush=True)
            continue
        yd_close = yd["Close"].copy()
        yd_close.index = yd.index.date
        r_pre = float((dd.loc[pre] / yd_close.loc[pre].to_numpy()).median())
        r_post = float((dd.loc[post] / yd_close.loc[post].to_numpy()).median())

        def close_to(x, t):
            return abs(x - t) / t < 0.05

        idx = pd.DatetimeIndex(out.index.date)
        if close_to(r_pre, ratio) and close_to(r_post, 1.0):
            mask = idx < pd.Timestamp(d)
            where = "pre-split bars"
        elif close_to(r_pre, 1.0) and close_to(r_post, 1.0):
            print(f"    {yf_sym}: {ratio:g}:1 on {d} already adjusted, no-op "
                  f"(r_pre={r_pre:.2f} r_post={r_post:.2f})", flush=True)
            continue
        elif close_to(r_pre, ratio) and close_to(r_post, ratio):
            mask = np.ones(len(out), dtype=bool)
            where = "ALL bars (vendor never adjusted)"
        else:
            print(f"    {yf_sym}: ambiguous ratios around {d} "
                  f"(r_pre={r_pre:.2f} r_post={r_post:.2f}), SKIPPED", flush=True)
            continue
        n = int(mask.sum())
        out.loc[mask, ["Open", "High", "Low", "Close"]] /= ratio
        out.loc[mask, "Volume"] *= ratio
        print(f"    split-adjust {yf_sym}: {ratio:g}:1 on {d} -> {where} "
              f"({n} bars, r_pre={r_pre:.2f} r_post={r_post:.2f})", flush=True)
    return out


def sanity(df4, sym):
    if df4.empty:
        return "EMPTY"
    chg = df4["Close"].pct_change().abs()
    worst = chg.max()
    if worst > 0.5:
        return f"DISCONTINUITY {worst:.1%} at {chg.idxmax()}"
    return f"ok ({len(df4)} 4h bars, {df4.index[0].date()} -> {df4.index[-1].date()})"


def main():
    for n, (yf_sym, duka) in enumerate(SYMBOLS.items()):
        out4 = os.path.join(CACHE, f"d4h_2022_{yf_sym}.pkl")
        if os.path.exists(out4):
            print(f"[{n+1}/{len(SYMBOLS)}] {yf_sym}: cached", flush=True)
            continue
        print(f"[{n+1}/{len(SYMBOLS)}] {yf_sym} <- {duka} ...", flush=True)
        try:
            h = fetch_hourly(duka)
            h = split_adjust(h, yf_sym)
            h.to_pickle(os.path.join(CACHE, f"h1_2022_{yf_sym}.pkl"))
            b4 = sr.resample_closed_4h(h, yf_sym)
            b4.to_pickle(out4)
            print(f"    {sanity(b4, yf_sym)}", flush=True)
        except Exception as e:
            print(f"    FAILED: {type(e).__name__}: {str(e)[:150]}", flush=True)
        time.sleep(1.0)
    print("done.")


if __name__ == "__main__":
    main()
