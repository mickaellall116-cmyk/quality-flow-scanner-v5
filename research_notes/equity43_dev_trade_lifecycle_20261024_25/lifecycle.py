#!/usr/bin/env python3
"""-25 trade-lifecycle investigation: derived ONLY from pinned artifacts.
Inputs: -13 trade_ledger.json (sha 267e794c...), -23 ordering_labels.json,
-24 register66.json + forensics_out.json. No bars, no vendor data, no sims."""
import json, statistics as st
from datetime import datetime, timezone
from collections import Counter, defaultdict

LED = json.load(open('/tmp/lifecycle/trade_ledger.json'))
LAB = json.load(open('/home/hatch/workspace/qf_anat_stage/wt/research_notes/'
                     'equity43_dev_winner_anatomy_20261024_23/ordering_labels.json'))['trades']
REG24 = json.load(open('/tmp/lifecycle/register66.json'))
FO = json.load(open('/tmp/lifecycle/forensics_out.json'))

def dt(s):
    return datetime.fromisoformat(s.replace('T', ' ')) if s else None

lab = {(t['symbol'], t['entry_time']): t['label'] for t in LAB}
for c in LED:
    c['_lab'] = lab.get((c['symbol'], c['entry_time'][:16])) if c['taken_4bps'] and not c['censored'] else None

taken_closed = [c for c in LED if c['taken_4bps'] and not c['censored']]
winners = [c for c in taken_closed if c['gross_r'] > 0]
losers = [c for c in taken_closed if c['gross_r'] < 0]
s66 = sorted([c for c in taken_closed if c['gross_r'] < -1.0], key=lambda c: c['gross_r'])
ordinary = [c for c in losers if c['gross_r'] >= -1.0]
assert len(taken_closed) == 187 and len(winners) == 90 and len(losers) == 97
assert len(s66) == 66 and len(ordinary) == 31, (len(s66), len(ordinary))

# cross-check the 66 against the -24 register (symbol + entry date + gross)
reg_keys = {(r['symbol'], r['entry']) for r in REG24}
my_keys = {(c['symbol'], c['entry_time'][:10]) for c in s66}
assert reg_keys == my_keys, (reg_keys ^ my_keys)
reg_gross = {(r['symbol'], r['entry']): r['gross'] for r in REG24}
max_dev = max(abs(reg_gross[(c['symbol'], c['entry_time'][:10])] - c['gross_r']) for c in s66)

out = {'population': {
    'candidates': len(LED),
    'skipped': Counter(c['disposition_4bps_c1'] for c in LED if not c['taken_4bps']),
    'taken': sum(c['taken_4bps'] for c in LED),
    'taken_closed': len(taken_closed),
    'censored': sum(c['censored'] for c in LED),
    'censored_symbols': sorted(c['symbol'] for c in LED if c['censored']),
    'censored_all_taken': all(c['taken_4bps'] for c in LED if c['censored']),
    'winners': len(winners), 'losers': len(losers), 's66': len(s66), 'ordinary_losers': len(ordinary),
    'reg66_crosscheck_max_gross_dev': round(max_dev, 6),
    's66_gross_sum': round(sum(c['gross_r'] for c in s66), 4),
}}

# ---------- PART A item 2: decomposition of the 64 stop-route ----------
stop64 = [c for c in s66 if c['reason'] == 'stop']
ema2 = [c for c in s66 if c['reason'] != 'stop']
assert len(stop64) == 64 and len(ema2) == 2, (len(stop64), len(ema2))
ident_err = 0.0
rows = []
for c in stop64:
    over = -1.0 - c['gross_r']                      # excess loss beyond planned -1R
    dist = (c['stop'] - c['exit_synth']) / (c['entry'] - c['stop'])  # fill below stop, in R
    ident_err = max(ident_err, abs(over - dist))
    rows.append({'symbol': c['symbol'], 'entry_time': c['entry_time'], 'gross_r': c['gross_r'],
                 'overshoot_R': round(over, 4), 'label': c['_lab'], 'hold_bars': c['hold_bars']})
