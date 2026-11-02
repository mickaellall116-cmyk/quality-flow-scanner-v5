"""Real pinned-dependency integration, synthetic transport only.

Run from a clean checkout after installing sibling pilot_harness/requirements.txt:
  python3 test_pinned_integration.py --output-dir <NEW PRIVATE DIRECTORY>
No dependency stubs, HTTP clients, vendor requests, or market data are used.
Output is append-free: refuses an existing output directory rather than deleting it.
"""
import argparse
import copy
import hashlib
import importlib.metadata
import json
import multiprocessing
import pathlib
import platform
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import td_min_collector as c
import pandas as pd
from validate_input import validate, expected_1h_starts, xnys_schedule
from construct_4h import construct_4h


def make_manifest(day='2026-09-08', interval='1h', order='asc'):
    r = dict(request_id='AAPL_FIXTURE', symbol='AAPL', leg='PAR' if interval=='1h' else 'PAR4H',
        interval=interval, start_date=day+'T00:00:00', end_date=day+'T23:59:59',
        timezone='America/New_York', adjust='none', order=order, outputsize=5000,
        max_attempts=1, pagination=False, credit_weight=1, expected_credits=1,
        output_name='AAPL_FIXTURE.json', one_response_bound_bars=7 if interval=='1h' else 2,
        venue_identity={'exchange':'NASDAQ','currency':'USD'})
    r['identity']=f"AAPL|/time_series|{interval}|{r['start_date']}|{r['end_date']}|America/New_York|adjust=none"
    return {'endpoint':c.ENDPOINT,'requests':[r]}


def make_body(day='2026-09-08', interval='1h', drop=False, reverse=False):
    schedule=xnys_schedule(pd.Timestamp(day,tz='America/New_York'))
    starts=expected_1h_starts(*schedule) if schedule else []
    if interval=='4h':starts=starts[::4]
    values=[]
    for i,t in enumerate(starts):
        price=10*(i+1)
        values.append({'datetime':t.strftime('%Y-%m-%d %H:%M:%S'),
                       'open':str(price),'high':str(price+1),'low':str(price-1),
                       'close':str(price),'volume':str(i+1)})
    if drop:values=values[:-1]
    if reverse:values=values[::-1]
    return json.dumps({'status':'ok','meta':{'symbol':'AAPL','interval':interval,
        'exchange':'NASDAQ','currency':'USD'},'values':values}).encode()


def other_process_lock(path, pipe):
    import fcntl
    with open(path,'a+') as f:
        fcntl.flock(f,fcntl.LOCK_EX);pipe.send('locked');pipe.recv()


