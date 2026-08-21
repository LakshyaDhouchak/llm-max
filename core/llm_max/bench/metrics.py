"""BenchmarkResult and the small stats helper used to compute it.

Pure data + pure functions — no I/O, no adapter calls. runner.py is the
only module that produces a BenchmarkResult; this module just defines its
shape and how percentiles are computed from raw latency samples.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class BenchmarkResult(BaseModel):
    config: dict
    tokens_per_sec: Optional[float] = None
    p50_latency_s: Optional[float] = None
    p95_latency_s: Optional[float] = None
    oom_occurred: bool = False
    error: Optional[str] = None
    samples_completed: int = 0
    samples_attempted: int = 0

    @property
    def succeeded(self) -> bool:
        return self.error is None and self.samples_completed == self.samples_attempted


def percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile. Fine for small sample counts (3-5 prompts);
    not meant to be statistically rigorous — just consistent run-to-run."""
    if not values:
        raise ValueError("cannot compute percentile of an empty list")
    sorted_vals = sorted(values)
    index = round(pct / 100 * (len(sorted_vals) - 1))
    index = max(0, min(len(sorted_vals) - 1, index))
    return sorted_vals[index]