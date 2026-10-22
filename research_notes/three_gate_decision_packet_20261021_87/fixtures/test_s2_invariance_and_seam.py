#!/usr/bin/env python3
"""
test_s2_invariance_and_seam.py — Gate 3 fixtures (task -87).

Three small numeric demonstrations behind the S2 disposition
recommendation, all synthetic, all stdlib:

  S2-1 UNIFORM-ADJUSTMENT INVARIANCE (the -62 §2 claim, exhibited):
       under a UNIFORM split adjustment (pre-split prices scaled by
       1/factor, volumes by factor), every quantity the frozen
       strategy consumes — bar returns, true-range/close ratios,
       relative volume — is IDENTICAL to the unadjusted economic
       series. A uniformly adjusted series needs no session
       exclusion to be safe.
  S2-2 MIXED-BASIS SEAM (what S2 actually guards against): if the
       pre-split segment is left on the raw basis, the seam bar
       carries a false return of exactly -(1 - 1/factor) (-90% for
       a 10:1 split) — a manufactured crash. The same step is what
       the -82/-86 completeness/convention checker detects as a
       convention break WITHOUT removing any session: the seam is a
       detectable data defect, not an argument for blanket
       exclusion of D-1/D/D+1.
  S2-3 EXCLUSION SHAPE ON THE REAL CALENDAR BYTES: applying S2's
       {prev(D), D, next(D)} session-adjacency rule (per the -59
       transform contract) over the pinned calendars removes exactly
       the session-adjacent triple — including across a closure (an
       event effective on the early-close session excludes Jul-2,
       Jul-3, Jul-5; the Jul-4 closure is not a session and cannot
       be excluded), and across the extension/-35 boundary (adjacency
       is over the COMBINED calendar — GATE-E4's range requirement).

Exit 1 on any FAIL.
"""
import json
import sys
from pathlib import Path

RESULTS = []


def case(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")


def returns(closes):
    return [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))]


def main():
    # --- S2-1: uniform adjustment removes the seam, changes nothing
    # else. Raw tape across a 10:1 split effective at index 3 (the
    # first post-split print, 10.4, is exactly the split-implied
    # price 104/10, i.e. the economically flat seam). ---
    raw_closes = [100.0, 102.0, 104.0, 10.4, 10.6, 10.5]
    raw_vols = [1000.0, 1100.0, 1050.0, 10500.0, 10600.0, 9900.0]
    # Vendor adjust=splits representation: pre-split segment scaled
    # (prices / factor, volumes x factor) — the representation -75
    # verified Twelve Data actually serves for NVDA.
    adj_closes = [c / 10.0 if i < 3 else c for i, c in enumerate(raw_closes)]
    adj_vols = [v * 10.0 if i < 3 else v for i, v in enumerate(raw_vols)]
    r_raw, r_adj = returns(raw_closes), returns(adj_closes)
    nonseam = [0, 1, 3, 4]  # return indices away from the seam (seam = 2)
    case("S2-1_nonseam_returns_unchanged",
         all(abs(r_raw[i] - r_adj[i]) < 1e-12 for i in nonseam),
         "adjustment alters no return away from the seam")
    case("S2-1b_seam_return_killed",
         abs(r_adj[2] - 0.0) < 1e-12 and abs(r_raw[2] - (-0.9)) < 1e-12,
         f"seam return: adjusted={r_adj[2]:.4f} (flat, as the economics are) "
         f"vs raw={r_raw[2]:.4f} (manufactured crash)")
    # TR/close (ATR ingredient): same shape — raw tape's seam TR/close
    # is 9.0 (a 900% "range"), the adjusted series' is 0.
    tr_raw = abs(raw_closes[3] - raw_closes[2]) / raw_closes[3]
    tr_adj = abs(adj_closes[3] - adj_closes[2]) / adj_closes[3]
    case("S2-1c_seam_tr_ratio_killed",
         abs(tr_adj) < 1e-12 and abs(tr_raw - 9.0) < 1e-9,
         f"seam TR/close: adjusted={tr_adj:.4f} vs raw={tr_raw:.4f}")
    # Relative volume: on the raw tape the seam bar's volume is a
    # 10.0x outlier vs the pre-split median; on the adjusted series
    # it is 1.0x — in family. (Volume scaling is what makes this so;
    # -75 verified TD scales volume by the same factor.)
    import statistics
    med_pre_raw = statistics.median(raw_vols[:3])
    med_pre_adj = statistics.median(adj_vols[:3])
    case("S2-1d_volume_spike_killed",
         abs(raw_vols[3] / med_pre_raw - 10.0) < 1e-9
         and abs(adj_vols[3] / med_pre_adj - 1.0) < 1e-9,
         f"seam volume / pre-split median: raw={raw_vols[3] / med_pre_raw:.2f}x "
         f"vs adjusted={adj_vols[3] / med_pre_adj:.2f}x")

    # --- S2-2: the mixed-basis seam is a detectable false crash ---
    mixed = [100.0, 102.0, 104.0, 10.4, 10.6, 10.5]  # pre-split NOT adjusted
    seam = mixed[3] / mixed[2] - 1.0
    case("S2-2_seam_false_return_exact",
         abs(seam - (-0.9)) < 1e-12,
         f"seam return={seam:.4f} = -(1 - 1/10) exactly")
    # The convention checker's step lane recovers the factor from the
    # seam ratio — the defect is machine-detectable without exclusion.
    step = mixed[2] / mixed[3]
    case("S2-2b_step_recovers_factor", abs(step - 10.0) < 1e-9,
         f"step ratio={step} -> factor-shaped, detectable without exclusion")

    # --- S2-3: exclusion shape over the pinned calendar bytes ---
    inputs = Path(__file__).parent / "inputs"
    v2 = json.loads((inputs / "XNYS_SESSION_SCHEDULE_V2.json").read_text())
    cand = json.loads((inputs /
                       "XNYS_SESSION_SCHEDULE_CANDIDATE_EXTENSION_20261021_81.json").read_text())
    sessions = [s["date"] for s in v2["sessions"]]
    idx = {d: i for i, d in enumerate(sessions)}

    def excluded(eff):
        i = idx[eff]
        return {sessions[i - 1], sessions[i], sessions[i + 1]}

    case("S2-3_triple_regular",
         excluded("2024-09-17") == {"2024-09-16", "2024-09-17", "2024-09-18"},
         str(sorted(excluded("2024-09-17"))))

    combined = sorted({s["date"] for s in cand["sessions"]} | set(sessions))
    cidx = {d: i for i, d in enumerate(combined)}

    def cexcluded(eff):
        i = cidx[eff]
        return {combined[i - 1], combined[i], combined[i + 1]}

    case("S2-3b_triple_combined_boundary",
         cexcluded("2024-09-16") == {"2024-09-13", "2024-09-16", "2024-09-17"},
         str(sorted(cexcluded("2024-09-16"))))
    case("S2-3c_triple_across_closure",
         cexcluded("2024-07-03") == {"2024-07-02", "2024-07-03", "2024-07-05"},
         "event on the early-close session: next is 07-05 (07-04 closure is not a session)")
    case("S2-3d_triple_event_after_closure",
         cexcluded("2024-07-05") == {"2024-07-03", "2024-07-05", "2024-07-08"},
         "prev of 07-05 is 07-03, skipping the closure")

    n_fail = sum(1 for _, ok in RESULTS if not ok)
    print(f"\n{len(RESULTS) - n_fail}/{len(RESULTS)} PASS")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
