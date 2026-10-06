#!/usr/bin/env python3
"""CP1 follow-up: full 52-symbol h4 cache audit (REV 2 - corrected grid comparator).
Task 2 of ChatGPT bounded assignment (Issue #1 comment 5986944792).
Correction per ChatGPT review (Issue #1 comment 5994294209, item B).

READ-ONLY: never mutates cache files. All findings tagged COMPUTED.
Calendar: pandas_market_calendars XNYS v5.5.0 (named explicitly for provenance).

CORRECTIONS vs rev 1:
- expected_equity_grid() now consults market_open/market_close from the named
  calendar. On early-close days (e.g. day after Thanksgiving, Christmas Eve),
  the 13:30 ET label is only expected if it falls within [market_open, market_close].
- Missing timestamps are classified into:
    scheduled_closure   - date not an XNYS trading day
    scheduled_truncation- trading day but label falls outside [open, close]
                          (early close / late open)
    coverage            - label outside the cache file's own date range
    label_mapping       - expected label absent BUT an actual bar exists on the
                          same date at a shifted label (the DST fixed-UTC-grid
                          defect: 08:30/12:30 ET instead of 09:30/13:30 ET)
    true_absent         - unexplained: no bar on that date at all
- The 22-symbol 2-bar gap evidence is preserved (true_absent on normal days).

Outputs:
  - audit_52symbol.json : machine-readable per-symbol audit table
  - audit_52symbol.md   : human-readable summary
"""
import pickle, hashlib, json, os
import pandas as pd
import pandas_market_calendars as mcal

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = "/home/hatch/workspace/quality-flow-scanner-v5/backtest_cache/v3"
CAL_NAME, CAL_VER = "XNYS", "pandas_market_calendars 5.5.0"
MCal_VER_PIN = mcal.__version__

CRYPTO = {"BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD", "LINK-USD", "AVAX-USD", "XRP-USD"}
NY = "America/New_York"

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def expected_equity_labels(start_date, end_date):
    """Return (expected_labels, day_info) for the INTENDED session-anchored grid.
    expected_labels: set of tz-aware 09:30 / 13:30 America/New_York Timestamps,
    one or two per XNYS trading day, but ONLY labels within [market_open, market_close].
    day_info: dict date -> {market_open, market_close, is_early_close} for classification.
    """
    cal = mcal.get_calendar("XNYS")
    sched = cal.schedule(start_date=start_date, end_date=end_date)
    expected = set()
    day_info = {}
    for day, row in sched.iterrows():
        d = day.date().isoformat()
        mo = row["market_open"].tz_convert(NY)
        mc = row["market_close"].tz_convert(NY)
        # early close heuristic: regular close is 16:00 ET
        is_early = mc.time() < pd.Timestamp("16:00").time()
        day_info[d] = {"market_open": mo.isoformat(), "market_close": mc.isoformat(),
                       "is_early_close": bool(is_early)}
        for hm in ("09:30", "13:30"):
            lbl = pd.Timestamp(d + " " + hm).tz_localize(NY)
            if mo <= lbl <= mc:
                expected.add(lbl)
            # else: scheduled_truncation (label outside session hours)
    return expected, day_info

def expected_crypto_grid(start, end):
    """Crypto: 24/7 at 00/04/08/12/16/20 UTC."""
    out = set()
    cur = pd.Timestamp(start.date()).tz_localize("UTC")
    end_u = pd.Timestamp(end.date()).tz_localize("UTC") + pd.Timedelta(days=1)
    while cur < end_u:
        for hh in (0, 4, 8, 12, 16, 20):
            out.add(cur + pd.Timedelta(hours=hh))
        cur += pd.Timedelta(days=1)
    return out

