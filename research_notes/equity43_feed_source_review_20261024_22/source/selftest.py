#!/usr/bin/env python3
"""Offline self-test for pilot_runner.py — stub transport, fake clock.
Exercises: schedule build, ladder stop-at-first-sighting, first-seen lag,
revision capture, MISSING at finalization, usage snapshots, 429 stop,
cap refusal. No network, no credential access."""
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.expanduser("~/workspace/qf_feed_measure_stage"))
import pilot_runner as pr  # noqa: E402

ET = ZoneInfo("America/New_York")
TMP = tempfile.mkdtemp(prefix="pilot_selftest_")
pr.ARCHIVE_NS = os.path.join(TMP, "archive_ns")
pr.JOURNAL_PATH = os.path.join(pr.ARCHIVE_NS, "journal.jsonl")
pr.STATE_PATH = os.path.join(TMP, "state.json")
pr.STATE_DIR = TMP
pr.STOP_PATH = os.path.join(TMP, "STOP")
pr.CLEAR_PATH = os.path.join(TMP, "tripwire_clear.json")
pr.REVIEW_HOLD_PATH = os.path.join(TMP, "REVIEW_HOLD")
pr.TRIPWIRE_DIR = os.path.join(TMP, "tripwire")
pr.PACE_S = 0
pr.gmail_tripwire_search = lambda: []  # noqa: E731 — clean mailbox default
pr.gmail_read_message = lambda mid: {"id": mid, "body": "stub reply body"}
os.makedirs(os.path.join(pr.ARCHIVE_NS, "payloads"), exist_ok=True)

CLOCK = {"now": datetime(2026, 10, 26, 9, 20, tzinfo=ET)}
pr.now_utc = lambda: CLOCK["now"].astimezone(timezone.utc)  # noqa: E731

MANIFEST = json.load(open(os.path.expanduser(
    "~/workspace/qf_feed_measure_stage/run_manifest.json")))


def row(sym, day, start, close="10.0", vol="1000"):
    return {"datetime": f"{day} {start}:00", "open": "9.9", "high": "10.1",
            "low": "9.8", "close": close, "volume": vol}


class StubA:
    """NVDA 09:30 bar appears at +180 rung with close 10.0, revised to
    10.5 by finalization; MELI 09:30 bar never appears; others at +60."""

    def __init__(self):
        self.calls = 0

    def __call__(self, kind, params):
        self.calls += 1
        if kind == "usage":
            return 200, json.dumps(
                {"current_usage": self.calls, "plan_limit": 800}).encode()
        sym, day = params["symbol"], params["start_date"][:10]
        now = CLOCK["now"]
        vals = []
        for bs in pr.BAR_STARTS:
            hh, mm = map(int, bs.split(":"))
            close_dt = datetime.fromisoformat(day).replace(
                tzinfo=ET, hour=hh, minute=mm) + timedelta(hours=1)
            if sym == "MELI" and bs == "09:30":
                continue  # never appears
            appear = close_dt + timedelta(seconds=60)
            if sym == "NVDA" and bs == "09:30":
                appear = close_dt + timedelta(seconds=180)
            if now >= appear:
                c = "10.0"
                if sym == "NVDA" and bs == "09:30" and \
                        now >= close_dt + timedelta(seconds=1800):
                    c = "10.5"  # revision at finalization
                vals.append(row(sym, day, bs, close=c))
        return 200, json.dumps({"meta": {"symbol": sym, "interval": "1h"},
                                "values": vals, "status": "ok"}).encode()


def drive(pilot, until):
    while True:
        nxt = None
        for a in pilot.st["actions"]:
            if a["status"] == "pending":
                nxt = datetime.fromisoformat(a["due"])
                break
        if nxt is None or nxt > until:
            break
        CLOCK["now"] = (nxt + timedelta(seconds=1)).astimezone(ET)
        st = pilot.run_due()
        if st in ("complete", "stopped"):
            return st
    return "running"


