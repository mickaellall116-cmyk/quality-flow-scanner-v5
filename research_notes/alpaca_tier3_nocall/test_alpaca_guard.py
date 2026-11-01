import copy
import json
import math
import unittest
import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

from alpaca_guard import GuardStop, preflight, validate_payload, validate_receipt


ROOT = Path(__file__).resolve().parent
MANIFEST = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
SESSIONS = [
    "2024-04-04", "2024-04-05", "2024-04-08", "2024-04-09",
    "2024-04-10", "2024-04-11", "2024-04-12", "2024-04-15",
    "2024-04-16", "2024-04-17", "2024-04-18", "2024-04-19",
    "2024-04-22", "2024-04-23",
]


def payload(sessions=SESSIONS):
    bars = []
    for day in sessions:
        for minutes in range(9 * 60 + 30, 16 * 60, 30):
            hour, minute = divmod(minutes, 60)
            local_stamp = dt.datetime.combine(
                dt.date.fromisoformat(day),
                dt.time(hour, minute),
                tzinfo=ZoneInfo("America/New_York"),
            )
            utc_stamp = local_stamp.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
            bars.append({
                "t": utc_stamp,
                "o": 1.0, "h": 2.0, "l": 0.5, "c": 1.5, "v": 100,
            })
    return {
        "symbol": "IREN", "next_page_token": None, "bars": bars,
    }


class GateTests(unittest.TestCase):
    def test_hold_precedes_credentials_and_network(self):
        touched = {"network": 0}
        class ExplodingEnv(dict):
            def get(self, key, default=None):
                raise AssertionError("credential lookup happened before rights gate")
        with self.assertRaisesRegex(GuardStop, "RIGHTS_GATE_NOT_GO"):
            preflight(MANIFEST, ExplodingEnv(), lambda: touched.__setitem__("network", 1))
        self.assertEqual(touched["network"], 0)

    def test_missing_secret_precedes_network_after_synthetic_go(self):
        manifest = copy.deepcopy(MANIFEST)
        manifest["route"]["rights_gate"] = "GO"
        manifest["route"]["adjudication_record_sha256"] = "a" * 64
        manifest["network_enabled"] = True
        touched = {"network": 0}
        with self.assertRaisesRegex(GuardStop, "CREDENTIAL_MISSING"):
            preflight(manifest, {"APCA_API_KEY_ID": "fixture"}, lambda: touched.__setitem__("network", 1))
        self.assertEqual(touched["network"], 0)

    def test_network_disabled_precedes_credentials(self):
        manifest = copy.deepcopy(MANIFEST)
        manifest["route"]["rights_gate"] = "GO"
        manifest["route"]["adjudication_record_sha256"] = "a" * 64
        with self.assertRaisesRegex(GuardStop, "NETWORK_NOT_EXPLICITLY_ENABLED"):
            preflight(manifest, {}, lambda: self.fail("network called"))


class PayloadTests(unittest.TestCase):
    def test_valid_grid_counts_only(self):
        receipt = validate_payload(payload(), symbol="IREN", expected_sessions=SESSIONS)
        self.assertEqual(receipt["raw_row_count"], 182)
        self.assertEqual(receipt["derived_row_count"], 98)
        self.assertEqual(receipt["session_count"], 14)
        validate_receipt(receipt, MANIFEST)

    def test_dst_boundary_accepts_utc_bars(self):
        # Friday before and Monday after the 2023 fall-back transition.
        sessions = ["2023-11-03", "2023-11-06"]
        value = payload(sessions)
        receipt = validate_payload(value, symbol="IREN", expected_sessions=sessions)
        self.assertEqual(receipt["raw_row_count"], 26)
        self.assertTrue(value["bars"][0]["t"].endswith("13:30:00Z"))
        self.assertTrue(value["bars"][13]["t"].endswith("14:30:00Z"))

    def test_equivalent_offset_is_not_duplicate_or_off_grid(self):
        value = payload()
        value["bars"][0]["t"] = "2024-04-04T09:30:00-04:00"
        receipt = validate_payload(value, symbol="IREN", expected_sessions=SESSIONS)
        self.assertEqual(receipt["raw_row_count"], 182)

    def test_non_mapping_is_non_json_error(self):
        with self.assertRaisesRegex(GuardStop, "HTTP_OR_NON_JSON_ERROR"):
            validate_payload([], symbol="IREN", expected_sessions=SESSIONS)

    def test_unexpected_page_token(self):
        value = payload(); value["next_page_token"] = "unexpected"
        with self.assertRaisesRegex(GuardStop, "UNEXPECTED_PAGE_TOKEN"):
            validate_payload(value, symbol="IREN", expected_sessions=SESSIONS)

    def test_wrong_feed(self):
        with self.assertRaisesRegex(GuardStop, "FEED_OR_TIMEFRAME_MISMATCH"):
            validate_payload(
                payload(), symbol="IREN", expected_sessions=SESSIONS,
                request_feed="iex",
            )

    def test_wrong_timeframe(self):
        with self.assertRaisesRegex(GuardStop, "FEED_OR_TIMEFRAME_MISMATCH"):
            validate_payload(
                payload(), symbol="IREN", expected_sessions=SESSIONS,
                request_timeframe="1Hour",
            )

    def test_duplicate(self):
        value = payload(); value["bars"].append(copy.deepcopy(value["bars"][0]))
        with self.assertRaisesRegex(GuardStop, "DUPLICATE_BAR"):
            validate_payload(value, symbol="IREN", expected_sessions=SESSIONS)

    def test_off_grid(self):
        value = payload(); value["bars"][0]["t"] = "2024-04-04T13:45:00Z"
        with self.assertRaisesRegex(GuardStop, "OFF_GRID_BAR"):
            validate_payload(value, symbol="IREN", expected_sessions=SESSIONS)

    def test_missing_bucket(self):
        value = payload(); value["bars"].pop()
        with self.assertRaisesRegex(GuardStop, "MISSING_BUCKET"):
            validate_payload(value, symbol="IREN", expected_sessions=SESSIONS)

    def test_nonfinite(self):
        value = payload(); value["bars"][0]["o"] = math.inf
        with self.assertRaisesRegex(GuardStop, "NONFINITE_VALUE"):
            validate_payload(value, symbol="IREN", expected_sessions=SESSIONS)

    def test_receipt_rejects_raw_or_secret_fields(self):
        for key in ("open", "bars", "api_secret", "raw_body", "unexpected"):
            with self.subTest(key=key), self.assertRaises(GuardStop):
                validate_receipt({"symbol": "IREN", key: "fixture"}, MANIFEST)


if __name__ == "__main__":
    unittest.main()
