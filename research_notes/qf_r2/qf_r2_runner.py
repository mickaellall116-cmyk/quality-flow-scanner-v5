#!/usr/bin/env python3
"""QF-R2-BRK-VOL-4H-001 — runner (PREFLIGHT ONLY; performance execution held).

Hypothesis: unusually high participation on a causal 4H bullish breakout
improves after-cost trade expectancy vs otherwise similar 4H breakouts
without the high-volume confirmation.

Spec: research_notes/qf_r2/qf_r2_brk_vol_4h_prereg_20261004.md
(provenance: GitHub Issue #1 comment #5981881915, ChatGPT, 2026-10-04).

Preflight contract:
- `--verify`: verify frozen input hashes + module hashes (fail closed), write
  the code/data manifest, establish EMPTY raw-output paths. No market data
  is read for performance in this mode (only file bytes for hashing).
- `--run`: FULL PERFORMANCE RUN. HARD-HELD unless env QF_R2_ALLOW_RUN=1.
  Never invoke during preflight.

Frozen inputs: yahoo 1H per-symbol files
(data_inventory_scratch_20261004/h1_raw/h1_{SYM}.pkl, fallback
pine_1h/cache/h1_{SYM}.pkl) hashed in
research_notes/yahoo_1h_input_manifest_20261004.json; corrected
session-anchored 4H constructor scanner_rules.resample_closed_4h_session_anchored
(the exact constructor used by the TOP-vs-BROAD evidence stack,
top_broad_performance.build_4h). Frozen SPY daily
(daily_ranking_frozen_20261004/d1_SPY.pkl) hashed in
research_notes/daily_ranking_manifest_20261004.json.

Nothing here modifies any frozen file. scanner_rules is imported read-only.
"""

import argparse
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))  # research_notes/qf_r2 -> repo root
if REPO not in sys.path:
    sys.path.insert(0, REPO)  # read-only import of frozen scanner_rules

# ---------------------------------------------------------------- constants
STUDY_START = "2025-03-17"
STUDY_END = "2026-09-14"
WARMUP_FROM = "2024-10-07"

VOLUME_THRESHOLD = 1.50
BASELINE_BARS = 20
PRIOR_HIGH_N = 20
ATR_LEN = 14
STOP_ATR_MULT = 0.50
TP_R = 2.0
MAX_HOLD_BARS = 20
COST_PRIMARY_BPS = 25.0
COST_DIAG_BPS = 4.0
SEED = 20261004
N_PERM = 10000
N_BOOT = 10000
MIN_PAIRS = 300
ABS_MIN_R = 0.10
INC_MIN_R = 0.10
P_MAX = 0.05
MIN_PERIOD_PAIRS = 75
Y1 = ("2025-03-17", "2026-03-16")
Y2 = ("2026-03-17", "2026-09-14")

EXCLUDED = {"BMNR", "CRWV", "GLXY", "NBIS", "XYZ", "CLSK", "SBET"}

EVIDENCE_TIER = "COMPUTED"  # never REPRODUCED until a clean rerun matches

RAW_PATHS = ["events.csv", "matches.csv", "ledger.csv",
             "inference_in.csv", "inference_out.csv", "gates.json",
             "code_data_manifest.json"]

TZ = "America/New_York"


# ------------------------------------------------------------------ hashing
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_1h(sym):
    p1 = os.path.join(REPO, "data_inventory_scratch_20261004", "h1_raw",
                      f"h1_{sym}.pkl")
    p2 = os.path.join(REPO, "pine_1h", "cache", f"h1_{sym}.pkl")
    if os.path.exists(p1):
        return p1
    if os.path.exists(p2):
        return p2
    return None


