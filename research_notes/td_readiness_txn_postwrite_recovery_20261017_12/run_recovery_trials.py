#!/usr/bin/env python3
"""Trial harness for QF-TD-READINESS-TXN-POSTWRITE-RECOVERY-20261017-12.

Modes:
  run_recovery_trials.py <trials_root> <output_json>   full matrix
  run_recovery_trials.py --child <trial_dir> <crash_at>
  run_recovery_trials.py --recover <workdir> <target>  prints JSON

Output is normalized (basenames only, no wall clock) so two runs under
`unshare -n` must be byte-identical.
"""
import json
import os
import subprocess
import sys

PKG = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PKG)
import readiness_transaction_r2 as RT  # noqa: E402

ORIGINAL = RT.canon({"schema": "legacy", "day": "2026-10-14", "spent": 8,
                     "window": [[1792001518.58, 1]] * 7})
CANDIDATE = RT.canon({"schema": "reservations",
                      "reservations": [{"rid": "legacy-%d" % i,
                                        "weight": 1} for i in range(8)]})
FACTS = {"plan_limit": 8, "plan_daily_limit": 800, "daily_usage": 0,
         "daily_remaining": 800}


def make_hooks(**over):
    hooks = {
        "fixture": True,
        "verify_helper": lambda: True,
        "status_call": lambda: dict(FACTS),
        "gate3": lambda facts: True,
        "dry_run": lambda ev: ["PASS"] * 12,
    }
    hooks.update(over)
    return hooks


def setup_trial(root, name):
    d = os.path.join(root, name)
    os.makedirs(d, exist_ok=True)
    target = os.path.join(d, "ledger.json")
    with open(target, "wb") as f:
        f.write(ORIGINAL)
    workdir = os.path.join(d, "txn")
    packet = {"mode": "fixture", "txn_id": "TXN-12-" + name,
              "target_path": target, "candidate_bytes": CANDIDATE,
              "expected_original_sha": RT.H(ORIGINAL),
              "expected_candidate_sha": RT.H(CANDIDATE)}
    return d, target, workdir, packet


def read(p):
    with open(p, "rb") as f:
        return f.read()


def journal_of(workdir):
    return json.loads(read(os.path.join(workdir, "journal.json")).decode())


