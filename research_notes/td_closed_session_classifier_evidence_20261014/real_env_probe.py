"""Real-environment fail-closed probe for -17. NO stubs anywhere: real
collector (candidate worktree), real pilot_harness deps (rate_limiter,
verify_sources, validate_input), real SPOT8 requests REQ-SPT-07/08, real
candidate supplement (probe-local copy with base_manifest_digest recomputed
for the 2-request probe manifest -- the only deviation, disclosed here).
Transport is stubbed only at the vendor boundary (constructor injection, the
same boundary every offline run uses). Expectation: pandas_market_calendars
is ABSENT in this environment -> classification disabled -> the exact SPT-07
payload fails closed to the pre-existing HOLD path; SPT-08 never dispatched.
"""
import importlib.util, json, pathlib, sys, tempfile
WT = pathlib.Path('/tmp/td17_wt/research_notes')
spec = importlib.util.spec_from_file_location('realcoll', WT / 'td_lifecycle_repair_candidate' / 'td_min_collector.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
out = {}
# Probe 1: the pinned mechanism itself in this environment
try:
    import pandas as pd
    from validate_input import xnys_schedule
    xnys_schedule(pd.Timestamp('2026-07-03'))
    out['mechanism_probe'] = 'xnys_schedule RAN (unexpected in this env)'
except Exception as e:
    out['mechanism_probe'] = f'{type(e).__name__}: {e}'
# Probe 2: end-to-end collector run with real deps
man_full = json.loads((WT / 'td_acquisition_adapter_preflight_evidence_20261013' / 'acquisition_manifest_v2_spot8.json').read_text())
reqs = [r for r in man_full['requests'] if r['request_id'] in ('REQ-SPT-07', 'REQ-SPT-08')]
man = {'endpoint': man_full['endpoint'], 'requests': reqs}
sup = json.loads((WT / 'td_lifecycle_repair_candidate' / 'p2_spot_supplement_v2.json').read_text())
sup['base_manifest_digest'] = mod.canonical_digest(man)  # probe-manifest binding only
EXACT = (b'{"code":400,"message":"No data is available on the specified dates. '
         b'Try setting different start/end dates.","status":"error",'
         b'"meta":{"symbol":"AAPL","interval":"1h","exchange":""}}')
tmp = pathlib.Path(tempfile.mkdtemp(prefix='td17_probe_'))
prereq = tmp / 'prereq.json'
prereq.write_text(json.dumps({'plan': 'Basic',
    'endpoint_weight': {'endpoint': '/time_series', 'credits_per_request': 1, 'evidence': 'probe'},
    'retention': {'status': 'BOUNDED_RESOLVED', 'condition': '30-day post-termination deletion'},
    'interval_semantics': {'status': 'INSUFFICIENT'}}))
from rate_limiter import RollingCreditLimiter
lim = RollingCreditLimiter(8, 100, state_path=tmp / 'ledger.json')
calls = []
def transport(req):
    calls.append(req['request_id'])
    if req['request_id'] == 'REQ-SPT-07':
        return 400, EXACT
    return 200, json.dumps({'status': 'ok', 'meta': {'symbol': 'QQQ', 'interval': '1h',
        'exchange': 'NASDAQ', 'currency': 'USD', 'mic_code': 'XNMS'},
        'values': [{'datetime': '2026-07-03 09:30:00', 'open': '1', 'high': '1',
                    'low': '1', 'close': '1', 'volume': '1'}]}).encode()
c = mod.Collector(tmp / 'state', man, lim, transport=transport,
                  prereq_path=prereq, closed_session_supplement=sup)
summary = c.run()
events = [json.loads(l) for l in (tmp / 'state' / 'lifecycle.jsonl').read_text().splitlines() if l.strip()]
out.update({
    'outcome': summary['outcome'],
    'transport_calls': calls,
    'closed_day_evidenced_summary': summary['closed_day_evidenced'],
    'closed_day_bin_exists': (tmp / 'state' / 'receipts' / 'REQ-SPT-07.closed_day.bin').exists(),
    'rejected_bin_exists': (tmp / 'state' / 'receipts' / 'REQ-SPT-07.rejected.bin').exists(),
    'closed_day_events': sum(1 for e in events if e['event'] == 'CLOSED_DAY_EVIDENCED'),
    'state_status': json.loads((tmp / 'state' / 'pilot_state.json').read_text())['status'],
})
out['verdict'] = ('FAIL-CLOSED CONFIRMED' if out['outcome'].startswith('HOLD')
                  and calls == ['REQ-SPT-07'] and not out['closed_day_bin_exists']
                  and out['closed_day_events'] == 0 else 'UNEXPECTED')
print(json.dumps(out, indent=1))