def verify_inputs():
    """Verify every frozen 1H input + SPY daily against their manifests.

    Returns (symbols, meta). Raises RuntimeError (fail closed) on any
    missing file or hash mismatch. No Yahoo substitution.
    """
    man_path = os.path.join(REPO, "research_notes",
                            "yahoo_1h_input_manifest_20261004.json")
    man = json.load(open(man_path))
    files = man["files"]
    symbols, checked = [], 0
    for sym, meta in sorted(files.items()):
        path = _resolve_1h(sym)
        if path is None:
            raise RuntimeError(f"FAIL CLOSED: frozen 1H input missing: {sym}")
        got = sha256_file(path)
        if got != meta["sha256"]:
            raise RuntimeError(f"FAIL CLOSED: hash mismatch on {sym}: "
                               f"expected {meta['sha256'][:12]} got {got[:12]}")
        checked += 1
        if sym not in EXCLUDED:
            symbols.append((sym, path))
    spy_man = json.load(open(os.path.join(
        REPO, "research_notes", "daily_ranking_manifest_20261004.json")))
    spy_meta = spy_man["files"]["SPY"]
    spy_path = os.path.join(REPO, "daily_ranking_frozen_20261004", "d1_SPY.pkl")
    if not os.path.exists(spy_path):
        raise RuntimeError("FAIL CLOSED: frozen SPY daily input missing")
    got = sha256_file(spy_path)
    if got != spy_meta["sha256"]:
        raise RuntimeError("FAIL CLOSED: SPY daily hash mismatch")
    return symbols, {
        "1h_manifest": man_path, "1h_manifest_sha256": sha256_file(man_path),
        "1h_files_checked": checked, "1h_pool": len(symbols),
        "spy_daily": spy_path, "spy_daily_sha256": got,
    }


def module_hashes():
    """Hashes of code modules the runner depends on (read-only)."""
    mods = {}
    for rel in ["scanner_rules.py"]:
        p = os.path.join(REPO, rel)
        mods[rel] = sha256_file(p)
    mods["qf_r2_runner.py"] = sha256_file(os.path.join(HERE, "qf_r2_runner.py"))
    mods["qf_r2_fixtures.py"] = sha256_file(
        os.path.join(HERE, "qf_r2_fixtures.py"))
    mods["qf_r2_brk_vol_4h_prereg_20261004.md"] = sha256_file(
        os.path.join(HERE, "qf_r2_brk_vol_4h_prereg_20261004.md"))
    return mods

# ------------------------------------------------------- bar construction
def build_4h(df1h, symbol):
    """Corrected session-anchored 4H from frozen 1H inputs.

    Exact constructor from the TOP-vs-BROAD evidence stack
    (top_broad_performance.build_4h -> scanner_rules.
    resample_closed_4h_session_anchored). scanner_rules is NOT modified.
    """
    import scanner_rules as sr
    df4h = sr.resample_closed_4h_session_anchored(df1h, symbol)
    df4h = df4h[df4h.index >= __import__("pandas").Timestamp(
        WARMUP_FROM, tz=TZ)]
    return df4h


def session_close_minutes(day):
    """Session close in minutes-since-midnight ET; None if non-trading day."""
    import pandas as pd
    import scanner_rules as sr
    sc = sr.session_close_et(pd.Timestamp(day).tz_localize(TZ)
                             if getattr(day, "tz", None) is None
                             else pd.Timestamp(day).tz_convert(TZ))
    if sc is None:
        return None
    sc = sc.tz_convert(TZ)
    return sc.hour * 60 + sc.minute


def bar_slot_and_minutes(bar_start):
    """(slot, bar_minutes) for a 4H bar start (tz-aware).

    slot: 'opening' (09:30 bar) or 'closing' (13:30 bar).
    bar_minutes: actual session minutes represented by the bar.
    """
    local = bar_start.tz_convert(TZ)
    start_min = local.hour * 60 + local.minute
    close_min = session_close_minutes(local.normalize())
    if start_min < 810:
        slot = "opening"
        # Opening bin is [09:30,13:30) by construction; on early-close days
        # the bar represents only up to the session close.
        minutes = min(810, close_min if close_min is not None else 960) - 570
    else:
        slot = "closing"
        minutes = (close_min if close_min is not None else 960) - 810
    return slot, int(minutes)


def is_normal_session(bar_start):
    """True iff the bar's session closed at 16:00 ET (not early-close)."""
    local = bar_start.tz_convert(TZ)
    return session_close_minutes(local.normalize()) == 960


