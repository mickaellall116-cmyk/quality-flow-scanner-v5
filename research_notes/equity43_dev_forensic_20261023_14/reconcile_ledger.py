#!/usr/bin/env python3
"""QF-EQUITY43-DEV-FORENSIC-20261023-14 — ledger reconciliation + divergence
state reconstruction. OFFLINE, descriptive only. Inputs: the COMMITTED -13
trade_ledger.json + results.json (package 521980a). No market data, no
simulator execution, no performance run: every figure below is regenerated
from the committed candidate ledger and committed reported outputs.
Usage: python3 reconcile_ledger.py <trade_ledger.json> <results.json>
"""
import json, sys
from collections import Counter

led = json.load(open(sys.argv[1]))
res = json.load(open(sys.argv[2]))
out = {}

closed = [r for r in led if not r['censored']]
cens = [r for r in led if r['censored']]
out['rows'] = len(led); out['closed'] = len(closed); out['censored'] = len(cens)
out['censored_symbols'] = sorted(r['symbol'] for r in cens)

def view_stats(taken, rkey):
    t = [r for r in closed if r[taken]]
    wins = [r for r in t if r[rkey] > 0]; losses = [r for r in t if r[rkey] <= 0]
    s = sum(r[rkey] for r in t)
    return {'taken_closed': len(t), 'wins': len(wins), 'sum_r': round(s, 4),
            'avg_r': round(s / len(t), 6),
            'pf': round(sum(r[rkey] for r in wins) / abs(sum(r[rkey] for r in losses)), 6),
            'exit_reasons': dict(Counter(r['reason'] for r in t))}

out['views'] = {'gross': view_stats('taken_gross', 'gross_r'),
                '4bps': view_stats('taken_4bps', 'net_r_4bps'),
                '25bps': view_stats('taken_25bps', 'net_r_25bps')}
out['monotone_violations_closed'] = sum(
    1 for r in closed if not (r['gross_r'] >= r['net_r_4bps'] >= r['net_r_25bps']))

g_only = [r for r in closed if r['taken_gross'] and not r['taken_4bps']]
b_only = [r for r in closed if r['taken_4bps'] and not r['taken_gross']]
common = [r for r in closed if r['taken_gross'] and r['taken_4bps']]
out['set_overlap'] = {
    'common_closed': len(common),
    'common_sum_gross_r': round(sum(r['gross_r'] for r in common), 4),
    'common_sum_4bps_r': round(sum(r['net_r_4bps'] for r in common), 4),
    'gross_only_closed': len(g_only),
    'gross_only_sum_gross_r': round(sum(r['gross_r'] for r in g_only), 4),
    'bps4_only_closed': len(b_only),
    'bps4_only_sum_4bps_r': round(sum(r['net_r_4bps'] for r in b_only), 4)}
out['r_bridge_4bps_minus_gross'] = {
    'friction_on_common': round(out['set_overlap']['common_sum_4bps_r']
                                - out['set_overlap']['common_sum_gross_r'], 4),
    'allocation_effect': round(out['set_overlap']['bps4_only_sum_4bps_r']
                               - out['set_overlap']['gross_only_sum_gross_r'], 4),
    'total': round(out['views']['4bps']['sum_r'] - out['views']['gross']['sum_r'], 4)}

t4 = [r for r in closed if r['taken_4bps']]
top5 = sorted(t4, key=lambda r: -r['net_r_4bps'])[:5]
out['top5_4bps'] = [{'symbol': r['symbol'], 'entry_time': r['entry_time'],
                     'signal_idx': r['signal_idx'], 'net_r_4bps': round(r['net_r_4bps'], 4)}
                    for r in top5]
out['top5_sum'] = round(sum(r['net_r_4bps'] for r in top5), 4)
out['top5_share_pct'] = round(100 * out['top5_sum'] / out['views']['4bps']['sum_r'], 2)
rest = [r for r in t4 if r not in top5]
out['non_top5'] = {'n': len(rest), 'sum_r': round(sum(r['net_r_4bps'] for r in rest), 4)}
out['year_split_4bps'] = {y: {'n': len([r for r in t4 if r['entry_time'].startswith(y)]),
                              'sum_r': round(sum(r['net_r_4bps'] for r in t4
                                                 if r['entry_time'].startswith(y)), 4)}
                          for y in ('2025', '2026')}

# terminal marks + equity decomposition from committed reported outputs
run = res['phases']['P5_run']
out['equity_decomposition'] = {}
for v in ('gross', '4bps', '25bps'):
    inv = run[v]['terminal_open_inventory']
    marks = round(sum(i['unreal_dollars'] for i in inv), 4)
    out['equity_decomposition'][v] = {
        'terminal_open_taken': run[v]['terminal_open_taken_count'],
        'terminal_symbols': [i['symbol'] for i in inv],
        'terminal_marks_sum': marks}
# realized/final at full precision live in results.json phase text; asserted
# against run_stdout in RESULT.md (realized + marks = final per view).

# divergence state reconstruction (ledger-derivable state only)
def opens_before(view, t):
    return [r for r in led if r[view] and r['entry_time'] < t
            and (r['censored'] or (r['exit_time'] and r['exit_time'] > t))]

div = [r for r in led if r['taken_gross'] != r['taken_4bps']]
div.sort(key=lambda r: (r['entry_time'], r['symbol'], r['signal_idx']))
out['first_divergence'] = {'entry_time': div[0]['entry_time'], 'symbol': div[0]['symbol'],
                           'signal_idx': div[0]['signal_idx']}
out['gross4bps_flag_diffs_before_first'] = sum(
    1 for r in led if r['entry_time'] < div[0]['entry_time']
    and r['taken_gross'] != r['taken_4bps'])
events = []
for r in div:
    t = r['entry_time']
    og, ob = opens_before('taken_gross', t), opens_before('taken_4bps', t)
    events.append({
        'entry_time': t, 'symbol': r['symbol'], 'signal_idx': r['signal_idx'],
        'sector': r['sector'], 'rs': round(r['rs'], 4), 'censored': r['censored'],
        'taken_gross': r['taken_gross'], 'taken_4bps': r['taken_4bps'],
        'taken_25bps': r['taken_25bps'], 'disposition_4bps_c1': r['disposition_4bps_c1'],
        'gross_r': r['gross_r'], 'net_r_4bps': r['net_r_4bps'],
        'cohort': [{'symbol': c['symbol'], 'rs': round(c['rs'], 4),
                    'disposition_4bps_c1': c['disposition_4bps_c1']}
                   for c in sorted([c for c in led if c['entry_time'] == t],
                                   key=lambda c: (c['symbol'], c['signal_idx']))],
        'gross_open': [{'symbol': o['symbol'], 'sector': o['sector']} for o in og],
        'bps4_open': [{'symbol': o['symbol'], 'sector': o['sector']} for o in ob],
        'gross_sector_counts': dict(Counter(o['sector'] for o in og)),
        'bps4_sector_counts': dict(Counter(o['sector'] for o in ob))})
out['divergence_events'] = events
print(json.dumps(out, indent=1))
