from llm_max.config import storage_backend
from llm_max.storage.base import Storage
from llm_max.storage.sqlite_store import SqliteStore


def get_storage() -> Storage:
    """Returns the active Storage backend based on LLM_MAX_STORAGE_BACKEND.

    Defaults to SqliteStore (zero-infra). Set LLM_MAX_STORAGE_BACKEND=mysql
    to switch, once migrations/sql has been applied to a running MySQL
    instance (see docker/docker-compose.yml).
    """
    backend = storage_backend()
    if backend == "mysql":
        from llm_max.storage.mysql_client import MySqlStore

        return MySqlStore()
    return SqliteStore()


__all__ = ["Storage", "SqliteStore", "get_storage"]