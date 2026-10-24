"""QF-EQUITY43-FWD-DECISION-PARITY-REPAIR-20261023-16 — offline
decision-parity repair harness (fail-before / root-cause / minimal repair /
one re-comparison).

Governing text: Issue #1 comment 6377575196. The -15 comparison
(commit 5f77509) recorded STOP_DECISION_PARITY_FAILURE with 201 decision
mismatches, but its candidate-parity loop never compared the candidate
`exit` price — a field simulate_stack consumes for cash-flow/equity state
via pb._outcome(entry, stop, exit, cost).

This harness extends the -15 comparison with:
  * FIELD CENSUS — every simulator-consumed candidate field compared
    between observer and -13 reference for all 590 candidates: symbol,
    signal_idx, entry, stop, tp1, EXIT, entry_time, exit_time,
    signal_time, reason, hold_bars, tp1_hit, censored, plus the derived
    risk denominator (entry-stop)/entry, plus dict key-set identity;
  * CLOSE-SERIES IDENTITY — the exact closes series each simulator path
    consumes (index + values, exact equality), per symbol;
  * CONFIG PINS — the -13 experiment config sha256 (87b8285a…) recomputed
    by the pinned reference driver, simulator constants, SECTOR map hash;
  * REFERENCE SELF-CHECK — the reference candidate set itself, run
    through the identical decision path, must reproduce the committed
    -13 ledger exactly (guards the harness, not the observer);
  * DIAGNOSTICS (optional, attribution only): chronological
    first-divergence walk and an exit-substitution experiment.

VERDICT DERIVATION (fail-closed): the verdict is computed at finish()
from the section VALUES in this process (mismatch counts, equality
booleans), never from any wrapper/stream signal. Exit 0 iff PASS.
The RESULT is produced by report16.py, which re-reads the JSON this
harness writes and re-derives the verdict from the counts — a PASS
cannot be reported unless the committed JSON itself proves it.

NO performance is computed or reported: no R/equity/returns are read
out as results. Simulators are decision oracles only; the walk uses
exit cash-flow VALUES solely to locate the first divergent event in
time (attribution), never as a performance figure.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import sys

ap = argparse.ArgumentParser()
ap.add_argument("stage")
ap.add_argument("--observer", required=True)
ap.add_argument("--tag", required=True)
ap.add_argument("--diagnostics", action="store_true")
ARGS = ap.parse_args()

STAGE = os.path.abspath(ARGS.stage)
WORK = os.path.join(STAGE, "work")
os.makedirs(WORK, exist_ok=True)
for p in (STAGE, os.path.join(STAGE, "engine_successor"),
          os.path.join(STAGE, "engine_successor", "pine_stack"),
          os.path.join(STAGE, "engine_successor", "pine_ranking"),
          os.path.join(STAGE, "engine_successor", "pine_exposure"),
          os.path.join(STAGE, "engine_successor",
                       "pine_signal_quality")):
    sys.path.insert(0, p)

import pandas as pd  # noqa: E402

spec_o = importlib.util.spec_from_file_location("fo16", ARGS.observer)
fo = importlib.util.module_from_spec(spec_o)
spec_o.loader.exec_module(fo)

spec = importlib.util.spec_from_file_location(
    "ref13", os.path.join(STAGE, "reference_run_study13.py"))
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)

import pine_backtest as pb  # noqa: E402
import pine_stack as st  # noqa: E402
from pine_ranking import compute_features  # noqa: E402
from pine_exposure import SECTOR  # noqa: E402

TOL = 1e-9
EXPECTED_CONFIG_SHA = \
    "87b8285a522ba0e3e5a80f0097b9668afc1ddf11da4fc5559c0ca31f55218706"
out = {"task": "QF-EQUITY43-FWD-DECISION-PARITY-REPAIR-20261023-16",
       "comparison": "observer (streaming) vs -13 study (batch), "
                     "decision-level only; full field census",
       "observer_module": os.path.basename(ARGS.observer),
       "tag": ARGS.tag,
       "sections": {}}
problems = []


def note(section, **kw):
    out["sections"][section] = kw
    print(f"[{section}] {kw}", flush=True)


def keyf(t):
    return (t["symbol"], t["signal_idx"])


def run_sim(cands, closes, feats, view, ranked, sector_cap):
    st.rs = {id(tr): feats[i]["rs"] for i, tr in enumerate(cands)}
    return st.simulate_stack(cands, closes, pb.COSTS[view], ranked,
                             sector_cap, False, SECTOR, cutoff=CUTOFF)


def main():
    global CUTOFF
    child_manifest = json.load(open(os.path.join(STAGE,
                                                 "child_manifest.json")))
    symbols43 = ref.PILOT + [l["symbol"] for l in child_manifest["legs"]
                             if l["window"] == "W_DEV"]
    assert len(symbols43) == 43 and len(set(symbols43)) == 43
    out["universe"] = symbols43

    # ---- inventory (ref P0/P1, unchanged from -15)
    ref.phase0()
    if ref.failures:
        problems.extend(ref.failures)
        return finish()
    ref.phase1(child_manifest)
    if ref.failures:
        problems.extend(ref.failures)
        return finish()
    note("inventory", pins="PASS (ref P0/P1 as -15)")

    # ---- config pins (census requirement)
    sector_sha = hashlib.sha256(json.dumps(
        {s: SECTOR[s] for s in symbols43}, sort_keys=True).encode()
        ).hexdigest()
    note("config_pins",
         experiment_config_sha256=ref.CONFIG_SHA256,
         experiment_config_sha_match=bool(
             ref.CONFIG_SHA256 == EXPECTED_CONFIG_SHA),
         start_equity=pb.START_EQUITY, risk_pct=pb.RISK_PCT,
         max_concurrent=pb.MAX_CONCURRENT,
         max_portfolio_risk=pb.MAX_PORTFOLIO_RISK,
         costs={k: pb.COSTS[k] for k in ("4bps", "25bps")},
         sl_atr=pb.SL_ATR, tp_atr=pb.TP_ATR, trail_atr=pb.TRAIL_ATR,
         warmup=pb.WARMUP, sector_map_sha256=sector_sha)
    if ref.CONFIG_SHA256 != EXPECTED_CONFIG_SHA:
        problems.append("experiment config pin mismatch")
        return finish()

    # ---- reference batch path (no phase5)
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
        sg_ref, feats_ref_list = ref.build_inputs(bars_ref, admitted,
                                                  symbols43)
    if ref.failures:
        problems.extend(ref.failures)
        return finish()
    CUTOFF = max(bars_ref[s].index[-1] for s in symbols43) \
        + pd.Timedelta(hours=4)
    note("reference", closed_candidates=len(closed_ref),
         censored_candidates=len(censored_ref),
         total_candidates=len(canonical_ref),
         skipped_gap_below_stop=sg_ref, cutoff=str(CUTOFF))

    # ---- observer streaming path over the same raw bytes
    table_o = fo.SessionTable(json.load(open(
        os.path.join(STAGE, "session_table.json"))))
    jpath = os.path.join(WORK, f"compare16_{ARGS.tag}_journal.jsonl")
    apath = os.path.join(WORK, "anchors", f"compare16_{ARGS.tag}.json")
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
    anchor = journal.anchor("decision_compare16 seal")
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

    # ---- bars parity (as -15)
    bar_bad = bar_n = 0
    vwap_max = 0.0
    for sym in symbols43:
        bo = obs.bars_frame(sym)
        br = bars_ref[sym]
        if len(bo) != len(br) or not bo.index.equals(br.index):
            bar_bad += 1
            problems.append(f"{sym}: bar index/count mismatch")
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

    # ---- benchmark parity (as -15)
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

    # ---- closes identity (the series each simulator consumes)
    data_o = {s: pb.add_pine_indicators(obs.bars_frame(s))
              for s in symbols43}
    closes_o = {s: data_o[s]["Close"] for s in symbols43}
    close_bad = []
    close_max = 0.0
    for sym in symbols43:
        a, b = closes_ref[sym], closes_o[sym]
        if not a.index.equals(b.index):
            close_bad.append(f"{sym}: index differs")
            continue
        d = float((a - b).abs().max())
        close_max = max(close_max, d)
        if d != 0.0:
            close_bad.append(f"{sym}: max abs diff {d}")
    note("closes_identity", symbols_compared=len(symbols43),
         symbols_bad=len(close_bad), max_abs_diff=close_max,
         first=close_bad[:5])
    if close_bad:
        problems.append("closes series identity failure")
        return finish()

    # ---- FIELD CENSUS: every simulator-consumed candidate field
    ref_by_key = {keyf(t): t for t in canonical_ref}
    obs_cands = obs.candidates()
    obs_by_key = {keyf(t): t for t in obs_cands}
    fields = ["entry", "stop", "tp1", "exit", "entry_time", "exit_time",
              "signal_time", "reason", "hold_bars", "tp1_hit", "censored",
              "risk_frac"]
    census = {}
    keyset_bad = []
    if set(ref_by_key) != set(obs_by_key):
        keyset_bad.append("candidate key sets differ")
    extra_keys = set()
    for k in set(ref_by_key) & set(obs_by_key):
        extra_keys |= (set(ref_by_key[k]) ^ set(obs_by_key[k]))
    for f in fields:
        bad = []
        maxd = 0.0
        for k in sorted(set(ref_by_key) & set(obs_by_key)):
            a, b = ref_by_key[k], obs_by_key[k]
            if f == "risk_frac":
                va = (a["entry"] - a["stop"]) / a["entry"]
                vb = (b["entry"] - b["stop"]) / b["entry"]
            elif f in ("entry_time", "exit_time"):
                va = None if a[f] is None else str(a[f])
                vb = None if b[f] is None else str(b[f])
            else:
                va, vb = a.get(f), b.get(f)
            if isinstance(va, float) and isinstance(vb, float):
                d = abs(va - vb)
                maxd = max(maxd, d)
                if d > TOL:
                    bad.append([str(k), va, vb])
            elif va != vb:
                bad.append([str(k), str(va), str(vb)])
        census[f] = {"compared": len(set(ref_by_key) & set(obs_by_key)),
                     "mismatches": len(bad), "max_abs_diff": maxd,
                     "first": bad[:5]}
    census_total = sum(c["mismatches"] for c in census.values()) \
        + len(keyset_bad)
    note("field_census", total_mismatches=census_total,
         per_field={f: census[f]["mismatches"] for f in fields},
         keyset_problems=keyset_bad,
         extra_key_asymmetry=sorted(extra_keys),
         detail=census)
    if keyset_bad:
        problems.extend(keyset_bad)

    # ---- decision parity vs committed -13 ledger/results (as -15)
    ledger = json.load(open(os.path.join(STAGE, "engine",
                                         "td13_trade_ledger.json")))
    led_by_key = {(r["symbol"], r["signal_idx"]): r for r in ledger}
    results13 = json.load(open(os.path.join(STAGE, "engine",
                                            "td13_results.json")))
    canonical_o = sorted(obs_cands, key=lambda t: (t["symbol"],
                                                   t["signal_idx"]))
    feats_o = compute_features(canonical_o, data_o, {"SPY": bench_obs})
    rs_bad_o = sum(1 for i, t in enumerate(canonical_o)
                   if abs(feats_o[i]["rs"]
                          - led_by_key[keyf(t)]["rs"]) > 1e-9)
    pb.COSTS.setdefault("gross", 0.0)
    taken_o, disp_o, term_o = {}, None, {}
    ports_o = {}
    for view in ("gross", "4bps", "25bps"):
        port = run_sim(canonical_o, closes_o, feats_o, view, True, True)
        ports_o[view] = port
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
    port_c0_o = run_sim(canonical_o, closes_o, feats_o, "4bps",
                        False, False)
    c0_ref = results13["phases"]["P4_c0_fidelity_trade_by_trade"]
    c0_counts_o = {"taken_count": len(port_c0_o["taken"]),
                   "skipped_cap": port_c0_o["skipped_cap"],
                   "skipped_risk": port_c0_o["skipped_risk"]}
    c0_ref_counts = {"taken_count": c0_ref["taken_count"],
                     "skipped_cap": c0_ref["skipped_cap"],
                     "skipped_risk": c0_ref["skipped_risk"]}
    note("decision_parity", rs_mismatches=rs_bad_o,
         decision_mismatches=len(dec_bad), first=dec_bad[:5],
         terminal_symbol_mismatch_views=term_bad,
         terminal_observer=term_o, terminal_reference=term_ref,
         c0_counts_observer=c0_counts_o, c0_counts_reference=c0_ref_counts)
    if rs_bad_o or dec_bad or term_bad or c0_counts_o != c0_ref_counts:
        problems.append("portfolio decision parity failure")

    # ---- REFERENCE SELF-CHECK: reference candidates through the same
    # decision path must reproduce the committed ledger exactly.
    canonical_r = sorted(canonical_ref, key=lambda t: (t["symbol"],
                                                        t["signal_idx"]))
    feats_r = compute_features(canonical_r, data_ref, {"SPY": bench_ref})
    rs_bad_r = sum(1 for i, t in enumerate(canonical_r)
                   if abs(feats_r[i]["rs"]
                          - led_by_key[keyf(t)]["rs"]) > 1e-9)
    taken_r, disp_r, term_r = {}, None, {}
    for view in ("gross", "4bps", "25bps"):
        port = run_sim(canonical_r, closes_ref, feats_r, view, True, True)
        taken_r[view] = {keyf(canonical_r[i]) for i in port["taken"]}
        term_r[view] = sorted(x["symbol"] for x in port["terminal_open"])
        if view == "4bps":
            disp_r = {keyf(canonical_r[i]): v
                      for i, v in port["disposition"].items()}
    self_bad = []
    for k, lr in led_by_key.items():
        for view in ("gross", "4bps", "25bps"):
            if (k in taken_r[view]) != bool(lr[f"taken_{view}"]):
                self_bad.append(f"{k}: taken_{view} differs")
        if disp_r.get(k) != lr["disposition_4bps_c1"]:
            self_bad.append(f"{k}: disposition_4bps differs")
    port_c0_r = run_sim(canonical_r, closes_ref, feats_r, "4bps",
                        False, False)
    c0_counts_r = {"taken_count": len(port_c0_r["taken"]),
                   "skipped_cap": port_c0_r["skipped_cap"],
                   "skipped_risk": port_c0_r["skipped_risk"]}
    self_term_bad = [v for v in term_r if term_r[v] != term_ref[v]]
    note("reference_selfcheck", rs_mismatches=rs_bad_r,
         decision_mismatches=len(self_bad),
         terminal_mismatch_views=self_term_bad,
         c0_counts=c0_counts_r,
         c0_match=bool(c0_counts_r == c0_ref_counts))
    if rs_bad_r or self_bad or self_term_bad \
            or c0_counts_r != c0_ref_counts:
        problems.append("REFERENCE SELF-CHECK failure (harness, "
                        "not observer)")

    # ---- DIAGNOSTICS (attribution only; not part of the verdict path
    # beyond what the sections above already record)
    if ARGS.diagnostics:
        diag = {}
        # earliest field-level divergence by exit_time (closed trades)
        exit_bad_keys = [k for k in sorted(set(ref_by_key)
                                           & set(obs_by_key))
                         if ref_by_key[k].get("exit")
                         != obs_by_key[k].get("exit")]
        exit_bad_keys_sorted = sorted(
            exit_bad_keys,
            key=lambda k: (str(ref_by_key[k]["exit_time"]), k))
        diag["exit_field_mismatch_count"] = len(exit_bad_keys)
        diag["exit_field_all_tp1_hit"] = bool(exit_bad_keys) and all(
            ref_by_key[k]["tp1_hit"] for k in exit_bad_keys)
        diag["exit_field_none_tp1_hit"] = bool(exit_bad_keys) and not any(
            ref_by_key[k]["tp1_hit"] for k in exit_bad_keys
            if ref_by_key[k].get("exit") is not None)
        if exit_bad_keys_sorted:
            k0 = exit_bad_keys_sorted[0]
            diag["first_exit_field_divergence"] = {
                "key": str(k0),
                "exit_time": str(ref_by_key[k0]["exit_time"]),
                "ref_exit": ref_by_key[k0]["exit"],
                "obs_exit": obs_by_key[k0]["exit"],
                "tp1_hit": ref_by_key[k0]["tp1_hit"],
                "reason": ref_by_key[k0]["reason"]}
        # first-divergence walk on the 4bps C1 sims (obs vs ref)
        port_o4 = ports_o["4bps"]
        port_r4 = run_sim(canonical_r, closes_ref, feats_r, "4bps",
                          True, True)
        cf_o = {tuple(x["key"]): x for x in port_o4["exit_cashflows"]}
        cf_r = {tuple(x["key"]): x for x in port_r4["exit_cashflows"]}
        exit_order = sorted(
            set(cf_o) | set(cf_r),
            key=lambda k: (str(ref_by_key[k]["exit_time"]), k))
        first_cf = None
        for k in exit_order:
            a, b = cf_r.get(k), cf_o.get(k)
            if a is None or b is None or a["cash_flow"] != b["cash_flow"] \
                    or a["net_r"] != b["net_r"]:
                first_cf = {"key": str(k),
                            "exit_time": str(ref_by_key[k]["exit_time"]),
                            "in_ref": a is not None,
                            "in_obs": b is not None,
                            "ref_cash_flow": None if a is None
                            else a["cash_flow"],
                            "obs_cash_flow": None if b is None
                            else b["cash_flow"]}
                break
        diag["first_cashflow_divergence"] = first_cf
        disp_r4 = {keyf(canonical_r[i]): v
                   for i, v in port_r4["disposition"].items()}
        disp_diff_keys = [k for k in disp_o if disp_o.get(k)
                          != disp_r4.get(k)]
        disp_diff_sorted = sorted(
            disp_diff_keys,
            key=lambda k: (str(ref_by_key[k]["entry_time"]), k))
        diag["disposition_diff_count_vs_ref_sim"] = len(disp_diff_keys)
        if disp_diff_sorted:
            kd = disp_diff_sorted[0]
            diag["first_disposition_divergence"] = {
                "key": str(kd),
                "entry_time": str(ref_by_key[kd]["entry_time"]),
                "obs": disp_o.get(kd), "ref": disp_r4.get(kd)}
        # classify the ledger decision mismatches: cascade vs independent
        t_field = None
        if exit_bad_keys_sorted:
            t_field = str(ref_by_key[exit_bad_keys_sorted[0]]
                          ["exit_time"])
        cascade = indep = 0
        indep_keys = []
        for msg in dec_bad:
            k = eval(msg.split(":")[0])
            et = str(ref_by_key[k]["entry_time"])
            if t_field is not None and et >= t_field:
                cascade += 1
            else:
                indep += 1
                indep_keys.append(msg)
        diag["classification"] = {
            "first_field_divergence_time": t_field,
            "cascade_consistent": cascade, "independent": indep,
            "independent_first": indep_keys[:5],
            "terminal_views_mismatch_are_endstate": term_bad}
        # substitution experiment: observer candidates with ONLY the
        # exit field replaced by the reference value
        hybrid = []
        for t in canonical_o:
            h = dict(t)
            h["exit"] = ref_by_key[keyf(t)]["exit"]
            hybrid.append(h)
        feats_h = feats_o  # rs is exit-independent; same features
        sub_bad = []
        term_h = {}
        disp_h = None
        for view in ("gross", "4bps", "25bps"):
            port = run_sim(hybrid, closes_o, feats_h, view, True, True)
            tk = {keyf(hybrid[i]) for i in port["taken"]}
            term_h[view] = sorted(x["symbol"]
                                  for x in port["terminal_open"])
            if view == "4bps":
                disp_h = {keyf(hybrid[i]): v
                          for i, v in port["disposition"].items()}
            for k, lr in led_by_key.items():
                if (k in tk) != bool(lr[f"taken_{view}"]):
                    sub_bad.append(f"{k}: taken_{view} differs")
        for k, lr in led_by_key.items():
            if disp_h.get(k) != lr["disposition_4bps_c1"]:
                sub_bad.append(f"{k}: disposition_4bps differs")
        port_c0_h = run_sim(hybrid, closes_o, feats_h, "4bps",
                            False, False)
        c0_counts_h = {"taken_count": len(port_c0_h["taken"]),
                       "skipped_cap": port_c0_h["skipped_cap"],
                       "skipped_risk": port_c0_h["skipped_risk"]}
        diag["substitution_exit_only"] = {
            "decision_mismatches": len(sub_bad),
            "terminal_observer": term_h,
            "terminal_mismatch_views":
                [v for v in term_h if term_h[v] != term_ref[v]],
            "c0_counts": c0_counts_h,
            "c0_match": bool(c0_counts_h == c0_ref_counts)}
        note("diagnostics", **{k: (v if not isinstance(v, dict) else
                                   "...") for k, v in diag.items()})
        out["sections"]["diagnostics_detail"] = diag
    return finish()


CUTOFF = None


def finish():
    out["problems"] = problems
    out["verdict"] = "DECISION_PARITY_PASS" if not problems else \
        "STOP_DECISION_PARITY_FAILURE"
    path = os.path.join(WORK, f"compare16_{ARGS.tag}.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(f"VERDICT: {out['verdict']} -> {path}", flush=True)
    if problems:
        print("PROBLEMS:", problems[:10], flush=True)
    return 0 if not problems else 2


if __name__ == "__main__":
    sys.exit(main())
