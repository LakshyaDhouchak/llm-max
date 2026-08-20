"""Environment-based configuration.

Everything here has a sensible default so llm-max keeps working with zero
config (SQLite backend, no Redis) — these only matter once you opt into
Phase 2 services via docker-compose and set LLM_MAX_STORAGE_BACKEND=mysql.

.env is loaded automatically (searching upward from the current working
directory) so you never need to manually set $env: variables per terminal
session — set them once in .env at the repo root and they just work,
whether you're running llm-max from the repo root or from core/.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))


@dataclass
class MySqlConfig:
    host: str
    port: int
    database: str
    user: str
    password: str


@dataclass
class RedisConfig:
    host: str
    port: int
    password: str | None


def storage_backend() -> str:
    """Which Storage implementation to use: 'sqlite' (default) or 'mysql'."""
    return os.environ.get("LLM_MAX_STORAGE_BACKEND", "sqlite").lower()


def mysql_config() -> MySqlConfig:
    return MySqlConfig(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        database=os.environ.get("MYSQL_DATABASE", "llm_max"),
        user=os.environ.get("MYSQL_USER", "llm_max"),
        password=os.environ.get("MYSQL_PASSWORD", "changeme"),
    )


def redis_config() -> RedisConfig:
    return RedisConfig(
        host=os.environ.get("REDIS_HOST", "localhost"),
        port=int(os.environ.get("REDIS_PORT", "6379")),
        password=os.environ.get("REDIS_PASSWORD") or None,
    )


def redis_enabled() -> bool:
    """Whether Redis status caching should be attempted at all.

    Defaults to False so the CLI never tries to reach Redis (and never pays
    a connection-timeout cost) unless you've explicitly opted in.
    """
    return os.environ.get("LLM_MAX_REDIS_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )