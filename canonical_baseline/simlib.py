"""Shared library for the canonical-baseline portfolio rebuild (worker d).

Read-only use of frozen modules: masterscanner_api, scanner_rules,
v54_rules, v54_engine (imported, never modified), modeb_engine (worker b),
pine_backtest (imported unmodified for the V0 sanity anchor).

PIT contract (canonical_baseline/PIT_FEATURES.md) is obeyed throughout:
- signals evaluated on completed 4H bars only, entry filled at next bar open
- indicator math causal (verified: add_indicators is fully causal, so a
  full-series computation read at row i == slice computation at row i)
- no daily data newer than signal-bar close (RS/regime endpoints)
- America/New_York everywhere
"""

import json
import os
import sys

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(REPO, "canonical_baseline")
DATA = os.path.join(BASE, "data")
sys.path.insert(0, REPO)
sys.path.insert(0, BASE)

import masterscanner_api as m53          # noqa: E402  (frozen, read-only)
import scanner_rules as sr               # noqa: E402  (frozen, read-only)
import v54_rules                         # noqa: E402  (frozen, read-only)
import v54_engine                        # noqa: E402  (frozen, read-only)
import modeb_engine                      # noqa: E402  (worker b, read-only)

# The frozen engine's own minimum-bars gate (v54_engine.v54_classify).
WARMUP_BARS = int(max(m53.TREND_EMA, m53.ATR_BASE_LEN,
                      m53.VOL_BASE_LEN, m53.VWAP_LEN) + 5)  # = 205

_H4_CACHE = {}
_D1_CACHE = {}


def load_h4(symbol):
    if symbol not in _H4_CACHE:
        df = pd.read_pickle(os.path.join(DATA, f"h4_{symbol}.pkl"))
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        _H4_CACHE[symbol] = df
    return _H4_CACHE[symbol]


def load_d1(symbol):
    if symbol not in _D1_CACHE:
        df = pd.read_pickle(os.path.join(DATA, f"d1_{symbol}.pkl"))
        _D1_CACHE[symbol] = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    return _D1_CACHE[symbol]


def load_universe():
    with open(os.path.join(BASE, "universe.json")) as fh:
        return json.load(fh)


def load_overlay14():
    with open(os.path.join(BASE, "universe_overlay_14.json")) as fh:
        return json.load(fh)


def load_coverage():
    with open(os.path.join(BASE, "coverage_report.json")) as fh:
        cov = json.load(fh)
    return {s["symbol"]: s for s in cov["symbols"]}


def signal_window(symbol, universe_entry, coverage_entry):
    """(start_ts, end_ts) of the eligible signal window for one symbol.

    Per UNIVERSE.md: backtests use max(eligible_from, effective_4h_from).
    """
    start = max(str(universe_entry.get("eligible_from", "2023-10-01")),
                str(coverage_entry.get("effective_4h_from", "2023-10-26")))
    end = str(universe_entry.get("eligible_to", "2026-09-30"))
    tz = "America/New_York"
    return (pd.Timestamp(start, tz=tz),
            pd.Timestamp(end, tz=tz) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1))


# ---------------------------------------------------------------------------
# V5.4 signal generation: vectorized prefilter + exact scalar pass
# ---------------------------------------------------------------------------

