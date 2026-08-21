"""SQLite storage backend.

Zero-infra local persistence: one file at ~/.llm-max/llm-max.db (or a path
you pass in, e.g. for tests). This is what makes `llm-max run` and
`llm-max tune` rememberable across invocations before a MySQL server
(Phase 2, team/server deployments) enters the picture at all — same
`Storage` interface, different backend, no CLI code changes needed later.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from llm_max.domain import AutopilotEvent, RunRecord, TunedConfig
from llm_max.storage.base import Storage

DEFAULT_DB_PATH = Path.home() / ".llm-max" / "llm-max.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS run_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id TEXT NOT NULL,
    runtime TEXT NOT NULL,
    prompt TEXT NOT NULL,
    tokens_generated INTEGER NOT NULL,
    total_duration_s REAL NOT NULL,
    tokens_per_sec REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tuned_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id TEXT NOT NULL,
    runtime TEXT NOT NULL,
    config_json TEXT NOT NULL,
    is_locked INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS autopilot_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_run_records_model_id ON run_records(model_id);
CREATE INDEX IF NOT EXISTS idx_tuned_configs_model_id ON tuned_configs(model_id);
CREATE INDEX IF NOT EXISTS idx_autopilot_events_model_id ON autopilot_events(model_id);
"""


class SqliteStore(Storage):
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def save_run(self, record: RunRecord) -> RunRecord:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO run_records
                    (model_id, runtime, prompt, tokens_generated,
                     total_duration_s, tokens_per_sec)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.model_id,
                    record.runtime,
                    record.prompt,
                    record.tokens_generated,
                    record.total_duration_s,
                    record.tokens_per_sec,
                ),
            )
            row = conn.execute(
                "SELECT * FROM run_records WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return _row_to_run_record(row)

    def list_runs(self, model_id: str | None = None, limit: int = 20) -> list[RunRecord]:
        with self._connect() as conn:
            if model_id:
                rows = conn.execute(
                    """
                    SELECT * FROM run_records
                    WHERE model_id = ?
                    ORDER BY created_at DESC, id DESC LIMIT ?
                    """,
                    (model_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM run_records ORDER BY created_at DESC, id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [_row_to_run_record(r) for r in rows]

    def save_tuned_config(self, config: TunedConfig) -> TunedConfig:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tuned_configs (model_id, runtime, config_json, is_locked)
                VALUES (?, ?, ?, ?)
                """,
                (
                    config.model_id,
                    config.runtime,
                    json.dumps(config.config),
                    int(config.is_locked),
                ),
            )
            row = conn.execute(
                "SELECT * FROM tuned_configs WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return _row_to_tuned_config(row)

    def get_tuned_config(self, model_id: str) -> TunedConfig | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM tuned_configs
                WHERE model_id = ?
                ORDER BY created_at DESC, id DESC LIMIT 1
                """,
                (model_id,),
            ).fetchone()
            return _row_to_tuned_config(row) if row else None

    def lock_config(self, model_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE tuned_configs SET is_locked = 1
                WHERE model_id = ? AND id = (
                    SELECT id FROM tuned_configs
                    WHERE model_id = ? ORDER BY created_at DESC, id DESC LIMIT 1
                )
                """,
                (model_id, model_id),
            )

    def save_autopilot_event(self, event: AutopilotEvent) -> AutopilotEvent:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO autopilot_events (model_id, event_type, details_json)
                VALUES (?, ?, ?)
                """,
                (event.model_id, event.event_type, json.dumps(event.details)),
            )
            row = conn.execute(
                "SELECT * FROM autopilot_events WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return _row_to_autopilot_event(row)

    def list_autopilot_events(
        self, model_id: str | None = None, limit: int = 20
    ) -> list[AutopilotEvent]:
        with self._connect() as conn:
            if model_id:
                rows = conn.execute(
                    """
                    SELECT * FROM autopilot_events
                    WHERE model_id = ?
                    ORDER BY created_at DESC, id DESC LIMIT ?
                    """,
                    (model_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM autopilot_events ORDER BY created_at DESC, id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [_row_to_autopilot_event(r) for r in rows]


def _row_to_run_record(row: sqlite3.Row) -> RunRecord:
    return RunRecord(
        id=row["id"],
        model_id=row["model_id"],
        runtime=row["runtime"],
        prompt=row["prompt"],
        tokens_generated=row["tokens_generated"],
        total_duration_s=row["total_duration_s"],
        tokens_per_sec=row["tokens_per_sec"],
        created_at=row["created_at"],
    )


def _row_to_tuned_config(row: sqlite3.Row) -> TunedConfig:
    return TunedConfig(
        id=row["id"],
        model_id=row["model_id"],
        runtime=row["runtime"],
        config=json.loads(row["config_json"]),
        is_locked=bool(row["is_locked"]),
        created_at=row["created_at"],
    )


def _row_to_autopilot_event(row: sqlite3.Row) -> AutopilotEvent:
    return AutopilotEvent(
        id=row["id"],
        model_id=row["model_id"],
        event_type=row["event_type"],
        details=json.loads(row["details_json"]),
        created_at=row["created_at"],
    )