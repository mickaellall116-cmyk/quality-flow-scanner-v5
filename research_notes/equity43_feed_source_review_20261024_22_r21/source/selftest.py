#!/usr/bin/env python3
"""Offline battery for the -22 pilot (r2.1) — stub transport, stub Gmail,
fake clock. Zero network, zero credential access. The SAME battery runs
against the r1 snapshot (fail-before) and the r2 source (fail-after);
the runner/finalize under test resolve from QF_STAGE_DIR, else from
this file's directory or its parent."""
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

_HERE = os.path.dirname(os.path.abspath(__file__))
if os.environ.get("QF_STAGE_DIR"):
    BASE_DIR = os.environ["QF_STAGE_DIR"]
elif os.path.exists(os.path.join(_HERE, "pilot_runner.py")):
    BASE_DIR = _HERE
elif os.path.exists(os.path.join(os.path.dirname(_HERE),
                                 "pilot_runner.py")):
    BASE_DIR = os.path.dirname(_HERE)
else:
    BASE_DIR = os.path.expanduser("~/workspace/qf_feed_measure_stage")
sys.path.insert(0, BASE_DIR)
import pilot_runner as pr  # noqa: E402
try:
    import finalize_pilot as fin  # noqa: E402
except Exception:  # noqa: BLE001
    fin = None

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

MANIFEST = json.load(open(os.path.join(BASE_DIR, "run_manifest.json")))


def row(sym, day, start, close="10.0", vol="1000"):
    return {"datetime": f"{day} {start}:00", "open": "9.9", "high": "10.1",
            "low": "9.8", "close": close, "volume": vol}


