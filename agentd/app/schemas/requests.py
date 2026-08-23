"""Request body schemas.

Response schemas mostly aren't needed here — llm_max.domain, .bench, and
.autotune already define pydantic models (HardwareProfile, RunRecord,
TuningSession, etc.), and FastAPI serializes those directly via
response_model. Only inputs and a couple of purpose-built envelopes live
here.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    prompt: str = Field(default="Hello! Briefly introduce yourself.")


class TuneRequest(BaseModel):
    dry_run: bool = False