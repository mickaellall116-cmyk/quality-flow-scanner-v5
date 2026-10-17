#!/usr/bin/env python3
"""QF-TD-LIVE-READINESS-EXECUTOR-FINALIZE-20261017-14 r1 trial runner.

Proves the integrated live-capable readiness executor OFFLINE:
lock-first ordering (no ledger read before lease+lock; locked bytes
are the only bytes journaled/backed-up/rolled back), the concurrent
cases with real processes, the accepted -13 exception/crash/tamper
cases re-run against the integrated executor, the live-mode clearance
gate, and the scope refusals. Usage:

  python3 run_executor_trials.py <trials_root> <matrix_out.json>
"""
import datetime
import fcntl
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
NOTES = os.path.dirname(HERE)
REPO = os.path.dirname(NOTES)
import live_readiness_executor as EX  # noqa: E402
from r4_dry_run_adapter import make_r4_dry_run_hook  # noqa: E402

H = EX.H
canon = EX.canon
NOW = 1792224000  # 2026-10-17T14:00:00Z; aligns with the accepted -11
# fixture clock shared by the r4 gate runner and the -11 txn runner.


def fmt(ts):
    return datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


LEGACY = open(os.path.join(REPO, "research_notes", "pilot_harness",
                           "credit_ledger.json"), "rb").read()
LEGACY_SHA = H(LEGACY)
assert LEGACY_SHA.startswith("7e5ccef0"), LEGACY_SHA
CAND_PATH = os.path.join(
    NOTES, "td_ledger_compat_card_binding_20261017_07",
    "candidate_credit_ledger.json")
CAND = open(CAND_PATH, "rb").read()
CAND_SHA = H(CAND)
assert CAND_SHA.startswith("79ff4844"), CAND_SHA
STUB = os.path.join(NOTES, "td_policy_a_live_readiness_packet_20261017_11",
                    "helper_stub", "dynamic_credentials.py")
STUB_SHA = EX._sha256_file(STUB)
assert STUB_SHA.startswith("8f80417d"), STUB_SHA
MUTATED = canon({"day": "2026-10-14", "spent": 9,
                 "window": [[1760000000, 1]]})
SCHEMA_BAD = canon({"reservations": []})

PASS_RAW = {"timestamp": fmt(NOW - 60), "current_usage": 0, "plan_limit": 8,
            "daily_usage": 100, "plan_daily_limit": 800,
            "plan_category": "basic"}
EDGE_RAW = dict(PASS_RAW, daily_usage=748)
FAIL_RAW = dict(PASS_RAW, daily_usage=760)


class Spy:
    def __init__(self, raw=None, exc=None):
        self.calls = []
        self.raw = PASS_RAW if raw is None else raw
        self.exc = exc

    def http_get(self, url):
        from urllib.parse import urlparse
        u = urlparse(url)
        self.calls.append({"host": u.hostname, "path": u.path,
                           "has_query": bool(u.query)})
        if self.exc is not None:
            raise self.exc
        return 200, canon(self.raw)


RESULTS = []


def record(name, checks):
    RESULTS.append({"trial": name, "checks": checks,
                    "ok": all(checks.values())})
    print(("PASS " if all(checks.values()) else "FAIL ") + name, flush=True)


def base_packet(root, txn, **over):
    pk = {
        "mode": "offline",
        "txn_id": txn,
        "workdir": os.path.join(root, "txn"),
        "target_path": os.path.join(root, "ledger.json"),
        "candidate_path": CAND_PATH,
        "expected_original_sha": LEGACY_SHA,
        "expected_candidate_sha": CAND_SHA,
        "go_record": {"record_id": EX.GO_RECORD_ID,
                      "comment_id": EX.GO_COMMENT_ID},
        "helper": {"path": STUB, "sha256": STUB_SHA},
        "dryrun_root": os.path.join(root, "dryrun"),
    }
    pk.update(over)
    return pk


def base_hooks(spy=None, **over):
    hk = {"fixture": True, "clock": lambda: NOW,
          "transport": spy if spy is not None else Spy(),
          "dry_run": lambda ev: ["PASS"] * 12}
    hk.update(over)
    return hk


def setup(root, target_bytes=LEGACY):
    os.makedirs(root, exist_ok=True)
    with open(os.path.join(root, "ledger.json"), "wb") as f:
        f.write(target_bytes)
    return os.path.join(root, "ledger.json")


def read(path):
    with open(path, "rb") as f:
        return f.read()


