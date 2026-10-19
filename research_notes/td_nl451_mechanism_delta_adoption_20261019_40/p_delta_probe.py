#!/usr/bin/env python3
"""QF-TD-NL451-MECHANISM-DELTA-20261019-40 r1 — P-family mechanism delta probe.
Executes ONLY P1-P8, fixed order, against the REAL pinned validate_input.xnys_schedule
+ real pandas_market_calendars 4.5.1. First failure stops (exit 1). One invocation."""
import json, sys
sys.path.insert(0, "/tmp/td40/run")
import pandas as pd
import pandas_market_calendars as mcal
from validate_input import xnys_schedule

NY = "America/New_York"
results = []

def record(pid, ok, detail):
    results.append({"check": pid, "result": "PASS" if ok else "FAIL", "detail": detail})
    print(f"{pid}: {'PASS' if ok else 'FAIL'} — {detail}", flush=True)
    if not ok:
        out = {"task": "QF-TD-NL451-MECHANISM-DELTA-20261019-40 r1",
               "verdict": "HOLD", "failed_at": pid, "checks": results}
        open("/tmp/td40/run/p_delta_results.json", "w").write(json.dumps(out, indent=2))
        sys.exit(1)

def fmt(res):
    if res is None: return None
    o, c = res
    return {"open": o.strftime("%H:%M"), "close": c.strftime("%H:%M"),
            "open_iso": o.isoformat(), "close_iso": c.isoformat()}

def expect(pid, date, want):
    res = xnys_schedule(pd.Timestamp(date))
    got = fmt(res)
    if want is None:
        record(pid, res is None, f"{date} -> {got} (expected None/closed)")
    else:
        ok = got is not None and got["open"] == want[0] and got["close"] == want[1]
        record(pid, ok, f"{date} -> {got} (expected {want[0]}-{want[1]} ET)")
    return res

r = {}
r["P1"] = expect("P1", "2025-01-08", ("09:30", "16:00"))   # regular day
r["P2"] = expect("P2", "2025-01-09", None)                  # Carter closure
r["P3"] = expect("P3", "2024-11-29", ("09:30", "13:00"))    # early close
r["P4"] = expect("P4", "2025-07-03", ("09:30", "13:00"))    # early close
r["P5"] = expect("P5", "2025-01-11", None)                  # weekend (Sat)
r["P6"] = expect("P6", "2025-03-10", ("09:30", "16:00"))    # DST spring regular
r["P7"] = expect("P7", "2025-11-03", ("09:30", "16:00"))    # DST fall regular

# P8: record get_calendar("XNYS") class/name; require P1-P7 through it
cal = mcal.get_calendar("XNYS")
info = {"class": type(cal).__name__, "module": type(cal).__module__,
        "name": getattr(cal, "name", None)}
agree = True
for pid, date in [("P1","2025-01-08"),("P2","2025-01-09"),("P3","2024-11-29"),
                  ("P4","2025-07-03"),("P5","2025-01-11"),("P6","2025-03-10"),
                  ("P7","2025-11-03")]:
    sched = cal.schedule(start_date=date, end_date=date)
    if sched.empty:
        direct = None
    else:
        row = sched.iloc[0]
        direct = (pd.Timestamp(row["market_open"]).tz_convert(NY),
                  pd.Timestamp(row["market_close"]).tz_convert(NY))
    if (direct is None) != (r[pid] is None): agree = False
    elif direct is not None and (direct[0] != r[pid][0] or direct[1] != r[pid][1]): agree = False
record("P8", agree, f"get_calendar('XNYS') -> {info}; P1-P7 reproduced through this calendar object: {agree}")

out = {"task": "QF-TD-NL451-MECHANISM-DELTA-20261019-40 r1",
       "verdict": "PASS", "checks_total": 8, "checks_passed": 8, "checks": results,
       "calendar_identity": info,
       "environment": {"python": sys.version.split()[0], "pmc_version": mcal.__version__}}
open("/tmp/td40/run/p_delta_results.json", "w").write(json.dumps(out, indent=2))
print("ALL 8 P-CHECKS PASS")
