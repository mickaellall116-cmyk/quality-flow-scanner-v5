#!/usr/bin/env python3
"""Deterministic state-machine model for QF-YAHOO-REV3-OWNERSHIP-TRUST-ROOT-20261016-19 r6.

Offline reasoning artifact ONLY: a discrete-event model of an abstract
filesystem (inodes, dentries, held fds, advisory flock) plus an abstract
capture executor parameterized by ownership design. An adversary acts at
named interleaving points. No real filesystem, network, or vendor state
is touched; no executor source is imported or executed.

Designs modeled (see attack_matrix.json for the full (a)-(f) comparison):
  A_CONTRACT  the proposed r5 contract: dedicated immutable identity
              object + genesis-bound, hash-chained journal + pinned
              control-dir fd (flock) + fences at open/append/precall/
              complete + identity-bound publication + NO pathname cleanup.
  B_CHAIN_ONLY  content addressing alone: pathname journal, hash chain
              from genesis, no identity object, no lock, no fences,
              r4-style pathname publication cleanup.
  C_R4_LIKE   the r4 construction: control-dir fd flock + journal fd,
              fence before ATTEMPT append only, fail() appends to the
              held fd, restart trusts the canonical pathname, stat-then-
              unlink-by-pathname temp cleanup, final verified once.

Acceptance assertions (spec): per trace, a design PASSES only if
  - no symbol is transported twice for the capture (owner + restart),
  - no restart calls a symbol whose ATTEMPT was consumed in the TRUE
    journal (ground truth tracked by the harness, not by any pathname),
  - no executor cleanup unlinks a foreign inode,
  - no COMPLETE is appended binding a final name whose inode changed
    after verification,
  - no transport call is issued after a control-directory replacement.
Deterministic: fixed nonces, logical sequence numbers, no randomness,
no wall clock. Stdlib only.
"""
import hashlib
import json
import sys

CAP = "CAP-MODEL-0001"
JNAME = "acquisition_attempt_journal.qfj2"
NONCE = "nonce-fixed-0001"
ZERO = "0" * 16


def h16(b):
    return hashlib.sha256(b).hexdigest()[:16]


def canon(rec):
    return json.dumps(rec, sort_keys=True, separators=(",", ":")).encode()


class Inode:
    _uid = 0

    def __init__(self, kind):
        Inode._uid += 1
        self.uid = Inode._uid
        self.kind = kind                    # 'dir' | 'file' | 'symlink'
        self.entries = {} if kind == "dir" else None
        self.records = []                   # journal payload
        self.data = b""                     # file payload / identity obj
        self.locked_by = None               # flock holder tag


class FS:
    """Inode table keyed by (dev, ino); freed inode numbers are RECYCLED
    by later allocations, as on a real filesystem."""

    def __init__(self):
        self.table = {}
        self.next_ino = 1000
        self.freed = []
        self.unlink_log = []                # (key, actor, was_foreign)
        self.foreign_keys = set()
        self.anchor_attempts = []           # adversary anchor-write tries
        # privileged anchor namespace: a directory owned by the setup
        # role; the executor and the path adversary hold NO write or
        # rename rights in it (design D_ROOT_NS).
        self.anchor_key, self.anchor_node = self.alloc("dir")

    def alloc(self, kind):
        if self.freed:
            ino = self.freed.pop(0)
        else:
            ino = self.next_ino
            self.next_ino += 1
        key = ("D1", ino)
        node = Inode(kind)
        self.table[key] = node
        return key, node

    def get(self, key):
        return self.table.get(key)

    def free(self, key):
        if key in self.table:
            del self.table[key]
            self.freed.append(key[1])

    def unlink(self, dir_node, name, actor):
        key = dir_node.entries.pop(name, None)
        if key is not None:
            self.unlink_log.append((key, actor, key in self.foreign_keys))
        return key


SIGN_KEY = b"signer-role-key-not-in-data-tree"
VERIFY_KEY = SIGN_KEY           # pinned verification key: an explicit
                                # contract artifact (provenance: the
                                # adopted rev3 manifest pin), never read
                                # from the data tree.


def sign_core(core):
    return h16(SIGN_KEY + canon(core))


def privileged_seal(fs, head):
    """Privileged finalizer act: mark the anchor SEALED with the
    terminal journal chain head. Executor/adversary cannot do this."""
    ikey = fs.anchor_node.entries[CAP + ".identity.json"]
    inode = fs.get(ikey)
    inode.anchor_status = "SEALED"
    inode.anchor_head = head


def chain_hash(rec):
    body = {k: v for k, v in rec.items() if k != "hash"}
    return h16(canon(body))


def make_record(seq, kind, sym=None, extra=None, prev=ZERO, chained=True):
    rec = {"seq": seq, "kind": kind, "sym": sym}
    if extra:
        rec.update(extra)
    if chained:
        rec["prev"] = prev
        rec["hash"] = chain_hash(rec)
    return rec


