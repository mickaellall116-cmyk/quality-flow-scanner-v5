"""r2 live P1 parity probe (bounded, read-only, no state writes).

For each symbol: fetch the SERIAL 1d/2y confirmation frame (the frame the
r2 candidate would stash) and the SERIAL 1d/10d daily-close frame (the
original premarket path) back-to-back, then prove:
  1. every overlapping daily row is byte-identical (max abs diff == 0.0);
  2. previous_regular_close(2y) == previous_regular_close(10d) exactly;
  3. the full premarket_fields dict built on the derived prev_close is
     identical to the one built on the fetched prev_close (same 5m frame);
  4. boundary semantics: on the real 2y frame, previous_regular_close at
     fixed `now` values around holiday / early-close / DST boundaries is
     identical whether it reads the full frame or a 10-bar / 3-bar tail
     window (the derivation only ever needs the tail).
Run from the live repo dir so it imports the production modules.
"""
import json
import time

import pandas as pd

import masterscanner_api as m53
import scanner_rules as sr

SYMBOLS = ["NVDA", "AAPL", "MSFT", "COST", "WMT", "XOM", "KO", "JNJ",
           "PG", "JPM", "HD", "AVGO", "BRK-B", "TSLA"]

BOUNDARIES = [
    ("2026-07-06", "Mon after Fri 2026-07-03 Independence-Day-observed holiday"),
    ("2025-12-01", "Mon after Fri 2025-11-28 early close (13:00 ET)"),
    ("2026-01-02", "Fri after Thu 2026-01-01 New Year holiday"),
    ("2025-11-03", "Mon after Sun 2025-11-02 DST fall-back"),
    ("2026-03-09", "Mon after Sun 2026-03-08 DST spring-forward"),
    ("2026-10-14", "today (regular session day)"),
]

results = []
for sym in SYMBOLS:
    rec = {"symbol": sym}
    t0 = time.monotonic()
    daily2y = m53.download_confirmation_data(sym, "1d", "2y")
    rec["t_1d2y_s"] = round(time.monotonic() - t0, 3)
    t0 = time.monotonic()
    daily10 = m53.download_daily_close_data(sym)
    rec["t_1d10d_s"] = round(time.monotonic() - t0, 3)

    rec["rows_2y"] = len(daily2y)
    rec["rows_10d"] = len(daily10)
    common = daily2y.index.intersection(daily10.index)
    rec["overlap_rows"] = len(common)
    maxdiff = 0.0
    for col in ("Open", "High", "Low", "Close", "Volume"):
        d = (daily2y.loc[common, col].astype(float)
             - daily10.loc[common, col].astype(float)).abs().max()
        maxdiff = max(maxdiff, float(d) if pd.notna(d) else 0.0)
    rec["overlap_max_abs_diff"] = maxdiff

    prev_derived = sr.previous_regular_close(daily2y)
    prev_fetched = sr.previous_regular_close(daily10)
    rec["prev_close_derived"] = prev_derived
    rec["prev_close_fetched"] = prev_fetched
    rec["prev_close_exact"] = (prev_derived == prev_fetched)

    t0 = time.monotonic()
    pm5 = m53.download_premarket_data(sym)
    rec["t_5m_s"] = round(time.monotonic() - t0, 3)
    pm_a = sr.premarket_snapshot(pm5, sym, prev_close=prev_derived)
    pm_b = sr.premarket_snapshot(pm5, sym, prev_close=prev_fetched)
    rec["pm_fields_exact"] = (json.dumps(pm_a, default=str, sort_keys=True)
                               == json.dumps(pm_b, default=str, sort_keys=True))
    rec["pm_read"] = pm_a.get("pm_read")

    def _dates(idx):
        return idx.date if idx.tz is None else idx.tz_convert(
            "America/New_York").date

    bounds = []
    for date_str, label in BOUNDARIES:
        now = pd.Timestamp(f"{date_str} 09:00", tz="America/New_York")
        asof = daily2y[_dates(daily2y.index) < now.date()]
        if asof.empty:
            bounds.append({"now": date_str, "label": label, "skip": True})
            continue
        full = sr.previous_regular_close(asof, now=now)
        t10 = sr.previous_regular_close(asof.tail(10), now=now)
        t3 = sr.previous_regular_close(asof.tail(3), now=now)
        bounds.append({
            "now": date_str, "label": label,
            "bar_used_date": str(_dates(asof.index)[-1]),
            "full": full, "tail10": t10, "tail3": t3,
            "exact": bool(full == t10 == t3),
        })
    rec["boundaries"] = bounds
    rec["boundaries_all_exact"] = all(b.get("exact", False)
                                      for b in bounds if not b.get("skip"))
    results.append(rec)
    print(f"{sym}: overlap={rec['overlap_rows']} maxdiff={maxdiff} "
          f"prev_exact={rec['prev_close_exact']} pm_exact={rec['pm_fields_exact']} "
          f"bounds_exact={rec['boundaries_all_exact']}")

summary = {
    "all_overlap_exact_zero": all(r["overlap_max_abs_diff"] == 0.0
                                  for r in results),
    "all_prev_close_exact": all(r["prev_close_exact"] for r in results),
    "all_pm_fields_exact": all(r["pm_fields_exact"] for r in results),
    "all_boundaries_exact": all(r["boundaries_all_exact"] for r in results),
    "results": results,
}
with open("/tmp/feed_r2_evidence/pm_parity_probe_result.json", "w") as fh:
    json.dump(summary, fh, indent=1, default=str)
print("SUMMARY:", {k: v for k, v in summary.items() if k != "results"})
