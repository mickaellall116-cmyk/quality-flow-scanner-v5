"""Offline lifecycle regression probes. No HTTP clients or vendor calls.

Accepted dependencies are stubbed ONLY to isolate collector lifecycle.
This suite is not integration/feed/session qualification.
"""
import copy
import importlib.util
import json
import multiprocessing
import pathlib
import sys
import tempfile
import types
import unittest

rate = types.ModuleType('rate_limiter')
rate.RollingCreditLimiter = object
rate.LedgerCorruptError = type('LedgerCorruptError', (Exception,), {})
sys.modules['rate_limiter'] = rate
verify = types.ModuleType('verify_sources')
verify.verify_directory = lambda *a: []
verify.PINNED = {}
verify.ARCHIVAL_DIR = pathlib.Path('.')
sys.modules['verify_sources'] = verify
validator = types.ModuleType('validate_input')
validator.validate = lambda *a, **k: {}
validator.ValidationError = ValueError
sys.modules['validate_input'] = validator
spec = importlib.util.spec_from_file_location('repair', pathlib.Path(__file__).with_name('td_min_collector.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class Limiter:
    def __init__(self):
        self.calls = 0
    def try_acquire(self, *a, **k):
        self.calls += 1
        return True


def manifest(interval='1h'):
    r = dict(request_id='AAPL_TEST', symbol='AAPL', leg='PAR' if interval == '1h' else 'PAR4H',
             interval=interval, start_date='2026-09-08T00:00:00', end_date='2026-09-08T23:59:59',
             timezone='America/New_York', adjust='none', order='asc', outputsize=5000,
             max_attempts=1, pagination=False, credit_weight=1, expected_credits=1,
             output_name='AAPL_TEST.json', one_response_bound_bars=7 if interval == '1h' else 2,
             venue_identity={'exchange': 'NASDAQ', 'currency': 'USD'})
    r['identity'] = f"AAPL|/time_series|{interval}|{r['start_date']}|{r['end_date']}|America/New_York|adjust=none"
    return {'endpoint': mod.ENDPOINT, 'requests': [r]}


def body(interval='1h'):
    return json.dumps({'status': 'ok', 'meta': {'symbol': 'AAPL', 'interval': interval,
                      'exchange': 'NASDAQ', 'currency': 'USD'},
                      'values': [{'datetime': '2026-09-08 09:30:00', 'open': '10',
                                  'high': '11', 'low': '9', 'close': '10', 'volume': '1'}]}).encode()


def hold_child_lock(path, pipe):
    import fcntl
    with open(path, 'a+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        pipe.send('locked')
        pipe.recv()


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.pr = self.root / 'prereq.json'
        self.pr.write_text(json.dumps({'plan': 'Basic', 'endpoint_weight': {'endpoint': '/time_series',
            'credits_per_request': 1, 'evidence': 'synthetic'}, 'retention': {'status': 'BOUNDED_RESOLVED',
            'condition': '30-day deletion'}, 'interval_semantics': {'status': 'INSUFFICIENT'}}))
        self.calls = []
        self.lim = Limiter()
    def tearDown(self):
        self.tmp.cleanup()
    def collector(self, man=None, transport=None):
        def synthetic(req):
            self.calls.append(req)
            return 200, body(req['interval'])
        c = mod.Collector(self.root / 'state', man or manifest(), self.lim,
                          transport=transport or synthetic, prereq_path=self.pr)
        c._validate_bars = lambda *a: None  # lifecycle isolation, explicitly NOT validation proof
        return c
    def test_validated_restart_reuses_without_dispatch(self):
        self.assertEqual(self.collector().run()['completed'], 1)
        self.assertEqual(self.collector().run()['reused'], 1)
        self.assertEqual(len(self.calls), 1)
    def test_received_crash_before_validation_stays_hold(self):
        c = self.collector()
        def crash(*a): raise KeyboardInterrupt()
        c._validate_bars = crash
        with self.assertRaises(KeyboardInterrupt): c.run()
        result = self.collector().run()
        self.assertIn('HOLD', result['outcome'])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(result['completed'], 0)
    def test_completed_event_crash_before_state_save_revalidates(self):
        c = self.collector()
        original = c._save_pilot_state
        def crash():
            if any(e['event'] == 'COMPLETED' for e in c._events): raise KeyboardInterrupt()
            original()
        c._save_pilot_state = crash
        with self.assertRaises(KeyboardInterrupt): c.run()
        self.assertEqual(self.collector().run()['completed'], 1)
        self.assertEqual(len(self.calls), 1)
    def test_started_crash_no_redispatch(self):
        def crash(req): raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt): self.collector(transport=crash).run()
        self.assertIn('HOLD', self.collector().run()['outcome'])
        self.assertEqual(self.calls, [])
    def test_changed_request_binding(self):
        self.collector().run()
        for field, val in [('adjust', 'splits'), ('outputsize', 4999), ('order', 'desc'),
                           ('venue_identity', {'exchange': 'NYSE', 'currency': 'USD'})]:
            m = manifest(); m['requests'][0][field] = val
            if field == 'adjust': m['requests'][0]['identity'] = m['requests'][0]['identity'].replace('adjust=none','adjust=splits')
            with self.assertRaisesRegex(mod.CollectorError, 'binding changed'): self.collector(m).run()
        self.assertEqual(len(self.calls), 1)
    def test_changed_date_binding(self):
        self.collector().run(); m = manifest();r=m['requests'][0]
        r['start_date']='2026-09-07T00:00:00';r['one_response_bound_bars']=14
        r['identity']=r['identity'].replace('2026-09-08T00:00:00','2026-09-07T00:00:00')
        with self.assertRaisesRegex(mod.CollectorError, 'binding changed'):self.collector(m).run()
    def test_revalidation_required_for_reuse(self):
        self.collector().run();c=self.collector();c._validate_bars=lambda *a:'invalid'
        self.assertIn('HOLD',c.run()['outcome']);self.assertEqual(len(self.calls),1)
    def test_prerequisite_gate_is_in_run(self):
        c=self.collector();self.pr.unlink()
        with self.assertRaisesRegex(mod.CollectorError,'preflight failed'):c.run()
        self.assertEqual(self.calls,[]);self.assertEqual(self.lim.calls,0)
    def test_source_gate_is_in_run(self):
        c=self.collector();old=mod.verify_directory;mod.verify_directory=lambda *a:['bad pin']
        try:
            with self.assertRaises(mod.CollectorError):c.run()
        finally:mod.verify_directory=old
        self.assertEqual(self.calls,[])
    def test_corrupt_state_errors_without_dispatch(self):
        self.collector().run();(self.root/'state/pilot_state.json').write_text('{')
        with self.assertRaises(ValueError):self.collector()
        self.assertEqual(len(self.calls),1)
    def test_legacy_unbound_evidence_refused(self):
        self.collector().run();(self.root/'state/manifest_binding.json').unlink()
        with self.assertRaisesRegex(mod.CollectorError,'legacy/unbound'):self.collector().run()
    def test_receipt_tamper_stays_hold(self):
        self.collector().run();(self.root/'state/receipts/AAPL_TEST.json').write_bytes(b'{}')
        self.assertIn('HOLD',self.collector().run()['outcome']);self.assertEqual(len(self.calls),1)
    def test_malformed_list_response_hold(self):
        self.assertIn('HOLD',self.collector(transport=lambda r:(200,b'[]')).run()['outcome'])
    def test_venue_mismatch_hold(self):
        def bad(r):
            o=json.loads(body());o['meta']['exchange']='NYSE';return 200,json.dumps(o).encode()
        self.assertIn('HOLD',self.collector(transport=bad).run()['outcome'])
    def test_native4h_is_structural_not_1h_validator(self):
        c=self.collector(manifest('4h'));c._validate_bars=types.MethodType(mod.Collector._validate_bars,c)
        old=validator.validate;validator.validate=lambda *a,**k:(_ for _ in ()).throw(AssertionError('1h validator called'))
        try:self.assertEqual(c.run()['completed'],1)
        finally:validator.validate=old
        self.assertEqual(c._events[-1]['validation_scope'],'native_4h_structural_diagnostic')
    def test_invalid_native4h_geometry_hold(self):
        def bad(r):
            o=json.loads(body('4h'));o['values'][0]['high']='1';return 200,json.dumps(o).encode()
        c=self.collector(manifest('4h'),bad);c._validate_bars=types.MethodType(mod.Collector._validate_bars,c)
        self.assertIn('HOLD',c.run()['outcome'])
    def test_concurrent_process_refused_before_dispatch(self):
        c=self.collector();p0,p1=multiprocessing.Pipe();p=multiprocessing.Process(target=hold_child_lock,args=(self.root/'state/collector.lock',p1));p.start()
        try:
            self.assertTrue(p0.poll(5));self.assertEqual(p0.recv(),'locked')
            with self.assertRaisesRegex(mod.CollectorError,'another collector'):c.run()
            self.assertEqual(self.calls,[])
        finally:p0.send('release');p.join(5)
        self.assertFalse(p.is_alive())
    def test_manifest_malformed_domains(self):
        self.assertTrue(mod.validate_manifest([]));self.assertTrue(mod.validate_manifest({'requests':[[]]}))
        for key,val in [('request_id','../escape'),('adjust','unknown'),('order','random'),('venue_identity',{}),('start_date','not-date')]:
            m=manifest();m['requests'][0][key]=val;self.assertTrue(mod.validate_manifest(m))
    def test_disabled_default_transport_preserved(self):
        c=mod.Collector(self.root/'state',manifest(),self.lim,prereq_path=self.pr)
        c._validate_bars=lambda *a:None
        self.assertIn('disabled',c.run()['outcome'])


if __name__=='__main__':unittest.main(verbosity=2)