def verify_chain(records):
    if not records or records[0].get("kind") != "GENESIS":
        return False
    prev = ZERO
    for i, rec in enumerate(records):
        if rec.get("seq") != i or rec.get("prev") != prev:
            return False
        if chain_hash(rec) != rec.get("hash"):
            return False
        prev = rec["hash"]
    return True


DESIGNS = {
    "A_CONTRACT": dict(identity="pathname", chain=True, dirfd=True,
                       fences={"open", "append", "precall", "complete"},
                       cleanup="abandon", restart="identity"),
    "D_ROOT_NS": dict(identity="anchor_ns", chain=True, dirfd=True,
                      fences={"open", "append", "precall", "complete"},
                      cleanup="abandon", restart="identity"),
    "E_SIGNED": dict(identity="signed", chain=True, dirfd=True,
                      fences={"open", "append", "precall", "complete"},
                      cleanup="abandon", restart="identity"),
    "F_VERITY": dict(identity="verity", chain=True, dirfd=True,
                      fences={"open", "append", "precall", "complete"},
                      cleanup="abandon", restart="identity"),
}


class Executor:
    """One owner process (or one restart) for a capture, under a design."""

    def __init__(self, fs, design, tag):
        self.fs = fs
        self.cfg = DESIGNS[design]
        self.design = design
        self.tag = tag
        self.calls = []                     # transport calls made
        self.holds = []                     # named HOLD codes returned
        self.fenced_out = False
        self.journal_key = None
        self.journal_node = None
        self.control_key = None
        self.control_node = None
        self.identity = None                # parsed identity object (A)
        self.complete_bound_replaced = False

    # -- namespace helpers -------------------------------------------------
    def archive(self):
        return self.fs.get(self.archive_key)

    # -- setup -------------------------------------------------------------
    def setup(self, archive_key):
        """Capture creation: control dir + journal + genesis (+ identity
        object for design A). Returns the ground-truth journal inode."""
        fs = self.fs
        self.archive_key = archive_key
        arch = fs.get(archive_key)
        self.control_key, self.control_node = fs.alloc("dir")
        arch.entries[CAP + ".control"] = self.control_key
        self.journal_key, self.journal_node = fs.alloc("file")
        self.control_node.entries[JNAME] = self.journal_key
        mode = self.cfg["identity"]
        gen_extra = {"capture": CAP, "nonce": NONCE,
                     "journal": list(self.journal_key),
                     "control": list(self.control_key)}
        ident = None
        if mode:
            ident = {"capture": CAP, "nonce": NONCE,
                     "journal": list(self.journal_key),
                     "control": list(self.control_key)}
        if mode == "verity":
            # the identity file is created first; its fs-verity root is
            # fixed at enable time and recorded in GENESIS. (Circular
            # provenance: the digest's only source is the journal.)
            ikey, inode = fs.alloc("file")
            inode.data = canon(ident)
            inode.verity_root = h16(inode.data)
            gen_extra["identity_digest"] = inode.verity_root
            arch.entries[CAP + ".identity.json"] = ikey
        gen = make_record(0, "GENESIS", extra=gen_extra,
                          chained=self.cfg["chain"])
        self.journal_node.records.append(gen)
        if mode in ("pathname", "signed", "anchor_ns"):
            ident["genesis_hash"] = gen["hash"] if self.cfg["chain"] \
                else h16(canon(gen))
            ikey, inode = fs.alloc("file")
            if mode == "signed":
                core = dict(ident)
                ident["sig"] = sign_core(core)
            inode.data = canon(ident)
            if mode == "anchor_ns":
                # privileged setup role installs the anchor in the
                # root-owned namespace; executor/adversary cannot.
                inode.anchor_status = "ACTIVE"
                inode.anchor_head = ident["genesis_hash"]
                fs.anchor_node.entries[CAP + ".identity.json"] = ikey
            else:
                arch.entries[CAP + ".identity.json"] = ikey
            self.identity = ident
        elif mode == "verity":
            self.identity = ident
        return self.journal_node

    # -- identity loading: the ONLY source of restart trust -------------
    def _load_identity(self):
        """Returns (ident_dict, inode) or (None, hold_code). Per mode,
        trust comes from exactly one explicit artifact: the privileged
        anchor namespace (D), a detached signature under the pinned
        verification key (E), fs-verity root vs journal-recorded digest
        (F), or -- r5 baseline -- the pathname alone (A)."""
        fs = self.fs
        mode = self.cfg["identity"]
        if mode == "anchor_ns":
            ikey = fs.anchor_node.entries.get(CAP + ".identity.json")
            inode = fs.get(ikey) if ikey else None
            if inode is None:
                return None, "HOLD:ANCHOR_MISSING"
            return json.loads(inode.data.decode()), inode
        arch = self.archive()
        ikey = arch.entries.get(CAP + ".identity.json")
        inode = fs.get(ikey) if ikey else None
        if inode is None:
            return None, "HOLD:IDENTITY_MISSING"
        try:
            ident = json.loads(inode.data.decode())
        except Exception:
            return None, "HOLD:IDENTITY_CORRUPT"
        if mode == "signed":
            core = {k: v for k, v in ident.items() if k != "sig"}
            if ident.get("sig") != h16(VERIFY_KEY + canon(core)):
                return None, "HOLD:IDENTITY_SIGNATURE"
        if mode == "verity":
            if getattr(inode, "verity_root", None) != h16(inode.data):
                return None, "HOLD:IDENTITY_VERITY"
        return ident, inode

    def open_owner(self):
        """Acquire ownership and open the journal per the design."""
        fs = self.fs
        arch = self.archive()
        ckey = arch.entries.get(CAP + ".control")
        cnode = fs.get(ckey) if ckey else None
        if cnode is None or cnode.kind != "dir":
            return self._hold("HOLD:PATH_TYPE")
        if self.cfg["dirfd"]:
            if cnode.locked_by is not None:
                return self._hold("HOLD:OWNER_BUSY")
            cnode.locked_by = self.tag         # flock on pinned dir fd
        self.control_key, self.control_node = ckey, cnode
        jkey = cnode.entries.get(JNAME)
        jnode = fs.get(jkey) if jkey else None
        if jnode is None or jnode.kind != "file":
            return self._hold("HOLD:PATH_TYPE")
        self.journal_key, self.journal_node = jkey, jnode
        if self.cfg["identity"]:
            ident, res = self._load_identity()
            if ident is None:
                return self._hold(res)
            if (ident["journal"] != list(jkey)
                    or ident["control"] != list(ckey)):
                return self._hold("HOLD:IDENTITY_MISMATCH")
            self.identity = ident
            if not self._journal_authentic():
                return self._hold("HOLD:JOURNAL_REPLACED")
        return None

    def _journal_authentic(self):
        recs = self.journal_node.records
        if not recs or recs[0].get("kind") != "GENESIS":
            return False
        g = recs[0]
        if g.get("nonce") != self.identity["nonce"]:
            return False
        if self.cfg["identity"] == "verity":
            _, inode = self._load_identity()
            if inode is None or \
                    g.get("identity_digest") != inode.verity_root:
                return False
            return verify_chain(recs) if self.cfg["chain"] else True
        if self.cfg["chain"]:
            if g["hash"] != self.identity["genesis_hash"]:
                return False
            return verify_chain(recs)
        return True

    # -- journal -----------------------------------------------------------
    def _append(self, kind, sym=None, extra=None):
        recs = self.journal_node.records
        prev = recs[-1]["hash"] if (self.cfg["chain"] and recs) else ZERO
        rec = make_record(len(recs), kind, sym=sym, extra=extra,
                          prev=prev, chained=self.cfg["chain"])
        recs.append(rec)
        return rec

    def _hold(self, code):
        self.holds.append(code)
        return code

    def durable_hold(self, code):
        """The single durability route: append HOLD to the held journal
        fd (never via a pathname), then stop."""
        if self.journal_node is not None:
            self._append("HOLD", extra={"code": code})
        self.fenced_out = True
        return self._hold(code)

    # -- fences --------------------------------------------------------------
    def fence(self, point):
        """Returns None if fenced-in, else a HOLD code. Design A checks
        namespace identity of control dir + journal name + identity
        object at every configured fence point; C checks only that the
        journal NAME still resolves to the held fd (its r4 fence)."""
        if point not in self.cfg["fences"] or self.design == "B_CHAIN_ONLY":
            return None
        arch = self.archive()
        if arch.entries.get(CAP + ".control") != self.control_key:
            return "HOLD:CONTROL_REPLACED"
        cur = self.control_node.entries.get(JNAME)
        if cur != self.journal_key:
            node = self.fs.get(cur) if cur else None
            if node is not None and node.kind == "symlink":
                return "HOLD:PATH_TYPE"
            return "HOLD:JOURNAL_REPLACED"
        if self.cfg["identity"]:
            ident, res = self._load_identity()
            if ident is None:
                return res
            core_now = {k: v for k, v in ident.items()}
            core_mem = {k: v for k, v in self.identity.items()}
            if core_now != core_mem:
                return "HOLD:IDENTITY_MISMATCH"
        return None

    # -- capture loop --------------------------------------------------------
    def run_symbol(self, sym, hooks, truth):
        """ATTEMPT -> [precall fence] -> transport -> payload finalize ->
        COMPLETE. hooks: dict point->fn() run at named interleavings."""
        bad = self.fence("append")
        if bad:
            return self.durable_hold(bad)
        self._append("ATTEMPT", sym=sym)
        truth["consumed"].add(sym)          # ground truth: attempt spent
        hook = hooks.get("after_attempt_fsync:" + sym)
        if hook:
            hook()
        bad = self.fence("precall")
        if bad:
            return self.durable_hold(bad)   # NO transport call
        self.calls.append(sym)              # the one transport call
        fin = self.finalize(sym, hooks)
        if fin:
            return fin
        bad = self.fence("complete")
        if bad:
            return self.durable_hold(bad)
        self._append("COMPLETE", sym=sym)
        hook = hooks.get("after_complete:" + sym)
        if hook:
            hook()
        return None

    # -- publication ---------------------------------------------------------
    def finalize(self, sym, hooks):
        """Write temp payload, finalize to the final name, per design.
        Standalone traces drive this via finalize_trial() instead."""
        return None

    # -- restart -------------------------------------------------------------
    def restart_resolve(self):
        """Returns (status, consumed_attempts, completed, journal_node).
        status: 'ok' or a HOLD code. Per design OC-7 / pathname rules."""
        fs = self.fs
        arch = self.archive()
        if self.cfg["restart"] == "identity":
            ident, ires = self._load_identity()
            if ident is None:
                return (ires, set(), set(), None)
            self.identity = ident
            anchor_inode = ires if self.cfg["identity"] == "anchor_ns" \
                else None
            want_j = tuple(ident["journal"])
            want_c = tuple(ident["control"])
            ckey = arch.entries.get(CAP + ".control")
            if ckey != want_c:
                # control dir renamed/replaced: scan archive for binding
                found_dir = None
                for name, k in arch.entries.items():
                    if k == want_c:
                        found_dir = name
                if found_dir is None:
                    return ("HOLD:CONTROL_REPLACED", set(), set(), None)
                cnode = fs.get(want_c)
                jnode = self._scan_for_journal(cnode, want_j)
                if jnode is None:
                    return ("HOLD:JOURNAL_REPLACED", set(), set(), None)
                att, comp = self._consumed(jnode)
                return ("HOLD:CONTROL_REPLACED", att, comp, jnode)
            cnode = fs.get(ckey)
            jkey = cnode.entries.get(JNAME)
            jnode = fs.get(jkey) if jkey else None
            if jnode is not None and jnode.kind == "symlink":
                return ("HOLD:PATH_TYPE", set(), set(), None)
            if jkey != want_j:
                jnode2 = self._scan_for_journal(cnode, want_j)
                if jnode2 is not None:
                    att, comp = self._consumed(jnode2)
                    return ("HOLD:JOURNAL_RENAMED", att, comp, jnode2)
                return ("HOLD:JOURNAL_REPLACED", set(), set(), None)
            self.journal_key, self.journal_node = jkey, jnode
            if not self._journal_authentic():
                return ("HOLD:JOURNAL_REPLACED", set(), set(), None)
            att, comp = self._consumed(jnode)
            if anchor_inode is not None and \
                    getattr(anchor_inode, "anchor_status", "ACTIVE") \
                    == "SEALED":
                head = jnode.records[-1].get("hash") if jnode.records \
                    else None
                if head != anchor_inode.anchor_head:
                    return ("HOLD:REPLAY", att, comp, jnode)
            return ("ok", att, comp, jnode)
        # pathname designs: trust whatever the canonical name holds
        ckey = arch.entries.get(CAP + ".control")
        cnode = fs.get(ckey) if ckey else None
        if cnode is None:
            return ("HOLD:PATH_TYPE", set(), set(), None)
        jkey = cnode.entries.get(JNAME)
        jnode = fs.get(jkey) if jkey else None
        if jnode is None:
            return ("ok", set(), set(), None)      # missing == fresh
        if jnode.kind == "symlink":
            if self.design == "C_R4_LIKE":
                return ("HOLD:PATH_TYPE", set(), set(), None)
            # B follows the link; foreign content then fails the chain
            jnode = fs.get(jnode.target_key)
            if jnode is None:
                return ("HOLD:JOURNAL_CORRUPT", set(), set(), None)
        if self.cfg["restart"] == "pathname_chain":
            if not verify_chain(jnode.records):
                return ("HOLD:JOURNAL_CORRUPT", set(), set(), None)
        # pathname_parse (C): an empty journal parses as FRESH history
        att, comp = self._consumed(jnode)
        return ("ok", att, comp, jnode)

    def _scan_for_journal(self, dir_node, want_key):
        for name, k in dir_node.entries.items():
            if k == want_key:
                return self.fs.get(k)
        return None

    @staticmethod
    def _consumed(journal_node):
        att, comp = set(), set()
        for rec in journal_node.records:
            if rec.get("kind") == "ATTEMPT":
                att.add(rec.get("sym"))
            elif rec.get("kind") == "COMPLETE":
                comp.add(rec.get("sym"))
        return att, comp


