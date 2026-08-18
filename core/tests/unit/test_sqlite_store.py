import pytest

from llm_max.domain import RunRecord, TunedConfig
from llm_max.storage.sqlite_store import SqliteStore


@pytest.fixture
def store(tmp_path):
    return SqliteStore(db_path=tmp_path / "test.db")


def test_save_and_list_runs(store):
    record = RunRecord(
        model_id="llama3.1:8b",
        prompt="hello",
        tokens_generated=42,
        total_duration_s=1.23,
        tokens_per_sec=34.1,
    )
    saved = store.save_run(record)

    assert saved.id is not None
    assert saved.created_at is not None

    runs = store.list_runs()
    assert len(runs) == 1
    assert runs[0].model_id == "llama3.1:8b"
    assert runs[0].tokens_generated == 42


def test_list_runs_filters_by_model(store):
    store.save_run(RunRecord(model_id="a", prompt="p", tokens_generated=1, total_duration_s=1))
    store.save_run(RunRecord(model_id="b", prompt="p", tokens_generated=1, total_duration_s=1))

    runs = store.list_runs(model_id="a")
    assert len(runs) == 1
    assert runs[0].model_id == "a"


def test_list_runs_respects_limit(store):
    for i in range(5):
        store.save_run(
            RunRecord(model_id="a", prompt=f"p{i}", tokens_generated=1, total_duration_s=1)
        )
    runs = store.list_runs(limit=2)
    assert len(runs) == 2


def test_list_runs_empty_by_default(store):
    assert store.list_runs() == []


def test_save_and_get_tuned_config(store):
    config = TunedConfig(model_id="llama3.1:8b", config={"num_ctx": 4096})
    saved = store.save_tuned_config(config)

    assert saved.id is not None
    assert saved.is_locked is False

    fetched = store.get_tuned_config("llama3.1:8b")
    assert fetched is not None
    assert fetched.config == {"num_ctx": 4096}


def test_get_tuned_config_returns_most_recent(store):
    store.save_tuned_config(TunedConfig(model_id="m", config={"num_ctx": 2048}))
    store.save_tuned_config(TunedConfig(model_id="m", config={"num_ctx": 4096}))

    fetched = store.get_tuned_config("m")
    assert fetched.config == {"num_ctx": 4096}


def test_get_tuned_config_missing_returns_none(store):
    assert store.get_tuned_config("nonexistent") is None


def test_lock_config_locks_most_recent(store):
    store.save_tuned_config(TunedConfig(model_id="m", config={"num_ctx": 2048}))
    store.save_tuned_config(TunedConfig(model_id="m", config={"num_ctx": 4096}))
    store.lock_config("m")

    fetched = store.get_tuned_config("m")
    assert fetched.is_locked is True
    assert fetched.config == {"num_ctx": 4096}