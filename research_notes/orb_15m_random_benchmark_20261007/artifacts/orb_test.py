#!/usr/bin/env python3
"""
15-minute Opening Range Breakout (ORB) vs 1,000 random-entry benchmark.
Research only. Standalone — touches no frozen strategy code.

Strategy (from Quant Lab video transcript):
  1. Range = high/low of first 15m bar of regular session (09:30-09:45 ET).
  2. Entry: first 15m candle that CLOSES outside the range.
  3. Stop: other side of the range.
  4. Target: 2x risk.  One trade/day max. Stop wins same-bar ties (conservative).
  5. EOD exit at last regular-session bar close if neither hit (not in video; required).

Random benchmark: same risk unit (that day's ORB range width), same 2R target,
random entry bar + random direction per day, 1,000 variants.
"""
import json
import numpy as np
import pandas as pd

COST_BPS_PER_SIDE = 1.0   # 1bp per side
N_RANDOM = 1000
SEED = 42

def load_symbol(early_path, late_path):
    bars = json.load(open(early_path))["bars"] + json.load(open(late_path))["bars"]
    df = pd.DataFrame(bars)
    df["ts_utc"] = pd.to_datetime(df["date"], utc=True)
    df["ts_et"] = df["ts_utc"].dt.tz_convert("America/New_York")
    df = df.sort_values("ts_utc").drop_duplicates("ts_utc").reset_index(drop=True)
    # regular session only: bar start >= 09:30 and bar start < 16:00 ET
    t = df["ts_et"].dt.time
    df = df[(t >= pd.Timestamp("09:30").time()) & (t < pd.Timestamp("16:00").time())].copy()
    df["day"] = df["ts_et"].dt.date
    return df[["day", "ts_et", "open", "high", "low", "close"]].reset_index(drop=True)


def simulate_trade(bars, entry_idx, direction, risk, cost_bps):
    """
    bars: DataFrame of the day's 15m bars (regular session).
    entry_idx: index into bars of the entry bar; entry at that bar's close.
    direction: +1 long, -1 short.  risk: $ risk unit (range width).
    Returns R multiple of the trade (after costs if cost_bps>0).
    """
    entry_px = bars["close"].iloc[entry_idx]
    if direction == 1:
        stop, target = entry_px - risk, entry_px + 2 * risk
    else:
        stop, target = entry_px + risk, entry_px - 2 * risk
    exit_px, hit = None, "eod"
    for j in range(entry_idx + 1, len(bars)):
        lo, hi = bars["low"].iloc[j], bars["high"].iloc[j]
        s_hit = (lo <= stop) if direction == 1 else (hi >= stop)
        t_hit = (hi >= target) if direction == 1 else (lo <= target)
        if s_hit and t_hit:
            exit_px, hit = stop, "stop"          # conservative: stop wins ties
            break
        if s_hit:
            exit_px, hit = stop, "stop"
            break
        if t_hit:
            exit_px, hit = target, "target"
            break
    if exit_px is None:
        exit_px, hit = bars["close"].iloc[-1], "eod"
    gross = direction * (exit_px - entry_px) / risk
    cost_r = 2 * (cost_bps / 1e4) * entry_px / risk   # in/out, as fraction of risk
    return gross - cost_r, hit


def orb_day(bars, cost_bps):
    """Run the ORB rule on one day's bars. Returns (R, hit, direction) or None."""
    if len(bars) < 2:
        return None
    r0 = bars.iloc[0]
    rng_hi, rng_lo = r0["high"], r0["low"]
    risk = rng_hi - rng_lo
    if risk <= 0:
        return None
    for i in range(1, len(bars)):
        c = bars["close"].iloc[i]
        if c > rng_hi:
            r, hit = simulate_trade(bars, i, +1, risk, cost_bps)
            return r, hit, +1
        if c < rng_lo:
            r, hit = simulate_trade(bars, i, -1, risk, cost_bps)
            return r, hit, -1
    return None  # no breakout -> no trade


def run_orb(df, cost_bps):
    rs, hits, dirs, days = [], [], [], []
    for day, bars in df.groupby("day", sort=True):
        bars = bars.reset_index(drop=True)
        # bar 0 must be the 09:30 bar; skip day if missing
        if bars["ts_et"].iloc[0].time() != pd.Timestamp("09:30").time():
            continue
        out = orb_day(bars, cost_bps)
        if out:
            r, hit, d = out
            rs.append(r); hits.append(hit); dirs.append(d); days.append(day)
    return pd.DataFrame({"day": days, "R": rs, "hit": hits, "dir": dirs})


