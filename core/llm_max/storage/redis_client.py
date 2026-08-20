"""Redis status cache — Phase 2.

Not part of the Storage interface: this is deliberately a separate,
narrower concern. Storage is durable history (run records, tuned configs);
this is a short-TTL cache of the most recent hardware scan, so repeated
`llm-max status` calls (or a future web dashboard) don't need to re-run
pynvml/psutil on every request.

Every method here fails soft: if Redis is unreachable, misconfigured, or
not running, callers get None / False rather than an exception. Redis is
optional infrastructure — its absence should never break the CLI.
"""

from __future__ import annotations

from llm_max.config import RedisConfig, redis_config
from llm_max.domain import HardwareProfile

_SCAN_CACHE_KEY = "llm-max:last-scan"
_DEFAULT_TTL_SECONDS = 300  # 5 minutes


class StatusCache:
    def __init__(self, config: RedisConfig | None = None):
        self.config = config or redis_config()

    def _client(self):
        import redis

        return redis.Redis(
            host=self.config.host,
            port=self.config.port,
            password=self.config.password,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
            decode_responses=True,
        )

    def set_last_scan(
        self, profile: HardwareProfile, ttl_seconds: int = _DEFAULT_TTL_SECONDS
    ) -> bool:
        """Cache a hardware scan result. Returns True on success, False if
        Redis is unreachable — callers should treat False as a no-op, not
        an error."""
        try:
            client = self._client()
            client.set(_SCAN_CACHE_KEY, profile.model_dump_json(), ex=ttl_seconds)
            return True
        except Exception:
            return False

    def get_last_scan(self) -> HardwareProfile | None:
        """Return the cached scan if present and unexpired, else None.
        Also returns None (never raises) if Redis is unreachable."""
        try:
            client = self._client()
            raw = client.get(_SCAN_CACHE_KEY)
            if raw is None:
                return None
            return HardwareProfile.model_validate_json(raw)
        except Exception:
            return None

    def is_available(self) -> bool:
        try:
            client = self._client()
            return bool(client.ping())
        except Exception:
            return False