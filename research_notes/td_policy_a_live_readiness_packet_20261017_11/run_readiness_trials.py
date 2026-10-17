#!/usr/bin/env python3
"""QF-TD-POLICY-A-LIVE-READINESS-PACKET-20261017-11 r1 - adversarial
trials for readiness_transaction.py. Fixtures only: the status hook is
a fixture callable, the ledger target is a fixture COPY of the legacy
ledger, adoption writes only inside the trial root. The real pilot
ledger is hash-checked before/after and never written.

  run_readiness_trials.py <trials_root> <output_json>
"""
import datetime
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

PKG = os.path.dirname(os.path.abspath(__file__))
NOTES = os.path.abspath(os.path.join(PKG, ".."))
sys.path.insert(0, PKG)
import readiness_transaction as TX  # noqa: E402

NOTES11 = PKG
REAL_LEDGER = os.path.join(NOTES, "pilot_harness", "credit_ledger.json")
LEGACY_BYTES = open(REAL_LEDGER, "rb").read()
CANDIDATE_PATH = os.path.join(NOTES, "td_ledger_compat_card_binding_20261017_07",
                              "candidate_credit_ledger.json")
MANIFEST_PATH = os.path.join(NOTES, "td_fresh_full_manifest_preflight_evidence_20261016",
                             "fresh_manifest.json")
SUPPLEMENT_PATH = os.path.join(NOTES, "td_fresh_full_manifest_preflight_evidence_20261016",
                               "fresh_supplement.json")
NOW = 1792224000  # 2026-10-17T14:00:00Z fixed test clock (matches r4 runner)
RUN_DAY = "2026-10-17"


def H(b):
    return hashlib.sha256(b).hexdigest()


def fmt(ts):
    return datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


MANIFEST_BYTES = open(MANIFEST_PATH, "rb").read()
REQ_IDS = [r["request_id"] for r in json.loads(MANIFEST_BYTES)["requests"]]
SEQ_SHA = H(TX.canon(REQ_IDS))
PASS_RAW = {"timestamp": fmt(NOW - 60), "current_usage": 0, "plan_limit": 8,
            "daily_usage": 100, "plan_daily_limit": 800,
            "plan_category": "basic"}


class Hooks:
    def __init__(self, raw=None, fail_at=(), consumer_ok=True):
        self.calls = {"resolve": 0, "status": 0}
        self.raw = PASS_RAW if raw is None else raw
        self.fail_at = set(fail_at)
        self.consumer_ok = consumer_ok

        def resolve_helper():
            self.calls["resolve"] += 1
            return {"fixture": True, "origin": "fixture-resolver"}
        resolve_helper.is_fixture = True
        self.resolve_helper = resolve_helper

        def status_call():
            self.calls["status"] += 1
            if isinstance(self.raw, Exception):
                raise self.raw
            return dict(self.raw)
        status_call.is_fixture = True
        self.status_call = status_call

    def consumer_verify(self, path):
        if not self.consumer_ok:
            return False
        led = json.loads(open(path, "rb").read())
        recs = led.get("reservations")
        if not isinstance(recs, list) or len(recs) != 8:
            return False
        return all(set(r) >= {"rid", "ts", "day", "weight"} for r in recs)

    def dry_run(self, _evidence_bytes):
        return {"decision": "PASS_DRY_RUN", "gates_passed": 12}


def real_dry_run_hook(txn_packet):
    """Dry-run hook backed by the REAL r4 gate (12/12 or it raises)."""
    import run_dispatch_gate_trials_r4 as R

    def hook(_evidence_bytes):
        root = os.path.join(txn_packet["fixture_root"], "dryrun_root")
        t2 = R.Trial("dryrun", root)
        ev = R.base_evidence(t2)
        ev["packet"]["ledger_path"] = txn_packet["ledger_target"]
        ev["account"] = {"api_usage": dict(PASS_RAW), "source": "txn_fixture"}
        fac = R.RecordingFactory(t2)
        res = t2.dispatch(R.G.canon(ev), transport_factory=fac)
        gates = res["receipt"]["gates"]
        return {"decision": res["receipt"]["decision"],
                "gates_passed": sum(1 for g in gates if g["result"] == "PASS")}
    return hook


