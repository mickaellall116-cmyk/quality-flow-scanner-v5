#!/usr/bin/env python3
"""-25 v2: whole-book Part B per ChatGPT counter-read rulings (1) whole-book
evaluation/assignment, (2) composition test post-exit set vs original-loss set,
plus concurred proposals: winner-side baseline, rule-picked counter-example.
Pinned artifacts only. No bars, no vendor data, no new sims."""
import json, statistics as st
from datetime import datetime
from collections import Counter, defaultdict

LED = json.load(open('/tmp/lifecycle/trade_ledger.json'))
LAB = json.load(open('/home/hatch/workspace/qf_anat_stage/wt/research_notes/'
                     'equity43_dev_winner_anatomy_20261024_23/ordering_labels.json'))['trades']
REG = json.load(open('/tmp/lifecycle/register_lifecycle66.json'))

def dt(s): return datetime.fromisoformat(s.replace('T', ' ')) if s else None
lab = {(t['symbol'], t['entry_time']): t['label'] for t in LAB}
for c in LED:
    c['_lab'] = lab.get((c['symbol'], c['entry_time'][:16])) if c['taken_4bps'] and not c['censored'] else None

taken_closed = [c for c in LED if c['taken_4bps'] and not c['censored']]
s66 = [c for c in taken_closed if c['gross_r'] < -1.0]
winners = [c for c in taken_closed if c['gross_r'] > 0]
assert len(s66) == 66 and len(winners) == 90

by_sym = defaultdict(list)
for c in LED: by_sym[c['symbol']].append(c)
for s in by_sym.values(): s.sort(key=lambda c: c['signal_time'])

def post_exit_set(anchors):
    """Distinct candidates (any symbol of an anchor) with signal_time after at
    least one anchor exit in the same symbol; each assigned to the MOST RECENT
    prior anchor exit in its symbol (single assignment, book-level)."""
    exits_by_sym = defaultdict(list)
    for a in anchors: exits_by_sym[a['symbol']].append(a)
    out = {}
    for sym, cands in by_sym.items():
        if sym not in exits_by_sym: continue
        exs = sorted(exits_by_sym[sym], key=lambda a: a['exit_time'])
        for c in cands:
            prior = [a for a in exs if dt(c['signal_time']) > dt(a['exit_time'])]
            if prior:
                out[(sym, c['signal_time'])] = (c, prior[-1])
    return out

pe66 = post_exit_set(s66)
peW = post_exit_set(winners)
print('=== 258 HUNT ===')
print('distinct post-exit candidates after the 66 (4bps basis):', len(pe66),
      '| taken incl censored:', sum(v[0]['taken_4bps'] for v in pe66.values()),
      '| taken closed:', sum(v[0]['taken_4bps'] and not v[0]['censored'] for v in pe66.values()),
      '| skipped:', sum(not v[0]['taken_4bps'] for v in pe66.values()))
alt = {}
# variant: gross-view 66 set
s66g = [c for c in LED if c['taken_gross'] and not c['censored'] and c['gross_r'] < -1.0]
alt['gross_view_66set_n'] = len(s66g)
exits_g = defaultdict(list)
for a in s66g: exits_g[a['symbol']].append(a)
cnt = 0
for sym, cands in by_sym.items():
    if sym in exits_g:
        first = min(dt(a['exit_time']) for a in exits_g[sym])
        cnt += sum(dt(c['signal_time']) > first for c in cands)
alt['gross_view_post_exit_distinct'] = cnt
# variant: net-basis 67 set
s67 = [c for c in taken_closed if c['net_r_4bps'] < -1.0]
alt['net_view_set_n'] = len(s67)
alt['net_view_post_exit_distinct'] = len(post_exit_set(s67))
# variant: non-strict >= on signal vs exit
cnt2 = 0
exits_66 = defaultdict(list)
for a in s66: exits_66[a['symbol']].append(a)
for sym, cands in by_sym.items():
    if sym in exits_66:
        first = min(dt(a['exit_time']) for a in exits_66[sym])
        cnt2 += sum(dt(c['signal_time']) >= first for c in cands)
alt['nonstrict_post_exit_distinct'] = cnt2
# variant: anchor = exit of ANY taken trade in symbol (not just the 66)
alt['any_taken_anchor_post_exit_distinct'] = len(post_exit_set(taken_closed))
print(json.dumps(alt, indent=1))

