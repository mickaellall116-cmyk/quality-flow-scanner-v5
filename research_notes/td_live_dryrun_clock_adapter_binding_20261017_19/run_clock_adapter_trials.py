#!/usr/bin/env python3
"""-19 trial suite: live dry-run clock + adapter binding.

Runs the reproduction of the -18 false-stale against the ORIGINAL
adapter, the corrected dedicated live adapter against the same
committed -18 facts, the freshness/skew/anchor/binding HOLD set,
and the executor's adapter path+sha binding (tamper/symlink/
shadow). Offline only; all ledgers are fixture copies; the real
pilot ledger is hash-checked untouched at the end.
Output: a canonical matrix JSON (no paths, no wall times).
"""
import ast
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
NOTES = os.path.dirname(HERE)
PKG17 = os.path.join(NOTES, "td_status_query_placement_20261017_17")
RUN18 = os.path.join(NOTES, "td_live_readiness_run_20261017_18")
CANDIDATE = os.path.join(
    NOTES, "td_ledger_compat_card_binding_20261017_07",
    "candidate_credit_ledger.json")
PILOT_LEDGER = os.path.join(NOTES, "pilot_harness", "credit_ledger.json")
EVIDENCE18 = os.path.join(RUN18, "txn", "evidence.json")
VENDOR_EPOCH = 1792270863  # "2026-10-17 21:01:03" UTC
ANCHOR18 = 1792270862.669557

M = {"trials": {}, "checks_total": 0, "checks_passed": 0}


def H(b):
    return hashlib.sha256(b).hexdigest()


def check(trial, label, cond):
    t = M["trials"].setdefault(trial, {"checks": {}, "ok": True})
    t["checks"][label] = bool(cond)
    M["checks_total"] += 1
    if cond:
        M["checks_passed"] += 1
    else:
        t["ok"] = False


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fresh_dir():
    return tempfile.mkdtemp(prefix="qf19_")


def fixture_target(d):
    p = os.path.join(d, "limiter_ledger.json")
    shutil.copyfile(CANDIDATE, p)
    return p


def fixture_packet(d, **kw):
    pk = {"txn_id": "QF-TD-READINESS-LIVE-20261017-18",
          "expected_candidate_sha":
              "79ff48444d9f05c1272bfbeec2376b8065f4c22dc97b86f657e2ad15495e846b",
          "dryrun_root": os.path.join(d, "dryrun"),
          "go_record": {"record_id": "QF-TD-POLICY-A-52-CREDIT-CEILING-GO-20261017",
                        "comment_id": 6234434220}}
    pk.update(kw)
    return pk


def fixture_evidence(d, mutate=None):
    doc = json.loads(open(EVIDENCE18).read())
    if mutate:
        mutate(doc)
    p = os.path.join(d, "evidence.json")
    with open(p, "w") as f:
        f.write(json.dumps(doc))
    return p


def run_new_adapter(pk, target, ev_path):
    A = load(os.path.join(HERE, "live_dry_run_adapter.py"), "qf19_adapter")
    hook = A.make_live_dry_run_hook(pk, target)
    try:
        return ("GATES", hook(ev_path))
    except A.LiveDryRunRefusal as e:
        return ("REFUSAL", e.code)


