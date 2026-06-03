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
        self.assertEqual(report["radar_report"]["stock_code"], "001309.SZ")
        latest = self.get_json("/api/radar/latest")
        self.assertEqual(latest["radar_report"]["report_id"], report["radar_report"]["report_id"])

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
