#!/usr/bin/env python3
"""Offline fixtures for the Option B clearance successor (2026-10-26,
Issue #1 comment 6432130873).

Exercises the tripwire-clearance path of the FIXED pilot_runner.py
against a COPY of the live pilot state (read-only source:
~/workspace/qf_feed_measure_stage/state/pilot_state.json), with stub
transport and stub Gmail. Zero network, zero credential access, zero
Twelve Data calls; the live stage state is never opened for writing.

Scenarios:
  A  clearance-path isolation (process_tripwire_clear called directly):
     past-session stale-marking exactness, current-session untouched,
     repeat-clear idempotence, restart idempotence.
  B  full daemon ticks (run_due): pre-clearance tick stays held; the
     clearance tick stale-marks Monday, executes ONLY current-session
     actions, and preserves the Oct-26 zero-call fact; restart after
     clearance resurrects nothing.
  C  CONTROL — the same clearance run against the PRE-FIX runner
     (work/pilot_runner.py.bak_20261026_optionB_prefix): the defect
     must reproduce (Monday usage/revision actions execute), proving
     the fixture can actually detect the bug the fix removes.

Simulated clearance time: Tue 2026-10-27 09:20 ET (after the 09:15
tripwire action is due, before 09:25), matching the approved ordering.

CORR1 COPY (2026-10-26, comment 6433085265): this is the Option B
fixture suite re-run against the CORR1 runner. Two expectations are
adapted to the corr1 semantics ChatGPT required: under an inherited
hold, the due current-session tripwire action now EXECUTES (and
only it) before clearance — so Scenario A first performs the held
tick, and Scenario B's pre-clearance tick changes exactly the
tripwire action instead of nothing, and its clearance tick then
executes only the pre_revision usage action (the tripwire already
ran, first). Every other assertion is unchanged from the Option B
suite, including the Scenario C control on the pre-fix runner.
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
FIXED_PATH = os.path.join(BUILD, "corr1", "pilot_runner.py")  # CORR1 build
PREFIX_PATH = os.path.join(
    STAGE, "work", "pilot_runner.py.bak_20261026_optionB_prefix")
SCRATCH_ROOT = os.path.join(BUILD, "scratch_corr1")
CLEAR_PAYLOAD = {"verdicts": {"1a174da9074a6edf": "confirmed"}}

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
    (same shape as the r2 selftest stub) and empty series payloads."""

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


def statuses(st):
    return {a["id"]: a["status"] for a in st["actions"]}


def census(st):
    return dict(Counter(a["status"] for a in st["actions"]))


def fresh_pilot(mod, transport):
    return mod.Pilot(MANIFEST, transport,
                     state=copy.deepcopy(LIVE_STATE))


T_HELD = datetime(2026, 10, 27, 9, 16, tzinfo=ET)
T_CLEAR = datetime(2026, 10, 27, 9, 20, tzinfo=ET)
T_AFTER = datetime(2026, 10, 27, 9, 22, tzinfo=ET)

MON_PENDING = [a["id"] for a in LIVE_STATE["actions"]
               if a["session"] == "2026-10-26"
               and a["status"] == "pending"]
MON_USAGE = [i for i in MON_PENDING if i.startswith("usage|2026-10-26")]

print(f"journal: total={len(LIVE_STATE['actions'])} "
      f"census={census(LIVE_STATE)} "
      f"monday_pending={len(MON_PENDING)} monday_usage={MON_USAGE}")

# ------------------------------------------------------------------ A
print("\n=== Scenario A: clearance-path isolation (FIXED) ===")
clock = {"now": T_CLEAR}
scratch = os.path.join(SCRATCH_ROOT, "A")
os.makedirs(scratch, exist_ok=True)
mod = load_module(FIXED_PATH, "pr_fixed_A", scratch, clock)
transport = StubTransport(clock)
pilot = fresh_pilot(mod, transport)
# Corr1: the current session's tripwire check must be recorded clean
# before clearance may lift the hold — serve it via the held tick.
pre_held = statuses(pilot.st)
held_status = pilot.run_due(T_HELD)
held_changed = {i for i in pre_held
                if pre_held[i] != statuses(pilot.st)[i]}
check("A: corr1 held tick returns held", held_status == "held",
      f"status={held_status}")
