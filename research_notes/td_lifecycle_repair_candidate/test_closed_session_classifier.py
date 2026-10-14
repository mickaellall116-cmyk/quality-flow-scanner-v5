"""Offline fixture matrix for the EXPECTED_EMPTY_CLOSED_SESSION classifier
(QF-TD-CLOSED-SESSION-CLASSIFIER-OFFLINE-20261014-17 r1; design -15 memo S7;
adjudication Issue #1 comment 6176337687).

Implements F1-F2 (positives) and N1-N12 (negatives) at 100% or the suite
fails. Every case runs the REAL run loop with a stubbed transport: positives
must advance to the following stubbed request; every negative must terminate
the batch before it. Accepted dependencies (limiter, source pins, validator)
are stubbed ONLY to isolate the collector, per the established pattern of
test_lifecycle_repair.py. The pinned calendar mechanism is stubbed at its
interface (validate_input.xnys_schedule + the library version attribute) so
the classifier logic is exercised deterministically; availability of the
REAL mechanism in the standing environment is probed separately (it is
ABSENT: pandas_market_calendars is not installed, so in the real environment
classification is disabled and the same fixtures fail closed to HOLD --
see the -17 evidence directory, real_env_probe).

Fixture provenance: EXACT_BODY is byte-identical to the preserved REQ-SPT-07
rejected evidence (180 bytes, sha256 3339c341...), the single empirical
observation this class is keyed to. It is a vendor error body: no market
data, no credentials.
"""
import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
import types
import unittest

HERE = pathlib.Path(__file__).resolve().parent

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
validator.__file__ = str(HERE.parent / 'pilot_harness' / 'validate_input.py')
CLOSED_DATES = {'2026-07-03', '2026-07-04', '2026-07-05'}


def _xnys(day):
    return None if str(day)[:10] in CLOSED_DATES else object()


validator.xnys_schedule = _xnys
sys.modules['validate_input'] = validator
mcal = types.ModuleType('pandas_market_calendars')
mcal.__version__ = '5.5.0'
sys.modules['pandas_market_calendars'] = mcal