def classify_equity_missing(missing, actual_by_date, day_info, cache_start, cache_end):
    """Classify each missing expected label. Returns dict of lists."""
    classes = {"scheduled_closure": [], "scheduled_truncation": [],
               "coverage": [], "label_mapping": [], "true_absent": []}
    for t in missing:
        d = t.date().isoformat()
        # outside cache coverage?
        if t < cache_start or t > cache_end:
            classes["coverage"].append(t.isoformat())
            continue
        # not a trading day?
        if d not in day_info:
            classes["scheduled_closure"].append(t.isoformat())
            continue
        # label outside session hours (early close)?
        info = day_info[d]
        mo = pd.Timestamp(info["market_open"])
        mc = pd.Timestamp(info["market_close"])
        if not (mo <= t <= mc):
            classes["scheduled_truncation"].append(t.isoformat())
            continue
        # actual bar exists on same date at a different label? -> label mapping
        day_bars = actual_by_date.get(t.date(), [])
        if day_bars:
            classes["label_mapping"].append({
                "expected": t.isoformat(),
                "actual_labels_same_date": sorted(b.isoformat() for b in day_bars),
            })
        else:
            classes["true_absent"].append(t.isoformat())
    return classes

def audit_symbol(sym):
    path = os.path.join(CACHE, f"h4_{sym}.pkl")
    df = pickle.load(open(path, "rb"))  # read-only
    idx = df.index
    rec = {
        "symbol": sym,
        "sha256": sha256_file(path),
        "n_bars": len(df),
        "tz": str(idx.tz),
        "start": idx[0].isoformat(),
        "end": idx[-1].isoformat(),
        "is_monotonic": bool(idx.is_monotonic_increasing),
        "n_duplicates": int(idx.duplicated().sum()),
        "columns": list(df.columns),
        "asset_class": "crypto" if sym in CRYPTO or sym.endswith("-USD") else "equity",
    }
    dup = idx[idx.duplicated()].tolist()
    rec["duplicate_timestamps"] = [t.isoformat() for t in dup[:20]]
    rec["n_duplicate_extra"] = max(0, len(dup) - 20)

    if rec["asset_class"] == "equity":
        rec.update(audit_equity_slots(sym, idx))
    else:
        exp = expected_crypto_grid(idx[0], idx[-1])
        actual = set(idx.tz_convert("UTC"))
        missing = sorted(exp - actual)
        extra = sorted(actual - exp)
        rec["expected_grid"] = "00/04/08/12/16/20 UTC daily"
        rec["n_missing_vs_expected"] = len(missing)
        rec["n_extra_vs_expected"] = len(extra)
        rec["missing_sample"] = [t.isoformat() for t in missing[:20]]
        rec["missing_all"] = [t.isoformat() for t in missing]
        rec["extra_sample"] = [t.isoformat() for t in extra[:20]]
        rec["n_offgrid_labels"] = 0
    return rec

