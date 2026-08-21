"""Turns a set of benchmarked candidates into a decision.

Pure functions, no I/O — everything here operates on already-measured
BenchmarkResults. This is where the actual "which config wins" logic
lives, separated from search.py (which candidates to try) and
runner.py (how to measure one).
"""

from __future__ import annotations

from llm_max.autotune.state import TuningCandidateResult

# Autopilot only switches configs when the improvement clears this bar —
# prevents thrashing between configs whose throughput difference is within
# normal run-to-run measurement noise.
DEFAULT_MIN_IMPROVEMENT_PCT = 5.0


def pick_best(
    results: list[TuningCandidateResult],
) -> TuningCandidateResult | None:
    """Pick the best candidate among successful, non-OOM results.

    Ranked by tokens/sec descending, tied-broken by lower p95 latency.
    Returns None if every candidate failed or OOM'd — callers should fall
    back to the baseline in that case, never leave a model unconfigured.
    """
    viable = [
        r
        for r in results
        if r.benchmark.succeeded and not r.benchmark.oom_occurred
    ]
    if not viable:
        return None

    def score(r: TuningCandidateResult) -> tuple[float, float]:
        tokens_per_sec = r.benchmark.tokens_per_sec or 0.0
        p95 = (
            r.benchmark.p95_latency_s
            if r.benchmark.p95_latency_s is not None
            else float("inf")
        )
        return (tokens_per_sec, -p95)

    return max(viable, key=score)


def is_meaningful_improvement(
    candidate: TuningCandidateResult,
    baseline: TuningCandidateResult,
    min_improvement_pct: float = DEFAULT_MIN_IMPROVEMENT_PCT,
) -> bool:
    """Whether `candidate` improves on `baseline` by enough to be worth
    switching to (as opposed to noise-level variation between runs)."""
    if not candidate.benchmark.succeeded or candidate.benchmark.oom_occurred:
        return False

    if not baseline.benchmark.succeeded:
        # Anything that works beats a baseline that's currently broken.
        return True

    baseline_tps = baseline.benchmark.tokens_per_sec or 0.0
    candidate_tps = candidate.benchmark.tokens_per_sec or 0.0

    if baseline_tps <= 0:
        return candidate_tps > 0

    improvement_pct = (candidate_tps - baseline_tps) / baseline_tps * 100
    return improvement_pct >= min_improvement_pct