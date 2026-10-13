#!/usr/bin/env python3
"""Independent integration review of td_lifecycle_repair_candidate @ af49bf4.
Uses ACTUAL pinned deps (fd03906): verify_sources, rate_limiter, validate_input.
Transport is an in-process stub returning synthetic bytes (no HTTP, zero calls).
"""
import json, shutil, subprocess, sys, time
from pathlib import Path

BASE = Path('/tmp/tdreview/run/research_notes')
sys.path.insert(0, str(BASE / 'td_lifecycle_repair_candidate'))
sys.path.insert(0, str(BASE / 'pilot_harness'))

import td_min_collector as C
from rate_limiter import RollingCreditLimiter
import validate_input as VI

PREREQ = Path('/tmp/tdreview/prereq.json')
ROOT = Path('/tmp/tdreview/scenarios')
shutil.rmtree(ROOT, ignore_errors=True); ROOT.mkdir(parents=True)
RESULTS = {}

def req(interval='4h', adjust='none', order='asc', outputsize=10,
        start='2026-10-05T00:00:00', end='2026-10-06T23:59:59',
        exchange='NASDAQ', rid=None):
    rid = rid or ('REQ-P4H-01' if interval == '4h' else 'REQ-P1H-01')
    days = ( __import__('datetime').date.fromisoformat(end[:10])
             - __import__('datetime').date.fromisoformat(start[:10]) ).days
    bound = (days + 1) * (2 if interval == '4h' else 7)
    return {'request_id': rid, 'symbol': 'AAPL', 'leg': 'PAR4H' if interval == '4h' else 'PAR',
            'interval': interval, 'start_date': start, 'end_date': end,
            'timezone': 'America/New_York', 'max_attempts': 1, 'credit_weight': 1,
            'expected_credits': 1, 'output_name': f'{rid}.json', 'adjust': adjust,
            'order': order, 'outputsize': outputsize, 'one_response_bound_bars': bound,
            'venue_identity': {'exchange': exchange, 'currency': 'USD'},
            'identity': f"AAPL|/time_series|{interval}|{start}|{end}|America/New_York|adjust={adjust}"}

def manifest(r):
    return {'manifest_id': 'REVIEW-20261012', 'endpoint': 'https://api.twelvedata.com/time_series',
            'requests': [r]}

def payload(interval='4h', exchange='NASDAQ'):
    if interval == '4h':
        vals = [{'datetime': '2026-10-05 09:30:00', 'open': '100', 'high': '105', 'low': '99', 'close': '104', 'volume': '1000'},
                {'datetime': '2026-10-05 13:30:00', 'open': '104', 'high': '106', 'low': '103', 'close': '105', 'volume': '900'},
                {'datetime': '2026-10-06 09:30:00', 'open': '105', 'high': '107', 'low': '104', 'close': '106', 'volume': '800'}]
    else:
        vals = [{'datetime': f'2026-10-05 {h:02d}:30:00', 'open': '100', 'high': '105', 'low': '99', 'close': '104', 'volume': '1000'}
                for h in (9, 10, 11, 12, 13, 14, 15)]
    body = {'meta': {'symbol': 'AAPL', 'interval': interval, 'exchange': exchange, 'currency': 'USD'},
            'values': vals, 'status': 'ok'}
    return json.dumps(body).encode()

def new_collector(sdir, man, transport):
    lim = RollingCreditLimiter(8, 800, state_path=Path(sdir) / 'ledger.json')
    return C.Collector(Path(sdir), man, lim, transport=transport, prereq_path=PREREQ)

def events(sdir):
    p = Path(sdir) / 'lifecycle.jsonl'
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []

# ---------- S0 control + (e): native 4H structural path, validate() bombed ----------
d = ROOT / 's0'; man = manifest(req())
bomb_calls = []
orig_validate = VI.validate
VI.validate = lambda *a, **k: bomb_calls.append(1) or (_ for _ in ()).throw(AssertionError('1H validate() called for native 4H'))
try:
    out = new_collector(d, man, lambda r: (200, payload('4h'))).run()
finally:
    VI.validate = orig_validate
ev = events(d)
completed = [e for e in ev if e['event'] == 'COMPLETED']
RESULTS['S0_control_4h_complete'] = out
RESULTS['e_native_4h'] = {
    'outcome': out['outcome'], 'validate_called': bool(bomb_calls),
    'validation_scope': completed[-1].get('validation_scope') if completed else None,
    'PASS': out['outcome'] == 'COMPLETE' and not bomb_calls
            and completed and completed[-1].get('validation_scope') == 'native_4h_structural_diagnostic'}

# ---------- S0b: restart, identical manifest -> reuse ----------
out = new_collector(d, man, lambda r: (200, payload('4h'))).run()
RESULTS['S0b_restart_reuse'] = out

# ---------- (a): crash after RECEIVED, before validation completes ----------
d = ROOT / 'sa'; man = manifest(req())
orig_vb = C.Collector._validate_bars
C.Collector._validate_bars = lambda self, r, v: (_ for _ in ()).throw(RuntimeError('SIMULATED CRASH after RECEIVED'))
crash = None
try:
    new_collector(d, man, lambda r: (200, payload('4h'))).run()
except RuntimeError as e:
    crash = str(e)
finally:
    C.Collector._validate_bars = orig_vb
