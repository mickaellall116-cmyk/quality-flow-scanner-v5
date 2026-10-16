"""Narrow no-socket compatibility fixture for -18 r2 (ledger separation).

Uses the PINNED accepted publisher (qfar1_publisher_h16.py @ 53bdc67,
imported read-only) against a local fake Git Data remote. Cases:
  L-01 correct 156-member synthetic root, both journals in the sibling
       control directory outside cap_dir -> census/build/publish PASS
  L-02 acquisition_attempt_journal inside the capture root -> HOLD:MEMBERSHIP
  L-03 qfj2_publication_journal inside the capture root -> HOLD:MEMBERSHIP
  L-04 pre-anchor remote verification succeeds from the sealed container /
       QFJ2 intent / independent pins, with NO anchor in existence
  L-05 the public anchor is emitted only after verification, and a later
       consumer starting from the anchor re-verifies commit/tree/blob/
       container/members
No corruption/crash/ceiling/concurrency suites are rerun (accepted pins).
"""
import base64
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile

REPO = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
PUB_PATH = os.path.join(REPO, "research_notes/yahoo_qfar1_journal_header_auth_20261016/qfar1_publisher_h16.py")
FROZEN = os.path.join(REPO, "research_notes/yahoo_clean_capture_preflight_20261015/capture_manifest.json")
CANDIDATE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "capture_manifest_rev3_ledger_separated_candidate.json")
CID = "TEST-CAPTURE-18R2"
PATH = f"captures/{CID}.qfar"

spec = importlib.util.spec_from_file_location("pub16", PUB_PATH)
pub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)
HoldError = pub.HoldError


def _git_id(kind, body):
    return hashlib.sha1(b"%s %d\x00" % (kind.encode(), len(body)) + body).hexdigest()


class FakeGitRemote:
    """No-socket Git Data API model (pattern per the -13 fixture, faults removed)."""

    def __init__(self):
        self.private, self.owner, self.name = True, pub.DESIGNATED_OWNER, pub.DESIGNATED_REPO
        self.blobs, self.trees, self.commits, self.refs = {}, {}, {}, {}

    def get_repo(self):
        return {"private": self.private, "owner": self.owner, "name": self.name}

    def get_ref(self, ref):
        return self.refs.get(ref)

    def create_ref(self, ref, sha):
        if ref in self.refs:
            raise pub._ApiError(422, "reference already exists")
        self.refs[ref] = sha
        return {"ref": ref, "sha": sha}

    def update_ref(self, ref, sha, force=False):
        if ref not in self.refs:
            raise pub._ApiError(422, "reference does not exist")
        cur = self.refs[ref]
        if not force and cur not in self._ancestors(sha):
            raise pub._ApiError(422, "not fast-forward")
        self.refs[ref] = sha
        return {"ref": ref, "sha": sha}

    def _ancestors(self, sha):
        seen, stack = set(), [sha]
        while stack:
            c = stack.pop()
            if c in seen or c not in self.commits:
                continue
            seen.add(c)
            stack.extend(self.commits[c]["parents"])
        return seen

    def create_blob(self, content_b64, encoding):
        data = base64.b64decode(content_b64)
        bid = _git_id("blob", data)
        self.blobs[bid] = data
        return {"sha": bid}

    def get_blob_raw(self, sha):
        return self.blobs[sha]

    def get_blob_json(self, sha):
        data = self.blobs[sha]
        b64 = base64.b64encode(data).decode()
        wrapped = "\n".join(b64[i:i + 60] for i in range(0, len(b64), 60))
        return {"content": wrapped, "encoding": "base64", "size": len(data)}

    def create_tree(self, base_tree, entries):
        tree = dict(self.trees.get(base_tree, {})) if base_tree else {}
        for e in entries:
            entry = {"mode": e["mode"], "type": e["type"], "sha": e["sha"]}
            if e["type"] == "blob" and e["sha"] in self.blobs:
                entry["size"] = len(self.blobs[e["sha"]])
            tree[e["path"]] = entry
        tid = _git_id("tree", json.dumps(tree, sort_keys=True).encode())
        self.trees[tid] = tree
        return tid

    def tree_entry(self, tree_id, path):
        if tree_id is None:
            return None
        return self.trees.get(tree_id, {}).get(path)

    def create_commit(self, message, tree, parents):
        body = (f"tree {tree}\n" + "".join(f"parent {p}\n" for p in parents)
                + "author QF Publisher <qf@localhost> 1700000000 +0000\n"
                + "committer QF Publisher <qf@localhost> 1700000000 +0000\n\n" + message).encode()
        cid = _git_id("commit", body)
        self.commits[cid] = {"tree": tree, "parents": list(parents), "message": message}
        return cid

    def get_commit(self, sha):
        return self.commits[sha]


