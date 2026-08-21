"""MySQL storage backend — Phase 2, team/server deployment.

Implements the exact same `Storage` interface as `SqliteStore`.
The CLI doesn't know or care which backend is active (see
config.storage_backend()); swapping is a one-line env var change,
not a code change.

Schema is managed by Flyway (see migrations/sql/V1__init_schema.sql) —
this module never creates or alters tables itself.
"""

from __future__ import annotations

import json

from llm_max.config import MySqlConfig, mysql_config
from llm_max.domain import AutopilotEvent, RunRecord, TunedConfig
from llm_max.storage.base import Storage


class MySqlStore(Storage):
    def __init__(self, config: MySqlConfig | None = None):
        self.config = config or mysql_config()

    def _connect(self):
        # Imported lazily so `mysql-connector-python` is only required when
        # the MySQL backend is actually selected.
        import mysql.connector

        return mysql.connector.connect(
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
            user=self.config.user,
            password=self.config.password,
        )

    def save_run(self, record: RunRecord) -> RunRecord:
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO run_records
                    (
                        model_id,
                        runtime,
                        prompt,
                        tokens_generated,
                        total_duration_s,
                        tokens_per_sec
                    )
                VALUES (%s, %s, %s, %s, %s, %s)
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
            conn.commit()

            new_id = cursor.lastrowid

            cursor.execute(
                "SELECT * FROM run_records WHERE id = %s",
                (new_id,),
            )
            row = cursor.fetchone()

            return _row_to_run_record(cursor.column_names, row)
        finally:
            conn.close()

    def list_runs(
        self,
        model_id: str | None = None,
        limit: int = 20,
    ) -> list[RunRecord]:
        conn = self._connect()
        try:
            cursor = conn.cursor()

            if model_id:
                cursor.execute(
                    """
                    SELECT *
                    FROM run_records
                    WHERE model_id = %s
                    ORDER BY created_at DESC, id DESC
                    LIMIT %s
                    """,
                    (model_id, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT *
                    FROM run_records
                    ORDER BY created_at DESC, id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )

            rows = cursor.fetchall()

            return [
                _row_to_run_record(cursor.column_names, row)
                for row in rows
            ]
        finally:
            conn.close()

    def save_tuned_config(self, config: TunedConfig) -> TunedConfig:
        conn = self._connect()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO tuned_configs
                    (
                        model_id,
                        runtime,
                        config_json,
                        is_locked
                    )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    config.model_id,
                    config.runtime,
                    json.dumps(config.config),
                    int(config.is_locked),
                ),
            )

            conn.commit()

            new_id = cursor.lastrowid

            cursor.execute(
                "SELECT * FROM tuned_configs WHERE id = %s",
                (new_id,),
            )
            row = cursor.fetchone()

            return _row_to_tuned_config(cursor.column_names, row)
        finally:
            conn.close()

    def get_tuned_config(self, model_id: str) -> TunedConfig | None:
        conn = self._connect()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT *
                FROM tuned_configs
                WHERE model_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (model_id,),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return _row_to_tuned_config(cursor.column_names, row)
        finally:
            conn.close()

    def lock_config(self, model_id: str) -> None:
        conn = self._connect()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE tuned_configs
                SET is_locked = 1
                WHERE model_id = %s
                  AND id = (
                      SELECT id
                      FROM (
                          SELECT id
                          FROM tuned_configs
                          WHERE model_id = %s
                          ORDER BY created_at DESC, id DESC
                          LIMIT 1
                      ) AS latest
                  )
                """,
                (model_id, model_id),
            )

            conn.commit()
        finally:
            conn.close()

    def save_autopilot_event(
        self,
        event: AutopilotEvent,
    ) -> AutopilotEvent:
        conn = self._connect()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO autopilot_events
                    (
                        model_id,
                        event_type,
                        details_json
                    )
                VALUES (%s, %s, %s)
                """,
                (
                    event.model_id,
                    event.event_type,
                    json.dumps(event.details),
                ),
            )

            conn.commit()

            new_id = cursor.lastrowid

            cursor.execute(
                "SELECT * FROM autopilot_events WHERE id = %s",
                (new_id,),
            )
            row = cursor.fetchone()

            return _row_to_autopilot_event(
                cursor.column_names,
                row,
            )
        finally:
            conn.close()

    def list_autopilot_events(
        self,
        model_id: str | None = None,
        limit: int = 20,
    ) -> list[AutopilotEvent]:
        conn = self._connect()
        try:
            cursor = conn.cursor()

            if model_id:
                cursor.execute(
                    """
                    SELECT *
                    FROM autopilot_events
                    WHERE model_id = %s
                    ORDER BY created_at DESC, id DESC
                    LIMIT %s
                    """,
                    (model_id, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT *
                    FROM autopilot_events
                    ORDER BY created_at DESC, id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )

            rows = cursor.fetchall()

            return [
                _row_to_autopilot_event(
                    cursor.column_names,
                    row,
                )
                for row in rows
            ]
        finally:
            conn.close()


def _row_to_run_record(
    columns: tuple,
    row: tuple,
) -> RunRecord:
    d = dict(zip(columns, row))

    return RunRecord(
        id=d["id"],
        model_id=d["model_id"],
        runtime=d["runtime"],
        prompt=d["prompt"],
        tokens_generated=d["tokens_generated"],
        total_duration_s=float(d["total_duration_s"]),
        tokens_per_sec=(
            float(d["tokens_per_sec"])
            if d["tokens_per_sec"] is not None
            else None
        ),
        created_at=str(d["created_at"]),
    )


def _row_to_autopilot_event(
    columns: tuple,
    row: tuple,
) -> AutopilotEvent:
    d = dict(zip(columns, row))

    return AutopilotEvent(
        id=d["id"],
        model_id=d["model_id"],
        event_type=d["event_type"],
        details=json.loads(d["details_json"]),
        created_at=str(d["created_at"]),
    )


def _row_to_tuned_config(
    columns: tuple,
    row: tuple,
) -> TunedConfig:
    d = dict(zip(columns, row))

    return TunedConfig(
        id=d["id"],
        model_id=d["model_id"],
        runtime=d["runtime"],
        config=json.loads(d["config_json"]),
        is_locked=bool(d["is_locked"]),
        created_at=str(d["created_at"]),
    )