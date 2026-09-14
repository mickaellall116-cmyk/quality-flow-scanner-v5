from pathlib import Path

root = Path(__file__).resolve().parents[1]

api_test = root / "tests" / "test_api_contract.py"
text = api_test.read_text()
text = text.replace('self.assertEqual(SCANNER_VERSION, "5.2")', 'self.assertEqual(SCANNER_VERSION, "5.3")')
text = text.replace('self.assertEqual(RULE_VERSION, "2026-09-10-v2")', 'self.assertEqual(RULE_VERSION, "2026-09-14-v3")')
api_test.write_text(text)

rules_test = root / "tests" / "test_scanner_rules.py"
text = rules_test.read_text()
text = text.replace('self.assertEqual(RULE_VERSION, "2026-09-10-v2")', 'self.assertEqual(RULE_VERSION, "2026-09-14-v3")')
rules_test.write_text(text)

print("Updated version assertions for MasterScanner V5.3")
