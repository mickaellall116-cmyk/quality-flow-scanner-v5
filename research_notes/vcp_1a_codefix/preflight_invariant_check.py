#!/usr/bin/env python3
"""QF-VCP-1A-INTERVAL-AUDIT-20261008-05 task 5:
Deterministic preflight check of the flag/status invariant:
    fwd_complete_<h> == (fwd_status_<h> in {'complete','delisted_flat'})
for every row and horizon h in {r3, r6, r12}.

Uses the PRODUCTION functions from research_notes/vcp_1a_codefix/:
  - forward_window(dates, pos, w, series_closed) -> (status, end_index)
  - resolve_horizon_filter(rows, ...) fail-closed schema validation

No vendor requests, no real-data performance. Synthetic dates only.
"""
import sys, itertools
sys.path.insert(0, "/home/hatch/workspace/quality-flow-scanner-v5/research_notes/vcp_1a_codefix")
from build_panels import forward_window, FWD_STATUS_OK
from analyze import resolve_horizon_filter

HORIZONS = {"r3": 63, "r6": 126, "r12": 252}

def trading_dates(n, start_year=2020):
    # synthetic consecutive trading-day date strings
    from datetime import date, timedelta
    out, d = [], date(start_year, 1, 6)  # a Monday
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out

def preflight_check(rows):
    """Deterministic preflight: every row/horizon must satisfy the invariant.
    Returns list of violations (empty = PASS)."""
    bad = []
    for i, r in enumerate(rows):
        for h in HORIZONS:
            st = r.get(f"fwd_status_{h}")
            cp = r.get(f"fwd_complete_{h}")
            if not isinstance(cp, bool) or st not in ("complete", "delisted_flat", "censored"):
                bad.append((i, h, "non-boolean flag or unknown status", st, cp))
            elif cp != (st in FWD_STATUS_OK):
                bad.append((i, h, "invariant violated", st, cp))
    return bad

def synth_row(dates, pos, series_closed, ticker="SYN"):
    r = {"ticker": ticker}
    for h, w in HORIZONS.items():
        st, _ = forward_window(dates, pos, w, series_closed)
        r[f"fwd_status_{h}"] = st
        r[f"fwd_complete_{h}"] = st in FWD_STATUS_OK
    return r

print("== producer-consistency: rows built ONLY via forward_window ==")
scenarios = []
# 1. long open series, mid position -> all complete
d = trading_dates(600); scenarios.append(("open mid", synth_row(d, 100, False)))
# 2. open series near boundary -> r12 censored, r3/r6 complete
scenarios.append(("open near-end", synth_row(d, 500, False)))
# 3. closed series (delisted), window past end -> delisted_flat
d2 = trading_dates(300); scenarios.append(("closed past-end", synth_row(d2, 250, True)))
# 4. closed series, window fits -> complete
scenarios.append(("closed fits", synth_row(d2, 10, True)))
rows = [r for _, r in scenarios]
viol = preflight_check(rows)
print(f"rows={len(rows)} violations={len(viol)} -> {'PASS' if not viol else 'FAIL'}")
for name, r in scenarios:
    print(f"  {name}: " + ", ".join(f"{h}={r[f'fwd_status_{h}']}/{r[f'fwd_complete_{h}']}" for h in HORIZONS))

print("\n== resolve_horizon_filter accepts consistent panel ==")
print(resolve_horizon_filter(rows))

print("\n== adversarial: hand-corrupted invariant row is caught ==")
bad_row = dict(rows[0]); bad_row["fwd_status_r12"] = "censored"; bad_row["fwd_complete_r12"] = True
viol2 = preflight_check([bad_row])
print(f"violations={len(viol2)} -> {'CAUGHT' if viol2 else 'MISSED'}: {viol2[0] if viol2 else ''}")
# resolve_horizon_filter itself does not assert the cross-field invariant (per adjudication);
# the preflight above is the execution-time gate to add.
print("\n== adversarial: missing flag schema -> resolve_horizon_filter hard-errors ==")
try:
    resolve_horizon_filter([{"ticker": "X"}])
    print("MISSED: no error")
except RuntimeError as e:
    print(f"CAUGHT: {e}")

print("\nPREFLIGHT SUITE: " + ("ALL PASS" if not viol and viol2 else "FAIL"))