check("A: corr1 held tick executed ONLY the current-session tripwire",
      held_changed == {"tripwire|2026-10-27"},
      f"changed={held_changed}")
check("A: corr1 held tick made zero transport calls",
      transport.calls == [])
before = statuses(pilot.st)
with open(mod.CLEAR_PATH, "w") as f:
    json.dump(CLEAR_PAYLOAD, f)
ret = pilot.process_tripwire_clear(T_CLEAR)
after = statuses(pilot.st)
changed = {i for i in before if before[i] != after[i]}
mon_changed = {i for i in changed
               if i.startswith(("usage|2026-10-26", "ladder|2026-10-26",
                                "fin|2026-10-26", "rev|2026-10-26",
                                "push|2026-10-26"))}
check("A: clearance returns None (no tripwire fire)", ret is None)
check("A: hold lifted", pilot.st["tripwire"]["hold"] is False)
check("A: pending_review drained",
      pilot.st["tripwire"]["pending_review"] == [])
check("A: reply filed exactly once",
      len(pilot.st["tripwire"]["filed"]) ==
      len(LIVE_STATE["tripwire"]["filed"]) + 1)
check("A: changed set == Monday pending set (149)",
      changed == set(MON_PENDING),
      f"changed={len(changed)} monday_pending={len(MON_PENDING)}")
check("A: all changed are missed_late/tripwire_hold",
      all(after[i] == "missed_late" for i in changed) and
      all(a.get("missed_cause") == "tripwire_hold"
          for a in pilot.st["actions"] if a["id"] in changed))
check("A: the 3 usage|2026-10-26 actions are terminal missed_late",
      all(after[i] == "missed_late" for i in MON_USAGE),
      f"{MON_USAGE}")
check("A: no current-session (>=2026-10-27) action changed",
      all(not i.split("|")[1].startswith(("2026-10-27", "2026-10-28",
                                          "2026-10-29", "2026-10-30",
                                          "2026-11-02"))
          for i in changed))
check("A: clearance made zero transport calls", transport.calls == [])
check("A: desk_calls still 0", pilot.st["desk_calls"] == 0)

snap_actions = copy.deepcopy(pilot.st["actions"])
snap_filed = copy.deepcopy(pilot.st["tripwire"]["filed"])
with open(mod.CLEAR_PATH, "w") as f:
    json.dump(CLEAR_PAYLOAD, f)
pilot.process_tripwire_clear(T_AFTER)
check("A: repeat-clear is a strict no-op",
      pilot.st["actions"] == snap_actions
      and pilot.st["tripwire"]["filed"] == snap_filed)

pilot2 = mod.Pilot(MANIFEST, StubTransport(clock),
                   state=mod.load_state())
check("A: restart reload keeps all 149 missed_late (no resurrection)",
      sum(1 for a in pilot2.st["actions"]
          if a["status"] == "missed_late") == 149)
with open(mod.CLEAR_PATH, "w") as f:
    json.dump(CLEAR_PAYLOAD, f)
pilot2.process_tripwire_clear(T_AFTER)
check("A: post-restart repeat-clear still a no-op",
      pilot2.st["actions"] == snap_actions)

# ------------------------------------------------------------------ B
print("\n=== Scenario B: full daemon ticks (FIXED) ===")
clock = {"now": T_HELD}
scratch = os.path.join(SCRATCH_ROOT, "B")
os.makedirs(scratch, exist_ok=True)
mod = load_module(FIXED_PATH, "pr_fixed_B", scratch, clock)
transport = StubTransport(clock)
pilot = fresh_pilot(mod, transport)
c0 = census(pilot.st)
pre_held = statuses(pilot.st)
status = pilot.run_due(T_HELD)
mid = statuses(pilot.st)
held_executed = {i for i in pre_held
                 if pre_held[i] == "pending" and mid[i] == "done"}
check("B: pre-clearance tick returns held", status == "held",
      f"status={status}")
check("B: corr1 pre-clearance tick executed ONLY the current-session "
      "tripwire (zero TD calls, Monday untouched)",
      held_executed == {"tripwire|2026-10-27"}
      and transport.calls == []
      and Counter(a["status"] for a in pilot.st["actions"]
                  if a["session"] == "2026-10-26")
      == {"done": 1, "pending": 149},
      f"held_executed={held_executed}")

