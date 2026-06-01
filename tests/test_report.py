import json
import unittest
from pathlib import Path

from cic.report import analyze_holdings


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.sample = json.loads(Path("data/sample_holdings.json").read_text(encoding="utf-8"))

    def test_report_contains_five_research_outputs(self):
        report = analyze_holdings(self.sample, use_llm=False)
        brief = report["brief"]
        self.assertIn("top_changes", brief)
        self.assertIn("thesis_checks", brief)
        self.assertIn("peer_comparisons", brief)
        self.assertIn("risk_alerts", brief)
        self.assertIn("validation_points", brief)
        self.assertGreater(len(brief["thesis_checks"]), 0)
        self.assertGreater(len(brief["validation_points"]), 0)

    def test_candidate_has_risk_radar_and_validation(self):
        report = analyze_holdings(self.sample, use_llm=False)
        risk_codes = {item["stock_code"] for item in report["brief"]["risk_alerts"]}
        validation_codes = {item["stock_code"] for item in report["brief"]["validation_points"]}
        self.assertIn("002594.SZ", risk_codes)
        self.assertIn("002594.SZ", validation_codes)

    def test_peer_comparison_mentions_missing_peer_set_for_single_theme(self):
        single = [self.sample[2]]
        report = analyze_holdings(single, use_llm=False)
        comparisons = report["brief"]["peer_comparisons"]
        self.assertEqual(comparisons[0]["missing_data"], ["peer_set"])


if __name__ == "__main__":
    unittest.main()