def main():
    import datetime
    conv = datetime.datetime.utcfromtimestamp(1792224000).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    check("epoch_conversion", "true_utc_of_1792224000", conv == "2026-10-17T08:00:00Z")
    M["trials"]["epoch_conversion"]["note"] = \
        "1792224000 == 2026-10-17T08:00:00Z (runner comment claims 14:00Z; wrong)"

    # --- 1. reproduction: ORIGINAL adapter + committed -18 facts ---
    d = fresh_dir()
    old = load(os.path.join(PKG17, "r4_dry_run_adapter.py"), "qf19_old_adapter")
    facts18 = json.loads(open(EVIDENCE18).read())["facts"]
    hook = old.make_r4_dry_run_hook({"dryrun_root": os.path.join(d, "dryrun")},
                                    fixture_target(d),
                                    account_raw=facts18["api_usage"])
    gates = hook("ignored")
    check("repro_old", "gates_11_of_12", gates.count("PASS") == 11)
    check("repro_old", "gate3_fail", gates[2] == "FAIL")
    rec = json.loads(open(os.path.join(
        d, "dryrun", "dryrun", "account", "gate_receipt.json")).read())
    check("repro_old", "receipt_stale_code",
          rec["gates"][2]["code"] == "ACCOUNT_EVIDENCE_STALE")
    check("repro_old", "receipt_clock_frozen_0800",
          rec["evaluated_at"] == "2026-10-17T08:00:00Z")
    check("repro_old", "receipt_clock_mode_injected",
          rec["clock_mode"] == "injected_test")
    check("repro_old", "receipt_decision_hold", rec["decision"] == "HOLD")
    M["trials"]["repro_old"]["gates"] = gates

    # --- 2. corrected adapter + the SAME -18 facts/anchor -> 12/12 ---
    d = fresh_dir()
    out = run_new_adapter(fixture_packet(d), fixture_target(d),
                          fixture_evidence(d))
    check("new_12of12", "no_refusal", out[0] == "GATES")
    gates = out[1] if out[0] == "GATES" else []
    check("new_12of12", "gates_12_of_12", gates == ["PASS"] * 12)
    rec = json.loads(open(os.path.join(
        d, "dryrun", "live_dryrun", "account", "gate_receipt.json")).read())
    check("new_12of12", "decision_pass_dry_run",
          rec["decision"] == "PASS_DRY_RUN")
    check("new_12of12", "evaluated_at_is_anchor",
          rec["evaluated_at"] == "2026-10-17T21:01:02Z")
    M["trials"]["new_12of12"]["gates"] = gates

    # --- 3.. freshness / skew / anchor discipline ---
    def expect_refusal(trial, mutate, code, packet_kw=None):
        d = fresh_dir()
        out = run_new_adapter(fixture_packet(d, **(packet_kw or {})),
                              fixture_target(d), fixture_evidence(d, mutate))
        check(trial, "refusal_" + code, out == ("REFUSAL", code))

    expect_refusal("stale_age_7200",
                   lambda doc: doc["facts"].__setitem__(
                       "evaluated_at", VENDOR_EPOCH + 7200),
                   "EVIDENCE_STALE_BEYOND_MAX_AGE")
    expect_refusal("skew_minus61",
                   lambda doc: doc["facts"].__setitem__(
                       "evaluated_at", VENDOR_EPOCH - 61),
                   "VENDOR_FUTURE_SKEW_BEYOND_TOLERANCE")
    expect_refusal("skew_minus3600",
                   lambda doc: doc["facts"].__setitem__(
                       "evaluated_at", VENDOR_EPOCH - 3600),
                   "VENDOR_FUTURE_SKEW_BEYOND_TOLERANCE")
    expect_refusal("anchor_string",
                   lambda doc: doc["facts"].__setitem__("evaluated_at", "soon"),
                   "ANCHOR_MALFORMED")
    expect_refusal("anchor_nan",
                   lambda doc: doc["facts"].__setitem__(
                       "evaluated_at", float("nan")),
                   "ANCHOR_MALFORMED")
    expect_refusal("anchor_missing",
                   lambda doc: doc["facts"].pop("evaluated_at"),
                   "ANCHOR_MALFORMED")
    expect_refusal("txn_mismatch",
                   lambda doc: doc.__setitem__("txn_id", "QF-OTHER"),
                   "EVIDENCE_TXN_MISMATCH")
    expect_refusal("candidate_mismatch",
                   lambda doc: doc.__setitem__("candidate_sha", "0" * 64),
                   "EVIDENCE_CANDIDATE_MISMATCH")
    expect_refusal("stale_window", None, "STALE_DISPATCH_WINDOW",
                   packet_kw={"dispatch_window": {"start": 1000, "end": 2000}})

    for trial, anchor in (("boundary_age_3600", VENDOR_EPOCH + 3600),
                          ("boundary_skew_minus60", VENDOR_EPOCH - 60)):
        d = fresh_dir()
        out = run_new_adapter(
            fixture_packet(d), fixture_target(d),
            fixture_evidence(d, lambda doc, a=anchor: doc["facts"]
                             .__setitem__("evaluated_at", a)))
        check(trial, "gates_12_of_12",
              out[0] == "GATES" and out[1] == ["PASS"] * 12)

    # --- 4. executor adapter binding (path + sha, tamper/symlink/shadow) ---
    X = load(os.path.join(HERE, "live_readiness_executor_r4.py"), "qf19_exec_r4")
    mod = X._load_live_adapter()
    check("binding_ok", "module_origin_is_pinned_path",
          os.path.abspath(mod.__file__) == os.path.abspath(X.ADAPTER_PATH))
    check("binding_ok", "adapter_pin_matches_file",
          X._sha256_file(X.ADAPTER_PATH) == X.ADAPTER_SHA256)
    check("binding_ok", "executor_source_sha_fn",
          X.executor_source_sha() == X._sha256_file(os.path.abspath(X.__file__)))

    d = fresh_dir()
    tampered = os.path.join(d, "live_dry_run_adapter.py")
    b = open(X.ADAPTER_PATH, "rb").read()
    open(tampered, "wb").write(b[:-1] + bytes([b[-1] ^ 1]))
    saved = X.ADAPTER_PATH
    try:
        X.ADAPTER_PATH = tampered
        try:
            X._load_live_adapter()
            check("binding_tamper", "refused", False)
        except X.Refusal as e:
            check("binding_tamper", "refused", e.code == "ADAPTER_PIN_MISMATCH")
        link = os.path.join(d, "link_adapter.py")
        os.symlink(saved, link)
        X.ADAPTER_PATH = link
        try:
            X._load_live_adapter()
            check("binding_symlink", "refused", False)
        except X.Refusal as e:
            check("binding_symlink", "refused", e.code == "ADAPTER_PATH_REFUSED")
    finally:
        X.ADAPTER_PATH = saved

    d = fresh_dir()
    decoy = os.path.join(d, "live_dry_run_adapter.py")
    open(decoy, "w").write("DECOY = True\n")
    sys.path.insert(0, d)
    try:
        mod = X._load_live_adapter()
        check("binding_shadow", "pinned_origin_despite_shadow",
              os.path.abspath(mod.__file__) == os.path.abspath(saved)
              and not hasattr(mod, "DECOY"))
    finally:
        sys.path.pop(0)

    # --- 5. structural audit: live adapter never touches the harness ---
    tree = ast.parse(open(os.path.join(HERE, "live_dry_run_adapter.py")).read())
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            imported.add(n.module or "")
    check("audit_no_harness", "no_trial_harness_import",
          not any("dispatch_gate_trials" in i for i in imported))
    check("audit_no_harness", "no_trial_or_base_evidence_names",
          "Trial" not in {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
          and "base_evidence" not in
          {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)})

    # --- 6. real pilot ledger untouched ---
    check("scope", "pilot_ledger_byte_identical",
          H(open(PILOT_LEDGER, "rb").read())
          == "7e5ccef0e5fd7e2faa744c8fe7ee646c3162fa4f72fc4a9a85317d52b5d890ed")

    M["summary"] = {"trials": len(M["trials"]),
                    "checks": M["checks_total"],
                    "passed": M["checks_passed"],
                    "all_ok": M["checks_passed"] == M["checks_total"]}
    out = sys.argv[1]
    with open(out, "w") as f:
        f.write(json.dumps(M, sort_keys=True, indent=1))
    print(json.dumps(M["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