def run_child(trial_dir, crash_at):
    target = os.path.join(trial_dir, "ledger.json")
    workdir = os.path.join(trial_dir, "txn")
    packet = {"mode": "fixture", "txn_id": "TXN-12-child",
              "target_path": target, "candidate_bytes": CANDIDATE,
              "expected_original_sha": RT.H(ORIGINAL),
              "expected_candidate_sha": RT.H(CANDIDATE)}
    txn = RT.ReadinessTransactionR2(workdir, packet,
                                    make_hooks(crash_at=crash_at))
    txn.run()
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        return run_child(sys.argv[2], sys.argv[3])
    if len(sys.argv) > 1 and sys.argv[1] == "--recover":
        res = RT.recover(sys.argv[2], sys.argv[3])
        print(json.dumps(res, sort_keys=True))
        return 0

    root, out_path = sys.argv[1], sys.argv[2]
    os.makedirs(root, exist_ok=True)
    trials = {}

    def record(name, checks, **extra):
        entry = {"checks": checks, "passed": all(checks.values())}
        entry.update(extra)
        trials[name] = entry

    def crash_trial(name, crash_at):
        d, target, workdir, _p = setup_trial(root, name)
        cp = subprocess.run([sys.executable, os.path.abspath(__file__),
                             "--child", d, crash_at],
                            capture_output=True)
        pre_journal = journal_of(workdir) if os.path.exists(
            os.path.join(workdir, "journal.json")) else {}
        rp = subprocess.run([sys.executable, os.path.abspath(__file__),
                             "--recover", workdir, target],
                            capture_output=True, text=True)
        res = json.loads(rp.stdout.strip().splitlines()[-1])
        j = journal_of(workdir)
        return d, target, workdir, cp, pre_journal, res, j

    # T01 happy path ------------------------------------------------------
    d, target, workdir, packet = setup_trial(root, "t01_happy")
    txn = RT.ReadinessTransactionR2(workdir, packet, make_hooks())
    out = txn.run()
    j = journal_of(workdir)
    lease_fd = open(target + ".dispatch_lease", "a+")
    import fcntl as _f
    try:
        _f.flock(lease_fd, _f.LOCK_EX | _f.LOCK_NB)
        lease_free = True
    except OSError:
        lease_free = False
    lease_fd.close()
    record("t01_happy_complete", {
        "outcome_complete": out["outcome"] == "COMPLETE",
        "target_is_candidate": read(target) == CANDIDATE,
        "journal_terminal_complete": j["phase"] == "TERMINAL_COMPLETE",
        "status_calls_1": j["status_calls"] == 1,
        "backup_is_original": read(os.path.join(
            workdir, "ledger_backup.bin")) == ORIGINAL,
        "receipt_12_of_12": json.loads(read(os.path.join(
            workdir, "dry_run_receipt.json")))["gates_passed"] == 12,
        "locks_released": lease_free,
        "phase_history_ordered": j["phase_history"] == [
            "BEGUN", "PREFLIGHT_OK", "LOCKS_HELD", "HELPER_OK",
            "STATUS_CONSUMED", "GATE3_OK", "BACKED_UP", "REPLACED",
            "VERIFIED", "REFROZEN", "DRYRUN_OK", "TERMINAL_COMPLETE"],
    })

    # T02 one-use -----------------------------------------------------------
    try:
        txn.run()
        refused = False
    except RT.Refusal as e:
        refused = e.code == "TXN_ALREADY_CONSUMED"
    record("t02_one_use_refusal", {"second_run_refused": refused})

    # T03 scope refusals ----------------------------------------------------
    codes = []
    for fn in (txn.request_token, txn.arm_transport, txn.call_time_series):
        try:
            fn()
            codes.append("NONE")
        except RT.Refusal as e:
            codes.append(e.code)
    try:
        RT.ReadinessTransactionR2(workdir, dict(packet, mode="live"),
                                  make_hooks())
        live_refused = False
    except RT.Refusal as e:
        live_refused = e.code == "LIVE_MODE_REFUSED"
    record("t03_scope_refusals", {
        "all_not_in_scope": codes == ["NOT_IN_READINESS_SCOPE"] * 3,
        "live_mode_refused": live_refused})

    # T04 gate-3 fail ---------------------------------------------------------
    d, target, workdir, packet = setup_trial(root, "t04_gate3_fail")
    out = RT.ReadinessTransactionR2(
        workdir, packet, make_hooks(gate3=lambda f: False)).run()
    record("t04_gate3_fail_hold", {
        "outcome_hold": out["outcome"] == "HOLD",
        "target_untouched": read(target) == ORIGINAL,
        "no_backup_created": not os.path.exists(
            os.path.join(workdir, "ledger_backup.bin"))})

    # T05-T10 ordinary post-replace faults ----------------------------------
    fault_trials = [
        ("t05_fault_evidence_write", {"fail_at": "evidence_write"}),
        ("t06_fault_card_write", {"fail_at": "card_write"}),
        ("t07_fault_dry_run_exception",
         {"dry_run": lambda ev: (_ for _ in ()).throw(
             RT.Refusal("DRYRUN_BOOM"))}),
        ("t08_fault_dry_run_11_of_12",
         {"dry_run": lambda ev: ["PASS"] * 11 + ["FAIL"]}),
        ("t09_fault_terminal_write", {"fail_at": "terminal_write"}),
        ("t10_fault_post_write_verify", {"fail_at": "post_write_verify"}),
    ]
    for name, over in fault_trials:
        d, target, workdir, packet = setup_trial(root, name)
        out = RT.ReadinessTransactionR2(
            workdir, packet, make_hooks(**over)).run()
        j = journal_of(workdir)
        record(name, {
            "outcome_rolled_back": out["outcome"] == "ROLLED_BACK",
            "target_exact_legacy": read(target) == ORIGINAL,
            "journal_terminal_rolled_back":
                j["phase"] == "TERMINAL_ROLLED_BACK",
            "terminal_record_written": os.path.exists(
                os.path.join(workdir, "terminal_record.json"))})

    # T11 crash after backup, then cold recovery -----------------------------
    d, target, workdir, cp, pre_j, res, j = crash_trial(
        "t11_crash_after_backup", "after_backup")
    record("t11_crash_after_backup", {
        "child_killed": cp.returncode == 42,
        "journal_bound_before_replace":
            pre_j.get("phase") == "BACKED_UP"
            and pre_j.get("backup_sha") == pre_j.get("original_sha")
            and pre_j.get("candidate_sha") == RT.H(CANDIDATE)
            and pre_j.get("txn_id") == "TXN-12-child",
        "classification_pre_replace": res["classification"] == "PRE_REPLACE",
        "recovery_zero_status_calls":
            res["status_calls_during_recovery"] == 0,
        "target_exact_legacy": read(target) == ORIGINAL,
        "journal_recovered_hold": j["phase"] == "TERMINAL_RECOVERED_HOLD",
        "total_status_calls_still_1": j["status_calls"] == 1},
        pre_journal_phase=pre_j.get("phase"))

    # T12-T16 crashes at/after replace ---------------------------------------
    crash_points = [
        ("t12_crash_after_replace", "after_replace"),
        ("t13_crash_during_evidence", "during_evidence"),
        ("t14_crash_during_card", "during_card"),
        ("t15_crash_during_dry_run", "during_dry_run"),
        ("t16_crash_during_terminal", "during_terminal"),
    ]
    for name, point in crash_points:
        d, target, workdir, cp, pre_j, res, j = crash_trial(name, point)
        record(name, {
            "child_killed": cp.returncode == 42,
            "saw_candidate_or_partial": pre_j.get("phase") in (
                "REPLACED", "VERIFIED", "REFROZEN", "DRYRUN_OK"),
            "classification_post_replace":
                res["classification"] == "POST_REPLACE_UNVERIFIED",
            "restored_flag": res.get("restored") is True,
            "recovery_zero_status_calls":
                res["status_calls_during_recovery"] == 0,
            "target_exact_legacy": read(target) == ORIGINAL,
            "journal_recovered_hold":
                j["phase"] == "TERMINAL_RECOVERED_HOLD",
            "total_status_calls_still_1": j["status_calls"] == 1},
            pre_journal_phase=pre_j.get("phase"))

    # T17 corrupt journal -> HOLD_MANUAL, no touch ----------------------------
    d, target, workdir, packet = setup_trial(root, "t17_corrupt_journal")
    cp = subprocess.run([sys.executable, os.path.abspath(__file__),
                         "--child", d, "after_replace"], capture_output=True)
    with open(os.path.join(workdir, "journal.json"), "wb") as f:
        f.write(b"{not json")
    rp = subprocess.run([sys.executable, os.path.abspath(__file__),
                         "--recover", workdir, target],
                        capture_output=True, text=True)
    res2 = json.loads(rp.stdout.strip().splitlines()[-1])
    record("t17_corrupt_journal_hold_manual", {
        "classification_hold_manual":
            res2["classification"] == "HOLD_MANUAL",
        "target_untouched_candidate": read(target) == CANDIDATE,
        "recovery_zero_status_calls":
            res2["status_calls_during_recovery"] == 0})

    # T18 unknown target bytes -> HOLD_MANUAL ---------------------------------
    d, target, workdir, cp, pre_j, res, j = crash_trial(
        "t18_unknown_target", "after_replace")
    with open(target, "wb") as f:
        f.write(b"third-party bytes")
    rp = subprocess.run([sys.executable, os.path.abspath(__file__),
                         "--recover", workdir, target],
                        capture_output=True, text=True)
    res2 = json.loads(rp.stdout.strip().splitlines()[-1])
    record("t18_unknown_target_hold_manual", {
        "classification_hold_manual":
            res2["classification"] == "HOLD_MANUAL",
        "target_untouched": read(target) == b"third-party bytes"})

    # T19 backup tampered -> HOLD_MANUAL ---------------------------------------
    d, target, workdir, cp, pre_j, res, j = crash_trial(
        "t19_backup_tampered", "after_replace")
    # NOTE: crash_trial already recovered t19's dir; rebuild a fresh one.
    d, target, workdir, packet = setup_trial(root, "t19b_backup_tampered")
    cp = subprocess.run([sys.executable, os.path.abspath(__file__),
                         "--child", d, "after_replace"], capture_output=True)
    with open(os.path.join(workdir, "ledger_backup.bin"), "wb") as f:
        f.write(b"tampered backup")
    rp = subprocess.run([sys.executable, os.path.abspath(__file__),
                         "--recover", workdir, target],
                        capture_output=True, text=True)
    res2 = json.loads(rp.stdout.strip().splitlines()[-1])
    record("t19_backup_tampered_hold_manual", {
        "child_killed": cp.returncode == 42,
        "classification_hold_manual":
            res2["classification"] == "HOLD_MANUAL",
        "reason_backup_verify": res2.get("reason") == "BACKUP_VERIFY_FAIL",
        "target_untouched_candidate": read(target) == CANDIDATE})

    # T20 recovery of a COMPLETE transaction ----------------------------------
    d, target, workdir, packet = setup_trial(root, "t20_recover_complete")
    RT.ReadinessTransactionR2(workdir, packet, make_hooks()).run()
    res = RT.recover(workdir, target)
    record("t20_recover_complete", {
        "classification_adopted_verified":
            res["classification"] == "ADOPTED_VERIFIED",
        "target_still_candidate": read(target) == CANDIDATE,
        "recovery_zero_status_calls":
            res["status_calls_during_recovery"] == 0})

    # T21 recovery NOT_STARTED ---------------------------------------------------
    d = os.path.join(root, "t21_not_started")
    os.makedirs(d, exist_ok=True)
    tgt = os.path.join(d, "ledger.json")
    with open(tgt, "wb") as f:
        f.write(ORIGINAL)
    res = RT.recover(os.path.join(d, "txn"), tgt)
    record("t21_recover_not_started", {
        "classification_not_started":
            res["classification"] == "NOT_STARTED"})

    # T22 recovery of a ROLLED_BACK terminal transaction -------------------------
    d, target, workdir, packet = setup_trial(root, "t22_recover_rolled_back")
    RT.ReadinessTransactionR2(
        workdir, packet, make_hooks(fail_at="card_write")).run()
    res = RT.recover(workdir, target)
    record("t22_recover_rolled_back", {
        "classification_rolled_back":
            res["classification"] == "ROLLED_BACK",
        "target_exact_legacy": read(target) == ORIGINAL})

    total_checks = sum(len(t["checks"]) for t in trials.values())
    passed_checks = sum(sum(1 for v in t["checks"].values() if v)
                        for t in trials.values())
    matrix = {"task": "QF-TD-READINESS-TXN-POSTWRITE-RECOVERY-20261017-12",
              "trials": trials,
              "totals": {"trials": len(trials),
                         "trials_passed": sum(
                             1 for t in trials.values() if t["passed"]),
                         "checks": total_checks,
                         "checks_passed": passed_checks}}
    with open(out_path, "wb") as f:
        f.write(RT.canon(matrix) + b"\n")
    print(json.dumps(matrix["totals"], sort_keys=True))
    return 0 if passed_checks == total_checks else 1


if __name__ == "__main__":
    sys.exit(main())
