#!/usr/bin/env python3
"""Corr1 fixtures (2026-10-26, Issue #1 comment 6433085265 — ChatGPT
independent review HOLD on the Option B clearance successor).

Defect under test: the Option B successor's own Scenario B output
recorded executed=['usage|2026-10-27|pre_revision',
'tripwire|2026-10-27'] — the current session's first Twelve Data
call ran BEFORE its 09:15 ET tripwire check, because run_due
returned immediately under the inherited hold (tripwire could not
run pre-clearance) and, once clearance lifted the hold, the sorted
due loop reached the overdue 07:55 usage action first.

Corr1 requirements under test:
  ORDER  held -> current-session tripwire check -> clearance ->
         first TD call; ZERO TD calls before the tripwire; the
         pre_revision usage action executes only after the tripwire;
         the clean check alone does NOT lift the inherited hold.
  DIRTY  the current-session check finds a NEW TD reply: the pilot
         stays fail-closed; clearing the PRIOR pending item alone
         does NOT lift the hold; no stale-marking runs; zero TD calls.
  FAIL   the current-session Gmail search fails: fail-closed; the
         prior item's clearance does NOT lift the hold; the
         clearance file is retained for a later tick; repeat
         processing files nothing twice; zero TD calls.

Offline harness identical in discipline to test_clearance_fixtures.py:
a COPY of the live pilot state (read-only source), stub transport,
stub Gmail, fake clock. Zero network, zero Twelve Data calls; the
live stage state is never opened for writing.

Event instrumentation: the pilot's process_tripwire_clear /
execute_tripwire / _call are wrapped to record an ordered event log,
so the ordering claims are asserted on the recorded sequence itself.
"""
import copy
import importlib.util
import json
import os
import sys
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
STAGE = os.path.expanduser("~/workspace/qf_feed_measure_stage")
BUILD = os.path.expanduser("~/workspace/qf_td_successor_build")
CORR1_PATH = os.path.join(BUILD, "corr1", "pilot_runner.py")
SCRATCH_ROOT = os.path.join(BUILD, "scratch_corr1")
CLEAR_PAYLOAD = {"verdicts": {"1a174da9074a6edf": "confirmed"}}
PRIOR_ID = "1a174da9074a6edf"
FAKE_ID = "f17e57c0ffee1234"

LIVE_STATE = json.load(open(os.path.join(STAGE, "state",
                                         "pilot_state.json")))
MANIFEST = json.load(open(os.path.join(STAGE, "run_manifest.json")))

RESULTS = []
FAILURES = []


def check(name, cond, detail=""):
    RESULTS.append({"check": name, "pass": bool(cond), "detail": detail})
    if not cond:
        FAILURES.append(name)
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")


