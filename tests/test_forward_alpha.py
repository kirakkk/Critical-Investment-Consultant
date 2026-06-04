import copy
import json
import unittest
from pathlib import Path

from cic.forward_alpha import run_forward_alpha_lab


class ForwardAlphaTest(unittest.TestCase):
    def setUp(self):
        self.sample = json.loads(Path("data/sample_radar_signals.json").read_text(encoding="utf-8"))

    def test_demingli_generates_forward_source_and_scenario_pack(self):
        result = run_forward_alpha_lab(self.sample, use_llm=False)
        forward = result["forward_alpha"]
        source_names = {item["source_name"] for item in forward["source_candidates"]}
        themes = set(forward["themes"])
        self.assertIn("NAND/DRAM 价格周期", themes)
        self.assertIn("TrendForce 存储价格与供需报告", source_names)
        self.assertIn("华强北存储渠道价格", source_names)
        self.assertGreater(len(forward["manual_import_tasks"]), 0)
        self.assertGreater(len(forward["hypotheses"]), 0)
        self.assertGreater(len(forward["scenarios"]), 0)

    def test_restricted_or_unknown_sources_are_not_auto_collected(self):
        result = run_forward_alpha_lab(self.sample, use_llm=False)
        forward = result["forward_alpha"]
        restricted = [
            item
            for item in forward["source_candidates"]
            if item["license_status"] in {"restricted", "unknown"} or not item["automation_allowed"]
        ]
        self.assertGreater(len(restricted), 0)
        self.assertTrue(all(item["collection_status"] != "auto_collectable" for item in restricted))

    def test_cashflow_counter_signal_generates_deep_dive_task(self):
        result = run_forward_alpha_lab(self.sample, use_llm=False)
        forward = result["forward_alpha"]
        comparisons = {item["metric"]: item for item in forward["comparisons"]}
        self.assertEqual(comparisons["operating_cashflow_quality"]["result_state"], "risk_blocker")
        self.assertGreater(len(result["deep_dives"]["tasks"]), 0)
        self.assertIn("现金流", result["deep_dives"]["tasks"][0]["question"])

    def test_kol_only_does_not_raise_forward_strength(self):
        sample = {
            "stock_code": "000001.SZ",
            "stock_name": "示例公司",
            "theme": "机器人",
            "weak_signals": [
                {
                    "signal_text": "KOL称公司机器人订单可能爆发。",
                    "source_family": "expert_kol",
                    "source_rank": "C",
                    "source_name": "@robot_watch",
                    "raw_excerpt": "机器人订单可能爆发。",
                    "independence_group": "kol_robot",
                }
            ],
            "evidence": [],
        }
        result = run_forward_alpha_lab(sample, use_llm=False)
        forward = result["forward_alpha"]
        self.assertEqual(forward["observations"], [])
        self.assertTrue(all(item["forward_score_delta"] == 0 for item in forward["comparisons"]))

    def test_two_independent_non_kol_sources_raise_forward_strength(self):
        sample = copy.deepcopy(self.sample)
        sample["evidence"] = [
            {
                "claim": "公司公告披露获得客户批量订单。",
                "source_family": "official_disclosure",
                "source_rank": "A",
                "source_name": "公告",
                "raw_excerpt": "获得客户批量订单。",
                "source_url": "https://example.com/a",
                "independence_group": "official_order",
            },
            {
                "claim": "客户采购平台显示公司相关产品中标。",
                "source_family": "public_footprint",
                "source_rank": "C",
                "source_name": "采购平台",
                "raw_excerpt": "相关产品中标。",
                "source_url": "https://example.com/b",
                "independence_group": "tender_order",
            },
        ]
        result = run_forward_alpha_lab(sample, use_llm=False)
        comparisons = {item["metric"]: item for item in result["forward_alpha"]["comparisons"]}
        self.assertEqual(comparisons["customer_order_validation"]["result_state"], "cross_source_converging")
        self.assertGreater(comparisons["customer_order_validation"]["forward_score_delta"], 0)

    def test_duplicate_same_group_does_not_add_forward_strength(self):
        sample = copy.deepcopy(self.sample)
        duplicate = copy.deepcopy(sample["evidence"][1])
        duplicate["source_name"] = "转载公告"
        duplicate["source_url"] = "https://example.com/duplicate"
        sample["evidence"] = [sample["evidence"][1], duplicate]
        result = run_forward_alpha_lab(sample, use_llm=False)
        comparisons = {item["metric"]: item for item in result["forward_alpha"]["comparisons"]}
        self.assertEqual(comparisons["business_exposure"]["result_state"], "single_source_watch")
        self.assertEqual(comparisons["business_exposure"]["forward_score_delta"], 0)


if __name__ == "__main__":
    unittest.main()
