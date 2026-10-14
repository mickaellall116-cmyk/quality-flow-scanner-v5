#!/usr/bin/env python3
"""Unit tests for the Phase A store (QF-IDEA-PIPELINE-PHASE-A-20261013-01).

Run: python3 tests/test_store.py   (from the phase_a/ directory)
All tests use scratch stores in temp dirs; no network, no live store.
"""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import store as S  # noqa: E402

FIXED = ["2026-10-13T21:00:00-04:00"]


def fixed_clock():
    return FIXED[0]


def candidate(**over):
    base = {
        "claim": "Stocks with unusually high volume appreciate next month.",
        "hypothesis": "High abnormal volume predicts positive forward returns.",
        "strategy_family": "volume_premium",
        "timeframe": "Daily OHLCV; ~1-month forward window",
        "mechanically_definable": True,
        "pit_data": "yes",
        "pit_inputs": ["daily volume", "daily close"],
        "source": {
            "authors": "Gervais, Kaniel & Mingelgrin",
            "title": "The High-Volume Return Premium",
            "venue": "Journal of Finance 56 (2001)",
            "url": "https://example.org/gkm2001",
            "accessed_at": "2026-10-13T21:00:00-04:00",
            "access_basis": "publisher abstract page — abstract only",
            "evidence": "Abstract states the high-volume return premium.",
            "content_hash": S.content_hash(
                "The High-Volume Return Premium",
                "Abstract states the high-volume return premium."),
            "extractor_version": S.EXTRACTOR_VERSION,
            "is_primary": True,
            "source_class": "SRC-JOURNAL-PAGES",
            "doi": "",
        },
        "limitations": ["Volume conventions vary by vendor."],
        "lane_fit": "daily",
        "created_at": "2026-10-13T21:00:00-04:00",
        "created_by": "idea-harvest-weekly",
    }
    base.update(over)
    return base


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="phasea-test-")
        self.store = S.Store(Path(self.tmp) / "store", clock=fixed_clock)
        self.store.init_layout()
        self.run = "RUN-20261013-001"
        self.store.acquire_lease(self.run)

    def tearDown(self):
        try:
            self.store.release_lease()
        except Exception:
            pass


class TestCanonicalAndKeys(StoreTestCase):
    def test_canonical_text_stable(self):
        a = S.canonical_text("<p>Hello   World</p>\nNew\tLine")
        b = S.canonical_text("hello world new line")
        self.assertEqual(a, b)

    def test_content_hash_changes_with_text(self):
        h1 = S.content_hash("T", "body one")
        h2 = S.content_hash("T", "body two")
        self.assertNotEqual(h1, h2)
        self.assertTrue(h1.startswith("sha256:"))

    def test_dedup_key_normalization(self):
        c1 = candidate(claim="High Volume!!  Appreciates.")
        c2 = candidate(claim="high volume appreciates")
        k1 = S.dedup_key(S.normalize_claim(c1["claim"]), c1["source"])
        k2 = S.dedup_key(S.normalize_claim(c2["claim"]), c2["source"])
        self.assertEqual(k1, k2)


class TestValidation(StoreTestCase):
    def test_license_key_forbidden(self):
        c = candidate()
        c["source"]["license"] = "MIT"
        with self.assertRaises(S.CardValidationError) as ctx:
            self.store.ingest(c, self.run)
        self.assertTrue(any("access_basis" in e for e in ctx.exception.errors))

    def test_empty_limitations_fail(self):
        with self.assertRaises(S.CardValidationError):
            self.store.ingest(candidate(limitations=[]), self.run)

    def test_parked_source_refused_for_new_intake(self):
        c = candidate()
        c["source"]["source_class"] = "SRC-SSRN"
        with self.assertRaises(S.CardValidationError) as ctx:
            self.store.ingest(c, self.run)
        self.assertTrue(any("SOURCE_PARKED" in e
                            for e in ctx.exception.errors))

    def test_secondary_cannot_be_primary(self):
        c = candidate()
        c["source"]["source_class"] = "SRC-GITHUB-REPOS"
        with self.assertRaises(S.CardValidationError):
            self.store.ingest(c, self.run)

    def test_unspecified_timeframe_fails(self):
        with self.assertRaises(S.CardValidationError):
            self.store.ingest(candidate(timeframe="Unspecified"), self.run)


