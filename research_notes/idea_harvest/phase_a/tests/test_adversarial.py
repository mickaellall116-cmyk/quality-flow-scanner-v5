#!/usr/bin/env python3
"""Adversarial process/crash tests for the Phase A store.

QF-IDEA-PHASE-A-CORRECTNESS-20261013-02 r1. These tests attack the five
defects proved against store phase-a-store/1.0.0:

  A1 unlocked writes          — mutations without the lease must refuse
  A2 lock takeover race       — a displaced owner must be fenced out
  A3 orphan card              — kill -9 between card write and event append
  A4 missing-newline append   — unterminated tail must not merge records
  A5 ID amendment             — run/event IDs are UUIDs, unique per attempt

Real subprocesses are spawned (this file re-invoked with --child), real
SIGKILLs are delivered, and JSONL tails are pre-corrupted on disk. No
in-process simulations of crashes.

Run: python3 tests/test_adversarial.py   (from the phase_a/ directory)
"""
import json
import re
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import store as S  # noqa: E402

THIS = Path(__file__).resolve()


def cand(claim, family="volume_premium"):
    return {
        "claim": claim,
        "hypothesis": "Falsifiable form: " + claim,
        "strategy_family": family,
        "timeframe": "Daily; 1-month hold",
        "mechanically_definable": True,
        "pit_data": "yes",
        "pit_inputs": ["daily close"],
        "source": {
            "authors": "Doe & Roe",
            "title": "A Paper About: " + claim,
            "venue": "Journal of Finance 1 (2020)",
            "url": "https://example.org/paper",
            "accessed_at": "2026-10-13T21:00:00-04:00",
            "access_basis": "publisher abstract page — abstract only",
            "evidence": "Abstract states: " + claim,
            "content_hash": S.content_hash("A Paper", "Abstract: " + claim),
            "extractor_version": S.EXTRACTOR_VERSION,
            "is_primary": True,
            "source_class": "SRC-JOURNAL-PAGES",
            "doi": "",
        },
        "limitations": ["Synthetic adversarial-test limitation."],
        "lane_fit": "daily",
        "created_at": "2026-10-13T21:00:00-04:00",
        "created_by": "idea-harvest-weekly",
    }


