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
            return {"reports": [], "decisions": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            backup = self.path.with_suffix(f".corrupt-{utc_now_iso().replace(':', '-')}.json")
            self.path.replace(backup)
            return {"reports": [], "decisions": [], "corrupt_backup": str(backup)}

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
