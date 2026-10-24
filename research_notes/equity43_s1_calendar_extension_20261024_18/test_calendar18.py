#!/usr/bin/env python3
"""QF-EQUITY43-S1-CALENDAR-EXTENSION-20261024-18 — proof battery.

Groups:
  A. prefix integrity (pinned SHA, row equality, byte prefix, first
     appended session, counts/range);
  B. boundary fixtures (Oct-16->next, DST 2026+2027 both directions
     with UTC instants, Thanksgiving early closes, July-3/4 rules,
     Christmas/New Year adjacency incl. the 2027-12-31 NYSE
     New-Year's exception, weekend/holiday exclusion, 2025-01-09
     special closure inside the qualified prefix);
  C. structural rejection (duplicate / missing / out-of-order) via
     the consumer verifier;
  D. tamper battery — altered date / open / close / timezone /
     source pin / table SHA / generator pin must STOP;
  E. fork re-pin — the isolated -17 observer fork (byte-identical
     file, sha 929c1bc4…) under the NEW pin: bins on regular and
     early-close appended sessions, causal BAR emission end-to-end,
     fail-closed rejection beyond the table and on a closure date;
     the original fork table is untouched.
"""
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_table18

PINNED = "/home/hatch/workspace/qf_td17_stage/harness/session_table.json"
PINNED_SHA = ("00c5555c26d391444509e54de322841fa3269b64f3"
              "161a50aa507bf1d2bd416f")
EXTENDED = os.path.join(HERE, "session_table_extended_candidate.json")
FORK_DIR = os.path.join(HERE, "..", "fork18")
ET = ZoneInfo("America/New_York")

RESULTS = []


def check(name, fn):
    try:
        fn()
        RESULTS.append((name, "PASS"))
        print(f"PASS {name}")
    except Exception as e:
        RESULTS.append((name, f"FAIL: {e}"))
        print(f"FAIL {name}: {e}")


def _sha(b):
    return hashlib.sha256(b).hexdigest()


PIN = json.load(open(os.path.join(FORK_DIR, "observer_repin18.json")))
OLD = json.load(open(PINNED))
NEW = json.load(open(EXTENDED))
ROWS = NEW["sessions"]
BY_DATE = {r["date"]: r for r in ROWS}


# ---------------------------------------------------------------- A
def a1():
    assert _sha(open(PINNED, "rb").read()) == PINNED_SHA


def a2():
    assert ROWS[:751] == OLD["sessions"]


def a3():
    seg = lambda rows: json.dumps(rows, separators=(",", ":"),
                                  ensure_ascii=True).encode()
    old_seg, new_seg = seg(OLD["sessions"]), seg(ROWS)
    assert new_seg[:len(old_seg) - 1] == old_seg[:-1]


def a4():
    assert ROWS[751] == {"date": "2026-10-19", "open": "09:30",
                         "close": "16:00"}
    assert date(2026, 10, 19).weekday() == 0  # Monday
    assert "2026-10-17" not in BY_DATE and "2026-10-18" not in BY_DATE


def a5():
    assert len(ROWS) == 1054 and len(ROWS) - 751 == 303
    assert ROWS[-1]["date"] == "2027-12-31"
    assert NEW["session_count"] == 1054


# ---------------------------------------------------------------- B
def _utc_open(dstr):
    dt = datetime.fromisoformat(dstr + "T09:30").replace(tzinfo=ET)
    return dt.astimezone(timezone.utc).strftime("%H:%M")


def b_dst(name, fri, mon, fri_utc, mon_utc):
    def f():
        assert _utc_open(fri) == fri_utc, (fri, _utc_open(fri))
        assert _utc_open(mon) == mon_utc, (mon, _utc_open(mon))
    check(name, f)


def b1():
    assert "2026-11-26" not in BY_DATE                    # Thanksgiving
    assert BY_DATE["2026-11-27"]["close"] == "13:00"      # day after
    assert "2027-11-25" not in BY_DATE
    assert BY_DATE["2027-11-26"]["close"] == "13:00"


def b2():
    # qualified-range anchors
    assert "2026-07-03" not in BY_DATE                    # Jul 4 2026 Sat
    assert BY_DATE["2026-07-02"]["close"] == "16:00"
    assert BY_DATE["2025-07-03"]["close"] == "13:00"      # Jul 4 2025 Fri
    assert BY_DATE["2024-07-03"]["close"] == "13:00"      # Jul 4 2024 Thu
    # extension: Jul 4 2027 Sunday -> Mon Jul 5 closed, Fri Jul 2 regular
    assert BY_DATE["2027-07-02"]["close"] == "16:00"
    assert "2027-07-05" not in BY_DATE


