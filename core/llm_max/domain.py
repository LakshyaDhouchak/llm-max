"""Shared data models (pydantic) used across the profiler, catalog, and CLI."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class GpuInfo(BaseModel):
    index: int
    name: str
    total_vram_mb: int
    free_vram_mb: int
    used_vram_mb: int
    compute_capability: Optional[str] = None
    utilization_pct: Optional[int] = None
    temperature_c: Optional[int] = None


class HardwareProfile(BaseModel):
    gpus: list[GpuInfo] = Field(default_factory=list)
    cpu_cores_physical: int
    cpu_cores_logical: int
    cpu_model: Optional[str] = None
    total_ram_mb: int
    available_ram_mb: int

    @property
    def has_gpu(self) -> bool:
        return len(self.gpus) > 0

    @property
    def total_vram_mb(self) -> int:
        return sum(g.total_vram_mb for g in self.gpus)


class CompatibilityTier(str, Enum):
    GREAT_FIT = "great_fit"
    WILL_RUN = "will_run"
    MAY_BE_SLOW = "may_be_slow"
    NOT_RECOMMENDED = "not_recommended"


class ModelSpec(BaseModel):
    """A single entry from the curated model catalog."""

    id: str  # e.g. "llama3:8b" — matches the Ollama tag where possible
    display_name: str
    family: str
    param_size_b: float  # billions of parameters
    quantizations: list[str] = Field(default_factory=lambda: ["Q4_K_M"])
    min_vram_mb: int
    recommended_vram_mb: int
    min_ram_mb: int
    notes: Optional[str] = None


class ModelCompatibility(BaseModel):
    model: ModelSpec
    tier: CompatibilityTier
    reason: str


class InstalledModel(BaseModel):
    """A model already pulled/available in the runtime (e.g. Ollama)."""

    id: str
    size_mb: Optional[int] = None
    digest: Optional[str] = None


class RunRecord(BaseModel):
    """A single `llm-max run` execution, persisted for local history."""

    id: Optional[int] = None  # set by storage on insert
    model_id: str
    runtime: str = "ollama"
    prompt: str
    tokens_generated: int
    total_duration_s: float
    tokens_per_sec: Optional[float] = None
    created_at: Optional[str] = None  # ISO 8601, set by storage on insert


class TunedConfig(BaseModel):
    """A saved/locked runtime configuration for a model on this host."""

    id: Optional[int] = None
    model_id: str
    runtime: str = "ollama"
    config: dict  # e.g. {"num_ctx": 4096, "num_batch": 512}
    is_locked: bool = False
    created_at: Optional[str] = None


class AutopilotEvent(BaseModel):
    """An audit-trail entry for an autotune decision — every adjust,
    rollback, lock, enable, or disable gets one. This is what makes
    autopilot's behavior inspectable after the fact rather than a black
    box, and what `llm-max autopilot status` reads from."""

    id: Optional[int] = None
    model_id: str
    event_type: str  # "adjust" | "rollback" | "lock" | "enable" | "disable"
    details: dict = Field(default_factory=dict)
    created_at: Optional[str] = None