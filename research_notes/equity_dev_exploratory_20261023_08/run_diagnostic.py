"""QF-EQUITY-DEV-EXPLORATORY-20261023-08 — driver.

Ordered fail-closed operation per Issue #1 comment 6373548773:
  Phase 0  pins (archive bytes, receipts, frozen code, calendar, PAUSED prod)
  Phase 1  DEV-only preflight on the EXISTING archived Twelve Data bytes
           (NVDA/TSLA/AAPL/SPY DEV legs only; HO files are hashed via the
           archive SHA256SUMS manifest check but their market content is
           NEVER parsed here)
  Phase 2  real-input engine parity (corrected session-anchored 4H grid vs
           the pinned session table; aggregation parity on every bar;
           per-candidate signal/level verification; C0 fidelity invariant)
  Phase 3  ONLY IF 1-2 pass: ONE preregistered unchanged-rule exploratory
           diagnostic (frozen C1 stack configuration: R1 rs ranking + R2
           sector cap, no R3; frozen 4bps/25bps cost pair). No tuning, no
           parameter variation, no second configuration.

Labels: EXPLORATORY / 4-NAME CONVENIENCE SAMPLE / G4 UNADOPTED /
NOT VALIDATED EDGE. Explicitly non-comparable to UX51 / C1.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "engine")
ARCHIVE = os.path.expanduser(
    "~/workspace/qf_td_pilot_20261023/archive_clone/captures/td_pilot_20261023")
SYMBOLS = ["NVDA", "TSLA", "AAPL", "SPY"]  # UNIVERSE_X order, as load_bull

sys.path.insert(0, ENGINE)
sys.path.insert(0, os.path.join(ENGINE, "pine_stack"))
sys.path.insert(0, os.path.join(ENGINE, "pine_ranking"))
sys.path.insert(0, os.path.join(ENGINE, "pine_exposure"))
sys.path.insert(0, os.path.join(ENGINE, "pine_signal_quality"))

import numpy as np
import pandas as pd

ET = "America/New_York"
FIXED_NOW = pd.Timestamp("2026-10-17 00:00:00", tz=ET)

EXPECTED_PINS = {
    "pine_backtest.py": "447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5",
    "scanner_rules.py": "62aa743ac28f05de9b6ec0ab962ee28bb7e5152bbef00bff5afa611a480f473c",
    "pine_stack/pine_stack.py": "839e4800624de253514095b5c007e8088afc0ab6c6ef45c86fb29a5956dfcefa",
    "pine_ranking/pine_ranking.py": "77afae0df120e3a2ad77a6d2d43247c8aea0ad296f08c273bff7d1cc833aaae6",
    "pine_signal_quality/pine_signal_quality.py": "b1b39ee8d0bd4bbb1387b3ce54c7345c1f8dd622f94a5ed390c989fed1d39e69",
    "pine_exposure/pine_exposure.py": "9f646161c27f6b28febe0980d03665bc9c1502fb844d37be6fd1d72ee45102be",
    "session_table.json": "00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f",
}
# -02 enumerated phantom rows (15:30 bar-opens on 13:00 early-close dates)
EXPECTED_EXCLUDED = {
    "NVDA": ["2024-11-29 15:30:00"],
    "TSLA": ["2024-11-29 15:30:00", "2024-12-24 15:30:00"],
    "AAPL": ["2024-11-29 15:30:00", "2024-12-24 15:30:00"],
    "SPY": ["2024-11-29 15:30:00", "2024-12-24 15:30:00"],
}
EXPECTED_ADMITTED = 3653
EXPECTED_BARS_4H = 1043  # 519 full sessions x2 + 5 early-close x1

ADMITTED_FRAMES = {}
report = {"task": "QF-EQUITY-DEV-EXPLORATORY-20261023-08",
          "labels": ["EXPLORATORY", "4-NAME CONVENIENCE SAMPLE",
                     "G4 UNADOPTED", "NOT VALIDATED EDGE"],
          "phases": {}}
failures = []


def fail(phase, msg):
    failures.append(f"{phase}: {msg}")
    print(f"FAIL [{phase}] {msg}", flush=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- Phase 0
def phase0():
    ph = {}
    for rel, want in EXPECTED_PINS.items():
        p = os.path.join(HERE, "session_table.json") if rel == "session_table.json" \
            else os.path.join(ENGINE, rel)
        got = sha256_file(p)
        ph[rel] = got
        if got != want:
            fail("P0", f"pin mismatch {rel}: {got} != {want}")
    # archive manifest integrity (hashes of ALL archived files incl. HO —
    # integrity only; HO market content is never parsed in this task)
    sums = {}
    with open(os.path.join(ARCHIVE, "SHA256SUMS")) as f:
        for line in f:
            line = line.strip()
            if line:
                digest, rel = line.split(None, 1)
                sums[rel.strip()] = digest
    bad = []
    for rel, want in sums.items():
        p = os.path.join(ARCHIVE, rel)
        if sha256_file(p) != want:
            bad.append(rel)
    ph["archive_sha256sums_files"] = len(sums)
    ph["archive_sha256sums_mismatches"] = bad
    if bad:
        fail("P0", f"archive SHA256SUMS mismatches: {bad}")
    # DEV receipts: body hash + row count cross-check
    ph["receipts"] = {}
    for sym in SYMBOLS:
        rc = json.load(open(os.path.join(ARCHIVE, "receipts", f"{sym}__DEV.receipt.json")))
        body = sha256_file(os.path.join(ARCHIVE, "raw", f"{sym}__DEV.json"))
        ok = (rc["response"]["sha256"] == body
              and rc["manifest_root_digest_sha256"] ==
              "79ccdd128e0b36537f56f8ae36a731b719e989b9756f65856b7dc47344327122"
              and rc["request"]["adjust"] == "splits"
              and rc["request"]["interval"] == "1h")
        ph["receipts"][sym] = {"receipt_response_sha256": rc["response"]["sha256"],
                               "receipt_rows": rc["response"]["rows"], "ok": ok}
        if not ok:
            fail("P0", f"receipt mismatch {sym}/DEV")
    report["phases"]["P0_pins"] = ph
    print(f"P0 done: {len(sums)} archive files verified, receipts ok", flush=True)


# ---------------------------------------------------------------- Phase 1
def load_session_table():
    t = json.load(open(os.path.join(HERE, "session_table.json")))
    dev = [s for s in t["sessions"] if s["date"] >= "2024-09-16"]
    assert len(dev) == 524, len(dev)
    return dev


def expected_starts(session):
    close_h, close_m = map(int, session["close"].split(":"))
    starts, mins = [], 9 * 60 + 30
    while mins < close_h * 60 + close_m:
        starts.append(f"{mins // 60:02d}:{mins % 60:02d}")
        mins += 60
    return starts


def phase1(dev_sessions):
    expected = {}  # (date, "HH:MM") -> True
    for s in dev_sessions:
        for st in expected_starts(s):
            expected[(s["date"], st)] = True
    assert len(expected) == EXPECTED_ADMITTED, len(expected)
    legs, admitted_frames = {}, {}
    for sym in SYMBOLS:
        raw = json.load(open(os.path.join(ARCHIVE, "raw", f"{sym}__DEV.json")))
        meta = raw["meta"]
        leg = {"meta_exchange_timezone": meta.get("exchange_timezone"),
               "meta_interval": meta.get("interval")}
        if meta.get("exchange_timezone") != ET or meta.get("interval") != "1h":
            fail("P1", f"{sym}: meta mismatch {meta}")
        rows = raw["values"]
        leg["raw_rows"] = len(rows)
        seen, admitted, excluded = {}, [], []
        parse_ok = True
        for r in rows:
            try:
                ts = pd.Timestamp(r["datetime"])
                o, h, l, c = (float(r[k]) for k in ("open", "high", "low", "close"))
                v = float(r["volume"])
            except Exception:
                parse_ok = False
                break
            if not all(np.isfinite(x) for x in (o, h, l, c, v)):
                fail("P1", f"{sym}: non-finite value at {r['datetime']}")
                parse_ok = False
                break
            if min(o, h, l, c) <= 0 or v < 0:
                fail("P1", f"{sym}: non-positive price / negative volume at {r['datetime']}")
                parse_ok = False
                break
            key = (r["datetime"][:10], r["datetime"][11:16])
            if key in seen:
                fail("P1", f"{sym}: duplicate stamp {r['datetime']}")
                parse_ok = False
                break
            seen[key] = True
            rec = {"ts": ts, "Open": o, "High": h, "Low": l, "Close": c, "Volume": v}
            if key in expected:
                admitted.append(rec)
            else:
                excluded.append(r["datetime"])
        if not parse_ok:
            legs[sym] = leg
            continue
        leg["excluded"] = sorted(excluded)
        leg["admitted_rows"] = len(admitted)
        if sorted(excluded) != EXPECTED_EXCLUDED[sym]:
            fail("P1", f"{sym}: excluded set {sorted(excluded)} != -02 enumeration "
                       f"{EXPECTED_EXCLUDED[sym]}")
        stamps = {(a["ts"].strftime("%Y-%m-%d"), a["ts"].strftime("%H:%M")) for a in admitted}
        if stamps != set(expected) or len(admitted) != EXPECTED_ADMITTED:
            fail("P1", f"{sym}: admitted grid != pinned-table expected set "
                       f"(admitted {len(admitted)}, unique {len(stamps)})")
        # zero-volume classification on admitted bytes (SMCI failure class)
        zv = [a for a in admitted if a["Volume"] == 0]
        zv_moving = [a for a in zv if not (a["Open"] == a["High"] == a["Low"] == a["Close"])]
        leg["zero_volume_admitted"] = len(zv)
        leg["zero_volume_price_moving"] = len(zv_moving)
        if zv_moving:
            fail("P1", f"{sym}: {len(zv_moving)} price-moving zero-volume admitted bars "
                       f"(provider-volume failure class)")
        idx = pd.DatetimeIndex([a["ts"] for a in admitted]).tz_localize(ET)
        if not idx.is_monotonic_increasing:
            fail("P1", f"{sym}: admitted stamps not strictly increasing")
        df = pd.DataFrame([{k: a[k] for k in ("Open", "High", "Low", "Close", "Volume")}
                           for a in admitted], index=idx)
        admitted_frames[sym] = df
        legs[sym] = leg
        print(f"P1 {sym}: raw {leg['raw_rows']} admitted {len(admitted)} "
              f"excluded {len(excluded)} zv {len(zv)}/{len(zv_moving)} moving", flush=True)
    report["phases"]["P1_preflight"] = legs
    report["phases"]["P1_vbasis_disclosure"] = (
        "All four legs remain CONVENTION_BREAK_SUSPECT via VBASIS per adjudication "
        "-02 (checker candidate-2, UNADOPTED): composite prints driven SOLELY by the "
        "VBASIS volume-ratio lane (SPY/HO 44 flags with no basis event; NVDA/HO ratios "
        "0.528-1.950 continuum). Price-side convention evidence on the same bytes: "
        "STEP PASS, STEP-ALL 0 undeclared factor steps, adjust=splits in force. Data "
        "is an exploratory candidate, NOT fully qualified; this diagnostic is "
        "permissible as a labeled exploratory run and asserts no G4 PASS.")
    return admitted_frames


# ---------------------------------------------------------------- Phase 2
def phase2(admitted, dev_sessions):
    import scanner_rules as sr
    import pine_backtest as pb
    out = {}
    bars4h = {}
    table = {s["date"]: s for s in dev_sessions}
    for sym in SYMBOLS:
        df = admitted[sym]
        bars = sr.resample_closed_4h_session_anchored(df, sym, now=FIXED_NOW)
        # grid vs pinned table
        grid_ok, detail = True, {}
        by_date = {}
        for ts in bars.index:
            by_date.setdefault(ts.strftime("%Y-%m-%d"), []).append(ts.strftime("%H:%M"))
        if set(by_date) != set(table):
            grid_ok = False
            detail["date_set_mismatch"] = True
        else:
            for d, sess in table.items():
                want = ["09:30"] if sess["close"] == "13:00" else ["09:30", "13:30"]
                if by_date[d] != want:
                    grid_ok = False
                    detail[d] = (by_date[d], want)
                    break
        if len(bars) != EXPECTED_BARS_4H:
            grid_ok = False
            detail["bar_count"] = len(bars)
        # aggregation parity on EVERY bar, recomputed from admitted 1h rows
        agg_bad = 0
        sess_rows = {}
        for ts, row in df.iterrows():
            sess_rows.setdefault(ts.strftime("%Y-%m-%d"), []).append((ts, row))
        for bts, brow in bars.iterrows():
            d = bts.strftime("%Y-%m-%d")
            bin_rows = [(ts, r) for ts, r in sess_rows[d]
                        if (ts.strftime("%H:%M") < "13:30") == (bts.strftime("%H:%M") == "09:30")]
            o = bin_rows[0][1]["Open"]; h = max(r["High"] for _, r in bin_rows)
            l = min(r["Low"] for _, r in bin_rows); c = bin_rows[-1][1]["Close"]
            v = sum(r["Volume"] for _, r in bin_rows)
            if not (o == brow["Open"] and h == brow["High"] and l == brow["Low"]
                    and c == brow["Close"] and v == brow["Volume"]):
                agg_bad += 1
            # SessionVWAP: cumulative within session through this bin's last row
            upto = [r for ts, r in sess_rows[d] if ts <= bin_rows[-1][0]]
            pv = sum(((r["High"] + r["Low"] + r["Close"]) / 3.0) * r["Volume"] for r in upto)
            vv = sum(r["Volume"] for r in upto)
            vwap = pv / vv if vv > 0 else np.nan
            if not np.isclose(vwap, brow["SessionVWAP"], rtol=1e-9, atol=1e-9):
                agg_bad += 1
        if agg_bad:
            fail("P2", f"{sym}: {agg_bad} bars fail aggregation parity")
        if not grid_ok:
            fail("P2", f"{sym}: 4H grid != pinned session table: {detail}")
        bars4h[sym] = bars
        out[sym] = {"bars_4h": len(bars), "grid_matches_pinned_table": grid_ok,
                    "aggregation_parity_bad_bars": agg_bad,
                    "first_bar": bars.index[0].isoformat(),
                    "last_bar": bars.index[-1].isoformat()}
        print(f"P2 {sym}: {len(bars)} 4H bars, grid ok={grid_ok}, agg bad={agg_bad}",
              flush=True)
    report["phases"]["P2_grid_parity"] = out
    return bars4h


# ---------------------------------------------------------------- Phase 3
def phase3(bars4h):
    import pine_backtest as pb
    import pine_stack as st
    from pine_ranking import gen_candidates, compute_features
    from pine_signal_quality import extend_row
    from pine_exposure import SECTOR

    data, closes = {}, {}
    for sym in SYMBOLS:
        data[sym] = pb.add_pine_indicators(bars4h[sym])
        closes[sym] = data[sym]["Close"]

    # SPY daily benchmark from the SAME admitted bytes (mirrors
    # load_benchmarks' tz handling: daily bars indexed ET-midnight -> UTC)
    daily = {}
    spy_adm = ADMITTED_FRAMES["SPY"]
    for d, grp in spy_adm.groupby(spy_adm.index.strftime("%Y-%m-%d")):
        daily[d] = {"Open": grp["Open"].iloc[0], "High": grp["High"].max(),
                    "Low": grp["Low"].min(), "Close": grp["Close"].iloc[-1],
                    "Volume": grp["Volume"].sum()}
    didx = pd.DatetimeIndex([pd.Timestamp(d) for d in daily]).tz_localize(ET).tz_convert("UTC")
    spy_daily = pd.DataFrame([daily[d] for d in daily], index=didx).sort_index()
    bench = {"SPY": spy_daily}

    # candidates, load_bull order/semantics
    all_trades, skipped_gap, order_of = [], 0, {}
    for sym in SYMBOLS:
        tr, sg = gen_candidates(sym, data[sym])
        skipped_gap += sg
        for t in tr:
            order_of[id(t)] = len(order_of)
        all_trades.extend(tr)
    all_trades.sort(key=lambda t: order_of[id(t)])

    # per-candidate parity on real input (frozen formulas at recorded indices)
    parity_bad = []
    for tr in all_trades:
        df = data[tr["symbol"]]
        i = tr["signal_idx"]
        sig = df.iloc[i]
        ok = (pb.pine_buy_signal(df, i)
              and tr["entry"] == float(df["Open"].iloc[i + 1])
              and abs(tr["stop"] - float(sig["Close"] - sig["atr"] * pb.SL_ATR)) < 1e-9
              and abs(tr["tp1"] - (tr["entry"] + float(sig["atr"]) * pb.TP_ATR)) < 1e-9
              and tr["entry_time"] == df.index[i + 1]
              and tr["exit_time"] >= tr["entry_time"])
        if not ok:
            parity_bad.append((tr["symbol"], tr["signal_time"]))
    if parity_bad:
        fail("P3", f"candidate parity failures: {parity_bad[:5]}")
    report["phases"]["P3_candidate_parity"] = {
        "candidates": len(all_trades), "parity_bad": len(parity_bad),
        "skipped_gap_below_stop": skipped_gap}

    feats = compute_features(all_trades, data, bench)
    st.rs = {id(tr): feats[i]["rs"] for i, tr in enumerate(all_trades)}

    # C0 fidelity invariant on THIS data (stack's own check, as in C1 script)
    port_pb = pb.simulate_portfolio(all_trades, closes, pb.COSTS["4bps"], pb.RISK_PCT)
    port_c0 = st.simulate_stack(all_trades, closes, pb.COSTS["4bps"],
                                False, False, False, SECTOR)
    fidelity = abs(port_pb["final_equity"] - port_c0["final_equity"]) < 1e-6
    report["phases"]["P3_c0_fidelity"] = {
        "pass": bool(fidelity),
        "pb_final_equity": port_pb["final_equity"],
        "stack_c0_final_equity": port_c0["final_equity"]}
    if not fidelity:
        fail("P3", "C0 fidelity invariant failed on diagnostic inputs")
        return

    # THE ONE RUN: frozen C1 configuration (R1 ranking + R2 sector cap, no R3)
    results = {}
    taken_by_cost = {}
    final_equity = {}
    for cost_name in ("4bps", "25bps"):
        cost = pb.COSTS[cost_name]
        port = st.simulate_stack(all_trades, closes, cost, True, True, False, SECTOR)
        final_equity[cost_name] = port["final_equity"]
        taken = [all_trades[i] for i in port["taken"]]
        row = pb.summarize("EXPLORATORY_4NAME_DEV_C1CFG", taken, port,
                           skipped_gap, cost_name)
        row = extend_row(row, taken, cost_name)
        row["sector_cap_skips"] = port["skipped_gate"]
        row["rank_skips"] = port["skipped_rank"]
        row["candidates_available"] = len(all_trades)
        gross = [pb._outcome(t["entry"], t["stop"], t["exit"], 0.0)[1] for t in taken]
        row["expectancy_gross_r"] = round(float(np.mean(gross)), 3) if gross else None
        results[cost_name] = row
        taken_by_cost[cost_name] = taken
    # determinism: identical re-invocation of the same preregistered sim
    port_rep = st.simulate_stack(all_trades, closes, pb.COSTS["4bps"],
                                 True, True, False, SECTOR)
    taken_idx_4 = [i for i, t in enumerate(all_trades) if t in taken_by_cost["4bps"]]
    det = (set(port_rep["taken"]) == set(taken_idx_4)
           and port_rep["final_equity"] == final_equity["4bps"])
    report["phases"]["P3_determinism"] = {
        "identical_taken_set": bool(set(port_rep["taken"]) == set(taken_idx_4)),
        "identical_final_equity": bool(port_rep["final_equity"] == final_equity["4bps"])}
    if not det:
        fail("P3", "determinism re-invocation diverged")
    report["phases"]["P3_run"] = results

    # per-symbol detail on taken trades + full ledger
    ledger = []
    for t in all_trades:
        _, gr, nr4, _ = pb._outcome(t["entry"], t["stop"], t["exit"], pb.COSTS["4bps"])
        _, _, nr25, _ = pb._outcome(t["entry"], t["stop"], t["exit"], pb.COSTS["25bps"])
        ledger.append({"symbol": t["symbol"], "signal_time": t["signal_time"],
                       "entry_time": str(t["entry_time"]), "exit_time": str(t["exit_time"]),
                       "entry": t["entry"], "stop": t["stop"], "tp1": t["tp1"],
                       "exit_synth": t["exit"], "reason": t["reason"],
                       "tp1_hit": t["tp1_hit"], "hold_bars": t["hold_bars"],
                       "gross_r": round(gr, 4), "net_r_4bps": round(nr4, 4),
                       "net_r_25bps": round(nr25, 4),
                       "taken_4bps": t in taken_by_cost["4bps"],
                       "taken_25bps": t in taken_by_cost["25bps"]})
    per_symbol = {}
    for sym in SYMBOLS:
        cand = [x for x in ledger if x["symbol"] == sym]
        tk = [x for x in cand if x["taken_4bps"]]
        per_symbol[sym] = {
            "candidates": len(cand), "taken": len(tk),
            "mean_net_r_4bps": round(float(np.mean([x["net_r_4bps"] for x in tk])), 3) if tk else None,
            "sum_net_r_4bps": round(float(np.sum([x["net_r_4bps"] for x in tk])), 3) if tk else None,
            "mean_net_r_25bps": round(float(np.mean([x["net_r_25bps"] for x in tk])), 3) if tk else None,
            "win_rate_4bps_pct": round(100.0 * np.mean([x["net_r_4bps"] > 0 for x in tk]), 1) if tk else None}
    report["phases"]["P3_per_symbol"] = per_symbol
    with open(os.path.join(HERE, "trade_ledger.json"), "w") as f:
        json.dump(ledger, f, indent=1, default=str)
    print(f"P3 run: candidates={len(all_trades)} taken4={len(taken_by_cost['4bps'])} "
          f"taken25={len(taken_by_cost['25bps'])}", flush=True)
    for cn, row in results.items():
        print(f"  [{cn}] n={row['trades']} exp={row['expectancy_net_r']}R "
              f"gross={row['expectancy_gross_r']}R PF={row['profit_factor']} "
              f"ret={row['total_return_pct']}% dd={row['max_drawdown_pct']}% "
              f"exposure={row['market_exposure_pct']}% win={row['win_rate_pct']}%", flush=True)


def main():
    phase0()
    dev = load_session_table()
    admitted = phase1(dev)
    ADMITTED_FRAMES.update(admitted)
    if failures:
        report["verdict"] = "STOP_PREFLIGHT"
        report["blockers"] = failures
        json.dump(report, open(os.path.join(HERE, "results.json"), "w"), indent=1, default=str)
        print("STOP: preflight failed; no performance figures produced.", flush=True)
        return 2
    bars = phase2(admitted, dev)
    if failures:
        report["verdict"] = "STOP_PARITY"
        report["blockers"] = failures
        json.dump(report, open(os.path.join(HERE, "results.json"), "w"), indent=1, default=str)
        print("STOP: parity failed; no performance figures produced.", flush=True)
        return 2
    phase3(bars)
    if failures:
        report["verdict"] = "STOP_RUN"
        report["blockers"] = failures
    else:
        report["verdict"] = "EXPLORATORY_RUN_COMPLETE"
    json.dump(report, open(os.path.join(HERE, "results.json"), "w"), indent=1, default=str)
    print(f"VERDICT: {report['verdict']}", flush=True)
    return 0 if not failures else 2


if __name__ == "__main__":
    sys.exit(main())
