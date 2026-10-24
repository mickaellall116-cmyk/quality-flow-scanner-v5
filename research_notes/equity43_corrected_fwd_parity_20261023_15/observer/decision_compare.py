"""QF-EQUITY43-CORRECTED-FORWARD-PARITY-BUILD-20261023-15 — actual-byte
decision-parity bridge (OFFLINE, instrument parity only).

Streams the lawfully retained DEV-only 1h bytes for the 43 equities
(qf-data-archive @ bb644db: continuation namespace + pilot namespace)
through the EQUITY43-CORRECTED-FWD-v1 candidate observer in global
chronological order, and compares — at DECISION level only — against the
-13 study (package 521980a):

  * emitted 4H bars vs the -13 batch session-anchored construction
    (OHLCV + SessionVWAP, every bar, every symbol);
  * the observer's SPY as-of daily benchmark vs the -13 as-of fork
    construction on the same admitted bytes;
  * candidate events (identity, entry/stop/TP1 terms, entry/exit times,
    exit reason, hold bars, TP1-hit, censoring) vs the -13 canonical
    candidate list produced by the pinned reference driver;
  * RS ranking features per candidate vs the -13 committed ledger;
  * portfolio DECISIONS (taken flags at gross/4bps/25bps, 4bps C1
    dispositions, terminal-inventory symbol membership per view, C0
    taken/skip counts) vs the -13 committed trade ledger / results.

NO performance is computed or reported here: no R, no equity, no returns
are read out of any simulator result or written to any artifact. The
simulators are used solely as decision oracles over candidate events,
exactly as the governing task specifies (instrument parity only).

Exit 0 = full decision parity. Exit 2 = STOP: first material mismatch is
reported verbatim; nothing is auto-corrected after viewing outcomes.
"""
import hashlib
import importlib.util
import json
import os
import sys

STAGE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else \
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WORK = os.path.join(STAGE, "work")
os.makedirs(WORK, exist_ok=True)
for p in (STAGE, os.path.join(STAGE, "engine_successor"),
          os.path.join(STAGE, "engine_successor", "pine_stack"),
          os.path.join(STAGE, "engine_successor", "pine_ranking"),
          os.path.join(STAGE, "engine_successor", "pine_exposure"),
          os.path.join(STAGE, "engine_successor",
                       "pine_signal_quality")):
    sys.path.insert(0, p)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

import fwd_observer as fo  # noqa: E402

# ------------------------------------------------------- reference driver
spec = importlib.util.spec_from_file_location(
    "ref13", os.path.join(STAGE, "reference_run_study13.py"))
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)

import pine_backtest as pb  # noqa: E402
import pine_stack as st  # noqa: E402
from pine_ranking import compute_features  # noqa: E402
from pine_exposure import SECTOR  # noqa: E402

TOL = 1e-9
out = {"task": "QF-EQUITY43-CORRECTED-FORWARD-PARITY-BUILD-20261023-15",
       "comparison": "observer (streaming) vs -13 study (batch), "
                     "decision-level only",
       "sections": {}}
problems = []


def note(section, **kw):
    out["sections"][section] = kw
    print(f"[{section}] {kw}", flush=True)