def build_packet(root, **over):
    target = os.path.join(root, "ledger.json")
    with open(target, "wb") as f:
        f.write(LEGACY_BYTES)
    pk = {
        "mode": "offline_fixture",
        "txn_id": "QF-TD-READINESS-TXN-FIXTURE-0001",
        "fixture_root": root,
        "ledger_target": target,
        "backup_path": os.path.join(root, "ledger_backup.json"),
        "evidence_path": os.path.join(root, "refrozen_evidence.json"),
        "card_path": os.path.join(root, "refrozen_card.json"),
        "run_id": "TD-FRESH-FM-20261016-03-R1",
        "run_day": RUN_DAY,
        "now": NOW,
        "window": {"start": NOW - 3600, "end": NOW + 3600},
        "policy_digest": TX.PIN_POLICY_A,
        "ceiling_credits": 52,
        "manifest_sequence_sha256": SEQ_SHA,
        "source_ledger_sha256": H(LEGACY_BYTES),
        "go_record": {"record_id": TX.GO_RECORD_ID,
                      "comment_id": TX.GO_COMMENT_ID,
                      "ceiling_credits": 52, "status_credits": 1,
                      "manifest_credits": 51, "spend_usd": 0},
        "pins": {"manifest": H(MANIFEST_BYTES),
                 "supplement": H(open(SUPPLEMENT_PATH, "rb").read()),
                 "ledger_candidate": H(open(CANDIDATE_PATH, "rb").read())},
        "pin_paths": {"manifest": MANIFEST_PATH,
                      "supplement": SUPPLEMENT_PATH,
                      "ledger_candidate": CANDIDATE_PATH},
    }
    pk.update(over)
    return pk


class WT:
    def __init__(self, name, root):
        self.name = name
        self.dir = os.path.join(root, name)
        os.makedirs(self.dir)
        self.checks = []
        self.facts = {}

    def check(self, name, cond):
        self.checks.append(name)
        if not cond:
            raise AssertionError(name)


def tgt_hash(pk):
    return H(open(pk["ledger_target"], "rb").read())


# ---------------------------------------------------------------- trials
def t01_happy(t):
    pk = build_packet(t.dir)
    hooks = Hooks()
    hooks.dry_run = real_dry_run_hook(pk)
    txn = TX.ReadinessTransaction(t.dir, pk, hooks)
    out = txn.run()
    t.check("outcome_complete", out["outcome"] == "COMPLETE")
    t.check("exactly_one_status_call", out["status_calls"] == 1
            and hooks.calls["status"] == 1)
    t.check("adopted_candidate", tgt_hash(pk) == pk["pins"]["ledger_candidate"])
    t.check("backup_is_legacy", H(open(pk["backup_path"], "rb").read()) == H(LEGACY_BYTES))
    t.check("step_order", [s["step"] for s in out["steps"]] ==
            ["begin", "preflight", "locks", "helper_verified", "status_call",
             "gate3", "backup", "adopted", "post_write_verified", "refreeze",
             "dry_run"])
    t.check("lock_order", out["steps"][2]["order"] == ["owner_lease", "ledger_lock"])
    t.check("gate3_pass", out["gate3"]["code"] == "ACCOUNT_VERIFIED_POLICY_A")
    t.check("dry_run_12_of_12", out["steps"][-1]["decision"] == "PASS_DRY_RUN")
    t.check("terminal_record", os.path.exists(os.path.join(t.dir, "terminal_record.json")))
    t.check("card_verifies", TX.ReadinessTransaction.verify_card(
        pk["card_path"], pk["evidence_path"]) is True)
    t.facts["evidence_digest"] = out["evidence_digest"]


def t02_one_use(t):
    pk = build_packet(t.dir)
    hooks = Hooks()
    out = TX.ReadinessTransaction(t.dir, pk, hooks).run()
    t.check("first_complete", out["outcome"] == "COMPLETE")
    out2 = TX.ReadinessTransaction(t.dir, pk, Hooks()).run()
    t.check("second_refused", out2["outcome"] == "HOLD"
            and out2["refusal"] == "TRANSACTION_ALREADY_CONSUMED")
    t.check("no_second_status_call", hooks.calls["status"] == 1)


