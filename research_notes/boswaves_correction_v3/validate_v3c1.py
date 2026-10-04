"""BOSWaves v3 robustness validation — frozen protocol implementation.

Implements boswaves_validation_protocol_v3_20261003.md EXACTLY.
STEP 0 (hashes) is done by the driver before import; this module only runs.
"""
import json, os, sys, math, hashlib
import numpy as np
from datetime import date

sys.path.insert(0, "/home/hatch/workspace/research/boswaves")
from boswaves_ind import compute_boswaves, position_plan
from backtest import backtest_symbol  # published engine, unmodified (source parity)

EOD = "/home/hatch/workspace/goals/vcp-fundamental-momentum-probe-v0-1/hidden_files/phase1a/raw/eod"
OUTDIR = "/home/hatch/workspace/research/boswaves_validation"
os.makedirs(OUTDIR, exist_ok=True)

# ---- Correction C1: permanent security identities (dedup before portfolio admission)
_MAPPING = json.load(open("/home/hatch/workspace/research/boswaves_correction/universe_mapping.json"))
TICKER2SEC = {}
for _sid, _info in _MAPPING["securities"].items():
    for _e in _info["tickers"]:
        TICKER2SEC[_e["ticker"]] = _sid
def sec_id(sym):
    return TICKER2SEC.get(sym, "SEC_" + sym)
def ticker_at(sid, date):
    """Date-appropriate ticker label for a permanent security identity.

    Durable rule: canonical security identity first; the displayed ticker is
    the one in effect at the given date — not newest-ticker-wins. Unknown
    securities (e.g. synthetic test symbols) fall back to the raw symbol.
    """
    info = _MAPPING["securities"].get(sid)
    if info is None:
        return sid[4:] if sid.startswith("SEC_") else sid
    for _e in info["tickers"]:
        if (_e["from"] is None or date >= _e["from"]) and (_e["to"] is None or date <= _e["to"]):
            return _e["ticker"]
    raise ValueError(f"no ticker for {sid} at {date}")

BANKRUPT_SUFFIX = ("Q",)  # Q-suffix tickers: bankruptcy proceedings
TRUNC_CUTOFF = "2026-09-01"  # data ending before this => delisted/acquired/bankrupt


def is_truncated(dates):
    return dates[-1] < TRUNC_CUTOFF


def is_bankrupt(symbol):
    return symbol.endswith(BANKRUPT_SUFFIX)


def load_symbol(symbol):
    fp = os.path.join(EOD, symbol + ".json")
    d = json.load(open(fp))
    dates = [b["date"][:10] for b in d]
    o = np.array([b["adjOpen"] for b in d], dtype=float)
    h = np.array([b["adjHigh"] for b in d], dtype=float)
    l = np.array([b["adjLow"] for b in d], dtype=float)
    c = np.array([b["adjClose"] for b in d], dtype=float)
    return dates, o, h, l, c


