"""Independent boundary values for pre-performance intake checks."""

import unittest

from fundamental_data_intake_audit import audit_rows, parse_delivery_timestamp


def record(**changes):
    row = {
        "security_id": "PERMANENT-123", "fiscal_period": "2025Q1",
        "metric": "consensus_eps", "value": 1.25,
        "available_at": "2025-04-01T13:29:00-04:00",
        "availability_provenance": "vendor_recorded",
        "vendor_record_id": "record-1", "source_version": "original",
    }
    row.update(changes)
    return row


class IntakeBoundaryTests(unittest.TestCase):
    def test_dates_and_naive_clocks_are_not_delivery_timestamps(self):
        for bad in ("2025-04-01", "2025-04-01T13:29:00", "2025-04-01T13:29Z", "unknown"):
            self.assertIsNone(parse_delivery_timestamp(bad))

    def test_inferred_delivery_and_missing_original_version_rejected(self):
        result = audit_rows([record(availability_provenance="inferred", source_version="")])
        self.assertEqual(result["status"], "STRUCTURAL_ISSUES")
        self.assertIn("not_vendor_delivery_evidence", result["issues"][0]["errors"])
        self.assertIn("missing:source_version", result["issues"][0]["errors"])

    def test_same_instant_with_disagreeing_values_is_conflict_across_timezones(self):
        a = record()
        b = record(vendor_record_id="record-2", value=1.35,
                   available_at="2025-04-01T17:29:00Z")
        result = audit_rows([a, b])
        self.assertEqual(result["counts"]["ambiguous_conflict_groups"], 1)

    def test_identical_duplicate_is_distinct_from_conflict(self):
        result = audit_rows([record(), record(vendor_record_id="record-2")])
        self.assertEqual(result["status"], "SHAPE_ONLY_OK")
        self.assertEqual(result["counts"]["identical_duplicate_groups"], 1)


if __name__ == "__main__":
    unittest.main()
