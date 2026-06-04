from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .forward_alpha import default_forward_alpha_summary
from .models import utc_now_iso


class ForwardAlphaStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ensure_schema()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def ensure_schema(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS forward_alpha_runs (
                    run_id TEXT PRIMARY KEY,
                    stock_code TEXT NOT NULL,
                    stock_name TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS source_candidates (
                    source_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_family TEXT NOT NULL,
                    license_status TEXT NOT NULL,
                    automation_allowed INTEGER NOT NULL,
                    collection_status TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS manual_import_tasks (
                    task_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS source_decisions (
                    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    decided_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )

    def append_run(self, result: dict[str, Any]) -> None:
        run = result.get("forward_alpha") if isinstance(result.get("forward_alpha"), dict) else {}
        run_id = str(run.get("run_id") or "")
        if not run_id:
            return
        with self.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO forward_alpha_runs
                    (run_id, stock_code, stock_name, generated_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    str(run.get("stock_code") or ""),
                    str(run.get("stock_name") or ""),
                    str(run.get("generated_at") or utc_now_iso()),
                    json.dumps(result, ensure_ascii=False),
                ),
            )
            for source in run.get("source_candidates", []) or []:
                if not isinstance(source, dict):
                    continue
                connection.execute(
                    """
                    INSERT OR REPLACE INTO source_candidates
                        (source_id, run_id, source_name, source_family, license_status,
                         automation_allowed, collection_status, payload_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(source.get("source_id") or ""),
                        run_id,
                        str(source.get("source_name") or ""),
                        str(source.get("source_family") or ""),
                        str(source.get("license_status") or "unknown"),
                        1 if source.get("automation_allowed") else 0,
                        str(source.get("collection_status") or ""),
                        json.dumps(source, ensure_ascii=False),
                    ),
                )
            for task in run.get("manual_import_tasks", []) or []:
                if not isinstance(task, dict):
                    continue
                connection.execute(
                    """
                    INSERT OR REPLACE INTO manual_import_tasks
                        (task_id, run_id, source_id, status, payload_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(task.get("task_id") or ""),
                        run_id,
                        str(task.get("source_id") or ""),
                        str(task.get("status") or "pending"),
                        json.dumps(task, ensure_ascii=False),
                    ),
                )

    def latest_run(self) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM forward_alpha_runs ORDER BY generated_at DESC LIMIT 1"
            ).fetchone()
        return json.loads(row["payload_json"]) if row else default_forward_alpha_summary()

    def find_run(self, run_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM forward_alpha_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def sources(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM source_candidates ORDER BY rowid DESC LIMIT 200"
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def record_source_decision(self, source_id: str, decision: str, reason: str, payload: dict[str, Any]) -> dict[str, Any]:
        decided_at = utc_now_iso()
        decision_payload = {
            "source_id": source_id,
            "decision": decision,
            "reason": reason,
            "decided_at": decided_at,
            "metadata": payload,
        }
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO source_decisions (source_id, decision, reason, decided_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (source_id, decision, reason, decided_at, json.dumps(decision_payload, ensure_ascii=False)),
            )
            row = connection.execute(
                "SELECT payload_json FROM source_candidates WHERE source_id = ?",
                (source_id,),
            ).fetchone()
            if row:
                source = json.loads(row["payload_json"])
                if decision == "block":
                    source["collection_status"] = "blocked"
                    source["automation_allowed"] = False
                elif decision == "mark_authorized":
                    source["license_status"] = "clear"
                    source["collection_status"] = "auto_collectable" if source.get("source_url") else "manual_import_required"
                elif decision == "approve_manual":
                    source["collection_status"] = "manual_import_required"
                connection.execute(
                    """
                    UPDATE source_candidates
                    SET license_status = ?, automation_allowed = ?, collection_status = ?, payload_json = ?
                    WHERE source_id = ?
                    """,
                    (
                        str(source.get("license_status") or "unknown"),
                        1 if source.get("automation_allowed") else 0,
                        str(source.get("collection_status") or ""),
                        json.dumps(source, ensure_ascii=False),
                        source_id,
                    ),
                )
        return decision_payload

    def record_manual_import(self, task_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        imported_at = utc_now_iso()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM manual_import_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if not row:
                return None
            task = json.loads(row["payload_json"])
            task["status"] = "imported"
            task["imported_at"] = imported_at
            task["import_payload"] = payload
            connection.execute(
                "UPDATE manual_import_tasks SET status = ?, payload_json = ? WHERE task_id = ?",
                ("imported", json.dumps(task, ensure_ascii=False), task_id),
            )
        return task
