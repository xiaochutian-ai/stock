from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


class HistoryStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS web_runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    results_json TEXT NOT NULL,
                    details_json TEXT NOT NULL
                )
                """
            )

    def save_run(self, payload: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO web_runs
                (run_id, created_at, status, params_json, summary_json, results_json, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["run_id"],
                    payload["created_at"],
                    payload["status"],
                    json.dumps(payload["params"], ensure_ascii=False),
                    json.dumps(payload["summary"], ensure_ascii=False),
                    json.dumps(payload["results"], ensure_ascii=False),
                    json.dumps(payload["details"], ensure_ascii=False),
                ),
            )

    def list_runs(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT run_id, created_at, status, summary_json FROM web_runs ORDER BY created_at DESC"
            ).fetchall()
        return [
            {
                "run_id": run_id,
                "created_at": created_at,
                "status": status,
                **json.loads(summary_json),
            }
            for run_id, created_at, status, summary_json in rows
        ]

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT run_id, created_at, status, params_json, summary_json, results_json, details_json
                FROM web_runs WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "run_id": row[0],
            "created_at": row[1],
            "status": row[2],
            "params": json.loads(row[3]),
            "summary": json.loads(row[4]),
            "results": json.loads(row[5]),
            "details": json.loads(row[6]),
        }
