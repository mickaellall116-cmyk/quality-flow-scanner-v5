#!/usr/bin/env python3
"""CP1 follow-up: trade intersection analysis (REV 2 - corrected).
Task 3 of ChatGPT bounded assignment (Issue #1 comment 5986944792).
Corrections per ChatGPT review (Issue #1 comment 5994294209, items A and C).

CORRECTION A — equity DST exposure separated from crypto calendar membership:
  The prior 82-count applied in_est() to every asset. Crypto trades on a 24/7
  UTC grid (00/04/08/12/16/20) with NO DST shift, so crypto entries during EST
  calendar periods were misclassified as shifted-grid exposure.
  Corrected: 82 = 51 equity shifted-regime entries + 31 crypto calendar-period
  entries. Only equities get the shifted-regime (defect-exposure) flag; crypto
  gets a separate calendar-period-membership flag that is explicitly NOT a defect.
  The superseded 82-count is preserved below with a correction note.

CORRECTION C — gaps derived from pinned audit evidence:
  Gap timestamps are derived from audit_52symbol.json (the pinned rev2 audit),
  not hard-coded. Equity gaps = absent_true slots per symbol. SOL gaps = missing
  timestamps vs the BTC reference grid from the crypto audit section.
  Signal-regime flags added; full holding-regime intersections emitted.
  All 240 rows validated against the pinned ledger.

Outputs trade_id, symbol, signal/entry/exit times, regime flags, gap refs.
Temporal overlap alone is NOT proof of performance impact — stated in output.
All findings tagged COMPUTED.
"""
import json, os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = ("/home/hatch/workspace/quality-flow-scanner-v5/research_notes/"
          "recovery_4h_20261004/cp1_bundle/02_c1_ledger/c1_240_trade_ledger.json")
AUDIT = os.path.join(HERE, "audit_52symbol.json")

# EST calendar periods within cache window (2024-09-16 -> 2026-09-14).
# For EQUITIES these are shifted-regime periods (bars on 08:30/12:30 EST).
# For CRYPTO these are calendar-period membership only (UTC grid has no DST shift).
EST_PERIODS = [
    ("2024-11-03", "2025-03-09"),  # EST 2024-25
    ("2025-11-02", "2026-03-08"),  # EST 2025-26
]

CRYPTO_SUFFIX = "-USD"

def asset_class(sym):
    return "crypto" if sym.endswith(CRYPTO_SUFFIX) else "equity"

def in_est_calendar(ts):
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    d = ts.date().isoformat()
    return any(s <= d <= e for s, e in EST_PERIODS)

def load_audit_gaps():
    """Derive gap tables from the pinned rev2 audit evidence."""
    a = json.load(open(AUDIT))
    by_sym = {s["symbol"]: s for s in a["symbols"]}
    # equity gaps: absent_true slots -> expected-label timestamps
    equity_gaps = {}
    for sym, s in by_sym.items():
        if s["asset_class"] != "equity":
            continue
        gaps = []
        for g in s.get("absent_true_slots", []):
            hm = "09:30" if g["slot"] == "morning" else "13:30"
            gaps.append(pd.Timestamp(f"{g['date']} {hm}").tz_localize("America/New_York"))
        if gaps:
            equity_gaps[sym] = sorted(gaps)
    # SOL gaps: missing timestamps vs BTC reference grid (from crypto audit)
    sol = by_sym.get("SOL-USD", {})
    sol_missing = [pd.Timestamp(t) for t in sol.get("missing_all", [])]
    btc = by_sym.get("BTC-USD", {})
    btc_missing = set(pd.Timestamp(t) for t in btc.get("missing_all", []))
    # SOL-specific gaps: missing in SOL but present in BTC grid
    sol_specific = sorted(t for t in sol_missing if t not in btc_missing)
    return equity_gaps, sol_specific, a["provenance"]