def _v54_scalar_eligible(dfi, i):
    """Exact replication of v54_engine.v54_classify's eligibility path at bar i.

    Uses the REAL frozen functions wherever possible
    (v54_engine._pure_setup_triggers, v54_rules.v54_hard_gates_pass,
    sr.trade_levels). Returns (eligible, record_fields).
    """
    last, prev = dfi.iloc[i], dfi.iloc[i - 1]
    price = float(last["Close"])
    e9 = float(last["EMA9"])
    e21 = float(last["EMA21"])
    e55 = float(last["EMA55"])
    e200 = float(last["EMA200"])
    adx = float(last["ADX"]) if not pd.isna(last["ADX"]) else 0.0
    atrv = float(last["ATR"]) if not pd.isna(last["ATR"]) else 0.0
    vwap = float(last["VWAP"]) if not pd.isna(last["VWAP"]) else float("nan")
    above_vwap = bool(price > vwap) if not pd.isna(vwap) else False

    zone_low = max(0.0, e21 - atrv * m53.BUY_ZONE_ATR_WIDTH)
    zone_high = e21 + atrv * m53.BUY_ZONE_ATR_WIDTH
    in_zone = zone_low <= price <= zone_high
    stop, tp1 = sr.trade_levels(zone_low, zone_high, atrv)

    trig = v54_engine._pure_setup_triggers(
        last, prev, price, e9, e21, e55, e200, adx, above_vwap)

    # --- protection / state / entry: verbatim from v54_classify ---
    extension = m53.safe_pct(price, e21)
    hot = (trig["trend_bull"] and trig["ema_bull"]
           and adx >= m53.HOT_ADX and extension >= m53.HOT_EXTENSION_PCT)
    if trig["exit_signal"]:
        protection = "EXIT"
    elif hot or extension >= m53.HOT_EXTENSION_PCT:
        protection = "LOCK GAINS"
    elif trig["trend_bull"] and trig["ema_bull"] and price >= e21 and above_vwap:
        protection = "SAFE"
    elif trig["trend_bull"] and price < e21 and price > e55:
        protection = "WARNING"
    else:
        protection = "WARNING"

    if trig["exit_signal"]:
        state = "EXIT"
    elif trig["fresh_buy"]:
        state = "BUY"
    elif trig["pullback_buy"]:
        state = "PULLBACK BUY"
    elif trig["early_buy"]:
        state = "EARLY BUY"
    else:
        state = "NEUTRAL"

    entry = "YES" if (
        state in ("BUY", "PULLBACK BUY")
        and protection == "SAFE"
        and above_vwap
        and in_zone
    ) else "NO"
    # --- end verbatim ---

    row = {
        "entry": entry, "protection": protection, "state": state,
        "above_vwap": above_vwap,
        "buy_zone": f"{zone_low:.2f}-{zone_high:.2f}",
        "price": price, "adx": adx,
    }
    eligible, reasons = v54_rules.v54_hard_gates_pass(row)
    fields = {
        "price": price, "stop": float(stop), "tp1": float(tp1),
        "state": state, "protection": protection, "adx": adx,
        "atr": atrv, "ema21": e21, "ema55": e55, "ema200": e200,
    }
    return eligible, fields