def atr14_wilder(df):
    """Wilder RMA(14) ATR on the 4H frame — identical formula to the
    TOP-vs-BROAD stack's pine_backtest.atr(df) default (l=14)."""
    import pandas as pd
    h, lw, c = df["High"], df["Low"], df["Close"]
    pc = c.shift(1)
    tr = pd.concat([h - lw, (h - pc).abs(), (lw - pc).abs()],
                   axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / ATR_LEN, adjust=False).mean()


# ------------------------------------------------------- event detection
def breakout_candidates(symbol, df4h, spy_regime):
    """Causal bullish-breakout candidates on completed 4H bars.

    Event-time fields only. NO volume classification and NO outcome here.
    prior_high20 strictly excludes the current bar (spec rule 1).
    """
    import pandas as pd
    cands, diag = [], {"early_close": 0}
    if df4h.empty or "Volume" not in df4h.columns:
        return cands, diag
    df = df4h.sort_index()
    atr = atr14_wilder(df)
    n = len(df)
    start_d = pd.Timestamp(STUDY_START, tz=TZ)
    end_d = pd.Timestamp(STUDY_END, tz=TZ) + pd.Timedelta(days=1)
    for i in range(PRIOR_HIGH_N, n):
        ts = df.index[i]
        if not (start_d <= ts < end_d):
            continue
        if not is_normal_session(ts):
            diag["early_close"] += 1
            continue  # spec: early-close signal bars excluded
        prior_high = float(df["High"].iloc[i - PRIOR_HIGH_N:i].max())
        close = float(df["Close"].iloc[i])
        if not close > prior_high:
            continue
        a = float(atr.iloc[i])
        if not (a > 0) or math.isnan(a):
            continue
        local = ts.tz_convert(TZ)
        slot, minutes = bar_slot_and_minutes(ts)
        cands.append({
            "symbol": symbol,
            "ts": ts.isoformat(),
            "signal_bar": i,
            "slot": slot,
            "bar_minutes": minutes,
            "normal_session": is_normal_session(ts),
            "quarter": f"{local.year}-Q{(local.month - 1) // 3 + 1}",
            "spy_regime": spy_regime(ts),
            "prior_high20": prior_high,
            "close": close,
            "atr14": a,
            "strength": (close - prior_high) / a,
            "atr_pct": a / close,
            "volume": float(df["Volume"].iloc[i]),
            "vol_rate": float(df["Volume"].iloc[i]) / minutes,
        })
    return cands, diag


def classify_volume(ev, df4h):
    """Frozen volume confirmation. Returns (ok, reason).

    vol_rate_t = Volume[t]/bar_minutes; baseline = median vol_rate of the
    previous 20 completed NORMAL-SESSION bars in the SAME session_slot
    (strictly before t). volume_ratio >= 1.50 -> HIGH-VOLUME.
    """
    import pandas as pd
    import statistics
    df = df4h.sort_index()
    i = ev["signal_bar"]
    base = []
    for j in range(i):
        ts = df.index[j]
        s, m = bar_slot_and_minutes(ts)
        if s == ev["slot"] and is_normal_session(ts):
            base.append(float(df["Volume"].iloc[j]) / m)
    if len(base) < BASELINE_BARS:
        return False, "no_baseline"
    baseline = statistics.median(base[-BASELINE_BARS:])
    if baseline <= 0:
        return False, "no_baseline"
    ev["baseline"] = baseline
    ev["volume_ratio"] = ev["vol_rate"] / baseline
    ev["high_volume"] = bool(ev["volume_ratio"] >= VOLUME_THRESHOLD)
    return True, ""


