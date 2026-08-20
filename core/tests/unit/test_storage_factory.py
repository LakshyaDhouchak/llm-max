from llm_max.storage import get_storage
from llm_max.storage.resilient import FallbackStorage
from llm_max.storage.sqlite_store import SqliteStore


def test_get_storage_defaults_to_sqlite(monkeypatch):
    monkeypatch.delenv("LLM_MAX_STORAGE_BACKEND", raising=False)
    assert isinstance(get_storage(), SqliteStore)


def test_get_storage_wraps_mysql_in_fallback(monkeypatch):
    monkeypatch.setenv("LLM_MAX_STORAGE_BACKEND", "mysql")
    storage = get_storage()

    assert isinstance(storage, FallbackStorage)
    assert isinstance(storage.fallback, SqliteStore)