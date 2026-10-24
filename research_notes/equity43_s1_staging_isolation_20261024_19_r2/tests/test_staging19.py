"""QF-EQUITY43-S1-STAGING-ISOLATION-PREFLIGHT-20261024-19 — battery.

Synthetic/replay-only tests for the staging bundle. Everything runs in
throwaway namespaces under the -19 stage runtime root; production is
touched read-only (identity checks) except in the shadow-root mutation
tests, which use a copied fake production root.

Cases (governing comment 6382675021 §5 + task -19):
  clean boot / repeated boot + replay idempotence / concurrent-lock
  refusal / mid-write crash + clean restart / journal tamper /
  path traversal + symlink + namespace collision / production-pin
  mutation (shadow) / missing pause sentinel (shadow) / calendar SHA
  mismatch / wrong universe / planted vendor adapter + accidental
  network attempt / kill-switch (boot + mid-run) / T0 authority absent,
  malformed and forged / journal pre-populated / unknown calendar
  date fail-closed / signal-only surface (static + execution trace).

Exit 0 iff every test passes.
"""
import json
import math
import os
import shutil
import socket
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
BUNDLE = os.path.join(PKG, "bundle")
STAGE = os.path.abspath(os.path.join(PKG, "..", "..", ".."))
RUNTIME = os.path.join(STAGE, "runtime", "battery")
PROD = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
sys.path.insert(0, BUNDLE)

import staging_gate19 as g  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}", flush=True)


def fresh_ns(name, cls="synthetic_test"):
    root = os.path.join(RUNTIME, name)
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root)
    return root


def gate_for(ns, cls="synthetic_test", bundle=BUNDLE, prod=PROD):
    return g.StagingGate(ns, prod, bundle_root=bundle, namespace_class=cls)


def expect_stop(name, fn, code):
    try:
        fn()
    except g.GateStop as e:
        check(name, e.code == code, f"[{e.code}] {e.detail[:80]}")
        return
    except Exception as e:  # wrong failure mode still fails closed
        check(name, False, f"wrong exception {type(e).__name__}: {e}")
        return
    check(name, False, "no stop raised")


# ------------------------------------------------------- synthetic feed
EXT = json.load(open(os.path.join(
    BUNDLE, "calendar", "session_table_extended_candidate.json")))
SESS = {s["date"]: s for s in EXT["sessions"]}


def starts(date):
    close = int(SESS[date]["close"][:2]) * 60 + int(SESS[date]["close"][3:5])
    out, mins = [], 570
    while mins < close:
        out.append(f"{mins // 60:02d}:{mins % 60:02d}")
        mins += 60
    return out


def synth_rows(symbol, dates, seed=0):
    rows, n, price = [], 0, 100.0 + seed
    for d in dates:
        for s in starts(d):
            n += 1
            drift = 0.35 * math.sin(n / 6.0) + 0.12 * math.sin(n / 2.3)
            o = price
            c = price + drift
            rows.append({"datetime": f"{d} {s}:00", "open": round(o, 4),
                         "high": round(max(o, c) * 1.001, 4),
                         "low": round(min(o, c) * 0.999, 4),
                         "close": round(c, 4), "volume": 10000.0})
            price = c
    return rows


# 140 appended-range sessions -> ~277 4H bars per symbol, past the
# engine WARMUP (215) so the candidate machinery genuinely advances.
DATES = [s["date"] for s in EXT["sessions"]
         if s["date"] >= "2026-10-19"][:140]
SYMS = ["NVDA", "SPY"]
STREAM = {s: synth_rows(s, DATES, seed=i * 7)
          for i, s in enumerate(SYMS)}