def admit_events(symbol, df4h, spy_regime):
    """Chronological admission with causal suppression.

    Suppression CHECK happens before volume classification (spec rule 7):
    a later breakout candidate at/below the busy horizon of an admitted
    event is suppressed without ever seeing its volume category or outcome.
    The busy horizon extends over the admitted event's trade path
    (exit bar) or the 20-bar horizon, whichever is hit first.
    """
    cands, diag = breakout_candidates(symbol, df4h, spy_regime)
    diag.update({"suppressed": 0, "no_baseline": 0, "no_next_open": 0})
    events, suppressed_until = [], -1
    n = len(df4h.sort_index())
    for ev in cands:  # already chronological
        i = ev["signal_bar"]
        if i <= suppressed_until:
            diag["suppressed"] += 1
            continue
        ok, reason = classify_volume(ev, df4h)
        if not ok:
            diag[reason] += 1
            continue  # ineligible: consumes no suppression
        if i + 1 >= n:
            diag["no_next_open"] += 1
            ev["excluded"] = "no_next_open"
            events.append(ev)
            continue
        import pandas as pd
        df = df4h.sort_index()
        ev["entry_ts"] = df.index[i + 1].isoformat()
        ev["entry_open"] = float(df["Open"].iloc[i + 1])
        ev["entry_bar"] = i + 1
        events.append(ev)
        trade = simulate_trade(ev, df)
        horizon_end = i + MAX_HOLD_BARS
        suppressed_until = min(trade["exit_bar"], horizon_end)
    return events, diag

# ------------------------------------------------------- trade simulation
def simulate_trade(ev, df4h):
    """Identical tradable path for both arms.

    entry = next 4H bar open. stop = prior_high20 - 0.5*ATR14[t].
    If R <= 0 -> invalid/unexecutable (excluded with reason).
    TP = entry + 2R. Max hold 20 completed 4H bars after entry.
    Exit at first of: stop, TP, close of bar 20.
    Same-bar stop+TP ambiguity: STOP-FIRST. Gap through stop: fill at the
    worse open. Costs: 25bps round-trip PRIMARY, 4bps SECONDARY diagnostic,
    applied as bps * entry / initial_R (R units).
    """
    df = df4h.sort_index()
    entry = float(ev["entry_open"])
    stop = float(ev["prior_high20"]) - STOP_ATR_MULT * float(ev["atr14"])
    r0 = entry - stop
    if r0 <= 0:
        return {"valid": False, "reason": "non_positive_r", "exit_bar": ev["entry_bar"]}
    tp = entry + TP_R * r0
    j0 = ev["entry_bar"]
    n = len(df)
    exit_price, exit_bar, exit_kind = None, None, None
    last = min(j0 + MAX_HOLD_BARS - 1, n - 1)
    for j in range(j0, last + 1):
        o = float(df["Open"].iloc[j])
        h = float(df["High"].iloc[j])
        lw = float(df["Low"].iloc[j])
        c = float(df["Close"].iloc[j])
        if o <= stop:
            # Gap through stop: fill at the worse open, never the stop.
            exit_price, exit_bar, exit_kind = o, j, "gap_stop"
            break
        if lw <= stop:
            # STOP-FIRST: stop wins any same-bar stop+TP ambiguity.
            exit_price, exit_bar, exit_kind = stop, j, "stop"
            break
        if h >= tp:
            exit_price, exit_bar, exit_kind = tp, j, "target"
            break
        if j == last:
            exit_price, exit_bar, exit_kind = c, j, "horizon"
    gross_r = (exit_price - entry) / r0
    cost_p = (COST_PRIMARY_BPS / 10000.0) * entry / r0
    cost_d = (COST_DIAG_BPS / 10000.0) * entry / r0
    return {
        "valid": True,
        "entry": entry, "stop": stop, "tp": tp, "r0": r0,
        "exit_price": exit_price, "exit_bar": exit_bar, "exit_kind": exit_kind,
        "gross_r": gross_r,
        "net_r_primary": gross_r - cost_p,
        "net_r_diag": gross_r - cost_d,
        "cost_r_primary": cost_p, "cost_r_diag": cost_d,
    }


# ------------------------------------------------------- matching
def assign_atr_deciles(events):
    """ATR_pct decile per event, pooled over all eligible events.

    Spec ambiguity (reported): the reference population for 'nearest
    ATR_pct decile' is not named. Implementation: deciles of the pooled
    eligible-event ATR_pct distribution (pd.qcut, 10 bins).
    """
    import pandas as pd
    vals = pd.Series([e["atr_pct"] for e in events])
    try:
        codes = pd.qcut(vals, 10, labels=False, duplicates="drop")
    except ValueError:
        codes = pd.Series(0, index=vals.index)
    codes = pd.Series(codes, index=vals.index).fillna(0).astype(int)
    for e, d in zip(events, codes):
        e["atr_decile"] = int(d)


