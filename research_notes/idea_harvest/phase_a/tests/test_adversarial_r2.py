#!/usr/bin/env python3
"""Adversarial process/crash tests for the Phase A store — R2 round.

QF-IDEA-PHASE-A-CORRECTNESS-R2-20261013-04 r1. Attacks the three gaps
ChatGPT's re-review found in store phase-a-store/1.1.0 (Issue #1 comment
6159623983):

  B1 takeover TOCTOU  — an age-based stale break must NEVER displace a
                        lock whose recorded PID is alive
  B2 unfenced reconciliation — reconcile_orphans must verify the fence
                        before any mutation, and a quarantine must be
                        logged BEFORE the card file moves (crash order)
  B3 init race        — concurrent init_layout must adopt the existing
                        log, never truncate or reset it

Real subprocesses throughout (this file re-invoked with --child), real
SIGKILL-equivalent hard exits (os._exit mid-operation), on-disk lock
forgery. Run: python3 tests/test_adversarial_r2.py  (from phase_a/)
"""
import json
import os
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
        "limitations": ["Synthetic R2 adversarial-test limitation."],
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
    except Exception as exc:
        Path(outcome).write_text(type(exc).__name__, encoding="utf-8")


def child_quarantine_crash(root, ready):
    """Plant an invalid orphan card, then hard-crash (os._exit) at the
    exact instant reconciliation tries to MOVE the card into quarantine —
    i.e. after the ERROR event has been appended, before the move."""
    st = S.Store(Path(root))
    st.init_layout()
    run = st.new_run_id()
    st.acquire_lease(run)
    st.append_event("RUN_START", run)
    card = cand("Invalid orphan planted for the quarantine crash test.")
    card["claim_normalized"] = S.normalize_claim(card["claim"])
    card["dedup_key"] = "sha256:" + "f" * 64  # does not recompute
    card["idea_id"] = "IDEA-2026-0007"
    st.write_card(card)  # durable card, no event: an orphan
    real_replace = os.replace

    def crashing_replace(src, dst):
        if "orphaned" in str(dst):
            os._exit(42)  # crash after the log append, before the move
        return real_replace(src, dst)

    os.replace = crashing_replace
    Path(ready).write_text(card["idea_id"], encoding="utf-8")
    st.reconcile_orphans(run)
    os._exit(3)  # unreachable if the crash fired


def child_initrace(root, go, rounds):
    if not wait_for(go, timeout=30):
        return
    st = S.Store(Path(root))
    for _ in range(int(rounds)):
        st.init_layout()


CHILDREN = {"hold": child_hold, "quarantinecrash": child_quarantine_crash,
            "initrace": child_initrace}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class R2TestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="phasea-r2-")
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


class TestLivePidNeverDisplaced(R2TestCase):
    def test_live_pid_aged_lock_takeover_refused(self):
        ready, go, outcome = (Path(self.tmp) / n
                              for n in ("ready", "go", "outcome"))
        child = self.spawn("hold", self.root, ready, go, outcome)
        self.assertTrue(wait_for(ready), "holder child never became ready")
        run = Path(ready).read_text(encoding="utf-8")
        # Age the lock 3h into the past; the recorded PID stays the
        # holder's REAL, LIVE pid. Under the r1 rule this broke the
        # lease; under the r2 rule a live PID is never displaced.
        lock_path = self.root / "pipeline.lock"
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
        self.assertTrue(S._pid_alive(payload["pid"]))
        aged = datetime.now().astimezone() - timedelta(hours=3)
        payload["acquired_at"] = aged.isoformat(timespec="seconds")
        lock_path.write_text(json.dumps(payload), encoding="utf-8")
        mine = S.Store(self.root)
        with self.assertRaises(S.LeaseHeldError):
            mine.acquire_lease(mine.new_run_id())
        # The lock on disk is still the child's, untouched.
        current = json.loads(lock_path.read_text(encoding="utf-8"))
        self.assertEqual(current["run_id"], run)
        # And the holder can still write: it was never displaced.
        go.write_text("go", encoding="utf-8")
        child.wait(timeout=20)
        self.assertEqual(Path(outcome).read_text(encoding="utf-8"), "WROTE")
        events = S.Store(self.root).read_events()
        self.assertEqual([e["event_type"] for e in events],
                         ["RUN_START", "RUN_END"])
        self.assertTrue(all(e["run_id"] == run for e in events))
        S.Store(self.root).verify_chain(events)

    def test_pidless_lock_uses_mtime_abandonment_test(self):
        # No usable PID recorded: a FRESH lockfile must not be breakable
        # (it may be mid-creation); an ANCIENT one (mtime) is abandoned.
        st = S.Store(self.root)
        st.init_layout()
        lock_path = self.root / "pipeline.lock"
        lock_path.write_text(json.dumps({"run_id": "RUN-GHOST"}),
                             encoding="utf-8")
        mine = S.Store(self.root)
        with self.assertRaises(S.LeaseHeldError):
            mine.acquire_lease(mine.new_run_id())
        old = time.time() - 3 * 3600
        os.utime(lock_path, (old, old))
        kind, _info = mine.acquire_lease(mine.new_run_id())
        self.assertEqual(kind, "broke-stale")
        mine.release_lease()


