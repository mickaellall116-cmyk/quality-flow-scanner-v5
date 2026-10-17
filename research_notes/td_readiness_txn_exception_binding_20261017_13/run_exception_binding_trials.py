#!/usr/bin/env python3
"""Trial harness for QF-TD-READINESS-TXN-EXCEPTION-BINDING-20261017-13.

Modes:
  run_exception_binding_trials.py <trials_root> <output_json>
  run_exception_binding_trials.py --child <trial_dir> <crash_at>
  run_exception_binding_trials.py --recover <workdir> <target>

Carries the -12 recovery matrix forward (adapted to the r3 candidate)
and adds: real OSError/RuntimeError injection at every post-replace
persistence point, rollback-failure -> HOLD_MANUAL, strict
TERMINAL_COMPLETE tamper negatives, and journal path-binding negatives.
Output is normalized (no wall clock) so two runs under `unshare -n`
must be byte-identical.
"""
import fcntl
import json
import os
import subprocess
import sys

PKG = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PKG)
import readiness_transaction_r3 as RT  # noqa: E402

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
    packet = {"mode": "fixture", "txn_id": "TXN-13-" + name,
              "target_path": target, "candidate_bytes": CANDIDATE,
              "expected_original_sha": RT.H(ORIGINAL),
              "expected_candidate_sha": RT.H(CANDIDATE)}
    return d, target, workdir, packet


def read(p):
    with open(p, "rb") as f:
        return f.read()


def journal_of(workdir):
    return json.loads(read(os.path.join(workdir, "journal.json")).decode())


def lease_free(target):
    fd = open(target + ".dispatch_lease", "a+")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        free = True
    except OSError:
        free = False
    fd.close()
    return free


