"""Result types shared across the tuning loop (search -> bench -> evaluator
-> rollback -> engine).

Kept separate from llm_max.domain because these are Phase 3-internal,
ephemeral concepts (a tuning session's results) rather than persisted
entities — only the winning config gets saved as a TunedConfig; the full
TuningSession (baseline + every candidate benchmarked) is shown to the
user and then discarded, not stored.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from llm_max.bench.metrics import BenchmarkResult


class TuningCandidateResult(BaseModel):
    """One config paired with its benchmark outcome."""

    config: dict
    benchmark: BenchmarkResult


class TuningOutcome(str, Enum):
    ACCEPTED_NEW = "accepted_new"
    KEPT_BASELINE = "kept_baseline"
    ROLLED_BACK = "rolled_back"
    LOCKED = "locked"


class TuningSession(BaseModel):
    model_id: str
    baseline: TuningCandidateResult
    candidates: list[TuningCandidateResult]
    winner: TuningCandidateResult
    outcome: TuningOutcome
    reason: str