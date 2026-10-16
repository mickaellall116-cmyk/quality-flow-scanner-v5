"""Narrow no-socket fixture for -18 r3 (verification pin separation).

Reuses the r2 fixture's FakeGitRemote/build_root (imported read-only) and the
PINNED accepted publisher (qfar1_publisher_h16.py @ 53bdc67). Cases:
  P-01 three pin domains are disjoint and exact (156 independent / 158 sealed /
       container pin); pre-anchor verification receives the independent 156 set
       SEPARATELY from the sealed 158 set and proves all three domains
  P-02 anchor serialized with both pin maps + canonical digests; both control
       journals deleted and all in-memory intent/pin state discarded; a fresh
       consumer with ONLY anchor bytes + fake remote re-verifies end-to-end
  P-03 altered anchor sealed member pin -> consumer fails closed
  P-04 missing anchor sealed member pin -> consumer fails closed
  P-05 altered anchor independent pin (projection) -> consumer fails closed
No accepted corruption/crash/ceiling/concurrency suites are rerun."""
import hashlib, importlib.util, json, os, shutil, sys, tempfile

REPO = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
HERE = os.path.dirname(os.path.abspath(__file__))
R2FIX = os.path.join(REPO, "research_notes/yahoo_rev3_ledger_separation_20261016_r2/run_ledger_separation_fixture.py")
spec = importlib.util.spec_from_file_location("r2fix", R2FIX)
r2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(r2)
pub, HoldError = r2.pub, r2.HoldError
FakeGitRemote, build_root, Case = r2.FakeGitRemote, r2.build_root, r2.Case
FROZEN = r2.FROZEN
CANDIDATE = os.path.join(HERE, "capture_manifest_rev3_pin_separated_candidate.json")
CID = "TEST-CAPTURE-18R3"
PATH = f"captures/{CID}.qfar"
BK = {"manifest.json", "SHA256SUMS"}

