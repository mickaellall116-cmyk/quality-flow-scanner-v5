"""Directory-backed fake Git Data remote (-14 fencing fixture).

Two real processes share one remote through files under a root directory, so
the interprocess intent fence is tested against genuinely shared state.
Objects are content-addressed files; refs are small files; mutations are
serialized with an flock on <root>/remote.lock. No sockets.
"""
import base64
import fcntl
import hashlib
import json
import os

import qfar1_publisher_h15 as qp
from qfar1_publisher_h15 import _ApiError, _TransportLost


def _git_id(kind, body):
    return hashlib.sha1(b"%s %d\x00" % (kind.encode(), len(body)) + body).hexdigest()


class SharedFakeRemote:
    def __init__(self, root):
        self.root = root
        for d in ("blobs", "trees", "commits", "refs"):
            os.makedirs(os.path.join(root, d), exist_ok=True)
        self._lock_fd = os.open(os.path.join(root, "remote.lock"),
                                os.O_RDWR | os.O_CREAT, 0o600)

    # -- internals
    def _locked(self):
        fcntl.flock(self._lock_fd, fcntl.LOCK_EX)

    def _unlocked(self):
        fcntl.flock(self._lock_fd, fcntl.LOCK_UN)

    def _put(self, kind, oid, data):
        p = os.path.join(self.root, kind, oid)
        if not os.path.exists(p):
            tmp = p + f".tmp{os.getpid()}"
            with open(tmp, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.rename(tmp, p)

    def _get(self, kind, oid):
        p = os.path.join(self.root, kind, oid)
        if not os.path.exists(p):
            return None
        with open(p, "rb") as f:
            return f.read()

    def _ref_path(self, ref):
        return os.path.join(self.root, "refs", ref.replace("/", "_"))

    # -- repo / refs
    def get_repo(self):
        return {"private": True, "owner": qp.DESIGNATED_OWNER, "name": qp.DESIGNATED_REPO}

    def get_ref(self, ref):
        data = self._get("refs", ref.replace("/", "_"))
        return data.decode() if data else None

    def create_ref(self, ref, sha):
        self._locked()
        try:
            if os.path.exists(self._ref_path(ref)):
                raise _ApiError(422, "reference already exists")
            self._put("refs", ref.replace("/", "_"), sha.encode())
            return {"ref": ref, "sha": sha}
        finally:
            self._unlocked()

    def update_ref(self, ref, sha, force=False):
        self._locked()
        try:
            cur = self.get_ref(ref)
            if cur is None:
                raise _ApiError(422, "reference does not exist")
            if not force and cur not in self._ancestors(sha):
                raise _ApiError(422, "not fast-forward")
            self._put("refs", ref.replace("/", "_"), sha.encode())
            return {"ref": ref, "sha": sha}
        finally:
            self._unlocked()

    def _ancestors(self, sha):
        seen, stack = set(), [sha]
        while stack:
            c = stack.pop()
            if c in seen:
                continue
            raw = self._get("commits", c)
            if raw is None:
                continue
            seen.add(c)
            stack.extend(json.loads(raw)["parents"])
        return seen

    # -- blobs
    def create_blob(self, content_b64, encoding):
        data = base64.b64decode(content_b64)
        bid = _git_id("blob", data)
        self._put("blobs", bid, data)
        return {"sha": bid}

    def get_blob_raw(self, sha):
        return self._get("blobs", sha)

    def get_blob_json(self, sha):
        data = self._get("blobs", sha)
        b64 = base64.b64encode(data).decode()
        wrapped = "\n".join(b64[i:i + 60] for i in range(0, len(b64), 60))
        return {"content": wrapped, "encoding": "base64", "size": len(data)}

    # -- trees
    def create_tree(self, base_tree, entries):
        tree = {}
        if base_tree:
            raw = self._get("trees", base_tree)
            if raw:
                tree = json.loads(raw)
        for e in entries:
            entry = {"mode": e["mode"], "type": e["type"], "sha": e["sha"]}
            if e["type"] == "blob":
                data = self._get("blobs", e["sha"])
                if data is not None:
                    entry["size"] = len(data)
            tree[e["path"]] = entry
        tid = _git_id("tree", json.dumps(tree, sort_keys=True).encode())
        self._put("trees", tid, json.dumps(tree, sort_keys=True).encode())
        return tid

    def tree_entry(self, tree_id, path):
        if tree_id is None:
            return None
        raw = self._get("trees", tree_id)
        if raw is None:
            return None
        return json.loads(raw).get(path)

    # -- commits
    def create_commit(self, message, tree, parents):
        parents = list(parents)
        body = (f"tree {tree}\n" + "".join(f"parent {p}\n" for p in parents)
                + "author QF Publisher <qf@localhost> 1700000000 +0000\n"
                + "committer QF Publisher <qf@localhost> 1700000000 +0000\n\n" + message).encode()
        cid = _git_id("commit", body)
        self._put("commits", cid,
                  json.dumps({"tree": tree, "parents": parents, "message": message}).encode())
        return cid

    def get_commit(self, sha):
        raw = self._get("commits", sha)
        if raw is None:
            raise KeyError(sha)
        return json.loads(raw)

    # -- helpers
    def commit_ids(self):
        d = os.path.join(self.root, "commits")
        return sorted(os.listdir(d)) if os.path.isdir(d) else []