fails = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail else ""))
    if not cond:
        fails.append(name)


# ---- Scenario A: one full session day (2026-10-26) + revision next 08:00
pilot = pr.Pilot(MANIFEST, StubA(), pr.init_state(MANIFEST))
end_day = datetime(2026, 10, 26, 16, 45, tzinfo=ET)
drive(pilot, end_day)
bars = pilot.st["bars"]
nvda = bars["2026-10-26|NVDA|09:30"]
check("A1 NVDA bar first seen at +180 rung",
      nvda["first_seen"] is not None and 180 <= nvda["first_seen"]["lag_s"] < 420,
      f"lag={nvda['first_seen'] and nvda['first_seen']['lag_s']}")
check("A2 NVDA revision recorded at finalization",
      len(nvda["revisions"]) == 1 and
      nvda["revisions"][0]["field_diffs"].get("close") == ["10.0", "10.5"],
      f"revisions={nvda['revisions']}")
meli = bars["2026-10-26|MELI|09:30"]
check("A3 MELI bar missing at finalization",
      meli["first_seen"] is None and meli["missing_at_finalization"])
spy = bars["2026-10-26|SPY|15:30"]
check("A4 SPY last bar first seen, lag in [60,180)",
      spy["first_seen"] is not None and 60 <= spy["first_seen"]["lag_s"] < 180,
      f"lag={spy['first_seen'] and spy['first_seen']['lag_s']}")
check("A5 usage snapshots start/midday/end recorded",
      [s["tag"] for s in pilot.st["usage_snapshots"]] ==
      ["start", "midday", "end"],
      f"{[s['tag'] for s in pilot.st['usage_snapshots']]}")
n_ladder_skips = sum(1 for a in pilot.st["actions"]
                     if a["status"] == "skipped_seen")
check("A6 ladder stops at first sighting (skips exist)", n_ladder_skips > 0,
      f"skips={n_ladder_skips}")
check("A7 desk calls within day cap", pilot.st["desk_calls"] <= 149,
      f"calls={pilot.st['desk_calls']}")
with open(pr.JOURNAL_PATH) as f:
    nlines = sum(1 for _ in f)
check("A8 journal lines == desk calls", nlines == pilot.st["desk_calls"],
      f"journal={nlines} calls={pilot.st['desk_calls']}")
# revision re-poll next morning executes
CLOCK["now"] = datetime(2026, 10, 27, 8, 0, 30, tzinfo=ET)
pilot.run_due()
rev_done = [a for a in pilot.st["actions"]
            if a["kind"] == "revision" and a["session"] == "2026-10-26"
            and a["status"] == "done"]
check("A9 revision re-poll executed for all 5 symbols", len(rev_done) == 5,
      f"done={len(rev_done)}")

# ---- Scenario B: two consecutive 429s stop the pilot
class StubB:
    def __call__(self, kind, params):
        return 429, json.dumps(
            {"code": 429, "message": "rate limit", "status": "error"}).encode()

pilot_b = pr.Pilot(MANIFEST, StubB(), pr.init_state(MANIFEST))
CLOCK["now"] = datetime(2026, 10, 26, 9, 26, tzinfo=ET)
res = pilot_b.run_due()          # usage call -> first 429
CLOCK["now"] = datetime(2026, 10, 26, 10, 31, 5, tzinfo=ET)
res = pilot_b.run_due()          # ladder call -> second consecutive 429
check("B1 two consecutive 429 -> stopped",
      pilot_b.st["stopped"] is not None and
      "429" in pilot_b.st["stopped"]["reason"],
      f"stopped={pilot_b.st['stopped']}")

# ---- Scenario C: cap refusal
pilot_c = pr.Pilot(MANIFEST, StubA(), pr.init_state(MANIFEST))
pilot_c.st["desk_calls"] = 800
a0 = pilot_c.st["actions"][0]
check("C1 total cap refusal", pilot_c.cap_check(a0) is not None)