def match_controls(events):
    """1:1 matched control per HIGH-VOLUME event, no replacement.

    Strata (exact): same session_slot, same calendar quarter, same SPY
    regime. Then nearest ATR_pct decile, then nearest breakout_strength.
    Deterministic tie-break: smallest absolute timestamp distance, then
    symbol alphabetically, then earlier timestamp.
    Deterministic processing order: HIGH-VOLUME events sorted by
    (ts, symbol).
    """
    import pandas as pd
    eligible = [e for e in events if "excluded" not in e and "entry_open" in e]
    assign_atr_deciles(eligible)
    highs = sorted([e for e in eligible if e["high_volume"]],
                   key=lambda e: (e["ts"], e["symbol"]))
    ctrls = [e for e in eligible if not e["high_volume"]]
    used, pairs, unmatched = set(), [], []
    for h in highs:
        hts = pd.Timestamp(h["ts"])
        cands = [c for c in ctrls
                 if id(c) not in used
                 and c["slot"] == h["slot"]
                 and c["quarter"] == h["quarter"]
                 and c["spy_regime"] == h["spy_regime"]]
        if not cands:
            unmatched.append(h)
            continue
        def key(c):
            cts = pd.Timestamp(c["ts"])
            return (abs(c["atr_decile"] - h["atr_decile"]),
                    abs(c["strength"] - h["strength"]),
                    abs((cts - hts).total_seconds()),
                    c["symbol"], cts)
        best = min(cands, key=key)
        used.add(id(best))
        pairs.append((h, best))
    return pairs, unmatched


# ------------------------------------------------------- inference
def weekly_blocks(pairs, trades):
    """Assign each pair to the HIGH-VOLUME event's calendar week (ISO,
    Monday-start). Returns dict week_key -> list of paired d_k (25bps net R
    differences). Spec ambiguity (reported): week definition not named;
    ISO week chosen."""
    import pandas as pd
    blocks = {}
    for h, c in pairs:
        th = trades[id(h)]["net_r_primary"]
        tc = trades[id(c)]["net_r_primary"]
        d = th - tc
        ts = pd.Timestamp(h["ts"]).tz_convert(TZ)
        wk = f"{ts.isocalendar().year}-W{ts.isocalendar().week:02d}"
        blocks.setdefault(wk, []).append(d)
    return blocks


def sign_flip_pvalue(blocks):
    """Two-sided p-value from 10,000 weekly block sign-flip permutations
    of the mean weekly paired difference."""
    import numpy as np
    rng = np.random.default_rng(SEED)
    sums = np.array([sum(v) for v in blocks.values()], dtype=float)
    if len(sums) == 0:
        return float("nan"), 0
    obs = sums.mean()
    ge = 0
    for _ in range(N_PERM):
        signs = rng.choice([-1.0, 1.0], size=len(sums))
        if abs((sums * signs).mean()) >= abs(obs):
            ge += 1
    return ge / N_PERM, obs


def block_bootstrap_ci(blocks):
    """95% CI for the mean paired advantage from 10,000 weekly block
    bootstraps (resample weeks with replacement), fixed seed 20261004."""
    import numpy as np
    rng = np.random.default_rng(SEED)
    weeks = list(blocks.values())
    if not weeks:
        return (float("nan"), float("nan")), float("nan")
    means = []
    for _ in range(N_BOOT):
        idx = rng.integers(0, len(weeks), size=len(weeks))
        ds = [d for k in idx for d in weeks[k]]
        means.append(sum(ds) / len(ds))
    lo, hi = np.percentile(means, [2.5, 97.5])
    return (float(lo), float(hi)), float(sum(means) / len(means))