def _preflight_refusal(t, over, code, check_resolve_zero=False):
    pk = build_packet(t.dir, **over)
    hooks = Hooks()
    out = TX.ReadinessTransaction(t.dir, pk, hooks).run()
    t.check("hold", out["outcome"] == "HOLD")
    t.check("refusal_code", out["refusal"] == code)
    t.check("zero_status_calls", hooks.calls["status"] == 0)
    t.check("target_unchanged", tgt_hash(pk) == H(LEGACY_BYTES))
    t.check("no_locks_acquired", not os.path.exists(pk["ledger_target"] + ".owner_lease"))
    if check_resolve_zero:
        t.check("helper_never_verified", hooks.calls["resolve"] == 0)


def t03_go_absent(t):
    pk = build_packet(t.dir)
    del pk["go_record"]
    hooks = Hooks()
    out = TX.ReadinessTransaction(t.dir, pk, hooks).run()
    t.check("hold", out["outcome"] == "HOLD")
    t.check("code", out["refusal"] == "GO_RECORD_MISSING")
    t.check("zero_calls", hooks.calls["status"] == 0)


def t04_go_malformed(t):
    go = {"record_id": TX.GO_RECORD_ID, "comment_id": 1, "ceiling_credits": 52,
          "status_credits": 1, "manifest_credits": 51, "spend_usd": 0}
    _preflight_refusal(t, {"go_record": go}, "GO_RECORD_MALFORMED")


def t05_policy_digest(t):
    _preflight_refusal(t, {"policy_digest": "0" * 64}, "POLICY_DIGEST_MISMATCH",
                       check_resolve_zero=True)


def t06_ceiling(t):
    _preflight_refusal(t, {"ceiling_credits": 51}, "POLICY_CEILING_MISMATCH")


def t07_manifest_sequence(t):
    _preflight_refusal(t, {"manifest_sequence_sha256": H(TX.canon(list(reversed(REQ_IDS))))},
                       "MANIFEST_SEQUENCE_MISMATCH")


def t08_manifest_dropped(t):
    drop_path = os.path.join(t.dir, "manifest_dropped.json")
    man = json.loads(MANIFEST_BYTES)
    man["requests"] = man["requests"][:-1]
    with open(drop_path, "wb") as f:
        f.write(TX.canon(man))
    pk = build_packet(t.dir)
    pk["pin_paths"]["manifest"] = drop_path
    pk["pins"]["manifest"] = H(open(drop_path, "rb").read())
    out = TX.ReadinessTransaction(t.dir, pk, Hooks()).run()
    t.check("hold", out["outcome"] == "HOLD")
    t.check("code", out["refusal"] == "MANIFEST_COUNT_MISMATCH")


def t09_pin_drift(t):
    pk = build_packet(t.dir)
    pk["pins"]["supplement"] = "0" * 64
    out = TX.ReadinessTransaction(t.dir, pk, Hooks()).run()
    t.check("hold", out["outcome"] == "HOLD")
    t.check("code", out["refusal"] == "PIN_DRIFT")


def t10_order_violations(t):
    pk = build_packet(t.dir)
    txn = TX.ReadinessTransaction(t.dir, pk, Hooks())
    for call, label in ((txn.call_status, "status_before_locks"),
                        (txn.adopt, "adopt_before_gate3"),
                        (txn.acquire_locks, "locks_before_preflight")):
        try:
            call()
            raise SystemExit("expected refusal: " + label)
        except TX.Refusal as r:
            t.check(label, r.code in ("ORDER_VIOLATION", "ADOPTION_NOT_REACHED"))


def t11_second_status(t):
    pk = build_packet(t.dir)
    hooks = Hooks()
    txn = TX.ReadinessTransaction(t.dir, pk, hooks)
    txn.begin(); txn.preflight(); txn.acquire_locks(); txn.verify_helper()
    txn.call_status()
    try:
        txn.call_status()
        raise SystemExit("expected STATUS_CALL_ALREADY_MADE")
    except TX.Refusal as r:
        t.check("second_call_refused", r.code == "STATUS_CALL_ALREADY_MADE")
    t.check("hook_called_once", hooks.calls["status"] == 1)


def t12_status_failure_no_retry(t):
    pk = build_packet(t.dir)
    hooks = Hooks(raw=RuntimeError("network died"))
    out = TX.ReadinessTransaction(t.dir, pk, hooks).run()
    t.check("hold", out["outcome"] == "HOLD")
    t.check("call_consumed", out["status_calls"] == 1)
    t.check("target_unchanged", tgt_hash(pk) == H(LEGACY_BYTES))
    out2 = TX.ReadinessTransaction(t.dir, pk, Hooks()).run()
    t.check("retry_impossible", out2["refusal"] == "TRANSACTION_ALREADY_CONSUMED")