# ---- Scenario D: email tripwire
pilot_d = pr.Pilot(MANIFEST, StubA(), pr.init_state(MANIFEST))
CLOCK["now"] = datetime(2026, 10, 26, 9, 16, tzinfo=ET)
pilot_d.run_due()
tw = pilot_d.st["tripwire"]
check("D1 clean mailbox -> tripwire clean, no hold",
      tw["checks"] and tw["checks"][-1]["outcome"] == "clean"
      and not tw["hold"], f"checks={tw['checks']}")
msg = {"id": "mX", "from": "Twelve Data <support@twelvedata.com>",
       "subject": "Re: API", "date_utc": "2026-10-27T12:00:00+00:00"}
pr.gmail_tripwire_search = lambda: [msg]  # noqa: E731
CLOCK["now"] = datetime(2026, 10, 27, 9, 16, tzinfo=ET)
res = pilot_d.run_due()
check("D2 reply found -> hold set, run_due held",
      res == "held" and pilot_d.st["tripwire"]["hold"]
      and pilot_d.st["tripwire"]["pending_review"][0]["id"] == "mX",
      f"res={res} hold={pilot_d.st['tripwire']['hold']}")
calls_at_hold = pilot_d.st["desk_calls"]
CLOCK["now"] = datetime(2026, 10, 27, 10, 35, tzinfo=ET)
pilot_d.run_due()
check("D3 while held, no TD calls execute",
      pilot_d.st["desk_calls"] == calls_at_hold,
      f"calls {calls_at_hold} -> {pilot_d.st['desk_calls']}")
with open(pr.CLEAR_PATH, "w") as f:
    json.dump({"verdicts": {"mX": "confirmed"}}, f)
CLOCK["now"] = datetime(2026, 10, 27, 12, 0, tzinfo=ET)
pilot_d.run_due()
stale = [a for a in pilot_d.st["actions"]
         if a["status"] == "missed_late"
         and a.get("missed_cause") == "tripwire_hold"]
check("D4 confirmed clear -> hold lifted, reply filed, stale polls "
      "marked missed_late(tripwire_hold)",
      not pilot_d.st["tripwire"]["hold"]
      and pilot_d.st["tripwire"]["filed"][0]["id"] == "mX"
      and len(stale) > 0,
      f"filed={pilot_d.st['tripwire']['filed']} stale={len(stale)}")
pilot_e = pr.Pilot(MANIFEST, StubA(), pr.init_state(MANIFEST))
msg2 = {**msg, "id": "mY"}
pr.gmail_tripwire_search = lambda: [msg2]  # noqa: E731
CLOCK["now"] = datetime(2026, 10, 26, 9, 16, tzinfo=ET)
pilot_e.run_due()
with open(pr.CLEAR_PATH, "w") as f:
    json.dump({"verdicts": {"mY": "contradiction"}}, f)
res = pilot_e.run_due()
check("D5 contradiction verdict -> TRIPWIRE FIRED stop",
      res == "stopped" and pilot_e.st["stopped"] is not None
      and "TRIPWIRE FIRED" in pilot_e.st["stopped"]["reason"],
      f"stopped={pilot_e.st['stopped']}")
pr.gmail_tripwire_search = lambda: []  # noqa: E731 — restore

# ---- Scenario C2: 149/day hard refusal (ChatGPT item 2a)
pilot_c2 = pr.Pilot(MANIFEST, StubA(), pr.init_state(MANIFEST))
pilot_c2.st["desk_calls_by_day"]["2026-10-26"] = 149
lad0 = next(a for a in pilot_c2.st["actions"] if a["kind"] == "ladder")
check("C2 day cap 149 hard refusal",
      pilot_c2.cap_check(lad0) is not None
      and "149" in pilot_c2.cap_check(lad0),
      f"cap_check={pilot_c2.cap_check(lad0)}")

# ---- Scenario D6: tripwire search ERROR -> hold, no TD calls (item 2b)
def _boom():
    raise RuntimeError("gmail cli unavailable (stub)")

