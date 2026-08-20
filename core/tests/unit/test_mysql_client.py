from llm_max.domain import RunRecord, TunedConfig
from llm_max.storage.mysql_client import MySqlStore


class FakeCursor:
    def __init__(self, fetchone_result=None, fetchall_result=None, lastrowid=1):
        self.column_names = ()
        self._fetchone_result = fetchone_result
        self._fetchall_result = fetchall_result or []
        self.lastrowid = lastrowid
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        return self._fetchone_result

    def fetchall(self):
        return self._fetchall_result


class FakeConnection:
    def __init__(self, cursor: FakeCursor):
        self._cursor = cursor
        self.committed = False
        self.closed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def _run_row():
    columns = (
        "id", "model_id", "runtime", "prompt", "tokens_generated",
        "total_duration_s", "tokens_per_sec", "created_at",
    )
    row = (1, "llama3.1:8b", "ollama", "hello", 42, 1.23, 34.1, "2026-01-01 00:00:00")
    return columns, row


def test_save_run_returns_saved_record(mocker):
    columns, row = _run_row()
    cursor = FakeCursor(fetchone_result=row, lastrowid=1)
    cursor.column_names = columns
    conn = FakeConnection(cursor)
    mocker.patch("mysql.connector.connect", return_value=conn)

    store = MySqlStore()
    result = store.save_run(
        RunRecord(model_id="llama3.1:8b", prompt="hello", tokens_generated=42, total_duration_s=1.23)
    )

    assert result.id == 1
    assert result.model_id == "llama3.1:8b"
    assert conn.committed is True
    assert conn.closed is True


def test_list_runs_parses_rows(mocker):
    columns, row = _run_row()
    cursor = FakeCursor(fetchall_result=[row])
    cursor.column_names = columns
    conn = FakeConnection(cursor)
    mocker.patch("mysql.connector.connect", return_value=conn)

    store = MySqlStore()
    results = store.list_runs()

    assert len(results) == 1
    assert results[0].model_id == "llama3.1:8b"
    assert conn.closed is True


def test_list_runs_filters_by_model_id(mocker):
    cursor = FakeCursor(fetchall_result=[])
    conn = FakeConnection(cursor)
    mocker.patch("mysql.connector.connect", return_value=conn)

    store = MySqlStore()
    store.list_runs(model_id="llama3.1:8b")

    query, params = cursor.executed[0]
    assert "WHERE model_id" in query
    assert params[0] == "llama3.1:8b"


def _config_row():
    import json

    columns = ("id", "model_id", "runtime", "config_json", "is_locked", "created_at")
    row = (1, "m", "ollama", json.dumps({"num_ctx": 4096}), 0, "2026-01-01 00:00:00")
    return columns, row


def test_save_tuned_config(mocker):
    columns, row = _config_row()
    cursor = FakeCursor(fetchone_result=row, lastrowid=1)
    cursor.column_names = columns
    conn = FakeConnection(cursor)
    mocker.patch("mysql.connector.connect", return_value=conn)

    store = MySqlStore()
    result = store.save_tuned_config(TunedConfig(model_id="m", config={"num_ctx": 4096}))

    assert result.config == {"num_ctx": 4096}
    assert result.is_locked is False


def test_get_tuned_config_returns_none_when_missing(mocker):
    cursor = FakeCursor(fetchone_result=None)
    conn = FakeConnection(cursor)
    mocker.patch("mysql.connector.connect", return_value=conn)

    store = MySqlStore()
    assert store.get_tuned_config("nonexistent") is None


def test_lock_config_executes_update(mocker):
    cursor = FakeCursor()
    conn = FakeConnection(cursor)
    mocker.patch("mysql.connector.connect", return_value=conn)

    store = MySqlStore()
    store.lock_config("m")

    query, params = cursor.executed[0]
    assert "UPDATE tuned_configs" in query
    assert conn.committed is True