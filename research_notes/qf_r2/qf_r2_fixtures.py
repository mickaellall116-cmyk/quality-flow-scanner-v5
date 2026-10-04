#!/usr/bin/env python3
"""QF-R2-BRK-VOL-4H-001 — 12 synthetic fixtures for the REQUIRED PRE-RUN
IMPLEMENTATION CHECKS (prereg directive, checks 1-12).

Purely synthetic data. No market-performance computation. Run:
    python3 qf_r2_fixtures.py
All 12 must pass.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qf_r2_runner as R

import pandas as pd
import numpy as np

TZ = R.TZ
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return bool(cond)


def synth_4h(rows):
    """rows: list of (date_str, hhmm, o,h,l,c,v). Returns 4H frame."""
    idx, data = [], []
    for d, hm, o, h, l, c, v in rows:
        idx.append(pd.Timestamp(f"{d} {hm}", tz=TZ))
        data.append((o, h, l, c, v))
    df = pd.DataFrame(data, columns=["Open", "High", "Low", "Close", "Volume"],
                      index=pd.DatetimeIndex(idx))
    return df.sort_index()


def flat_bars(day, slot_hm, n, price, vol, start_i=0):
    rows = []
    for k in range(n):
        rows.append((day, slot_hm, price, price + 0.5, price - 0.5, price, vol))
    return rows


# ------------------------------------------------------------------ check 1
def f1_manifest_committed():
    mp = os.path.join(HERE, "qf_r2_manifest.json")
    ok = os.path.exists(mp)
    if not ok:
        return check("1 manifest committed with runner/spec/hash manifest",
                     False, "qf_r2_manifest.json missing")
    m = __import__("json").load(open(mp))
    spec_ok = m.get("spec_sha256") == R.sha256_file(
        os.path.join(HERE, "qf_r2_brk_vol_4h_prereg_20261004.md"))
    run_ok = m.get("runner_sha256") == R.sha256_file(
        os.path.join(HERE, "qf_r2_runner.py"))
    fix_ok = m.get("fixtures_sha256") == R.sha256_file(
        os.path.join(HERE, "qf_r2_fixtures.py"))
    return check("1 manifest committed with runner/spec/hash manifest",
                 spec_ok and run_ok and fix_ok,
                 "spec/runner/fixtures hashes match" if (spec_ok and run_ok and fix_ok)
                 else "hash mismatch in manifest")


# ------------------------------------------------------------------ check 2
def f2_hash_verify_and_fail_closed():
    try:
        symbols, meta = R.verify_inputs()
        verified = meta["1h_files_checked"] > 0 and meta["1h_pool"] > 0
    except RuntimeError as e:
        return check("2 input/module hash verification + fail-closed",
                     False, f"verify raised unexpectedly: {e}")
    # Fail-closed: a missing required input must raise, never substitute.
    orig = R._resolve_1h
    R._resolve_1h = lambda sym: None if sym == "AAPL" else orig(sym)
    try:
        R.verify_inputs()
        fail_closed = False
    except RuntimeError:
        fail_closed = True
    finally:
        R._resolve_1h = orig
    mods = R.module_hashes()
    return check("2 input/module hash verification + fail-closed",
                 verified and fail_closed and len(mods["scanner_rules.py"]) == 64,
                 f"{meta['1h_files_checked']} inputs verified; "
                 f"missing-input raises={fail_closed}")


# ------------------------------------------------------------------ check 3
def f3_prior_high_excludes_current():
    # 20 flat bars at 100, then a bar with high=109 (own high is the max)
    # and close=108. Correct: prior_high20=100 -> breakout. If the current
    # bar leaked into prior_high20, no breakout (108 < 109).
    rows = flat_bars("2025-04-01", "0930", 20, 100.0, 100000)
    rows += [("2025-04-01", "1330", 107.0, 109.0, 106.5, 108.0, 100000)]
    # pad: need bars before study start? breakout_candidates only scans
    # within study window; put the 20 priors on prior trading days.
    df = synth_4h(rows)
    spy = lambda ts: True
    cands, _ = R.breakout_candidates("SYN", df, spy)
    got = len(cands) == 1 and abs(cands[0]["prior_high20"] - 100.5) < 1e-9
    # 100.5 = prior bars' high (price+0.5)
    return check("3 breakout cannot use current bar in prior_high20", got,
                 f"prior_high20={cands[0]['prior_high20'] if cands else None}, "
                 f"n_cands={len(cands)}")


# ------------------------------------------------------------------ check 4
def f4_volume_uses_vol_per_minute_and_slot():
    # 25 opening bars at vol_rate 100 (240 min), then a signal opening bar
    # with raw volume 24000 -> rate 100 -> ratio 1.0 (not high).
    # The SAME raw volume on a closing bar (150 min) -> rate 160 -> 1.6 high.
    # Proves: vol/minute + slot, and duration alone flips raw-volume reads.
    def frame(slot_hm, minutes, sig_vol):
        rows = []
        for k in range(25):
            rows.append(("2025-04-01", slot_hm, 50.0, 50.5, 49.5, 50.0,
                         100 * minutes))
        rows.append(("2025-04-02", slot_hm, 50.0, 60.0, 49.0, 59.0, sig_vol))
        return synth_4h(rows)
    df_open = frame("0930", 240, 24000)     # rate 100 -> ratio 1.0
    df_close = frame("1330", 150, 24000)   # rate 160 -> ratio 1.6
    ev_o = {"signal_bar": 25, "slot": "opening", "vol_rate": 24000 / 240,
            "symbol": "SYN"}
    ev_c = {"signal_bar": 25, "slot": "closing", "vol_rate": 24000 / 150,
            "symbol": "SYN"}
    ok_o, _ = R.classify_volume(ev_o, df_open)
    ok_c, _ = R.classify_volume(ev_c, df_close)
    cond = (ok_o and not ev_o["high_volume"]
            and ok_c and ev_c["high_volume"]
            and abs(ev_o["volume_ratio"] - 1.0) < 1e-9
            and abs(ev_c["volume_ratio"] - 1.6) < 1e-9)
    return check("4 volume uses vol/min + slot; duration alone can't flip class",
                 cond,
                 f"open ratio={ev_o.get('volume_ratio')}, "
                 f"close ratio={ev_c.get('volume_ratio')}")


# ------------------------------------------------------------------ check 5
def f5_early_close_excluded():
    # Breakout setup with the signal bar on 2024-11-29 (13:00 early close).
    rows = []
    for k in range(20):
        rows.append(("2025-04-01", "0930", 100.0, 100.5, 99.5, 100.0, 100000))
    rows.append(("2024-11-29", "0930", 101.0, 102.0, 100.0, 101.5, 500000))
    df = synth_4h(rows)
    spy = lambda ts: True
    cands, diag = R.breakout_candidates("SYN", df, spy)
    # 2024-11-29 is before STUDY_START so it wouldn't qualify anyway;
    # use a date inside the window instead: 2025-11-28 is also early-close.
    rows2 = []
    for k in range(20):
        rows2.append(("2025-11-27", "0930", 100.0, 100.5, 99.5, 100.0, 100000))
    rows2.append(("2025-11-28", "0930", 101.0, 102.0, 100.0, 101.5, 500000))
    df2 = synth_4h(rows2)
    cands2, diag2 = R.breakout_candidates("SYN", df2, spy)
    cond = len(cands2) == 0 and diag2["early_close"] >= 1
    return check("5 early-close signal bar excluded", cond,
                 f"n_cands={len(cands2)}, early_close_hits={diag2['early_close']}")


# ------------------------------------------------------------------ check 6
def f6_next_bar_open_only():
    # Signal bar close=108, next bar open=107 -> entry must be 107.
    rows = flat_bars("2025-04-01", "0930", 20, 100.0, 100000)
    rows += [("2025-04-01", "1330", 107.0, 109.0, 106.5, 108.0, 200000),
             ("2025-04-02", "0930", 107.0, 108.0, 106.0, 107.5, 100000),
             ("2025-04-02", "1330", 107.5, 108.5, 107.0, 108.0, 100000)]
    # need 20 baseline bars per slot before signal -> add more history
    pre = []
    for k in range(25):
        pre.append(("2025-03-28", "0930", 100.0, 100.5, 99.5, 100.0, 24000))
        pre.append(("2025-03-28", "1330", 100.0, 100.5, 99.5, 100.0, 15000))
    df = synth_4h(pre + rows)
    spy = lambda ts: True
    events, _ = R.admit_events("SYN", df, spy)
    admitted = [e for e in events if "excluded" not in e]
    cond_entry = (len(admitted) >= 1
                  and abs(admitted[0]["entry_open"] - 107.0) < 1e-9
                  and abs(R.simulate_trade(admitted[0], df)["entry"] - 107.0) < 1e-9)
    # Missing next open: signal bar is the last bar -> excluded no_next_open.
    rows_last = flat_bars("2025-04-01", "0930", 20, 100.0, 100000)
    rows_last += [("2025-04-01", "1330", 107.0, 109.0, 106.5, 108.0, 200000)]
    df_last = synth_4h(pre + rows_last)
    events_last, diag_last = R.admit_events("SYN", df_last, spy)
    cond_missing = diag_last["no_next_open"] >= 1
    return check("6 next-bar-open entry only; missing open excluded",
                 cond_entry and cond_missing,
                 f"entry={admitted[0]['entry_open'] if admitted else None}, "
                 f"no_next_open={diag_last['no_next_open']}")


# ------------------------------------------------------------------ check 7
def f7_causal_suppression():
    # Two breakout candidates 2 bars apart; second is high-volume-worthy
    # but must be suppressed WITHOUT volume classification.
    pre = []
    for k in range(25):
        pre.append(("2025-03-28", "0930", 100.0, 100.5, 99.5, 100.0, 24000))
        pre.append(("2025-03-28", "1330", 100.0, 100.5, 99.5, 100.0, 15000))
    rows = flat_bars("2025-04-01", "0930", 20, 100.0, 100000)
    rows += [("2025-04-01", "1330", 107.0, 109.0, 106.5, 108.0, 200000),
             ("2025-04-02", "0930", 108.0, 110.0, 107.5, 109.5, 900000),
             ("2025-04-02", "1330", 109.0, 110.0, 108.0, 109.0, 100000)]
    df = synth_4h(pre + rows)
    spy = lambda ts: True
    events, diag = R.admit_events("SYN", df, spy)
    cond = diag["suppressed"] >= 1 and len([e for e in events
                                           if "excluded" not in e]) == 1
    return check("7 overlapping same-symbol events suppressed causally",
                 cond, f"suppressed={diag['suppressed']}, "
                 f"admitted={len([e for e in events if 'excluded' not in e])}")


# ------------------------------------------------------------------ check 8
def f8_matching_uses_only_event_time_fields():
    def ev(sym, ts, slot="opening", q="2025-Q2", regime=True,
           dec=5, strength=1.0):
        return {"symbol": sym, "ts": ts, "slot": slot, "quarter": q,
                "spy_regime": regime, "atr_pct": 0.01, "strength": strength,
                "high_volume": False, "entry_open": 100.0}
    h = dict(ev("HV", "2025-04-02T09:30:00-04:00"), high_volume=True)
    c1 = ev("AAA", "2025-04-03T09:30:00-04:00")
    c2 = ev("ZZZ", "2025-04-03T09:30:00-04:00")
    # identical candidates except symbol -> alphabetical tie-break picks AAA
    pairs, _ = R.match_controls([h, c1, c2])
    tie_ok = len(pairs) == 1 and pairs[0][1]["symbol"] == "AAA"
    # outcome fields must not influence matching: attach decoy net R
    c1["decoy_net_r"] = -99.0
    c2["decoy_net_r"] = +99.0
    pairs2, _ = R.match_controls([h, c1, c2])
    outcome_blind = len(pairs2) == 1 and pairs2[0][1]["symbol"] == "AAA"
    # no replacement: one control can't serve two highs
    h2 = dict(ev("HV2", "2025-04-04T09:30:00-04:00"), high_volume=True)
    pairs3, unm = R.match_controls([h, h2, c1])
    no_repl = len(pairs3) == 1 and len(unm) == 1
    return check("8 matching uses only event-time fields + deterministic tie-break",
                 tie_ok and outcome_blind and no_repl,
                 f"tie={pairs[0][1]['symbol'] if pairs else None}, "
                 f"no_replacement_unmatched={len(unm)}")


# ------------------------------------------------------------------ check 9
def f9_stop_first():
    # Bar hits both stop and TP -> stop wins.
    # stop = 105 - 0.5*2 = 104; R0 = 3; TP = 113.
    ev = {"entry_open": 107.0, "prior_high20": 105.0, "atr14": 2.0,
          "entry_bar": 0}
    df = synth_4h([
        ("2025-04-02", "0930", 107.0, 108.0, 106.0, 107.5, 100000),
        ("2025-04-02", "1330", 107.0, 114.0, 99.0, 105.0, 100000),
    ])
    t = R.simulate_trade(ev, df)
    cond = t["valid"] and t["exit_kind"] == "stop" and abs(t["exit_price"] - 104.0) < 1e-9
    # gap through stop: open below stop -> fill at open
    df2 = synth_4h([
        ("2025-04-02", "0930", 107.0, 108.0, 106.0, 107.5, 100000),
        ("2025-04-02", "1330", 100.0, 101.0, 99.0, 100.5, 100000),
    ])
    t2 = R.simulate_trade(ev, df2)
    cond2 = t2["valid"] and t2["exit_kind"] == "gap_stop" and abs(t2["exit_price"] - 100.0) < 1e-9
    return check("9 stop-first ambiguity; gap-through-stop at open",
                 cond and cond2,
                 f"both-hit->{t.get('exit_kind')}, gap->{t2.get('exit_kind')}")


# ------------------------------------------------------------------ check 10
def f10_each_gate_flips_verdict():
    # Baseline: 320 pairs, d=+0.2 constant, weeks split Y1/Y2 >=75 each.
    # NOTE: weekly_blocks parses ts as ISO; use real ISO dates.
    def mk2(dates, d, hv_r, d_diag=None):
        pairs, trades = [], {}
        for dt in dates:
            h = {"symbol": "H", "ts": dt, "high_volume": True,
                 "entry_open": 100.0}
            c = {"symbol": "C", "ts": dt, "high_volume": False,
                 "entry_open": 100.0}
            pairs.append((h, c))
            dd = d_diag if d_diag is not None else d
            trades[id(h)] = {"net_r_primary": hv_r, "net_r_diag": hv_r}
            trades[id(c)] = {"net_r_primary": hv_r - d,
                             "net_r_diag": hv_r - dd}
        return pairs, trades
    y1 = [f"2025-06-{d:02d}T09:30:00-04:00" for d in range(1, 29)] * 8   # 224
    y2 = [f"2026-06-{d:02d}T09:30:00-04:00" for d in range(1, 29)] * 8   # 224
    base_dates = (y1 + y2)[:320]
    flips = []

    def verdict_for(dates, d, hv_r, d_diag=None):
        pairs, trades = mk2(dates, d, hv_r, d_diag)
        _, v = R.evaluate_gates(pairs, trades)
        return v, pairs, trades

    v0, _, _ = verdict_for(base_dates, 0.2, 0.3)
    flips.append(("baseline PASS", v0 == "PASS"))
    # G0: 299 pairs -> INSUFFICIENT
    v, _, _ = verdict_for(base_dates[:299], 0.2, 0.3)
    flips.append(("G0 flips", v == "INSUFFICIENT"))
    # G1: hv mean 0.05 < 0.10, d still 0.2 -> FAIL
    v, _, _ = verdict_for(base_dates, 0.2, 0.05)
    flips.append(("G1 flips", v == "FAIL"))
    # G2: d = 0.05 -> FAIL
    v, _, _ = verdict_for(base_dates, 0.05, 0.3)
    flips.append(("G2 flips", v == "FAIL"))
    # G3: alternating +/-1 d -> p ~ 1 -> FAIL
    pairs, trades = [], {}
    for i, dt in enumerate(base_dates):
        sgn = 1.0 if i % 2 == 0 else -1.0
        h = {"symbol": "H", "ts": dt, "high_volume": True, "entry_open": 100.0}
        c = {"symbol": "C", "ts": dt, "high_volume": False, "entry_open": 100.0}
        pairs.append((h, c))
        trades[id(h)] = {"net_r_primary": sgn, "net_r_diag": sgn}
        trades[id(c)] = {"net_r_primary": 0.0, "net_r_diag": 0.0}
    _, v = R.evaluate_gates(pairs, trades)
    flips.append(("G3 flips", v == "FAIL"))
    # G4: Y2 hv < ctrl -> FAIL
    dates_g4 = y1[:160] + y2[:160]
    pairs, trades = mk2(dates_g4, 0.2, 0.3)
    for h, c in pairs:
        if "2026-" in h["ts"]:
            trades[id(h)]["net_r_primary"] = -0.5
            trades[id(c)]["net_r_primary"] = 0.5
    _, v = R.evaluate_gates(pairs, trades)
    flips.append(("G4 flips", v == "FAIL"))
    # G4 count: Y2 < 75 pairs -> INSUFFICIENT
    v, _, _ = verdict_for(y1[:112] + y2[:10], 0.2, 0.3)
    flips.append(("G4-count flips", v == "INSUFFICIENT"))
    # G5: diag advantage <= 0 -> FAIL
    v, _, _ = verdict_for(base_dates, 0.2, 0.3, d_diag=-0.1)
    flips.append(("G5 flips", v == "FAIL"))

    ok = all(f[1] for f in flips)
    return check("10 each gate G0-G5 can flip the verdict", ok,
                 "; ".join(f"{n}={'ok' if p else 'NO'}" for n, p in flips))


# ------------------------------------------------------------------ check 11
def f11_raw_paths_exist():
    missing = [p for p in R.RAW_PATHS
               if not os.path.exists(os.path.join(HERE, "raw_evidence", p))]
    return check("11 raw-output paths established before run",
                 not missing, f"missing={missing}" if missing else
                 f"{len(R.RAW_PATHS)} paths present (empty)")


# ------------------------------------------------------------------ check 12
def f12_evidence_tier_computed_only():
    tier_ok = R.EVIDENCE_TIER == "COMPUTED"
    import glob, re
    # Flag only an actual REPRODUCED tier *claim* (quoted tier value), not
    # prose such as "no REPRODUCED claim until a clean rerun matches".
    pat = re.compile(r"""['"]REPRODUCED['"]""")
    found = []
    for fp in glob.glob(os.path.join(HERE, "*.py")) + \
            glob.glob(os.path.join(HERE, "*.md")) + \
            glob.glob(os.path.join(HERE, "*.json")):
        if pat.search(open(fp, errors="ignore").read()):
            found.append(os.path.basename(fp))
    return check("12 evidence tier COMPUTED only; no REPRODUCED claim",
                 tier_ok and not found,
                 f"tier={R.EVIDENCE_TIER}, reproduced_claim_in={found}")


def main():
    f1_manifest_committed()
    f2_hash_verify_and_fail_closed()
    f3_prior_high_excludes_current()
    f4_volume_uses_vol_per_minute_and_slot()
    f5_early_close_excluded()
    f6_next_bar_open_only()
    f7_causal_suppression()
    f8_matching_uses_only_event_time_fields()
    f9_stop_first()
    f10_each_gate_flips_verdict()
    f11_raw_paths_exist()
    f12_evidence_tier_computed_only()
    n_pass = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\n{n_pass}/12 fixtures passed")
    sys.exit(0 if n_pass == 12 else 1)


if __name__ == "__main__":
    main()
