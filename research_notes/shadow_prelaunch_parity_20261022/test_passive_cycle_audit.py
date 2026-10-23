#!/usr/bin/env python3
"""Offline synthetic evidence for passive-cycle safety gates. No network."""
from datetime import datetime, timedelta, timezone
import copy
from passive_cycle_audit import evaluate

NOW = datetime(2026, 10, 22, 20, 0, tzinfo=timezone.utc)
S = {
  'generated_at': (NOW-timedelta(minutes=2)).isoformat(),
  'interval': '4h', 'rule_version': '2026-09-15-v54',
  'source': 'v54-engine-local', 'count': 1,
  'results': [{
    'symbol':'MSFT', 'signal_id':'v54:MSFT:4h:2026-10-22T13:30:00-04:00:2026-09-15-v54',
    'signal_bar_start_at':'2026-10-22T09:30:00-04:00',
    'signal_bar_close_at':'2026-10-22T13:30:00-04:00',
  }],
  'forward_test': {
    'universe_size':250, 'cohort_sizes':{'UX51':51,'X2':199},
    'last_cycle':{'cycle_status':'HEALTHY','errors':[],'entries_paused':True,'entries_suppressed':True,
                  'coverage':{'global_provider_status':'ok','market_data_gap':False,
                    'expected_symbols':252,'fresh_symbols':252,'degraded_symbols':[],
                    'unresolved_security_events':[]}}
  }
}
P = dict(grid_id='SESSION_ANCHORED_XNYS_AND_CRYPTO_V1',
         scanner_stack_sha256='a'*64, universe_sha256='b'*64, calendar_sha256='c'*64)

def check(name, payload, *, expected=None, paused=True, proof=None):
    r = evaluate(payload, now=NOW, pause_sentinel=paused, producer_grid_proof=proof)
    if expected is None:
        assert r['verdict']=='STRUCTURAL_CANDIDATE_ONLY', (name,r)
    else:
        assert expected in r['reasons'], (name,r)
    print('PASS',name)


def main():
    check('candidate still cannot launch',S,proof=P)
    check('missing independent attestation holds',S,expected='NO_INDEPENDENT_CORRECT_GRID_ATTESTATION')
    check('missing pause sentinel refuses',S,expected='PAUSE_SENTINEL_NOT_PRESENT',paused=False,proof=P)
    x=copy.deepcopy(S);x['generated_at']=(NOW-timedelta(hours=4)).isoformat()
    check('stale snapshot refuses',x,expected='MISSING_FUTURE_OR_STALE_CYCLE_TIMESTAMP',proof=P)
    x=copy.deepcopy(S);x['forward_test']['last_cycle']['cycle_status']='DEGRADED'
    check('degraded cycle refuses',x,expected='ORDINARY_CYCLE_NOT_HEALTHY',proof=P)
    x=copy.deepcopy(S);x['forward_test']['last_cycle']['coverage']['fresh_symbols']=250
    check('incomplete scan refuses',x,expected='COMPLETE_COHORT_AND_MARKET_NOT_PROVEN',proof=P)
    x=copy.deepcopy(S);x['forward_test']['last_cycle']['entries_paused']=False
    check('unpaused refuses',x,expected='PAUSED_SYSTEM_NOT_PROVEN',proof=P)
    x=copy.deepcopy(S);x['count']=0
    check('count mismatch refuses',x,expected='RESULT_COUNT_OR_ARRAY_INVALID',proof=P)
    x=copy.deepcopy(S);x['results'][0]['signal_bar_close_at']='2026-10-23T13:30:00-04:00'
    check('partial/future signal refuses',x,expected='BAD_SIGNAL_ROWS',proof=P)
    x=copy.deepcopy(S);x['results']=[S['results'][0],S['results'][0]];x['count']=2
    check('duplicate ID refuses',x,expected='BAD_SIGNAL_ROWS',proof=P)
    check('no rows still require proof',dict(S,results=[],count=0),expected='NO_INDEPENDENT_CORRECT_GRID_ATTESTATION')
    print('11/11 offline assertions PASS')


if __name__=='__main__': main()
