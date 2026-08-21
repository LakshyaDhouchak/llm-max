import pytest

from llm_max.bench.metrics import BenchmarkResult, percentile


def test_percentile_p50_of_odd_count():
    assert percentile([1.0, 2.0, 3.0], 50) == 2.0


def test_percentile_p95_of_small_sample():
    result = percentile([1.0, 2.0, 3.0, 4.0, 5.0], 95)
    assert result in [1.0, 2.0, 3.0, 4.0, 5.0]


def test_percentile_single_value():
    assert percentile([7.5], 50) == 7.5
    assert percentile([7.5], 95) == 7.5


def test_percentile_empty_raises():
    with pytest.raises(ValueError):
        percentile([], 50)


def test_benchmark_result_succeeded_true_on_full_completion():
    result = BenchmarkResult(
        config={}, tokens_per_sec=50.0, p50_latency_s=1.0, p95_latency_s=1.5,
        samples_completed=3, samples_attempted=3,
    )
    assert result.succeeded is True


def test_benchmark_result_succeeded_false_on_error():
    result = BenchmarkResult(
        config={}, error="boom", samples_completed=1, samples_attempted=2,
    )
    assert result.succeeded is False