# ----------------------------------------------------------------------------
# Executable engine (§4B), long-only
# ----------------------------------------------------------------------------
def executable_symbol(symbol, dates, o, h, l, c, sig_cache, invalid_log):
    """Returns (trades, signals). trades: list of dicts. signals: list of
    (signal_k, momentum inputs) for portfolio tie-break."""
    sig = sig_cache
    n = len(c)
    trades = []
    signals = []
    pos = None
    flip_exit_pending = False
    entry_pending = None  # (plan, signal_k)

    def close_pos(exit_k, exit_px, reason):
        r = (exit_px - pos["entry"]) / pos["risk"] if pos["risk"] > 0 else 0.0
        trades.append({
            "symbol": symbol,
            "signal_k": pos["signal_k"],
            "signal_date": dates[pos["signal_k"]],
            "entry_idx": pos["entry_idx"],
            "entry_date": dates[pos["entry_idx"]],
            "exit_idx": exit_k,
            "exit_date": dates[exit_k],
            "entry": pos["entry"],
            "exit": exit_px,
            "stop": pos["stop"],
            "risk": pos["risk"],
            "bars_held": exit_k - pos["entry_idx"],
            "reason": reason,
            "direction": 1,
            "gross_r": r,
        })

    for k in range(n):
        # A. Stop gap check at open (active stop)
        if pos is not None and pos["stop_active"] and o[k] <= pos["stop"]:
            close_pos(k, o[k], "stop_gap")
            pos = None
        # B. Scheduled flip exit at open (only if position survived A)
        if flip_exit_pending:
            if pos is not None:
                close_pos(k, o[k], "flip")
                pos = None
            flip_exit_pending = False
        # C. Scheduled entry at open — IMPLEMENTATION CHECK FIRST
        if entry_pending is not None:
            plan, sk = entry_pending
            fill = o[k]
            # Test opening fill against PRE-EXISTING stop before recalculating geometry.
            if fill <= plan["stop"]:
                invalid_log.append({
                    "symbol": symbol, "signal_k": sk, "signal_date": dates[sk],
                    "entry_date": dates[k], "fill": float(fill),
                    "preexisting_stop": float(plan["stop"]),
                    "reason": "skipped_stop_breached_at_entry"})
            else:
                risk_ps = fill - plan["stop"]
                pos = {"signal_k": sk, "entry_idx": k, "entry": float(fill),
                       "stop": float(plan["stop"]), "risk": float(risk_ps),
                       "stop_active": True}
            entry_pending = None
        # D. Intrabar stop touch (active stop)
        if pos is not None and pos["stop_active"] and l[k] <= pos["stop"]:
            close_pos(k, pos["stop"], "stop")
            pos = None
        # E. Flip detection at close (long-only: both flips exit, only bull enters)
        if sig["bull_flip"][k] or sig["bear_flip"][k]:
            if pos is not None:
                flip_exit_pending = True
            if sig["bull_flip"][k] and k + 1 < n:
                plan = position_plan(
                    {"index": k, "close": c[k], "highs": h, "lows": l}, sig, 1)
                if plan is not None:
                    entry_pending = (plan, k)
                    signals.append({"symbol": symbol, "signal_k": k,
                                    "signal_date": dates[k]})

    # End of data: delisting handling
    if pos is not None:
        if is_truncated(dates) and is_bankrupt(symbol):
            # -100% delisting return: position value -> 0  => exit at 0
            close_pos(n - 1, 0.0, "delist_bankrupt")
        elif is_truncated(dates):
            close_pos(n - 1, c[n - 1], "delist_acquired")
        else:
            close_pos(n - 1, c[n - 1], "eod_open")
    # Pending actions with no next bar: drop, log
    if flip_exit_pending or entry_pending is not None:
        invalid_log.append({"symbol": symbol, "reason": "pending_at_data_end_dropped"})
    return trades, signals


