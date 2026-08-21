from llm_max.bench.prompts import BENCHMARK_PROMPTS
from llm_max.bench.runner import run_benchmark
from tests.fakes.fake_ollama_adapter import FakeOllamaAdapter


def test_successful_benchmark_returns_aggregated_metrics():
    adapter = FakeOllamaAdapter(
        run_response={
            "response": "ok",
            "total_duration_s": 2.0,
            "tokens_generated": 20,
            "tokens_per_sec": 10.0,
            "raw": {},
        }
    )

    result = run_benchmark(adapter, "model:1b", options={"num_ctx": 2048})

    assert result.succeeded is True
    assert result.samples_completed == len(BENCHMARK_PROMPTS)
    assert result.samples_attempted == len(BENCHMARK_PROMPTS)
    assert result.tokens_per_sec == 10.0
    assert result.p50_latency_s == 2.0
    assert result.p95_latency_s == 2.0
    assert result.oom_occurred is False
    assert result.config == {"num_ctx": 2048}


def test_benchmark_uses_all_fixed_prompts():
    adapter = FakeOllamaAdapter()
    run_benchmark(adapter, "model:1b")

    prompts_used = [call[1] for call in adapter.run_calls]
    assert prompts_used == BENCHMARK_PROMPTS


def test_oom_error_classified_correctly():
    adapter = FakeOllamaAdapter(
        raise_on_run=RuntimeError("CUDA error: out of memory")
    )

    result = run_benchmark(adapter, "model:70b")

    assert result.succeeded is False
    assert result.oom_occurred is True
    assert "out of memory" in result.error.lower()


def test_non_oom_error_not_classified_as_oom():
    adapter = FakeOllamaAdapter(
        raise_on_run=ConnectionError("connection refused")
    )

    result = run_benchmark(adapter, "model:1b")

    assert result.succeeded is False
    assert result.oom_occurred is False
    assert result.error is not None


def test_failure_partway_through_stops_early_with_partial_samples():
    adapter = FakeOllamaAdapter(
        raise_on_run=RuntimeError("out of memory"),
        raise_on_call_number=2,  # first prompt succeeds, second fails
    )

    result = run_benchmark(adapter, "model:1b")

    assert result.samples_completed == 1
    assert result.samples_attempted == 2
    assert len(adapter.run_calls) == 2


def test_none_tokens_per_sec_excluded_from_average():
    adapter = FakeOllamaAdapter(
        run_response={
            "response": "ok",
            "total_duration_s": 1.0,
            "tokens_generated": 0,
            "tokens_per_sec": None,
            "raw": {},
        }
    )

    result = run_benchmark(adapter, "model:1b")

    assert result.tokens_per_sec is None
    assert result.p50_latency_s == 1.0