def build_root(root):
    """156 tiny deterministic payloads at the frozen rel set."""
    consts = pub.derive_constants(FROZEN)
    pins = {}
    for rel in consts["payload_rels"]:
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        data = f"synthetic payload for {rel}\n".encode()
        with open(p, "wb") as fh:
            fh.write(data)
        pins[rel] = hashlib.sha256(data).hexdigest()
    return consts, pins


class Case:
    def __init__(self, cid, title):
        self.id, self.title = cid, title
        self.checks, self.failures = 0, []

    def check(self, ok, label):
        self.checks += 1
        if not ok:
            self.failures.append(label)

    def done(self):
        return {"id": self.id, "title": self.title, "checks": self.checks,
                "failures": self.failures,
                "verdict": "PASS" if not self.failures else "FAIL"}


def expect_membership(fn):
    try:
        fn()
    except HoldError as e:
        return str(e).startswith("HOLD:MEMBERSHIP")
    except Exception:
        return False
    return False


def main():
    out_path = sys.argv[1]
    base = tempfile.mkdtemp(prefix="qf18r2_")
    cases = []

    # ---------- L-01: both journals outside -> PASS ----------
    c = Case("L-01", "156-member root, both journals in sibling control dir -> publish PASS")
    cap = os.path.join(base, "cap_ok")
    ctrl = os.path.join(base, "cap_ok.control")
    os.makedirs(ctrl)
    consts, pins = build_root(cap)
    acq_j = os.path.join(ctrl, "acquisition_attempt_journal.qfj2")
    pub_j = os.path.join(ctrl, "qfj2_publication_journal.qfj2")
    pub._journal_append(acq_j, {"type": "attempt", "capture_id": CID, "symbol": "NVDA"})
    remote = FakeGitRemote()
    res = pub.publish(cap, CID, remote, pub_j, os.path.join(base, "staging_ok"),
                      FROZEN, pins)
    c.check(res["status"] == "PUBLISHED", "publish PUBLISHED")
    c.check(sorted(os.listdir(cap)) == ["actions", "meta", "raw"],
            "capture root top level is exactly the member dirs")
    c.check(os.path.exists(acq_j) and os.path.exists(pub_j),
            "both journals exist in the control directory, outside cap_dir")
    journal = pub._journal_read(pub_j)
    intent = next(r for r in journal if r.get("type") == "intent")
    published = next(r for r in journal if r.get("type") == "published")
    c.check(len(intent["pins"]) == 158, "sealed member set is exactly 158 (156+2)")
    c.check(published["commit"] == res["commit"], "published record pins the commit")
    cases.append(c.done())

    # ---------- L-02: acquisition journal inside root -> HOLD:MEMBERSHIP ----------
    c = Case("L-02", "acquisition_attempt_journal inside capture root -> HOLD:MEMBERSHIP")
    cap2 = os.path.join(base, "cap_acq_in")
    shutil.copytree(cap, cap2)
    with open(os.path.join(cap2, "acquisition_attempt_journal.qfj2"), "wb") as fh:
        fh.write(b"misplaced journal\n")
    ctrl2 = os.path.join(base, "cap_acq_in.control"); os.makedirs(ctrl2)
    c.check(expect_membership(lambda: pub.publish(
        cap2, CID, FakeGitRemote(), os.path.join(ctrl2, "qfj2_publication_journal.qfj2"),
        os.path.join(base, "staging2"), FROZEN, pins)), "membership HOLD raised")
    cases.append(c.done())

    # ---------- L-03: QFJ2 publication journal inside root -> HOLD:MEMBERSHIP ----------
    c = Case("L-03", "qfj2_publication_journal inside capture root -> HOLD:MEMBERSHIP")
    cap3 = os.path.join(base, "cap_pub_in")
    shutil.copytree(cap, cap3)
    c.check(expect_membership(lambda: pub.publish(
        cap3, CID, FakeGitRemote(), os.path.join(cap3, "qfj2_publication_journal.qfj2"),
        os.path.join(base, "staging3"), FROZEN, pins)), "membership HOLD raised")
    cases.append(c.done())

    # ---------- L-04: pre-anchor verification without any anchor ----------
    c = Case("L-04", "pre-anchor remote verification from sealed/pinned evidence (no anchor exists)")
    scanner_tmp = os.path.join(base, "scanner_repo")
    anchor_path = os.path.join(scanner_tmp, "research_notes", "archive_anchors", f"{CID}.json")
    c.check(not os.path.exists(anchor_path), "anchor does not exist before verification")
    info = {"container_sha256": intent["container_sha256"], "blob_id": intent["blob_id"],
            "pins": intent["pins"]}
    transcript = pub._verify_remote(remote, res["commit"], intent["parent"], PATH,
                                    info, consts["payload_rels"], CID)
    c.check(isinstance(transcript, str) and len(transcript) == 64,
            "verification transcript produced from intent/sealed/pins only")
    c.check(transcript == published["transcript"], "transcript equals the journal published record")
    c.check(not os.path.exists(anchor_path), "verification consumed no anchor and created none")
    cases.append(c.done())

    # ---------- L-05: anchor emitted after verification; consumer re-verifies ----------
    c = Case("L-05", "anchor emitted only after verification; consumer starts from anchor and re-verifies")
    commit = remote.get_commit(res["commit"])
    anchor = {
        "designated_repo": "mickaellall116-cmyk/qf-data-archive",
        "designated_ref": pub.REF,
        "commit": res["commit"],
        "tree": commit["tree"],
        "blob": res["blob_id"],
        "container_sha256": res["container_sha256"],
        "capture_id": CID,
        "adopted_rev3_manifest_pin": hashlib.sha256(open(CANDIDATE, "rb").read()).hexdigest(),
        "member_count": 158,
        "verification_transcript_hash": transcript,
    }
    os.makedirs(os.path.dirname(anchor_path))
    with open(anchor_path, "w") as fh:
        json.dump(anchor, fh, indent=1, sort_keys=True)
        fh.write("\n")
    a = json.load(open(anchor_path))
    c.check(remote.get_commit(a["commit"])["tree"] == a["tree"], "consumer: commit/tree match anchor")
    entry = remote.tree_entry(a["tree"], PATH)
    c.check(entry is not None and entry["sha"] == a["blob"], "consumer: tree entry is the anchor blob")
    data = remote.get_blob_raw(a["blob"])
    c.check(_git_id("blob", data) == a["blob"], "consumer: blob id recomputes")
    c.check(hashlib.sha256(data[:-pub.TRAILER_BYTES]).hexdigest() == a["container_sha256"],
            "consumer: CONTAINER_SHA256 recomputes from fetched bytes")
    fd = os.memfd_create("qf18-consumer")
    try:
        os.write(fd, data)
        parsed = pub.parse_container_fd(fd, len(data), consts["payload_rels"])
    finally:
        os.close(fd)
    c.check(len(parsed["members"]) == a["member_count"] == 158, "consumer: member count 158")
    c.check(all(parsed["members"][r] == (intent["pins"][r]["length"], intent["pins"][r]["sha256"])
                if isinstance(intent["pins"][r], dict) else
                tuple(intent["pins"][r]) == parsed["members"][r]
                for r in parsed["members"]), "consumer: every member matches the sealed pins")
    cases.append(c.done())

    results = {
        "suite": "QF-YAHOO-REV3-MANIFEST-LEDGER-SEPARATION-20261016-18 r2 (narrow compatibility fixture)",
        "publisher": "qfar1_publisher_h16.py @ 53bdc672e609791dc55277023dd984cd8727f3c3",
        "candidate_sha256": hashlib.sha256(open(CANDIDATE, "rb").read()).hexdigest(),
        "cases": cases,
        "total_checks": sum(x["checks"] for x in cases),
        "total_failures": sum(len(x["failures"]) for x in cases),
        "verdict": "PASS" if all(not x["failures"] for x in cases) else "FAIL",
        "container_sha256": res["container_sha256"],
        "commit": res["commit"],
    }
    with open(out_path, "w") as fh:
        json.dump(results, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(results["verdict"], results["total_checks"], "checks,",
          results["total_failures"], "failures")
    shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    main()