# ----------------------------------------------------------------------------
# Portfolio overlay (§2) — chronological selection over executable candidates
# ----------------------------------------------------------------------------
def apply_portfolio(candidates, sectors, spy_close_by_date, spy_dates,
                    start_equity=100000.0):
    """candidates: executable trades (no portfolio). Each needs signal_date,
    entry_date, exit_date, symbol, entry, exit, stop, risk, gross_r.
    Returns (taken, skipped_log, open_at_end)."""
    # momentum score per candidate: R20(sym,k) - R20(SPY,k); computed by caller
    # and stored as cand['mom_score']. Sort: signal_date, then -mom_score.
    # Correction C1: collapse rename-aliases before admission; caps count securities
    deduped = {}
    for t in candidates:
        k = (t["signal_date"], sec_id(t["symbol"]))
        prev = deduped.get(k)
        # deterministic: one candidate per (signal_date, security identity).
        # Higher mom_score wins; on EXACT ties (expected for duplicate files
        # with identical prices -> identical momentum scores) the
        # lexicographically smallest raw ticker wins, so file/glob ordering
        # can never choose the retained record. The admitted trade is then
        # relabeled with the date-appropriate ticker for its signal date.
        if prev is None or t["mom_score"] > prev["mom_score"] or \
                (t["mom_score"] == prev["mom_score"] and t["symbol"] < prev["symbol"]):
            c = dict(t)
            c["symbol"] = ticker_at(k[1], t["signal_date"])
            c["security_id"] = k[1]
            deduped[k] = c
    n_alias_collapsed = len(candidates) - len(deduped)
    cands = sorted(deduped.values(),
                   key=lambda t: (t["signal_date"], -t["mom_score"], t["symbol"]))
    # Protocol §2: exact momentum ties broken by symbol alphabetical ascending.
    # (Python's sort is stable, so without the third key ties would resolve by
    # input order — not deterministic per the spec.)
    open_pos = []  # taken trades still open
    taken = []
    skipped_log = []
    equity = start_equity

    def sector_of(sym):
        return sectors.get(sym, sym)  # unclassified -> own bucket

    for cand in cands:
        d = cand["signal_date"]
        sid = sec_id(cand["symbol"])
        # settle exits at or before this signal date (realized, gross for sizing)
        still_open = []
        for t in open_pos:
            if t["exit_date"] <= d:
                pnl = t["gross_r"] * t["risk_dollars"]
                equity += pnl
            else:
                still_open.append(t)
        open_pos = still_open
        # slot checks (caps count permanent security identities, not tickers)
        n_open = len(open_pos)
        sec = sector_of(cand["symbol"])
        sec_n = sum(1 for t in open_pos if sector_of(t["symbol"]) == sec)
        heat = sum(t["risk_dollars"] for t in open_pos) / equity if equity > 0 else 1.0
        reason = None
        if any(sec_id(t["symbol"]) == sid for t in open_pos):
            reason = "skipped_duplicate_security"
        elif n_open >= 20:
            reason = "skipped_position_cap"
        elif sec_n >= 5:
            reason = "skipped_sector_cap"
        elif heat >= 0.10:
            reason = "skipped_heat_cap"
        if reason:
            skipped_log.append({"symbol": cand["symbol"], "signal_date": d,
                                "reason": reason, "mom_score": cand["mom_score"]})
            continue
        # take it
        risk_dollars = 0.01 * equity
        size = risk_dollars / cand["risk"] if cand["risk"] > 0 else 0.0
        t = dict(cand)
        t["size"] = size
        t["risk_dollars"] = risk_dollars
        t["equity_at_entry"] = equity
        taken.append(t)
        open_pos.append(t)
    # open at end of sample
    open_at_end = [t for t in open_pos]
    return taken, skipped_log, open_at_end


def cost_r(bps, fill_price, risk_per_share):
    return (bps / 10000.0) * fill_price / risk_per_share if risk_per_share > 0 else 0.0


def apply_costs(taken, bps):
    """Returns list of (net_r, net_pnl_dollars) per taken trade at given bps."""
    out = []
    for t in taken:
        cr = cost_r(bps, t["entry"], t["risk"])
        net_r = t["gross_r"] - cr
        net_pnl = net_r * t["risk_dollars"]
        out.append((net_r, net_pnl))
    return out


# ----------------------------------------------------------------------------
# Clustered inference (§5)
# ----------------------------------------------------------------------------
def two_way_clustered_se(y, g1, g2):
    n = len(y)
    mu = float(np.mean(y))
    e = y - mu

    def one_way(groups):
        uniq, inv = np.unique(groups, return_inverse=True)
        G = len(uniq)
        if G <= 1:
            return 0.0, G
        sums = np.bincount(inv, weights=e)
        return (G / (G - 1)) * float(np.sum(sums ** 2)) / n ** 2, G

    v1, G1 = one_way(np.asarray(g1))
    v2, G2 = one_way(np.asarray(g2))
    both = np.array([f"{a}|{b}" for a, b in zip(g1, g2)])
    v12, G12 = one_way(both)
    v_tw = v1 + v2 - v12
    # CGM can go negative in finite samples; take max with one-ways (conservative)
    v_tw = max(v_tw, v1, v2, 0.0)
    se = math.sqrt(v_tw)
    se_naive = float(np.std(y, ddof=1) / math.sqrt(n)) if n > 1 else 0.0
    return {"se": se, "t": mu / se if se > 0 else 0.0, "mu": mu,
            "G1": G1, "G2": G2, "G12": G12,
            "n_eff": n * (se_naive / se) ** 2 if se > 0 else 0.0,
            "se_naive": se_naive}


