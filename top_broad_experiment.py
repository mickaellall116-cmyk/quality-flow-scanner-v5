#!/usr/bin/env python3
"""TOP-50 / BROAD experiment module (System 1).

Frozen experiment logic for the TOP-vs-BROAD comparison. Imported by the
run script (not yet authorized) and by the synthetic test suite.

REPAIR 2026-10-04 (Mike's final source check):
1. Split handling has NO lookahead: the 3-day exclusion applies UNCONDITIONALLY
   to all flagged split events. The earlier "continuity check" used 5 days of
   post-event data to classify events — for a Jun 29 event with a Jun 30
   rebalance, that leaks the future. Removed entirely.
2. The 60-day window is fixed FIRST (last 60 trading days), then split days
   are excluded from within it. No backward backfill: the mean uses the
   remaining 57-60 days. Earlier code did tail(60) after dropping, which
   reached older days to refill to 60.
3. This module (not the test file) is the authoritative implementation.
"""
import numpy as np
import pandas as pd

# Frozen parameters
LIQ_WINDOW = 60          # trading days for dollar-volume mean
LIQ_MIN_VALID = 50      # minimum valid days after exclusions
RS_LOOKBACK = 126       # trading days for RS vs SPY
TOP_N = 50              # TOP selection count
SPLIT_EXCL_HALF = 1     # exclude event day +/-1 (3 trading days)


def compute_top50(dollar_vol, rs_ret, split_dates=None, top_n=TOP_N):
    """Select TOP-N by frozen composite. No lookahead.

    dollar_vol: dict symbol -> Series of daily dollar volume, indexed by
      trading day (ascending). Must contain >= LIQ_WINDOW days.
    rs_ret: dict symbol -> 126-day return vs SPY (float or None).
    split_dates: dict symbol -> list of event dates. The 3 trading days
      centered on each event are excluded from the mean, UNCONDITIONALLY.
      No post-event data is consulted for any decision.
    Returns: (selected list, diagnostics dict)
    """
    rows = []
    for sym, dv in dollar_vol.items():
        # REPAIR 2: fix the 60-day window FIRST from the raw series.
        if len(dv) < LIQ_WINDOW:
            continue
        window = dv.tail(LIQ_WINDOW).copy()
        # REPAIR 1: unconditional exclusion — no continuity classification,
        # no post-event data. All flagged events treated identically.
        for sd in (split_dates or {}).get(sym, []):
            sd = pd.Timestamp(sd).tz_localize(None) if pd.Timestamp(sd).tzinfo else pd.Timestamp(sd)
            widx = window.index.tz_localize(None) if hasattr(window.index, 'tz_localize') else window.index
            # Find trading days within +/-1 calendar day of the event
            try:
                center = widx.get_indexer([sd], method="nearest")[0]
            except Exception:
                continue
            lo = max(0, center - SPLIT_EXCL_HALF)
            hi = min(len(window), center + SPLIT_EXCL_HALF + 1)
            window = window.drop(window.index[lo:hi])
        if len(window) < LIQ_MIN_VALID:
            continue  # excluded, not imputed
        liq = float(window.mean())
        rs = rs_ret.get(sym)
        if rs is None or not np.isfinite(rs) or not np.isfinite(liq):
            continue
        rows.append((sym, liq, rs))
    if len(rows) <= 1:
        return [], {"n_valid": len(rows), "degenerate": True}
    syms = [r[0] for r in rows]
    liqs = np.array([r[1] for r in rows])
    rss = np.array([r[2] for r in rows])

    def pct_rank_best0(vals):
        order = np.argsort(-vals)
        ranks = np.empty(len(vals))
        k = 0
        while k < len(vals):
            j = k
            while j + 1 < len(vals) and vals[order[j + 1]] == vals[order[k]]:
                j += 1
            avg = (k + j) / 2.0
            ranks[order[k:j + 1]] = avg
            k = j + 1
        n = len(vals)
        return ranks / (n - 1) if n > 1 else np.full(n, 0.5)

    composite = 0.5 * pct_rank_best0(liqs) + 0.5 * pct_rank_best0(rss)
    order = np.argsort(composite, kind="stable")
    if len(order) <= top_n:
        selected = [syms[i] for i in order]
        cutoff = None
    else:
        cutoff = composite[order[top_n - 1]]
        selected = [syms[i] for i in order if composite[i] <= cutoff + 1e-12]
    return selected, {"n_valid": len(rows), "degenerate": False, "cutoff": cutoff}


def paired_block_bootstrap(top_trades, broad_trades, month_index,
                           n_resamples=10000, seed=20261004,
                           block_months=3, min_trades=5):
    """Paired moving-block bootstrap for TOP - BROAD expectancy difference.

    top_trades/broad_trades: lists of dicts with 'exit_month' (int index into
      month_index) and 'net_r'. Trades assigned ONCE by exit month.
    month_index: list of month labels (length M).
    Returns dict with CI, point estimate, valid/attempted counts.
    INCONCLUSIVE (not rejection) when discard rate > 10% or no valid draws.
    """
    rng = np.random.default_rng(seed)
    M = len(month_index)
    blocks = [list(range(s, s + block_months))
              for s in range(M - block_months + 1)]

    def by_month(trades):
        d = {}
        for t in trades:
            d.setdefault(t["exit_month"], []).append(t["net_r"])
        return d

    top_by_m = by_month(top_trades)
    broad_by_m = by_month(broad_trades)
    diffs = []
    discarded = 0
    for _ in range(n_resamples):
        months_covered = []
        while len(months_covered) < M:
            b = blocks[rng.integers(len(blocks))]
            months_covered.extend(b)
        months_covered = months_covered[:M]
        t_rs, b_rs = [], []
        for m in months_covered:
            t_rs.extend(top_by_m.get(m, []))
            b_rs.extend(broad_by_m.get(m, []))
        if len(t_rs) < min_trades or len(b_rs) < min_trades:
            discarded += 1
            continue
        diffs.append(np.mean(t_rs) - np.mean(b_rs))
    diffs = np.array(diffs)
    valid = len(diffs)
    if valid == 0:
        return {"valid": 0, "attempted": n_resamples, "discarded": discarded,
                "ci": None, "inconclusive": True}
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    t_all = [t["net_r"] for t in top_trades]
    b_all = [t["net_r"] for t in broad_trades]
    point = np.mean(t_all) - np.mean(b_all) if t_all and b_all else None
    disc_rate = discarded / n_resamples
    return {"valid": valid, "attempted": n_resamples, "discarded": discarded,
            "discard_rate": disc_rate,
            "ci": (float(lo), float(hi)),
            "point": float(point) if point is not None else None,
            "g5_pass": bool(lo > 0),
            "inconclusive": bool(disc_rate > 0.10)}