pr.gmail_tripwire_search = _boom
pilot_d6 = pr.Pilot(MANIFEST, StubA(), pr.init_state(MANIFEST))
CLOCK["now"] = datetime(2026, 10, 26, 9, 16, tzinfo=ET)
res = pilot_d6.run_due()
check("D6 tripwire search error -> fail-closed hold, zero TD calls",
      res == "held" and pilot_d6.st["tripwire"]["hold"]
      and pilot_d6.st["tripwire"]["checks"][-1]["outcome"] == "search_failed"
      and pilot_d6.st["desk_calls"] == 0,
      f"res={res} checks={pilot_d6.st['tripwire']['checks']}")
pr.gmail_tripwire_search = lambda: []  # noqa: E731

# ---- Scenario E: ChatGPT source-review gate (comment 6385813954)
with open(pr.REVIEW_HOLD_PATH, "w") as f:
    f.write("source review pending")
pilot_e1 = pr.Pilot(MANIFEST, StubA(), pr.init_state(MANIFEST))
CLOCK["now"] = datetime(2026, 10, 26, 9, 16, tzinfo=ET)
res = pilot_e1.run_due()
CLOCK["now"] = datetime(2026, 10, 26, 9, 26, tzinfo=ET)
res2 = pilot_e1.run_due()
check("E1 review HOLD: tripwire runs, zero TD calls, status held_review",
      res == "held_review" and res2 == "held_review"
      and pilot_e1.st["desk_calls"] == 0
      and pilot_e1.st["tripwire"]["checks"][-1]["outcome"] == "clean",
      f"res={res}/{res2} calls={pilot_e1.st['desk_calls']}")
pilot_e2 = pr.Pilot(MANIFEST, StubA(), pr.init_state(MANIFEST))
CLOCK["now"] = datetime(2026, 10, 26, 7, 0, tzinfo=ET)
pilot_e2.run_due()
os.remove(pr.REVIEW_HOLD_PATH)
CLOCK["now"] = datetime(2026, 10, 26, 9, 26, tzinfo=ET)
pilot_e2.run_due()
check("E2 review clears before windows -> no slip, day proceeds",
      pilot_e2.st["desk_calls"] >= 1
      and not [a for a in pilot_e2.st["actions"]
               if a["status"] == "skipped_review_wait"],
      f"calls={pilot_e2.st['desk_calls']}")
with open(pr.REVIEW_HOLD_PATH, "w") as f:
    f.write("source review pending")
pilot_e3 = pr.Pilot(MANIFEST, StubA(), pr.init_state(MANIFEST))
CLOCK["now"] = datetime(2026, 10, 26, 9, 16, tzinfo=ET)
pilot_e3.run_due()
CLOCK["now"] = datetime(2026, 10, 27, 7, 0, tzinfo=ET)
pilot_e3.run_due()
push_mon = next(a for a in pilot_e3.st["actions"]
                if a["id"] == "push|2026-10-26")
os.remove(pr.REVIEW_HOLD_PATH)
pilot_e3.run_due()
skipped = [a for a in pilot_e3.st["actions"]
           if a["status"] == "skipped_review_wait"]
mon_bars_seen = sum(1 for b in pilot_e3.st["bars"].values()
                    if b["session"] == "2026-10-26" and b["first_seen"])
CLOCK["now"] = datetime(2026, 10, 27, 9, 26, tzinfo=ET)
pilot_e3.run_due()
check("E3 held through Mon -> session slips as review-wait at lift "
      "(148 actions skipped, archive push still ran, no Mon backfill, "
      "Tue proceeds)",
      pilot_e3.st["sessions_status"]["2026-10-26"] == "slipped_review_wait"
      and len(skipped) == 148 and push_mon["status"] == "done"
      and mon_bars_seen == 0 and pilot_e3.st["desk_calls"] > 0,
      f"skipped={len(skipped)} push={push_mon['status']} "
      f"mon_seen={mon_bars_seen} calls={pilot_e3.st['desk_calls']}")