def b3():
    assert BY_DATE["2026-12-24"]["close"] == "13:00"      # Dec 25 2026 Fri
    assert "2026-12-25" not in BY_DATE
    assert BY_DATE["2026-12-31"]["close"] == "16:00"      # regular
    assert "2027-01-01" not in BY_DATE
    # Dec 25 2027 Saturday -> Fri Dec 24 is the OBSERVED closure
    assert "2027-12-24" not in BY_DATE
    assert BY_DATE["2027-12-23"]["close"] == "16:00"
    # NYSE New-Year's exception: Jan 1 2028 Saturday -> Dec 31 2027
    # is a REGULAR session (both pinned libraries agree)
    assert BY_DATE["2027-12-31"]["close"] == "16:00"


def b4():
    for r in ROWS:
        assert date.fromisoformat(r["date"]).weekday() < 5
    for d in ("2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31",
              "2027-06-18", "2027-09-06", "2027-11-25", "2027-12-24"):
        assert d not in BY_DATE, d  # 2027 holidays (incl. observed);
        # Good Friday 2027 = Mar 26 (Easter Sunday Mar 28, 2027)
    assert "2025-01-09" not in BY_DATE  # Carter day of mourning


# ---------------------------------------------------------------- C/D
def _mutated_table(tmp, mutate):
    t = json.loads(open(EXTENDED).read())
    mutate(t)
    p = os.path.join(tmp, "mut.json")
    with open(p, "w") as f:
        f.write(json.dumps(t, separators=(",", ":")) + "\n")
    return p


def _verify(table=EXTENDED, pin=None, gen=None):
    pin = pin or os.path.join(FORK_DIR, "observer_repin18.json")
    gen = gen or os.path.join(HERE, "calendar_gen18.py")
    return verify_table18.verify(table, pin, PINNED, gen)


def c_d():
    ok, detail = _verify()
    assert ok, detail
    tmp = tempfile.mkdtemp(dir=HERE)
    cases = {}

    def t_dup(t):
        t["sessions"].insert(800, dict(t["sessions"][800]))
        t["session_count"] += 1
    cases["duplicate_row"] = t_dup

    def t_missing(t):
        del t["sessions"][800]
        t["session_count"] -= 1
    cases["missing_row"] = t_missing

    def t_order(t):
        t["sessions"][800], t["sessions"][801] = \
            t["sessions"][801], t["sessions"][800]
    cases["out_of_order"] = t_order

    def t_date(t):
        t["sessions"][900]["date"] = "2027-06-16"
    cases["tamper_date"] = t_date

    def t_open(t):
        t["sessions"][900]["open"] = "09:00"
    cases["tamper_open"] = t_open

    def t_close(t):
        t["sessions"][900]["close"] = "15:00"
    cases["tamper_close"] = t_close

    for name, mut in cases.items():
        def make(mut=mut, name=name):
            p = _mutated_table(tmp, mut)
            ok, detail = _verify(table=p)
            assert not ok, f"{name} not rejected"
        check(f"C/D {name} STOPs", make)

    def pin_tamper(field, value):
        pin = json.load(open(os.path.join(FORK_DIR,
                                          "observer_repin18.json")))
        pin[field] = value
        p = os.path.join(tmp, f"pin_{field}.json")
        json.dump(pin, open(p, "w"))
        ok, detail = _verify(pin=p)
        assert not ok, f"pin {field} tamper not rejected"
    check("D tamper_timezone STOPs",
          lambda: pin_tamper("timezone", "America/Chicago"))
    check("D tamper_source_pin STOPs",
          lambda: pin_tamper("supersedes_table_sha256", "0" * 64))
    check("D tamper_table_sha STOPs",
          lambda: pin_tamper("table_sha256", "0" * 64))
    check("D tamper_generator_pin STOPs",
          lambda: pin_tamper("generator_sha256", "0" * 64))


