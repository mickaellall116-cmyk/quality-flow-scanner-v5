#!/usr/bin/env python3
"""Next-day continuity fixture for the Option B clearance successor
(addendum, Issue #1 comments 6432009084 / 6432051510).

Question answered: after the simulated Tue Oct 27 clearance, does the
Oct-27 session then execute NORMALLY and IN ORDER — tripwire, usage
snapshots, ladder polls, finalizations, archive push — under the fixed
runner? Method: same offline harness as test_clearance_fixtures.py
(copied live state, stub transport/Gmail, fake clock). After the
clearance tick (09:20 ET), the fake clock is stepped to each next
pending action's due time (+5s) and run_due is ticked, through the end
of the Oct-27 ET day. The stub transport returns no bars, so every
ladder rung fires — the worst case for call counts; ordering and
completion are what is asserted. Zero network, zero real TD calls.
"""
import copy
import importlib.util
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from importlib.machinery import SourceFileLoader
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
STAGE = os.path.expanduser("~/workspace/qf_feed_measure_stage")
BUILD = os.path.expanduser("~/workspace/qf_td_successor_build")
FIXED_PATH = os.path.join(BUILD, "fixed", "pilot_runner.py")
SCRATCH = os.path.join(BUILD, "scratch", "D")
CLEAR_PAYLOAD = {"verdicts": {"1a174da9074a6edf": "confirmed"}}

LIVE_STATE = json.load(open(os.path.join(STAGE, "state",
                                         "pilot_state.json")))
MANIFEST = json.load(open(os.path.join(STAGE, "run_manifest.json")))
RESULTS, FAILURES = [], []


def check(name, cond, detail=""):
    RESULTS.append({"check": name, "pass": bool(cond), "detail": detail})
    if not cond:
        FAILURES.append(name)
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")