class StubTransport:
    """Records every call; returns the real recorded /api_usage schema
    and empty series payloads (same shape as the Option B fixtures)."""

    def __init__(self, clock):
        self.calls = []
        self.clock = clock

    def __call__(self, kind, params):
        self.calls.append({"kind": kind, "params": dict(params)})
        if kind == "usage":
            from datetime import timezone
            ts = self.clock["now"].astimezone(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S")
            return 200, json.dumps(
                {"timestamp": ts, "current_usage": 1, "plan_limit": 8,
                 "daily_usage": len(self.calls), "plan_daily_limit": 800,
                 "plan_category": "basic"}).encode()
        return 200, json.dumps({"values": []}).encode()


def load_module(path, name, scratch, clock):
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader(name, path)
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    os.makedirs(os.path.join(scratch, "archive_ns", "payloads"),
                exist_ok=True)
    mod.BASE = scratch
    mod.STATE_DIR = scratch
    mod.STATE_PATH = os.path.join(scratch, "pilot_state.json")
    mod.CLEAR_PATH = os.path.join(scratch, "tripwire_clear.json")
    mod.STOP_PATH = os.path.join(scratch, "STOP")
    mod.REVIEW_HOLD_PATH = os.path.join(scratch, "REVIEW_HOLD")
    mod.TRIPWIRE_DIR = os.path.join(scratch, "tripwire")
    mod.ARCHIVE_NS = os.path.join(scratch, "archive_ns")
    mod.JOURNAL_PATH = os.path.join(mod.ARCHIVE_NS, "journal.jsonl")
    mod.PACE_S = 0
    mod.gmail_tripwire_search = lambda: []  # clean mailbox
    mod.gmail_read_message = lambda mid: {"id": mid, "body": "stub"}
    mod.now_utc = lambda: clock["now"]
    return mod


def instrument(pilot, mod, events):
    orig_clear = pilot.process_tripwire_clear
    orig_tw = pilot.execute_tripwire
    orig_call = pilot._call

    def clear_w(now):
        had = os.path.exists(mod.CLEAR_PATH)
        r = orig_clear(now)
        events.append(("clearance_file_consumed" if had
                       else "clearance_none",
                       pilot.st["tripwire"]["hold"]))
        return r

    def tw_w(action, now):
        r = orig_tw(action, now)
        last = pilot.st["tripwire"]["checks"][-1]
        events.append(("tripwire_check", action["id"],
                       last.get("outcome")))
        return r

    def call_w(action):
        events.append(("td_call", action["id"]))
        return orig_call(action)

    pilot.process_tripwire_clear = clear_w
    pilot.execute_tripwire = tw_w
    pilot._call = call_w


def statuses(st):
    return {a["id"]: a["status"] for a in st["actions"]}


def census(st):
    return dict(Counter(a["status"] for a in st["actions"]))


def fresh_pilot(mod, transport):
    return mod.Pilot(MANIFEST, transport,
                     state=copy.deepcopy(LIVE_STATE))


def write_clear(mod, payload=CLEAR_PAYLOAD):
    with open(mod.CLEAR_PATH, "w") as f:
        json.dump(payload, f)


T1 = datetime(2026, 10, 27, 9, 16, tzinfo=ET)   # after 09:15 tripwire
T2 = datetime(2026, 10, 27, 9, 20, tzinfo=ET)   # clearance tick
T3 = datetime(2026, 10, 27, 9, 22, tzinfo=ET)   # repeat / restart ticks
MON = "2026-10-26"

print(f"journal: total={len(LIVE_STATE['actions'])} "
      f"census={census(LIVE_STATE)} desk_calls={LIVE_STATE['desk_calls']}")

# ------------------------------------------------------------- ORDER
print("\n=== Corr1 ORDER: held -> tripwire -> clearance -> first TD call ===")
clock = {"now": T1}
scratch = os.path.join(SCRATCH_ROOT, "ORDER")
os.makedirs(scratch, exist_ok=True)
mod = load_module(CORR1_PATH, "pr_corr1_order", scratch, clock)
transport = StubTransport(clock)
pilot = fresh_pilot(mod, transport)
events = []
instrument(pilot, mod, events)

status = pilot.run_due(T1)
check("ORDER: held tick returns 'held'", status == "held",
      f"status={status}")
check("ORDER: current-session tripwire executed under the hold",
      statuses(pilot.st)["tripwire|2026-10-27"] == "done")
check("ORDER: tripwire check recorded clean for 2026-10-27",
      pilot.st["tripwire"]["checks"][-1]["session"] == "2026-10-27"
      and pilot.st["tripwire"]["checks"][-1]["outcome"] == "clean",
      f"last={pilot.st['tripwire']['checks'][-1]}")
check("ORDER: clean check alone does NOT lift the inherited hold",
      pilot.st["tripwire"]["hold"] is True)
check("ORDER: ZERO TD calls before the tripwire",
      transport.calls == [] and pilot.st["desk_calls"] == 0,
      f"events={events}")
check("ORDER: pre_revision usage did NOT execute before the tripwire",
      statuses(pilot.st)["usage|2026-10-27|pre_revision"] == "pending")
mon = [a for a in pilot.st["actions"] if a["session"] == MON]
check("ORDER: nothing stale-marked before clearance "
      "(Monday still 1 done + 149 pending)",
      Counter(a["status"] for a in mon) == {"done": 1, "pending": 149},
      f"{Counter(a['status'] for a in mon)}")

write_clear(mod)
clock["now"] = T2
status = pilot.run_due(T2)
check("ORDER: clearance tick proceeds (not held/stopped)",
      status == "running", f"status={status}")
check("ORDER: hold lifted by clearance after the clean check",
      pilot.st["tripwire"]["hold"] is False)
seq = [e[0] for e in events]
i_tw = seq.index("tripwire_check")
i_cl = seq.index("clearance_file_consumed")
i_td = seq.index("td_call")
check("ORDER: event sequence tripwire -> clearance -> first TD call",
      i_tw < i_cl < i_td, f"events={events}")
check("ORDER: first TD call is Tue pre_revision usage, after tripwire",
      events[i_td] == ("td_call", "usage|2026-10-27|pre_revision")
      and len(transport.calls) == 1
      and transport.calls[0]["kind"] == "usage",
      f"calls={transport.calls}")
check("ORDER: Oct-26 zero-call fact preserved (no 2026-10-26 day key)",
      pilot.st["desk_calls_by_day"] == {"2026-10-27": 1},
      f"by_day={pilot.st['desk_calls_by_day']}")
mon = [a for a in pilot.st["actions"] if a["session"] == MON]
check("ORDER: Monday census terminal: 1 done + 149 missed_late",
      Counter(a["status"] for a in mon) ==
      {"done": 1, "missed_late": 149}
      and all(a.get("missed_cause") == "tripwire_hold"
              for a in mon if a["status"] == "missed_late"),
      f"{Counter(a['status'] for a in mon)}")
check("ORDER: usage|2026-10-27|start (due 09:25) still pending",
      statuses(pilot.st)["usage|2026-10-27|start"] == "pending")
check("ORDER: journal reconciles: total 757",
      len(pilot.st["actions"]) == 757
      and sum(census(pilot.st).values()) == 757,
      f"census={census(pilot.st)}")

snap = statuses(pilot.st)
n_filed = len(pilot.st["tripwire"]["filed"])
write_clear(mod)
clock["now"] = T3
pilot.run_due(T3)
check("ORDER: repeat-clear is a strict no-op",
      statuses(pilot.st) == snap
      and len(pilot.st["tripwire"]["filed"]) == n_filed
      and len(transport.calls) == 1)

pilot2 = mod.Pilot(MANIFEST, transport, state=mod.load_state())
write_clear(mod)
pilot2.run_due(T3)
check("ORDER: restart + repeat-clear resurrects/re-executes nothing",
      statuses(pilot2.st) == snap and len(transport.calls) == 1
      and sum(1 for a in pilot2.st["actions"]
              if a["status"] == "missed_late") == 149)

# ------------------------------------------------------------- DIRTY
print("\n=== Corr1 DIRTY: new reply at current check -> stays held ===")
clock = {"now": T1}
scratch = os.path.join(SCRATCH_ROOT, "DIRTY")
os.makedirs(scratch, exist_ok=True)
mod = load_module(CORR1_PATH, "pr_corr1_dirty", scratch, clock)
mod.gmail_tripwire_search = lambda: [{
    "id": FAKE_ID, "from": "Twelve Data <api@twelvedata.com>",
    "subject": "Re: Basic tier rights questions",
    "date_utc": "2026-10-27T12:00:00+00:00"}]
transport = StubTransport(clock)
pilot = fresh_pilot(mod, transport)
events = []
instrument(pilot, mod, events)

status = pilot.run_due(T1)
check("DIRTY: held tick returns 'held'", status == "held",
      f"status={status}")
check("DIRTY: current check outcome is reply_pending_review",
      pilot.st["tripwire"]["checks"][-1]["outcome"]
      == "reply_pending_review",
      f"last={pilot.st['tripwire']['checks'][-1]}")
check("DIRTY: new reply joined pending_review alongside the prior item",
      {r["id"] for r in pilot.st["tripwire"]["pending_review"]}
      == {PRIOR_ID, FAKE_ID},
      f"pending={[r['id'] for r in pilot.st['tripwire']['pending_review']]}")
check("DIRTY: zero TD calls", transport.calls == []
      and pilot.st["desk_calls"] == 0)

write_clear(mod)  # verdict for the PRIOR item only
clock["now"] = T2
status = pilot.run_due(T2)
check("DIRTY: prior-item clearance alone does NOT lift the hold",
      pilot.st["tripwire"]["hold"] is True and status == "held",
      f"status={status}")
check("DIRTY: prior item filed, new item still pending",
      [r["id"] for r in pilot.st["tripwire"]["filed"]] == [PRIOR_ID]
      and [r["id"] for r in pilot.st["tripwire"]["pending_review"]]
      == [FAKE_ID])
check("DIRTY: no stale-marking ran (zero missed_late)",
      sum(1 for a in pilot.st["actions"]
          if a["status"] == "missed_late") == 0)
check("DIRTY: still zero TD calls; pre_revision still pending",
      transport.calls == []
      and statuses(pilot.st)["usage|2026-10-27|pre_revision"]
      == "pending")

# -------------------------------------------------------------- FAIL
print("\n=== Corr1 FAIL: search failure at current check -> fail-closed ===")
clock = {"now": T1}
scratch = os.path.join(SCRATCH_ROOT, "FAIL")
os.makedirs(scratch, exist_ok=True)
mod = load_module(CORR1_PATH, "pr_corr1_fail", scratch, clock)


def _boom():
    raise RuntimeError("gmail search unavailable (stub)")


mod.gmail_tripwire_search = _boom
transport = StubTransport(clock)
pilot = fresh_pilot(mod, transport)
events = []
instrument(pilot, mod, events)

status = pilot.run_due(T1)
check("FAIL: held tick returns 'held'", status == "held",
      f"status={status}")
check("FAIL: current check outcome is search_failed",
      pilot.st["tripwire"]["checks"][-1]["outcome"] == "search_failed",
      f"last={pilot.st['tripwire']['checks'][-1]}")
check("FAIL: hold set with reason 'tripwire search failed'",
      pilot.st["tripwire"]["hold"] is True
      and pilot.st["tripwire"]["hold_info"]["reason"]
      == "tripwire search failed")
check("FAIL: zero TD calls", transport.calls == []
      and pilot.st["desk_calls"] == 0)

write_clear(mod)  # verdict for the PRIOR item only
clock["now"] = T2
status = pilot.run_due(T2)
check("FAIL: prior-item clearance does NOT lift after a failed check",
      pilot.st["tripwire"]["hold"] is True and status == "held",
      f"status={status}")
check("FAIL: prior item filed exactly once, pending drained",
      [r["id"] for r in pilot.st["tripwire"]["filed"]] == [PRIOR_ID]
      and pilot.st["tripwire"]["pending_review"] == [])
check("FAIL: clearance file RETAINED for a later tick (corr1 gate)",
      os.path.exists(mod.CLEAR_PATH))
check("FAIL: no stale-marking ran; zero TD calls; pre_revision pending",
      sum(1 for a in pilot.st["actions"]
          if a["status"] == "missed_late") == 0
      and transport.calls == []
      and statuses(pilot.st)["usage|2026-10-27|pre_revision"]
      == "pending")
clock["now"] = T3
pilot.run_due(T3)
check("FAIL: retained file re-processing files nothing twice",
      [r["id"] for r in pilot.st["tripwire"]["filed"]] == [PRIOR_ID]
      and pilot.st["tripwire"]["hold"] is True)

print(f"\n==== {'ALL CORR1 FIXTURES PASS' if not FAILURES else 'FAILURES: ' + str(FAILURES)} ====")
out = {"failures": FAILURES, "results": RESULTS,
       "live_journal_census_before": census(LIVE_STATE)}
with open(os.path.join(BUILD, "corr1_tests", "corr1_results.json"),
          "w") as f:
    json.dump(out, f, indent=1)
sys.exit(1 if FAILURES else 0)