def run_child(cfg, root, name):
    cfgp = os.path.join(root, name + "_cfg.json")
    with open(cfgp, "w") as f:
        f.write(json.dumps(cfg))
    return subprocess.Popen(
        [sys.executable, os.path.join(HERE, "child_executor.py"), cfgp],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def child_cfg(root, txn, workdir, spy_kind="pass", **kw):
    cfg = {"packet": base_packet(root, txn, workdir=workdir),
           "spy_kind": spy_kind,
           "counter_file": os.path.join(root, "counter_%s.txt" % txn),
           "result_file": os.path.join(root, "result_%s.json" % txn)}
    cfg.update(kw)
    return cfg


def wait_result(path, timeout=60):
    for _ in range(int(timeout * 10)):
        if os.path.exists(path):
            return json.loads(read(path).decode())
        time.sleep(0.1)
    raise RuntimeError("timeout waiting for " + path)


def counter_total(root):
    total = 0
    for n in os.listdir(root):
        if n.startswith("counter_"):
            total += len(read(os.path.join(root, n)).decode().split())
    return total


def main():
    troot, matrix_out = sys.argv[1], sys.argv[2]
    os.makedirs(troot, exist_ok=True)

    # e01 happy path, REAL r4 gate as the dry-run hook ----------------
    root = os.path.join(troot, "e01"); target = setup(root)
    pk = base_packet(root, "QF14-E01")
    spy = Spy()
    hk = base_hooks(spy, dry_run=make_r4_dry_run_hook(pk, target,
                                                      account_raw=PASS_RAW))
    out = EX.LiveReadinessExecutor(pk, hk).run()
    rec = EX.recover_live(pk["workdir"], target)
    record("e01_happy_real_r4_dry_run", {
        "complete": out.get("outcome") == "COMPLETE",
        "target_is_candidate": read(target) == CAND,
        "backup_is_locked_legacy": read(pk["workdir"] + "/ledger_backup.bin") == LEGACY,
        "one_status_call": len(spy.calls) == 1,
        "status_host_path": spy.calls[0]["host"] == "api.twelvedata.com"
        and spy.calls[0]["path"] == "/api_usage",
        "recovery_adopted_verified": rec["classification"] == "ADOPTED_VERIFIED",
        "recovery_zero_status_calls": rec["status_calls_during_recovery"] == 0,
    })

    # e02 ledger mutated by another process BEFORE lock acquisition --
    root = os.path.join(troot, "e02"); target = setup(root)
    go = os.path.join(root, "go")
    cfg = child_cfg(root, "QF14-E02", os.path.join(root, "txn"),
                    go_file=go)
    p = run_child(cfg, root, "e02")
    time.sleep(0.5)
    with open(target, "wb") as f:
        f.write(MUTATED)
    open(go, "w").write("go")
    p.communicate(timeout=60)
    res = wait_result(cfg["result_file"])
    record("e02_prelock_mutation_binds_locked_bytes_or_holds", {
        "hold_pin_mismatch": res.get("outcome") == "HOLD"
        and res.get("reason") == "LOCKED_LEDGER_PIN_MISMATCH",
        "mutated_bytes_never_overwritten": read(target) == MUTATED,
        "zero_status_calls": counter_total(root) == 0,
    })

    # e03 mutation attempt while locks held blocks ---------------------
    root = os.path.join(troot, "e03"); target = setup(root)
    sig, rel = os.path.join(root, "sig"), os.path.join(root, "rel")
    cfg = child_cfg(root, "QF14-E03", os.path.join(root, "txn"),
                    pause_locks={"signal": sig, "release": rel})
    p = run_child(cfg, root, "e03")
    for _ in range(300):
        if os.path.exists(sig):
            break
        time.sleep(0.1)
    nb_blocked = False
    try:
        fd = open(target + ".lock", "a+")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fd.close()
    except BlockingIOError:
        nb_blocked = True
    waiter_flag = os.path.join(root, "waiter_got")
    waiter = subprocess.Popen(
        [sys.executable, "-c",
         "import fcntl,sys\n"
         "fd=open(sys.argv[1],'a+')\n"
         "fcntl.flock(fd, fcntl.LOCK_EX)\n"
         "open(sys.argv[2],'w').write('got')\n",
         target + ".lock", waiter_flag])
    time.sleep(0.8)
    blocked_while_held = not os.path.exists(waiter_flag)
    open(rel, "w").write("release")
    p.communicate(timeout=60)
    waiter.wait(timeout=30)
    res = wait_result(cfg["result_file"])
    record("e03_mutation_attempt_blocks_while_lock_held", {
        "nb_attempt_blocked": nb_blocked,
        "blocking_attempt_waits": blocked_while_held,
        "waiter_acquires_only_after_release": os.path.exists(waiter_flag),
        "executor_completed": res.get("outcome") == "COMPLETE",
        "no_overwrite_target_is_candidate": read(target) == CAND,
    })

    # e04 two executors, same transaction/workdir -----------------------
    root = os.path.join(troot, "e04"); target = setup(root)
    go = os.path.join(root, "go")
    wd = os.path.join(root, "txn")
    ca = child_cfg(root, "QF14-E04", wd, go_file=go)
    cb = child_cfg(root, "QF14-E04", wd, go_file=go)
    cb["counter_file"] = ca["counter_file"]
    cb["result_file"] = os.path.join(root, "result_b.json")
    ca["result_file"] = os.path.join(root, "result_a.json")
    pa, pb = run_child(ca, root, "e04a"), run_child(cb, root, "e04b")
    time.sleep(0.5)
    open(go, "w").write("go")
    pa.communicate(timeout=60); pb.communicate(timeout=60)
    ra = wait_result(ca["result_file"]); rb = wait_result(cb["result_file"])
    kinds = sorted([ra.get("outcome"), rb.get("outcome")])
    loser = ra if ra.get("outcome") != "COMPLETE" else rb
    record("e04_two_executors_same_workdir", {
        "exactly_one_completes": kinds == ["COMPLETE", "REFUSED"],
        "loser_marker_exclusive_create": loser.get("reason")
        == "TXN_ALREADY_CONSUMED",
        "at_most_one_status_call": counter_total(root) == 1,
        "target_is_candidate": read(target) == CAND,
    })

    # e05 two executors, different workdirs, same target -----------------
    # Both pause after acquiring locks; only one can hold them, so the
    # loser is guaranteed to contend while the winner is paused.
    root = os.path.join(troot, "e05"); target = setup(root)
    go = os.path.join(root, "go")
    sig, rel = os.path.join(root, "sig5"), os.path.join(root, "rel5")
    pause = {"signal": sig, "release": rel}
    ca = child_cfg(root, "QF14-E05A", os.path.join(root, "txnA"),
                   go_file=go, pause_locks=pause)
    cb = child_cfg(root, "QF14-E05B", os.path.join(root, "txnB"),
                   go_file=go, pause_locks=pause)
    pa, pb = run_child(ca, root, "e05a"), run_child(cb, root, "e05b")
    time.sleep(0.5)
    open(go, "w").write("go")
    loser_res = None
    for _ in range(300):
        for cf in (ca, cb):
            if os.path.exists(cf["result_file"]):
                loser_res = json.loads(read(cf["result_file"]).decode())
        if loser_res is not None and os.path.exists(sig):
            break
        time.sleep(0.1)
    open(rel, "w").write("release")
    pa.communicate(timeout=60); pb.communicate(timeout=60)
    ra = wait_result(ca["result_file"]); rb = wait_result(cb["result_file"])
    kinds = sorted([ra.get("outcome"), rb.get("outcome")])
    loser = ra if ra.get("outcome") != "COMPLETE" else rb
    record("e05_two_executors_diff_workdirs_same_target", {
        "exactly_one_completes": kinds == ["COMPLETE", "HOLD"],
        "loser_lock_contention": loser.get("reason", "").startswith(
            "LOCK_CONTENTION"),
        "at_most_one_status_call": counter_total(root) == 1,
        "target_is_candidate": read(target) == CAND,
    })

    # e06 recovery TOCTOU: journal / ledger drift precheck->lock ---------
    for swap, want_reason in (("journal", "RECOVERY_JOURNAL_DRIFT_UNDER_LOCK"),
                              ("ledger", "TARGET_UNKNOWN_BYTES")):
        # For the ledger swap the hook itself drifted the bytes; the
        # recovery must leave exactly those drifted bytes in place.
        want_bytes = CAND if swap == "journal" else \
            b"drifted-bytes-not-original-not-candidate"
        root = os.path.join(troot, "e06_" + swap); target = setup(root)
        cfg = child_cfg(root, "QF14-E06" + swap, os.path.join(root, "txn"),
                        crash_at="after_replace")
        p = run_child(cfg, root, "e06")
        p.communicate(timeout=60)
        crashed_ok = p.returncode == 42 and read(target) == CAND
        rcfg = {"workdir": cfg["packet"]["workdir"], "target": target,
                "swap": swap,
                "result_file": os.path.join(root, "recover.json")}
        rcfgp = os.path.join(root, "rcfg.json")
        open(rcfgp, "w").write(json.dumps(rcfg))
        subprocess.run([sys.executable,
                        os.path.join(HERE, "child_recover.py"), rcfgp],
                       check=True, timeout=60)
        rec = wait_result(rcfg["result_file"])
        record("e06_recovery_toctou_" + swap, {
            "crash_state_post_replace": crashed_ok,
            "hold_manual": rec["classification"] == "HOLD_MANUAL",
            "reason": rec.get("reason") == want_reason,
            "ledger_untouched": read(target) == want_bytes,
            "zero_status_calls": rec["status_calls_during_recovery"] == 0,
        })

    # e07 gate-3 FAIL: no adoption, status consumed once ------------------
    root = os.path.join(troot, "e07"); target = setup(root)
    pk = base_packet(root, "QF14-E07"); spy = Spy(raw=FAIL_RAW)
    out = EX.LiveReadinessExecutor(pk, base_hooks(spy)).run()
    record("e07_gate3_fail_no_adoption", {
        "hold": out.get("outcome") == "HOLD",
        "target_untouched": read(target) == LEGACY,
        "status_consumed_once": len(spy.calls) == 1,
        "journal_terminal_hold": json.loads(read(
            pk["workdir"] + "/journal.json").decode())["phase"]
        == "TERMINAL_HOLD_PRE",
    })

    # e08 gate-3 boundary: remaining exactly 52 ----------------------------
    root = os.path.join(troot, "e08"); target = setup(root)
    pk = base_packet(root, "QF14-E08"); spy = Spy(raw=EDGE_RAW)
    out = EX.LiveReadinessExecutor(pk, base_hooks(spy)).run()
    record("e08_gate3_boundary_52_passes", {
        "complete": out.get("outcome") == "COMPLETE",
        "target_is_candidate": read(target) == CAND,
    })

    # e09 transport raises: HOLD, no retry ----------------------------------
    root = os.path.join(troot, "e09"); target = setup(root)
    pk = base_packet(root, "QF14-E09")
    spy = Spy(exc=ConnectionError("down"))
    out = EX.LiveReadinessExecutor(pk, base_hooks(spy)).run()
    record("e09_transport_exception_no_retry", {
        "hold": out.get("outcome") == "HOLD",
        "exactly_one_invocation": len(spy.calls) == 1,
        "journal_status_consumed": json.loads(read(
            pk["workdir"] + "/journal.json").decode())["status_calls"] == 1,
        "target_untouched": read(target) == LEGACY,
    })

    # e10 status slot: second call structurally refused ----------------------
    handle = EX.RESOLVER.resolve(STUB, STUB_SHA)
    spy = Spy()
    b = EX.StatusBoundary(handle, spy.http_get)
    b.call()
    second = None
    try:
        b.call()
    except EX.Refusal as e:
        second = e.code
    record("e10_status_slot_one_use", {
        "first_call_ok": len(spy.calls) == 1,
        "second_refused": second == "STATUS_SLOT_ALREADY_CONSUMED",
        "no_second_invocation": len(spy.calls) == 1,
    })

    # e11 accepted exception cases against the integrated executor -----------
    root = os.path.join(troot, "e11a"); target = setup(root)
    pk = base_packet(root, "QF14-E11A")
    out = EX.LiveReadinessExecutor(pk, base_hooks(
        raise_at={"evidence:fsync": OSError("disk")})).run()
    record("e11a_evidence_fsync_fault_rolls_back", {
        "rolled_back": out.get("outcome") == "ROLLED_BACK",
        "exact_legacy_restored": read(target) == LEGACY,
    })
    root = os.path.join(troot, "e11b"); target = setup(root)
    pk = base_packet(root, "QF14-E11B")

    def boom(_ev):
        raise RuntimeError("dry-run boom")
    out = EX.LiveReadinessExecutor(pk, base_hooks(dry_run=boom)).run()
    record("e11b_dry_run_runtime_error_rolls_back", {
        "rolled_back": out.get("outcome") == "ROLLED_BACK",
        "exact_legacy_restored": read(target) == LEGACY,
    })
    root = os.path.join(troot, "e11c"); target = setup(root)
    pk = base_packet(root, "QF14-E11C")
    out = EX.LiveReadinessExecutor(pk, base_hooks(
        dry_run=boom,
        raise_at={"rollback:fsync": OSError("disk")})).run()
    record("e11c_rollback_failure_is_hold_manual", {
        "hold_manual": out.get("outcome") == "HOLD_MANUAL",
        "never_claims_rolled_back": out.get("reason")
        == "ROLLBACK_UNVERIFIED",
        "candidate_left_in_place": read(target) == CAND,
    })

    # e12/e13 crash + cold recovery in a fresh process -----------------------
    for name, crash_at in (("e12", "after_replace"),
                           ("e13", "during_terminal")):
        root = os.path.join(troot, name); target = setup(root)
        cfg = child_cfg(root, "QF14-" + name.upper(),
                        os.path.join(root, "txn"), crash_at=crash_at)
        p = run_child(cfg, root, name)
        p.communicate(timeout=60)
        rcfg = {"workdir": cfg["packet"]["workdir"], "target": target,
                "swap": "none",
                "result_file": os.path.join(root, "recover.json")}
        rcfgp = os.path.join(root, "rcfg.json")
        open(rcfgp, "w").write(json.dumps(rcfg))
        subprocess.run([sys.executable,
                        os.path.join(HERE, "child_recover.py"), rcfgp],
                       check=True, timeout=60)
        rec = wait_result(rcfg["result_file"])
        record(name + "_crash_" + crash_at + "_cold_recovery", {
            "crash_exit_42": p.returncode == 42,
            "post_replace_unverified": rec["classification"]
            == "POST_REPLACE_UNVERIFIED",
            "exact_legacy_restored": read(target) == LEGACY,
            "zero_status_calls_in_recovery":
            rec["status_calls_during_recovery"] == 0,
        })

    # e14 tamper: forged 11/12 receipt on a COMPLETE journal ------------------
    root = os.path.join(troot, "e14"); target = setup(root)
    pk = base_packet(root, "QF14-E14")
    out = EX.LiveReadinessExecutor(pk, base_hooks()).run()
    rp = os.path.join(pk["workdir"], "dry_run_receipt.json")
    r = json.loads(read(rp).decode())
    r["gates"] = ["PASS"] * 11 + ["FAIL"]; r["gates_passed"] = 11
    open(rp, "wb").write(canon(r))
    rec = EX.recover_live(pk["workdir"], target)
    record("e14_forged_receipt_hold_manual", {
        "had_completed": out.get("outcome") == "COMPLETE",
        "hold_manual": rec["classification"] == "HOLD_MANUAL",
        "ledger_untouched": read(target) == CAND,
    })

    # e15 tamper: relocated journal / edited target binding --------------------
    root = os.path.join(troot, "e15"); target = setup(root)
    cfg = child_cfg(root, "QF14-E15", os.path.join(root, "txn"),
                    crash_at="after_replace")
    p = run_child(cfg, root, "e15"); p.communicate(timeout=60)
    import shutil
    wd2 = os.path.join(root, "relocated")
    shutil.copytree(cfg["packet"]["workdir"], wd2)
    rec = EX.recover_live(wd2, target)
    jp = os.path.join(cfg["packet"]["workdir"], "journal.json")
    st = json.loads(read(jp).decode())
    st["target_path"] = os.path.join(root, "decoy.json")
    open(jp, "wb").write(canon(st))
    rec2 = EX.recover_live(cfg["packet"]["workdir"], target)
    record("e15_journal_relocation_and_target_edit", {
        "relocated_hold_manual": rec["classification"] == "HOLD_MANUAL",
        "edited_target_hold_manual": rec2["classification"]
        == "HOLD_MANUAL",
        "ledger_untouched": read(target) == CAND,
    })

    # e16 live-mode clearance gate ----------------------------------------------
    root = os.path.join(troot, "e16"); target = setup(root)
    pk = base_packet(root, "QF14-E16", mode="live")
    codes = {}
    try:
        EX.LiveReadinessExecutor(pk, {"fixture": True})
    except EX.Refusal as e:
        codes["hooks"] = e.code
    ex = EX.LiveReadinessExecutor(pk, None)
    try:
        ex.run()
    except EX.Refusal as e:
        codes["missing"] = e.code
    no_marker = not os.path.exists(pk["workdir"])
    clr = os.path.join(root, "clearance.json")
    open(clr, "wb").write(canon({"txn_id": "QF14-E16"}))
    pk2 = base_packet(root, "QF14-E16", mode="live", clearance_path=clr,
                      clearance_sha256="0" * 64)
    try:
        EX.LiveReadinessExecutor(pk2, None).run()
    except EX.Refusal as e:
        codes["pin"] = e.code
    record("e16_live_clearance_gate", {
        "live_hooks_refused": codes.get("hooks") == "LIVE_HOOKS_REFUSED",
        "clearance_missing": codes.get("missing") == "CLEARANCE_MISSING",
        "no_marker_or_workdir_created": no_marker,
        "clearance_pin_mismatch": codes.get("pin")
        == "CLEARANCE_PIN_MISMATCH",
        "ledger_untouched": read(target) == LEGACY,
    })

    # e17 scope refusals -----------------------------------------------------------
    root = os.path.join(troot, "e17"); setup(root)
    ex = EX.LiveReadinessExecutor(base_packet(root, "QF14-E17"),
                                  base_hooks())
    codes = []
    for fn in (ex.request_token, ex.arm_transport, ex.call_time_series):
        try:
            fn()
        except EX.Refusal as e:
            codes.append(e.code)
    record("e17_scope_refusals", {
        "all_not_in_readiness_scope": codes == ["NOT_IN_READINESS_SCOPE"] * 3,
    })

    # e18 pre-existing marker refuses before locks -----------------------------------
    root = os.path.join(troot, "e18"); target = setup(root)
    pk = base_packet(root, "QF14-E18")
    os.makedirs(pk["workdir"], exist_ok=True)
    open(pk["marker_path"] if "marker_path" in pk else
         os.path.join(pk["workdir"], "CONSUMED.marker"), "wb").write(b"{}")
    code = None
    try:
        EX.LiveReadinessExecutor(pk, base_hooks()).run()
    except EX.Refusal as e:
        code = e.code
    record("e18_marker_exclusive_create", {
        "already_consumed": code == "TXN_ALREADY_CONSUMED",
        "no_lease_file_created": not os.path.exists(
            target + ".dispatch_lease"),
        "ledger_untouched": read(target) == LEGACY,
    })

    # e19 candidate pin drift refuses before marker -------------------------------------
    root = os.path.join(troot, "e19"); target = setup(root)
    pk = base_packet(root, "QF14-E19", expected_candidate_sha="0" * 64)
    code = None
    try:
        EX.LiveReadinessExecutor(pk, base_hooks()).run()
    except EX.Refusal as e:
        code = e.code
    record("e19_candidate_pin_drift", {
        "pin_drift_candidate": code == "PIN_DRIFT_CANDIDATE",
        "no_marker_created": not os.path.exists(
            os.path.join(pk["workdir"], "CONSUMED.marker")),
        "ledger_untouched": read(target) == LEGACY,
    })

    # e20 locked bytes match pin but fail legacy schema ----------------------------------
    root = os.path.join(troot, "e20"); target = setup(root, SCHEMA_BAD)
    pk = base_packet(root, "QF14-E20",
                     expected_original_sha=H(SCHEMA_BAD))
    spy = Spy()
    out = EX.LiveReadinessExecutor(pk, base_hooks(spy)).run()
    record("e20_locked_schema_mismatch_holds", {
        "hold_schema": out.get("outcome") == "HOLD"
        and out.get("reason") == "LOCKED_LEDGER_SCHEMA_MISMATCH",
        "bytes_untouched": read(target) == SCHEMA_BAD,
        "zero_status_calls": len(spy.calls) == 0,
    })

    matrix = {"task": "QF-TD-LIVE-READINESS-EXECUTOR-FINALIZE-20261017-14",
              "trials": RESULTS,
              "trials_total": len(RESULTS),
              "trials_passed": sum(1 for r in RESULTS if r["ok"]),
              "checks_total": sum(len(r["checks"]) for r in RESULTS),
              "checks_passed": sum(sum(1 for v in r["checks"].values() if v)
                                   for r in RESULTS)}
    with open(matrix_out, "w") as f:
        f.write(json.dumps(matrix, indent=1, sort_keys=True))
    print("MATRIX %d/%d trials, %d/%d checks" % (
        matrix["trials_passed"], matrix["trials_total"],
        matrix["checks_passed"], matrix["checks_total"]), flush=True)
    return 0 if matrix["trials_passed"] == matrix["trials_total"] else 1


if __name__ == "__main__":
    sys.exit(main())
