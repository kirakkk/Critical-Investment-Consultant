import json
import unittest
from pathlib import Path

from cic.radar_report import analyze_radar_input


class RadarReportTest(unittest.TestCase):
    def setUp(self):
        self.sample = json.loads(Path("data/sample_radar_signals.json").read_text(encoding="utf-8"))

    def test_report_contains_radar_sections_without_llm(self):
        report = analyze_radar_input(self.sample, use_llm=False)
        radar = report["radar_report"]
        self.assertEqual(radar["stock_code"], "001309.SZ")
        self.assertGreater(len(radar["claims"]), 0)
        self.assertGreater(len(radar["cross_validation"]), 0)
        self.assertGreater(len(radar["validation_tasks"]), 0)
        self.assertGreater(len(radar["bear_cases"]), 0)
        self.assertIn("suggested_user_action", radar)

    def test_report_has_no_unconditional_trade_instruction(self):
        report = analyze_radar_input(self.sample, use_llm=False)
        text = json.dumps(report, ensure_ascii=False)
        for forbidden in ("无条件买入", "无条件卖出", "满仓", "梭哈"):
            self.assertNotIn(forbidden, text)

    def test_each_claim_has_validation_task(self):
        report = analyze_radar_input(self.sample, use_llm=False)
        radar = report["radar_report"]
        claim_ids = {item["claim_id"] for item in radar["claims"]}
        task_claim_ids = {item["claim_id"] for item in radar["validation_tasks"]}
        self.assertTrue(claim_ids.issubset(task_claim_ids))


if __name__ == "__main__":
    unittest.main()