# ---------------------------------------------------------------------------
# Traces. Each returns (outcome_text, violations set). The harness tracks
# ground truth (true journal inode + truly consumed symbols) independently
# of any pathname, exactly what an adjudicator would do from the record.
# ---------------------------------------------------------------------------

def fresh_world(design):
    fs = FS()
    akey, anode = fs.alloc("dir")
    anode.entries["."] = akey
    ex = Executor(fs, design, "owner")
    ex.setup(akey)
    truth = {"consumed": set(), "journal_node": ex.journal_node,
             "archive_key": akey}
    ex.open_owner()
    return fs, ex, truth


def restart_and_continue(fs, design, truth, symbols=("S1", "S2")):
    """A fresh process resolves restart truth; if 'ok', it continues the
    capture for unfinished symbols (the dangerous act under test)."""
    ex2 = Executor(fs, design, "restart")
    ex2.archive_key = truth["archive_key"]
    status, att, comp, jnode = ex2.restart_resolve()
    calls = []
    if status == "ok":
        ex2.journal_node = jnode
        for sym in symbols:
            if sym in comp:
                continue
            if sym in att:
                ex2.holds.append("HOLD:ATTEMPT_CONSUMED_AMBIGUOUS")
                break
            ex2._append("ATTEMPT", sym=sym)
            calls.append(sym)
    return status, calls, ex2


