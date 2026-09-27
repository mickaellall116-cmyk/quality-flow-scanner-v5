"""Synthetic adversarial controls for F7 decision-clock version selection.

All fixtures are invented. No vendor data, no returns, no scoring.
Covers the ChatGPT REVIEW DECISION (2026-09-26) checklist:
equality boundary, future delivery, late revisions, permanent-ID/ticker
reuse, delisted names, vendor-sequence conflicts, exact coverage/missingness
boundaries, <=T corporate-action invariance.
"""

import math
import unittest
from datetime import datetime, timedelta, timezone

from fundamental_version_selection import (
    completeness,
    group_by_fact,
    parse_instant,
    select_version,
    split_adjust,
)

DECISION = datetime(2025, 4, 1, 16, 0, tzinfo=timezone.utc)  # 12:00 ET
BUF = timedelta(minutes=1)


def ver(available_at, value=1.25, **kw):
    v = {"security_id": "PERM-1", "fiscal_period": "2025Q1", "metric": "consensus_eps",
         "available_at": available_at, "value": value,
         "vendor_record_id": kw.pop("rid", "r1")}
    v.update(kw)
    return v


class EqualityBoundaryTests(unittest.TestCase):
    def test_available_plus_buffer_equal_to_decision_is_not_eligible(self):
        # available_at + 1min buffer == decision_at exactly -> STRICT inequality fails
        v = ver("2025-04-01T15:59:00Z")
        self.assertEqual(select_version([v], DECISION, BUF)["status"], "NO_ELIGIBLE_VERSION")

    def test_one_second_inside_boundary_is_eligible(self):
        v = ver("2025-04-01T15:58:59Z")  # +60s = 15:59:59Z < 16:00:00Z
        self.assertEqual(select_version([v], DECISION, BUF)["status"], "SELECTED")

    def test_available_equal_to_decision_with_zero_buffer_is_not_eligible(self):
        v = ver("2025-04-01T16:00:00Z")
        self.assertEqual(select_version([v], DECISION, timedelta(0))["status"],
                         "NO_ELIGIBLE_VERSION")


class FutureDeliveryTests(unittest.TestCase):
    def test_version_delivered_after_decision_is_never_selected(self):
        early = ver("2025-04-01T10:00:00Z", value=1.00)
        future = ver("2025-04-01T18:00:00Z", value=9.99, rid="r2")  # lookahead bait
        out = select_version([early, future], DECISION, BUF)
        self.assertEqual(out["status"], "SELECTED")
        self.assertEqual(out["version"]["value"], 1.00)

    def test_only_future_versions_means_no_eligible_version(self):
        out = select_version([ver("2025-04-01T18:00:00Z")], DECISION, BUF)
        self.assertEqual(out["status"], "NO_ELIGIBLE_VERSION")


class LateRevisionTests(unittest.TestCase):
    def test_revision_after_decision_does_not_leak_backwards(self):
        v1 = ver("2025-04-01T09:00:00Z", value=1.00)
        v2 = ver("2025-04-01T15:00:00Z", value=2.00, rid="r2")  # revision
        early_decision = datetime(2025, 4, 1, 14, 0, tzinfo=timezone.utc)
        late_decision = datetime(2025, 4, 1, 18, 0, tzinfo=timezone.utc)
        self.assertEqual(select_version([v1, v2], early_decision, BUF)["version"]["value"], 1.00)
        self.assertEqual(select_version([v1, v2], late_decision, BUF)["version"]["value"], 2.00)

    def test_latest_eligible_wins_not_latest_overall(self):
        versions = [ver("2025-04-01T09:00:00Z", value=1.00),
                    ver("2025-04-01T11:00:00Z", value=1.50, rid="r2"),
                    ver("2025-04-01T10:00:00Z", value=1.25, rid="r3")]
        out = select_version(versions, DECISION, BUF)
        self.assertEqual(out["version"]["value"], 1.50)


class TickerReuseTests(unittest.TestCase):
    def test_same_ticker_different_security_ids_stay_separate(self):
        a = ver("2025-04-01T09:00:00Z", value=1.00, ticker="AAA")
        b = ver("2025-04-01T09:00:00Z", value=7.77, rid="r9", ticker="AAA",
                security_id="PERM-2")  # ticker reused by a different company
        groups = group_by_fact([a, b])
        self.assertEqual(len(groups), 2)
        out_a = select_version(groups[("PERM-1", "2025Q1", "consensus_eps")], DECISION, BUF)
        out_b = select_version(groups[("PERM-2", "2025Q1", "consensus_eps")], DECISION, BUF)
        self.assertEqual(out_a["version"]["value"], 1.00)
        self.assertEqual(out_b["version"]["value"], 7.77)

    def test_missing_grouping_key_fails_closed(self):
        with self.assertRaises(ValueError):
            group_by_fact([{"available_at": "2025-04-01T09:00:00Z", "value": 1.0}])


