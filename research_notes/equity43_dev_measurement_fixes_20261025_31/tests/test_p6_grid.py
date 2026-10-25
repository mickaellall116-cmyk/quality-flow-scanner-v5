"""P6 full-grid repair battery (-31).

Pins, with hand-computed exact values:
  1. FAIL-BEFORE fixture (the -30 verdict's case): an exit loss
     lowers equity while another position remains open. The pinned
     -30 entry-only sampler misses the peak (1.5 vs the true grid
     peak 2.25); the successor's full-grid sampler measures it.
  2. Coincident-timestamp convention: at a timestamp carrying both
     an exit and an entry, the sample is POST-EVENT — the exiting
     position is excluded, the entering position is included, and
     equity is the event mark (last in committed order), not the
     coincident bar_close mark.
  3. Fail-closed equity lookup before the first mark.
  4. Real-data invariants: committed-order mark kinds at coincident
     timestamps; grid census (964 / 173 / 148 / 63).
  5. Superseded reproduction: the pinned -30 module reproduces the
     committed -30 artifact exactly.
  6. Superset property: on the same sizing and sampling equity, the
     full-grid peak is >= the entry-only peak.
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "..", "code"))
import exposure_report as er  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
    if not cond:
        FAILS.append(name)


def T(s):
    return datetime.fromisoformat(s)


# ---- Fixture 1: exit loss lowers equity, another position open ----
t0 = T("2025-01-06T09:30:00-05:00")
t1 = T("2025-01-06T13:30:00-05:00")
t2 = T("2025-01-07T09:30:00-05:00")
t3 = T("2025-01-07T13:30:00-05:00")
t4 = T("2025-01-08T09:30:00-05:00")
marks1 = [(t0, 1000.0), (t1, 1000.0), (t2, 400.0), (t3, 400.0)]
pos1 = [{"entry_time": t0, "exit_time": t2, "notional": 600.0},
        {"entry_time": t1, "exit_time": t4, "notional": 900.0}]
eqmap = {t0: 1000.0, t1: 1000.0, t2: 400.0, t3: 400.0, t4: 400.0}

pred = er.load_predecessor()
old = pred.compute_exposure(pos1, lambda t: eqmap[t])
check("F1 fail-before: -30 entry-only peak is 1.5 (misses 2.25)",
      old["peak_gross"] == 1.5 and old["samples"] == 2,
      f"peak={old['peak_gross']} samples={old['samples']}")
check("F1 fail-before: -30 entry-only mean is 1.05",
      old["mean_gross"] == (600.0 / 1000.0 + 1500.0 / 1000.0) / 2)

eq1, series_ts1 = er.committed_order_equity(marks1)
grid1 = er.build_grid(pos1, series_ts1)
new = er.compute_exposure_grid(pos1, eq1, grid1, {t0, t1}, {t2, t4})
check("F1 full grid has 5 samples (entry+exit+series union)",
      new["samples"] == 5, f"samples={new['samples']}")
check("F1 full-grid peak is the exit-timestamp 2.25",
      new["peak_gross"] == 900.0 / 400.0
      and new["peak_gross_at"] == t2
      and "exit" in new["peak_gross_at_classes"],
      f"peak={new['peak_gross']} at={new['peak_gross_at']}")
check("F1 full-grid mean is exact",
      new["mean_gross"] == (600.0 / 1000.0 + 1500.0 / 1000.0
                            + 900.0 / 400.0 + 900.0 / 400.0 + 0.0) / 5,
      f"mean={new['mean_gross']}")
check("F1 full-grid max single share is 2.25 (surviving position "
      "over post-loss equity)",
      new["max_single_share"] == 900.0 / 400.0)

# ---- Fixture 2: coincident exit + entry, post-event convention ----
t4 = T("2025-02-03T09:30:00-05:00")
t5 = T("2025-02-03T13:30:00-05:00")
t6 = T("2025-02-04T09:30:00-05:00")
# committed order at t5: bar_close mark first, event mark second
marks2 = [(t4, 1000.0), (t5, 1000.0), (t5, 800.0), (t6, 800.0)]
pos2 = [{"entry_time": t4, "exit_time": t5, "notional": 500.0},
        {"entry_time": t5, "exit_time": t6, "notional": 300.0}]
eq2, series_ts2 = er.committed_order_equity(marks2)
check("F2 committed-order equity at coincident t5 is the event "
      "mark 800, not the bar_close 1000", eq2(t5) == 800.0)
grid2 = er.build_grid(pos2, series_ts2)
rep2 = er.compute_exposure_grid(pos2, eq2, grid2, {t4, t5}, {t5, t6})
row5 = [r for r in rep2["rows"] if r["t"] == t5][0]
check("F2 post-event sample at t5: exit closed, entry open, "
      "gross = 300/800 = 0.375",
      row5["open"] == 1 and row5["gross"] == 300.0 / 800.0,
      f"open={row5['open']} gross={row5['gross']}")
check("F2 coincident classes recorded at t5",
      "entry" in row5["classes"] and "exit" in row5["classes"])

# ---- Fixture 3: fail-closed equity lookup ----
try:
    eq2(T("2025-02-03T09:29:00-05:00"))
    check("F3 equity before first mark raises", False)
except ValueError:
    check("F3 equity before first mark raises", True)

# ---- Real-data invariants ----
ledger, series = er._load_inputs()
kinds_at = {}
for t, _v, k in series:
    kinds_at.setdefault(t, []).append(k)
multi = {t: ks for t, ks in kinds_at.items() if len(ks) > 1}
order_ok = all(ks == sorted(ks, key=lambda k: 0 if k == "bar_close"
                            else 1) for ks in multi.values())
check("R1 coincident series timestamps order bar_close before "
      "event (committed order)", order_ok and len(multi) > 0,
      f"coincident-mark timestamps={len(multi)}")

art = er.dev_application()
s = art["sampling"]
check("R2 grid census 964 = union; 173 entry; 148 exit; 63 "
      "coincident entry+exit",
      s["grid_timestamps"] == 964 and s["entry_timestamps"] == 173
      and s["exit_timestamps"] == 148
      and s["coincident_entry_exit_timestamps"] == 63
      and s["series_timestamps"] == 964, str(s))

# ---- Superseded reproduction vs the committed -30 artifact ----
root = er._repo_root()
committed30 = json.load(open(os.path.join(
    root, "research_notes", er.PRED_PKG, "artifacts",
    "exposure_dev.json")))
sup = art["superseded_entry_only"]
for basis in ("A_last_mark_le_entry", "B_first_mark_ge_entry"):
    a, b = sup["basis"][basis], committed30["basis"][basis]
    check(f"R3 superseded {basis} reproduced exactly by pinned "
          "-30 code",
          all(a[k] == b[k] for k in ("peak_gross", "mean_gross",
                                     "peak_net",
                                     "max_single_share",
                                     "max_concurrent", "samples")),
          f"peak={a['peak_gross']}")
check("R3 superseded flat cross-check reproduced exactly",
      sup["flat_equity_crosscheck"]["peak_gross"]
      == committed30["flat_equity_crosscheck"]["peak_gross"])

# ---- Superset property (same sizing + sampling equity) ----
check("R4 full-grid peak >= entry-only bridge peak (basis A)",
      art["corrected_full_grid"]["basis"]["A_last_mark_le_entry"]
      ["peak_gross"] >= art["convention_bridge"]["peak_gross"],
      f"full={art['corrected_full_grid']['basis']['A_last_mark_le_entry']['peak_gross']} "
      f"bridge={art['convention_bridge']['peak_gross']}")
check("R4 corrected samples == grid size",
      art["corrected_full_grid"]["basis"]["A_last_mark_le_entry"]
      ["samples"] == 964)

print("BATTERY", "FAIL" if FAILS else "PASS", f"({len(FAILS)} fails)")
raise SystemExit(1 if FAILS else 0)