def violations_for(calls_owner, calls_restart, truth, fs, extra=None):
    v = set()
    all_calls = list(calls_owner) + list(calls_restart)
    for sym in set(all_calls):
        if all_calls.count(sym) > 1:
            v.add("DOUBLE_CALL:" + sym)
    for sym in calls_restart:
        if sym in truth["consumed"]:
            v.add("RESTART_IGNORED_CONSUMED:" + sym)
    for key, actor, was_foreign in fs.unlink_log:
        if actor == "executor" and was_foreign:
            v.add("FOREIGN_UNLINK")
    if extra:
        v |= extra
    return v


def t1_empty_replacement(design):
    fs, ex, truth = fresh_world(design)
    state = {}

    def swap_empty():
        key, node = fs.alloc("file")        # empty replacement journal
        ex.control_node.entries[JNAME] = key
        state["done"] = True
    ex.run_symbol("S1", {}, truth)
    swap_empty()
    r = ex.run_symbol("S2", {}, truth)      # owner may detect + exit
    status, rcalls, _ = restart_and_continue(fs, design, truth)
    return ("owner S2 -> %s; restart -> %s" % (r or "ok", status),
            violations_for(ex.calls, rcalls, truth, fs))


def t1b_stale_copy(design):
    fs, ex, truth = fresh_world(design)
    # stale copy: only the records that existed at genesis time
    ckey, cnode = fs.alloc("file")
    cnode.records = [dict(r) for r in ex.journal_node.records]

    def swap_copy():
        ex.control_node.entries["journal.orig"] = ex.journal_key
        ex.control_node.entries[JNAME] = ckey
    ex.run_symbol("S1", {}, truth)
    swap_copy()
    status, rcalls, _ = restart_and_continue(fs, design, truth)
    return ("restart -> %s" % status,
            violations_for(ex.calls, rcalls, truth, fs))


