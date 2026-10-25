"""-23 closeout supplement computations.
Evidence: pinned -13 trade_ledger.json (sha256 267e794c...) + memo S5 intrabar
artifact (/tmp/anat/intrabar.json, deep2.py output). Ledger/source-derived only.
No vendor bars are read by this script."""
import json
from collections import Counter, defaultdict

led = json.load(open('/tmp/anat/trade_ledger.json'))
intra = json.load(open('/tmp/anat/intrabar.json'))

taken = [r for r in led if r['taken_4bps']]
censored = [r for r in taken if r['censored']]
closed = [r for r in taken if not r['censored']]
assert len(led) == 590 and len(taken) == 191 and len(closed) == 187, (len(led), len(taken), len(closed))

def key(r):
    return (r['symbol'], r['entry_time'][:16].replace('T', ' '))

breach_keys = {tuple(x) for x in intra['pre_breach']}
assert len(breach_keys) == 87
breach = [r for r in closed if key(r) in breach_keys]
nonbreach = [r for r in closed if key(r) not in breach_keys]
assert len(breach) == 87 and len(nonbreach) == 100

def s(rows, f):
    return round(sum(f(r) for r in rows), 4)

out = {}

# ---------- Point 5: arithmetic validation ----------
out['p5'] = {
    'breach_n': len(breach), 'breach_net': s(breach, lambda r: r['net_r_4bps']),
    'breach_gross': s(breach, lambda r: r['gross_r']),
    'nonbreach_n': len(nonbreach), 'nonbreach_net': s(nonbreach, lambda r: r['net_r_4bps']),
    'total_net_187': s(closed, lambda r: r['net_r_4bps']),
    'total_gross_187': s(closed, lambda r: r['gross_r']),
    'never_tp1_n': sum(1 for r in closed if not r['tp1_hit']),
    'never_tp1_all_gross_neg': all(r['gross_r'] < 0 for r in closed if not r['tp1_hit']),
    'never_tp1_all_net_neg': all(r['net_r_4bps'] < 0 for r in closed if not r['tp1_hit']),
    'gross_losers': sum(1 for r in closed if r['gross_r'] < 0),
    'net_losers': sum(1 for r in closed if r['net_r_4bps'] < 0),
    'net_positives': sum(1 for r in closed if r['net_r_4bps'] > 0),
    'tp1_and_net_neg': sum(1 for r in closed if r['tp1_hit'] and r['net_r_4bps'] < 0),
    'tp1_and_gross_neg': sum(1 for r in closed if r['tp1_hit'] and r['gross_r'] < 0),
    'tp1_reached': sum(1 for r in closed if r['tp1_hit']),
    'censored_symbols': sorted(r['symbol'] for r in censored),
    'censored_all_taken': all(r['disposition_4bps_c1'] == 'taken' for r in censored),
    'worst_gross': min(r['gross_r'] for r in closed),
    'gross_below_minus1': sum(1 for r in closed if r['gross_r'] < -1.0),
    'gross_below_minus1p1': sum(1 for r in closed if r['gross_r'] < -1.1),
}

# ---------- Point 2: the 87 breaches ----------
def split(rows):
    return {
        'n': len(rows),
        'tp1_reached': sum(1 for r in rows if r['tp1_hit']),
        'tp1_never': sum(1 for r in rows if not r['tp1_hit']),
        'gross_pos': sum(1 for r in rows if r['gross_r'] > 0),
        'gross_neg': sum(1 for r in rows if r['gross_r'] < 0),
        'net_pos': sum(1 for r in rows if r['net_r_4bps'] > 0),
        'net': s(rows, lambda r: r['net_r_4bps']),
        'ge_2R_net': sum(1 for r in rows if r['net_r_4bps'] >= 2.0),
        'by_reason': dict(Counter(r['reason'] for r in rows)),
    }
