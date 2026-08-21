"""Storage interface.

`SqliteStore` (Phase 1/2, local, zero-infra) and `MySqlStore` (Phase 2,
team/server deployment) both implement this contract, so the CLI and
agentd never need to know which backend is active.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from llm_max.domain import AutopilotEvent, RunRecord, TunedConfig


class Storage(ABC):
    @abstractmethod
    def save_run(self, record: RunRecord) -> RunRecord:
        """Persist a run record. Returns the record with id/created_at set."""

    @abstractmethod
    def list_runs(self, model_id: str | None = None, limit: int = 20) -> list[RunRecord]:
        """List recent run records, most recent first, optionally filtered by model."""

    @abstractmethod
    def save_tuned_config(self, config: TunedConfig) -> TunedConfig:
        """Insert or update a tuned config for a model."""

    @abstractmethod
    def get_tuned_config(self, model_id: str) -> TunedConfig | None:
        """Get the current (most recent) tuned config for a model, if any."""

    @abstractmethod
    def lock_config(self, model_id: str) -> None:
        """Mark a model's current tuned config as locked (won't be auto-tuned)."""

    @abstractmethod
    def save_autopilot_event(self, event: AutopilotEvent) -> AutopilotEvent:
        """Persist an autopilot audit-trail event."""

    @abstractmethod
    def list_autopilot_events(
        self, model_id: str | None = None, limit: int = 20
    ) -> list[AutopilotEvent]:
        """List recent autopilot events, most recent first, optionally
        filtered by model."""