class TestIngestAndTransitions(StoreTestCase):
    def test_ingest_rank_shortlist_flow(self):
        res = self.store.ingest(candidate(), self.run)
        self.assertEqual(res["outcome"], "ingested")
        iid = res["idea_id"]
        self.store.transition(iid, "RANKED", self.run, rank=1,
                              score_breakdown={"testability": 3,
                                               "novelty": 3, "lane_fit": 3})
        self.store.transition(iid, "SHORTLISTED", self.run)
        self.assertEqual(self.store.current_states()[iid], "SHORTLISTED")
        self.store.verify_chain()

    def test_duplicate_seen_no_new_id(self):
        r1 = self.store.ingest(candidate(), self.run)
        r2 = self.store.ingest(candidate(), self.run)
        self.assertEqual(r2["outcome"], "duplicate")
        self.assertEqual(r2["idea_id"], r1["idea_id"])
        self.assertEqual(len(self.store.all_cards()), 1)
        types = [e["event_type"] for e in self.store.read_events()]
        self.assertIn("DUPLICATE_SEEN", types)

    def test_seed_reject_and_terminal(self):
        c = candidate(strategy_family="ml_price_forecasting",
                      claim="An LSTM forecasts trend from price features.")
        res = self.store.ingest(c, self.run)
        self.assertEqual(res["outcome"], "rejected")
        iid = res["idea_id"]
        with self.assertRaises(S.IllegalTransitionError):
            self.store.transition(iid, "RANKED", self.run)

    def test_seed_family_with_justification_flags_not_verdicts(self):
        c = candidate(strategy_family="ml_price_forecasting",
                      claim="A state-space filter forecasts volatility "
                            "regimes, not prices.",
                      materially_different_mechanism="Forecasts volatility "
                                                     "regimes; no price "
                                                     "prediction.")
        res = self.store.ingest(c, self.run)
        self.assertEqual(res["outcome"], "ingested")
        self.assertTrue(res["adjacency_flag"])

    def test_forbidden_targets_refused(self):
        res = self.store.ingest(candidate(), self.run)
        iid = res["idea_id"]
        self.store.transition(iid, "RANKED", self.run, rank=2)
        self.store.transition(iid, "SHORTLISTED", self.run)
        for target in ("PREREGISTERED", "ELIGIBLE"):
            with self.assertRaises(S.IllegalTransitionError):
                self.store.transition(iid, target, self.run)
        self.assertEqual(self.store.current_states()[iid], "SHORTLISTED")
        errs = [e for e in self.store.read_events()
                if e["event_type"] == "ERROR"]
        self.assertEqual(len(errs), 2)

    def test_transition_requires_reason(self):
        res = self.store.ingest(candidate(), self.run)
        with self.assertRaises(S.IllegalTransitionError):
            self.store.transition(res["idea_id"], "BLOCKED-DATA", self.run)

    def test_card_immutability(self):
        res = self.store.ingest(candidate(), self.run)
        card = self.store.read_card(res["idea_id"])
        with self.assertRaises(S.StoreError):
            self.store.write_card(card)

    def test_registry_write_refused(self):
        with self.assertRaises(S.ScopeViolation):
            self.store.guard_registry_write("research_notes/research_loop/"
                                            "registry.json")


class TestLeaseAndChain(StoreTestCase):
    def test_second_writer_refused_live_lease(self):
        other = S.Store(Path(self.tmp) / "store", clock=fixed_clock)
        with self.assertRaises(S.LeaseHeldError):
            other.acquire_lease("RUN-20261013-002")

    def test_chain_tamper_detected(self):
        self.store.ingest(candidate(), self.run)
        events = self.store.read_events()
        events[0]["reason"] = "tampered"
        with self.assertRaises(S.ChainVerificationError):
            self.store.verify_chain(events)


class TestMaterializers(StoreTestCase):
    def test_draft_materialization_deterministic(self):
        res = self.store.ingest(candidate(), self.run)
        iid = res["idea_id"]
        self.store.transition(iid, "RANKED", self.run, rank=1)
        self.store.transition(iid, "SHORTLISTED", self.run)
        p1 = Path(self.tmp) / "d1.json"
        p2 = Path(self.tmp) / "d2.json"
        S.materialize_drafts(self.store, self.run, out_path=p1)
        first = p1.read_bytes()
        S.materialize_drafts(self.store, self.run, out_path=p2)
        self.assertEqual(first, p2.read_bytes())
        doc = json.loads(first)
        self.assertEqual(doc["experiments"][0]["idea_id"], iid)
        self.assertEqual(doc["experiments"][0]["state"],
                         "DRAFT-INTAKE-NOT-MERGED")
        self.assertEqual(doc["experiments"][0]["queue_run_id"], self.run)

    def test_ledger_materialization_deterministic(self):
        reg = {
            "experiments": [
                {"experiment_id": "EXP-X", "state": "CLOSED-FAIL",
                 "verdict": "FAIL", "created_at": "2026-10-12",
                 "failure_strategy_family": "ml_price_forecasting"},
            ]
        }
        reg_path = Path(self.tmp) / "registry.json"
        reg_path.write_text(json.dumps(reg), encoding="utf-8")
        res = self.store.ingest(candidate(), self.run)
        self.store.transition(res["idea_id"], "RANKED", self.run, rank=1)
        self.store.transition(res["idea_id"], "SHORTLISTED", self.run)
        l1 = Path(self.tmp) / "l1.json"
        l2 = Path(self.tmp) / "l2.json"
        S.materialize_ledger(self.store, reg_path, out_path=l1)
        b1 = l1.read_bytes()
        S.materialize_ledger(self.store, reg_path, out_path=l2)
        self.assertEqual(b1, l2.read_bytes())
        doc = json.loads(b1)
        fams = {r["strategy_family"]: r for r in doc["families"]}
        self.assertEqual(fams["volume_premium"]["shortlisted_count"], 1)
        self.assertEqual(fams["ml_price_forecasting"]["family_state"],
                         "closed")
        closed = S.closed_families_from_ledger(doc)
        self.assertIn("ml_price_forecasting", closed)
        # the pinned registry input is untouched
        self.assertEqual(json.loads(reg_path.read_text()), reg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
