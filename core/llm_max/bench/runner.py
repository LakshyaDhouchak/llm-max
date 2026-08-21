"""Runs the fixed benchmark prompt set against a model with a given config,
producing a BenchmarkResult.

Pure measurement — no tuning decisions here (that's autotune/evaluator.py's
job once it exists). Fails fast: the first error/OOM stops the run and
returns a partial result rather than continuing with a config that already
demonstrated it doesn't work.
"""

from __future__ import annotations

from llm_max.adapters.base import RuntimeAdapter
from llm_max.bench.metrics import BenchmarkResult, percentile
from llm_max.bench.prompts import BENCHMARK_PROMPTS

# Substrings checked (case-insensitive) in an exception message to classify
# a failure as an out-of-memory condition rather than some other error.
# Heuristic, not exhaustive — different runtimes/drivers phrase OOM errors
# differently, so this may need vendor-specific entries as more adapters
# (vLLM, llama.cpp) are added.
_OOM_KEYWORDS = ("out of memory", "cuda", "oom", "failed to allocate")


def run_benchmark(
    adapter: RuntimeAdapter, model_id: str, options: dict | None = None
) -> BenchmarkResult:
    """Run BENCHMARK_PROMPTS against model_id with the given runtime
    options, returning aggregate throughput/latency or failure details."""
    config = options or {}
    latencies: list[float] = []
    tokens_per_sec_samples: list[float] = []
    attempted = 0

    for prompt in BENCHMARK_PROMPTS:
        attempted += 1
        try:
            result = adapter.run(model_id, prompt, options=options)
        except Exception as exc:
            message = str(exc).lower()
            is_oom = any(keyword in message for keyword in _OOM_KEYWORDS)
            return BenchmarkResult(
                config=config,
                oom_occurred=is_oom,
                error=str(exc),
                samples_completed=len(latencies),
                samples_attempted=attempted,
            )

        latencies.append(result["total_duration_s"])
        if result.get("tokens_per_sec"):
            tokens_per_sec_samples.append(result["tokens_per_sec"])

    return BenchmarkResult(
        config=config,
        tokens_per_sec=(
            sum(tokens_per_sec_samples) / len(tokens_per_sec_samples)
            if tokens_per_sec_samples
            else None
        ),
        p50_latency_s=percentile(latencies, 50),
        p95_latency_s=percentile(latencies, 95),
        samples_completed=len(latencies),
        samples_attempted=attempted,
    )