import unittest

from scanner_rules import RULE_VERSION, SCANNER_VERSION, risk_reward, trade_levels


class ApiContractTests(unittest.TestCase):
    def test_version_contract(self):
        self.assertEqual(SCANNER_VERSION, "5.2")
        self.assertEqual(RULE_VERSION, "2026-09-10-v2")

    def test_stop_and_target_are_zone_anchored_not_fixed_1_33_ratio(self):
        stop, target = trade_levels(99.0, 101.0, 2.0)
        row = {"price": 100.0, "stop": stop, "tp1": target}
        self.assertEqual(stop, 97.7)
        self.assertEqual(target, 106.0)
        self.assertNotAlmostEqual(risk_reward(row), 4 / 3, places=2)


if __name__ == "__main__":
    unittest.main()
