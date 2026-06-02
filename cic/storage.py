from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Decision, to_jsonable, utc_now_iso


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

    def append_radar_report(self, report: dict[str, Any]) -> None:
        data = self.load()
        reports = data.setdefault("radar_reports", [])
        reports.append(report)
        data["radar_reports"] = reports[-20:]
        snapshots = data.setdefault("radar_claims_snapshot", [])
        radar_report = report.get("radar_report", {})
        snapshots.extend(radar_report.get("claims", []))
        data["radar_claims_snapshot"] = snapshots[-100:]
        self.save(data)

    def latest_radar_report(self) -> dict[str, Any] | None:
        reports = self.load().get("radar_reports", [])
        return reports[-1] if reports else None


def default_store() -> dict[str, Any]:
    return {"reports": [], "decisions": [], "radar_reports": [], "radar_decisions": [], "radar_claims_snapshot": []}


def normalize_store(data: dict[str, Any]) -> dict[str, Any]:
    normalized = default_store()
    normalized.update(data)
    for key in ("reports", "decisions", "radar_reports", "radar_decisions", "radar_claims_snapshot"):
        if not isinstance(normalized.get(key), list):
            normalized[key] = []
    return normalized
