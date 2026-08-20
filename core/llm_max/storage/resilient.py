"""Resilient storage wrapper: tries a primary backend, falls back to a
secondary one on any failure.

Used to make the MySQL backend "opt-in but never a hard requirement" — if
Docker isn't running, MySQL is unreachable, or credentials are wrong,
`llm-max run`/`history` keep working against local SQLite instead of
crashing. This mirrors the soft-fail philosophy already used for Redis
(storage/redis_client.py): infrastructure being down should degrade
gracefully, not break the CLI.

Catches broad Exception deliberately — any primary-backend failure (network
refused, auth failure, missing table, timeout) should trigger fallback, not
just a curated subset of error types.
"""

from __future__ import annotations

from llm_max.domain import RunRecord, TunedConfig
from llm_max.storage.base import Storage


class FallbackStorage(Storage):
    def __init__(self, primary: Storage, fallback: Storage):
        self.primary = primary
        self.fallback = fallback
        # Set after every call — lets callers (e.g. the CLI) show a
        # one-line note when the fallback was actually used, without
        # this class owning any presentation concerns itself.
        self.last_used_fallback = False

    def _call(self, method_name: str, *args, **kwargs):
        try:
            result = getattr(self.primary, method_name)(*args, **kwargs)
            self.last_used_fallback = False
            return result
        except Exception:
            self.last_used_fallback = True
            return getattr(self.fallback, method_name)(*args, **kwargs)

    def save_run(self, record: RunRecord) -> RunRecord:
        return self._call("save_run", record)

    def list_runs(
        self, model_id: str | None = None, limit: int = 20
    ) -> list[RunRecord]:
        return self._call("list_runs", model_id=model_id, limit=limit)

    def save_tuned_config(self, config: TunedConfig) -> TunedConfig:
        return self._call("save_tuned_config", config)

    def get_tuned_config(self, model_id: str) -> TunedConfig | None:
        return self._call("get_tuned_config", model_id)

    def lock_config(self, model_id: str) -> None:
        return self._call("lock_config", model_id)