import pytest

from llm_max.domain import RunRecord, TunedConfig
from llm_max.storage.base import Storage
from llm_max.storage.resilient import FallbackStorage


class WorkingStorage(Storage):
    def __init__(self):
        self.calls = []

    def save_run(self, record):
        self.calls.append(("save_run", record))
        return record.model_copy(update={"id": 1})

    def list_runs(self, model_id=None, limit=20):
        self.calls.append(("list_runs", model_id, limit))
        return []

    def save_tuned_config(self, config):
        self.calls.append(("save_tuned_config", config))
        return config.model_copy(update={"id": 1})

    def get_tuned_config(self, model_id):
        self.calls.append(("get_tuned_config", model_id))
        return None

    def lock_config(self, model_id):
        self.calls.append(("lock_config", model_id))


class BrokenStorage(Storage):
    """Simulates an unreachable backend — every method raises."""

    def save_run(self, record):
        raise ConnectionError("simulated connection failure")

    def list_runs(self, model_id=None, limit=20):
        raise ConnectionError("simulated connection failure")

    def save_tuned_config(self, config):
        raise ConnectionError("simulated connection failure")

    def get_tuned_config(self, model_id):
        raise ConnectionError("simulated connection failure")

    def lock_config(self, model_id):
        raise ConnectionError("simulated connection failure")


SAMPLE_RUN = RunRecord(
    model_id="m", prompt="p", tokens_generated=1, total_duration_s=1.0
)


def test_uses_primary_when_it_succeeds():
    primary = WorkingStorage()
    fallback = WorkingStorage()
    storage = FallbackStorage(primary=primary, fallback=fallback)

    storage.save_run(SAMPLE_RUN)

    assert len(primary.calls) == 1
    assert len(fallback.calls) == 0
    assert storage.last_used_fallback is False


def test_falls_back_when_primary_raises():
    primary = BrokenStorage()
    fallback = WorkingStorage()
    storage = FallbackStorage(primary=primary, fallback=fallback)

    result = storage.save_run(SAMPLE_RUN)

    assert len(fallback.calls) == 1
    assert result.id == 1
    assert storage.last_used_fallback is True


def test_fallback_flag_resets_on_next_successful_call():
    primary = BrokenStorage()
    fallback = WorkingStorage()
    storage = FallbackStorage(primary=primary, fallback=fallback)

    storage.save_run(SAMPLE_RUN)
    assert storage.last_used_fallback is True

    # Swap in a working primary and confirm the flag clears on success.
    storage.primary = WorkingStorage()
    storage.save_run(SAMPLE_RUN)
    assert storage.last_used_fallback is False


def test_list_runs_falls_back():
    primary = BrokenStorage()
    fallback = WorkingStorage()
    storage = FallbackStorage(primary=primary, fallback=fallback)

    storage.list_runs(model_id="m", limit=5)

    assert fallback.calls == [("list_runs", "m", 5)]


def test_get_tuned_config_falls_back():
    primary = BrokenStorage()
    fallback = WorkingStorage()
    storage = FallbackStorage(primary=primary, fallback=fallback)

    storage.get_tuned_config("m")

    assert fallback.calls == [("get_tuned_config", "m")]


def test_lock_config_falls_back():
    primary = BrokenStorage()
    fallback = WorkingStorage()
    storage = FallbackStorage(primary=primary, fallback=fallback)

    storage.lock_config("m")

    assert fallback.calls == [("lock_config", "m")]


def test_save_tuned_config_falls_back():
    primary = BrokenStorage()
    fallback = WorkingStorage()
    storage = FallbackStorage(primary=primary, fallback=fallback)

    config = TunedConfig(model_id="m", config={"num_ctx": 2048})
    result = storage.save_tuned_config(config)

    assert fallback.calls == [("save_tuned_config", config)]
    assert result.id == 1