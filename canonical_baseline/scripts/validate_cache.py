"""Step 6: validate the 4H + daily cache.

For each universe symbol:
  - expected 4H bars in eligible window from the daily calendar
    (2 per full day, 1 per NYSE half-day; half-days detected empirically
    from AAPL's 4H data as days with a single 09:30 bar)
  - actual 4H bars present; missing% = 1 - actual/expected; flag >5%
  - data-quality checks: NaN OHLC, zero-volume bars, dup timestamps,
    tz, impossible wicks (High<max(O,C) etc.)
Also computes effective_4h_from = max(rule eligible_from, 60th 4H bar
for new listings).
Writes canonical_baseline/coverage_report.json
"""
import os, json
import pandas as pd

REPO = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
CB = os.path.join(REPO, "canonical_baseline")
DATA = os.path.join(CB, "data")
WIN_END = pd.Timestamp("2026-09-30", tz="America/New_York")

universe = json.load(open(os.path.join(CB, "universe.json")))

ref = pd.read_pickle(os.path.join(DATA, "h4_AAPL.pkl"))
by_day = ref.groupby(ref.index.date).size()
# NYSE 13:00 early closes in the 4H window (verified: each is a single-bar
# day in AAPL 4H; 2026-01-30 / 2026-02-02 single-bar days are Yahoo 1h gaps,
# not holidays, and count as missing bars)
half_days = {pd.Timestamp(d).date() for d in
             ["2023-11-24", "2024-07-03", "2024-11-29", "2024-12-24",
              "2025-07-03", "2025-11-28", "2025-12-24"]}
empirical_single = sorted(str(d) for d, n in by_day.items() if n == 1 and d not in half_days)
print("empirical single-bar NON-holidays (data gaps):", empirical_single)
print(f"empirical half-days in AAPL 4H ({len(half_days)}):", sorted(str(d) for d in half_days))

report = []
for u in universe:
    s = u["symbol"]
    h4 = pd.read_pickle(os.path.join(DATA, f"h4_{s}.pkl"))
    d1 = pd.read_pickle(os.path.join(DATA, f"d1_{s}.pkl"))
    elig_from = pd.Timestamp(u["eligible_from"], tz="America/New_York")
    # effective 4H start: rule + 60-bar requirement for new listings
    if u["reason"].startswith("new_listing"):
        listing = pd.Timestamp(u["listing_date"], tz="America/New_York")
        bars_from_listing = h4[h4.index >= listing]
        eff = bars_from_listing.index[59] if len(bars_from_listing) >= 60 else None
    else:
        eff = max(elig_from, h4.index[0]) if len(h4) else None
    days = d1[(d1.index >= elig_from) & (d1.index <= WIN_END)].index
    # restrict to days on/after effective 4h start for the 4H expectation
    eff_days = days[days >= eff] if eff is not None else days[:0]
    expected = sum(1 if d.date() in half_days else 2 for d in eff_days)
    actual = int(((h4.index >= eff) & (h4.index <= WIN_END)).sum()) if eff is not None else 0
    missing_pct = round(100 * (1 - actual / expected), 2) if expected else None
    # quality checks on full 4H frame
    q = {
        "nan_ohlc": int(h4[["Open","High","Low","Close"]].isna().any(axis=1).sum()),
        "zero_volume": int((h4["Volume"] == 0).sum()),
        "dup_ts": int(h4.index.duplicated().sum()),
        "bad_wick": int(((h4["High"] < h4[["Open","Close"]].max(axis=1)) |
                         (h4["Low"] > h4[["Open","Close"]].min(axis=1))).sum()),
        "tz_ok": str(h4.index.tz) == "America/New_York",
        "bars_not_0930_1330": int((~pd.Series(h4.index.time).isin(
            [pd.Timestamp("09:30").time(), pd.Timestamp("13:30").time()])).sum()),
    }
    report.append({
        "symbol": s, "eligible_from": u["eligible_from"],
        "effective_4h_from": eff.strftime("%Y-%m-%d") if eff is not None else None,
        "expected_4h": expected, "actual_4h": actual,
        "missing_pct": missing_pct,
        "flagged": bool(missing_pct is not None and missing_pct > 5),
        "quality": q,
    })

flagged = [r for r in report if r["flagged"]]
badq = [r for r in report if any([r["quality"]["nan_ohlc"], r["quality"]["zero_volume"],
                                 r["quality"]["dup_ts"], r["quality"]["bad_wick"],
                                 not r["quality"]["tz_ok"], r["quality"]["bars_not_0930_1330"]])]
json.dump({"half_days": sorted(str(d) for d in half_days),
          "empirical_single_bar_gaps": empirical_single,
          "symbols": report},
          open(os.path.join(CB, "coverage_report.json"), "w"), indent=1)
print(f"symbols: {len(report)} | flagged >5% missing: {len(flagged)}")
for r in flagged: print("  FLAG", r["symbol"], r["missing_pct"], "expected", r["expected_4h"], "actual", r["actual_4h"])
print(f"quality issues: {len(badq)}")
for r in badq: print("  QUAL", r["symbol"], {k: v for k, v in r["quality"].items() if v not in (0, True)})
mp = [r["missing_pct"] for r in report if r["missing_pct"] is not None]
import statistics
print(f"missing% — mean {statistics.mean(mp):.2f}, max {max(mp):.2f}, median {statistics.median(mp):.2f}")