class TestReconcileFencing(R2TestCase):
    def _plant_orphan(self, st, idea_id="IDEA-2026-0007"):
        path = st.card_path(idea_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        card = cand("Planted orphan for reconcile fencing test.")
        card["claim_normalized"] = S.normalize_claim(card["claim"])
        card["dedup_key"] = "sha256:" + "f" * 64
        card["idea_id"] = idea_id
        path.write_text(json.dumps(card, indent=2), encoding="utf-8")
        return path

    def test_reconcile_refused_without_lease(self):
        st = S.Store(self.root)
        st.init_layout()
        card_path = self._plant_orphan(st)
        log_before = st.log_path.read_bytes()
        with self.assertRaises(S.FencingError):
            st.reconcile_orphans("RUN-UNLEASED")
        self.assertTrue(card_path.exists())  # nothing moved
        self.assertFalse((st.ideas_dir / "orphaned").exists())
        self.assertEqual(st.log_path.read_bytes(), log_before)

    def test_reconcile_refused_with_stale_fencing(self):
        st = S.Store(self.root)
        st.init_layout()
        run = st.new_run_id()
        st.acquire_lease(run)  # clean store: reconcile inside is a no-op
        card_path = self._plant_orphan(st)  # orphan appears AFTER acquire
        # Displace this instance on disk (token replaced, as a takeover
        # would): its fencing is now stale.
        lock = json.loads(st.lock_path.read_text(encoding="utf-8"))
        lock["fence_token"] = "0" * 32
        st.lock_path.write_text(json.dumps(lock), encoding="utf-8")
        log_before = st.log_path.read_bytes()
        with self.assertRaises(S.FencingError):
            st.reconcile_orphans(run)
        self.assertTrue(card_path.exists())  # nothing moved
        self.assertFalse((st.ideas_dir / "orphaned").exists())
        self.assertEqual(st.log_path.read_bytes(), log_before)

    def test_quarantine_crash_order_completes_without_duplicate(self):
        ready = Path(self.tmp) / "ready"
        child = self.spawn("quarantinecrash", self.root, ready)
        self.assertTrue(wait_for(ready), "quarantine child never ready")
        idea_id = Path(ready).read_text(encoding="utf-8")
        rc = child.wait(timeout=20)
        self.assertEqual(rc, 42)  # crashed at the move, after the append
        st = S.Store(self.root)
        # The ERROR event is already in the log; the card has NOT moved.
        errors = [e for e in st.read_events()
                  if e.get("idea_id") == idea_id
                  and e["event_type"] == "ERROR"
                  and e.get("quarantined_orphan")]
        self.assertEqual(len(errors), 1)
        self.assertTrue(st.card_path(idea_id).exists())
        # Next startup reconciliation completes the pending move under
        # the new lease — without appending a second ERROR event.
        run = st.new_run_id()
        kind, info = st.acquire_lease(run)
        self.assertEqual(kind, "broke-stale")  # crashed child's dead pid
        completed = [a for a in info["reconciled"]
                     if a.get("action") == "quarantine-completed"
                     and a.get("idea_id") == idea_id]
        self.assertEqual(len(completed), 1, info["reconciled"])
        self.assertFalse(st.card_path(idea_id).exists())
        self.assertTrue((st.ideas_dir / "orphaned"
                         / f"{idea_id}.json").exists())
        errors_after = [e for e in st.read_events()
                        if e.get("idea_id") == idea_id
                        and e["event_type"] == "ERROR"]
        self.assertEqual(len(errors_after), 1)  # still exactly one
        st.verify_chain()
        st.release_lease()


class TestInitRace(R2TestCase):
    def test_concurrent_init_fresh_root_single_intact_log(self):
        go = Path(self.tmp) / "go"
        procs = [self.spawn("initrace", self.root, go, 100)
                 for _ in range(8)]
        go.write_text("go", encoding="utf-8")
        for p in procs:
            self.assertEqual(p.wait(timeout=30), 0)
        log = self.root / "queue" / "queue_log.jsonl"
        self.assertTrue(log.exists())
        self.assertEqual(log.read_bytes(), b"")  # one log, never reset
        st = S.Store(self.root)  # store fully usable afterwards
        run = st.new_run_id()
        st.acquire_lease(run)
        st.append_event("RUN_START", run)
        st.release_lease()
        self.assertEqual(len(S.Store(self.root).read_events()), 1)

    def test_concurrent_init_never_truncates_seeded_log(self):
        st = S.Store(self.root)
        st.init_layout()
        run = st.new_run_id()
        st.acquire_lease(run)
        st.append_event("RUN_START", run)
        st.ingest(cand("Seeded claim that must survive init races."), run)
        st.append_event("RUN_END", run)
        st.release_lease()
        before = st.log_path.read_bytes()
        self.assertGreater(len(before), 0)
        go = Path(self.tmp) / "go"
        procs = [self.spawn("initrace", self.root, go, 200)
                 for _ in range(8)]
        go.write_text("go", encoding="utf-8")
        for p in procs:
            self.assertEqual(p.wait(timeout=30), 0)
        self.assertEqual(st.log_path.read_bytes(), before)  # byte-identical
        S.Store(self.root).verify_chain()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        CHILDREN[sys.argv[2]](*sys.argv[3:])
        sys.exit(0)
    unittest.main(verbosity=2)
