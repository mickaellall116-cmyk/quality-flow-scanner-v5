#!/usr/bin/env python3
"""QF-TD-LIVE-CLEARANCE-PATH-BINDING-20261017-15 r1 trial runner.

Proves OFFLINE, against live_readiness_executor_r2.py:
- clearance schema v2 binding the canonical live paths + packet
  digest: admission passes exactly for the canonical fixture and
  refuses decoy target / workdir drift / edited clearance / packet
  drift / path-set mismatch BEFORE marker creation, with zero
  status consumption;
- path hygiene: symlink target / candidate / workdir ancestor /
  lease path refused at admission;
- target pathname/inode/realpath identity revalidated under lock
  immediately before the status boundary and again before mutation:
  symlink swap and inode drift HOLD without overwrite, with the
  status counter at 0 for pre-status drift;
- the executor-side final URL boundary: malicious helper returns
  (host confusion, alternate path, redirect-shaped, userinfo, port,
  extra query, http scheme, fragment) produce ZERO transport
  invocations; a well-formed credential query passes.

Usage: python3 run_path_binding_trials.py <trials_root> <matrix_out>
"""
import datetime
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
NOTES = os.path.dirname(HERE)
REPO = os.path.dirname(NOTES)
import live_readiness_executor_r2 as EX  # noqa: E402
from r4_dry_run_adapter import make_r4_dry_run_hook  # noqa: E402

H = EX.H
canon = EX.canon
Refusal = EX.Refusal
NOW = 1792224000  # 2026-10-17T14:00:00Z (the accepted -11 fixture clock)


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
VARIANTS = os.path.join(HERE, "helper_variants")

PASS_RAW = {"timestamp": fmt(NOW - 60), "current_usage": 0, "plan_limit": 8,
            "daily_usage": 100, "plan_daily_limit": 800,
            "plan_category": "basic"}


class Spy:
    def __init__(self, raw=None, side_effect=None):
        self.calls = []
        self.raw = PASS_RAW if raw is None else raw
        self.side_effect = side_effect

    def http_get(self, url):
        from urllib.parse import urlparse
        u = urlparse(url)
        self.calls.append({"host": u.hostname, "path": u.path,
                           "has_query": bool(u.query)})
        if self.side_effect is not None:
            self.side_effect()
        return 200, canon(self.raw)


RESULTS = []


def record(name, checks):
    RESULTS.append({"trial": name, "checks": checks,
                    "ok": all(checks.values())})
    print(("PASS " if all(checks.values()) else "FAIL ") + name, flush=True)


def read(path):
    with open(path, "rb") as f:
        return f.read()


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


def make_clearance(pk, path):
    """Build a schema-v2 clearance exactly binding pk's identity."""
    live_pk = dict(pk, mode="live")
    c = {
        "schema": "QF-TD-READINESS-CLEARANCE",
        "schema_version": 2,
        "txn_id": pk["txn_id"],
        "executor_sha256": EX.executor_source_sha(),
        "gate_sha256": EX.PIN_R4_GATE,
        "policy_digest": EX.PIN_POLICY_A_DIGEST,
        "candidate_sha256": pk["expected_candidate_sha"],
        "legacy_ledger_sha256": pk["expected_original_sha"],
        "ceiling_credits": 52,
        "scope": "READINESS_ONLY_ONE_API_USAGE",
        "target_path": os.path.abspath(pk["target_path"]),
        "target_realpath": os.path.realpath(pk["target_path"]),
        "workdir": os.path.abspath(pk["workdir"]),
        "candidate_path": os.path.abspath(pk["candidate_path"]),
        "dryrun_root": os.path.abspath(pk["dryrun_root"]),
        "packet_digest": H(canon(EX._packet_identity(live_pk))),
    }
    raw = canon(c)
    with open(path, "wb") as f:
        f.write(raw)
    return H(raw)


def admission_outcome(pk):
    """Run live admission only; return the Refusal code or 'OK'."""
    ex = EX.LiveReadinessExecutor(pk)
    try:
        ex.validate_live_admission()
        return "OK"
    except Refusal as e:
        return e.code