# ---- Scenario F: lateness / no-backfill (item 2d)
pilot_f = pr.Pilot(MANIFEST, StubA(), pr.init_state(MANIFEST))
CLOCK["now"] = datetime(2026, 10, 26, 9, 16, tzinfo=ET)
pilot_f.run_due()
CLOCK["now"] = datetime(2026, 10, 26, 11, 16, tzinfo=ET)
pilot_f.run_due()
nvda_0930 = [a for a in pilot_f.st["actions"]
             if a.get("bar_key") == "2026-10-26|NVDA|09:30"]
CLOCK["now"] = datetime(2026, 10, 26, 12, 0, tzinfo=ET)
pilot_f.run_due()
nvda_bar = pilot_f.st["bars"]["2026-10-26|NVDA|09:30"]
check("F overdue polls marked missed_late and NEVER polled later; the "
      "bar surfaces only as spillover inside a later on-time payload, "
      "stamped with its true lag (no silent backfill)",
      all(a["status"] == "missed_late" for a in nvda_0930)
      and nvda_bar["missing_at_finalization"]
      and nvda_bar["first_seen"] is not None
      and nvda_bar["first_seen"]["lag_s"] >= 5400
      and nvda_bar["first_seen"]["via"] == "finalization"
      and pilot_f.st["desk_calls"] == 6,  # 1 usage + 5 on-time 10:30-bar
      # finalizations; ZERO polls were spent on the overdue 09:30 bar
      f"statuses={[a['status'] for a in nvda_0930]} "
      f"first_seen={nvda_bar['first_seen']}")

# ---- Scenario G: schedule census incl. final Nov 2 revision (item 2e)
from collections import Counter
census = Counter(a["kind"] for a in pr.build_schedule(MANIFEST))
rev_final = [a for a in pr.build_schedule(MANIFEST)
             if a["kind"] == "revision" and a["session"] == "2026-10-30"]
check("G schedule census: 752 actions; final-session revision re-poll "
      "lands Mon 2026-11-02 08:00 EST; pilot_close + final push present",
      dict(census) == {"tripwire": 5, "usage": 16, "ladder": 525,
                       "finalization": 175, "revision": 25,
                       "archive_push": 6}
      and len(rev_final) == 5
      and all(a["due"] == "2026-11-02T13:00:00+00:00" for a in rev_final)
      and any(a["id"] == "usage|2026-11-02|pilot_close"
              for a in pr.build_schedule(MANIFEST)),
      f"census={dict(census)}")

# ---- Scenario H: write-path audit (items 2f + 2g)
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "pilot_runner_fresh",
    os.path.expanduser("~/workspace/qf_feed_measure_stage/pilot_runner.py"))
_fresh = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_fresh)
_repo = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
_write_paths = [_fresh.STATE_PATH, _fresh.JOURNAL_PATH, _fresh.ARCHIVE_NS,
                _fresh.HEARTBEAT_PATH, _fresh.TRIPWIRE_DIR,
                _fresh.CLEAR_PATH, _fresh.REVIEW_HOLD_PATH,
                _fresh.STOP_PATH]
audit_ok = all(p.startswith(_fresh.BASE) and not p.startswith(_repo)
               for p in _write_paths)
raw_ok = (_fresh.ARCHIVE_NS.startswith(
    os.path.join(_fresh.BASE, "archive_clone"))
    and _fresh.JOURNAL_PATH.startswith(_fresh.ARCHIVE_NS))
check("H production-path write rejection + raw-output destinations: "
      "every runner write path sits inside the stage; journal/payloads "
      "only inside the PRIVATE archive clone; none under the production "
      "scanner tree (journal writes follow the JOURNAL_PATH constant — "
      "proven functionally in A8 under a redirected path)",
      audit_ok and raw_ok, f"BASE={_fresh.BASE}")

print("SELFTEST", "PASS" if not fails else f"FAIL {fails}")
sys.exit(1 if fails else 0)