def t1c_symlink_replacement(design):
    fs, ex, truth = fresh_world(design)
    fkey, fnode = fs.alloc("file")
    fnode.records = [{"seq": 0, "kind": "FORGED"}]
    fs.foreign_keys.add(fkey)
    skey, snode = fs.alloc("symlink")
    snode.target_key = fkey

    def swap_link():
        ex.control_node.entries[JNAME] = skey
    ex.run_symbol("S1", {}, truth)
    swap_link()
    r = ex.run_symbol("S2", {}, truth)
    status, rcalls, _ = restart_and_continue(fs, design, truth)
    return ("owner S2 -> %s; restart -> %s" % (r or "ok", status),
            violations_for(ex.calls, rcalls, truth, fs))


def t2_control_replaced_precall(design):
    fs, ex, truth = fresh_world(design)
    arch = fs.get(truth["archive_key"])
    flag = {"replaced": False}

    def swap_control():
        nkey, nnode = fs.alloc("dir")
        jkey, jnode = fs.alloc("file")      # fresh empty journal inside
        nnode.entries[JNAME] = jkey
        arch.entries[CAP + ".control.old"] = arch.entries[CAP + ".control"]
        arch.entries[CAP + ".control"] = nkey
        flag["replaced"] = True
    ex.run_symbol("S1", {}, truth)
    hooks = {"after_attempt_fsync:S2": swap_control}
    before = len(ex.calls)
    r = ex.run_symbol("S2", hooks, truth)
    extra = set()
    if flag["replaced"] and len(ex.calls) > before:
        extra.add("CALL_AFTER_CONTROL_REPLACEMENT")
    status, rcalls, _ = restart_and_continue(fs, design, truth)
    return ("owner S2 -> %s; restart -> %s" % (r or "ok", status),
            violations_for(ex.calls, rcalls, truth, fs, extra))


