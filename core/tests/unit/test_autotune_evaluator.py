from llm_max.autotune.evaluator import (
    DEFAULT_MIN_IMPROVEMENT_PCT,
    is_meaningful_improvement,
    pick_best,
)
from llm_max.autotune.state import TuningCandidateResult
from llm_max.bench.metrics import BenchmarkResult


def _candidate(config: dict, tokens_per_sec: float | None, p95: float = 1.0, oom: bool = False, error: str | None = None, completed: int = 3, attempted: int = 3) -> TuningCandidateResult:
    return TuningCandidateResult(
        config=config,
        benchmark=BenchmarkResult(
            config=config,
            tokens_per_sec=tokens_per_sec,
            p95_latency_s=p95,
            oom_occurred=oom,
            error=error,
            samples_completed=completed,
            samples_attempted=attempted,
        ),
    )


def test_pick_best_picks_highest_throughput():
    candidates = [
        _candidate({"num_ctx": 1024}, tokens_per_sec=30.0),
        _candidate({"num_ctx": 2048}, tokens_per_sec=50.0),
        _candidate({"num_ctx": 4096}, tokens_per_sec=20.0),
    ]
    best = pick_best(candidates)
    assert best.config == {"num_ctx": 2048}


def test_pick_best_excludes_oom_candidates():
    candidates = [
        _candidate({"num_ctx": 4096}, tokens_per_sec=100.0, oom=True),
        _candidate({"num_ctx": 2048}, tokens_per_sec=40.0),
    ]
    best = pick_best(candidates)
    assert best.config == {"num_ctx": 2048}


def test_pick_best_excludes_failed_candidates():
    candidates = [
        _candidate({"num_ctx": 4096}, tokens_per_sec=None, error="connection refused", completed=0, attempted=1),
        _candidate({"num_ctx": 2048}, tokens_per_sec=40.0),
    ]
    best = pick_best(candidates)
    assert best.config == {"num_ctx": 2048}


def test_pick_best_returns_none_when_all_fail():
    candidates = [
        _candidate({"num_ctx": 4096}, tokens_per_sec=None, oom=True),
        _candidate({"num_ctx": 2048}, tokens_per_sec=None, error="boom", completed=0, attempted=1),
    ]
    assert pick_best(candidates) is None


def test_pick_best_tiebreaks_on_lower_p95_latency():
    candidates = [
        _candidate({"num_ctx": 1024}, tokens_per_sec=50.0, p95=2.0),
        _candidate({"num_ctx": 2048}, tokens_per_sec=50.0, p95=1.0),
    ]
    best = pick_best(candidates)
    assert best.config == {"num_ctx": 2048}


def test_is_meaningful_improvement_true_above_threshold():
    baseline = _candidate({"num_ctx": 2048}, tokens_per_sec=100.0)
    candidate = _candidate({"num_ctx": 4096}, tokens_per_sec=110.0)
    assert is_meaningful_improvement(candidate, baseline) is True


def test_is_meaningful_improvement_false_below_threshold():
    baseline = _candidate({"num_ctx": 2048}, tokens_per_sec=100.0)
    candidate = _candidate({"num_ctx": 4096}, tokens_per_sec=102.0)
    assert is_meaningful_improvement(candidate, baseline) is False


def test_is_meaningful_improvement_respects_custom_threshold():
    baseline = _candidate({"num_ctx": 2048}, tokens_per_sec=100.0)
    candidate = _candidate({"num_ctx": 4096}, tokens_per_sec=102.0)
    assert is_meaningful_improvement(candidate, baseline, min_improvement_pct=1.0) is True


def test_is_meaningful_improvement_true_when_baseline_broken():
    baseline = _candidate({"num_ctx": 2048}, tokens_per_sec=None, error="boom", completed=0, attempted=1)
    candidate = _candidate({"num_ctx": 4096}, tokens_per_sec=1.0)
    assert is_meaningful_improvement(candidate, baseline) is True


def test_is_meaningful_improvement_false_when_candidate_ooms():
    baseline = _candidate({"num_ctx": 2048}, tokens_per_sec=50.0)
    candidate = _candidate({"num_ctx": 4096}, tokens_per_sec=200.0, oom=True)
    assert is_meaningful_improvement(candidate, baseline) is False


def test_default_threshold_is_five_percent():
    assert DEFAULT_MIN_IMPROVEMENT_PCT == 5.0