def t13_gate3_fail_no_write(t):
    raw = dict(PASS_RAW, daily_usage=749)  # remaining 51 < 52
    pk = build_packet(t.dir)
    txn = TX.ReadinessTransaction(t.dir, pk, Hooks(raw=raw))
    out = txn.run()
    t.check("hold", out["outcome"] == "HOLD")
    t.check("gate3_code", out["refusal"] == "GATE3_NOT_PASS"
            and out["gate3"]["code"] == "ACCOUNT_CAPACITY_INSUFFICIENT")
    t.check("target_unchanged", tgt_hash(pk) == H(LEGACY_BYTES))
    t.check("no_backup_created", not os.path.exists(pk["backup_path"]))
    try:
        txn.adopt()
        raise SystemExit("expected ADOPTION_NOT_REACHED")
    except TX.Refusal as r:
        t.check("write_after_fail_refused", r.code == "ADOPTION_NOT_REACHED")


def t14_backup_failure(t):
    pk = build_packet(t.dir)
    out = TX.ReadinessTransaction(t.dir, pk, Hooks(fail_at={"backup"})).run()
    t.check("hold", out["outcome"] == "HOLD")
    t.check("target_unchanged", tgt_hash(pk) == H(LEGACY_BYTES))


def t15_replace_failure(t):
    pk = build_packet(t.dir)
    out = TX.ReadinessTransaction(t.dir, pk, Hooks(fail_at={"replace"})).run()
    t.check("hold", out["outcome"] == "HOLD")
    t.check("target_unchanged", tgt_hash(pk) == H(LEGACY_BYTES))
    t.check("backup_intact", H(open(pk["backup_path"], "rb").read()) == H(LEGACY_BYTES))
    t.check("no_temp_left", not os.path.exists(pk["ledger_target"] + ".tmp"))


def t16_post_write_rollback(t):
    pk = build_packet(t.dir)
    out = TX.ReadinessTransaction(t.dir, pk, Hooks(consumer_ok=False)).run()
    t.check("rolled_back", out["outcome"] == "ROLLED_BACK")
    t.check("target_restored_exactly", open(pk["ledger_target"], "rb").read() == LEGACY_BYTES)
    t.check("rollback_step_logged", any(s["step"] == "rollback" for s in out["steps"]))


def t17_scope_boundary(t):
    pk = build_packet(t.dir)
    txn = TX.ReadinessTransaction(t.dir, pk, Hooks())
    for call, label in ((txn.request_token, "token"),
                        (txn.arm_transport, "transport"),
                        (txn.call_time_series, "time_series")):
        try:
            call()
            raise SystemExit("expected NOT_IN_READINESS_SCOPE: " + label)
        except TX.Refusal as r:
            t.check("scope_" + label, r.code == "NOT_IN_READINESS_SCOPE")


def t18_card_drift(t):
    pk = build_packet(t.dir)
    out = TX.ReadinessTransaction(t.dir, pk, Hooks()).run()
    t.check("complete", out["outcome"] == "COMPLETE")
    card = json.loads(open(pk["card_path"], "rb").read())
    card["window"] = {"start": 0, "end": 0}
    with open(pk["card_path"], "wb") as f:
        f.write(TX.canon(card))
    try:
        TX.ReadinessTransaction.verify_card(pk["card_path"], pk["evidence_path"])
        raise SystemExit("expected CARD_DRIFT")
    except TX.Refusal as r:
        t.check("card_drift_refused", r.code == "CARD_DRIFT")