# ---------------------------------------------------------------- E
def _load_fork():
    spec = importlib.util.spec_from_file_location(
        "fwd_observer17", os.path.join(FORK_DIR, "fwd_observer17.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def e1():
    assert _sha(open(os.path.join(FORK_DIR, "fwd_observer17.py"),
                     "rb").read()) == PIN["observer_fork_sha256"]


def e2():
    fo = _load_fork()
    table = fo.SessionTable(json.load(open(
        os.path.join(FORK_DIR, "session_table.json"))))
    b = table.bins("2026-10-19")
    assert b == [("09:30", "13:30", ["09:30", "10:30", "11:30", "12:30"]),
                 ("13:30", "16:00", ["13:30", "14:30", "15:30"])], b
    b = table.bins("2026-11-27")
    assert b == [("09:30", "13:00",
                  ["09:30", "10:30", "11:30", "12:30"])], b
    assert table.expected_starts("2026-10-19") == \
        ["09:30", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30"]


def _feed_day(fo, table, dstr, starts):
    feed = fo.SymbolFeed("TEST", table)
    events = []
    px = 100.0
    for s in starts:
        events += feed.ingest({"datetime": f"{dstr} {s}",
                               "open": px, "high": px + 1, "low": px - 1,
                               "close": px + 0.5, "volume": 1000})
        px += 1
    return events


def e3():
    fo = _load_fork()
    table = fo.SessionTable(json.load(open(
        os.path.join(FORK_DIR, "session_table.json"))))
    ev = _feed_day(fo, table, "2026-10-19",
                   ["09:30", "10:30", "11:30", "12:30",
                    "13:30", "14:30", "15:30"])
    bars = [e for e in ev if e["type"] == "BAR"]
    assert len(bars) == 2, ev
    assert bars[0]["emitted_at"] == "2026-10-19 13:30"
    assert bars[1]["emitted_at"] == "2026-10-19 16:00"
    assert any(e["type"] == "SESSION_COMPLETE" for e in ev)


def e4():
    fo = _load_fork()
    table = fo.SessionTable(json.load(open(
        os.path.join(FORK_DIR, "session_table.json"))))
    ev = _feed_day(fo, table, "2026-11-27",
                   ["09:30", "10:30", "11:30", "12:30"])
    bars = [e for e in ev if e["type"] == "BAR"]
    assert len(bars) == 1 and bars[0]["emitted_at"] == "2026-11-27 13:00", ev


def e5():
    fo = _load_fork()
    table = fo.SessionTable(json.load(open(
        os.path.join(FORK_DIR, "session_table.json"))))
    feed = fo.SymbolFeed("TEST", table)
    ev = feed.ingest({"datetime": "2028-01-03 09:30", "open": 1,
                      "high": 1, "low": 1, "close": 1, "volume": 1})
    assert ev and ev[0]["type"] == "REJECTED" and \
        ev[0]["class"] == "UNKNOWN_SESSION", ev
    ev = feed.ingest({"datetime": "2027-12-24 09:30", "open": 1,
                      "high": 1, "low": 1, "close": 1, "volume": 1})
    assert ev and ev[0]["class"] == "UNKNOWN_SESSION", ev


def e6():
    assert _sha(open(PINNED, "rb").read()) == PINNED_SHA  # original intact
    assert PIN["supersedes_table_sha256"] == PINNED_SHA
    assert PIN["table_sha256"] == _sha(open(
        os.path.join(FORK_DIR, "session_table.json"), "rb").read())


if __name__ == "__main__":
    check("A1 pinned table SHA", a1)
    check("A2 prefix rows equal (751)", a2)
    check("A3 sessions-segment byte prefix", a3)
    check("A4 first appended = 2026-10-19 Mon", a4)
    check("A5 counts 751+303=1054, last 2027-12-31", a5)
    b_dst("B DST 2026 spring (Mar 6->9)", "2026-03-06", "2026-03-09",
          "14:30", "13:30")
    b_dst("B DST 2026 fall (Oct 30->Nov 2)", "2026-10-30", "2026-11-02",
          "13:30", "14:30")
    b_dst("B DST 2027 spring (Mar 12->15)", "2027-03-12", "2027-03-15",
          "14:30", "13:30")
    b_dst("B DST 2027 fall (Nov 5->8)", "2027-11-05", "2027-11-08",
          "13:30", "14:30")
    check("B Thanksgiving early closes 2026+2027", b1)
    check("B July-3/4 rules incl. 2027 Sunday case", b2)
    check("B Christmas/New Year adjacency incl. 2027-12-31", b3)
    check("B weekend/holiday exclusion + special closure", b4)
    check("C/D verifier accepts clean table", lambda: (
        lambda okd: (_ for _ in ()).throw(AssertionError(okd))
        if not _verify()[0] else None)(_verify()[1]))
    c_d()
    check("E1 fork file byte-identical to -17 pin", e1)
    check("E2 fork bins regular + early-close under new pin", e2)
    check("E3 fork causal BAR emission, regular appended day", e3)
    check("E4 fork causal BAR emission, early-close appended day", e4)
    check("E5 fork fail-closed beyond table + on closure date", e5)
    check("E6 repin record consistent; original table untouched", e6)
    n_pass = sum(1 for _, s in RESULTS if s == "PASS")
    print(f"\n{len(RESULTS)} checks: {n_pass} PASS, "
          f"{len(RESULTS) - n_pass} FAIL")
    sys.exit(0 if n_pass == len(RESULTS) else 1)
