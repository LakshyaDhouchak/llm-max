from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str


class TunedConfigStatusResponse(BaseModel):
    model_id: str
    config: Optional[dict] = None
    is_locked: bool = False
    created_at: Optional[str] = None
    has_config: bool