def main():
    troot, matrix_out = sys.argv[1], sys.argv[2]
    os.makedirs(troot, exist_ok=True)

    # q01 canonical live-path fixture: admission passes, touches nothing
    root = os.path.join(troot, "q01"); target = setup(root)
    pk = base_packet(root, "QF15-Q01", mode="live")
    clr = os.path.join(root, "clearance.json")
    pin = make_clearance(pk, clr)
    pk["clearance_path"] = clr; pk["clearance_sha256"] = pin
    code = admission_outcome(pk)
    record("q01_admission_canonical_passes_touches_nothing", {
        "admission_ok": code == "OK",
        "no_marker": not os.path.exists(pk["workdir"]),
        "target_untouched": read(target) == LEGACY,
        "no_lease_or_lock": not os.path.exists(target + ".dispatch_lease")
        and not os.path.exists(target + ".lock"),
    })

    # q02 byte-identical decoy target refused before marker/status
    root = os.path.join(troot, "q02"); target = setup(root)
    decoy_dir = os.path.join(root, "decoy"); os.makedirs(decoy_dir)
    decoy = os.path.join(decoy_dir, "ledger.json")
    with open(decoy, "wb") as f:
        f.write(LEGACY)
    pk = base_packet(root, "QF15-Q02", mode="live")
    clr = os.path.join(root, "clearance.json")
    pin = make_clearance(pk, clr)  # binds the CANONICAL target
    pk2 = dict(pk, target_path=decoy, clearance_path=clr,
               clearance_sha256=pin)
    code = admission_outcome(pk2)
    record("q02_decoy_target_refused", {
        "refused_binding": code == "CLEARANCE_BINDING_MISMATCH",
        "no_marker": not os.path.exists(pk2["workdir"]),
        "decoy_untouched": read(decoy) == LEGACY,
        "canonical_untouched": read(target) == LEGACY,
    })

    # q03 packet workdir drift refused before marker creation
    root = os.path.join(troot, "q03"); target = setup(root)
    pk = base_packet(root, "QF15-Q03", mode="live")
    clr = os.path.join(root, "clearance.json")
    pin = make_clearance(pk, clr)
    drift_wd = os.path.join(root, "elsewhere")
    pk2 = dict(pk, workdir=drift_wd, clearance_path=clr,
               clearance_sha256=pin)
    code = admission_outcome(pk2)
    record("q03_workdir_drift_refused_before_marker", {
        "refused_binding": code == "CLEARANCE_BINDING_MISMATCH",
        "drift_workdir_not_created": not os.path.exists(drift_wd),
        "bound_workdir_not_created": not os.path.exists(pk["workdir"]),
    })

    # q04 clearance path edited: stale pin -> PIN_MISMATCH; re-pinned
    # edit -> BINDING_MISMATCH (the hash alone cannot launder a path)
    root = os.path.join(troot, "q04"); target = setup(root)
    pk = base_packet(root, "QF15-Q04", mode="live")
    clr = os.path.join(root, "clearance.json")
    pin = make_clearance(pk, clr)
    edited = json.loads(read(clr).decode())
    edited["target_path"] = os.path.join(root, "other.json")
    with open(clr, "wb") as f:
        f.write(canon(edited))
    pk_stale = dict(pk, clearance_path=clr, clearance_sha256=pin)
    code_stale = admission_outcome(pk_stale)
    pk_repinned = dict(pk, clearance_path=clr,
                       clearance_sha256=H(read(clr)))
    code_repinned = admission_outcome(pk_repinned)
    record("q04_edited_clearance_refused", {
        "stale_pin_refused": code_stale == "CLEARANCE_PIN_MISMATCH",
        "repinned_edit_refused": code_repinned == "CLEARANCE_BINDING_MISMATCH",
        "no_marker": not os.path.exists(pk["workdir"]),
        "target_untouched": read(target) == LEGACY,
    })

    # q05 packet field drift after clearance issuance (dryrun_root)
    root = os.path.join(troot, "q05"); target = setup(root)
    pk = base_packet(root, "QF15-Q05", mode="live")
    clr = os.path.join(root, "clearance.json")
    pin = make_clearance(pk, clr)
    pk2 = dict(pk, dryrun_root=os.path.join(root, "dryrun2"),
               clearance_path=clr, clearance_sha256=pin)
    code = admission_outcome(pk2)
    record("q05_packet_digest_drift_refused", {
        "refused_binding": code == "CLEARANCE_BINDING_MISMATCH",
        "no_marker": not os.path.exists(pk["workdir"]),
    })

    # q06 symlink target refused at admission (hygiene)
    root = os.path.join(troot, "q06"); real = setup(root)
    link = os.path.join(root, "link_ledger.json")
    os.symlink(real, link)
    pk = base_packet(root, "QF15-Q06", mode="live", target_path=link)
    clr = os.path.join(root, "clearance.json")
    pin = make_clearance(pk, clr)
    pk["clearance_path"] = clr; pk["clearance_sha256"] = pin
    code = admission_outcome(pk)
    record("q06_symlink_target_refused", {
        "refused_hygiene": code == "PATH_HYGIENE_REFUSED",
        "no_marker": not os.path.exists(pk["workdir"]),
        "real_untouched": read(real) == LEGACY,
    })

    # q07 symlink candidate refused at admission (hygiene)
    root = os.path.join(troot, "q07"); target = setup(root)
    cand_link = os.path.join(root, "cand_link.json")
    os.symlink(CAND_PATH, cand_link)
    pk = base_packet(root, "QF15-Q07", mode="live",
                     candidate_path=cand_link)
    clr = os.path.join(root, "clearance.json")
    pin = make_clearance(pk, clr)
    pk["clearance_path"] = clr; pk["clearance_sha256"] = pin
    code = admission_outcome(pk)
    record("q07_symlink_candidate_refused", {
        "refused_hygiene": code == "PATH_HYGIENE_REFUSED",
        "no_marker": not os.path.exists(pk["workdir"]),
    })

    # q08 symlinked workdir ancestor refused at admission (hygiene)
    root = os.path.join(troot, "q08"); target = setup(root)
    real_wd_parent = os.path.join(root, "realparent"); os.makedirs(real_wd_parent)
    link_parent = os.path.join(root, "linkparent")
    os.symlink(real_wd_parent, link_parent)
    pk = base_packet(root, "QF15-Q08", mode="live",
                     workdir=os.path.join(link_parent, "txn"))
    clr = os.path.join(root, "clearance.json")
    pin = make_clearance(pk, clr)
    pk["clearance_path"] = clr; pk["clearance_sha256"] = pin
    code = admission_outcome(pk)
    record("q08_symlink_workdir_ancestor_refused", {
        "refused_hygiene": code == "PATH_HYGIENE_REFUSED",
        "no_marker": not os.path.exists(os.path.join(real_wd_parent, "txn")),
    })

    # q09 symlink lease path refused at admission (hygiene)
    root = os.path.join(troot, "q09"); target = setup(root)
    os.symlink(target, target + ".dispatch_lease")
    pk = base_packet(root, "QF15-Q09", mode="live")
    clr = os.path.join(root, "clearance.json")
    pin = make_clearance(pk, clr)
    pk["clearance_path"] = clr; pk["clearance_sha256"] = pin
    code = admission_outcome(pk)
    record("q09_symlink_lease_path_refused", {
        "refused_hygiene": code == "PATH_HYGIENE_REFUSED",
        "no_marker": not os.path.exists(pk["workdir"]),
        "target_untouched": read(target) == LEGACY,
    })

    # q10 exact canonical paths, full offline run passes ONCE
    root = os.path.join(troot, "q10"); target = setup(root)
    pk = base_packet(root, "QF15-Q10")
    spy = Spy()
    hk = base_hooks(spy, dry_run=make_r4_dry_run_hook(pk, target,
                                                      account_raw=PASS_RAW))
    ex = EX.LiveReadinessExecutor(pk, hk)
    out = ex.run()
    rec = EX.recover_live(pk["workdir"], target)
    record("q10_canonical_paths_full_run_passes_once", {
        "complete": out.get("outcome") == "COMPLETE",
        "one_status_call": len(spy.calls) == 1,
        "target_is_candidate": read(target) == CAND,
        "recovery_adopted_verified": rec["classification"] == "ADOPTED_VERIFIED",
        "recovery_zero_status_calls": rec["status_calls_during_recovery"] == 0,
    })

    # q11 symlink swap BEFORE status: HOLD, status counter 0, no overwrite
    root = os.path.join(troot, "q11"); target = setup(root)
    decoy = os.path.join(root, "decoy.json")
    with open(decoy, "wb") as f:
        f.write(LEGACY)

    def swap_to_symlink():
        os.remove(target)
        os.symlink(decoy, target)

    pk = base_packet(root, "QF15-Q11")
    spy = Spy()
    hk = base_hooks(spy, pre_status=swap_to_symlink)
    ex = EX.LiveReadinessExecutor(pk, hk)
    out = ex.run()
    journal = json.loads(read(pk["workdir"] + "/journal.json").decode())
    record("q11_symlink_swap_before_status", {
        "hold_drift": out.get("outcome") == "HOLD"
        and out.get("reason") == "TARGET_IDENTITY_DRIFT",
        "zero_transport": len(spy.calls) == 0,
        "journal_status_calls_zero": journal.get("status_calls") == 0,
        "decoy_not_overwritten": read(decoy) == LEGACY,
        "path_still_symlink": os.path.islink(target),
    })

    # q12 inode drift BEFORE status (identical bytes, new inode)
    root = os.path.join(troot, "q12"); target = setup(root)
    tmp_swap = os.path.join(root, "swap.bin")
    with open(tmp_swap, "wb") as f:
        f.write(LEGACY)

    def swap_inode():
        os.replace(tmp_swap, target)

    pk = base_packet(root, "QF15-Q12")
    spy = Spy()
    hk = base_hooks(spy, pre_status=swap_inode)
    ex = EX.LiveReadinessExecutor(pk, hk)
    out = ex.run()
    journal = json.loads(read(pk["workdir"] + "/journal.json").decode())
    record("q12_inode_drift_before_status", {
        "hold_drift": out.get("outcome") == "HOLD"
        and out.get("reason") == "TARGET_IDENTITY_DRIFT",
        "zero_transport": len(spy.calls) == 0,
        "journal_status_calls_zero": journal.get("status_calls") == 0,
        "target_bytes_intact": read(target) == LEGACY,
    })

    # q13 inode drift DURING status: caught before mutation, no adoption
    root = os.path.join(troot, "q13"); target = setup(root)
    tmp_swap = os.path.join(root, "swap.bin")
    with open(tmp_swap, "wb") as f:
        f.write(LEGACY)
    pk = base_packet(root, "QF15-Q13")
    spy = Spy(side_effect=lambda: os.replace(tmp_swap, target))
    hk = base_hooks(spy)
    ex = EX.LiveReadinessExecutor(pk, hk)
    out = ex.run()
    record("q13_inode_drift_before_mutation", {
        "hold_drift": out.get("outcome") == "HOLD"
        and out.get("reason") == "TARGET_IDENTITY_DRIFT",
        "one_transport": len(spy.calls) == 1,
        "no_adoption": read(target) == LEGACY,
    })

    # q14 symlink swap DURING status: caught before mutation, decoy safe
    root = os.path.join(troot, "q14"); target = setup(root)
    decoy = os.path.join(root, "decoy.json")
    with open(decoy, "wb") as f:
        f.write(LEGACY)

    def swap_link_during():
        os.remove(target)
        os.symlink(decoy, target)

    pk = base_packet(root, "QF15-Q14")
    spy = Spy(side_effect=swap_link_during)
    hk = base_hooks(spy)
    ex = EX.LiveReadinessExecutor(pk, hk)
    out = ex.run()
    record("q14_symlink_swap_before_mutation", {
        "hold": out.get("outcome") in ("HOLD", "HOLD_MANUAL"),
        "decoy_not_overwritten": read(decoy) == LEGACY,
        "no_adoption_through_link": read(decoy) != CAND,
    })

    # q15-q22 URL boundary: malicious helper returns -> zero transport
    url_cases = ["host_confusion", "alt_path", "redirect_shaped",
                 "userinfo", "port", "extra_query", "http_scheme",
                 "fragment"]
    for i, name in enumerate(url_cases):
        root = os.path.join(troot, "q%02d" % (15 + i)); target = setup(root)
        vpath = os.path.join(VARIANTS, name + ".py")
        pk = base_packet(root, "QF15-Q%02d" % (15 + i),
                         helper={"path": vpath,
                                 "sha256": EX._sha256_file(vpath)})
        spy = Spy()
        hk = base_hooks(spy)
        ex = EX.LiveReadinessExecutor(pk, hk)
        out = ex.run()
        record("q%02d_url_boundary_%s" % (15 + i, name), {
            "hold_url_boundary": out.get("outcome") == "HOLD"
            and out.get("reason") == "STATUS_URL_BOUNDARY",
            "zero_transport_invocations": len(spy.calls) == 0,
            "boundary_zero_invocations": ex.boundary is not None
            and ex.boundary.invocations == 0,
            "target_untouched": read(target) == LEGACY,
        })

    # q23 well-formed credential query passes the boundary
    root = os.path.join(troot, "q23"); target = setup(root)
    vpath = os.path.join(VARIANTS, "good_token.py")
    pk = base_packet(root, "QF15-Q23",
                     helper={"path": vpath,
                             "sha256": EX._sha256_file(vpath)})
    spy = Spy()
    hk = base_hooks(spy)
    ex = EX.LiveReadinessExecutor(pk, hk)
    out = ex.run()
    record("q23_url_good_token_passes", {
        "complete": out.get("outcome") == "COMPLETE",
        "one_transport": len(spy.calls) == 1,
        "transport_path": spy.calls and spy.calls[0]["path"] == "/api_usage",
        "target_is_candidate": read(target) == CAND,
    })

    matrix = {"task": "QF-TD-LIVE-CLEARANCE-PATH-BINDING-20261017-15 r1",
              "trials": RESULTS,
              "all_ok": all(r["ok"] for r in RESULTS),
              "n_trials": len(RESULTS),
              "n_checks": sum(len(r["checks"]) for r in RESULTS),
              "n_checks_ok": sum(sum(1 for v in r["checks"].values() if v)
                                 for r in RESULTS)}
    with open(matrix_out, "w") as f:
        f.write(json.dumps(matrix, indent=1, sort_keys=True))
    print("matrix:", matrix["n_trials"], "trials,",
          matrix["n_checks_ok"], "/", matrix["n_checks"], "checks,",
          "ALL OK" if matrix["all_ok"] else "FAILURES PRESENT")
    return 0 if matrix["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