def run_random(df, cost_bps, seed):
    """
    Vectorized random-entry benchmark.
    Per day: entry bar uniform over bars[1:], direction uniform {+1,-1},
    risk = that day's ORB range width. Returns (n_days, N_RANDOM) R matrix.
    """
    rng = np.random.default_rng(seed)
    day_list = []
    for day, bars in df.groupby("day", sort=True):
        bars = bars.reset_index(drop=True)
        if bars["ts_et"].iloc[0].time() != pd.Timestamp("09:30").time():
            continue
        r0 = bars.iloc[0]
        risk = r0["high"] - r0["low"]
        if risk <= 0 or len(bars) < 3:
            continue
        day_list.append((day, bars, risk))
    n_days = len(day_list)
    R = np.zeros((n_days, N_RANDOM))
    for di, (day, bars, risk) in enumerate(day_list):
        n = len(bars)
        o = bars["open"].to_numpy(); h = bars["high"].to_numpy()
        l = bars["low"].to_numpy(); c = bars["close"].to_numpy()
        ei = rng.integers(1, n, size=N_RANDOM)          # entry bar in [1, n)
        d = rng.choice([-1, 1], size=N_RANDOM)          # direction
        ep = c[ei]
        stop = np.where(d == 1, ep - risk, ep + risk)
        tgt = np.where(d == 1, ep + 2 * risk, ep - 2 * risk)
        # outcome per variant: scan bars after entry
        # build (n, N) boolean hit matrices via broadcasting
        idx = np.arange(n)[:, None]
        after = idx > ei[None, :]
        s_hit = np.where(d[None, :] == 1, l[:, None] <= stop[None, :],
                         h[:, None] >= stop[None, :]) & after
        t_hit = np.where(d[None, :] == 1, h[:, None] >= tgt[None, :],
                         l[:, None] <= tgt[None, :]) & after
        # first bar index where either hit; stop wins ties
        any_hit = s_hit | t_hit
        has = any_hit.any(axis=0)
        first = np.where(has, any_hit.argmax(axis=0), n - 1)
        # exit price: stop if stop-hit at first bar else target (tie->stop), else EOD close
        fb = first
        sh = s_hit[fb, np.arange(N_RANDOM)]
        exit_px = np.where(has, np.where(sh, stop, tgt), c[-1])
        gross = d * (exit_px - ep) / risk
        cost_r = 2 * (cost_bps / 1e4) * ep / risk
        R[di, :] = gross - cost_r
    return R, [d for d, _, _ in day_list]


def stats(rs):
    rs = np.asarray(rs, float)
    cum = np.cumsum(rs)
    dd = np.maximum.accumulate(cum) - cum
    wins = rs[rs > 0]; losses = rs[rs <= 0]
    return {
        "n": len(rs), "total_R": float(rs.sum()),
        "win_rate": float((rs > 0).mean()) if len(rs) else 0.0,
        "avg_win": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss": float(losses.mean()) if len(losses) else 0.0,
        "max_dd_R": float(dd.max()) if len(dd) else 0.0,
    }


def main():
    out_lines = []
    def log(s=""):
        print(s); out_lines.append(s)

    for sym, ep_, lp in [("QQQ", "/tmp/qqq_15m_early.json", "/tmp/qqq_15m.json"),
                        ("SPY", "/tmp/spy_15m_early.json", "/tmp/spy_15m_late.json")]:
        log(f"===== {sym} =====")
        df = load_symbol(ep_, lp)
        log(f"bars={len(df)} days={df['day'].nunique()} "
            f"range={df['day'].min()}..{df['day'].max()}")
        for cost, clabel in [(0.0, "zero-cost"), (COST_BPS_PER_SIDE, "1bp/side")]:
            orb = run_orb(df, cost)
            Rmat, days = run_random(df, cost, SEED)
            # Benchmark B (primary): random restricted to ORB's trading days
            orb_days = set(orb["day"])
            keep = [i for i, d in enumerate(days) if d in orb_days]
            Rmat_b = Rmat[keep, :]
            orb = orb[orb["day"].isin(orb_days)].sort_values("day").reset_index(drop=True)
            assert len(orb) == Rmat_b.shape[0], (len(orb), Rmat_b.shape)
            o = stats(orb["R"].to_numpy())
            rand_b = Rmat_b.sum(axis=0)
            pct_b = float((rand_b < o["total_R"]).mean() * 100)
            # Benchmark A (secondary): random on every valid day
            rand_a = Rmat.sum(axis=0)
            pct_a = float((rand_a < o["total_R"]).mean() * 100)
            log(f"--- {clabel} ---")
            log(f"ORB: n={o['n']} total={o['total_R']:.1f}R win={o['win_rate']:.1%} "
                f"avgW={o['avg_win']:.2f}R avgL={o['avg_loss']:.2f}R maxDD={o['max_dd_R']:.1f}R")
            log(f"RANDOM-matched-days(n={N_RANDOM}): mean={rand_b.mean():.1f}R "
                f"median={np.median(rand_b):.1f}R std={rand_b.std():.1f}R "
                f"p5={np.percentile(rand_b,5):.1f}R p95={np.percentile(rand_b,95):.1f}R")
            log(f"ORB percentile vs random-matched: {pct_b:.1f}%")
            log(f"RANDOM-all-days(n={N_RANDOM}): mean={rand_a.mean():.1f}R "
                f"median={np.median(rand_a):.1f}R "
                f"-> ORB percentile vs random-all-days: {pct_a:.1f}%")
            # per-year
            orb["yr"] = pd.to_datetime(orb["day"]).dt.year
            for yr, g in orb.groupby("yr"):
                log(f"  {yr}: n={len(g)} total={g['R'].sum():.1f}R")
        log("")
    open("/tmp/orb_report.txt", "w").write("\n".join(out_lines))


if __name__ == "__main__":
    main()
