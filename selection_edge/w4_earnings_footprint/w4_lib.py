"""Shared machinery for W4 selection-edge factors F7/F8.

Strict PIT, 14-name blinding, canonical trade population. Nothing here touches
production or the frozen V5.4 system.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.expanduser("~/workspace/quality-flow-scanner-v5/canonical_baseline")
OUT = os.path.expanduser("~/workspace/quality-flow-scanner-v5/selection_edge/w4_earnings_footprint")
sys.path.insert(0, BASE)
import simlib  # noqa: E402  (read-only reuse of canonical data loaders)

MASK14 = {'QQQ', 'SMCI', 'PLTR', 'ANET', 'SOFI', 'RKLB', 'ONDS', 'DRAM',
          'SPCX', 'ASTX', 'BBAI', 'NIO', 'HOOD', 'AMD'}

COST_KEYS = ['net_r_25bps', 'net_r_50bps', 'net_r_75bps', 'net_r_100bps']
HEADLINE = 'net_r_50bps'

DEV = (pd.Timestamp('2023-10-01', tz='America/New_York'),
       pd.Timestamp('2025-01-01', tz='America/New_York'))   # [start, end)
VAL = (pd.Timestamp('2025-01-01', tz='America/New_York'),
       pd.Timestamp('2026-10-01', tz='America/New_York'))   # [start, end)
WF_WINDOWS = [
    ('2024H2', '2024-07-01', '2025-01-01'),
    ('2025H1', '2025-01-01', '2025-07-01'),
    ('2025H2', '2025-07-01', '2026-01-01'),
    ('2026H1', '2026-01-01', '2026-07-01'),
    ('2026H2+', '2026-07-01', '2026-10-01'),
]


def load_trades():
    """Canonical taken trades, 14 masked. Adds parsed signal timestamps."""
    with open(os.path.join(BASE, 'canonical_trades.json')) as fh:
        trades = json.load(fh)
    out = []
    for t in trades:
        if t['symbol'] in MASK14:
            continue
        t = dict(t)
        t['sig_ts'] = pd.Timestamp(t['signal_bar_close_at'])
        out.append(t)
    return out


def load_universe_working():
    u = simlib.load_universe()
    return [s for s in u if s['symbol'] not in MASK14]


def last_completed_daily_idx(d1_index, sig_ts):
    """Latest daily-bar index whose 16:00 ET close is strictly before sig_ts.

    Daily bars are indexed at 00:00 ET of their trading day; the bar covers
    09:30-16:00 ET. Strictly-prior convention: 16:00:00 signals use the prior
    day's bar (the same-day close is not actionable at the signal instant).
    """
    ref = sig_ts.normalize()  # midnight of signal day
    # daily date < signal date  <=>  its 16:00 close < sig_ts (for sig at/after 00:00)
    pos = d1_index.searchsorted(ref, side='left') - 1
    return pos


def daily_window(sym, sig_ts, n):
    """Last n completed daily bars (strict PIT) + the bar before them.

    Returns (window_df, pre_row) or (None, None) if insufficient history.
    """
    d = simlib.load_d1(sym)
    pos = last_completed_daily_idx(d.index, sig_ts)
    if pos < n:  # need n bars plus one prior bar for day-over-day
        return None, None
    win = d.iloc[pos - n + 1:pos + 1]
    pre = d.iloc[pos - n]
    return win, pre


def f8_balance(sym, sig_ts, n=20):
    """Smart-money day balance over trailing n trading days, strict PIT.

    (frac up-days on above-median volume) - (frac down-days on above-median volume).
    Up/down = day-over-day close move. Median = median volume of the same window.
    Returns float in [-1, 1], or None if insufficient history.
    """
    win, pre = daily_window(sym, sig_ts, n)
    if win is None:
        return None
    closes = np.concatenate([[float(pre['Close'])], win['Close'].to_numpy(float)])
    vols = win['Volume'].to_numpy(float)
    med = float(np.median(vols))
    up = (closes[1:] > closes[:-1]) & (vols > med)
    dn = (closes[1:] < closes[:-1]) & (vols > med)
    return float((up.sum() - dn.sum()) / n)


# ---------------------------------------------------------------------------
# Split statistics + protocol
# ---------------------------------------------------------------------------

def period_mask(trades, start, end):
    s = pd.Timestamp(start, tz='America/New_York')
    e = pd.Timestamp(end, tz='America/New_York')
    return np.array([(s <= t['sig_ts'] < e) for t in trades])


def split_stats(trades, sel, cost_key=HEADLINE):
    """Expectancy split for a boolean selection mask."""
    sel = np.asarray(sel, dtype=bool)
    rs = np.array([t[cost_key] for t in trades])
    r_sel = rs[sel]
    r_uns = rs[~sel]
    def stats(r):
        if len(r) == 0:
            return {'n': 0, 'exp': None, 'winrate': None}
        return {'n': int(len(r)), 'exp': float(r.mean()),
                'winrate': float((r > 0).mean())}
    s, u = stats(r_sel), stats(r_uns)
    delta = (s['exp'] - u['exp']) if (s['n'] and u['n']) else None
    return {
        'n_sel': s['n'], 'n_uns': u['n'],
        'sel_rate': float(sel.mean()),
        'sel_exp': s['exp'], 'uns_exp': u['exp'],
        'sel_winrate': s['winrate'], 'uns_winrate': u['winrate'],
        'delta': delta,
    }


def bootstrap_delta(trades, sel, cost_key=HEADLINE, n_iter=5000, seed=7):
    """P(selected expectancy > unselected expectancy) via resampling."""
    rng = np.random.default_rng(seed)
    sel = np.asarray(sel, dtype=bool)
    rs = np.array([t[cost_key] for t in trades])
    a, b = rs[sel], rs[~sel]
    if len(a) < 2 or len(b) < 2:
        return {'p_pos': None, 'ci95': None, 'n_iter': n_iter}
    da = rng.choice(a, size=(n_iter, len(a)), replace=True).mean(axis=1)
    db = rng.choice(b, size=(n_iter, len(b)), replace=True).mean(axis=1)
    d = da - db
    return {'p_pos': float((d > 0).mean()),
            'ci95': [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
            'mean_delta': float(d.mean()), 'n_iter': n_iter}


def loso_delta(trades, sel, cost_key=HEADLINE):
    """Leave-one-symbol-out: recompute full-period delta dropping each symbol."""
    sel = np.asarray(sel, dtype=bool)
    syms = sorted(set(t['symbol'] for t in trades))
    out = []
    for s in syms:
        keep = np.array([t['symbol'] != s for t in trades])
        st = split_stats([t for t, k in zip(trades, keep) if k],
                         sel[keep], cost_key)
        out.append({'drop': s, 'delta': st['delta'],
                    'n_sel': st['n_sel'], 'n_uns': st['n_uns']})
    deltas = [o['delta'] for o in out if o['delta'] is not None]
    return {'per_symbol': out,
            'min_delta': float(min(deltas)) if deltas else None,
            'max_delta': float(max(deltas)) if deltas else None,
            'frac_positive': float(np.mean([d > 0 for d in deltas])) if deltas else None}


def concentration(trades, sel, cost_key=HEADLINE):
    """Per-symbol contribution to the selected-group total R."""
    sel = np.asarray(sel, dtype=bool)
    tot = {}
    for t, s in zip(trades, sel):
        if s:
            tot[t['symbol']] = tot.get(t['symbol'], 0.0) + t[cost_key]
    ranked = sorted(tot.items(), key=lambda kv: -kv[1])
    total = sum(tot.values())
    cum = 0.0
    top = []
    for sym, r in ranked[:5]:
        cum += r
        top.append({'symbol': sym, 'r_sum': round(r, 3),
                    'share_of_selected_total': round(r / total, 3) if total else None,
                    'cum_share_topk': round(cum / total, 3) if total else None})
    # delta after removing top contributors from the selected group
    ex = {}
    for k in (1, 3, 5):
        drop = set(sym for sym, _ in ranked[:k])
        keep = np.array([not (s and t['symbol'] in drop)
                         for t, s in zip(trades, sel)])
        st = split_stats([t for t, kk in zip(trades, keep) if kk],
                         sel[keep], cost_key)
        ex[f'ex_top{k}'] = {'delta': st['delta'], 'n_sel': st['n_sel']}
    return {'top5': top, 'selected_total_r': round(total, 3), 'ex_top': ex}


def full_protocol(trades, sel, label, cost_key=HEADLINE):
    """All splits + bootstrap + LOSO + concentration for one selection."""
    res = {'label': label, 'cost': cost_key}
    res['full'] = split_stats(trades, sel, cost_key)
    res['dev'] = split_stats([t for t, m in zip(trades, period_mask(trades, *DEV)) if m],
                             np.asarray(sel)[period_mask(trades, *DEV)], cost_key)
    res['val'] = split_stats([t for t, m in zip(trades, period_mask(trades, *VAL)) if m],
                             np.asarray(sel)[period_mask(trades, *VAL)], cost_key)
    res['years'] = {}
    for y in (2024, 2025, 2026):
        m = period_mask(trades, f'{y}-01-01', f'{y+1}-01-01')
        sub = [t for t, mm in zip(trades, m) if mm]
        res['years'][str(y)] = split_stats(sub, np.asarray(sel)[m], cost_key)
    res['walkforward'] = {}
    for name, s, e in WF_WINDOWS:
        m = period_mask(trades, s, e)
        sub = [t for t, mm in zip(trades, m) if mm]
        res['walkforward'][name] = split_stats(sub, np.asarray(sel)[m], cost_key)
    res['bootstrap'] = bootstrap_delta(trades, sel, cost_key)
    res['loso'] = loso_delta(trades, sel, cost_key)
    res['concentration'] = concentration(trades, sel, cost_key)
    return res


def cost_ladder(trades, sel, label):
    out = {'label': label}
    for ck in COST_KEYS:
        out[ck] = split_stats(trades, sel, ck)
    return out


def save_json(name, obj):
    with open(os.path.join(OUT, name), 'w') as fh:
        json.dump(obj, fh, indent=1)
    print(f'wrote {name}', flush=True)
