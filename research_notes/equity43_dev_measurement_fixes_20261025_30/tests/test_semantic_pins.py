"""30 battery: P2 / P3 / P6 / P9 semantic pins.

Run: python3 tests/test_semantic_pins.py  (exit 0 = all hold)

Converts the -27 documented semantics (§2.2 P2, §2.3 P3, §2.6 P6,
§3 P9 — the answers -28 R20 recorded) into executable pins:

  P2  the frozen pine_stack.py copy is hash-verified against the
      -13 results.json P0 pin, then its rank semantics are pinned
      structurally: free0 occurs exactly once (dead code, never
      read); the operative free is recomputed in-loop; contested
      uses the live value; the rank cap is min(2, live free); the
      disposition order is rank -> cap -> sector gate -> heat risk.
      The config's canonical (symbol, signal_idx) processing order
      and the ledger's disposition census (191/326/45/28) reproduce.
  P3  asof_benchmark.py is hash-verified against its P0 pin; its
      16:00 ET completion stamp (early closes included) is pinned
      at source, and the causal selection property is exercised
      functionally: at 09:30/13:30 on day D the frozen rule (last
      index <= t) selects D-1's completed session — delay, never
      leak. The retired midnight construction is shown selecting
      the same day's bar (the -08 defect, fail-before artifact).
  P6  exposure_report.compute_exposure is pinned by hand-computed
      fixtures; the DEV application reproduces the recorded
      ~2.83x flat-equity proxy and reports peak gross ~2.79x on
      the committed-equity bases, max single-position share
      ~1.65x, max concurrency 5 — heat is never exposure.
  P9  parity_check.parity_report() recomputes all three cost
      views from the committed ledger over each view's OWN taken
      set; every check must pass and the committed artifact must
      agree.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "code"))
import exposure_report as xr  # noqa: E402
import parity_check as pc  # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
    if not cond:
        FAILURES.append(name)


def _root():
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    root = _root()
    p13 = os.path.join(
        root, "research_notes", "equity43_dev_order_censor_20261023_13")
    results = json.load(open(os.path.join(p13, "results.json")))
    pins = results["phases"]["P0_pins"]["pins"]
    bundle = os.path.join(
        root, "research_notes",
        "equity43_feed_source_review_20261024_22", "bundle", "engine")

    # ---------------- P2: rank semantics --------------------------
    stack_p = os.path.join(bundle, "pine_stack", "pine_stack.py")
    check("P2: pine_stack copy matches the -13 P0 pin",
          _sha(stack_p) == pins["engine_successor/pine_stack/"
                                "pine_stack.py"])
    src = open(stack_p).read()
    check("P2: free0 occurs exactly once (dead code, never read)",
          src.count("free0") == 1,
          f"count={src.count('free0')}")
    i_free = src.find("free = pb.MAX_CONCURRENT - len(open_pos)")
    i_cont = src.find("contested_now = n_cands_t > free")
    i_cap = src.find("taken_at_t >= min(2, free)")
    check("P2: live in-loop free -> contested -> min(2, free) cap, "
          "in source order",
          -1 < i_free < i_cont < i_cap)
    order = [src.find(f'disposition[idx] = "{d}"') for d in
             ("skipped_rank", "skipped_cap", "skipped_gate",
              "skipped_risk")]
    check("P2: disposition order rank -> cap -> gate -> risk",
          all(x >= 0 for x in order) and order == sorted(order),
          f"{order}")
    check("P2: config pins the canonical (symbol, signal_idx) order",
          results["experiment_config"]["candidate_processing_order"]
          .startswith("canonical (symbol, signal_idx)"))
    ledger = json.load(open(os.path.join(p13, "trade_ledger.json")))
    keys = [(r["symbol"], r["signal_idx"]) for r in ledger]
    check("P2: ledger rows are in canonical order, keys unique",
          keys == sorted(keys) and len(set(keys)) == len(keys))
    from collections import Counter
    disp = Counter(r["disposition_4bps_c1"] for r in ledger)
    check("P2: ledger disposition census 191/326/45/28",
          disp == {"taken": 191, "skipped_rank": 326,
                   "skipped_risk": 45, "skipped_gate": 28},
          f"{dict(disp)}")

    # ---------------- P3: SPY as-of -------------------------------
    asof_p = os.path.join(bundle, "asof_benchmark.py")
    check("P3: asof_benchmark copy matches the -13 P0 pin",
          _sha(asof_p) == pins["asof_benchmark.py"])
    asrc = open(asof_p).read()
    check("P3: 16:00 ET completion stamp pinned at source",
          "SESSION_CLOSE = pd.Timedelta(hours=16)" in asrc
          and "only delay, never leak" in asrc.replace("\n", " ")
          or "never leak" in asrc)
    sys.path.insert(0, bundle)
    import pandas as pd  # noqa: E402
    import asof_benchmark as ab  # noqa: E402

    def intraday(day_closes):
        idx, rows = [], []
        for d, c in day_closes:
            for h in range(9, 16):
                idx.append(pd.Timestamp(
                    f"{d} {h:02d}:30", tz="America/New_York"))
                rows.append({"Open": c, "High": c, "Low": c,
                             "Close": c, "Volume": 100})
        return pd.DataFrame(rows, index=pd.DatetimeIndex(idx))

    frame = intraday([("2025-11-03", 100.0), ("2025-11-04", 200.0),
                      ("2025-11-05", 300.0)])
    daily = ab.build_daily_asof(frame)

    def select(df, ts_et):
        t = pd.Timestamp(ts_et, tz="America/New_York").tz_convert("UTC")
        sel = df.index[df.index <= t]
        return None if len(sel) == 0 else df.loc[sel[-1], "Close"]

    check("P3: as-of stamps are 16:00 ET on the session date",
          all(ts.tz_convert("America/New_York").strftime("%H:%M")
              == "16:00" for ts in daily.index))
    check("P3: at 09:30 on day D the rule selects D-1's close",
          select(daily, "2025-11-04 09:30") == 100.0)
    check("P3: at 13:30 on day D the rule selects D-1's close",
          select(daily, "2025-11-04 13:30") == 100.0)
    check("P3: at 16:00 on day D the rule selects D's close",
          select(daily, "2025-11-04 16:00") == 200.0)
    # Early-close session (2025-07-03, bars end 13:00) is still
    # stamped 16:00: at 14:00 that day the bar is NOT yet visible.
    frame_ec = intraday([("2025-07-02", 50.0), ("2025-07-03", 60.0)])
    daily_ec = ab.build_daily_asof(frame_ec)
    check("P3: early-close bar stamped 16:00 — invisible at 14:00 "
          "(delay, never leak)",
          select(daily_ec, "2025-07-03 14:00") == 50.0
          and select(daily_ec, "2025-07-03 16:00") == 60.0)
    # The retired -08 midnight construction leaks the same day.
    daily_mid = ab.build_daily_midnight(frame)
    check("P3: midnight construction selects the SAME day at 09:30 "
          "(the retired defect, shown for the record)",
          select(daily_mid, "2025-11-04 09:30") == 200.0)

    # ---------------- P6: exposure reporting ----------------------
    t0 = datetime(2025, 1, 6, 9, 30, tzinfo=timezone.utc)
    pos = [{"entry_time": t0, "exit_time": t0 + timedelta(days=3),
            "notional": 300.0},
           {"entry_time": t0 + timedelta(days=1),
            "exit_time": t0 + timedelta(days=2), "notional": 100.0}]
    rep = xr.compute_exposure(pos, lambda t: 100.0)
    check("P6 fixture: peak/mean gross hand-computed (4.0 / 3.5)",
          rep["peak_gross"] == 4.0 and rep["mean_gross"] == 3.5)
    check("P6 fixture: max single share 3.0, concurrency 2",
          rep["max_single_share"] == 3.0
          and rep["max_concurrent"] == 2)
    check("P6 fixture: entry_notional = risk$ / risk_frac",
          xr.entry_notional(100.0, 98.0, 10000.0) == 5000.0)
    try:
        xr.entry_notional(100.0, 100.0, 10000.0)
        check("P6 fixture: zero-width stop refused", False)
    except ValueError:
        check("P6 fixture: zero-width stop refused", True)
    dev = xr.dev_application()
    art = json.load(open(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..",
        "artifacts", "exposure_dev.json")))
    a = dev["basis"]["A_last_mark_le_entry"]
    check("P6 DEV: peak gross ~2.79x on committed-equity basis A",
          abs(a["peak_gross"] - 2.7859) < 0.001
          and abs(art["basis"]["A_last_mark_le_entry"]["peak_gross"]
                  - a["peak_gross"]) < 1e-9,
          f"{a['peak_gross']:.4f}")
    check("P6 DEV: flat-equity cross-check reproduces the recorded "
          "2.83x proxy",
          abs(dev["flat_equity_crosscheck"]["peak_gross"] - 2.8337)
          < 0.001,
          f"{dev['flat_equity_crosscheck']['peak_gross']:.4f}")
    check("P6 DEV: max single-position share ~1.65x equity; "
          "concurrency capped at 5",
          abs(a["max_single_share"] - 1.6453) < 0.001
          and a["max_concurrent"] == 5)

    # ---------------- P9: ledger parity ---------------------------
    rep9 = pc.parity_report()
    check("P9: parity recomputation verdict PASS",
          rep9["verdict"] == "PASS",
          f"{[c['name'] for c in rep9['checks'] if not c['pass']]}")
    check("P9: 25bps view reproduces over its OWN taken set "
          "(189 taken / 185 closed / +0.107509R)",
          rep9["views"]["25bps"]["recomputed"]["taken"] == 189
          and rep9["views"]["25bps"]["recomputed"]["closed"] == 185
          and abs(rep9["views"]["25bps"]["recomputed"]["mean_r"]
                  - 0.107509) < 1e-6)
    art9 = json.load(open(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..",
        "artifacts", "p9_parity.json")))
    check("P9: committed parity artifact agrees with recomputation",
          art9["verdict"] == "PASS"
          and art9["views"]["4bps"]["recomputed"]["sum_r"]
          == rep9["views"]["4bps"]["recomputed"]["sum_r"])

    print("SUMMARY", "FAIL" if FAILURES else "PASS", FAILURES)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