def v54_signals(symbol, win_start, win_end):
    """All v54-eligible signals for one symbol.

    dfi computed once on the full causal series (verified identical to
    per-slice computation). Signals evaluated at bars i with
    WARMUP_BARS <= i < n-1 inside [win_start, win_end]; entry fills at
    next bar's open; skipped when entry <= stop or no next bar.
    """
    df = load_h4(symbol)
    n = len(df)
    if n < WARMUP_BARS + 2:
        return [], df
    dfi = m53.add_indicators(df)

    close = dfi["Close"].to_numpy()
    e9 = dfi["EMA9"].to_numpy()
    e21 = dfi["EMA21"].to_numpy()
    e55 = dfi["EMA55"].to_numpy()
    e200 = dfi["EMA200"].to_numpy()
    adx = dfi["ADX"].to_numpy()
    atrv = dfi["ATR"].to_numpy()
    vw = dfi["VWAP"].to_numpy()

    # --- vector prefilter (exact boolean mirror of the scalar path) ---
    price = close
    above_vwap = (price > vw) & ~np.isnan(vw)
    zl = np.maximum(0.0, e21 - atrv * m53.BUY_ZONE_ATR_WIDTH)
    zh = e21 + atrv * m53.BUY_ZONE_ATR_WIDTH
    in_zone = (zl <= price) & (price <= zh)

    e21p, e55p = np.roll(e21, 1), np.roll(e55, 1)
    trend_bull = price > e200
    ema_bull = e21 > e55
    accel_bull = e9 > e21
    fast_rising = e21 > e21p
    accel_rising = e9 > np.roll(e9, 1)
    fresh_buy = (e21 > e55) & (e21p <= e55p) & trend_bull
    early_buy = (trend_bull & accel_bull & fast_rising & accel_rising
                 & (price > e21) & (e21 <= e55 * 1.015))
    ext = np.where(e21 != 0, (price - e21) / e21 * 100.0, 0.0)
    pullback_buy = (trend_bull & ema_bull & (price >= e21)
                    & (np.abs(ext) <= m53.PULLBACK_NEAR_EMA_PCT) & (adx >= m53.ADX_MIN))
    exit_signal = (price < e55) | ((e21 < e55) & (e21p >= e55p))
    hot = trend_bull & ema_bull & (adx >= m53.HOT_ADX) & (ext >= m53.HOT_EXTENSION_PCT)

    protection = np.full(n, "WARNING", dtype=object)
    protection[exit_signal] = "EXIT"
    lg = (~exit_signal) & (hot | (ext >= m53.HOT_EXTENSION_PCT))
    protection[lg] = "LOCK GAINS"
    safe_m = (~exit_signal) & (~lg) & trend_bull & ema_bull & (price >= e21) & above_vwap
    protection[safe_m] = "SAFE"

    state = np.full(n, "NEUTRAL", dtype=object)
    state[exit_signal] = "EXIT"
    m = ~exit_signal
    state[m & fresh_buy] = "BUY"
    state[m & ~fresh_buy & pullback_buy] = "PULLBACK BUY"
    state[m & ~fresh_buy & ~pullback_buy & early_buy] = "EARLY BUY"

    entry_yes = (((state == "BUY") | (state == "PULLBACK BUY"))
                 & (protection == "SAFE") & above_vwap & in_zone)
    cand = entry_yes & (adx >= v54_rules.MIN_ADX)

    idx = df.index
    sigs = []
    skipped_nobar = 0
    skipped_gap = 0
    for i in np.flatnonzero(cand):
        if i < WARMUP_BARS or i >= n - 1:
            continue
        ts = idx[i]
        if not (win_start <= ts <= win_end):
            continue
        eligible, f = _v54_scalar_eligible(dfi, i)
        if not eligible:
            continue  # vector/scalar disagree -> trust the exact scalar path
        entry_px = float(df["Open"].iloc[i + 1])
        if entry_px <= f["stop"]:
            skipped_gap += 1
            continue
        bar_close = sr.bar_close_at(ts, symbol)
        sigs.append({
            "signal_id": f"v54:{symbol}:4h:{bar_close.isoformat()}:{v54_rules.V54_RULE_VERSION}",
            "symbol": symbol,
            "signal_bar_idx": int(i),
            "signal_bar_start_at": ts.isoformat(),
            "signal_bar_close_at": bar_close.isoformat(),
            "entry_bar_idx": int(i + 1),
            "entry_bar_ts": idx[i + 1].isoformat(),
            "entry": entry_px,
            "stop": f["stop"],
            "tp1": f["tp1"],
            "signal_close": f["price"],
            "adx": f["adx"],
            "atr": f["atr"],
        })
    return sigs, df


def verify_v54_replication(symbols, n_each=4, seed=7):
    """Spot-check the vectorized+scalar replication against real v54_classify.

    Calls the frozen v54_engine.v54_classify on df slices (read-only) and
    compares v54_eligible. Returns (checked, mismatches).
    """
    rng = np.random.default_rng(seed)
    checked = mismatches = 0
    for sym in symbols:
        df = load_h4(sym)
        n = len(df)
        if n < WARMUP_BARS + 2:
            continue
        dfi = m53.add_indicators(df)
        cand_idx = None
        for trial in range(n_each * 6):
            i = int(rng.integers(WARMUP_BARS, n - 1))
            row = v54_engine.v54_classify(
                sym, "Verify", df.iloc[:i + 1], None, {}, "4h")
            if row is None:
                continue
            mine_elig, _ = _v54_scalar_eligible(dfi, i)
            checked += 1
            if bool(row.get("v54_eligible")) != bool(mine_elig):
                mismatches += 1
                print(f"MISMATCH {sym} bar {i}: engine={row.get('v54_eligible')} mine={mine_elig}")
            if checked >= n_each * len(symbols):
                break
    return checked, mismatches


def exit_states_vector(symbol):
    """Per-bar V5.3 EXIT scanner state ('EXIT'/None), causal.

    v53_state_for_bar's EXIT == pure price-structure exit_signal
    (masterscanner_api.classify_symbol: price<e55 or EMA21/55 bear cross),
    which takes priority over every score-gated state. Computed on the
    causal indicator frame.
    """
    df = load_h4(symbol)
    dfi = m53.add_indicators(df)
    e21 = dfi["EMA21"].to_numpy()
    e55 = dfi["EMA55"].to_numpy()
    close = dfi["Close"].to_numpy()
    e21p, e55p = np.roll(e21, 1), np.roll(e55, 1)
    xs = (close < e55) | ((e21 < e55) & (e21p >= e55p))
    xs[0] = False
    return ["EXIT" if b else None for b in xs]