spec = importlib.util.spec_from_file_location('closedmod', HERE / 'td_min_collector.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

EXACT_BODY = (b'{"code":400,"message":"No data is available on the specified dates. '
              b'Try setting different start/end dates.","status":"error",'
              b'"meta":{"symbol":"AAPL","interval":"1h","exchange":""}}')
EXACT_SHA256 = '3339c34154648c0ea4ddb9bd553e5274d390f953552518ad957d79704b7d5d50'
FOLLOW_RID = 'REQ-FOLLOW-01'


def make_req(rid, symbol, start, end, bound):
    r = dict(request_id=rid, symbol=symbol, leg='SPOT', interval='1h',
             start_date=start, end_date=end, timezone='America/New_York',
             adjust='splits', order='asc', outputsize=5000, max_attempts=1,
             pagination=False, credit_weight=1, expected_credits=1,
             output_name=f'{rid}.json', one_response_bound_bars=bound,
             venue_identity={'exchange': 'NASDAQ', 'currency': 'USD'})
    r['identity'] = f"{symbol}|/time_series|1h|{start}|{end}|America/New_York|adjust=splits"
    return r


def follow_req():
    return make_req(FOLLOW_RID, 'AAPL', '2026-07-06T00:00:00', '2026-07-06T23:59:59', 7)


def ok_body(symbol='AAPL'):
    return json.dumps({'status': 'ok',
                       'meta': {'symbol': symbol, 'interval': '1h',
                                'exchange': 'NASDAQ', 'currency': 'USD'},
                       'values': [{'datetime': '2026-07-06 09:30:00', 'open': '10',
                                   'high': '11', 'low': '9', 'close': '10',
                                   'volume': '1'}]}).encode()


def make_supplement(man, entries_spec):
    by_id = {r['request_id']: r for r in man['requests']}
    return {'supplement_id': 'P2-SPOT', 'version': 'v2',
            'base_manifest_digest': mod.canonical_digest(man),
            'calendar': {'mechanism': 'pandas_market_calendars:XNYS via '
                                      'pilot_harness/validate_input.py::xnys_schedule',
                         'mechanism_module_sha256': hashlib.sha256(
                             pathlib.Path(validator.__file__).read_bytes()).hexdigest(),
                         'expected_library_version': '5.5.0'},
            'entries': {rid: {'expected_bars': eb,
                              'request_digest': mod.canonical_digest(by_id[rid])}
                        for rid, eb in entries_spec.items()}}


class Limiter:
    def __init__(self):
        self.calls = 0

    def try_acquire(self, *a, **k):
        self.calls += 1
        return True


class Matrix(unittest.TestCase):
    def setUp(self):
        self._tmps = []

    def tearDown(self):
        for t in self._tmps:
            t.cleanup()
        validator.xnys_schedule = _xnys
        mcal.__version__ = '5.5.0'
        sys.modules['pandas_market_calendars'] = mcal

    def run_batch(self, closed_req, closed_response, supplement='AUTO',
                  entries_spec='AUTO'):
        """Real run loop over [closed_req, follow_req] with stub transport."""
        tmp = tempfile.TemporaryDirectory()
        self._tmps.append(tmp)
        root = pathlib.Path(tmp.name)
        prereq = root / 'prereq.json'
        prereq.write_text(json.dumps({
            'plan': 'Basic',
            'endpoint_weight': {'endpoint': '/time_series', 'credits_per_request': 1,
                                'evidence': 'synthetic'},
            'retention': {'status': 'BOUNDED_RESOLVED', 'condition': '30-day deletion'},
            'interval_semantics': {'status': 'INSUFFICIENT'}}))
        man = {'endpoint': mod.ENDPOINT, 'requests': [closed_req, follow_req()]}
        if entries_spec == 'AUTO':
            entries_spec = {closed_req['request_id']: 0}
        sup = (make_supplement(man, entries_spec) if supplement == 'AUTO' else supplement)
        calls, validated = [], []
        lim = Limiter()

        def transport(req):
            calls.append(req['request_id'])
            if req['request_id'] == closed_req['request_id']:
                return closed_response
            return 200, ok_body(req['symbol'])

        c = mod.Collector(root / 'state', man, lim, transport=transport,
                          prereq_path=prereq, closed_session_supplement=sup)

        def vb(req, values):
            validated.append(req['request_id'])
            return None

        c._validate_bars = vb  # lifecycle isolation only (established pattern)
        summary = c.run()
        state = json.loads((root / 'state' / 'pilot_state.json').read_text())
        events = [json.loads(l) for l in
                  (root / 'state' / 'lifecycle.jsonl').read_text().splitlines() if l.strip()]
        receipts = root / 'state' / 'receipts'
        return {'summary': summary, 'calls': calls, 'validated': validated,
                'limiter_calls': lim.calls, 'state': state, 'events': events,
                'receipts': receipts, 'collector': c, 'root': root,
                'manifest': man, 'supplement': sup}

    # -- shared assertion shapes -------------------------------------------
    def assert_classified(self, r, rid):
        s = r['summary']
        self.assertEqual(s['outcome'], 'COMPLETE_WITH_CLOSED_DAY_EVIDENCED')
        self.assertEqual(s['closed_day_evidenced'], 1)
        self.assertEqual(s['completed'], 1)
        self.assertEqual(r['calls'], [rid, FOLLOW_RID])  # run CONTINUED
        self.assertEqual(r['state']['status'], 'ACTIVE')
        self.assertEqual(r['state']['completed'], [FOLLOW_RID])
        self.assertEqual(r['state']['closed_day_evidenced'], [rid])
        self.assertEqual(r['state']['credit_reservations'], 2)  # credit stands spent
        self.assertEqual(r['limiter_calls'], 2)
        ev = [e for e in r['events'] if e['event'] == 'CLOSED_DAY_EVIDENCED']
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]['lifecycle_class'], 'EXPECTED_EMPTY_CLOSED_SESSION')
        self.assertEqual(ev[0]['sha256'], EXACT_SHA256)
        self.assertTrue(ev[0]['calendar_proof_digest'])
        self.assertEqual(ev[0]['supplement_digest'], mod.canonical_digest(r['supplement']))
        self.assertFalse(any(e['event'] in ('RECEIVED', 'COMPLETED')
                             and e['request_id'] == rid for e in r['events']))
        self.assertEqual(r['validated'], [FOLLOW_RID])  # no bar validation for the class
        self.assertTrue((r['receipts'] / f'{FOLLOW_RID}.json').exists())
        self.assertFalse((r['receipts'] / f'{rid}.json').exists())  # no receipt
        closed_bin = r['receipts'] / f'{rid}.closed_day.bin'
        self.assertTrue(closed_bin.exists())
        self.assertEqual(closed_bin.read_bytes(), EXACT_BODY)  # write-once raw evidence
        self.assertFalse((r['receipts'] / f'{rid}.rejected.bin').exists())

    def assert_hold(self, r, rid):
        s = r['summary']
        self.assertTrue(s['outcome'].startswith('HOLD'), s['outcome'])
        self.assertEqual(s['closed_day_evidenced'], 0)
        self.assertEqual(r['calls'], [rid])  # batch TERMINATED before the next request
        self.assertEqual(r['state']['status'], 'HOLD')
        self.assertFalse(any(e['event'] == 'CLOSED_DAY_EVIDENCED' for e in r['events']))
        self.assertFalse((r['receipts'] / f'{rid}.closed_day.bin').exists())
        self.assertFalse((r['receipts'] / f'{FOLLOW_RID}.json').exists())

    # -- provenance ----------------------------------------------------------
    def test_fixture_provenance(self):
        self.assertEqual(len(EXACT_BODY), 180)
        self.assertEqual(hashlib.sha256(EXACT_BODY).hexdigest(), EXACT_SHA256)

    # -- positives -----------------------------------------------------------
    def test_F1_single_closed_day(self):
        req = make_req('REQ-TST-07', 'AAPL', '2026-07-03T00:00:00', '2026-07-03T23:59:59', 7)
        self.assert_classified(self.run_batch(req, (400, EXACT_BODY)), 'REQ-TST-07')

    def test_F2_multiday_all_closed(self):
        req = make_req('REQ-TST-F2', 'AAPL', '2026-07-03T00:00:00', '2026-07-05T23:59:59', 21)
        self.assert_classified(self.run_batch(req, (400, EXACT_BODY)), 'REQ-TST-F2')

    # -- negatives -----------------------------------------------------------
    def test_N1_mixed_window(self):
        req = make_req('REQ-TST-N1', 'AAPL', '2026-07-03T00:00:00', '2026-07-06T23:59:59', 28)
        self.assert_hold(self.run_batch(req, (400, EXACT_BODY)), 'REQ-TST-N1')

    def test_N2_message_mutated_one_char(self):
        body = EXACT_BODY.replace(b'dates. Try', b'dates! Try')
        self.assertNotEqual(body, EXACT_BODY)
        req = make_req('REQ-TST-N2', 'AAPL', '2026-07-03T00:00:00', '2026-07-03T23:59:59', 7)
        self.assert_hold(self.run_batch(req, (400, body)), 'REQ-TST-N2')

    def test_N3_code_status_altered(self):
        base = json.loads(EXACT_BODY)
        variants = []
        v = dict(base); v['code'] = '400'; variants.append(v)          # retyped
        v = dict(base); v['code'] = 401; variants.append(v)            # altered
        v = dict(base); del v['status']; variants.append(v)            # missing
        v = dict(base); v['status'] = 'err'; variants.append(v)        # altered
        for i, v in enumerate(variants):
            with self.subTest(variant=i):
                rid = f'REQ-TST-N3{ i }'
                req = make_req(rid, 'AAPL', '2026-07-03T00:00:00', '2026-07-03T23:59:59', 7)
                self.assert_hold(self.run_batch(req, (400, json.dumps(v).encode())), rid)

    def test_N4_http200_ok_empty_values(self):
        body = json.dumps({'status': 'ok',
                           'meta': {'symbol': 'AAPL', 'interval': '1h',
                                    'exchange': 'NASDAQ', 'currency': 'USD'},
                           'values': []}).encode()
        req = make_req('REQ-TST-N4', 'AAPL', '2026-07-03T00:00:00', '2026-07-03T23:59:59', 7)
        self.assert_hold(self.run_batch(req, (200, body)), 'REQ-TST-N4')

    def test_N5_http200_error_exact_message(self):
        req = make_req('REQ-TST-N5', 'AAPL', '2026-07-03T00:00:00', '2026-07-03T23:59:59', 7)
        self.assert_hold(self.run_batch(req, (200, EXACT_BODY)), 'REQ-TST-N5')

    def test_N6_http400_auth_message(self):
        v = json.loads(EXACT_BODY)
        v['message'] = 'Invalid api key. Please check your API key and try again.'
        req = make_req('REQ-TST-N6', 'AAPL', '2026-07-03T00:00:00', '2026-07-03T23:59:59', 7)
        self.assert_hold(self.run_batch(req, (400, json.dumps(v).encode())), 'REQ-TST-N6')

    def test_N7_auth_rate_server_statuses(self):
        for st in (401, 403, 429, 500):
            with self.subTest(status=st):
                rid = f'REQ-TST-N7{st}'
                req = make_req(rid, 'AAPL', '2026-07-03T00:00:00', '2026-07-03T23:59:59', 7)
                self.assert_hold(self.run_batch(req, (st, EXACT_BODY)), rid)

    def test_N8_http400_unparseable_body(self):
        req = make_req('REQ-TST-N8', 'AAPL', '2026-07-03T00:00:00', '2026-07-03T23:59:59', 7)
        self.assert_hold(self.run_batch(req, (400, b'not json{{')), 'REQ-TST-N8')

    def test_N9_not_preregistered_expected_bars(self):
        req = make_req('REQ-TST-N9', 'AAPL', '2026-07-03T00:00:00', '2026-07-03T23:59:59', 7)
        with self.subTest(variant='entry_absent'):
            self.assert_hold(self.run_batch(req, (400, EXACT_BODY), entries_spec={}),
                             'REQ-TST-N9')
        with self.subTest(variant='expected_bars_nonzero'):
            self.assert_hold(self.run_batch(
                req, (400, EXACT_BODY),
                entries_spec={'REQ-TST-N9': 7}), 'REQ-TST-N9')

    def test_N10_calendar_unavailable_or_version_mismatch(self):
        req = make_req('REQ-TST-N10', 'AAPL', '2026-07-03T00:00:00', '2026-07-03T23:59:59', 7)
        with self.subTest(variant='mechanism_raises'):
            def boom(day):
                raise ImportError('No module named pandas_market_calendars')
            validator.xnys_schedule = boom
            try:
                self.assert_hold(self.run_batch(req, (400, EXACT_BODY)), 'REQ-TST-N10')
            finally:
                validator.xnys_schedule = _xnys
        with self.subTest(variant='version_mismatch'):
            mcal.__version__ = '9.9.9'
            try:
                self.assert_hold(self.run_batch(req, (400, EXACT_BODY)), 'REQ-TST-N10')
            finally:
                mcal.__version__ = '5.5.0'
        with self.subTest(variant='library_absent'):
            del sys.modules['pandas_market_calendars']
            try:
                self.assert_hold(self.run_batch(req, (400, EXACT_BODY)), 'REQ-TST-N10')
            finally:
                sys.modules['pandas_market_calendars'] = mcal

    def test_N11_values_field_present(self):
        v = json.loads(EXACT_BODY)
        v['values'] = []
        req = make_req('REQ-TST-N11', 'AAPL', '2026-07-03T00:00:00', '2026-07-03T23:59:59', 7)
        self.assert_hold(self.run_batch(req, (400, json.dumps(v).encode())), 'REQ-TST-N11')

    def test_N12_digest_mismatch(self):
        req = make_req('REQ-TST-N12', 'AAPL', '2026-07-03T00:00:00', '2026-07-03T23:59:59', 7)
        with self.subTest(variant='manifest_digest'):
            man = {'endpoint': mod.ENDPOINT, 'requests': [req, follow_req()]}
            sup = make_supplement(man, {req['request_id']: 0})
            sup['base_manifest_digest'] = '0' * 64
            self.assert_hold(self.run_batch(req, (400, EXACT_BODY), supplement=sup),
                             'REQ-TST-N12')
        with self.subTest(variant='request_digest'):
            man = {'endpoint': mod.ENDPOINT, 'requests': [req, follow_req()]}
            sup = make_supplement(man, {req['request_id']: 0})
            sup['entries'][req['request_id']]['request_digest'] = '0' * 64
            self.assert_hold(self.run_batch(req, (400, EXACT_BODY), supplement=sup),
                             'REQ-TST-N12')

    # -- supplementary (beyond the required matrix) ---------------------------
    def test_S1_meta_symbol_mismatch(self):
        body = EXACT_BODY.replace(b'"symbol":"AAPL"', b'"symbol":"QQQ"')
        req = make_req('REQ-TST-S1', 'AAPL', '2026-07-03T00:00:00', '2026-07-03T23:59:59', 7)
        self.assert_hold(self.run_batch(req, (400, body)), 'REQ-TST-S1')

    def test_S2_no_supplement_existing_behavior(self):
        req = make_req('REQ-TST-S2', 'AAPL', '2026-07-03T00:00:00', '2026-07-03T23:59:59', 7)
        self.assert_hold(self.run_batch(req, (400, EXACT_BODY), supplement=None),
                         'REQ-TST-S2')

    def test_S3_restart_never_redispatches_evidenced(self):
        req = make_req('REQ-TST-S3', 'AAPL', '2026-07-03T00:00:00', '2026-07-03T23:59:59', 7)
        r = self.run_batch(req, (400, EXACT_BODY))
        self.assert_classified(r, 'REQ-TST-S3')
        calls2 = []

        def transport2(req2):
            calls2.append(req2['request_id'])
            return 200, ok_body(req2['symbol'])

        lim2 = Limiter()
        c2 = mod.Collector(r['root'] / 'state', r['manifest'], lim2,
                           transport=transport2,
                           prereq_path=r['root'] / 'prereq.json',
                           closed_session_supplement=r['supplement'])
        c2._validate_bars = lambda rq, values: None
        s2 = c2.run()
        self.assertEqual(calls2, [])  # nothing redispatched
        self.assertEqual(s2['closed_day_evidenced'], 1)
        self.assertEqual(s2['reused'], 1)
        self.assertNotIn('HOLD', s2['outcome'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
