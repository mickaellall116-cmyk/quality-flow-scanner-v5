#!/usr/bin/env python3
"""Register v2 for -25: v1 evidence rows + (proposal 2) one named missing-record
field per UNKNOWN, bound to the telemetry spec; (ruling 1) each subsequent
candidate carries its single whole-book assignment anchor (most recent prior
66-exit in its symbol). Evidence fields only; no prevention scoring."""
import json
from datetime import datetime
from collections import defaultdict

LED = json.load(open('/tmp/lifecycle/trade_ledger.json'))
V1 = json.load(open('/tmp/lifecycle/register_lifecycle66.json'))
def dt(s): return datetime.fromisoformat(s.replace('T', ' ')) if s else None

s66 = [c for c in LED if c['taken_4bps'] and not c['censored'] and c['gross_r'] < -1.0]
exits_by_sym = defaultdict(list)
for a in s66: exits_by_sym[a['symbol']].append(a)
for v in exits_by_sym.values(): v.sort(key=lambda a: a['exit_time'])
cand = {(c['symbol'], c['signal_time']): c for c in LED}

MISSING = {
 'unknown_overshoot_split': {
   'status': 'UNKNOWN',
   'missing_record': 'exit-decision-bar OHLC (the trigger bar Close)',
   'telemetry_spec_key': 'T3_exit_decision_bar_close'},
 'unknown_signal_state_at_fire': {
   'status': 'UNKNOWN',
   'missing_record': 'full indicator state at signal fire (ADX/DI, trendScore, VWAP distance, rel-vol, EMA geometry, gate reasons) — only rs was persisted',
   'telemetry_spec_key': 'T1_signal_state_at_fire'},
 'unknown_intrabar_excursion': {
   'status': 'UNKNOWN',
   'missing_record': 'bar-level path of the trade (per-bar Low/High sequence vs stop/TP1 thresholds; MAE/MFE, duration under threshold)',
   'telemetry_spec_key': 'T4_bar_path_threshold_events'},
 'unknown_fill': {
   'status': 'UNKNOWN',
   'missing_record': 'any executable fill record (order/ack/fill) — none exists; all outcomes are simulator semantics',
   'telemetry_spec_key': 'T6_execution_records'},
}

out = []
for r in V1:
    row = dict(r)
    subs = []
    for s in r['subsequent_candidates']:
        c = cand[(r['symbol'], s['signal_time'])]
        prior = [a for a in exits_by_sym[r['symbol']] if dt(c['signal_time']) > dt(a['exit_time'])]
        s2 = dict(s)
        s2['assigned_anchor_66_entry_time'] = prior[-1]['entry_time'] if prior else None
        subs.append(s2)
    row['subsequent_candidates'] = subs
    row['unknowns'] = MISSING
    out.append(row)
json.dump(out, open('/tmp/lifecycle/register_lifecycle66_v2.json', 'w'), indent=1)
print('rows:', len(out), '| all 66/66:', len(out) == 66)
print('subsequent entries total (per-row views):', sum(len(r['subsequent_candidates']) for r in out))