clock["now"] = T_CLEAR
with open(mod.CLEAR_PATH, "w") as f:
    json.dump(CLEAR_PAYLOAD, f)
before = statuses(pilot.st)
status = pilot.run_due(T_CLEAR)
after = statuses(pilot.st)
executed = [i for i in before
            if before[i] == "pending" and after[i] == "done"]
check("B: clearance tick executed ONLY current-session actions",
      all("|2026-10-26" not in i for i in executed),
      f"executed={executed}")
check("B: clearance tick executed only Tue pre_revision usage "
      "(tripwire already ran first, in the held tick)",
      set(executed) == {"usage|2026-10-27|pre_revision"},
      f"executed={executed}")
check("B: across both ticks the executed set is Tue tripwire + Tue "
      "pre_revision usage, tripwire first",
      held_executed | set(executed) ==
      {"usage|2026-10-27|pre_revision", "tripwire|2026-10-27"})
check("B: exactly one TD transport call (Tue pre_revision usage)",
      len(transport.calls) == 1
      and transport.calls[0]["kind"] == "usage",
      f"calls={transport.calls}")
check("B: Oct-26 zero-call fact preserved (no 2026-10-26 day key)",
      pilot.st["desk_calls_by_day"] == {"2026-10-27": 1},
      f"by_day={pilot.st['desk_calls_by_day']}")
mon = [a for a in pilot.st["actions"] if a["session"] == "2026-10-26"]
check("B: Monday census terminal: 1 done + 149 missed_late",
      Counter(a["status"] for a in mon) ==
      {"done": 1, "missed_late": 149},
      f"{Counter(a['status'] for a in mon)}")
tue_ladder = [a for a in pilot.st["actions"]
              if a["session"] == "2026-10-27"
              and a["kind"] == "ladder"]
check("B: Tuesday polls stay live (all ladder pending)",
      all(a["status"] == "pending" for a in tue_ladder),
      f"n={len(tue_ladder)}")
check("B: journal reconciles: total 757",
      sum(census(pilot.st).values()) == 757
      and len(pilot.st["actions"]) == 757,
      f"census={census(pilot.st)}")

pilot3 = mod.Pilot(MANIFEST, transport, state=mod.load_state())
snap = statuses(pilot3.st)
clock["now"] = T_AFTER
pilot3.run_due(T_AFTER)
check("B: restart after clearance resurrects/re-executes nothing",
      statuses(pilot3.st) == snap and len(transport.calls) == 1)

# ------------------------------------------------------------------ C
print("\n=== Scenario C: CONTROL (PRE-FIX runner, defect must show) ===")
clock = {"now": T_CLEAR}
scratch = os.path.join(SCRATCH_ROOT, "C")
os.makedirs(scratch, exist_ok=True)
mod = load_module(PREFIX_PATH, "pr_prefix_C", scratch, clock)
transport = StubTransport(clock)
pilot = fresh_pilot(mod, transport)
with open(mod.CLEAR_PATH, "w") as f:
    json.dump(CLEAR_PAYLOAD, f)
before = statuses(pilot.st)
pilot.run_due(T_CLEAR)
after = statuses(pilot.st)
executed = [i for i in before
            if before[i] == "pending" and after[i] == "done"]
mon_executed = [i for i in executed if "|2026-10-26" in i]
check("C: CONTROL defect reproduced — Monday actions executed",
      len(mon_executed) >= 8, f"monday_executed={mon_executed}")
check("C: CONTROL — the 3 usage|2026-10-26 actions executed (done)",
      all(after[i] == "done" for i in MON_USAGE))
check("C: CONTROL — TD transport calls > 0",
      len(transport.calls) > 0, f"calls={len(transport.calls)}")

print(f"\n==== {'ALL FIXTURES PASS' if not FAILURES else 'FAILURES: ' + str(FAILURES)} ====")
out = {"failures": FAILURES, "results": RESULTS,
       "live_journal_census_before": census(LIVE_STATE),
       "monday_pending": len(MON_PENDING)}
with open(os.path.join(BUILD, "corr1_tests", "fixtures_corr1_results.json"),
          "w") as f:
    json.dump(out, f, indent=1)
sys.exit(1 if FAILURES else 0)