out['p2_breach'] = split(breach)
out['p2_breach_tp1'] = split([r for r in breach if r['tp1_hit']])
out['p2_breach_notp1'] = split([r for r in breach if not r['tp1_hit']])
out['p2_nonbreach'] = split(nonbreach)
out['p2_recoveries'] = sorted(
    [(r['symbol'], r['entry_time'][:10], r['tp1_hit'], round(r['net_r_4bps'], 4))
     for r in breach if r['net_r_4bps'] > 0], key=lambda x: -x[3])

# ---------- Point 3: the 66 losses below -1R (gross) ----------
sub = [r for r in closed if r['gross_r'] < -1.0]
assert len(sub) == 66, len(sub)
mech = {}
for reason in sorted(set(r['reason'] for r in sub)):
    for tp in (False, True):
        rows = [r for r in sub if r['reason'] == reason and r['tp1_hit'] == tp]
        if rows:
            mech[f'{reason}|tp1={tp}'] = {
                'n': len(rows), 'gross_sum': s(rows, lambda r: r['gross_r']),
                'excess_beyond_-1R': round(sum(-1.0 - r['gross_r'] for r in rows), 4),
                'worst': min(r['gross_r'] for r in rows)}
out['p3_mechanisms'] = mech
# for no-TP1 stop exits the fill IS exit_synth: overshoot of fill below stop, in R
ov = []
for r in sub:
    if r['reason'] == 'stop' and not r['tp1_hit']:
        risk = r['entry'] - r['stop']
        ov.append(((r['stop'] - r['exit_synth']) / risk, r))
out['p3_stop_notp1_fill_below_stop'] = {
    'n': len(ov),
    'all_fills_below_stop': all(x[0] > 0 for x in ov),
    'overshoot_R_sum': round(sum(x[0] for x in ov), 4),
    'overshoot_R_median': round(sorted(x[0] for x in ov)[len(ov) // 2], 4),
    'overshoot_R_max': round(max(x[0] for x in ov), 4)}
# ema55-route members of the 66: trigger is the trend condition, not the stop
ema = [r for r in sub if r['reason'] != 'stop']
out['p3_nonstop_route'] = {
    'n': len(ema), 'reasons': dict(Counter(r['reason'] for r in ema)),
    'tp1_among': sum(1 for r in ema if r['tp1_hit']),
    'gross_sum': s(ema, lambda r: r['gross_r'])}
# losers between -1R and 0 (context denominator)
out['p3_losers_minus1_to_0'] = sum(1 for r in closed if -1.0 <= r['gross_r'] < 0)

# ---------- Point 6: ordering classification census ----------
labels = {}
for r in closed:
    if key(r) in breach_keys:
        lab = 'CONFIRMED_STOP_FIRST'
    elif r['tp1_hit']:
        lab = 'CONFIRMED_TP1_FIRST'
    else:
        lab = 'SIMULATOR_ASSUMED'
    labels.setdefault(lab, []).append((r['symbol'], r['entry_time'][:16], r['signal_idx'],
                                       r['tp1_hit'], r['reason'], round(r['net_r_4bps'], 4)))
out['p6_census'] = {k: len(v) for k, v in labels.items()}
out['p6_census']['SAME_BAR_AMBIGUOUS'] = len(intra['dual4h'])
out['p6_census']['INSUFFICIENT_EVIDENCE'] = len(intra['und1h']) + (187 - intra['counts']['trades_walked'])
out['p6_tp1_first_net'] = round(sum(x[5] for x in labels.get('CONFIRMED_TP1_FIRST', [])), 4)
out['p6_sim_assumed_net'] = round(sum(x[5] for x in labels.get('SIMULATOR_ASSUMED', [])), 4)
out['p6_sim_assumed_all_neg'] = all(x[5] < 0 for x in labels.get('SIMULATOR_ASSUMED', []))

json.dump({'summary': out, 'labels': {k: v for k, v in labels.items()}},
          open('/tmp/anat/supplement_out.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