# ---------------------------------------------------------------------------
# V3.6 Hybrid signals (old system; pine_backtest imported unmodified for V0)
# ---------------------------------------------------------------------------

def v36_signal_mask(symbol):
    """Vectorized pine_backtest.pine_buy_signal over all bars (verified)."""
    sys.path.insert(0, REPO)
    import pine_backtest as pb  # noqa: E402  (frozen, read-only)
    df = load_h4(symbol)
    d = pb.add_pine_indicators(df)
    c = d["Close"].to_numpy()
    e9, e21, e55, e200 = (d["e9"].to_numpy(), d["e21"].to_numpy(),
                          d["e55"].to_numpy(), d["e200"].to_numpy())
    atr, adx = d["atr"].to_numpy(), d["adx"].to_numpy()
    atr_ratio = d["atr_ratio"].to_numpy()
    vol, vol_ma = d["Volume"].to_numpy(), d["vol_ma"].to_numpy()
    hi = d["High"].to_numpy()
    ok = ~(np.isnan(e200) | np.isnan(d["atr_base"].to_numpy()) | np.isnan(adx))
    volume_ok = vol > vol_ma
    hot = c > e9 + atr * pb.HOT_ATR
    safe = ~hot
    trend_bull = (e21 > e55) & (c > e200)
    strong_trend = (adx > 20) & (atr_ratio > 0.85)
    score = ((e9 > e21).astype(int) + (e21 > e55).astype(int)
             + (c > e200).astype(int) + (adx > 25).astype(int)
             + (atr_ratio > 1).astype(int))
    breakout = c > pd.Series(hi).shift(1).rolling(pb.BREAKOUT_BARS).max().to_numpy()
    cp, e21p, e55p, arp = np.roll(c, 1), np.roll(e21, 1), np.roll(e55, 1), np.roll(atr_ratio, 1)
    ready_prev = (cp < e21p) & (cp > e55p) & (e21p > e55p) & (arp > 0.85)
    ready_prev[0] = False
    confirmed = (c > e21) & (e21 > e55) & (c > e200) & (score >= 4) & volume_ok & safe
    breakout_buy = trend_bull & strong_trend & breakout & volume_ok & safe
    ready_buy = ready_prev & (c > e21) & (score >= 3) & volume_ok & safe
    sig = (confirmed | breakout_buy | ready_buy) & ok
    sig[:max(pb.WARMUP, 1)] = False
    return sig, d


def verify_v36_replication(symbols, n_each=60, seed=11):
    """Spot-check vectorized pine_buy_signal vs the real scalar function."""
    import pine_backtest as pb
    rng = np.random.default_rng(seed)
    checked = mismatches = 0
    for sym in symbols:
        df = load_h4(sym)
        d = pb.add_pine_indicators(df)
        mask, _ = v36_signal_mask(sym)
        n = len(d)
        for _ in range(n_each):
            i = int(rng.integers(pb.WARMUP, n - 1))
            mine = bool(mask[i])
            theirs = bool(pb.pine_buy_signal(d, i))
            checked += 1
            if mine != theirs:
                mismatches += 1
                print(f"V36 MISMATCH {sym} bar {i}: vec={mine} scalar={theirs}")
    return checked, mismatches


# ---------------------------------------------------------------------------
# RS / benchmark helpers (strict PIT per the contract)
# ---------------------------------------------------------------------------

def bench_ret_daily(closes, t0, t1):
    """SPY-daily return over [t0, t1] using last completed daily bar <= each
    timestamp (right-1 searchsorted). None if unavailable. Mirrors
    pine_signal_quality.bench_ret."""
    idx = closes.index
    j1 = idx.searchsorted(t1, side="right") - 1
    j0 = idx.searchsorted(t0, side="right") - 1
    if j1 < 0 or j0 < 0 or j1 <= j0:
        return None
    c1, c0 = float(closes.iloc[j1]), float(closes.iloc[j0])
    if c0 <= 0 or np.isnan(c0) or np.isnan(c1):
        return None
    return c1 / c0 - 1.0