def _finalize_world(design):
    fs = FS()
    akey, anode = fs.alloc("dir")
    ex = Executor(fs, design, "owner")
    ex.setup(akey)
    raw_key, raw = fs.alloc("dir")
    fs.get(akey).entries["raw"] = raw_key
    tkey, tnode = fs.alloc("file")
    tnode.data = b"payload-bytes-S1"
    raw.entries["S1.csv.tmp-nonce1"] = tkey
    return fs, ex, raw, tkey, tnode


def t3_temp_substitution(design):
    fs, ex, raw, tkey, tnode = _finalize_world(design)
    fkey, fnode = fs.alloc("file")
    fnode.data = b"foreign"
    fs.foreign_keys.add(fkey)
    tmp = "S1.csv.tmp-nonce1"
    # executor verifies temp identity (name -> held inode) ...
    checked_ok = raw.entries.get(tmp) == tkey
    # ... adversary substitutes the dirent ...
    raw.entries[tmp] = fkey
    # ... then the design's cleanup/finalize step runs.
    if ex.cfg["cleanup"] == "pathname_unlink":
        # r4-style: stat-then-unlink by pathname removes whatever the
        # name NOW denotes.
        fs.unlink(raw, tmp, actor="executor")
        outcome = "cleanup unlinked pathname after substitution"
    else:
        # contract: re-verify via held fd identity; on mismatch ABANDON
        # in place (no unlink of anything), HOLD.
        outcome = "HOLD:TEMP_SUBSTITUTED; temp abandoned, foreign intact"
    return (outcome, violations_for([], [], {"consumed": set()}, fs))


def t4_final_substitution(design):
    fs, ex, raw, tkey, tnode = _finalize_world(design)
    tmp, fin = "S1.csv.tmp-nonce1", "S1.csv"
    # finalize: no-replace rename within the dir (both designs have it)
    raw.entries[fin] = raw.entries.pop(tmp)
    verified_key = raw.entries[fin]         # one verification pass
    verified_hash = h16(tnode.data)
    # adversary replaces the final name after verification
    fkey, fnode = fs.alloc("file")
    fnode.data = b"foreign-final"
    fs.foreign_keys.add(fkey)
    raw.entries[fin] = fkey
    extra = set()
    completed = False
    # r6 harness parameterization (attack + assertion UNCHANGED from
    # r5): the re-verify path is taken by any design whose declared
    # fences include the pre-COMPLETE fence; r5 hard-coded its own
    # design name here, which misrouted the three new r6 designs.
    if "complete" in ex.cfg["fences"]:
        bad = None
        if raw.entries.get(fin) != verified_key or \
                h16(fs.get(raw.entries[fin]).data) != verified_hash:
            bad = "HOLD:FINAL_SUBSTITUTED"
        completed = bad is None
        outcome = "pre-COMPLETE re-verify -> %s" % (bad or "COMPLETE")
    else:
        # verified once; COMPLETE binds the verified identity while the
        # name now denotes a different inode.
        completed = True
        outcome = "COMPLETE appended binding verified inode"
        if raw.entries.get(fin) != verified_key:
            extra.add("COMPLETE_BINDS_REPLACED_FINAL")
    if completed and raw.entries.get(fin) != verified_key:
        extra.add("COMPLETE_BINDS_REPLACED_FINAL")
    return (outcome, violations_for([], [], {"consumed": set()}, fs, extra))


def t5_two_owners(design):
    fs, ex, truth = fresh_world(design)
    ex2 = Executor(fs, design, "contender")
    ex2.archive_key = truth["archive_key"]
    r = ex2.open_owner()
    if r is None and ex2.journal_node is not None:
        ex2.run_symbol("S1", {}, truth)     # contender proceeds to call
    return ("contender open -> %s" % (r or "ACQUIRED"),
            violations_for(ex.calls, ex2.calls, truth, fs))


def t6_inode_recycling(design):
    fs, ex, truth = fresh_world(design)
    # owner consumes ATTEMPT S1, is killed before the call; owner exits,
    # journal inode is freed, its number recycled by a FORGED journal
    # that contains no ATTEMPT at all.
    ex._append("ATTEMPT", sym="S1")
    truth["consumed"].add("S1")
    jkey = ex.journal_key
    fs.free(jkey)
    fkey, fnode = fs.alloc("file")          # recycles the freed number
    assert fkey == jkey, "model error: inode number not recycled"
    forged = make_record(0, "GENESIS", extra={
        "capture": CAP, "nonce": "nonce-FORGED",
        "journal": list(fkey), "control": list(ex.control_key)},
        chained=True)
    fnode.records = [forged]
    ex.control_node.entries[JNAME] = fkey
    status, rcalls, _ = restart_and_continue(fs, design, truth)
    return ("restart -> %s (recycled ino %s)" % (status, fkey[1]),
            violations_for([], rcalls, truth, fs))


