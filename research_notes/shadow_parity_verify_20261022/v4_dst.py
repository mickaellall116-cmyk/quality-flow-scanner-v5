import sys
sys.path.insert(0, "/home/hatch/workspace/quality-flow-scanner-v5")
sys.dont_write_bytecode = True
import types
stub = types.ModuleType("yfinance")
stub.__getattr__ = lambda a: (_ for _ in ()).throw(RuntimeError("stub"))
sys.modules["yfinance"] = stub
import pandas as pd
from datetime import date, timedelta
from zoneinfo import ZoneInfo
import scanner_rules as sr
ET = ZoneInfo("America/New_York")
rows = {}
days = []
d = date(2026, 10, 26)
while d <= date(2026, 11, 6):
    if d.weekday() < 5:
        days.append(d)
    d += timedelta(days=1)
idx, vals = [], []
for day in days:
    for h in (9, 10, 11, 12, 13, 14, 15):
        idx.append(pd.Timestamp(day.year, day.month, day.day, h, 30, tz="America/New_York"))
        vals.append(100.0)
df = pd.DataFrame({"Open": vals, "High": vals, "Low": vals, "Close": vals,
                   "Volume": [1000] * len(vals)}, index=pd.DatetimeIndex(idx))
now = pd.Timestamp("2026-11-06 20:00", tz="America/New_York")
for name, fn in (("legacy", sr.resample_closed_4h),
                 ("anchored", sr.resample_closed_4h_session_anchored)):
    out = fn(df.copy(), "AAPL", now=now)
    per_day = {}
    for ts in out.index:
        loc = ts.tz_convert("America/New_York")
        per_day.setdefault(str(loc.date()), []).append(loc.strftime("%H:%M"))
    print(name, {k: per_day[k] for k in ("2026-10-30", "2026-11-02", "2026-11-06")})