def main():
    shutil.rmtree(RUNTIME, ignore_errors=True)
    os.makedirs(RUNTIME)

    # ---- 1. clean boot on the designated staging namespace
    staging_ns = os.path.join(STAGE, "runtime", "staging")
    rep = gate_for(staging_ns, cls="staging").preflight()
    check("clean_boot_prep_ready", rep["verdict"] == "PREP_READY"
          and rep["launch"] == "LAUNCH_HOLD")
    check("clean_boot_hold_reasons",
          rep["launch_hold_reasons"] == ["G4_VBASIS_UNADOPTED",
                                         "FEED_RIGHTS_UNQUALIFIED",
                                         "T0_AUTHORITY_ABSENT"],
          str(rep["launch_hold_reasons"]))
    check("clean_boot_pins", rep["pins_checked"]["source_pins"] == 14
          and rep["pins_checked"]["extended_table_sha256"].startswith(
              "86a1d4ea"))
    # processing is unreachable in a staging namespace
    expect_stop("staging_processing_unreachable",
                lambda: gate_for(staging_ns, cls="staging")
                .build_observer(SYMS), "STOP_LAUNCH_HOLD")

    # ---- 2. repeated boot / idempotence
    rep2 = gate_for(staging_ns, cls="staging").preflight()
    check("repeated_boot_identical",
          rep2["verdict"] == rep["verdict"]
          and rep2["pins_checked"] == rep["pins_checked"])
    ns_a, ns_b = fresh_ns("idem_a"), fresh_ns("idem_b")
    sig_a, _o, j_a = g.replay_synthetic(gate_for(ns_a), SYMS, STREAM)
    sig_b, _o, j_b = g.replay_synthetic(gate_for(ns_b), SYMS, STREAM)
    ja = open(os.path.join(ns_a, "journal",
                           "observer_journal.jsonl"), "rb").read()
    jb = open(os.path.join(ns_b, "journal",
                           "observer_journal.jsonl"), "rb").read()
    check("replay_idempotent_journal_bytes", ja == jb,
          f"{len(ja)} bytes, {len(j_a.records)} records")
    check("replay_idempotent_signals", sig_a == sig_b,
          f"{len(sig_a)} signal records")
    check("signal_record_keys_exact",
          all(set(r) == g.SIGNAL_KEYS for r in sig_a)
          and not any(set(r) & g.FORBIDDEN_OUTPUT_KEYS for r in sig_a))
    import fwd_observer17 as fo
    ok, info = fo.Journal.verify(
        os.path.join(ns_a, "journal", "observer_journal.jsonl"),
        os.path.join(ns_a, "anchors", "journal_anchor.json"))
    check("journal_chain_verifies", ok and info["records"] > 0, str(info))

    # ---- 3. concurrent-lock refusal
    ns_l = fresh_ns("lock")
    g1 = gate_for(ns_l)
    g1.acquire_lock()
    expect_stop("concurrent_lock_refusal",
                lambda: gate_for(ns_l).preflight(), "STOP_LOCK_HELD")
    g1.release_lock()
    check("lock_released_reboot_ok",
          gate_for(ns_l).preflight()["verdict"] == "PREP_READY")

    # ---- 4. clean restart: snapshot/resume continues byte-identically
    ns_r = fresh_ns("restart")
    fo_r, obs_r, j_r = gate_for(ns_r).build_observer(SYMS)
    half = len(STREAM["NVDA"]) // 2
    for row in STREAM["NVDA"][:half]:
        obs_r.ingest("NVDA", row)
    j_r.anchor("mid-run")
    snap = os.path.join(ns_r, "state", "snapshot.json")
    obs_r.snapshot(snap)
    j_r.close()
    j_r2 = fo.Journal.resume(
        os.path.join(ns_r, "journal", "observer_journal.jsonl"),
        os.path.join(ns_r, "anchors", "journal_anchor.json"))
    table = fo.SessionTable(EXT)
    import pine_backtest as pb
    obs_r2 = fo.ForwardObserver.restore(
        snap, table, j_r2, pb, SYMS,
        sentinel_path=os.path.join(PROD, "forward_test",
                                   "PAUSE_NEW_ENTRIES"), armed=False)
    for row in STREAM["NVDA"][half:]:
        obs_r2.ingest("NVDA", row)
    obs_r2.flush()
    for row in STREAM["SPY"]:
        obs_r2.ingest("SPY", row)
    obs_r2.flush()
    j_r2.anchor("restarted complete")
    j_r2.close()
    jr = open(os.path.join(ns_r, "journal",
                           "observer_journal.jsonl"), "rb").read()
    check("restart_journal_byte_identical", jr == ja,
          f"{len(jr)} vs {len(ja)} bytes")

    # ---- 5. mid-write crash: truncated tail fails closed
    crash_j = os.path.join(RUNTIME, "crash_journal.jsonl")
    crash_a = os.path.join(RUNTIME, "crash_anchor.json")
    shutil.copy(os.path.join(ns_a, "journal", "observer_journal.jsonl"),
                crash_j)
    shutil.copy(os.path.join(ns_a, "anchors", "journal_anchor.json"),
                crash_a)
    with open(crash_j, "a") as f:
        f.write('{"seq": 9999, "type": "INP')
    try:
        ok_c, _i = fo.Journal.verify(crash_j, crash_a)
        crashed_closed = not ok_c
    except Exception:
        crashed_closed = True
    check("crash_truncated_tail_fails_closed", crashed_closed)
    try:
        fo.Journal.resume(crash_j, crash_a)
        resume_refused = False
    except Exception:
        resume_refused = True
    check("crash_resume_refused", resume_refused)

    # ---- 6. journal tamper: one flipped payload char breaks the chain
    lines = ja.decode().splitlines()
    rec = json.loads(lines[10])
    rec["payload"] = {"tampered": True}
    lines[10] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    tamp_j = os.path.join(RUNTIME, "tampered_journal.jsonl")
    with open(tamp_j, "w") as f:
        f.write("\n".join(lines) + "\n")
    ok_t, info_t = fo.Journal.verify(tamp_j, os.path.join(
        ns_a, "anchors", "journal_anchor.json"))
    check("journal_tamper_detected", not ok_t, str(info_t)[:70])

    # ---- 7. traversal / symlink / collision
    evil = os.path.join(RUNTIME, "..", "..", "..",
                        "quality-flow-scanner-v5", "forward_test")
    expect_stop("traversal_into_production",
                lambda: gate_for(evil).preflight(),
                "STOP_NAMESPACE_OVERLAP")
    ns_s = fresh_ns("symlink")
    outside = os.path.join(RUNTIME, "outside")
    os.makedirs(outside, exist_ok=True)
    os.symlink(outside, os.path.join(ns_s, "journal"))
    expect_stop("symlink_escape_refused",
                lambda: gate_for(ns_s).preflight(),
                "STOP_NAMESPACE_ESCAPE")
    expect_stop("namespace_inside_production",
                lambda: gate_for(os.path.join(
                    PROD, "v54_forward", "staging_x")).preflight(),
                "STOP_NAMESPACE_OVERLAP")

    # ---- 8/9. shadow production: pin mutation + missing sentinel
    shadow = os.path.join(RUNTIME, "shadow_prod")
    os.makedirs(os.path.join(shadow, "forward_test"))
    shutil.copy(os.path.join(PROD, "v54_forward_harness.py"),
                os.path.join(shadow, "v54_forward_harness.py"))
    open(os.path.join(shadow, "forward_test", "PAUSE_NEW_ENTRIES"),
         "w").close()
    ns_sh = fresh_ns("shadow_ok")
    check("shadow_prod_paused_ok",
          gate_for(ns_sh).check_paused(shadow)["harness_sha256"]
          .startswith("ce7c902c"))
    with open(os.path.join(shadow, "v54_forward_harness.py"), "a") as f:
        f.write("# drift\n")
    expect_stop("production_pin_mutation_stops",
                lambda: gate_for(ns_sh).check_paused(shadow),
                "STOP_PAUSED_PIN_DRIFT")
    shutil.copy(os.path.join(PROD, "v54_forward_harness.py"),
                os.path.join(shadow, "v54_forward_harness.py"))
    os.remove(os.path.join(shadow, "forward_test", "PAUSE_NEW_ENTRIES"))
    expect_stop("missing_pause_sentinel_stops",
                lambda: gate_for(ns_sh).check_paused(shadow),
                "STOP_PAUSED_PIN_DRIFT")

    # ---- 10. calendar SHA mismatch (drifted bundle copy)
    tmp_bundle = os.path.join(RUNTIME, "bundle_drift")
    shutil.copytree(BUNDLE, tmp_bundle)
    cal_p = os.path.join(tmp_bundle, "calendar",
                         "session_table_extended_candidate.json")
    data = bytearray(open(cal_p, "rb").read())
    data[-20] ^= 0x01
    open(cal_p, "wb").write(bytes(data))
    expect_stop("calendar_sha_mismatch_stops",
                lambda: gate_for(fresh_ns("drift"), bundle=tmp_bundle)
                .check_pins(), "STOP_PIN_DRIFT")

    # ---- 11. wrong universe (drifted bundle copy)
    tmp_b2 = os.path.join(RUNTIME, "bundle_uni")
    shutil.copytree(BUNDLE, tmp_b2)
    uni_p = os.path.join(tmp_b2, "config", "universe43.json")
    uni = json.load(open(uni_p))
    uni["symbols"] = uni["symbols"] + ["SMCI"]
    json.dump(uni, open(uni_p, "w"))
    expect_stop("wrong_universe_stops",
                lambda: gate_for(fresh_ns("uni"), bundle=tmp_b2)
                .check_universe_and_sector(), "STOP_UNIVERSE")

    # ---- 12. planted vendor adapter -> audit STOP; network trace = 0
    tmp_b3 = os.path.join(RUNTIME, "bundle_vendor")
    shutil.copytree(BUNDLE, tmp_b3)
    with open(os.path.join(tmp_b3, "engine", "vendor_adapter.py"),
              "w") as f:
        f.write("import requests\n\ndef fetch():\n    return requests.get"
                "('https://example.invalid')\n")
    audit_v = g.static_audit(tmp_b3)
    check("planted_vendor_adapter_flagged", len(audit_v["violations"]) >= 1,
          str(audit_v["violations"])[:90])
    expect_stop("planted_vendor_adapter_stops_preflight",
                lambda: gate_for(fresh_ns("vendor"), bundle=tmp_b3)
                .preflight(), "STOP_AUDIT_SURFACE")
    attempts = {"n": 0}
    real_socket = socket.socket

    class CountingSocket:
        def __init__(self, *a, **k):
            attempts["n"] += 1
            raise RuntimeError("network attempt in synthetic replay")

    socket.socket = CountingSocket
    try:
        ns_n = fresh_ns("nonet")
        g.replay_synthetic(gate_for(ns_n), SYMS, STREAM)
        net_ok = attempts["n"] == 0
    finally:
        socket.socket = real_socket
    check("accidental_network_attempt_none", net_ok,
          f"attempts={attempts['n']}")

    # ---- 13. kill switch: at boot and mid-run
    ns_k = fresh_ns("kill_boot")
    open(os.path.join(ns_k, "KILL"), "w").close()
    expect_stop("kill_switch_boot", lambda: gate_for(ns_k).preflight(),
                "STOP_KILLED")
    ns_m = fresh_ns("kill_mid")
    _fo, obs_m, j_m = gate_for(ns_m).build_observer(SYMS)
    for row in STREAM["NVDA"][:60]:
        obs_m.ingest("NVDA", row)
    j_m.anchor("pre-kill")
    open(os.path.join(ns_m, "KILL"), "w").close()
    expect_stop("kill_switch_midrun",
                lambda: gate_for(ns_m).check_kill(), "STOP_KILLED")
    j_m.close()
    ok_k, info_k = fo.Journal.verify(
        os.path.join(ns_m, "journal", "observer_journal.jsonl"),
        os.path.join(ns_m, "anchors", "journal_anchor.json"))
    check("kill_midrun_journal_still_verifies", ok_k, str(info_k))

    # ---- 14. T0 authority: malformed + forged cannot unlock
    ns_t = fresh_ns("auth", cls="staging")
    os.makedirs(os.path.join(ns_t, "config"))
    with open(os.path.join(ns_t, "config", "LAUNCH_AUTHORITY.json"),
              "w") as f:
        f.write("{not json")
    rep_t = gate_for(ns_t, cls="staging").preflight()
    check("t0_malformed_holds",
          "T0_AUTHORITY_MALFORMED" in rep_t["launch_hold_reasons"]
          and rep_t["launch"] == "LAUNCH_HOLD")
    with open(os.path.join(ns_t, "config", "LAUNCH_AUTHORITY.json"),
              "w") as f:
        json.dump({"t0": "2026-11-02", "mike_go_ref": "forged",
                   "feed_qualification": "claimed",
                   "g4_adoption": "claimed"}, f)
    rep_f = gate_for(ns_t, cls="staging").preflight()
    check("t0_forged_still_holds",
          rep_f["launch"] == "LAUNCH_HOLD"
          and "G4_VBASIS_UNADOPTED" in rep_f["launch_hold_reasons"]
          and "FEED_RIGHTS_UNQUALIFIED" in rep_f["launch_hold_reasons"],
          str(rep_f["launch_hold_reasons"]))
    expect_stop("t0_forged_processing_unreachable",
                lambda: gate_for(ns_t, cls="staging").build_observer(SYMS),
                "STOP_LAUNCH_HOLD")

    # ---- 15. pre-populated journal refused
    ns_p = fresh_ns("prepop")
    os.makedirs(os.path.join(ns_p, "journal"))
    with open(os.path.join(ns_p, "journal", "observer_journal.jsonl"),
              "w") as f:
        f.write("{}\n")
    expect_stop("journal_prepopulated_refused",
                lambda: gate_for(ns_p).preflight(),
                "STOP_JOURNAL_PREPOPULATED")

    # ---- 16. unknown calendar dates fail closed at the feed
    ns_u = fresh_ns("unknown_date")
    _fo, obs_u, j_u = gate_for(ns_u).build_observer(SYMS)
    ev = obs_u.ingest("NVDA", {"datetime": "2026-10-18 09:30:00",
                               "open": 1, "high": 1, "low": 1, "close": 1,
                               "volume": 1})
    ev2 = obs_u.ingest("NVDA", {"datetime": "2028-06-01 09:30:00",
                                "open": 1, "high": 1, "low": 1, "close": 1,
                                "volume": 1})
    cls = {e.get("class") for e in ev + ev2 if e["type"] == "REJECTED"}
    j_u.close()
    check("unknown_session_dates_rejected", cls == {"UNKNOWN_SESSION"},
          str(cls))
    table_u = fo.SessionTable(EXT)
    check("unknown_date_not_session",
          not table_u.is_session("2028-06-01")
          and not table_u.is_session("2026-10-18"))

    # ---- 17. signal-only execution trace
    executed = set()

    def tracer(frame, event, arg):
        if event == "call":
            executed.add(frame.f_code.co_name)
        return tracer

    ns_x = fresh_ns("trace")
    sys.settrace(tracer)
    try:
        g.replay_synthetic(gate_for(ns_x), SYMS, STREAM)
    finally:
        sys.settrace(None)
    check("trace_no_simulator_execution",
          not (executed & g.SIMULATOR_FUNCS),
          f"simulators hit: {executed & g.SIMULATOR_FUNCS}")
    check("trace_signal_primitives_ran",
          {"add_pine_indicators", "pine_buy_signal"} <= executed)
    import staging_gate19 as _g2
    obs_attrs = [a for a in dir(fo.ForwardObserver)
                 if any(t in a.lower() for t in
                        ("order", "broker", "submit", "fill", "buy_",
                         "sell_", "trade_exec"))]
    check("observer_has_no_order_surface", obs_attrs == [], str(obs_attrs))

    n_pass = sum(1 for _n, ok in RESULTS if ok)
    print(f"SUMMARY {n_pass}/{len(RESULTS)} PASS")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