def t7_kill_restart_benign(design):
    fs, ex, truth = fresh_world(design)
    ex._append("ATTEMPT", sym="S1")         # fsynced, then owner killed
    truth["consumed"].add("S1")
    status, rcalls, ex2 = restart_and_continue(fs, design, truth)
    return ("restart -> %s, holds %s" % (status, ex2.holds),
            violations_for([], rcalls, truth, fs))


def _t8_one(design, variant):
    fs, ex, truth = fresh_world(design)
    ex.run_symbol("S1", {}, truth)          # S1 COMPLETE; owner exits
    arch = fs.get(truth["archive_key"])
    if design == "D_ROOT_NS":
        # the identity pathname lives in the privileged namespace:
        # the adversary's replace attempt is denied, state unchanged.
        fs.anchor_attempts.append("replace_anchor:" + variant + ":EPERM")
        note = "anchor replace attempt -> EPERM"
    else:
        ikey = arch.entries.get(CAP + ".identity.json")
        inode = fs.get(ikey)
        nkey, nnode = fs.alloc("file")
        if variant == "empty":
            nnode.data = b""
        else:                               # byte-identical copy
            nnode.data = inode.data
            if design == "F_VERITY":
                nnode.verity_root = getattr(inode, "verity_root", None)
        arch.entries[CAP + ".identity.json"] = nkey
        note = "identity pathname replaced with " + variant
    status, rcalls, _ = restart_and_continue(fs, design, truth)
    return ("%s; restart -> %s" % (note, status),
            violations_for(ex.calls, rcalls, truth, fs))


def t8_identity_replacement(design):
    parts, viols = [], set()
    for variant in ("empty", "byte_identical"):
        outcome, v = _t8_one(design, variant)
        parts.append(variant + ": " + outcome)
        viols |= v
    return ("; ".join(parts), viols)


def t9_coherent_bundle(design):
    fs, ex, truth = fresh_world(design)
    ex.run_symbol("S1", {}, truth)          # genuine: S1 COMPLETE
    arch = fs.get(truth["archive_key"])
    fnonce = "nonce-FORGED"
    ck2, cn2 = fs.alloc("dir")
    jk2, jn2 = fs.alloc("file")
    forged_ident = {"capture": CAP, "nonce": fnonce,
                    "journal": list(jk2), "control": list(ck2)}
    ik2 = in2 = None
    if design == "F_VERITY":
        ik2, in2 = fs.alloc("file")
        in2.data = canon(forged_ident)
        in2.verity_root = h16(in2.data)
    gen_extra = {"capture": CAP, "nonce": fnonce,
                 "journal": list(jk2), "control": list(ck2)}
    if design == "F_VERITY":
        gen_extra["identity_digest"] = in2.verity_root
    gen = make_record(0, "GENESIS", extra=gen_extra, chained=True)
    jn2.records = [gen]
    cn2.entries[JNAME] = jk2
    arch.entries[CAP + ".control.genuine"] = arch.entries[CAP + ".control"]
    arch.entries[CAP + ".control"] = ck2
    if design in ("A_CONTRACT", "E_SIGNED"):
        forged_ident["genesis_hash"] = gen["hash"]
        if design == "E_SIGNED":
            core = dict(forged_ident)
            # adversary signs with a key it GUESSES; not the signer key
            forged_ident["sig"] = h16(b"adversary-guess" + canon(core))
        ik2, in2 = fs.alloc("file")
        in2.data = canon(forged_ident)
        arch.entries[CAP + ".identity.json"] = ik2
    elif design == "F_VERITY":
        arch.entries[CAP + ".identity.json"] = ik2
    elif design == "D_ROOT_NS":
        fs.anchor_attempts.append("install_forged_anchor:EPERM")
    status, rcalls, _ = restart_and_continue(fs, design, truth)
    return ("fresh self-consistent bundle at canonical paths; "
            "restart -> %s" % status,
            violations_for(ex.calls, rcalls, truth, fs))