ev_mid = events(d)
out = new_collector(d, man, lambda r: (200, payload('4h'))).run()
RESULTS['a_crash_after_received'] = {
    'crash': crash, 'events_before_restart': [e['event'] for e in ev_mid],
    'restart_outcome': out,
    'PASS': crash is not None and any(e['event'] == 'RECEIVED' for e in ev_mid)
            and not any(e['event'] == 'COMPLETED' for e in ev_mid)
            and out['outcome'].startswith('HOLD') and out['dispatched'] == 0 and out['reused'] == 0}

# ---------- (b1): changed params under same request_id (manifest-level binding) ----------
variants = {}
for name, kw in [('start_date', {'start': '2026-10-04T00:00:00'}),
                 ('adjust', {'adjust': 'all'}), ('order', {'order': 'desc'}),
                 ('outputsize', {'outputsize': 11}), ('venue', {'exchange': 'NYSE'})]:
    dd = ROOT / f'sb1_{name}'
    shutil.copytree(ROOT / 's0', dd)
    try:
        out = new_collector(dd, manifest(req(**kw)), lambda r: (200, payload('4h'))).run()
        variants[name] = f'NO REFUSAL: {out}'
    except C.CollectorError as e:
        variants[name] = f'REFUSED (CollectorError): {e}'
    except Exception as e:
        variants[name] = f'OTHER {type(e).__name__}: {e}'
RESULTS['b1_changed_params'] = {'variants': variants,
    'PASS': all(v.startswith('REFUSED') for v in variants.values())}

# ---------- (b2): receipt-level binding (binding file swapped to changed-manifest digest) ----------
dd = ROOT / 'sb2'; shutil.copytree(ROOT / 's0', dd)
man2 = manifest(req(adjust='all'))
(dd / 'manifest_binding.json').write_text(json.dumps({'sha256': C.canonical_digest(man2)}))
out = new_collector(dd, man2, lambda r: (200, payload('4h'))).run()
RESULTS['b2_receipt_level_binding'] = {'outcome': out,
    'PASS': out['outcome'].startswith('HOLD') and out['reused'] == 0}

# ---------- (c): concurrent second process holds the state lock ----------
d = ROOT / 'sc'; man = manifest(req())
d.mkdir(parents=True, exist_ok=True)
holder = subprocess.Popen([sys.executable, '-c',
    "import fcntl,sys,time; f=open(sys.argv[1],'a+'); fcntl.flock(f, fcntl.LOCK_EX|fcntl.LOCK_NB); print('LOCKED',flush=True); time.sleep(20)",
    str(d / 'collector.lock')], stdout=subprocess.PIPE, text=True)
assert holder.stdout.readline().strip() == 'LOCKED'
try:
    new_collector(d, man, lambda r: (200, payload('4h'))).run()
    c_out = 'NO REFUSAL — run proceeded under contention'
except C.CollectorError as e:
    c_out = f'REFUSED (CollectorError): {e}'
finally:
    holder.terminate()
led = json.loads((d / 'ledger.json').read_text()) if (d / 'ledger.json').exists() else {}
RESULTS['c_concurrent_lock'] = {'result': c_out,
    'started_events': [e for e in events(d) if e['event'] == 'STARTED'],
    'PASS': c_out.startswith('REFUSED') and not [e for e in events(d) if e['event'] == 'STARTED']}

# ---------- (d): malformed payload — JSON list instead of object ----------
d = ROOT / 'sd'; man = manifest(req())
try:
    out = new_collector(d, man, lambda r: (200, b'["not","an","object"]')).run()
    d_res = {'outcome': out, 'raised': None}
except Exception as e:
    d_res = {'outcome': None, 'raised': f'{type(e).__name__}: {e}'}
rej = list((d / 'receipts').glob('*.rejected.bin')) if (d / 'receipts').exists() else []
RESULTS['d_malformed_list'] = {**d_res, 'rejected_evidence_files': [p.name for p in rej],
    'PASS': d_res['raised'] is None and d_res['outcome']['outcome'].startswith('HOLD') and bool(rej)}

# ---------- (f): 1H request with ACTUAL validate_input (calendar dep check) ----------
d = ROOT / 'sf'; man = manifest(req(interval='1h', outputsize=20))
try:
    out = new_collector(d, man, lambda r: (200, payload('1h'))).run()
    f_res = {'outcome': out, 'raised': None}
except Exception as e:
    f_res = {'outcome': None, 'raised': f'{type(e).__name__}: {e}'}
RESULTS['f_1h_actual_validator'] = {**f_res,
    'note': 'pandas_market_calendars absent in this env; 1H completion impossible here = coverage gap. Fail-closed HOLD is the safe outcome.'}

# ---------- (g) NEW: receipt byte tamper (same length) after completion ----------
dd = ROOT / 'sg'; shutil.copytree(ROOT / 's0', dd)
rp = dd / 'receipts' / 'REQ-P4H-01.json'
raw = bytearray(rp.read_bytes()); raw[30] = raw[30] ^ 1; rp.write_bytes(bytes(raw))
out = new_collector(dd, manifest(req()), lambda r: (200, payload('4h'))).run()
RESULTS['g_receipt_tamper'] = {'outcome': out,
    'PASS': out['outcome'].startswith('HOLD') and out['reused'] == 0}

print(json.dumps(RESULTS, indent=1, default=str))
