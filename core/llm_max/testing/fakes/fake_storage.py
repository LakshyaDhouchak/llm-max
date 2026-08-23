"""In-memory Storage double.

Used by tests that need real insert/query semantics (e.g. "get the most
recently saved tuned config") without file I/O (SqliteStore) or mocking a
network client (MySqlStore). Shared across launcher/ and autotune/ tests.
"""

from __future__ import annotations

from llm_max.domain import AutopilotEvent, RunRecord, TunedConfig
from llm_max.storage.base import Storage


class InMemoryStorage(Storage):
    def __init__(self):
        self.saved_runs: list[RunRecord] = []
        self.tuned_configs: list[TunedConfig] = []
        self.autopilot_events: list[AutopilotEvent] = []

    def save_run(self, record: RunRecord) -> RunRecord:
        saved = record.model_copy(update={"id": len(self.saved_runs) + 1})
        self.saved_runs.append(saved)
        return saved

    def list_runs(self, model_id: str | None = None, limit: int = 20) -> list[RunRecord]:
        matches = [r for r in self.saved_runs if model_id is None or r.model_id == model_id]
        return list(reversed(matches))[:limit]

    def save_tuned_config(self, config: TunedConfig) -> TunedConfig:
        saved = config.model_copy(update={"id": len(self.tuned_configs) + 1})
        self.tuned_configs.append(saved)
        return saved

    def get_tuned_config(self, model_id: str) -> TunedConfig | None:
        matches = [c for c in self.tuned_configs if c.model_id == model_id]
        return matches[-1] if matches else None

    def lock_config(self, model_id: str) -> None:
        for i in range(len(self.tuned_configs) - 1, -1, -1):
            if self.tuned_configs[i].model_id == model_id:
                self.tuned_configs[i] = self.tuned_configs[i].model_copy(
                    update={"is_locked": True}
                )
                return

    def save_autopilot_event(self, event: AutopilotEvent) -> AutopilotEvent:
        saved = event.model_copy(update={"id": len(self.autopilot_events) + 1})
        self.autopilot_events.append(saved)
        return saved

    def list_autopilot_events(
        self, model_id: str | None = None, limit: int = 20
    ) -> list[AutopilotEvent]:
        matches = [
            e for e in self.autopilot_events if model_id is None or e.model_id == model_id
        ]
        return list(reversed(matches))[:limit]