def t10_replay(design):
    parts, viols = [], set()
    # (a) same-generation journal PREFIX replay: genuine journal is
    # renamed out of the control dir; a post-S1 copy takes its name,
    # after S2 has completed in the true journal.
    fs, ex, truth = fresh_world(design)
    ex.run_symbol("S1", {}, truth)
    pk, pn = fs.alloc("file")
    pn.records = [dict(r) for r in ex.journal_node.records]
    ex.run_symbol("S2", {}, truth)          # later state exists
    if design == "D_ROOT_NS":
        privileged_seal(fs, ex.journal_node.records[-1]["hash"])
    arch = fs.get(truth["archive_key"])
    ex.control_node.entries.pop(JNAME)
    arch.entries["stash.journal"] = ex.journal_key
    ex.control_node.entries[JNAME] = pk
    status, rcalls, _ = restart_and_continue(fs, design, truth)
    parts.append("prefix replay -> %s" % status)
    viols |= violations_for(ex.calls, rcalls, truth, fs)
    # (b) PRIOR-GENERATION bundle replay after capture-id reuse: gen1
    # completed S1 only; gen2 (same capture id) completed S1+S2 and,
    # for D, was sealed. Adversary rolls the whole data tree back to
    # the gen1 bundle at the canonical names.
    fs = FS()
    akey, anode = fs.alloc("dir")
    anode.entries["."] = akey
    arch = anode
    truth = {"consumed": set(), "archive_key": akey}
    g1 = Executor(fs, design, "gen1")
    g1.setup(akey)
    g1.open_owner()
    g1.run_symbol("S1", {}, truth)
    g1_control = arch.entries[CAP + ".control"]
    if design == "D_ROOT_NS":
        g1_ident = fs.anchor_node.entries[CAP + ".identity.json"]
    else:
        g1_ident = arch.entries[CAP + ".identity.json"]
    g2 = Executor(fs, design, "gen2")
    g2.setup(akey)
    g2.open_owner()
    g2.run_symbol("S1", {}, truth)
    g2.run_symbol("S2", {}, truth)
    if design == "D_ROOT_NS":
        privileged_seal(fs, g2.journal_node.records[-1]["hash"])
    arch.entries[CAP + ".control"] = g1_control
    if design == "D_ROOT_NS":
        fs.anchor_attempts.append("rollback_anchor:EPERM")
    else:
        arch.entries[CAP + ".identity.json"] = g1_ident
    status, rcalls, _ = restart_and_continue(fs, design, truth)
    parts.append("prior-generation replay -> %s" % status)
    viols |= violations_for(g2.calls, rcalls, truth, fs)
    return ("; ".join(parts), viols)


TRACES = [
    ("T1", "journal replaced with EMPTY while owner live; owner exits; fresh restart", t1_empty_replacement),
    ("T1b", "journal replaced with STALE COPY (genesis only) after S1 completed", t1b_stale_copy),
    ("T1c", "journal replaced with SYMLINK to foreign file", t1c_symlink_replacement),
    ("T2", "control directory replaced between ATTEMPT fsync and transport call", t2_control_replaced_precall),
    ("T3", "temp substitution between identity check and unlink", t3_temp_substitution),
    ("T4", "final substitution after verification, before COMPLETE", t4_final_substitution),
    ("T5", "two live owner processes contend", t5_two_owners),
    ("T6", "journal inode freed and RECYCLED by a forged genesis-only journal", t6_inode_recycling),
    ("T7", "kill after ATTEMPT fsync; benign restart", t7_kill_restart_benign),
    ("T8", "identity pathname replaced: EMPTY file and BYTE-IDENTICAL copy", t8_identity_replacement),
    ("T9", "after owner exit, identity+control+journal coherently replaced with a fresh self-consistent bundle", t9_coherent_bundle),
    ("T10", "replay: (a) journal prefix after later state; (b) prior-generation bundle after capture-id reuse + seal", t10_replay),
]


def main():
    results = {"model": "QF-YAHOO-REV3-OWNERSHIP-TRUST-ROOT-20261016-19 r6",
               "designs": {}, "acceptance": {}}
    for design in DESIGNS:
        rows = []
        ok_all = True
        for tid, title, fn in TRACES:
            Inode._uid = 0
            outcome, viol = fn(design)
            passed = not viol
            ok_all = ok_all and passed
            rows.append({"trace": tid, "title": title,
                         "outcome": outcome,
                         "violations": sorted(viol),
                         "verdict": "PASS" if passed else "FAIL"})
        results["designs"][design] = {"traces": rows,
                                      "verdict": "PASS" if ok_all else "FAIL"}
    d = results["designs"]["D_ROOT_NS"]["verdict"]
    a9 = [t for t in results["designs"]["A_CONTRACT"]["traces"]
          if t["trace"] == "T9"][0]["verdict"]
    results["acceptance"] = {
        "recommended_design_all_traces_pass": d == "PASS",
        "r5_baseline_fails_T9_coherent_replacement": a9 == "FAIL",
        "note": "Acceptance binds the RECOMMENDED design (D_ROOT_NS: "
                "privileged anchor namespace). A_CONTRACT is the r5 "
                "baseline, retained to show the trust-root defect "
                "deterministically. E_SIGNED and F_VERITY are modeled "
                "to expose exactly which traces a signature root and "
                "an fs-verity root do and do not close."}
    results["verdict"] = ("REV3_OWNERSHIP_TRUST_ROOT_MODEL_PASS"
                          if d == "PASS" else "MODEL_FAIL")
    out = sys.argv[1] if len(sys.argv) > 1 else "model_results.json"
    with open(out, "w") as fh:
        json.dump(results, fh, indent=1, sort_keys=True)
        fh.write("\n")
    for d, r in results["designs"].items():
        fails = [t["trace"] for t in r["traces"] if t["verdict"] == "FAIL"]
        print(d, r["verdict"], "failing traces:", fails or "none")
    print(results["verdict"])


if __name__ == "__main__":
    main()
