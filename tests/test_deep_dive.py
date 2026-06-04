import copy
import json
import unittest
from pathlib import Path

from cic.deep_dive import run_deep_dive_task
from cic.radar_report import analyze_radar_input


class DeepDiveTest(unittest.TestCase):
    def setUp(self):
        self.sample = json.loads(Path("data/sample_radar_signals.json").read_text(encoding="utf-8"))

    def analyze(self, sample=None):
        return analyze_radar_input(sample or self.sample, use_llm=False, auto_run_deep_dives=False)

    def task_by_type(self, report, trigger_type):
        for task in report["deep_dives"]["tasks"]:
            if task["trigger_type"] == trigger_type:
                return task
        self.fail(f"missing task {trigger_type}")

    def verdict_for(self, bundle, task_id):
        for verdict in bundle["verdicts"]:
            if verdict["task_id"] == task_id:
                return verdict
        self.fail(f"missing verdict for {task_id}")

    def test_demingli_generates_three_deep_dive_tasks(self):
        report = self.analyze()
        task_types = {item["trigger_type"] for item in report["deep_dives"]["tasks"]}
        self.assertEqual(len(report["deep_dives"]["tasks"]), 3)
        self.assertEqual(
            task_types,
            {"cashflow_quality", "customer_order_capacity_validation", "capacity_margin_stress"},
        )

    def test_cashflow_counter_generates_maintained_blocker(self):
        report = self.analyze()
        task = self.task_by_type(report, "cashflow_quality")
        bundle = run_deep_dive_task(task, report)
        verdict = self.verdict_for(bundle, task["task_id"])
        self.assertEqual(verdict["verdict"], "blocker_maintained")
        self.assertTrue(verdict["review_required"])

    def test_kol_only_support_cannot_remove_blocker(self):
        sample = {
            "stock_code": "001309.SZ",
            "stock_name": "德明利",
            "theme": "国产存储",
            "weak_signals": [
                {
                    "signal_text": "KOL称德明利可能拿到大客户订单并提升产能消化。",
                    "source_family": "expert_kol",
                    "source_rank": "C",
                    "source_name": "@kol_only",
                    "independence_group": "kol_only_group",
                }
            ],
            "evidence": [],
            "risks": [],
        }
        report = self.analyze(sample)
        task = self.task_by_type(report, "customer_order_capacity_validation")
        bundle = run_deep_dive_task(task, report)
        verdict = self.verdict_for(bundle, task["task_id"])
        self.assertEqual(verdict["verdict"], "insufficient_evidence")
        self.assertNotEqual(verdict["verdict"], "blocker_removed")

    def test_ab_counter_explained_only_softens(self):
        sample = copy.deepcopy(self.sample)
        sample["evidence"].append(
            {
                "claim": "公司公告解释经营现金流改善，回款改善，应收下降，结算周期缩短。",
                "source_family": "official_disclosure",
                "source_rank": "A",
                "source_name": "现金流改善公告",
                "source_url": "manual://official/cashflow-improvement",
                "raw_excerpt": "经营现金流改善，回款改善，应收下降。",
                "independence_group": "dml_cashflow_resolution",
            }
        )
        report = self.analyze(sample)
        task = self.task_by_type(report, "cashflow_quality")
        bundle = run_deep_dive_task(task, report)
        verdict = self.verdict_for(bundle, task["task_id"])
        self.assertEqual(verdict["verdict"], "blocker_softened")
        self.assertNotEqual(verdict["verdict"], "blocker_removed")

    def test_missing_evidence_returns_insufficient(self):
        task = {
            "task_id": "ddt_missing",
            "claim_id": "missing",
            "trigger_type": "customer_order_capacity_validation",
            "budget": {"max_sources": 5, "max_llm_calls": 2, "timeout_seconds": 120, "max_token_estimate": 3200},
        }
        bundle = run_deep_dive_task(task, {"radar_report": {"claims": [], "evidence": []}})
        verdict = self.verdict_for(bundle, task["task_id"])
        self.assertEqual(verdict["verdict"], "insufficient_evidence")

    def test_duplicate_sources_do_not_increase_sources_checked(self):
        sample = copy.deepcopy(self.sample)
        duplicate = copy.deepcopy(sample["evidence"][1])
        duplicate["raw_excerpt"] = sample["evidence"][1]["raw_excerpt"]
        sample["evidence"].append(duplicate)
        report = self.analyze(sample)
        task = self.task_by_type(report, "cashflow_quality")
        bundle = run_deep_dive_task(task, report)
        self.assertLess(len(bundle["runs"][0]["sources_checked"]), len(report["radar_report"]["evidence"]))

    def test_source_budget_stop_is_recorded(self):
        report = self.analyze()
        task = self.task_by_type(report, "cashflow_quality")
        task["budget"] = {"max_sources": 1, "max_llm_calls": 2, "timeout_seconds": 120, "max_token_estimate": 3200}
        bundle = run_deep_dive_task(task, report)
        self.assertEqual(bundle["runs"][0]["status"], "stopped")
        self.assertEqual(bundle["runs"][0]["stop_reason"], "source_budget_reached")


if __name__ == "__main__":
    unittest.main()