def summarize(post, name):
    cs = [v[0] for v in post.values()]
    tk = [c for c in cs if c['taken_4bps'] and not c['censored']]
    sk = [c for c in cs if not c['taken_4bps']]
    cens = [c for c in cs if c['censored']]
    d = {'set': name, 'n_candidates': len(cs), 'n_taken_closed': len(tk), 'n_skipped': len(sk),
         'n_censored': len(cens),
         'taken_gross_sum': round(sum(c['gross_r'] for c in tk), 4),
         'taken_winners': sum(c['gross_r'] > 0 for c in tk),
         'taken_tp1_rate': round(sum(c['tp1_hit'] for c in tk) / len(tk), 3) if tk else None,
         'skipped_standalone_gross_sum': round(sum(c['gross_r'] for c in sk if c['gross_r'] is not None), 4),
         'skipped_tp1_rate_sa': round(sum(c['tp1_hit'] for c in sk) / len(sk), 3) if sk else None,
         'dispositions': dict(Counter(c['disposition_4bps_c1'] for c in cs)),
         'sectors': dict(Counter(c['sector'] for c in cs)),
         'rs_median': round(st.median(c['rs'] for c in cs), 4),
         'reasons_taken': dict(Counter(c['reason'] for c in tk))}
    return d

S = {}
S['post_exit_after_66'] = summarize(pe66, 'post-exit after the 66 (distinct, assigned)')
S['post_exit_after_winners'] = summarize(peW, 'post-exit after winners (distinct, assigned)')
S['original_loss_set_66'] = {'set': 'the 66 (taken closed)', 'n_candidates': 66,
    'dispositions': {'taken': 66},
    'sectors': dict(Counter(c['sector'] for c in s66)),
    'rs_median': round(st.median(c['rs'] for c in s66), 4),
    'tp1_rate': 0.0, 'gross_sum': round(sum(c['gross_r'] for c in s66), 4),
    'reasons': dict(Counter(c['reason'] for c in s66)),
    'hold_median': st.median(c['hold_bars'] for c in s66)}
S['all_candidates_590'] = {'set': 'all candidates', 'n_candidates': 590,
    'dispositions': dict(Counter(c['disposition_4bps_c1'] for c in LED)),
    'sectors': dict(Counter(c['sector'] for c in LED)),
    'rs_median': round(st.median(c['rs'] for c in LED), 4),
    'tp1_rate_sa': round(sum(c['tp1_hit'] for c in LED if not c['censored']) / 586, 3)}
print(json.dumps(S, indent=1, default=str))

# rule-picked counter-example: largest recorded re-entry LOSS after a stop-out
re_losses = sorted([v[0] for v in pe66.values() if v[0]['taken_4bps'] and not v[0]['censored'] and v[0]['gross_r'] < 0],
                   key=lambda c: c['gross_r'])
worst = re_losses[0]
anchor = pe66[(worst['symbol'], worst['signal_time'])][1]
print('\nCOUNTER-EXAMPLE (rule: largest re-entry loss after a stop-out):')
print(json.dumps({'symbol': worst['symbol'], 'signal_time': worst['signal_time'], 'entry_time': worst['entry_time'],
                  'exit_time': worst['exit_time'], 'gross_r': worst['gross_r'], 'reason': worst['reason'],
                  'tp1_hit': worst['tp1_hit'], 'hold_bars': worst['hold_bars'], 'rs': round(worst['rs'], 4),
                  'sector': worst['sector'],
                  'assigned_anchor_66': {'symbol': anchor['symbol'], 'entry_time': anchor['entry_time'],
                                         'exit_time': anchor['exit_time'], 'gross_r': anchor['gross_r']}},
                 indent=1, default=str))
json.dump({'counts_variants': alt, 'summaries': S,
           'counter_example': {'symbol': worst['symbol'], 'signal_time': worst['signal_time'],
                               'gross_r': worst['gross_r'],
                               'anchor_exit': anchor['exit_time'], 'anchor_gross': anchor['gross_r']}},
          open('/tmp/lifecycle/lifecycle_v2_out.json', 'w'), indent=1, default=str)
