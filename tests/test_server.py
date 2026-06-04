import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from cic.server import create_server


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.server = create_server("127.0.0.1", 0, Path(self.tmpdir.name) / "store.json")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmpdir.cleanup()

    def get_json(self, path):
        with urllib.request.urlopen(f"{self.base_url}{path}", timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def post_json(self, path, payload):
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def test_health(self):
        data = self.get_json("/api/health")
        self.assertTrue(data["ok"])

    def test_analyze_endpoint(self):
        sample = self.get_json("/api/sample-holdings")
        report = self.post_json("/api/holdings/analyze", {"holdings": sample, "use_llm": False})
        self.assertIn("brief", report)
        latest = self.get_json("/api/reports/latest")
        self.assertEqual(latest["brief"]["brief_date"], report["brief"]["brief_date"])

    def test_radar_analyze_endpoint(self):
        sample = self.get_json("/api/sample-radar-signals")
        report = self.post_json("/api/radar/analyze", {"radar": sample, "use_llm": False})
        self.assertIn("radar_report", report)
        self.assertIn("forward_alpha", report)
        self.assertEqual(report["radar_report"]["stock_code"], "001309.SZ")
        self.assertGreater(len(report["deep_dives"]["tasks"]), 0)
        self.assertGreater(len(report["forward_alpha"]["source_candidates"]), 0)
        latest = self.get_json("/api/radar/latest")
        self.assertEqual(latest["radar_report"]["report_id"], report["radar_report"]["report_id"])

    def test_forward_alpha_endpoints(self):
        sample = self.get_json("/api/sample-radar-signals")
        result = self.post_json("/api/radar/forward-alpha/run", {"radar": sample, "use_llm": False})
        self.assertIn("forward_alpha", result)
        run_id = result["forward_alpha"]["run_id"]
        latest = self.get_json("/api/radar/forward-alpha/latest")
        self.assertEqual(latest["forward_alpha"]["run_id"], run_id)
        by_id = self.get_json(f"/api/radar/forward-alpha/runs/{run_id}")
        self.assertEqual(by_id["forward_alpha"]["run_id"], run_id)
        sources = self.get_json("/api/radar/forward-alpha/sources")
        self.assertGreater(len(sources["sources"]), 0)
        source_id = sources["sources"][0]["source_id"]
        decision = self.post_json(
            f"/api/radar/forward-alpha/source-decisions/{source_id}",
            {"decision": "approve_manual", "reason": "先手动录入"},
        )
        self.assertTrue(decision["ok"])
        task_id = result["forward_alpha"]["manual_import_tasks"][0]["task_id"]
        imported = self.post_json(
            f"/api/radar/forward-alpha/manual-imports/{task_id}",
            {"raw_excerpt": "渠道价环比上涨。"},
        )
        self.assertTrue(imported["ok"])

    def test_deep_dive_queue_run_and_decision_endpoints(self):
        sample = self.get_json("/api/sample-radar-signals")
        report = self.post_json("/api/radar/analyze", {"radar": sample, "use_llm": False, "auto_run_deep_dives": False})
        task_id = report["deep_dives"]["tasks"][0]["task_id"]
        queue = self.get_json("/api/radar/deep-dives")
        self.assertEqual(queue["deep_dives"]["tasks"][0]["task_id"], task_id)
        run = self.post_json(f"/api/radar/deep-dives/{task_id}/run", {})
        self.assertTrue(run["ok"])
        self.assertGreater(len(run["deep_dives"]["verdicts"]), 0)
        decision = self.post_json(
            f"/api/radar/deep-dives/{task_id}/decision",
            {"decision": "add_to_review", "reason": "反证深挖进入复盘"},
        )
        self.assertTrue(decision["ok"])
        queue = self.get_json("/api/radar/deep-dives")
        self.assertEqual(queue["deep_dives"]["decisions"][0]["task_id"], task_id)

    def test_radar_claim_decision_endpoint(self):
        sample = self.get_json("/api/sample-radar-signals")
        report = self.post_json("/api/radar/analyze", {"radar": sample, "use_llm": False})
        radar = report["radar_report"]
        claim_id = radar["claims"][0]["claim_id"]
        decision = self.post_json(
            f"/api/radar/claims/{claim_id}/decision",
            {
                "decision": "add_to_review",
                "reason": "现金流反证需要复盘",
                "report_id": radar["report_id"],
                "stock_code": radar["stock_code"],
                "stock_name": radar["stock_name"],
            },
        )
        self.assertTrue(decision["ok"])
        decisions = self.get_json("/api/radar/decisions")
        self.assertEqual(decisions["decisions"][0]["claim_id"], claim_id)
        self.assertEqual(decisions["decisions"][0]["decision"], "add_to_review")


if __name__ == "__main__":
    unittest.main()