class Integration(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)
        self.pr=self.root/'prereq.json'
        self.pr.write_text(json.dumps({'plan':'Basic',
            'endpoint_weight':{'endpoint':'/time_series','credits_per_request':1,'evidence':'synthetic evidence fixture'},
            'retention':{'status':'BOUNDED_RESOLVED','condition':'30-day deletion: synthetic prerequisite fixture'},
            'interval_semantics':{'status':'INSUFFICIENT'}}))
        self.calls=[]
        self.epoch=1791900000.0
    def tearDown(self):self.tmp.cleanup()
    def collector(self,man=None,transport=None):
        man=man or make_manifest()
        def synthetic(r):
            self.calls.append(r['request_id'])
            return 200,make_body(r['start_date'][:10],r['interval'])
        limiter=c.RollingCreditLimiter(8,800,state_path=self.root/'shared_credit.json',clock=lambda:self.epoch)
        return c.Collector(self.root/'state',man,limiter,transport=transport or synthetic,prereq_path=self.pr)
    def test_actual_sources_verify(self):
        self.assertEqual(c.verify_directory(c.ARCHIVAL_DIR,c.PINNED),[])
    def test_real_regular_1h_completion_and_reuse(self):
        result=self.collector().run();self.assertEqual(result['completed'],1)
        self.assertEqual(self.collector().run()['reused'],1)
        self.assertEqual(self.calls,['AAPL_FIXTURE'])
        self.assertEqual(json.loads((self.root/'shared_credit.json').read_text())['spent'],1)
    def test_real_early_close(self):
        self.assertEqual(self.collector(make_manifest('2025-11-28')).run()['completed'],1)
    def test_real_spring_and_fall_dst(self):
        for day,offset in [('2026-03-09',-4),('2025-11-03',-5)]:
            starts=expected_1h_starts(*xnys_schedule(pd.Timestamp(day,tz='America/New_York')))
            self.assertEqual(len(starts),7);self.assertEqual(starts[0].utcoffset().total_seconds()/3600,offset)
    def test_missing_constituent_hold(self):
        result=self.collector(transport=lambda r:(200,make_body(drop=True))).run()
        self.assertIn('HOLD',result['outcome']);self.assertEqual(result['completed'],0)
    def test_holiday_validator_empty_is_closed(self):
        day='2026-07-03'
        df=pd.DataFrame(columns=['open','high','low','close','volume'])
        report=validate(df,'AAPL',day,day,as_of=pd.Timestamp(day+'T23:59:59',tz='America/New_York'))
        self.assertEqual(report['expected_open_days'],0);self.assertEqual(report['bars_validated'],0)
    def test_native_4h_actual_structural_path(self):
        obj=self.collector(make_manifest(interval='4h'));self.assertEqual(obj.run()['completed'],1)
        self.assertEqual(obj._events[-1]['validation_scope'],'native_4h_structural_diagnostic')
    def test_crash_received_before_real_validation(self):
        obj=self.collector();real=obj._validate_bars
        def crash(*a):raise KeyboardInterrupt()
        obj._validate_bars=crash
        with self.assertRaises(KeyboardInterrupt):obj.run()
        result=self.collector().run();self.assertIn('HOLD',result['outcome'])
        self.assertEqual(result['completed'],0);self.assertEqual(len(self.calls),1)
    def test_changed_request_real_preflight_refusal(self):
        self.collector().run()
        for field,val in [('outputsize',4999),('order','desc'),('adjust','splits'),
                          ('venue_identity',{'exchange':'NYSE','currency':'USD'})]:
            man=make_manifest();r=man['requests'][0];r[field]=val
            if field=='adjust':r['identity']=r['identity'].replace('adjust=none','adjust=splits')
            with self.assertRaisesRegex(c.CollectorError,'binding changed'):self.collector(man).run()
        self.assertEqual(len(self.calls),1)
    def test_actual_limiter_restart_window_refuses(self):
        path=self.root/'credits.json'
        a=c.RollingCreditLimiter(8,800,state_path=path,clock=lambda:self.epoch)
        for _ in range(8):self.assertTrue(a.try_acquire(1))
        b=c.RollingCreditLimiter(8,800,state_path=path,clock=lambda:self.epoch+10)
        self.assertFalse(b.try_acquire(1));self.assertEqual(json.loads(path.read_text())['spent'],8)
    def test_actual_corrupt_limiter_blocks_transport(self):
        obj=self.collector();(self.root/'shared_credit.json').write_text('{')
        self.assertIn('HOLD',obj.run()['outcome']);self.assertEqual(self.calls,[])
    def test_actual_prerequisite_missing_blocks_transport(self):
        obj=self.collector();self.pr.unlink()
        with self.assertRaises(c.CollectorError):obj.run()
        self.assertEqual(self.calls,[])
    def test_source_tamper_isolated_copy(self):
        p=self.root/'archive';p.mkdir()
        for n in c.PINNED:(p/n).write_bytes((c.ARCHIVAL_DIR/n).read_bytes())
        (p/'scanner_rules.py').write_text('tampered synthetic copy')
        failures=c.verify_directory(p,c.PINNED)
        self.assertTrue(any('HASH MISMATCH' in f for f in failures))
    def test_malformed_payload_real_dependencies(self):
        self.assertIn('HOLD',self.collector(transport=lambda r:(200,b'[]')).run()['outcome'])
    def test_second_process_lock_blocks_transport(self):
        obj=self.collector();parent,child=multiprocessing.Pipe()
        p=multiprocessing.Process(target=other_process_lock,args=(self.root/'state/collector.lock',child));p.start()
        try:
            self.assertTrue(parent.poll(5));self.assertEqual(parent.recv(),'locked')
            with self.assertRaisesRegex(c.CollectorError,'another collector'):obj.run()
            self.assertEqual(self.calls,[])
        finally:parent.send('release');p.join(5)
        self.assertFalse(p.is_alive())
    def test_partial_bin_exact_ohlcv_real_validation_and_construction(self):
        day='2026-09-08';values=json.loads(make_body())['values'][:4]
        df=pd.DataFrame(values);df.index=pd.DatetimeIndex(pd.to_datetime(df.datetime)).tz_localize('America/New_York')
        for key in ['open','high','low','close','volume']:df[key]=pd.to_numeric(df[key])
        cutoff=pd.Timestamp(day+'T13:30:00',tz='America/New_York')
        report=validate(df,'AAPL',day,day,as_of=cutoff)
        ends=pd.Series({pd.Timestamp(k):pd.Timestamp(v) for k,v in report['interval_ends'].items()})
        df=df.rename(columns={k:k.title() for k in ['open','high','low','close','volume']})
        bars=construct_4h(df,'AAPL',as_of=cutoff,validated_ends=ends)
        self.assertEqual(len(bars),1)
        self.assertEqual(bars.iloc[0].tolist(),[10,41,9,40,10])


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output-dir',required=True);args=ap.parse_args()
    out=pathlib.Path(args.output_dir);out.mkdir(parents=True,exist_ok=False)
    class Captured(unittest.TextTestResult):
        def __init__(self,*a):super().__init__(*a);self.passed=[]
        def addSuccess(self,test):super().addSuccess(test);self.passed.append(test.id())
    with (out/'test_output.txt').open('w') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Captured).run(unittest.defaultTestLoader.loadTestsFromTestCase(Integration))
    dependencies={name:importlib.metadata.version(name) for name in ['pandas','numpy','pandas_market_calendars','pytz','python-dateutil','exchange-calendars','tzdata']}
    files=[HERE/'td_min_collector.py',pathlib.Path(__file__).resolve()]
    files+=list((HERE.parent/'pilot_harness').glob('*.py'))
    files+=list(c.ARCHIVAL_DIR.glob('*.py'))
    hashes={str(p.relative_to(HERE.parent.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    summary={'tests_run':result.testsRun,'passed':result.passed,'failures':[(t.id(),e) for t,e in result.failures],
             'errors':[(t.id(),e) for t,e in result.errors],'success':result.wasSuccessful(),
             'python':platform.python_version(),'dependencies':dependencies,'source_sha256':hashes,
             'vendor_calls':0,'credits':0,'dependency_stubs':False,'transport':'synthetic fixtures only'}
    (out/'results.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'output_dir':str(out),'tests_run':result.testsRun,'success':result.wasSuccessful()}))
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