def t19_guards(t):
    pk = build_packet(t.dir, ledger_target=REAL_LEDGER)
    out = TX.ReadinessTransaction(t.dir, pk, Hooks()).run()
    t.check("real_target_refused", out["refusal"] == "REAL_LEDGER_TARGET_FORBIDDEN")
    t.check("real_ledger_unchanged", H(open(REAL_LEDGER, "rb").read()) == H(LEGACY_BYTES))
    pk2 = build_packet(t.dir, mode="live")
    try:
        TX.ReadinessTransaction(t.dir, pk2, Hooks())
        raise SystemExit("expected LIVE_NOT_AUTHORIZED")
    except TX.Refusal as r:
        t.check("live_mode_refused", r.code == "LIVE_NOT_AUTHORIZED_IN_CANDIDATE")
    hooks = Hooks()
    hooks.status_call = lambda: dict(PASS_RAW)  # no is_fixture marker
    try:
        TX.ReadinessTransaction(t.dir, build_packet(t.dir), hooks)
        raise SystemExit("expected FIXTURE_HOOK_REQUIRED")
    except TX.Refusal as r:
        t.check("nonfixture_hook_refused", r.code == "FIXTURE_HOOK_REQUIRED")


def t20_crash(t):
    for mode, expect in (("status", H(LEGACY_BYTES)),
                         ("postwrite", None)):
        sub = os.path.join(t.dir, mode)
        os.makedirs(sub)
        r = subprocess.run([sys.executable, os.path.join(PKG, "crash_child.py"),
                            mode, sub], capture_output=True, timeout=120)
        t.check("crash_exit42_" + mode, r.returncode == 42)
        target = os.path.join(sub, "ledger.json")
        got = H(open(target, "rb").read())
        if mode == "status":
            t.check("crash_status_target_original", got == expect)
        else:
            cand = H(open(CANDIDATE_PATH, "rb").read())
            t.check("crash_postwrite_atomic", got in (cand, H(LEGACY_BYTES)))
            t.check("crash_postwrite_backup_intact",
                    H(open(os.path.join(sub, "ledger_backup.json"), "rb").read())
                    == H(LEGACY_BYTES))
            json.loads(open(target, "rb").read())  # parses: never half-written
            t.check("crash_postwrite_parses", True)


TRIALS = [
    ("T01_happy_path_real_dry_run", t01_happy),
    ("T02_one_use_consumed", t02_one_use),
    ("T03_go_record_absent", t03_go_absent),
    ("T04_go_record_malformed", t04_go_malformed),
    ("T05_policy_digest_drift", t05_policy_digest),
    ("T06_ceiling_drift", t06_ceiling),
    ("T07_manifest_reordered", t07_manifest_sequence),
    ("T08_manifest_dropped", t08_manifest_dropped),
    ("T09_pin_drift", t09_pin_drift),
    ("T10_order_violations", t10_order_violations),
    ("T11_second_status_request", t11_second_status),
    ("T12_status_failure_no_retry", t12_status_failure_no_retry),
    ("T13_gate3_fail_no_ledger_write", t13_gate3_fail_no_write),
    ("T14_backup_failure", t14_backup_failure),
    ("T15_replace_failure", t15_replace_failure),
    ("T16_post_write_consumer_rollback", t16_post_write_rollback),
    ("T17_no_data_scope_boundary", t17_scope_boundary),
    ("T18_card_drift", t18_card_drift),
    ("T19_real_target_and_mode_guards", t19_guards),
    ("T20_crash_atomicity", t20_crash),
]


def main():
    root, out_path = sys.argv[1], sys.argv[2]
    os.makedirs(root, exist_ok=True)
    before = H(open(REAL_LEDGER, "rb").read())
    results = []
    for name, fn in TRIALS:
        t = WT(name, root)
        status = "PASS"
        try:
            fn(t)
        except AssertionError as e:
            status = "FAIL:" + str(e)
        except SystemExit as e:
            status = "FAIL:" + str(e)
        except Exception as e:  # noqa: BLE001
            status = "ERROR:%s:%s" % (type(e).__name__, e)
        results.append({"trial": name, "status": status, "checks": t.checks,
                        "n_checks": len(t.checks), "facts": t.facts})
    summary = {"task": "QF-TD-POLICY-A-LIVE-READINESS-PACKET-20261017-11",
               "suite": "readiness_transaction",
               "trials": results, "n_trials": len(results),
               "n_pass": sum(1 for r in results if r["status"] == "PASS"),
               "total_checks": sum(r["n_checks"] for r in results),
               "real_pilot_ledger_unchanged":
                   H(open(REAL_LEDGER, "rb").read()) == before}
    with open(out_path, "w") as f:
        f.write(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"n_trials": summary["n_trials"], "n_pass": summary["n_pass"],
                      "total_checks": summary["total_checks"]}))


if __name__ == "__main__":
    main()