class StubA:
    """NVDA 09:30 bar appears at +180 rung with close 10.0, revised to
    10.5 by finalization; MELI 09:30 bar never appears; others at +60.
    Usage responses use the REAL recorded /api_usage schema; the
    usage_script hook (callable(calls) -> (status, bytes)) overrides
    them for the adversarial budget tests."""

    usage_script = None

    def __init__(self):
        self.calls = 0
        self.series_calls = 0

    def __call__(self, kind, params):
        self.calls += 1
        if kind == "usage":
            if self.usage_script is not None:
                return self.usage_script(self.calls)
            ts = CLOCK["now"].astimezone(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S")
            return 200, json.dumps(
                {"timestamp": ts, "current_usage": 1, "plan_limit": 8,
                 "daily_usage": self.calls, "plan_daily_limit": 800,
                 "plan_category": "basic"}).encode()
        self.series_calls += 1
        sym, day = params["symbol"], params["start_date"][:10]
        now = CLOCK["now"]
        vals = []
        for bs in pr.BAR_STARTS:
            hh, mm = map(int, bs.split(":"))
            start_dt = datetime.fromisoformat(day).replace(
                tzinfo=ET, hour=hh, minute=mm)
            # the feed's bars complete at the true bar close: the final
            # 15:30 bar completes at the 16:00 session close
            close_dt = min(start_dt + timedelta(hours=1),
                           datetime.fromisoformat(day).replace(
                               tzinfo=ET, hour=16, minute=0))
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
check("G schedule census: 757 actions (r2.1 recomputed: +5 pre_revision "
      "usage); final-session revision re-poll "
      "lands Mon 2026-11-02 08:00 EST; pilot_close + final push present",
      dict(census) == {"tripwire": 5, "usage": 21, "ladder": 525,
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

# ---- Scenario A2: session boundary regression (STOP 1)
_acts = pr.build_schedule(MANIFEST)
_by_id = {a["id"]: a for a in _acts}
_st0 = pr.init_state(MANIFEST)
_a2_ok = True
for d in MANIFEST["sessions"]:
    _a2_ok &= _by_id[f"fin|{d}|NVDA|09:30"]["due"] == f"{d}T15:00:00+00:00"
    _a2_ok &= _by_id[f"fin|{d}|NVDA|12:30"]["due"] == f"{d}T18:00:00+00:00"
    _a2_ok &= _by_id[f"fin|{d}|NVDA|15:30"]["due"] == f"{d}T20:30:00+00:00"
    _a2_ok &= _by_id[f"ladder|{d}|NVDA|15:30|60"]["due"] == \
        f"{d}T20:01:00+00:00"
    _a2_ok &= _st0["bars"][f"{d}|NVDA|09:30"]["close_utc"] == \
        f"{d}T14:30:00+00:00"
    _a2_ok &= _st0["bars"][f"{d}|NVDA|12:30"]["close_utc"] == \
        f"{d}T17:30:00+00:00"
    _a2_ok &= _st0["bars"][f"{d}|NVDA|13:30"]["close_utc"] == \
        f"{d}T18:30:00+00:00"
    _a2_ok &= _st0["bars"][f"{d}|NVDA|15:30"]["close_utc"] == \
        f"{d}T20:00:00+00:00"
check("A2 session boundary: 09:30->10:30, 12:30->13:30, 13:30->14:30, "
      "15:30->16:00 closes every session day (final-bar fin due 16:30 ET, "
      "first ladder poll 16:01 ET — never 16:30 close / 17:00 fin)",
      _a2_ok)

# ---- Scenario U: provider budget enforcement (STOP 2)
def usage_body(daily, limit=800, ts=None):
    ts = ts or CLOCK["now"].astimezone(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S")
    return json.dumps({"timestamp": ts, "current_usage": 1,
                       "plan_limit": 8, "daily_usage": daily,
                       "plan_daily_limit": limit,
                       "plan_category": "basic"}).encode()


def u_pilot(script):
    stub = StubA()
    stub.usage_script = script
    return pr.Pilot(MANIFEST, stub, pr.init_state(MANIFEST)), stub


pilot_u1, stub_u1 = u_pilot(lambda n: (200, usage_body(790)))
CLOCK["now"] = datetime(2026, 10, 26, 9, 26, tzinfo=ET)
res = pilot_u1.run_due()
CLOCK["now"] = datetime(2026, 10, 26, 10, 31, tzinfo=ET)
pilot_u1.run_due()
check("U1 provider usage already near 800 -> STOP at baseline, refusal "
      "BEFORE any series call, no request after STOP",
      res == "stopped" and pilot_u1.st["stopped"] is not None
      and pilot_u1.st["stopped"]["reason"].startswith(
          "provider_headroom_exhausted")
      and stub_u1.series_calls == 0,
      f"stopped={pilot_u1.st['stopped']} series={stub_u1.series_calls}")
pilot_u2, stub_u2 = u_pilot(lambda n: (200, b"not-json"))
CLOCK["now"] = datetime(2026, 10, 26, 9, 26, tzinfo=ET)
pilot_u2.run_due()
check("U2 malformed usage body -> STOP usage_data_malformed, no calls",
      pilot_u2.st["stopped"] is not None
      and pilot_u2.st["stopped"]["reason"].startswith(
          "usage_data_malformed") and stub_u2.series_calls == 0,
      f"stopped={pilot_u2.st['stopped']}")
pilot_u3, stub_u3 = u_pilot(lambda n: (500, b"{}"))
CLOCK["now"] = datetime(2026, 10, 26, 9, 26, tzinfo=ET)
pilot_u3.run_due()
check("U3 non-200 usage -> STOP usage_http_500, no series calls",
      pilot_u3.st["stopped"] is not None
      and pilot_u3.st["stopped"]["reason"] == "usage_http_500"
      and stub_u3.series_calls == 0,
      f"stopped={pilot_u3.st['stopped']}")
pilot_u7, stub_u7 = u_pilot(lambda n: (200, usage_body(0, limit=400)))
CLOCK["now"] = datetime(2026, 10, 26, 9, 26, tzinfo=ET)
pilot_u7.run_due()
check("U7 plan_daily_limit != 800 -> STOP plan mismatch",
      pilot_u7.st["stopped"] is not None
      and pilot_u7.st["stopped"]["reason"].startswith(
          "usage_plan_daily_limit_mismatch"),
      f"stopped={pilot_u7.st['stopped']}")
_u4_calls = {"n": 0}


def u4_script(n):
    _u4_calls["n"] += 1
    return 200, usage_body(100)  # counter never moves


pilot_u4, stub_u4 = u_pilot(u4_script)
CLOCK["now"] = datetime(2026, 10, 26, 9, 26, tzinfo=ET)
pilot_u4.run_due()
drive(pilot_u4, datetime(2026, 10, 26, 13, 1, tzinfo=ET))
calls_at_stop = stub_u4.calls
CLOCK["now"] = datetime(2026, 10, 26, 13, 5, tzinfo=ET)
pilot_u4.run_due()
check("U4 provider counter unmoving across >=3 series calls -> STOP "
      "usage_data_stale_counter; no calls after STOP",
      pilot_u4.st["stopped"] is not None
      and pilot_u4.st["stopped"]["reason"] == "usage_data_stale_counter"
      and stub_u4.calls == calls_at_stop,
      f"stopped={pilot_u4.st['stopped']}")
_u5 = {"n": 0}


def u5_script(n):
    _u5["n"] += 1
    if _u5["n"] == 1:
        return 200, usage_body(100)
    return 200, usage_body(100 + n + 10)  # +10 external burn vs desk


pilot_u5, stub_u5 = u_pilot(u5_script)
CLOCK["now"] = datetime(2026, 10, 26, 9, 26, tzinfo=ET)
pilot_u5.run_due()
drive(pilot_u5, datetime(2026, 10, 26, 13, 1, tzinfo=ET))
_u5_events = (pilot_u5.st.get("usage_guard") or {}).get(
    "external_events", [])
check("U5 unrelated-account usage increase (+10 over desk) -> external "
      "event recorded, headroom intact, pilot CONTINUES",
      pilot_u5.st["stopped"] is None and len(_u5_events) >= 1
      and _u5_events[0]["excess"] > 2,
      f"events={_u5_events}")
pilot_u6 = pr.Pilot(MANIFEST, StubA(), pr.init_state(MANIFEST))
if "usage_guard" not in pilot_u6.st or not hasattr(
        pilot_u6, "provider_precheck"):
    check("U6 local<cap but provider headroom < worst-case remaining -> "
          "pre-call refusal; ample headroom -> allowed", False,
          "provider_precheck/usage_guard missing (r1)")
    pilot_u6 = None
if pilot_u6 is not None:
    pilot_u6.st["usage_guard"]["last"] = {
        "daily_usage": 700, "plan_daily_limit": 800,
        "et_date": "2026-10-26", "receipt_utc": "2026-10-26T13:25:00+00:00"}
    pilot_u6.st["usage_guard"]["desk_calls_at_last"] = \
        pilot_u6.st["desk_calls"]
    lad_u6 = next(a for a in pilot_u6.st["actions"]
                  if a["kind"] == "ladder")
    pre_full = pilot_u6.provider_precheck(
        lad_u6, datetime(2026, 10, 26, 9, 26, tzinfo=ET))
    pilot_u6.st["usage_guard"]["last"]["daily_usage"] = 100
    pre_ok = pilot_u6.provider_precheck(
        lad_u6, datetime(2026, 10, 26, 9, 26, tzinfo=ET))
    check("U6 local<cap but provider headroom < worst-case remaining -> "
          "pre-call refusal; ample headroom -> allowed",
          pre_full is not None and "provider_headroom_exhausted" in
          pre_full and pre_ok is None,
          f"pre_full={pre_full} pre_ok={pre_ok}")

# ---- Scenario CL: latency label rule (STOP 3)
if fin is None or not hasattr(fin, "latency_label_for"):
    check("CL finalize exposes the restored §7 label rule", False,
          "latency_label_for missing")
else:
    _full = {d: {"complete": True} for d in MANIFEST["sessions"]}
    _3of5 = {d: {"complete": i < 3}
             for i, d in enumerate(MANIFEST["sessions"])}
    _4of5 = {d: {"complete": i < 4}
             for i, d in enumerate(MANIFEST["sessions"])}
    check("CL1 5/5 complete, not stopped -> LATENCY_MEASURED",
          fin.latency_label_for(_full, None) == "LATENCY_MEASURED")
    check("CL2 3/5 complete (+100 bars fixture) -> LATENCY_UNMEASURED",
          fin.latency_label_for(_3of5, None) == "LATENCY_UNMEASURED")
    check("CL3 4/5 complete -> LATENCY_UNMEASURED; stopped -> UNMEASURED",
          fin.latency_label_for(_4of5, None) == "LATENCY_UNMEASURED"
          and fin.latency_label_for(_full, {"reason": "x"})
          == "LATENCY_UNMEASURED")

# ---- Scenario V: r2.1 residual 1 — revision traffic baseline gating
if os.path.exists(pr.REVIEW_HOLD_PATH):
    os.remove(pr.REVIEW_HOLD_PATH)
if os.path.exists(pr.STOP_PATH):
    os.remove(pr.STOP_PATH)
pilot_v1 = pr.Pilot(MANIFEST, StubA(), pr.init_state(MANIFEST))
rev_action = next(a for a in pilot_v1.st["actions"]
                  if a["kind"] == "revision")
pilot_v1.st["usage_guard"]["last"] = {
    "et_date": "2026-10-26", "daily_usage": 100, "plan_daily_limit": 800}
pilot_v1.st["usage_guard"]["desk_calls_at_last"] = \
    pilot_v1.st["desk_calls"]
now_v = datetime(2026, 10, 27, 8, 0, tzinfo=ET)
pre_v1 = pilot_v1.provider_precheck(rev_action, now_v)
check("V1 revision call with only a PRIOR-day baseline -> refused "
      "usage_baseline_missing_today (no exemption)",
      pre_v1 == "usage_baseline_missing_today", f"pre={pre_v1}")
sched_v = pr.build_schedule(MANIFEST)
from collections import Counter as _Counter
cnt_v = _Counter(a["kind"] for a in sched_v)


def _et_date(a):
    return datetime.fromisoformat(a["due"]).astimezone(ET).date() \
        .isoformat()


rev_days_v = sorted({_et_date(a) for a in sched_v
                     if a["kind"] == "revision"})
order_ok = True
for d in rev_days_v:
    pres = [a for a in sched_v if a["kind"] == "usage"
            and a.get("tag") == "pre_revision" and _et_date(a) == d]
    revs = [a for a in sched_v if a["kind"] == "revision"
            and _et_date(a) == d]
    if len(pres) != 1 or not revs or not all(
            pres[0]["due"] < r["due"] for r in revs):
        order_ok = False
check("V2 census 757 actions / 21 usage, and a 07:55 pre_revision "
      "baseline precedes every 08:00 revision batch",
      len(sched_v) == 757 and cnt_v["usage"] == 21 and order_ok,
      f"n={len(sched_v)} usage={cnt_v['usage']} order_ok={order_ok}")
pilot_v1.st["usage_guard"]["last"] = {
    "et_date": "2026-10-27", "daily_usage": 5, "plan_daily_limit": 800}
pre_v2 = pilot_v1.provider_precheck(rev_action, now_v)
check("V2b fresh same-day baseline -> revision precheck passes",
      pre_v2 is None, f"pre={pre_v2}")


class StubC(StubA):
    """Tue+ /api_usage reports 700 already consumed (near cap)."""

    def __init__(self):
        super().__init__()
        self.series_days = []

    def __call__(self, kind, params):
        now = CLOCK["now"]
        if kind == "usage" and now.astimezone(ET).date().isoformat() \
                >= "2026-10-27":
            ts = now.astimezone(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S")
            return 200, json.dumps(
                {"timestamp": ts, "current_usage": 700, "plan_limit": 8,
                 "daily_usage": 700, "plan_daily_limit": 800,
                 "plan_category": "basic"}).encode()
        if kind != "usage":
            self.series_days.append(
                now.astimezone(ET).date().isoformat())
        return super().__call__(kind, params)


stub_c = StubC()
pilot_v3 = pr.Pilot(MANIFEST, stub_c, pr.init_state(MANIFEST))
CLOCK["now"] = datetime(2026, 10, 26, 9, 20, tzinfo=ET)
res_v3 = drive(pilot_v3, datetime(2026, 10, 27, 8, 30, tzinfo=ET))
check("V3 near-cap 07:55 baseline reading -> pilot STOPs at the "
      "reading, ZERO revision (or any) series calls that day",
      res_v3 == "stopped" and "2026-10-27" not in stub_c.series_days
      and pilot_v3.st["stopped"] is not None
      and "headroom" in pilot_v3.st["stopped"]["reason"],
      f"res={res_v3} stopped={pilot_v3.st['stopped']} "
      f"tue_series={stub_c.series_days.count('2026-10-27')}")

# ---- Scenario DL: raw-data leak closure (STOP 4, tightened by r2.1)
if fin is None:
    check("DL finalize importable for leak fixtures", False)
else:
    import hashlib as _hl
    diag_dl = {"symbol": "AAA", "kind": "value", "column": "Close",
               "bar": "2026-10-26 12:30:00-04:00",
               "stream_value": 777.77, "batch_value": 999.99}
    sink_dl = []
    pub_dl = fin._public_mismatch(diag_dl, sink_dl) \
        if hasattr(fin, "_public_mismatch") else None
    pub_blob = json.dumps(pub_dl) if pub_dl else ""
    unkeyed_dl = {
        _hl.sha256(repr(v).encode()).hexdigest()
        for v in (777.77, 999.99)}
    unkeyed_dl.add(_hl.sha256(json.dumps(
        diag_dl, sort_keys=True, default=str).encode()).hexdigest())
    check("DL1 mismatch records carry a KEYED opaque anchor, never raw "
          "values, never unkeyed per-value or whole-record hashes",
          pub_dl is not None and sink_dl == [diag_dl]
          and len(pub_dl.get("diagnostic_anchor", "")) == 64
          and "777.77" not in pub_blob and "999.99" not in pub_blob
          and all(h not in pub_blob for h in unkeyed_dl),
          f"pub={pub_dl}")
    # end-to-end forced mismatch through the real adapter parity path
    NS = os.path.join(TMP, "leak_ns")
    os.makedirs(os.path.join(NS, "payloads"), exist_ok=True)
    fin.ARCHIVE_NS = NS
    fin.JOURNAL_PATH = os.path.join(NS, "journal.jsonl")
    DAYS = ["2026-10-26", "2026-10-27"]
    SYMS = ["AAA", "BBB", "SPY"]

    def prow(day, bs, close="10.5", vol="1000"):
        return {"datetime": f"{day} {bs}:00", "open": "10.0",
                "high": "11.0", "low": "9.0", "close": close,
                "volume": vol}

    journal = []
    bars = {}

    def payload_for(sym, day, tweak=None):
        rows = []
        for bs in pr.BAR_STARTS:
            c, v = "10.5", "1000"
            if tweak and (bs, "close") in tweak:
                c = tweak[(bs, "close")]
            if tweak and (bs, "volume") in tweak:
                v = tweak[(bs, "volume")]
            rows.append(prow(day, bs, close=c, vol=v))
        return rows

    seq = 0
    for sym in SYMS:
        for day in DAYS:
            tweak = None
            if sym == "AAA" and day == "2026-10-26":
                tweak = {("12:30", "close"): "777.77"}
            if sym == "BBB" and day == "2026-10-26":
                tweak = {("10:30", "volume"): "555555"}
            rows = payload_for(sym, day, tweak)
            seq += 1
            rel = f"payloads/{seq:05d}_{sym}_{day}.json"
            with open(os.path.join(NS, rel), "w") as f:
                json.dump({"values": rows}, f)
            journal.append({"kind": "ladder", "http_status": 200,
                            "payload_file": rel, "symbol": sym})
            for r in rows:
                bs = r["datetime"][11:16]
                lv = {"open": r["open"], "high": r["high"],
                      "low": r["low"], "close": r["close"],
                      "volume": r["volume"]}
                if sym == "AAA" and day == "2026-10-26" and bs == "12:30":
                    lv["close"] = "999.99"   # batch disagrees on price
                if sym == "BBB" and day == "2026-10-26" and bs == "10:30":
                    lv["volume"] = "444444"  # batch disagrees on volume
                bars[f"{day}|{sym}|{bs}"] = {
                    "session": day, "symbol": sym, "bar_start_et": bs,
                    "first_seen": {"lag_s": 61.0, "via": "ladder"},
                    "last_values": lv, "revisions": [],
                    "missing_at_finalization": False}
    with open(fin.JOURNAL_PATH, "w") as f:
        for rec_j in journal:
            f.write(json.dumps(rec_j) + "\n")
    parity = fin.adapter_parity({"bars": bars})
    blob = json.dumps(parity)
    dict_hashes = set()
    for v in (777.77, 999.99, 555555.0, 444444.0,
              "777.77", "999.99", "555555", "444444"):
        dict_hashes.add(_hl.sha256(repr(v).encode()).hexdigest())
        dict_hashes.add(_hl.sha256(str(v).encode()).hexdigest())
    check("DL2 forced price+volume mismatch -> ADAPTER_PARITY_FAIL with "
          "ZERO raw OHLCV and NO unkeyed per-value hash in the public "
          "parity record (keyed anchor only)",
          parity["verdict"] == "ADAPTER_PARITY_FAIL"
          and parity["mismatch_count"] >= 2
          and "777.77" not in blob and "999.99" not in blob
          and "555555" not in blob and "444444" not in blob
          and "diagnostic_anchor" in blob
          and all(h not in blob for h in dict_hashes),
          f"first_mismatch={parity['first_mismatch']}")
    rep = fin.sanitize_reply(
        {"from": "Jane Helper <jane@twelvedata.com>",
         "subject": "Account 4451 reset code 8471",
         "date": "Mon, 26 Oct 2026 09:02:00 -0400",
         "body_text": "Hi Mike, call 561-555-0134. Code 8471. "
                      "PLTR close printed 777.77."}) \
        if hasattr(fin, "sanitize_reply") else {}
    rep_blob = json.dumps(rep)
    check("DL3 TD reply public record is METADATA ONLY (sender domain + "
          "receipt date + classification; no subject, no body, no "
          "mailbox content)",
          rep.get("from_domain") == "twelvedata.com"
          and "classification" in rep
          and set(rep) <= {"from_domain", "received_date",
                           "classification"}
          and all(s not in rep_blob for s in
                  ("8471", "4451", "561-555-0134", "777.77", "Jane",
                   "reset code")),
          f"rep={rep}")

# ---- S21: armed-state schedule consistency (live stage layout only)
_state_path = os.path.join(BASE_DIR, "state", "pilot_state.json")
if os.path.exists(_state_path):
    _armed = json.load(open(_state_path))
    _fresh = pr.init_state(MANIFEST)
    _fa = sorted((a["id"], a["due"]) for a in _fresh["actions"])
    _aa = sorted((a["id"], a["due"]) for a in _armed["actions"])
    _closes_ok = all(
        _armed["bars"][k]["close_utc"] == _fresh["bars"][k]["close_utc"]
        for k in _fresh["bars"])
    check("S21 armed state schedule == fresh pinned build (757 "
          "actions; ids, dues, bar closes identical)",
          _fa == _aa and _closes_ok and len(_aa) == 757,
          f"armed={len(_aa)} closes_ok={_closes_ok}")
else:
    print("SKIP S21 armed-state check (no live state in this layout)")

print("SELFTEST", "PASS" if not fails else f"FAIL {fails}")
sys.exit(1 if fails else 0)
