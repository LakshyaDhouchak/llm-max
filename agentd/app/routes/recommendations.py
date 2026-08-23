"""Autopilot status/disable routes.

`enable` is deliberately NOT exposed here in v1. Phase 3's design
(docs/PHASE3_DESIGN.md section 5) makes autopilot an explicit, visible,
foreground process the user starts and watches — a fire-and-forget HTTP
POST that spawns a background loop is a materially different (and
riskier) trust model than that, and deserves its own deliberate design
pass (e.g. websocket/SSE streaming of live status, explicit stop
semantics) rather than being added as a side effect of building this
route file. Status and disable (locking) carry no such risk — they're
read-only and safe respectively — so they ship now.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from llm_max.storage.base import Storage

from app.dependencies import get_storage
from app.schemas.responses import TunedConfigStatusResponse

router = APIRouter(prefix="/autopilot", tags=["autopilot"])


@router.get("/{model_id}/status", response_model=TunedConfigStatusResponse)
def autopilot_status(model_id: str, storage: Storage = Depends(get_storage)) -> TunedConfigStatusResponse:
    config = storage.get_tuned_config(model_id)
    if config is None:
        return TunedConfigStatusResponse(model_id=model_id, has_config=False)
    return TunedConfigStatusResponse(
        model_id=model_id,
        config=config.config,
        is_locked=config.is_locked,
        created_at=config.created_at,
        has_config=True,
    )


@router.post("/{model_id}/disable")
def autopilot_disable(model_id: str, storage: Storage = Depends(get_storage)) -> dict:
    """Lock the model's current config so autopilot (run via CLI) skips it."""
    existing = storage.get_tuned_config(model_id)
    if existing is None:
        raise HTTPException(
            status_code=404,
            detail=f"No tuned config exists yet for {model_id} — run tune first.",
        )
    storage.lock_config(model_id)
    return {"model_id": model_id, "locked": True}