out['decomp64'] = {
    'n': 64, 'planned_R_each': -1.0, 'planned_sum': -64.0,
    'gross_sum': round(sum(c['gross_r'] for c in stop64), 4),
    'overshoot_sum': round(sum(r['overshoot_R'] for r in rows), 4),
    'overshoot_median': round(st.median(r['overshoot_R'] for r in rows), 4),
    'overshoot_max': round(max(r['overshoot_R'] for r in rows), 4),
    'fill_below_stop_identity_max_err': round(ident_err, 8),
    'all_tp1_hit_false': all(not c['tp1_hit'] for c in stop64),
    'labels': Counter(c['_lab'] for c in stop64),
}
out['ema2'] = [{'symbol': c['symbol'], 'entry_time': c['entry_time'], 'exit_time': c['exit_time'],
                'reason': c['reason'], 'gross_r': c['gross_r'], 'hold_bars': c['hold_bars'],
                'tp1_hit': c['tp1_hit'], 'label': c['_lab'], 'rs': round(c['rs'], 4),
                'sector': c['sector'],
                'fill_vs_stop_R': round((c['exit_synth'] - c['stop']) / (c['entry'] - c['stop']), 4)}
               for c in ema2]

# ---------- PART A item 4: time-to-failure + threshold excursions ----------
def holdstats(s):
    h = sorted(c['hold_bars'] for c in s)
    return {'n': len(s), 'median': st.median(h), 'min': h[0], 'max': h[-1],
            'le2': sum(x <= 2 for x in h), 'le4': sum(x <= 4 for x in h), 'le10': sum(x <= 10 for x in h)}
def ended_by(s, hs=(2, 4, 10, 20, 30)):
    return {f'by_{h}': round(sum(c['hold_bars'] <= h for c in s) / len(s), 3) for h in hs}
def thresh(s):
    return {'n': len(s),
            'tp1_reached': sum(c['tp1_hit'] for c in s),
            'stop_first_label': sum(c['_lab'] == 'CONFIRMED_STOP_FIRST' for c in s),
            'tp1_first_label': sum(c['_lab'] == 'CONFIRMED_TP1_FIRST' for c in s),
            'sim_assumed_label': sum(c['_lab'] == 'SIMULATOR_ASSUMED' for c in s),
            'breach_then_tp1': sum(c['_lab'] == 'CONFIRMED_STOP_FIRST' and c['tp1_hit'] for c in s)}
out['time_to_failure'] = {'s66': holdstats(s66), 'ordinary': holdstats(ordinary),
                          'winners': holdstats(winners),
                          'ended_by_s66': ended_by(s66), 'ended_by_ordinary': ended_by(ordinary),
                          'ended_by_winners': ended_by(winners)}
out['threshold_excursions'] = {'s66': thresh(s66), 'ordinary': thresh(ordinary), 'winners': thresh(winners)}

# ---------- PART A item 5: top-5 labels ----------
top5 = sorted(taken_closed, key=lambda c: -c['gross_r'])[:5]
out['top5'] = [{'symbol': c['symbol'], 'gross_r': c['gross_r'], 'net_r_4bps': c['net_r_4bps'],
                'entry_time': c['entry_time'], 'label': c['_lab'], 'tp1_hit': c['tp1_hit'],
                'reason': c['reason'], 'hold_bars': c['hold_bars']} for c in top5]
breach_recovery = [c for c in taken_closed if c['_lab'] == 'CONFIRMED_STOP_FIRST' and c['gross_r'] > 0]
out['breach_set_recovery'] = {'n_positive_of_87': len(breach_recovery),
    'ge_2R': [{'symbol': c['symbol'], 'gross_r': c['gross_r'], 'net_r_4bps': c['net_r_4bps'],
               'entry_time': c['entry_time']} for c in breach_recovery if c['net_r_4bps'] >= 2.0]}

# ---------- PART B: post-exit lifecycle per the 66 ----------
by_sym = defaultdict(list)
for c in LED:
    by_sym[c['symbol']].append(c)
