"""Tests for the frozen X2 forward-test universe (added 2026-09-15).

Guards: cohort 2 is exactly the frozen list, disjoint from UX51, and every
forward symbol carries its cohort theme.
"""

import unittest

import hybrid_exit_test
import v54_forward_harness as H
import v54_universe_x2 as ux2


class TestUniverseX2(unittest.TestCase):
    def test_x2_frozen_size(self):
        self.assertEqual(len(ux2.UNIVERSE_X2), ux2.EXPECTED_X2_SIZE)
        self.assertEqual(len(ux2.UNIVERSE_X2), 199)

    def test_x2_no_duplicates(self):
        self.assertEqual(len(set(ux2.UNIVERSE_X2)), len(ux2.UNIVERSE_X2))

    def test_x2_all_valid_symbols(self):
        for s in ux2.UNIVERSE_X2:
            self.assertIsInstance(s, str)
            self.assertTrue(s.strip(), "empty symbol in X2")

    def test_x2_disjoint_from_ux51(self):
        overlap = set(ux2.UNIVERSE_X2) & set(hybrid_exit_test.UNIVERSE_X)
        self.assertEqual(overlap, set(), f"X2 overlaps UX51: {overlap}")

    def test_ux51_unchanged(self):
        self.assertEqual(len(hybrid_exit_test.UNIVERSE_X), 51)
        self.assertEqual(len(H.UX51_UNIVERSE), 51)

    def test_forward_universe_combined(self):
        self.assertEqual(len(H.FORWARD_UNIVERSE), 51 + 199)
        self.assertEqual(len(set(H.FORWARD_UNIVERSE)), len(H.FORWARD_UNIVERSE))

    def test_theme_map_cohort_tags(self):
        for s in H.UX51_UNIVERSE:
            self.assertEqual(H.THEME_MAP[s], "Forward-UX51")
        for s in ux2.UNIVERSE_X2:
            self.assertEqual(H.THEME_MAP[s], "Forward-X2")
        self.assertEqual(len(H.THEME_MAP), len(H.FORWARD_UNIVERSE))

    def test_cohort_sizes(self):
        self.assertEqual(H.COHORT_SIZES, {"UX51": 51, "X2": 199})

    def test_key_names_present(self):
        # Names Mike explicitly asked for.
        for s in ["QQQ", "TSM", "GME", "MARA", "SLV", "LLY", "FTNT",
                  "NBIS", "CRWV", "BNB-USD", "ONDO-USD", "BRK-B"]:
            self.assertIn(s, ux2.UNIVERSE_X2, f"{s} missing from X2")


if __name__ == "__main__":
    unittest.main()