def rs_top2_scores(signals_by_symbol):
    """rs = 20-bar 4H return minus SPY return over the same calendar span.

    Symbol leg: Close[i]/Close[i-20] on 4H bars. SPY leg: bench_ret on SPY
    daily with strict PIT endpoints (last completed daily bar <= t).
    Returns dict signal_id -> rs (float; -inf when unrankable).
    """
    spy = load_d1("SPY")["Close"]
    out = {}
    for sym, sigs in signals_by_symbol.items():
        df = load_h4(sym)
        closes = df["Close"]
        for s in sigs:
            i = s["signal_bar_idx"]
            if i < m53.RS_LOOKBACK:
                out[s["signal_id"]] = float("-inf")
                continue
            sym_ret = float(closes.iloc[i] / closes.iloc[i - m53.RS_LOOKBACK] - 1.0)
            t1 = df.index[i].tz_convert("UTC")
            t0 = df.index[i - m53.RS_LOOKBACK].tz_convert("UTC")
            br = bench_ret_daily(spy, t0, t1)
            out[s["signal_id"]] = float(sym_ret - br) if br is not None else float("-inf")
    return out


# ---------------------------------------------------------------------------
# Regime (prior-study definition, strict PIT join)
# ---------------------------------------------------------------------------

def build_regime():
    """Bull/bear/sideways tri-state from SPY daily (pine_regime_backtest).

    bull = close>e200 & e200 rising (vs 20 bars ago); bear = close<e200 &
    e200 falling; else sideways. Joined at the last completed daily bar <=
    signal-bar close (PIT contract rule 2).
    """
    spy = load_d1("SPY")["Close"]
    e200 = spy.ewm(span=200, adjust=False).mean()
    reg = pd.DataFrame(index=spy.index)
    reg["above"] = spy > e200
    reg["rising"] = e200 > e200.shift(20)
    reg["tri"] = np.where(reg["above"] & reg["rising"], "bull",
                  np.where(~reg["above"] & ~reg["rising"], "bear", "sideways"))
    return reg[["tri"]]


def regime_at(reg, ts):
    """Regime label as of timestamp ts (last completed daily bar <= ts)."""
    idx = reg.index
    j = idx.searchsorted(ts, side="right") - 1
    if j < 0:
        return "unknown"
    return str(reg["tri"].iloc[j])


# ---------------------------------------------------------------------------
# Trade statistics
# ---------------------------------------------------------------------------

def expectancy(rs):
    rs = np.asarray(rs, dtype=float)
    return float(np.mean(rs)) if len(rs) else 0.0


def profit_factor(rs):
    rs = np.asarray(rs, dtype=float)
    gw = rs[rs > 0].sum()
    gl = -rs[rs <= 0].sum()
    if gl <= 0:
        return float("inf") if gw > 0 else 0.0
    return float(gw / gl)


def win_rate(rs):
    rs = np.asarray(rs, dtype=float)
    return float((rs > 0).mean()) if len(rs) else 0.0


def max_drawdown(equity):
    eq = np.asarray(equity, dtype=float)
    if len(eq) == 0:
        return 0.0
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / peak
    return float(dd.min())


def max_losing_streak(rs):
    rs = np.asarray(rs, dtype=float)
    best = cur = 0
    for r in rs:
        if r <= 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def year_bucket(ts):
    ts = pd.Timestamp(ts)
    y = ts.year
    if y == 2023:
        return "2023-partial"
    if y == 2026:
        return "2026-YTD"
    return str(y)


def overlap_episodes(trades):
    """Cluster trades into time-connected market episodes.

    Nodes = trades; edge = holding periods overlap (entry_ts <= other exit
    and vice versa). Connected components = episodes (per
    research_audit/independence/REPORT.md). Returns (n_episodes, sizes,
    assignment dict trade_idx -> episode_id).
    """
    n = len(trades)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    starts = [pd.Timestamp(t["entry_ts"]) for t in trades]
    ends = [pd.Timestamp(t["exit_ts"]) for t in trades]
    order = sorted(range(n), key=lambda k: starts[k])
    # sweep line over sorted starts
    import heapq
    active = []  # (end, idx)
    for k in order:
        s = starts[k]
        while active and active[0][0] < s:
            heapq.heappop(active)
        for _, j in active:
            union(k, j)
        heapq.heappush(active, (ends[k], k))
    comp = {}
    assign = {}
    for k in range(n):
        r = find(k)
        comp.setdefault(r, []).append(k)
        assign[k] = r
    sizes = sorted((len(v) for v in comp.values()), reverse=True)
    return len(comp), sizes, assign