# ------------------------------------------------------- gates
def evaluate_gates(pairs, trades):
    """Wire gates G0-G5 exactly per spec. Returns (gates dict, verdict)."""
    import pandas as pd
    g = {}
    n = len(pairs)
    ds_primary = [trades[id(h)]["net_r_primary"] - trades[id(c)]["net_r_primary"]
                  for h, c in pairs]
    ds_diag = [trades[id(h)]["net_r_diag"] - trades[id(c)]["net_r_diag"]
               for h, c in pairs]
    hv_primary = [trades[id(h)]["net_r_primary"] for h, c in pairs]
    ctrl_primary = [trades[id(c)]["net_r_primary"] for h, c in pairs]

    g["G0"] = {"pass": n >= MIN_PAIRS, "n_pairs": n,
               "required": MIN_PAIRS}

    mean_hv = sum(hv_primary) / n if n else float("nan")
    g["G1"] = {"pass": (mean_hv >= ABS_MIN_R) if n else False,
               "mean_hv_primary": mean_hv, "required": ABS_MIN_R}

    mean_d = sum(ds_primary) / n if n else float("nan")
    g["G2"] = {"pass": (mean_d >= INC_MIN_R) if n else False,
               "mean_paired_advantage_primary": mean_d,
               "required": INC_MIN_R}

    blocks = weekly_blocks(pairs, trades)
    pval, obs = sign_flip_pvalue(blocks)
    (lo, hi), boot_mean = block_bootstrap_ci(blocks)
    g["G3"] = {"pass": bool(pval < P_MAX and lo > 0),
               "p_value": pval, "ci_95": [lo, hi], "n_weeks": len(blocks)}

    # Breadth: both sub-periods, >=75 pairs each, HIGH mean > CONTROL mean.
    per = {"Y1": [], "Y2": []}
    for (h, c) in pairs:
        d = pd.Timestamp(h["ts"]).tz_convert(TZ).date().isoformat()
        key = "Y1" if Y1[0] <= d <= Y1[1] else ("Y2" if Y2[0] <= d <= Y2[1] else None)
        if key:
            per[key].append((trades[id(h)]["net_r_primary"],
                             trades[id(c)]["net_r_primary"]))
    yres = {}
    for key in ("Y1", "Y2"):
        nn = len(per[key])
        if nn:
            mh = sum(x[0] for x in per[key]) / nn
            mc = sum(x[1] for x in per[key]) / nn
        else:
            mh, mc = float("nan"), float("nan")
        yres[key] = {"n_pairs": nn, "mean_hv": mh, "mean_ctrl": mc,
                     "hv_gt_ctrl": bool(mh > mc) if nn else False,
                     "count_ok": nn >= MIN_PERIOD_PAIRS}
    breadth_ok = all(yres[k]["hv_gt_ctrl"] and yres[k]["count_ok"]
                     for k in ("Y1", "Y2"))
    g["G4"] = {"pass": breadth_ok, "periods": yres}

    mean_d_diag = sum(ds_diag) / n if n else float("nan")
    g["G5"] = {"pass": bool(mean_d_diag > 0) if n else False,
               "mean_paired_advantage_diag": mean_d_diag}

    if not g["G0"]["pass"] or not all(yres[k]["count_ok"] for k in ("Y1", "Y2")):
        verdict = "INSUFFICIENT"
    elif all(g[k]["pass"] for k in ("G1", "G2", "G3", "G4", "G5")):
        verdict = "PASS"
    else:
        verdict = "FAIL"
    return g, verdict


# ------------------------------------------------------- SPY regime
def make_spy_regime():
    """Prior-trading-day SPY regime: Close_SPY > EMA200_SPY (frozen daily).

    PIT note (reported ambiguity): spec says 'SPY regime at t close'.
    A same-day daily close is not known at a 13:30 4H bar close, so the
    PIT-safe prior trading day is used uniformly for both slots.
    """
    import pandas as pd
    spy_path = os.path.join(REPO, "daily_ranking_frozen_20261004", "d1_SPY.pkl")
    df = pd.read_pickle(spy_path).sort_index()
    ema200 = df["Close"].ewm(span=200, adjust=False).mean()
    regime = (df["Close"] > ema200)
    dates = sorted({ts.tz_convert(TZ).date() for ts in df.index})

    def fn(bar_ts):
        d = bar_ts.tz_convert(TZ).date()
        prior = [x for x in dates if x < d]
        if not prior:
            return None
        return bool(regime.loc[df.index[
            df.index.tz_convert(TZ).date == prior[-1]]].iloc[-1])
    return fn