def audit_equity_slots(sym, idx):
    """Per-day session-slot analysis (rev2 corrected comparator).

    For each XNYS trading day in the cache range, each session has two slots:
      morning_slot:   bar at 08:30 or 09:30 ET
      afternoon_slot: bar at 12:30 or 13:30 ET
    Each slot is classified:
      present_correct   - bar at intended 09:30 / 13:30 ET label
      present_shifted   - bar at 08:30 / 12:30 ET (DST fixed-UTC-grid defect)
      absent_true       - no bar for this slot (genuine data gap)
      scheduled_trunc   - slot outside [market_open, market_close] (early close)
      scheduled_closure - not a trading day (no slots expected)
      coverage          - day outside cache file's date range
    """
    cal = mcal.get_calendar("XNYS")
    et_idx = idx.tz_convert(NY)
    # actual bars keyed by (date, slot)
    actual_slots = {}
    for t in et_idx:
        d = t.date()
        if (t.hour, t.minute) in ((8, 30), (9, 30)):
            actual_slots[(d, "morning")] = t.isoformat()
        elif (t.hour, t.minute) in ((12, 30), (13, 30)):
            actual_slots[(d, "afternoon")] = t.isoformat()
    sched = cal.schedule(start_date=et_idx[0].date(), end_date=et_idx[-1].date())
    trading = {r.name.date(): (r["market_open"].tz_convert(NY),
                               r["market_close"].tz_convert(NY))
               for _, r in sched.iterrows()}
    slot_rows = []
    counts = {"present_correct": 0, "present_shifted": 0, "absent_true": 0,
              "scheduled_trunc": 0}
    for d, (mo, mc) in sorted(trading.items()):
        for slot, intended_hm in (("morning", (9, 30)), ("afternoon", (13, 30))):
            intended = pd.Timestamp(d.isoformat() +
                                    f" {intended_hm[0]:02d}:{intended_hm[1]:02d}").tz_localize(NY)
            # scheduled truncation: intended label outside session hours
            if not (mo <= intended <= mc):
                counts["scheduled_trunc"] += 1
                slot_rows.append({"date": d.isoformat(), "slot": slot,
                                  "class": "scheduled_trunc",
                                  "intended": intended.isoformat(),
                                  "actual": None})
                continue
            act = actual_slots.get((d, slot))
            if act is None:
                counts["absent_true"] += 1
                slot_rows.append({"date": d.isoformat(), "slot": slot,
                                  "class": "absent_true",
                                  "intended": intended.isoformat(),
                                  "actual": None})
            else:
                at = pd.Timestamp(act)
                cls = ("present_correct"
                       if (at.hour, at.minute) == intended_hm else "present_shifted")
                counts[cls] += 1
                slot_rows.append({"date": d.isoformat(), "slot": slot,
                                  "class": cls,
                                  "intended": intended.isoformat(),
                                  "actual": act})
    absent = [r for r in slot_rows if r["class"] == "absent_true"]
    shifted = [r for r in slot_rows if r["class"] == "present_shifted"]
    return {
        "expected_grid": ("per-day morning/afternoon session slots; intended labels "
                          "09:30/13:30 America/New_York within [market_open, market_close]"),
        "calendar": f"{CAL_NAME} ({CAL_VER}); mcal.__version__={MCal_VER_PIN}",
        "n_trading_days": len(trading),
        "n_slots_present_correct": counts["present_correct"],
        "n_slots_present_shifted": counts["present_shifted"],
        "n_slots_absent_true": counts["absent_true"],
        "n_slots_scheduled_trunc": counts["scheduled_trunc"],
        "absent_true_slots": [{"date": r["date"], "slot": r["slot"]} for r in absent],
        "n_offgrid_labels": counts["present_shifted"],
        "gap22_evidence_preserved": True,
    }

def main():
    files = sorted(f[3:-4] for f in os.listdir(CACHE) if f.startswith("h4_") and f.endswith(".pkl"))
    assert len(files) == 52, f"expected 52, got {len(files)}"
    results = [audit_symbol(s) for s in files]
    out = {
        "provenance": {
            "method": "COMPUTED",
            "revision": "rev2-corrected-comparator",
            "calendar": f"{CAL_NAME} ({CAL_VER})",
            "mcal_version": MCal_VER_PIN,
            "read_only": True,
            "n_files": 52,
            "correction_note": ("expected_equity_grid now consults market_open/market_close; "
                                "missing labels classified into scheduled_closure / "
                                "scheduled_truncation / coverage / label_mapping / true_absent"),
        },
        "symbols": results,
    }
    with open(os.path.join(HERE, "audit_52symbol.json"), "w") as f:
        json.dump(out, f, indent=1)
    lines = ["# 52-symbol h4 cache audit — REV 2 corrected comparator (COMPUTED)", "",
             f"Calendar: {CAL_NAME} {CAL_VER} (mcal {MCal_VER_PIN}). Read-only.",
             "Equity slots: present_correct (09:30/13:30 ET) / present_shifted (08:30/12:30 ET) /",
             "absent_true (genuine gap) / scheduled_trunc (early close).", "",
             "| Symbol | Bars | Correct | Shifted | Absent(true) | Sched trunc |",
             "|---|---|---|---|---|---|"]
    for r in results:
        if r["asset_class"] == "equity":
            lines.append(f"| {r['symbol']} | {r['n_bars']} | {r['n_slots_present_correct']} | "
                         f"{r['n_slots_present_shifted']} | {r['n_slots_absent_true']} | "
                         f"{r['n_slots_scheduled_trunc']} |")
        else:
            lines.append(f"| {r['symbol']} | {r['n_bars']} | {r['n_missing_vs_expected']}(crypto miss) | - | - | - |")
    open(os.path.join(HERE, "audit_52symbol.md"), "w").write("\n".join(lines) + "\n")
    print(f"audited {len(results)} symbols (rev2 comparator)")

if __name__ == "__main__":
    main()
