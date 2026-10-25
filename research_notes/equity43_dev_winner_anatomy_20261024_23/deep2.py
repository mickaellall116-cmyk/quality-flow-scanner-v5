import json, os
from collections import Counter, defaultdict
from datetime import datetime

BASE = os.path.expanduser('~/workspace/qf_td13_stage/archive_clone/captures')
NS = ['td_capture_equity39_continue_20261023', 'td_pilot_20261023']

def load_rows(sym):
    for ns in NS:
        p = os.path.join(BASE, ns, 'raw', f'{sym}__DEV.json')
        if os.path.exists(p):
            raw = json.load(open(p))
            return raw['values'], ns
    return None, None

def build_4h(rows):
    # rows: TD 1h values, datetime 'YYYY-MM-DD HH:MM:SS'
    bins = {}
    for r in rows:
        dt = r['datetime']
        date, hm = dt[:10], dt[11:16]
        if hm in ('09:30','10:30','11:30','12:30'): b = '09:30'
        elif hm in ('13:30','14:30','15:30'): b = '13:30'
        else: continue
        key = (date, b)
        bins.setdefault(key, []).append((hm, float(r['open']), float(r['high']), float(r['low']), float(r['close'])))
    bars = {}
    sub = {}
    for (date, b), parts in bins.items():
        parts.sort()
        if parts[0][0] != b: continue
        bars[f'{date} {b}'] = {'Open': parts[0][1], 'High': max(p[2] for p in parts),
                               'Low': min(p[3] for p in parts), 'Close': parts[-1][4]}
        sub[f'{date} {b}'] = parts
    return bars, sub

d = json.load(open('/tmp/anat/trade_ledger.json'))
taken = [r for r in d if r['taken_4bps']]
syms = sorted(set(r['symbol'] for r in taken))
frames, subs, srcns = {}, {}, {}
for s in syms:
    rows, ns = load_rows(s)
    assert rows, s
    frames[s], subs[s] = build_4h(rows)
    srcns[s] = ns
print('symbols:', len(syms), 'bar counts:', {s: len(frames[s]) for s in syms[:6]}, '...')

# verification: entry bar Open == ledger entry for all 191 taken
ok = bad = 0; badex = []
for r in taken:
    key = r['entry_time'][:16].replace('T', ' ')
    bar = frames[r['symbol']].get(key)
    if bar and abs(bar['Open'] - r['entry']) < 1e-9: ok += 1
    else: bad += 1; badex.append((r['symbol'], key, r['entry'], None if not bar else bar['Open']))
print(f'ENTRY-OPEN verification: {ok} match / {bad} mismatch of {len(taken)}')
for b in badex[:5]: print('  MISS:', b)

closed = [r for r in taken if not r['censored']]
res = Counter(); undetermined_4h = []; undetermined_1h = []; sim_samebar = []; pre_breach = []
for r in closed:
    bars = frames[r['symbol']]; sub = subs[r['symbol']]
    keys = sorted(bars.keys())
    ek = r['entry_time'][:16].replace('T', ' ')
    xk = str(r['exit_time'])[:16].replace('T', ' ')
    if ek not in bars or xk not in bars: res['bar_missing'] += 1; continue
    ei, xi = keys.index(ek), keys.index(xk)
    path = keys[ei:xi]  # entry bar .. exit-decision bar (exit fills at open of xk)
    tp_touch = None
    for k in path:
        if bars[k]['High'] >= r['tp1']: tp_touch = k; break
    if r['tp1_hit'] and tp_touch is None: res['tp1_bar_not_found'] += 1; continue
    if not r['tp1_hit'] and tp_touch is not None: res['tp1_flag_mismatch'] += 1; continue
    pre = path[:path.index(tp_touch)] if tp_touch else path
    if any(bars[k]['Low'] <= r['stop'] for k in pre): res['intrabar_stop_breach_pre_tp1'] += 1; pre_breach.append((r['symbol'], ek))
    if tp_touch:
        if bars[tp_touch]['Low'] <= r['stop']:
            res['dual_touch_same_4h_bar'] += 1; undetermined_4h.append((r['symbol'], ek, tp_touch))
            # 1h grain ordering inside the touch bar
            parts = sub[tp_touch]
            first_tp = next((p for p in parts if p[2] >= r['tp1']), None)
            first_st = next((p for p in parts if p[3] <= r['stop']), None)
            if first_tp and first_st:
                if first_tp[0] < first_st[0]: res['dual_resolved_1h_tp1_first'] += 1
                elif first_st[0] < first_tp[0]: res['dual_resolved_1h_stop_first'] += 1
                else: res['dual_undetermined_1h'] += 1; undetermined_1h.append((r['symbol'], ek, tp_touch))
        if tp_touch == path[-1] and r['reason'] == 'stop': res['sim_tp1_and_exit_same_bar'] += 1; sim_samebar.append((r['symbol'], ek))
    res['trades_walked'] += 1

print('\nINTRABAR CENSUS (187 taken closed):')
for k, v in sorted(res.items()): print(f'  {k}: {v}')
print(' dual-touch 4h bars:', undetermined_4h[:10])
print(' undetermined 1h:', undetermined_1h[:10])
print(' pre-TP1 intrabar stop breaches (symbols):', [x[0] for x in pre_breach])
json.dump({'counts': dict(res), 'dual4h': undetermined_4h, 'und1h': undetermined_1h,
           'pre_breach': pre_breach, 'sim_samebar': sim_samebar},
          open('/tmp/anat/intrabar.json', 'w'), indent=1)