class StubTransport:
    def __init__(self, clock):
        self.calls = []
        self.clock = clock

    def __call__(self, kind, params):
        self.calls.append({"kind": kind, "params": dict(params)})
        if kind == "usage":
            ts = self.clock["now"].astimezone(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S")
            return 200, json.dumps(
                {"timestamp": ts, "current_usage": 1, "plan_limit": 8,
                 "daily_usage": len(self.calls), "plan_daily_limit": 800,
                 "plan_category": "basic"}).encode()
        return 200, json.dumps({"values": []}).encode()


os.makedirs(os.path.join(SCRATCH, "archive_ns", "payloads"),
            exist_ok=True)
loader = SourceFileLoader("pr_fixed_D", FIXED_PATH)
spec = importlib.util.spec_from_loader("pr_fixed_D", loader)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.BASE = SCRATCH
mod.STATE_DIR = SCRATCH
mod.STATE_PATH = os.path.join(SCRATCH, "pilot_state.json")
mod.CLEAR_PATH = os.path.join(SCRATCH, "tripwire_clear.json")
mod.STOP_PATH = os.path.join(SCRATCH, "STOP")
mod.REVIEW_HOLD_PATH = os.path.join(SCRATCH, "REVIEW_HOLD")
mod.TRIPWIRE_DIR = os.path.join(SCRATCH, "tripwire")
mod.ARCHIVE_NS = os.path.join(SCRATCH, "archive_ns")
mod.JOURNAL_PATH = os.path.join(mod.ARCHIVE_NS, "journal.jsonl")
mod.PACE_S = 0
mod.gmail_tripwire_search = lambda: []  # noqa: E731
mod.gmail_read_message = lambda mid: {"id": mid, "body": "stub"}

clock = {"now": datetime(2026, 10, 27, 9, 20, tzinfo=ET)}
mod.now_utc = lambda: clock["now"]
transport = StubTransport(clock)
pilot = mod.Pilot(MANIFEST, transport, state=copy.deepcopy(LIVE_STATE))

# --- clearance (as in Scenario B) -------------------------------------
with open(mod.CLEAR_PATH, "w") as f:
    json.dump(CLEAR_PAYLOAD, f)
pilot.run_due(clock["now"])
check("D: clearance tick done, not stopped",
      pilot.st["stopped"] is None and pilot.st["tripwire"]["hold"] is False)

tue = [a for a in pilot.st["actions"] if a["session"] == "2026-10-27"]
tue_window = [a for a in tue
              if datetime.fromisoformat(a["due"]).astimezone(ET).date()
              .isoformat() == "2026-10-27"]
print(f"Oct-27 session actions: {len(tue)} total, "
      f"{len(tue_window)} due within Oct-27 ET "
      f"(kinds: {dict(Counter(a['kind'] for a in tue_window))})")

# --- step the clock through the rest of the Oct-27 day ----------------
WINDOW_END = datetime(2026, 10, 28, 0, 0, tzinfo=ET)
exec_order = []
ticks = 0
while True:
    nxt = next((a for a in pilot.st["actions"]
                if a["status"] == "pending"), None)
    if nxt is None:
        break
    due = datetime.fromisoformat(nxt["due"])
    if due > WINDOW_END:
        break
    clock["now"] = due + timedelta(seconds=5)
    before = {a["id"]: a["status"] for a in pilot.st["actions"]}
    pilot.run_due(clock["now"])
    ticks += 1
    for a in pilot.st["actions"]:
        if before[a["id"]] == "pending" and a["status"] == "done":
            exec_order.append((a["id"], a["due"]))
    if pilot.st["stopped"]:
        break

print(f"continuity ticks: {ticks}; executed in window: "
      f"{len(exec_order)}")
for aid, due in exec_order[:6]:
    print(f"  first: {aid} due {due}")
for aid, due in exec_order[-3:]:
    print(f"  last:  {aid} due {due}")

tue_after = [a for a in pilot.st["actions"]
             if a["session"] == "2026-10-27"
             and datetime.fromisoformat(a["due"]).astimezone(ET).date()
             .isoformat() == "2026-10-27"]
check("D: every Oct-27 action due within Oct-27 ET is done "
      "(tripwire, usage, ladder, finalization, archive_push)",
      all(a["status"] == "done" for a in tue_after),
      f"census={dict(Counter(a['status'] for a in tue_after))}")
dues = [d for _, d in exec_order]
check("D: executions are in scheduled (due-time) order",
      dues == sorted(dues), f"n={len(dues)}")
kinds_done = Counter(a["kind"] for a in tue_after
                     if a["status"] == "done")
check("D: kind census executed: tripwire 1, usage 4, ladder 105, "
      "finalization 35, archive_push 1",
      kinds_done == {"tripwire": 1, "usage": 4, "ladder": 105,
                     "finalization": 35, "archive_push": 1},
      f"{dict(kinds_done)}")
check("D: Oct-27 TD calls = 144, within the 149/day cap",
      pilot.st["desk_calls_by_day"].get("2026-10-27") == 144
      and pilot.st["desk_calls"] == 144,
      f"by_day={pilot.st['desk_calls_by_day']}")
check("D: no Oct-26 TD calls (zero-call fact still preserved)",
      "2026-10-26" not in pilot.st["desk_calls_by_day"])
wed = [a for a in pilot.st["actions"]
       if a["session"] in ("2026-10-28", "2026-10-29", "2026-10-30")
       or a["id"].startswith("rev|2026-10-27")]
check("D: later sessions untouched (all still pending)",
      all(a["status"] == "pending" for a in wed), f"n={len(wed)}")
check("D: pilot never stopped during the continuity day",
      pilot.st["stopped"] is None)
check("D: journal still reconciles at 757",
      len(pilot.st["actions"]) == 757
      and sum(Counter(a["status"] for a in pilot.st["actions"])
              .values()) == 757,
      f"census={dict(Counter(a['status'] for a in pilot.st['actions']))}")

print(f"\n==== {'CONTINUITY FIXTURE PASS' if not FAILURES else 'FAILURES: ' + str(FAILURES)} ====")
with open(os.path.join(BUILD, "tests", "continuity_results.json"),
          "w") as f:
    json.dump({"failures": FAILURES, "results": RESULTS,
               "exec_order": exec_order, "ticks": ticks,
               "desk_calls_by_day": pilot.st["desk_calls_by_day"]},
              f, indent=1)
sys.exit(1 if FAILURES else 0)
