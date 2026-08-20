from llm_max.config import mysql_config, redis_config, redis_enabled, storage_backend


def test_storage_backend_defaults_to_sqlite(monkeypatch):
    monkeypatch.delenv("LLM_MAX_STORAGE_BACKEND", raising=False)
    assert storage_backend() == "sqlite"


def test_storage_backend_reads_env(monkeypatch):
    monkeypatch.setenv("LLM_MAX_STORAGE_BACKEND", "MySQL")
    assert storage_backend() == "mysql"  # case-insensitive


def test_mysql_config_defaults(monkeypatch):
    for var in ["MYSQL_HOST", "MYSQL_PORT", "MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD"]:
        monkeypatch.delenv(var, raising=False)

    config = mysql_config()
    assert config.host == "localhost"
    assert config.port == 3306
    assert config.database == "llm_max"


def test_mysql_config_reads_env(monkeypatch):
    monkeypatch.setenv("MYSQL_HOST", "db.example.com")
    monkeypatch.setenv("MYSQL_PORT", "3307")

    config = mysql_config()
    assert config.host == "db.example.com"
    assert config.port == 3307


def test_redis_config_defaults(monkeypatch):
    for var in ["REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD"]:
        monkeypatch.delenv(var, raising=False)

    config = redis_config()
    assert config.host == "localhost"
    assert config.port == 6379
    assert config.password is None


def test_redis_enabled_defaults_false(monkeypatch):
    monkeypatch.delenv("LLM_MAX_REDIS_ENABLED", raising=False)
    assert redis_enabled() is False


def test_redis_enabled_true_variants(monkeypatch):
    for value in ["1", "true", "True", "yes"]:
        monkeypatch.setenv("LLM_MAX_REDIS_ENABLED", value)
        assert redis_enabled() is True