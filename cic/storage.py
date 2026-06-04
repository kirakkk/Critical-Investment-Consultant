from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Decision, DeepDiveDecision, RadarDecision, to_jsonable, utc_now_iso


class JsonStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return default_store()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return normalize_store(data if isinstance(data, dict) else {})
        except json.JSONDecodeError:
            backup = self.path.with_suffix(f".corrupt-{utc_now_iso().replace(':', '-')}.json")
            self.path.replace(backup)
            data = default_store()
            data["corrupt_backup"] = str(backup)
            return data

    def save(self, data: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def append_report(self, report: dict[str, Any]) -> None:
        data = self.load()
        reports = data.setdefault("reports", [])
        reports.append(report)
        data["reports"] = reports[-20:]
        self.save(data)

    def latest_report(self) -> dict[str, Any] | None:
        reports = self.load().get("reports", [])
        return reports[-1] if reports else None

    def add_decision(self, decision: Decision) -> None:
        data = self.load()
        decisions = data.setdefault("decisions", [])
        decisions.append(to_jsonable(decision))
        self.save(data)

    def decisions(self) -> list[dict[str, Any]]:
        return list(self.load().get("decisions", []))

    def add_radar_decision(self, decision: RadarDecision) -> None:
        data = self.load()
        decisions = data.setdefault("radar_decisions", [])
        decisions.append(to_jsonable(decision))
        data["radar_decisions"] = decisions[-100:]
        self.save(data)

    def radar_decisions(self) -> list[dict[str, Any]]:
        return list(self.load().get("radar_decisions", []))

    def append_radar_report(self, report: dict[str, Any]) -> None:
        data = self.load()
        reports = data.setdefault("radar_reports", [])
        reports.append(report)
        data["radar_reports"] = reports[-20:]
        snapshots = data.setdefault("radar_claims_snapshot", [])
        radar_report = report.get("radar_report", {})
        snapshots.extend(radar_report.get("claims", []))
        data["radar_claims_snapshot"] = snapshots[-100:]
        self.merge_deep_dive_bundle(data, report.get("deep_dives", {}))
        self.save(data)

    def latest_radar_report(self) -> dict[str, Any] | None:
        reports = self.load().get("radar_reports", [])
        return reports[-1] if reports else None

    def find_radar_report(self, report_id: str) -> dict[str, Any] | None:
        for report in reversed(self.load().get("radar_reports", [])):
            radar_report = report.get("radar_report", {})
            if radar_report.get("report_id") == report_id:
                return report
        return None

    def deep_dives(self) -> dict[str, list[dict[str, Any]]]:
        data = self.load()
        return {
            "tasks": list(data.get("deep_dive_tasks", [])),
            "runs": list(data.get("deep_dive_runs", [])),
            "findings": list(data.get("deep_dive_findings", [])),
            "verdicts": list(data.get("deep_dive_verdicts", [])),
            "decisions": list(data.get("deep_dive_decisions", [])),
        }

    def find_deep_dive_task(self, task_id: str) -> dict[str, Any] | None:
        for task in reversed(self.load().get("deep_dive_tasks", [])):
            if task.get("task_id") == task_id:
                return task
        return None

    def append_deep_dive_bundle(self, bundle: dict[str, Any]) -> None:
        data = self.load()
        self.merge_deep_dive_bundle(data, bundle)
        self.save(data)

    def add_deep_dive_decision(self, decision: DeepDiveDecision) -> None:
        data = self.load()
        decisions = data.setdefault("deep_dive_decisions", [])
        decisions.append(to_jsonable(decision))
        data["deep_dive_decisions"] = decisions[-100:]
        self.save(data)

    def merge_deep_dive_bundle(self, data: dict[str, Any], bundle: dict[str, Any]) -> None:
        key_map = {
            "tasks": ("deep_dive_tasks", "task_id", 200),
            "runs": ("deep_dive_runs", "run_id", 200),
            "findings": ("deep_dive_findings", "finding_id", 500),
            "verdicts": ("deep_dive_verdicts", "task_id", 200),
        }
        for bundle_key, (store_key, id_key, limit) in key_map.items():
            incoming = bundle.get(bundle_key) if isinstance(bundle.get(bundle_key), list) else []
            existing = data.setdefault(store_key, [])
            by_id = {str(item.get(id_key) or ""): item for item in existing if item.get(id_key)}
            no_id = [item for item in existing if not item.get(id_key)]
            for item in incoming:
                item_id = str(item.get(id_key) or "")
                if item_id:
                    by_id[item_id] = item
                else:
                    no_id.append(item)
            data[store_key] = (list(by_id.values()) + no_id)[-limit:]


def default_store() -> dict[str, Any]:
    return {
        "reports": [],
        "decisions": [],
        "radar_reports": [],
        "radar_decisions": [],
        "radar_claims_snapshot": [],
        "deep_dive_tasks": [],
        "deep_dive_runs": [],
        "deep_dive_findings": [],
        "deep_dive_verdicts": [],
        "deep_dive_decisions": [],
    }


def normalize_store(data: dict[str, Any]) -> dict[str, Any]:
    normalized = default_store()
    normalized.update(data)
    for key in (
        "reports",
        "decisions",
        "radar_reports",
        "radar_decisions",
        "radar_claims_snapshot",
        "deep_dive_tasks",
        "deep_dive_runs",
        "deep_dive_findings",
        "deep_dive_verdicts",
        "deep_dive_decisions",
    ):
        if not isinstance(normalized.get(key), list):
            normalized[key] = []
    return normalized
