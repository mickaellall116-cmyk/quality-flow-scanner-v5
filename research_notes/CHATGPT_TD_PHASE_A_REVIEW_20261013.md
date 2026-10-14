# Independent review — 2026-10-13
Reviewer: ChatGPT. Mike authorized continued autonomous Muse/ChatGPT collaboration at 21:00 ET.

## Twelve Data: ACCEPTED, synthetic integration only
Reviewed main checkout 46bee121b3cd939da2d3eef37b5060ca876310e8 and candidate f64d12f885339e9e2ab4fa38b4a55df78db39b9f.
Muse rerun JSON sha256: 8a093a43cbb31edc0f8c3a146fd3ce08b7fc3d97c0c1b9b30417fccf99a47116.
Compared tests_run, exact passed test list, failures, errors, success, dependencies, vendor_calls, credits, dependency_stubs, transport against candidate integration_results.json: all identical.
Recomputed all eight author's source hashes from git show f64d12f:<path>: all match both manifests. Extra four Muse manifest paths do not invalidate the matching load-bearing subset; pin the explicit subset in future.
16/16 independently reproduced by Muse. Reviewer performed byte/result reconciliation, not another integration rerun.
The reproducibility gap is closed for this NEW pinned synthetic integration evidence. Preserve the Oct 12 stdout-only and calendar-coverage limitations historically; do not retroactively label that artifact fully reproduced.
No live acquisition, historical feed qualification, merge, performance or deployable-edge acceptance follows.

Next core task: QF-TD-ACQUISITION-ADAPTER-PREFLIGHT-20261013-01 r1. Muse to supply a minimal named HTTP adapter and revised pinned acquisition manifest, ascending requests and exact venue/interval/date-end/adjustment contract, account entitlement/retention evidence, shared persisted live limiter, sanitized timeout/error handling, and a predeclared coverage/depth/revision comparison protocol.
Bound: 60 minutes total, at most one 15-minute local repair; scratch/synthetic verification and primary-document review only, no authenticated vendor/API calls, credits, spend, merge, Tiingo input or performance. Existing free-screen authority need not be requested again; actual calls wait for this concrete preflight review. If infeasible return the exact missing prerequisite rather than broadening scope. Historical qualification/baseline recovery remains first priority.

## Phase A: HOLD — delivered happy-path suite passes, adversarial cases fail
store.py sha256 declared 2443dfa14d0c0b9ca756732221daa6d39545c636bafeba1d3bc46457f07f19ee.
Ran original tests/test_store.py: 20/20 PASS; fixtures/run_fixtures.py: 8/8 PASS on clean local checkout, scratch stores only.
Concrete counterexamples reproduced:
1. append_event and ingest accept writes with no lease. Output UNLEASED_WRITE_ACCEPTED ingested.
2. A live owner at injected 12:00 UTC is displaced by a second Store at 15:00:01 UTC solely because age exceeds two hours. Same live PID. Output SECOND_WRITER broke-stale. Displaced owner can still append; two RUN_START events written. PID/age recovery contradicts the required fail-closed owner fencing.
3. Inject RuntimeError in append_event after write_card succeeds. Retry same candidate returns duplicate with state null and only DUPLICATE_SEEN in log. Card write/event commit gap strands the record and next_idea_seq does not account for that orphan.
4. Remove ONLY final newline from an otherwise valid event. append_event accepts tail and appends adjacent JSON objects; subsequent read_events raises JSONDecodeError. It should refuse before mutation, with original bytes preserved.
Additional instruction deviations from source inspection: new_run_id/event IDs use store-local counters rather than required timestamp+nonce/UUID and run-associated event IDs; card writes use exists-check then replace without write-once exclusive installation. Do not claim global uniqueness or concurrent immutability from the happy-path tests.

Reproduction (run from repo root; stdlib only, temp stores):
```python
import sys,tempfile,os,json
from pathlib import Path
sys.path.insert(0,'research_notes/idea_harvest/phase_a')
import store as S
from fixtures.run_fixtures import cand
with tempfile.TemporaryDirectory() as d:
 st=S.Store(Path(d)/'unlocked'); st.init_layout()
 st.append_event('RUN_START','UNLOCKED')
 print('UNLEASED_WRITE_ACCEPTED',st.ingest(cand('Unlocked write probe','probe'),'UNLOCKED')['outcome'])
with tempfile.TemporaryDirectory() as d:
 a=S.Store(d,clock=lambda:'2026-10-13T12:00:00+00:00'); a.acquire_lease('owner-a')
 b=S.Store(d,clock=lambda:'2026-10-13T15:00:01+00:00')
 print('LIVE_PID',os.getpid(),'SECOND_WRITER',b.acquire_lease('owner-b')[0])
 a.append_event('RUN_START','owner-a'); b.append_event('RUN_START','owner-b')
 print('DISPLACED_OWNER_CAN_STILL_APPEND',len(a.read_events())==2)
with tempfile.TemporaryDirectory() as d:
 st=S.Store(d); st.init_layout(); st.acquire_lease('crash-probe')
 original=st.append_event
 def crash(*args,**kwargs): raise RuntimeError('injected after card write, before event')
 st.append_event=crash
 try: st.ingest(cand('Orphan probe','probe'),'crash-probe')
 except RuntimeError: pass
 st.append_event=original
 print('ORPHAN_RETRY',st.ingest(cand('Orphan probe','probe'),'crash-probe'))
with tempfile.TemporaryDirectory() as d:
 st=S.Store(d); st.init_layout(); st.append_event('RUN_START','newline-probe')
 st.log_path.write_bytes(st.log_path.read_bytes().rstrip(b'\n'))
 st.append_event('RUN_END','newline-probe')
 try: st.read_events()
 except Exception as e: print('NEWLINELESS_TAIL_APPEND_CORRUPTS',type(e).__name__)
```

Next secondary task QF-IDEA-PHASE-A-CORRECTNESS-20261013-02 r1: revised isolated candidate, no cutover/Phase B. 60 minutes total with one <=15-minute local repair. Enforce lease ownership on every mutation; no stealing live/unknown owners by age; immutable owner token and safe local OS lock or equivalent fencing; define crash/orphan reconciliation with audit events; exclusive card installation; validate newline/tail before mutation; meet unique-ID amendments.
Add real separate-process contention/owner-loss tests and the four counterexamples above, plus independent stores' ID collision coverage. Preserve original failing evidence, source/migration data and registry bytes. Stop and return a minimal revised design if storage/schema redesign exceeds this bound. This is a newly recorded task, not an unlogged extra repair within the exhausted Phase A build allowance.
Family aliases may both be retained with explicit mapping; historical BLOCKED-DATA migration is acceptable when original disposition is preserved. Neither exception authorizes live cutover.

## Ruflo
No ACK found in fetched bridge comments or Slack as of this review. Request 6157785219 remains pending. Existing collaboration proceeds without waiting for Ruflo; it is secondary to data qualification.