def block_bootstrap_ci(y, quarters, n_resamples=10000, seed=20261003):
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    uq = np.unique(quarters)
    idx_by_q = {q: np.where(quarters == q)[0] for q in uq}
    means = np.empty(n_resamples)
    for i in range(n_resamples):
        chosen = rng.choice(uq, size=len(uq), replace=True)
        idx = np.concatenate([idx_by_q[q] for q in chosen])
        means[i] = y[idx].mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    return {"ci_lo": float(lo), "ci_hi": float(hi),
            "excludes_zero": bool(lo > 0 or hi < 0),
            "n_quarters": len(uq)}


# ----------------------------------------------------------------------------
# Tail diagnostics (§6)
# ----------------------------------------------------------------------------
def tail_diagnostics(trades_25bps):
    """trades_25bps: list of dicts with net_r_25. Returns dict of removals."""
    rs = np.array([t["net_r_25"] for t in trades_25bps])
    n = len(rs)
    order = np.argsort(-rs)  # descending
    out = {}

    def analyze(mask, label):
        sub = rs[mask]
        return {"n": int(mask.sum()), "expectancy": float(sub.mean()) if mask.sum() else 0.0}

    # (a1) top 1%
    k1 = math.ceil(0.01 * n)
    cutoff = rs[order[k1 - 1]]
    drop1 = rs >= cutoff  # conservative: all ties included
    # (protect: ensure at least k1 dropped; ties only add)
    out["top1pct"] = {"dropped": int(drop1.sum()), "cutoff_r": float(cutoff)}
    out["top1pct"].update(analyze(~drop1, "top1"))
    # (a2) top 5%
    k5 = math.ceil(0.05 * n)
    cutoff5 = rs[order[k5 - 1]]
    drop5 = rs >= cutoff5
    out["top5pct"] = {"dropped": int(drop5.sum()), "cutoff_r": float(cutoff5)}
    out["top5pct"].update(analyze(~drop5, "top5"))
    # (a3) best year by exit date
    years = {}
    for t in trades_25bps:
        y = t["exit_date"][:4]
        years[y] = years.get(y, 0.0) + t["net_r_25"]
    best_y = max(years, key=years.get)
    dropy = np.array([t["exit_date"][:4] == best_y for t in trades_25bps])
    out["best_year"] = {"year": best_y, "year_total_r": float(years[best_y]),
                        "dropped": int(dropy.sum())}
    out["best_year"].update(analyze(~dropy, "besty"))
    out["year_totals"] = {y: float(v) for y, v in sorted(years.items())}
    return out


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------
def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def main():
    import glob
    ledger_path = "/home/hatch/workspace/research/boswaves_correction/validation_ledger_c1.jsonl"
    t_start = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()

    # ---- STEP 0: hashes (protocol + code), written to ledger BEFORE executing
    proto = "/home/hatch/workspace/research/boswaves_validation_protocol_v3_20261003.md"
    code_files = {
        "protocol_v3": proto,
        "boswaves_ind.py": "/home/hatch/workspace/research/boswaves/boswaves_ind.py",
        "backtest.py": "/home/hatch/workspace/research/boswaves/backtest.py",
        "validate_v3c1.py": os.path.join(OUTDIR, "validate_v3c1.py"),
        "universe_mapping": "/home/hatch/workspace/research/boswaves_correction/universe_mapping.json",
    }
    hashes = {k: sha256_file(p) for k, p in code_files.items()}
    print("STEP 0 hashes:")
    for k, v in hashes.items():
        print(f"  {k}: {v[:16]}...")

    # ---- universe + coverage audit
    uni = [l.strip() for l in open(
        "/home/hatch/workspace/goals/vcp-fundamental-momentum-probe-v0-1/hidden_files/phase1a/batch_all.txt")
        if l.strip()]
    files = {os.path.basename(f)[:-5]: f
             for f in glob.glob(os.path.join(EOD, "*.json"))}
    cov = {"universe_n": len(uni), "files_present": len(files)}
    missing = [t for t in uni if t not in files]
    cov["missing_no_file"] = missing
    usable, short, inactive = [], [], []
    enddates = {}
    for sym, fp in files.items():
        try:
            d = json.load(open(fp))
        except Exception:
            continue
        if len(d) < 100:
            short.append(sym)
            continue
        usable.append(sym)
        enddates[sym] = d[-1]["date"][:10]
        if d[-1]["date"][:10] < TRUNC_CUTOFF:
            inactive.append(sym)
    cov["usable_ge100"] = len(usable)
    cov["short_lt100"] = short
    cov["inactive_truncated"] = sorted(inactive)
    cov["inactive_bankrupt_q"] = sorted([s for s in inactive if is_bankrupt(s)])
    print(f"Coverage: universe={cov['universe_n']} files={cov['files_present']} "
          f"usable={cov['usable_ge100']} inactive={len(inactive)} "
          f"bankruptQ={len(cov['inactive_bankrupt_q'])} missing={len(missing)}")
    json.dump(cov, open(os.path.join(OUTDIR, "coverage_audit.json"), "w"), indent=2)

    # ---- SPY closes for momentum tie-break
    spyd = json.load(open(os.path.join(EOD, "SPY.json")))
    spy_by_date = {b["date"][:10]: b["adjClose"] for b in spyd}
    spy_dates = sorted(spy_by_date)

    def spy_r20(dstr):
        # 20 trading days prior in SPY calendar
        try:
            i = spy_dates.index(dstr)
        except ValueError:
            return None
        if i < 20:
            return None
        c0, c1 = spy_by_date[spy_dates[i - 20]], spy_by_date[dstr]
        return c1 / c0 - 1 if c0 else None

    sectors = json.load(open("/tmp/sector_union.json"))

    # ---- load clean universe data + signals cache
    # (SPY excluded: not a common stock, not in the 831 universe; loaded
    # separately below for the fidelity reproduction only)
    data = {}
    for sym in usable:
        if sym == "SPY":
            continue
        dates, o, h, l, c = load_symbol(sym)
        # restrict to pinned sample window (data already within)
        sig = compute_boswaves(o, h, l, c)
        data[sym] = (dates, o, h, l, c, sig)
    print(f"loaded {len(data)} symbols")

    def load_any(sym):
        dates, o, h, l, c = load_symbol(sym)
        return dates, o, h, l, c, compute_boswaves(o, h, l, c)

    # ---- FIDELITY (§7.1): published engine on original 145 symbols
    orig_syms = [l.strip() for l in open("/tmp/orig_symbols.txt") if l.strip()]
    fl = []
    for sym in orig_syms:
        dates, o, h, l, c, sig = data.get(sym) or load_any(sym)
        for t in backtest_symbol(dates, o.tolist(), h.tolist(), l.tolist(), c.tolist()):
            if t["direction"] == 1 and t["reason"] != "eod_open":
                fl.append(t["r"])
    f_n, f_mu = len(fl), float(np.mean(fl))
    fidelity = {"n": f_n, "expectancy": f_mu,
                "pass": f_n == 10247 and abs(f_mu - 0.23123128812746693) < 0.001}
    print(f"FIDELITY: n={f_n} exp={f_mu:+.6f} PASS={fidelity['pass']}")
    if not fidelity["pass"]:
        print("Fidelity gate FAILED — stopping per protocol.")
        return

    # ---- Layer 1: source-parity on clean universe (published engine, long-only)
    L1 = []
    for sym, (dates, o, h, l, c, sig) in data.items():
        for t in backtest_symbol(dates, o.tolist(), h.tolist(), l.tolist(), c.tolist()):
            if t["direction"] != 1:
                continue
            if t["reason"] == "eod_open":
                # delisting treatment on truncated symbols
                if is_truncated(dates):
                    if is_bankrupt(sym):
                        t = dict(t); t["exit"] = 0.0; t["reason"] = "delist_bankrupt"
                        t["r"] = -t["entry"] / t["risk"] if t["risk"] > 0 else 0.0
                    else:
                        t = dict(t); t["reason"] = "delist_acquired"
                else:
                    continue  # survivor eod_open excluded like the original study
            t["symbol"] = sym
            # signal_k = entry_idx for parity engine (entry at flip-bar close)
            t["signal_k"] = t.get("entry_idx", None)
            L1.append(t)
    print(f"Layer1 parity(clean): {len(L1)} long trades")

    # ---- Layer 2: executable fills, no portfolio
    invalid_log = []
    L2, siglist = [], []
    for sym, (dates, o, h, l, c, sig) in data.items():
        tr, sg = executable_symbol(sym, dates, o, h, l, c, sig, invalid_log)
        L2.extend(tr)
        siglist.extend(sg)
    print(f"Layer2 executable(no-portfolio): {len(L2)} trades, "
          f"{len(invalid_log)} invalid/skipped-at-entry")
    json.dump(invalid_log, open(os.path.join(OUTDIR, "entry_invalidations.json"), "w"), indent=2)

    # momentum scores for candidates (tie-break)
    for t in L2:
        sym = t["symbol"]; k = t["signal_k"]
        dates, o, h, l, c, sig = data[sym]
        r_sym = c[k] / c[k - 20] - 1 if k >= 20 and c[k - 20] else None
        r_spy = spy_r20(t["signal_date"])
        t["mom_score"] = (r_sym - r_spy) if (r_sym is not None and r_spy is not None) else -999.0

    # ---- Layer 3: executable + portfolio overlay
    taken, skipped_log, open_at_end = apply_portfolio(L2, sectors, spy_by_date, spy_dates)
    print(f"Layer3 portfolio: taken={len(taken)} skipped={len(skipped_log)} "
          f"open_at_end={len(open_at_end)}")
    json.dump([{"symbol": s["symbol"], "signal_date": s["signal_date"],
                "reason": s["reason"]} for s in skipped_log],
              open(os.path.join(OUTDIR, "portfolio_skips.json"), "w"), indent=2)

    # primary sample: closed trades only (open_at_end excluded per §2/§7)
    open_ids = {id(t) for t in open_at_end}
    closed_taken = [t for t in taken if id(t) not in open_ids]

    # ---- cost legs on Layer 3 closed trades
    legs = {}
    for bps in (4, 25, 50):
        nr = [r for t, (r, p) in zip(taken, apply_costs(taken, bps))
              if id(t) not in open_ids]
        legs[bps] = np.array(nr)
    print(f"closed for primary stats: {len(closed_taken)}")

    # ---- clustered inference on 25bps net R (closed)
    y25 = np.array([r for t, (r, p) in zip(taken, apply_costs(taken, 25))
                    if id(t) not in open_ids])
    syms_c = [t["symbol"] for t in taken if id(t) not in open_ids]
    months_c = [t["exit_date"][:7] for t in taken if id(t) not in open_ids]
    cl = two_way_clustered_se(y25, syms_c, months_c)
    quarters = np.array([t["exit_date"][:4] + "-Q" + str((int(t["exit_date"][5:7]) - 1) // 3 + 1)
                         for t in taken if id(t) not in open_ids])
    bb = block_bootstrap_ci(y25, quarters)
    print(f"clustered: mu={cl['mu']:+.4f} se={cl['se']:.4f} t={cl['t']:+.2f} "
          f"G_sym={cl['G1']} G_mo={cl['G2']} n_eff={cl['n_eff']:.0f}")
    print(f"bootstrap 95% CI: [{bb['ci_lo']:+.4f}, {bb['ci_hi']:+.4f}] "
          f"excludes_zero={bb['excludes_zero']} n_q={bb['n_quarters']}")

    # ---- tail diagnostics (25bps net R, closed)
    taken25 = []
    for t, (r_net, pnl) in zip(taken, apply_costs(taken, 25)):
        if id(t) in open_ids:
            continue
        t2 = dict(t); t2["net_r_25"] = r_net
        taken25.append(t2)
    tails = tail_diagnostics(taken25)
    # clustered t on tail-removed sets
    def tail_t(mask):
        yy = y25[mask]
        gg1 = [s for s, m in zip(syms_c, mask) if m]
        gg2 = [s for s, m in zip(months_c, mask) if m]
        return two_way_clustered_se(yy, gg1, gg2)
    rs25 = np.array([t["net_r_25"] for t in taken25])
    n25 = len(rs25); order = np.argsort(-rs25)
    k1 = math.ceil(0.01 * n25); cut1 = rs25[order[k1 - 1]]
    mask1 = ~(rs25 >= cut1)
    t1 = tail_t(mask1)
    years = {}
    for t in taken25:
        years[t["exit_date"][:4]] = years.get(t["exit_date"][:4], 0.0) + t["net_r_25"]
    by = max(years, key=years.get)
    masky = np.array([t["exit_date"][:4] != by for t in taken25])
    ty = tail_t(masky)
    print(f"tail top1%: n_rem={mask1.sum()} exp={t1['mu']:+.4f} t={t1['t']:+.2f}")
    print(f"tail bestyr {by}: n_rem={masky.sum()} exp={ty['mu']:+.4f} t={ty['t']:+.2f}")

    # ---- equity curve + annualized Calmar (25bps, closed trades)
    pnl25 = [p for t, (r, p) in zip(taken, apply_costs(taken, 25)) if id(t) not in open_ids]
    exd = [t["exit_date"] for t in taken if id(t) not in open_ids]
    ord_e = np.argsort(exd)
    eq = 100000.0; peak = eq; maxdd = 0.0; curve = []
    for i in ord_e:
        eq += pnl25[i]
        curve.append((exd[i], eq))
        peak = max(peak, eq)
        maxdd = max(maxdd, (peak - eq) / peak if peak > 0 else 0.0)
    total_ret = eq / 100000.0 - 1
    # trading days first entry -> last exit
    alld = sorted(spy_dates)
    d0 = min(t["entry_date"] for t in taken if id(t) not in open_ids)
    d1 = max(t["exit_date"] for t in taken if id(t) not in open_ids)
    ntd = sum(1 for d in alld if d0 <= d <= d1)
    cagr = (1 + total_ret) ** (252 / ntd) - 1 if ntd > 0 and total_ret > -1 else -1.0
    calmar = cagr / maxdd if maxdd > 0 else 0.0
    print(f"equity: final=${eq:,.0f} total_ret={total_ret:+.2%} ntd={ntd} "
          f"CAGR={cagr:+.2%} maxDD={maxdd:.2%} Calmar={calmar:.2f}")

    # ---- divergence table L1 vs L2
    # Match on (symbol, signal_date): L1 entry_date == flip-bar date (entry at close);
    # L2 signal_date == flip-bar date. Each (symbol, signal_date) is unique
    # (edge-triggered flips, one position per symbol).
    def key1(t):
        return (t["symbol"], t["entry_date"])
    def key2(t):
        return (t["symbol"], t["signal_date"])
    L1key = {}
    for t in L1:
        L1key.setdefault(key1(t), []).append(t)
    L2key = {}
    for t in L2:
        L2key.setdefault(key2(t), []).append(t)
    div = []
    for key in sorted(set(L1key) | set(L2key)):
        alist, blist = L1key.get(key, []), L2key.get(key, [])
        if alist and blist:
            a, b = alist[0], blist[0]
            if (a["reason"] != b["reason"] or a["exit_date"] != b["exit_date"]
                    or abs(a["exit"] - b["exit"]) > 1e-9):
                div.append({"symbol": key[0], "signal_date": key[1],
                            "L1_exit": [a["exit_date"], round(a["exit"], 4), a["reason"], round(a["r"], 4)],
                            "L2_exit": [b["exit_date"], round(b["exit"], 4), b["reason"], round(b["gross_r"], 4)],
                            "dR": round(b["gross_r"] - a["r"], 4)})
            if len(alist) > 1 or len(blist) > 1:
                div.append({"symbol": key[0], "signal_date": key[1],
                            "note": "multiple trades same key",
                            "n_L1": len(alist), "n_L2": len(blist)})
        elif alist and not blist:
            a = alist[0]
            div.append({"symbol": key[0], "signal_date": key[1], "L1_only": True,
                        "L1_exit": [a["exit_date"], round(a["exit"], 4), a["reason"]]})
        else:
            b = blist[0]
            div.append({"symbol": key[0], "signal_date": key[1], "L2_only": True,
                        "L2_exit": [b["exit_date"], round(b["exit"], 4), b["reason"]]})
    dR_total = sum(d.get("dR", 0.0) for d in div if "dR" in d)
    print(f"divergence: {len(div)} rows, dR_total={dR_total:+.2f}R")
    json.dump(div, open(os.path.join(OUTDIR, "divergence_table.json"), "w"), indent=2)

    # ---- gate verdicts
    exp25 = float(np.mean(y25))
    # Correction C1: §7.7 coverage gate — wired into the verdict, not narrated.
    # missing_no_file = tickers with no file AND no reason = unquantified gaps.
    # Protocol: material unquantifiable gaps -> INCONCLUSIVE (not FAIL).
    audit_path = os.path.join(OUTDIR, "coverage_audit.json")
    assert os.path.exists(audit_path), "coverage audit skipped: run blocked per §8"
    coverage_ok = len(cov.get("missing_no_file", ["__audit_key_missing__"])) == 0
    if not coverage_ok:
        print(f"COVERAGE GATE: {len(cov['missing_no_file'])} tickers with no file "
              f"and no reason -> INCONCLUSIVE per §7.7")
    gates = {
        "fidelity": bool(fidelity["pass"]),
        "expectancy_gt_015": bool(exp25 > 0.15),
        "clustered_t_gt_2": bool(abs(cl["t"]) > 2.0 and bb["excludes_zero"]),
        "calmar_gt_1": bool(calmar > 1.0),
        "tail_top1_gt_0": bool(t1["mu"] > 0),
        "tail_bestyr_gt_0": bool(ty["mu"] > 0),
        "clusters_ok": bool(cl["G1"] >= 30 and cl["G2"] >= 24),
        "coverage_ok": bool(coverage_ok),
    }
    verdict = "PASS" if all(gates.values()) else "FAIL"
    if not (cl["G1"] >= 30 and cl["G2"] >= 24) or not bb["excludes_zero"] == (abs(cl["t"]) > 2.0):
        verdict = "INCONCLUSIVE"
    if not coverage_ok:
        verdict = "INCONCLUSIVE"
    print("GATES:", gates, "->", verdict)

    # ---- save everything
    results = {
        "hashes": hashes,
        "coverage": {k: (v if not isinstance(v, list) or len(v) < 50 else f"{len(v)} items")
                     for k, v in cov.items()},
        "fidelity": fidelity,
        "layer1_n": len(L1),
        "layer2_n": len(L2),
        "layer3_taken": len(taken),
        "layer3_closed": len(closed_taken),
        "invalid_at_entry": len(invalid_log),
        "cost_legs": {str(b): {"expectancy": float(np.mean(v)), "n": len(v)} for b, v in legs.items()},
        "clustered_25bps": {k: (float(v) if isinstance(v, float) else v) for k, v in cl.items()},
        "bootstrap_25bps": bb,
        "tails": tails,
        "tail_top1_clustered": {"mu": t1["mu"], "t": t1["t"], "n": int(mask1.sum())},
        "tail_bestyr_clustered": {"mu": ty["mu"], "t": ty["t"], "n": int(masky.sum())},
        "equity_25bps": {"final": eq, "total_ret": total_ret, "ntd": ntd,
                         "cagr": cagr, "maxdd": maxdd, "calmar": calmar},
        "divergence_rows": len(div),
        "divergence_dR_total": dR_total,
        "gates": gates,
        "verdict": verdict,
    }
    json.dump(results, open(os.path.join(OUTDIR, "robustness_results.json"), "w"), indent=2)

    # ---- ledger entries (append-only)
    import datetime
    for label in ["source_parity", "executable_4bps", "executable_25bps", "executable_50bps"]:
        entry = {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 "run_label": label, "config_hash": hashes["validate_v3.py"],
                 "protocol_hash": hashes["protocol_v3"],
                 "verdict": verdict, "gates": gates}
        with open(ledger_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    print("ledger appended; results saved")
    return results


if __name__ == "__main__":
    main()
