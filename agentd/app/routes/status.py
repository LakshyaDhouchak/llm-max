from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from llm_max.config import redis_enabled
from llm_max.domain import HardwareProfile, RunRecord
from llm_max.profiler import scan_hardware
from llm_max.storage.base import Storage

from app.dependencies import get_storage

router = APIRouter(tags=["status"])


@router.get("/status", response_model=HardwareProfile)
def status() -> HardwareProfile:
    """Hardware status, using the Redis cache if LLM_MAX_REDIS_ENABLED is
    set — same behavior as `llm-max status`."""
    if redis_enabled():
        from llm_max.storage.redis_client import StatusCache

        cache = StatusCache()
        cached = cache.get_last_scan()
        if cached is not None:
            return cached

        fresh = scan_hardware()
        cache.set_last_scan(fresh)
        return fresh

    return scan_hardware()


@router.get("/history", response_model=list[RunRecord])
def history(
    model_id: str | None = Query(default=None),
    limit: int = Query(default=20, le=200),
    storage: Storage = Depends(get_storage),
) -> list[RunRecord]:
    """Recent `run` history, most recent first."""
    return storage.list_runs(model_id=model_id, limit=limit)