def wait_for(path, timeout=20.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if Path(path).exists():
            return True
        time.sleep(0.05)
    return False


def spawn_child(mode, *args):
    return subprocess.Popen(
        [sys.executable, str(THIS), "--child", mode, *[str(a) for a in args]],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


# ---------------------------------------------------------------------------
# Child processes
# ---------------------------------------------------------------------------

def child_hold(root, ready, go, outcome):
    st = S.Store(Path(root))
    st.init_layout()
    run = st.new_run_id()
    st.acquire_lease(run)
    st.append_event("RUN_START", run)
    Path(ready).write_text(run, encoding="utf-8")
    if not wait_for(go, timeout=30):
        Path(outcome).write_text("TIMEOUT", encoding="utf-8")
        return
    try:
        st.append_event("RUN_END", run)
        Path(outcome).write_text("WROTE", encoding="utf-8")
    except Exception as exc:  # report the exact refusal class
        Path(outcome).write_text(type(exc).__name__, encoding="utf-8")


def child_orphan(root, ready):
    st = S.Store(Path(root))
    st.init_layout()
    run = st.new_run_id()
    st.acquire_lease(run)
    st.append_event("RUN_START", run)
    card = cand("Orphaned by a kill -9 between card and event.")
    card["claim_normalized"] = S.normalize_claim(card["claim"])
    card["dedup_key"] = S.dedup_key(card["claim_normalized"], card["source"])
    card["idea_id"] = f"IDEA-2026-{st.next_idea_seq():04d}"
    errs = S.validate_card(card, st.sources_idx, new_intake=True)
    assert not errs, errs
    st.write_card(card)          # durable card, then "crash" before the event
    Path(ready).write_text(card["idea_id"], encoding="utf-8")
    time.sleep(60)               # parent SIGKILLs inside this window


def child_ingestloop(root, ready):
    st = S.Store(Path(root))
    st.init_layout()
    run = st.new_run_id()
    st.acquire_lease(run)
    st.append_event("RUN_START", run)
    Path(ready).write_text(run, encoding="utf-8")
    i = 0
    while True:
        i += 1
        st.ingest(cand(f"Loop claim number {i} appreciates.",
                       family="loop_family"), run)


def child_runids(root, out):
    st = S.Store(Path(root))
    Path(out).write_text("\n".join(st.new_run_id() for _ in range(3)),
                         encoding="utf-8")


CHILDREN = {"hold": child_hold, "orphan": child_orphan,
            "ingestloop": child_ingestloop, "runids": child_runids}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class AdversarialTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="phasea-adv-")
        self.root = Path(self.tmp) / "store"
        self.procs = []

    def tearDown(self):
        for p in self.procs:
            if p.poll() is None:
                p.kill()
                p.wait(timeout=10)
            for stream in (p.stdout, p.stderr):
                if stream:
                    stream.close()

    def spawn(self, mode, *args):
        p = spawn_child(mode, *args)
        self.procs.append(p)
        return p


class TestUnlockedWrites(AdversarialTestCase):
    def test_mutations_require_lease_in_process(self):
        st = S.Store(self.root)
        st.init_layout()
        run = st.new_run_id()
        with self.assertRaises(S.FencingError):
            st.append_event("RUN_START", run)
        with self.assertRaises(S.FencingError):
            st.write_card({"idea_id": "IDEA-2026-0001"})
        with self.assertRaises(S.FencingError):
            st.ingest(cand("No lease, no ingest."), run)
        with self.assertRaises(S.FencingError):
            S.materialize_drafts(st, run,
                                 out_path=Path(self.tmp) / "d.json")
        # Holding the lease works; releasing it revokes write access.
        st.acquire_lease(run)
        st.append_event("RUN_START", run)
        st.release_lease()
        with self.assertRaises(S.FencingError):
            st.append_event("RUN_END", run)

    def test_unleased_process_cannot_write_while_holder_active(self):
        ready, go, outcome = (Path(self.tmp) / n
                              for n in ("ready", "go", "outcome"))
        child = self.spawn("hold", self.root, ready, go, outcome)
        self.assertTrue(wait_for(ready), "holder child never became ready")
        run = Path(ready).read_text(encoding="utf-8")
        mine = S.Store(self.root)
        with self.assertRaises(S.FencingError):
            mine.append_event("RUN_START", mine.new_run_id())
        with self.assertRaises(S.LeaseHeldError):
            mine.acquire_lease(mine.new_run_id())
        go.write_text("go", encoding="utf-8")
        child.wait(timeout=20)
        self.assertEqual(Path(outcome).read_text(encoding="utf-8"), "WROTE")
        events = S.Store(self.root).read_events()
        self.assertEqual([e["event_type"] for e in events],
                         ["RUN_START", "RUN_END"])
        self.assertTrue(all(e["run_id"] == run for e in events))


class TestTakeoverFencing(AdversarialTestCase):
    def test_displaced_owner_release_cannot_delete_new_lock(self):
        # In-process companion to the subprocess race below: after a
        # takeover, the displaced owner's release_lease() must be a no-op
        # — it must NOT unlink the new owner's lockfile.
        a = S.Store(self.root)
        a.init_layout()
        run_a = a.new_run_id()
        a.acquire_lease(run_a)
        lock_path = self.root / "pipeline.lock"
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
        aged = datetime.now().astimezone() - timedelta(hours=3)
        payload["acquired_at"] = aged.isoformat(timespec="seconds")
        payload["pid"] = 999999  # dead pid: unambiguously stale
        lock_path.write_text(json.dumps(payload), encoding="utf-8")
        b = S.Store(self.root)
        run_b = b.new_run_id()
        kind, _ = b.acquire_lease(run_b)
        self.assertEqual(kind, "broke-stale")
        a.release_lease()  # displaced owner "releases"
        self.assertTrue(lock_path.exists())
        current = json.loads(lock_path.read_text(encoding="utf-8"))
        self.assertEqual(current["run_id"], run_b)
        b.append_event("RUN_START", run_b)  # new owner still writes
        b.release_lease()
        self.assertFalse(lock_path.exists())

    def test_stale_takeover_fences_displaced_owner(self):
        ready, go, outcome = (Path(self.tmp) / n
                              for n in ("ready", "go", "outcome"))
        child = self.spawn("hold", self.root, ready, go, outcome)
        self.assertTrue(wait_for(ready), "holder child never became ready")
        # Forge staleness exactly as an aged-out lease would present:
        # same live PID, same fencing token, acquired_at 3h in the past.
        lock_path = self.root / "pipeline.lock"
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
        aged = datetime.now().astimezone() - timedelta(hours=3)
        payload["acquired_at"] = aged.isoformat(timespec="seconds")
        lock_path.write_text(json.dumps(payload), encoding="utf-8")
        mine = S.Store(self.root)
        run_b = mine.new_run_id()
        kind, _info = mine.acquire_lease(run_b)
        self.assertEqual(kind, "broke-stale")
        mine.append_event("RUN_START", run_b)   # new owner writes fine
        go.write_text("go", encoding="utf-8")
        child.wait(timeout=20)
        # The displaced original owner is STILL ALIVE and tried to write:
        self.assertEqual(Path(outcome).read_text(encoding="utf-8"),
                         "FencingError")
        mine.verify_chain()
        mine.release_lease()
        types = [e["event_type"] for e in S.Store(self.root).read_events()]
        self.assertEqual(types, ["RUN_START", "RUN_START"])  # no RUN_END


class TestOrphanRecovery(AdversarialTestCase):
    def test_kill9_orphan_card_adopted(self):
        ready = Path(self.tmp) / "ready"
        child = self.spawn("orphan", self.root, ready)
        self.assertTrue(wait_for(ready), "orphan child never became ready")
        orphan_id = Path(ready).read_text(encoding="utf-8")
        child.send_signal(signal.SIGKILL)
        child.wait(timeout=10)
        st = S.Store(self.root)
        run = st.new_run_id()
        kind, info = st.acquire_lease(run)
        self.assertEqual(kind, "broke-stale")  # dead PID
        adopted = [a for a in info["reconciled"]
                   if a.get("action") == "adopted"
                   and a.get("idea_id") == orphan_id]
        self.assertEqual(len(adopted), 1, info["reconciled"])
        self.assertIsNotNone(st.read_card(orphan_id))
        self.assertEqual(st.current_states()[orphan_id], "INGESTED")
        rec = [e for e in st.read_events()
               if e.get("idea_id") == orphan_id
               and e["event_type"] == "INGESTED"]
        self.assertEqual(len(rec), 1)
        self.assertTrue(rec[0].get("recovered_orphan"))
        st.verify_chain()
        st.release_lease()

    def test_kill9_during_ingest_loop_keeps_invariant(self):
        ready = Path(self.tmp) / "ready"
        child = self.spawn("ingestloop", self.root, ready)
        self.assertTrue(wait_for(ready), "loop child never became ready")
        time.sleep(1.0)
        child.send_signal(signal.SIGKILL)
        child.wait(timeout=10)
        st = S.Store(self.root)
        try:
            st.acquire_lease(st.new_run_id())
        except S.ChainVerificationError:
            # The kill landed inside the single write+fsync of one event:
            # a torn final line. The required behavior is a loud abort,
            # never a merge or silent repair — verify exactly that.
            raw = st.log_path.read_bytes()
            last = raw.rstrip(b"\n").split(b"\n")[-1]
            with self.assertRaises(json.JSONDecodeError):
                json.loads(last.decode("utf-8"))
            return
        events = st.read_events()
        known = {e.get("idea_id") for e in events
                 if e.get("event_type") in ("INGESTED", "MIGRATED")}
        cards = st.all_cards()
        self.assertGreaterEqual(len(cards), 1)
        self.assertTrue(set(cards) <= known,
                        "every durable card has its INGESTED event "
                        "after reconciliation")
        st.verify_chain()
        st.release_lease()


class TestTailTermination(AdversarialTestCase):
    def _seeded_store(self):
        st = S.Store(self.root)
        st.init_layout()
        run = st.new_run_id()
        st.acquire_lease(run)
        st.append_event("RUN_START", run)
        st.ingest(cand("Tail termination seed claim."), run)
        st.append_event("RUN_END", run)
        st.release_lease()
        return S.Store(self.root).read_events()

    def test_unterminated_valid_tail_is_terminated_not_merged(self):
        before = self._seeded_store()
        raw = self.root.joinpath("queue", "queue_log.jsonl").read_bytes()
        self.assertTrue(raw.endswith(b"\n"))
        log = self.root / "queue" / "queue_log.jsonl"
        log.write_bytes(raw[:-1])  # strip ONLY the final newline
        st = S.Store(self.root)
        run = st.new_run_id()
        st.acquire_lease(run)
        st.append_event("RUN_START", run)
        st.release_lease()
        events = S.Store(self.root).read_events()
        self.assertEqual(len(events), len(before) + 1)
        self.assertEqual(events[-1]["event_type"], "RUN_START")
        S.Store(self.root).verify_chain(events)

    def test_torn_tail_aborts_loudly_and_writes_nothing(self):
        self._seeded_store()
        log = self.root / "queue" / "queue_log.jsonl"
        raw = log.read_bytes()
        torn = raw[:-40]  # cut mid-line through the final event
        log.write_bytes(torn)
        st = S.Store(self.root)
        with self.assertRaises(S.ChainVerificationError):
            st.acquire_lease(st.new_run_id())
            st.append_event("RUN_START", st.new_run_id())
        try:
            st.release_lease()
        except Exception:
            pass
        self.assertEqual(log.read_bytes(), torn)  # untouched, unmerged


class TestUuidIds(AdversarialTestCase):
    RUN_RE = re.compile(r"^RUN-\d{8}-[0-9a-f]{12}$")
    EVT_RE = re.compile(r"^EVT-[0-9a-f]{32}$")

    def test_run_ids_unique_across_processes_same_log_state(self):
        outs, procs = [], []
        for i in range(6):
            out = Path(self.tmp) / f"runids-{i}"
            outs.append(out)
            procs.append(self.spawn("runids", self.root, out))
        for p in procs:
            p.wait(timeout=20)
        ids = []
        for out in outs:
            ids.extend(out.read_text(encoding="utf-8").split())
        self.assertEqual(len(ids), 18)
        self.assertEqual(len(set(ids)), 18)  # zero collisions
        self.assertTrue(all(self.RUN_RE.match(i) for i in ids))

    def test_event_ids_are_uuids_and_record_their_run(self):
        st = S.Store(self.root)
        st.init_layout()
        run_a = st.new_run_id()
        st.acquire_lease(run_a)
        st.append_event("RUN_START", run_a)
        st.ingest(cand("First run claim."), run_a)
        st.release_lease()
        run_b = st.new_run_id()
        st.acquire_lease(run_b)
        st.append_event("RUN_START", run_b)
        st.ingest(cand("Second run claim."), run_b)
        st.release_lease()
        self.assertNotEqual(run_a, run_b)
        events = S.Store(self.root).read_events()
        ev_ids = [e["event_id"] for e in events]
        self.assertTrue(all(self.EVT_RE.match(i) for i in ev_ids))
        self.assertEqual(len(set(ev_ids)), len(ev_ids))
        by_run = {}
        for e in events:
            by_run.setdefault(e["run_id"], 0)
            by_run[e["run_id"]] += 1
        self.assertEqual(set(by_run), {run_a, run_b})


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        CHILDREN[sys.argv[2]](*sys.argv[3:])
        sys.exit(0)
    unittest.main(verbosity=2)