class DelistedNameTests(unittest.TestCase):
    def test_delisted_security_versions_still_selectable(self):
        v = ver("2025-04-01T09:00:00Z", value=0.80, security_id="DELISTED-9")
        out = select_version([v], DECISION, BUF)
        self.assertEqual(out["status"], "SELECTED")
        self.assertEqual(out["version"]["value"], 0.80)


class VendorSequenceConflictTests(unittest.TestCase):
    def test_same_instant_conflicting_values_fail_closed(self):
        a = ver("2025-04-01T09:00:00Z", value=1.00)
        b = ver("2025-04-01T09:00:00Z", value=1.50, rid="r2")  # same instant, differs
        out = select_version([a, b], DECISION, BUF)
        self.assertEqual(out["status"], "SAME_TIME_CONFLICT")
        self.assertIsNone(out["version"])

    def test_same_instant_identical_values_select_fine(self):
        a = ver("2025-04-01T09:00:00Z", value=1.00)
        b = ver("2025-04-01T09:00:00Z", value=1.00, rid="r2")
        self.assertEqual(select_version([a, b], DECISION, BUF)["status"], "SELECTED")

    def test_timezone_equivalent_instants_still_conflict(self):
        a = ver("2025-04-01T09:00:00Z", value=1.00)
        b = ver("2025-04-01T05:00:00-04:00", value=1.50, rid="r2")  # same instant as a
        self.assertEqual(select_version([a, b], DECISION, BUF)["status"], "SAME_TIME_CONFLICT")


class CoverageMissingnessBoundaryTests(unittest.TestCase):
    REQ = ["eps_rev", "fwd_growth", "rev_growth", "surprise", "margin_chg", "pv_pressure"]

    def full(self, **kw):
        c = {k: 0.5 for k in self.REQ}
        c.update(kw)
        return c

    def test_all_present_is_computable(self):
        self.assertEqual(completeness(self.full()), "COMPUTABLE")

    def test_one_missing_component_is_unknown_not_renormalized(self):
        self.assertEqual(completeness(self.full(surprise=None)), "UNKNOWN")

    def test_zero_is_a_real_value_not_missing(self):
        # exact boundary: stored 0.0 counts as present
        self.assertEqual(completeness(self.full(margin_chg=0.0)), "COMPUTABLE")

    def test_nan_and_unknown_string_are_unknown(self):
        self.assertEqual(completeness(self.full(rev_growth=math.nan)), "UNKNOWN")
        self.assertEqual(completeness(self.full(fwd_growth="UNKNOWN")), "UNKNOWN")

    def test_empty_components_is_unknown(self):
        self.assertEqual(completeness({}), "UNKNOWN")


class CorporateActionInvarianceTests(unittest.TestCase):
    T = "2025-04-01T12:00:00Z"  # split effective instant

    def test_versions_at_or_before_T_are_never_rewritten(self):
        before = ver("2025-04-01T09:00:00Z", value=100.0)
        at = ver("2025-04-01T12:00:00Z", value=100.0, rid="r2")  # equality boundary
        after = ver("2025-04-01T15:00:00Z", value=100.0, rid="r3")
        out = split_adjust([before, at, after], self.T, 0.5)
        self.assertEqual(out[0]["value"], 100.0)
        self.assertEqual(out[1]["value"], 100.0)  # == T is NOT adjusted
        self.assertNotIn("corporate_action_applied", out[0])
        self.assertNotIn("corporate_action_applied", out[1])
        self.assertEqual(out[2]["value"], 50.0)
        self.assertEqual(out[2]["corporate_action_applied"], self.T)

    def test_unparseable_effective_at_fails_closed(self):
        with self.assertRaises(ValueError):
            split_adjust([ver("2025-04-01T09:00:00Z")], "not-a-time", 0.5)


class ParseInstantTests(unittest.TestCase):
    def test_rejects_dates_naive_and_offsetless(self):
        for bad in ("2025-04-01", "2025-04-01T09:00:00", "2025-04-01T09:00Z", "", None, 123):
            self.assertIsNone(parse_instant(bad))

    def test_accepts_z_and_offsets(self):
        self.assertIsNotNone(parse_instant("2025-04-01T09:00:00Z"))
        self.assertIsNotNone(parse_instant("2025-04-01T05:00:00-04:00"))


if __name__ == "__main__":
    unittest.main()