def main():
    led = json.load(open(LEDGER))
    trades = led["trades"]
    assert len(trades) == 240, f"ledger changed: {len(trades)} trades"
    # validate ledger integrity: every trade has required fields
    for i, t in enumerate(trades):
        for k in ("symbol", "signal_time", "entry_time", "exit_time"):
            assert k in t, f"trade {i} missing {k}"
    equity_gaps, sol_specific, audit_prov = load_audit_gaps()

    out = []
    for i, t in enumerate(trades):
        tid = f"T{i:03d}"
        sym = t["symbol"]
        ac = asset_class(sym)
        sig = pd.Timestamp(t["signal_time"])
        ent = pd.Timestamp(t["entry_time"])
        ext = pd.Timestamp(t["exit_time"])
        in_cal = in_est_calendar(ent)
        rec = {
            "trade_id": tid, "symbol": sym, "asset_class": ac,
            "signal_time": sig.isoformat(), "entry_time": ent.isoformat(),
            "exit_time": ext.isoformat(),
            # signal regime flag (new in rev2)
            "signal_in_est_calendar": in_est_calendar(sig),
            # equity: shifted-regime = defect exposure. crypto: calendar only.
            "equity_shifted_regime_entry": (in_cal if ac == "equity" else False),
            "equity_shifted_regime_exit": (in_est_calendar(ext) if ac == "equity" else False),
            "crypto_est_calendar_entry": (in_cal if ac == "crypto" else False),
            "holding_intersects_est_calendar": (in_cal or in_est_calendar(ext)
                                                or in_est_calendar(sig)),
            "gap_refs": [],
        }
        # equity gaps from pinned audit (derived, not hard-coded)
        for g in equity_gaps.get(sym, []):
            if ent <= g <= ext:
                rec["gap_refs"].append(f"AUDIT-GAP({sym} {g.date()} "
                                       f"{'morning' if g.hour == 9 else 'afternoon'}_slot_absent)")
        # SOL gaps from pinned audit (derived)
        if sym == "SOL-USD":
            for g in sol_specific:
                if ent <= g <= ext:
                    rec["gap_refs"].append(f"SOL-AUDIT-GAP({g.isoformat()})")
        out.append(rec)

    n_eq_shift = sum(1 for r in out if r["equity_shifted_regime_entry"])
    n_cr_cal = sum(1 for r in out if r["crypto_est_calendar_entry"])
    summ = {
        "method": "COMPUTED",
        "revision": "rev2-corrected",
        "audit_provenance": audit_prov.get("revision"),
        "n_trades": len(out),
        "n_equity_trades": sum(1 for r in out if r["asset_class"] == "equity"),
        "n_crypto_trades": sum(1 for r in out if r["asset_class"] == "crypto"),
        # corrected counts
        "n_equity_shifted_regime_entry": n_eq_shift,
        "n_crypto_est_calendar_entry": n_cr_cal,
        "n_with_gap_refs": sum(1 for r in out if r["gap_refs"]),
        "correction_note": (
            "SUPERSEDED: prior rev1 reported 82 trades 'entered during EST "
            "shifted-regime periods' by applying in_est() to all assets. "
            "Corrected: 51 equity shifted-regime entries (defect exposure) + "
            "31 crypto EST-calendar-period entries (calendar membership only; "
            "crypto UTC grid has no DST shift, NOT a defect). "
            "82 = calendar-period membership, not demonstrated shifted-grid exposure."),
        "disclaimer": ("Temporal overlap alone is NOT proof of performance impact. "
                       "These tables enumerate coincidence of trade intervals with "
                       "known data-regime boundaries; causal effect on P&L is UNRESOLVED."),
        "trades": out,
    }
    with open(os.path.join(HERE, "trade_intersection.json"), "w") as f:
        json.dump(summ, f, indent=1)
    print(f"total={len(out)} equity_shifted={n_eq_shift} crypto_cal={n_cr_cal} "
          f"gap_refs={summ['n_with_gap_refs']}")
    # key examples
    for r in out:
        if r["trade_id"] in ("T145", "T146") or (r["symbol"] == "SOL-USD" and r["gap_refs"]):
            print(f"  {r['trade_id']} {r['symbol']} {r['entry_time'][:16]} -> "
                  f"{r['exit_time'][:16]} gaps={r['gap_refs']}")

if __name__ == "__main__":
    main()
