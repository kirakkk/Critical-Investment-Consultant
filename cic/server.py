from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .models import Decision, RadarDecision, to_jsonable
from .radar_report import analyze_radar_input, latest_radar_report_summary
from .report import analyze_holdings, latest_report_summary
from .storage import JsonStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = PROJECT_ROOT / "web"
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "local_store.json"


class CICRequestHandler(SimpleHTTPRequestHandler):
    store: JsonStore = JsonStore(DEFAULT_DATA_PATH)

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        if parsed.path == "/":
            return str(WEB_ROOT / "index.html")
        if parsed.path.startswith("/web/"):
            return str(WEB_ROOT / parsed.path.removeprefix("/web/"))
        return str(WEB_ROOT / parsed.path.lstrip("/"))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.write_json({"ok": True, "service": "critical-investment-consultant"})
            return
        if parsed.path == "/api/sample-holdings":
            sample_path = PROJECT_ROOT / "data" / "sample_holdings.json"
            self.write_json(json.loads(sample_path.read_text(encoding="utf-8")))
            return
        if parsed.path == "/api/sample-radar-signals":
            sample_path = PROJECT_ROOT / "data" / "sample_radar_signals.json"
            self.write_json(json.loads(sample_path.read_text(encoding="utf-8")))
            return
        if parsed.path in {"/api/dashboard/today", "/api/reports/latest"}:
            self.write_json(latest_report_summary(self.store.latest_report()))
            return
        if parsed.path == "/api/radar/latest":
            self.write_json(latest_radar_report_summary(self.store.latest_radar_report()))
            return
        if parsed.path == "/api/decisions":
            self.write_json({"decisions": self.store.decisions()})
            return
        if parsed.path == "/api/radar/decisions":
            self.write_json({"decisions": self.store.radar_decisions()})
            return
        if parsed.path.startswith("/api/"):
            self.write_error(HTTPStatus.NOT_FOUND, "unknown api endpoint")
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/holdings/analyze":
            payload = self.read_json()
            holdings = payload.get("holdings")
            if not isinstance(holdings, list):
                self.write_error(HTTPStatus.BAD_REQUEST, "payload.holdings must be a list")
                return
            report = analyze_holdings(holdings, use_llm=bool(payload.get("use_llm", True)))
            self.store.append_report(report)
            self.write_json(report)
            return
        if parsed.path == "/api/radar/analyze":
            payload = self.read_json()
            radar_payload = payload.get("radar") if isinstance(payload.get("radar"), dict) else payload
            try:
                report = analyze_radar_input(radar_payload, use_llm=bool(payload.get("use_llm", True)))
            except ValueError as exc:
                self.write_error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            self.store.append_radar_report(report)
            self.write_json(report)
            return
        if parsed.path.startswith("/api/signals/") and parsed.path.endswith("/decision"):
            parts = parsed.path.strip("/").split("/")
            signal_id = parts[2] if len(parts) >= 3 else ""
            payload = self.read_json()
            decision = Decision(
                signal_id=signal_id,
                decision=str(payload.get("decision") or ""),
                reason=str(payload.get("reason") or ""),
                next_action=str(payload.get("next_action") or ""),
                stop_condition=str(payload.get("stop_condition") or ""),
            )
            if decision.decision not in {"confirm", "ignore", "add_to_review"}:
                self.write_error(HTTPStatus.BAD_REQUEST, "decision must be confirm, ignore, or add_to_review")
                return
            self.store.add_decision(decision)
            self.write_json({"ok": True, "decision": to_jsonable(decision)})
            return
        if parsed.path.startswith("/api/radar/claims/") and parsed.path.endswith("/decision"):
            parts = parsed.path.strip("/").split("/")
            claim_id = parts[3] if len(parts) >= 4 else ""
            payload = self.read_json()
            decision = RadarDecision(
                claim_id=claim_id,
                decision=str(payload.get("decision") or ""),
                reason=str(payload.get("reason") or ""),
                report_id=str(payload.get("report_id") or ""),
                stock_code=str(payload.get("stock_code") or ""),
                stock_name=str(payload.get("stock_name") or ""),
                next_action=str(payload.get("next_action") or ""),
            )
            if decision.decision not in {"confirm", "ignore", "add_to_review"}:
                self.write_error(HTTPStatus.BAD_REQUEST, "decision must be confirm, ignore, or add_to_review")
                return
            if not decision.claim_id:
                self.write_error(HTTPStatus.BAD_REQUEST, "claim_id is required")
                return
            self.store.add_radar_decision(decision)
            self.write_json({"ok": True, "decision": to_jsonable(decision)})
            return
        self.write_error(HTTPStatus.NOT_FOUND, "unknown api endpoint")

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def write_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def write_error(self, status: HTTPStatus, message: str) -> None:
        self.write_json({"ok": False, "error": message}, status)

    def log_message(self, format: str, *args: object) -> None:
        # Keep local dev output calm; tests assert behavior, not access logs.
        if os.getenv("CIC_VERBOSE_HTTP"):
            super().log_message(format, *args)


def create_server(host: str = "127.0.0.1", port: int = 8765, data_path: str | Path | None = None) -> ThreadingHTTPServer:
    handler = CICRequestHandler
    handler.store = JsonStore(data_path or os.getenv("CIC_DATA_PATH") or DEFAULT_DATA_PATH)
    return ThreadingHTTPServer((host, port), handler)


def main() -> None:
    host = os.getenv("CIC_HOST") or "127.0.0.1"
    port = int(os.getenv("CIC_PORT") or "8765")
    try:
        server = create_server(host, port)
    except PermissionError:
        server = create_server(host, 0)
    actual_host, actual_port = server.server_address
    url = f"http://{actual_host}:{actual_port}"
    port_file = os.getenv("CIC_PORT_FILE")
    if port_file:
        Path(port_file).write_text(url, encoding="utf-8")
    print(f"Critical Investment Consultant running at {url}", flush=True)
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