# ------------------------------------------------------- manifest / verify
def write_manifest(verify_meta, mod_hashes):
    man = {
        "hypothesis": "QF-R2-BRK-VOL-4H-001",
        "spec": "research_notes/qf_r2/qf_r2_brk_vol_4h_prereg_20261004.md",
        "spec_sha256": mod_hashes["qf_r2_brk_vol_4h_prereg_20261004.md"],
        "runner": "research_notes/qf_r2/qf_r2_runner.py",
        "runner_sha256": mod_hashes["qf_r2_runner.py"],
        "fixtures": "research_notes/qf_r2/qf_r2_fixtures.py",
        "fixtures_sha256": mod_hashes["qf_r2_fixtures.py"],
        "input_verification": verify_meta,
        "module_hashes": {k: v for k, v in mod_hashes.items()
                          if k not in ("qf_r2_runner.py", "qf_r2_fixtures.py",
                                       "qf_r2_brk_vol_4h_prereg_20261004.md")},
        "constants": {
            "study_window": [STUDY_START, STUDY_END],
            "volume_threshold": VOLUME_THRESHOLD,
            "baseline_bars": BASELINE_BARS,
            "prior_high_n": PRIOR_HIGH_N,
            "stop_atr_mult": STOP_ATR_MULT, "tp_r": TP_R,
            "max_hold_bars": MAX_HOLD_BARS,
            "cost_bps_primary": COST_PRIMARY_BPS,
            "cost_bps_diag": COST_DIAG_BPS,
            "seed": SEED, "n_perm": N_PERM, "n_boot": N_BOOT,
            "min_pairs": MIN_PAIRS,
        },
        "raw_evidence_paths": [os.path.join("raw_evidence", p)
                               for p in RAW_PATHS],
        "evidence_tier": EVIDENCE_TIER,
        "performance_status": "HELD — no market-performance run executed",
    }
    out = os.path.join(HERE, "qf_r2_manifest.json")
    json.dump(man, open(out, "w"), indent=1)
    # raw_evidence copy of the code/data manifest (empty-performance stub)
    json.dump(man, open(os.path.join(HERE, "raw_evidence",
                                    "code_data_manifest.json"), "w"), indent=1)
    return out


def establish_raw_paths():
    d = os.path.join(HERE, "raw_evidence")
    os.makedirs(d, exist_ok=True)
    for p in RAW_PATHS:
        fp = os.path.join(d, p)
        if not os.path.exists(fp):
            open(fp, "w").close()  # EMPTY until an authorized run fills them
    return d


def cmd_verify():
    symbols, verify_meta = verify_inputs()
    mods = module_hashes()
    man_path = write_manifest(verify_meta, mods)
    raw_d = establish_raw_paths()
    print(json.dumps({
        "mode": "verify",
        "inputs_verified": verify_meta["1h_files_checked"],
        "pool_symbols": verify_meta["1h_pool"],
        "spy_daily_sha256": verify_meta["spy_daily_sha256"][:16],
        "scanner_rules_sha256": mods["scanner_rules.py"][:16],
        "manifest": man_path,
        "raw_evidence_dir": raw_d,
        "performance": "HELD",
    }, indent=1))


def cmd_run():
    if os.environ.get("QF_R2_ALLOW_RUN") != "1":
        print("PERFORMANCE HELD — no market-performance run executed. "
              "Set QF_R2_ALLOW_RUN=1 only after pre-run checks are reviewed "
              "and authorized.")
        sys.exit(2)
    raise NotImplementedError(
        "Performance path not implemented in this preflight package.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.verify:
        cmd_verify()
    elif a.run:
        cmd_run()
    else:
        print("usage: qf_r2_runner.py --verify | --run")
        sys.exit(2)


if __name__ == "__main__":
    main()