def run_child(trial_dir, crash_at):
    target = os.path.join(trial_dir, "ledger.json")
    workdir = os.path.join(trial_dir, "txn")
    packet = {"mode": "fixture", "txn_id": "TXN-13-child",
              "target_path": target, "candidate_bytes": CANDIDATE,
              "expected_original_sha": RT.H(ORIGINAL),
              "expected_candidate_sha": RT.H(CANDIDATE)}
    txn = RT.ReadinessTransactionR3(workdir, packet,
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

    def recover_sub(workdir, target):
        rp = subprocess.run([sys.executable, os.path.abspath(__file__),
                             "--recover", workdir, target],
                            capture_output=True, text=True)
        return json.loads(rp.stdout.strip().splitlines()[-1])

    def crash_trial(name, crash_at):
        d, target, workdir, _p = setup_trial(root, name)
        cp = subprocess.run([sys.executable, os.path.abspath(__file__),
                             "--child", d, crash_at],
                            capture_output=True)
        pre_journal = journal_of(workdir) if os.path.exists(
            os.path.join(workdir, "journal.json")) else {}
        res = recover_sub(workdir, target)
        j = journal_of(workdir)
        return d, target, workdir, cp, pre_journal, res, j

    def completed(name):
        d, target, workdir, packet = setup_trial(root, name)
        RT.ReadinessTransactionR3(workdir, packet, make_hooks()).run()
        return d, target, workdir

    def tamper(name, fn, reason_key=None):
        d, target, workdir = completed(name)
        fn(d, target, workdir)
        res = RT.recover(workdir, target)
        checks = {
            "classification_hold_manual":
                res["classification"] == "HOLD_MANUAL",
            "target_untouched_candidate": read(target) == CANDIDATE,
            "recovery_zero_status_calls":
                res["status_calls_during_recovery"] == 0}
        if reason_key is not None:
            checks["reason"] = res.get("reason") == reason_key
        record(name, checks)

    # T01 happy path ------------------------------------------------------
    d, target, workdir, packet = setup_trial(root, "t01_happy")
    txn = RT.ReadinessTransactionR3(workdir, packet, make_hooks())
    out = txn.run()
    j = journal_of(workdir)
    receipt = json.loads(read(os.path.join(
        workdir, "dry_run_receipt.json")))
    record("t01_happy_complete", {
        "outcome_complete": out["outcome"] == "COMPLETE",
        "target_is_candidate": read(target) == CANDIDATE,
        "journal_terminal_complete": j["phase"] == "TERMINAL_COMPLETE",
        "journal_paths_absolute_bound":
            j["target_path"] == os.path.abspath(target)
            and j["backup_path"] == os.path.join(
                os.path.abspath(workdir), "ledger_backup.bin"),
        "status_calls_1": j["status_calls"] == 1,
        "backup_is_original": read(os.path.join(
            workdir, "ledger_backup.bin")) == ORIGINAL,
        "receipt_bound_12_of_12":
            receipt["gates"] == ["PASS"] * 12
            and receipt["gates_passed"] == 12
            and receipt["txn_id"] == packet["txn_id"],
        "locks_released": lease_free(target),
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
        RT.ReadinessTransactionR3(workdir, dict(packet, mode="live"),
                                  make_hooks())
        live_refused = False
    except RT.Refusal as e:
        live_refused = e.code == "LIVE_MODE_REFUSED"
    record("t03_scope_refusals", {
        "all_not_in_scope": codes == ["NOT_IN_READINESS_SCOPE"] * 3,
        "live_mode_refused": live_refused})

    # T04 gate-3 fail ---------------------------------------------------------
    d, target, workdir, packet = setup_trial(root, "t04_gate3_fail")
    out = RT.ReadinessTransactionR3(
        workdir, packet, make_hooks(gate3=lambda f: False)).run()
    record("t04_gate3_fail_hold", {
        "outcome_hold": out["outcome"] == "HOLD",
        "target_untouched": read(target) == ORIGINAL,
        "no_backup_created": not os.path.exists(
            os.path.join(workdir, "ledger_backup.bin"))})

    # T05-T10 -12 Refusal post-replace faults (regression) -------------------
    def boom(_ev):
        raise RT.Refusal("DRYRUN_BOOM")
    fault_trials = [
        ("t05_fault_evidence_write", {"fail_at": "evidence_write"}),
        ("t06_fault_card_write", {"fail_at": "card_write"}),
        ("t07_fault_dry_run_refusal", {"dry_run": boom}),
        ("t08_fault_dry_run_11_of_12",
         {"dry_run": lambda ev: ["PASS"] * 11 + ["FAIL"]}),
        ("t09_fault_terminal_write", {"fail_at": "terminal_write"}),
        ("t10_fault_post_write_verify", {"fail_at": "post_write_verify"}),
    ]
    for name, over in fault_trials:
        d, target, workdir, packet = setup_trial(root, name)
        out = RT.ReadinessTransactionR3(
            workdir, packet, make_hooks(**over)).run()
        j = journal_of(workdir)
        record(name, {
            "outcome_rolled_back": out["outcome"] == "ROLLED_BACK",
            "target_exact_legacy": read(target) == ORIGINAL,
            "journal_terminal_rolled_back":
                j["phase"] == "TERMINAL_ROLLED_BACK",
            "terminal_record_written": os.path.exists(
                os.path.join(workdir, "terminal_record.json"))})

    # X01-X07 REAL exceptions after replace ----------------------------------
    def rt_boom(_ev):
        raise RuntimeError("dry-run hook exploded")
    exc_trials = [
        ("x01_oserror_evidence_write",
         {"raise_at": {"evidence:write": OSError("disk gone")}}),
        ("x02_oserror_evidence_fsync",
         {"raise_at": {"evidence:fsync": OSError("fsync failed")}}),
        ("x03_oserror_card_fsync",
         {"raise_at": {"card:fsync": OSError("fsync failed")}}),
        ("x04_runtimeerror_dry_run", {"dry_run": rt_boom}),
        ("x05_oserror_receipt_write",
         {"raise_at": {"receipt:write": OSError("disk gone")}}),
        ("x06_oserror_terminal_fsync",
         {"raise_at": {"terminal:fsync": OSError("fsync failed")}}),
        ("x07_oserror_terminal_journal_advance",
         {"raise_at": {"journal:TERMINAL_COMPLETE":
                       OSError("journal flush failed")}}),
    ]
    for name, over in exc_trials:
        d, target, workdir, packet = setup_trial(root, name)
        out = RT.ReadinessTransactionR3(
            workdir, packet, make_hooks(**over)).run()
        j = journal_of(workdir)
        record(name, {
            "outcome_rolled_back": out["outcome"] == "ROLLED_BACK",
            "target_exact_legacy_before_lock_release":
                read(target) == ORIGINAL,
            "journal_terminal_rolled_back":
                j["phase"] == "TERMINAL_ROLLED_BACK",
            "locks_released": lease_free(target)})

    # X08 rollback itself fails -> HOLD_MANUAL, never ROLLED_BACK -------------
    d, target, workdir, packet = setup_trial(root, "x08_rollback_fails")
    out = RT.ReadinessTransactionR3(workdir, packet, make_hooks(
        raise_at={"evidence:write": OSError("disk gone"),
                  "rollback:write": OSError("rollback disk gone")})).run()
    j = journal_of(workdir)
    record("x08_rollback_fails_hold_manual", {
        "outcome_hold_manual": out["outcome"] == "HOLD_MANUAL",
        "reason_rollback_unverified":
            out.get("reason") == "ROLLBACK_UNVERIFIED",
        "journal_terminal_hold_manual":
            j["phase"] == "TERMINAL_HOLD_MANUAL",
        "target_still_candidate_not_claimed_rolled_back":
            read(target) == CANDIDATE,
        "locks_released": lease_free(target)})

    # T11 crash after backup, then cold recovery -----------------------------
    d, target, workdir, cp, pre_j, res, j = crash_trial(
        "t11_crash_after_backup", "after_backup")
    record("t11_crash_after_backup", {
        "child_killed": cp.returncode == 42,
        "journal_bound_before_replace":
            pre_j.get("phase") == "BACKED_UP"
            and pre_j.get("backup_sha") == pre_j.get("original_sha")
            and pre_j.get("candidate_sha") == RT.H(CANDIDATE)
            and pre_j.get("txn_id") == "TXN-13-child",
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
    subprocess.run([sys.executable, os.path.abspath(__file__),
                    "--child", d, "after_replace"], capture_output=True)
    with open(os.path.join(workdir, "journal.json"), "wb") as f:
        f.write(b"{not json")
    res2 = recover_sub(workdir, target)
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
    res2 = recover_sub(workdir, target)
    record("t18_unknown_target_hold_manual", {
        "classification_hold_manual":
            res2["classification"] == "HOLD_MANUAL",
        "target_untouched": read(target) == b"third-party bytes"})

    # T19 backup tampered -> HOLD_MANUAL ---------------------------------------
    d, target, workdir, packet = setup_trial(root, "t19_backup_tampered")
    cp = subprocess.run([sys.executable, os.path.abspath(__file__),
                         "--child", d, "after_replace"], capture_output=True)
    with open(os.path.join(workdir, "ledger_backup.bin"), "wb") as f:
        f.write(b"tampered backup")
    res2 = recover_sub(workdir, target)
    record("t19_backup_tampered_hold_manual", {
        "child_killed": cp.returncode == 42,
        "classification_hold_manual":
            res2["classification"] == "HOLD_MANUAL",
        "reason_backup_verify": res2.get("reason") == "BACKUP_VERIFY_FAIL",
        "target_untouched_candidate": read(target) == CANDIDATE})

    # T20 recovery of a COMPLETE transaction (strict validation passes) --------
    d, target, workdir = completed("t20_recover_complete")
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
    RT.ReadinessTransactionR3(
        workdir, packet, make_hooks(fail_at="card_write")).run()
    res = RT.recover(workdir, target)
    record("t22_recover_rolled_back", {
        "classification_rolled_back":
            res["classification"] == "ROLLED_BACK",
        "target_exact_legacy": read(target) == ORIGINAL})

    # B01-B07 TERMINAL_COMPLETE tamper negatives --------------------------------
    def t_receipt_empty(d, target, workdir):
        open(os.path.join(workdir, "dry_run_receipt.json"), "wb").close()
    tamper("b01_receipt_empty", t_receipt_empty, "RECEIPT_UNREADABLE")

    def t_receipt_11(d, target, workdir):
        p = os.path.join(workdir, "dry_run_receipt.json")
        r = json.loads(read(p))
        r["gates"] = ["PASS"] * 11 + ["FAIL"]
        r["gates_passed"] = 11
        with open(p, "wb") as f:
            f.write(RT.canon(r))
    tamper("b02_receipt_11_of_12", t_receipt_11,
           "RECEIPT_NOT_12_OF_12_BOUND")

    def t_receipt_wrong_txn(d, target, workdir):
        p = os.path.join(workdir, "dry_run_receipt.json")
        r = json.loads(read(p))
        r["txn_id"] = "TXN-OTHER"
        with open(p, "wb") as f:
            f.write(RT.canon(r))
    tamper("b03_receipt_wrong_txn", t_receipt_wrong_txn,
           "RECEIPT_NOT_12_OF_12_BOUND")

    def t_terminal_wrong_id(d, target, workdir):
        p = os.path.join(workdir, "terminal_record.json")
        r = json.loads(read(p))
        r["txn_id"] = "TXN-OTHER"
        with open(p, "wb") as f:
            f.write(RT.canon(r))
    tamper("b04_terminal_wrong_id", t_terminal_wrong_id,
           "TERMINAL_RECORD_MISMATCH")

    def t_terminal_wrong_outcome(d, target, workdir):
        p = os.path.join(workdir, "terminal_record.json")
        r = json.loads(read(p))
        r["outcome"] = "HOLD"
        with open(p, "wb") as f:
            f.write(RT.canon(r))
    tamper("b05_terminal_wrong_outcome", t_terminal_wrong_outcome,
           "TERMINAL_RECORD_MISMATCH")

    def t_evidence_tampered(d, target, workdir):
        p = os.path.join(workdir, "evidence.json")
        e = json.loads(read(p))
        e["facts"] = {"plan_limit": 999}
        with open(p, "wb") as f:
            f.write(RT.canon(e))
    tamper("b06_evidence_tampered", t_evidence_tampered,
           "CARD_CROSS_DIGEST_MISMATCH")

    def t_card_tampered(d, target, workdir):
        p = os.path.join(workdir, "token_card.json")
        c = json.loads(read(p))
        c["evidence_sha"] = "0" * 64
        with open(p, "wb") as f:
            f.write(RT.canon(c))
    tamper("b07_card_tampered", t_card_tampered,
           "CARD_CROSS_DIGEST_MISMATCH")

    # B08-B14 journal binding negatives ------------------------------------------
    def t_marker_mismatch(d, target, workdir):
        p = os.path.join(workdir, "CONSUMED.marker")
        m = json.loads(read(p))
        m["txn_id"] = "TXN-OTHER"
        with open(p, "wb") as f:
            f.write(RT.canon(m))
    tamper("b08_marker_journal_mismatch", t_marker_mismatch,
           "MARKER_JOURNAL_TXN_MISMATCH")

    def t_history_nonmonotonic(d, target, workdir):
        p = os.path.join(workdir, "journal.json")
        jj = json.loads(read(p))
        h = jj["phase_history"]
        h[3], h[4] = h[4], h[3]
        with open(p, "wb") as f:
            f.write(RT.canon(jj))
    tamper("b09_history_nonmonotonic", t_history_nonmonotonic,
           "JOURNAL_PHASE_HISTORY_INVALID")

    def t_journal_target_edited(d, target, workdir):
        p = os.path.join(workdir, "journal.json")
        jj = json.loads(read(p))
        jj["target_path"] = os.path.join(d, "other_ledger.json")
        with open(p, "wb") as f:
            f.write(RT.canon(jj))
    tamper("b10_journal_target_edited", t_journal_target_edited,
           "JOURNAL_TARGET_BINDING")

    def t_journal_backup_edited(d, target, workdir):
        p = os.path.join(workdir, "journal.json")
        jj = json.loads(read(p))
        jj["backup_path"] = os.path.join(workdir, "elsewhere.bin")
        with open(p, "wb") as f:
            f.write(RT.canon(jj))
    tamper("b11_journal_backup_edited", t_journal_backup_edited,
           "JOURNAL_BACKUP_BINDING")

    # B12 caller supplies a wrong target -----------------------------------------
    d, target, workdir = completed("b12_wrong_caller_target")
    wrong = os.path.join(d, "decoy_ledger.json")
    with open(wrong, "wb") as f:
        f.write(CANDIDATE)
    res = RT.recover(workdir, wrong)
    record("b12_wrong_caller_target", {
        "classification_hold_manual":
            res["classification"] == "HOLD_MANUAL",
        "reason_target_binding": res.get("reason") == "JOURNAL_TARGET_BINDING",
        "decoy_untouched": read(wrong) == CANDIDATE,
        "no_lock_files_on_decoy":
            not os.path.exists(wrong + ".lock")
            and not os.path.exists(wrong + ".dispatch_lease"),
        "real_target_untouched": read(target) == CANDIDATE})

    # B13 symlink substitution of the target --------------------------------------
    d, target, workdir = completed("b13_symlink_substitution")
    decoy = os.path.join(d, "decoy.json")
    with open(decoy, "wb") as f:
        f.write(CANDIDATE)
    os.remove(target)
    os.symlink(decoy, target)
    res = RT.recover(workdir, target)
    record("b13_symlink_substitution", {
        "classification_hold_manual":
            res["classification"] == "HOLD_MANUAL",
        "reason_symlink":
            res.get("reason") == "TARGET_SYMLINK_OR_REALPATH_MISMATCH",
        "decoy_untouched": read(decoy) == CANDIDATE,
        "target_still_symlink": os.path.islink(target)})

    # B14 journal relocated to a second workdir ------------------------------------
    import shutil
    d, target, workdir = completed("b14_journal_relocated")
    workdir2 = workdir + "_copy"
    shutil.copytree(workdir, workdir2)
    res = RT.recover(workdir2, target)
    record("b14_journal_relocated", {
        "classification_hold_manual":
            res["classification"] == "HOLD_MANUAL",
        "reason_workdir_binding":
            res.get("reason") == "JOURNAL_WORKDIR_BINDING",
        "target_untouched": read(target) == CANDIDATE})

    # B15 second journal for the same target ---------------------------------------
    d, target, workdir = completed("b15_second_journal")
    shutil.copy(os.path.join(workdir, "journal.json"),
                os.path.join(workdir, "journal_copy.json"))
    res = RT.recover(workdir, target)
    record("b15_second_journal_ambiguous", {
        "classification_hold_manual":
            res["classification"] == "HOLD_MANUAL",
        "reason_ambiguous": res.get("reason") == "AMBIGUOUS_SECOND_JOURNAL",
        "target_untouched": read(target) == CANDIDATE})

    total_checks = sum(len(t["checks"]) for t in trials.values())
    passed_checks = sum(sum(1 for v in t["checks"].values() if v)
                        for t in trials.values())
    matrix = {"task": "QF-TD-READINESS-TXN-EXCEPTION-BINDING-20261017-13",
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