def main():
    child_manifest = json.load(open(os.path.join(STAGE,
                                                 "child_manifest.json")))
    symbols43 = ref.PILOT + [l["symbol"] for l in child_manifest["legs"]
                             if l["window"] == "W_DEV"]
    assert len(symbols43) == 43 and len(set(symbols43)) == 43
    out["universe"] = symbols43

    # ---- inventory evidence: pins, archive sums, receipt chains (ref P0/P1)
    ref.phase0()
    if ref.failures:
        problems.extend(ref.failures)
        return finish()
    ref.phase1(child_manifest)
    if ref.failures:
        problems.extend(ref.failures)
        return finish()
    note("inventory", pins="PASS (ref P0: successor/fork/original engine "
                           "pins, archive SHA256SUMS, PAUSED pins)",
         chains="PASS (ref P1: child chain 54/54 from GENESIS, roots "
                "recomputed; pilot receipts field-verified)")

    # ---- reference batch path (admission, bars, candidates) — no phase5
    table, dev_sessions = ref.load_session_table()
    admitted = ref.phase2(table, dev_sessions, symbols43)
    if ref.failures:
        problems.extend(ref.failures)
        return finish()
    bars_ref = ref.phase4(admitted, dev_sessions, symbols43)
    if ref.failures:
        problems.extend(ref.failures)
        return finish()
    data_ref, closes_ref, canonical_ref, closed_ref, censored_ref, \
        sg_ref, feats_ref = ref.build_inputs(bars_ref, admitted, symbols43)
    if ref.failures:
        problems.extend(ref.failures)
        return finish()
    cutoff = max(bars_ref[s].index[-1] for s in symbols43) \
        + pd.Timedelta(hours=4)
    note("reference", closed_candidates=len(closed_ref),
         censored_candidates=len(censored_ref),
         total_candidates=len(canonical_ref),
         skipped_gap_below_stop=sg_ref, cutoff=str(cutoff))

    # ---- observer streaming path over the same raw bytes
    table_o = fo.SessionTable(json.load(open(
        os.path.join(STAGE, "session_table.json"))))
    jpath = os.path.join(WORK, "compare_journal.jsonl")
    apath = os.path.join(WORK, "anchors", "compare_anchor.json")
    os.makedirs(os.path.dirname(apath), exist_ok=True)
    journal = fo.Journal(jpath, apath)
    obs = fo.ForwardObserver(table_o, journal, pb, symbols43)
    rows = []
    for sym in symbols43:
        ns = ref.NSP if sym in ref.PILOT else ref.NS11
        raw = json.load(open(os.path.join(ns, "raw", f"{sym}__DEV.json")))
        for r in raw["values"]:
            rows.append((r["datetime"], sym, r))
    rows.sort(key=lambda x: (x[0], x[1]))
    n_rej = n_excl = 0
    for _, sym, r in rows:
        for ev in obs.ingest(sym, r):
            if ev["type"] == "REJECTED":
                n_rej += 1
                problems.append(f"observer rejected a DEV byte: {ev}")
            elif ev["type"] == "EXCLUDED_POSTCLOSE":
                n_excl += 1
    obs.flush()
    anchor = journal.anchor("decision_compare seal")
    journal.close()
    ok_j, info_j = fo.Journal.verify(jpath, apath)
    note("observer_stream", raw_rows=len(rows), rejected=n_rej,
         excluded_postclose=n_excl,
         decision_events=len(obs.decision_events),
         journal_records=len(journal.records), journal_verify=ok_j,
         journal_info=info_j, anchor_head=anchor["head"][:16])
    if not ok_j:
        problems.append(f"journal verification failed: {info_j}")
    if n_rej:
        return finish()

    # ---- bars parity
    bar_bad = bar_n = vwap_max = 0
    for sym in symbols43:
        bo = obs.bars_frame(sym)
        br = bars_ref[sym]
        if len(bo) != len(br) or not bo.index.equals(br.index):
            bar_bad += 1
            problems.append(f"{sym}: bar index/count mismatch "
                            f"{len(bo)} vs {len(br)}")
            continue
        for col in ("Open", "High", "Low", "Close", "Volume"):
            if not (bo[col].to_numpy() == br[col].to_numpy()).all():
                bar_bad += 1
                problems.append(f"{sym}: {col} mismatch")
        d = (bo["SessionVWAP"] - br["SessionVWAP"]).abs().max()
        vwap_max = max(vwap_max, float(d) if d == d else 0.0)
        bar_n += len(br)
    note("bars_parity", bars_compared=bar_n, symbols_bad=bar_bad,
         sessionvwap_max_abs_diff=vwap_max)
    if bar_bad or vwap_max > 1e-9:
        problems.append("4H bar parity failure")
        return finish()

    # ---- benchmark parity (observer SPY as-of vs fork construction)
    import asof_benchmark
    bench_ref = asof_benchmark.build_daily_asof(admitted["SPY"])
    bench_obs = obs.benchmark_asof("SPY")
    bench_ok = bench_obs.index.equals(bench_ref.index) and all(
        (bench_obs[c].to_numpy() == bench_ref[c].to_numpy()).all()
        for c in ("Open", "High", "Low", "Close", "Volume"))
    note("benchmark_parity", equal=bool(bench_ok),
         sessions=len(bench_ref))
    if not bench_ok:
        problems.append("SPY as-of benchmark mismatch")
        return finish()

    # ---- candidate parity (decision fields only)
    def keyf(t):
        return (t["symbol"], t["signal_idx"])

    ref_by_key = {keyf(t): t for t in canonical_ref}
    obs_cands = obs.candidates()
    obs_by_key = {keyf(t): t for t in obs_cands}
    cand_bad = []
    max_term_diff = 0.0
    if set(ref_by_key) != set(obs_by_key):
        cand_bad.append(f"candidate key sets differ: only-ref "
                        f"{sorted(set(ref_by_key) - set(obs_by_key))[:5]} "
                        f"only-obs "
                        f"{sorted(set(obs_by_key) - set(ref_by_key))[:5]}")
    for k in sorted(set(ref_by_key) & set(obs_by_key)):
        a, b = ref_by_key[k], obs_by_key[k]
        for f in ("entry", "stop", "tp1"):
            max_term_diff = max(max_term_diff, abs(a[f] - b[f]))
            if abs(a[f] - b[f]) > TOL:
                cand_bad.append(f"{k}: {f} {a[f]} vs {b[f]}")
        checks = [
            ("tp1_hit", a["tp1_hit"] == b["tp1_hit"]),
            ("entry_time", str(a["entry_time"]) == str(b["entry_time"])),
            ("signal_time", a["signal_time"] == b["signal_time"]),
            ("censored", bool(a.get("censored")) == bool(b.get("censored"))),
            ("exit_time", (None if a["exit_time"] is None
                           else str(a["exit_time"])) ==
                          (None if b["exit_time"] is None
                           else str(b["exit_time"]))),
            ("reason", a["reason"] == b["reason"]),
            ("hold_bars", a["hold_bars"] == b["hold_bars"]),
        ]
        for name, okc in checks:
            if not okc:
                cand_bad.append(f"{k}: {name} differs "
                                f"({a.get(name)} vs {b.get(name)})")
    note("candidate_parity", compared=len(ref_by_key),
         mismatches=len(cand_bad), first=cand_bad[:5],
         max_term_abs_diff=max_term_diff,
         skipped_gap_below_stop_observer=sum(
             m.skipped_gap for m in obs.machines.values()),
         skipped_gap_below_stop_reference=sg_ref)
    if cand_bad:
        problems.extend(cand_bad[:10])
        return finish()

    # ---- portfolio decision parity vs the committed -13 ledger/results
    ledger = json.load(open(os.path.join(STAGE, "engine",
                                         "td13_trade_ledger.json")))
    led_by_key = {(r["symbol"], r["signal_idx"]): r for r in ledger}
    results13 = json.load(open(os.path.join(STAGE, "engine",
                                            "td13_results.json")))
    canonical_o = sorted(obs_cands, key=lambda t: (t["symbol"],
                                                   t["signal_idx"]))
    data_o = {s: pb.add_pine_indicators(obs.bars_frame(s))
              for s in symbols43}
    closes_o = {s: data_o[s]["Close"] for s in symbols43}
    feats_o = compute_features(canonical_o, data_o, {"SPY": bench_obs})
    rs_bad = 0
    for i, t in enumerate(canonical_o):
        lr = led_by_key[keyf(t)]
        if abs(feats_o[i]["rs"] - lr["rs"]) > 1e-9:
            rs_bad += 1
    pb.COSTS.setdefault("gross", 0.0)
    st.rs = {id(tr): feats_o[i]["rs"] for i, tr in enumerate(canonical_o)}
    taken_o, disp_o, term_o = {}, None, {}
    for view in ("gross", "4bps", "25bps"):
        port = st.simulate_stack(canonical_o, closes_o, pb.COSTS[view],
                                 True, True, False, SECTOR, cutoff=cutoff)
        taken_o[view] = {keyf(canonical_o[i]) for i in port["taken"]}
        term_o[view] = sorted(x["symbol"] for x in port["terminal_open"])
        if view == "4bps":
            disp_o = {keyf(canonical_o[i]): v
                      for i, v in port["disposition"].items()}
    dec_bad = []
    for k, lr in led_by_key.items():
        for view in ("gross", "4bps", "25bps"):
            if (k in taken_o[view]) != bool(lr[f"taken_{view}"]):
                dec_bad.append(f"{k}: taken_{view} differs")
        if disp_o.get(k) != lr["disposition_4bps_c1"]:
            dec_bad.append(f"{k}: disposition_4bps {disp_o.get(k)} vs "
                           f"{lr['disposition_4bps_c1']}")
    term_ref = {}
    for view, lst in results13["phases"]["P5_terminal_open_disclosure"][
            "c1_outcomes_by_view"].items():
        term_ref[view] = sorted(x["symbol"] for x in lst)
    term_bad = [v for v in term_o if term_o[v] != term_ref[v]]
    # C0 (unranked control) decision counts at 4bps vs -13 results.json
    port_c0 = st.simulate_stack(canonical_o, closes_o, pb.COSTS["4bps"],
                                False, False, False, SECTOR, cutoff=cutoff)
    c0_ref = results13["phases"]["P4_c0_fidelity_trade_by_trade"]
    c0_counts = {"taken_count": len(port_c0["taken"]),
                 "skipped_cap": port_c0["skipped_cap"],
                 "skipped_risk": port_c0["skipped_risk"]}
    c0_ref_counts = {"taken_count": c0_ref["taken_count"],
                     "skipped_cap": c0_ref["skipped_cap"],
                     "skipped_risk": c0_ref["skipped_risk"]}
    note("decision_parity", rs_mismatches=rs_bad,
         decision_mismatches=len(dec_bad), first=dec_bad[:5],
         terminal_symbol_mismatch_views=term_bad,
         terminal_observer=term_o, terminal_reference=term_ref,
         c0_counts_observer=c0_counts, c0_counts_reference=c0_ref_counts)
    if rs_bad or dec_bad or term_bad or c0_counts != c0_ref_counts:
        problems.append("portfolio decision parity failure")
        return finish()
    return finish()


def finish():
    out["problems"] = problems
    out["verdict"] = "DECISION_PARITY_PASS" if not problems else \
        "STOP_DECISION_PARITY_FAILURE"
    with open(os.path.join(WORK, "compare_results.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(f"VERDICT: {out['verdict']}", flush=True)
    if problems:
        print("PROBLEMS:", problems[:10], flush=True)
    return 0 if not problems else 2


if __name__ == "__main__":
    sys.exit(main())