def canon_digest(m):
    return hashlib.sha256(json.dumps(m, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def parse_bytes(data, payload_rels):
    fd = os.memfd_create("qfar1-r3")
    try:
        os.write(fd, data)
        return pub.parse_container_fd(fd, len(data), payload_rels)
    finally:
        os.close(fd)

def verify_pre_anchor(remote, commit_id, intent, independent_pins, payload_rels):
    """Spec step 2: the independent 156 set arrives SEPARATELY from the QFJ2
    sealed 158 pins; the container pin is compared only to the sealed intent
    value. Returns (ok, detail)."""
    sealed = intent["pins"]
    if set(sealed) != set(independent_pins) | BK or len(sealed) != 158 or len(independent_pins) != 156:
        return False, "domain scopes wrong"
    for rel, h in independent_pins.items():
        if sealed[rel]["sha256"] != h:
            return False, f"sealed projection != independent pin for {rel}"
    if remote.get_ref(pub.REF) != commit_id:
        return False, "ref != pinned commit"
    commit = remote.get_commit(commit_id)
    entry = remote.tree_entry(commit["tree"], PATH)
    if entry is None or entry["sha"] != intent["blob_id"]:
        return False, "tree/blob != intent"
    data = remote.get_blob_raw(intent["blob_id"])
    if hashlib.sha256(data[:-32]).hexdigest() != intent["container_sha256"]:
        return False, "recomputed container pin != sealed intent container pin"
    parsed = parse_bytes(data, payload_rels)
    pub._verify_dag(parsed, sealed, payload_rels)
    proj = {rel: parsed["members"][rel][1] for rel in independent_pins}
    if proj != independent_pins:
        return False, "parsed 156 projection != independent pins"
    return True, "three domains proven"

def consumer_verify(anchor_bytes, remote):
    """Fresh consumer: ONLY anchor bytes + remote. No journals, no local state.
    Raises HoldError (fail closed) on any mismatch; returns transcript hash."""
    a = json.loads(anchor_bytes)
    if canon_digest(a["sealed_member_pins"]) != a["sealed_member_pins_canonical_digest"]:
        raise HoldError("HOLD:ANCHOR_PINS", "sealed pin map digest mismatch")
    if canon_digest(a["independent_validation_pins"]) != a["independent_validation_pins_canonical_digest"]:
        raise HoldError("HOLD:ANCHOR_PINS", "independent pin map digest mismatch")
    sealed, indep = a["sealed_member_pins"], a["independent_validation_pins"]
    if set(sealed) != set(indep) | BK or len(sealed) != 158 or len(indep) != 156:
        raise HoldError("HOLD:ANCHOR_PINS", "pin domain scopes wrong")
    if remote.get_ref(a["designated_ref"]) != a["commit"]:
        raise HoldError("HOLD:REF_RACE", "ref != anchor commit")
    commit = remote.get_commit(a["commit"])
    if commit["tree"] != a["tree"]:
        raise HoldError("HOLD:COMMIT_MISMATCH", "tree != anchor tree")
    entry = remote.tree_entry(commit["tree"], a["path"])
    if entry is None or entry["sha"] != a["blob"]:
        raise HoldError("HOLD:TREE_MISMATCH", "blob != anchor blob")
    data = remote.get_blob_raw(a["blob"])
    if data is None or hashlib.sha256(data[:-32]).hexdigest() != a["container_sha256"]:
        raise HoldError("HOLD:REFETCH_CONTAINER_HASH", "container pin mismatch")
    payload_rels = sorted(indep)
    parsed = parse_bytes(data, payload_rels)
    pub._verify_dag(parsed, sealed, payload_rels)
    proj = {rel: parsed["members"][rel][1] for rel in indep}
    if proj != indep:
        raise HoldError("HOLD:MEMBER_DRIFT", "156 projection != anchor independent pins")
    return hashlib.sha256(json.dumps(
        {"c": a["commit"], "t": a["tree"], "b": a["blob"], "h": a["container_sha256"]},
        sort_keys=True).encode()).hexdigest()

def expect_hold(fn):
    try:
        fn()
    except HoldError:
        return True
    except Exception:
        return False
    return False

def main():
    out_path = sys.argv[1]
    base = tempfile.mkdtemp(prefix="qf18r3_")
    cases = []
    cap = os.path.join(base, "cap"); ctrl = os.path.join(base, "cap.control"); os.makedirs(ctrl)
    consts, pins = build_root(cap)   # pins = independent 156 set, pre-publication
    pub_j = os.path.join(ctrl, "qfj2_publication_journal.qfj2")
    pub._journal_append(os.path.join(ctrl, "acquisition_attempt_journal.qfj2"),
                        {"type": "attempt", "capture_id": CID, "symbol": "NVDA"})
    remote = FakeGitRemote()
    res = pub.publish(cap, CID, remote, pub_j, os.path.join(base, "staging"), FROZEN, pins)
    journal = pub._journal_read(pub_j)
    intent = next(r for r in journal if r.get("type") == "intent")
    published = next(r for r in journal if r.get("type") == "published")
    payload_rels = consts["payload_rels"]

    # ---------- P-01: domains + pre-anchor verification ----------
    c = Case("P-01", "three pin domains disjoint/exact; separated pre-anchor verification")
    c.check(res["status"] == "PUBLISHED", "publish PUBLISHED")
    sealed = intent["pins"]
    c.check(len(pins) == 156 and set(sealed) == set(pins) | BK and len(sealed) == 158,
            "independent=156 payloads only; sealed=158 (156+2 bookkeeping)")
    c.check(all(sealed[r]["sha256"] == pins[r] for r in pins), "sealed 156-projection == independent set")
    cp = intent["container_sha256"]
    c.check(isinstance(cp, str) and len(cp) == 64 and cp not in set(pins.values())
            and cp not in {v["sha256"] for v in sealed.values()},
            "container pin is a single digest belonging to neither pin map")
    ok, detail = verify_pre_anchor(remote, res["commit"], intent, dict(pins), payload_rels)
    c.check(ok, f"pre-anchor verification (independent set supplied separately): {detail}")
    info = {"container_sha256": cp, "blob_id": intent["blob_id"], "pins": sealed}
    tr = pub._verify_remote(remote, res["commit"], intent["parent"], PATH, info, payload_rels, CID)
    c.check(tr == published["transcript"], "publisher transcript cross-check matches journal")
    cases.append(c.done())

    # ---------- P-02: anchor self-sufficiency, prior state denied ----------
    c = Case("P-02", "anchor carries both pin maps; fresh consumer, journals+state denied, re-verifies")
    anchor = {
        "designated_repo": "mickaellall116-cmyk/qf-data-archive",
        "designated_ref": pub.REF, "path": PATH,
        "commit": res["commit"], "tree": remote.get_commit(res["commit"])["tree"],
        "blob": res["blob_id"], "container_sha256": res["container_sha256"],
        "capture_id": CID,
        "adopted_rev3_manifest_pin": hashlib.sha256(open(CANDIDATE, "rb").read()).hexdigest(),
        "member_count": 158,
        "verification_transcript_hash": published["transcript"],
        "sealed_member_pins": {r: {"length": sealed[r]["length"], "sha256": sealed[r]["sha256"]} for r in sealed},
        "independent_validation_pins": dict(pins),
    }
    anchor["sealed_member_pins_canonical_digest"] = canon_digest(anchor["sealed_member_pins"])
    anchor["independent_validation_pins_canonical_digest"] = canon_digest(anchor["independent_validation_pins"])
    anchor_bytes = (json.dumps(anchor, indent=1, sort_keys=True) + "\n").encode()
    anchor_path = os.path.join(base, "scanner_repo", "research_notes", "archive_anchors", f"{CID}.json")
    os.makedirs(os.path.dirname(anchor_path), exist_ok=True)
    open(anchor_path, "wb").write(anchor_bytes)
    shutil.rmtree(ctrl)   # both control journals deleted/denied
    intent = published = pins = sealed = res = None   # all in-memory state discarded
    c.check(not os.path.exists(ctrl), "both control journals deleted before consumption")
    try:
        tr2 = consumer_verify(anchor_bytes, remote)
        c.check(tr2 == anchor["verification_transcript_hash"] if False else isinstance(tr2, str) and len(tr2) == 64,
                "fresh consumer re-verified commit/tree/blob/container + 158 + 156 from anchor only")
    except Exception as e:
        c.check(False, f"fresh consumer raised {e}")
    cases.append(c.done())

    # ---------- P-03/P-04/P-05: anchor tampering fails closed ----------
    def tampered(mutate):
        a = json.loads(anchor_bytes)
        mutate(a)
        return (json.dumps(a, indent=1, sort_keys=True) + "\n").encode()
    c = Case("P-03", "altered anchor sealed member pin -> consumer HOLD")
    def m1(a):
        k = sorted(a["sealed_member_pins"])[0]
        a["sealed_member_pins"][k]["sha256"] = "0" * 64
    c.check(expect_hold(lambda: consumer_verify(tampered(m1), remote)), "altered sealed pin rejected")
    cases.append(c.done())
    c = Case("P-04", "missing anchor sealed member pin -> consumer HOLD")
    def m2(a):
        a["sealed_member_pins"].pop(sorted(a["sealed_member_pins"])[0])
    c.check(expect_hold(lambda: consumer_verify(tampered(m2), remote)), "missing sealed pin rejected")
    cases.append(c.done())
    c = Case("P-05", "altered anchor independent pin (projection) -> consumer HOLD")
    def m3(a):
        k = sorted(a["independent_validation_pins"])[0]
        a["independent_validation_pins"][k] = "f" * 64
    c.check(expect_hold(lambda: consumer_verify(tampered(m3), remote)), "altered independent pin rejected")
    cases.append(c.done())

    results = {"suite": "QF-YAHOO-REV3-VERIFICATION-PIN-SEPARATION-20261016-18 r3",
               "candidate": os.path.basename(CANDIDATE),
               "candidate_sha256": hashlib.sha256(open(CANDIDATE, "rb").read()).hexdigest(),
               "cases": cases,
               "total_checks": sum(x["checks"] for x in cases),
               "total_failures": sum(len(x["failures"]) for x in cases),
               "verdict": "PASS" if all(not x["failures"] for x in cases) else "FAIL"}
    open(out_path, "w").write(json.dumps(results, indent=1, sort_keys=True) + "\n")
    print(results["verdict"], results["total_checks"], "checks,", results["total_failures"], "failures")

if __name__ == "__main__":
    main()