for s in by_sym.values():
    s.sort(key=lambda c: c['signal_time'])
dev_end = max(dt(c['signal_time']) for c in LED)
out['dev_last_signal'] = str(dev_end)

register = []
agg = Counter(); sub_taken_R = []; sub_taken_n = 0; sub_win = 0
skipped_sa_R = []
for c in s66:
    xt = dt(c['exit_time'])
    subs = [s for s in by_sym[c['symbol']] if dt(s['signal_time']) > xt]
    follow_days = (dev_end - xt).days
    sub_list = []
    for s in subs:
        sub_list.append({'signal_time': s['signal_time'], 'days_after_exit': (dt(s['signal_time']) - xt).days,
                         'disposition': s['disposition_4bps_c1'], 'taken': bool(s['taken_4bps']),
                         'reason': s['reason'], 'standalone_gross_r': s['gross_r'],
                         'censored': s['censored'], 'hold_bars': s['hold_bars'], 'tp1_hit': s['tp1_hit']})
        if s['taken_4bps'] and not s['censored']:
            sub_taken_n += 1; sub_taken_R.append(s['gross_r']); sub_win += s['gross_r'] > 0
        elif not s['taken_4bps'] and s['gross_r'] is not None:
            skipped_sa_R.append(s['gross_r'])
    agg['with_any_subsequent'] += bool(subs)
    agg['with_subsequent_taken'] += any(s['taken'] for s in sub_list)
    agg['no_subsequent'] += not subs
    agg['no_subsequent_follow_ge_180d'] += (not subs and follow_days >= 180)
    agg['no_subsequent_follow_lt_180d'] += (not subs and follow_days < 180)
    register.append({'symbol': c['symbol'], 'sector': c['sector'], 'signal_time': c['signal_time'],
        'entry_time': c['entry_time'], 'entry': c['entry'], 'stop': c['stop'], 'tp1': c['tp1'],
        'tp1_hit': c['tp1_hit'], 'rs': round(c['rs'], 4), 'exit_time': c['exit_time'],
        'exit_synth': c['exit_synth'], 'reason': c['reason'], 'hold_bars': c['hold_bars'],
        'gross_r': c['gross_r'], 'net_r_4bps': c['net_r_4bps'], 'ordering_label': c['_lab'],
        'planned_R': -1.0,
        'overshoot_R': round(-1.0 - c['gross_r'], 4) if c['reason'] == 'stop' else None,
        'overshoot_note': ('fill-below-threshold combined (trigger excursion + gap split NOT_RECOVERABLE)'
                           if c['reason'] == 'stop' else 'EMA55 route: stop threshold not the exit trigger'),
        'followup_days_to_dev_end': follow_days,
        'subsequent_candidates': sub_list,
        'subsequent_summary': {'n': len(sub_list),
                               'n_taken': sum(s['taken'] for s in sub_list),
                               'n_skipped': sum(not s['taken'] for s in sub_list),
                               'taken_gross_sum': round(sum(s['standalone_gross_r'] for s in sub_list if s['taken'] and s['standalone_gross_r'] is not None), 4),
                               'skipped_standalone_gross_sum': round(sum(s['standalone_gross_r'] for s in sub_list if not s['taken'] and s['standalone_gross_r'] is not None), 4)}})
out['partB_agg'] = dict(agg)
out['partB_agg'].update({'subsequent_taken_trades': sub_taken_n,
                         'subsequent_taken_gross_sum': round(sum(sub_taken_R), 4),
                         'subsequent_taken_winners': sub_win,
                         'subsequent_skipped_candidates': len(skipped_sa_R),
                         'subsequent_skipped_standalone_gross_sum': round(sum(skipped_sa_R), 4)})
json.dump(out, open('/tmp/lifecycle/lifecycle_out.json', 'w'), indent=1)
json.dump(register, open('/tmp/lifecycle/register_lifecycle66.json', 'w'), indent=1)
print(json.dumps(out, indent=1, default=str))
print('register rows:', len(register))
