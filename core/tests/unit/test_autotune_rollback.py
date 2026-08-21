from llm_max.autotune.rollback import needs_rollback, rollback_target
from llm_max.autotune.state import TuningCandidateResult
from llm_max.bench.metrics import BenchmarkResult


def _result(config: dict, succeeded: bool = True, oom: bool = False) -> TuningCandidateResult:
    return TuningCandidateResult(
        config=config,
        benchmark=BenchmarkResult(
            config=config,
            tokens_per_sec=50.0 if succeeded else None,
            oom_occurred=oom,
            error=None if succeeded else "boom",
            samples_completed=3 if succeeded else 0,
            samples_attempted=3,
        ),
    )


def test_needs_rollback_true_on_oom():
    active = _result({"num_ctx": 4096}, succeeded=True, oom=True)
    assert needs_rollback(active) is True


def test_needs_rollback_true_on_failure():
    active = _result({"num_ctx": 4096}, succeeded=False)
    assert needs_rollback(active) is True


def test_needs_rollback_false_when_healthy():
    active = _result({"num_ctx": 2048}, succeeded=True)
    assert needs_rollback(active) is False


def test_rollback_target_finds_most_recent_good_config():
    current = _result({"num_ctx": 4096}, succeeded=True, oom=True)
    history = [
        _result({"num_ctx": 1024}, succeeded=True),
        _result({"num_ctx": 2048}, succeeded=True),
        current,
    ]
    target = rollback_target(current, history)
    assert target == {"num_ctx": 2048}


def test_rollback_target_skips_current_config_in_history():
    current = _result({"num_ctx": 4096}, succeeded=True, oom=True)
    history = [
        _result({"num_ctx": 2048}, succeeded=True),
        _result({"num_ctx": 4096}, succeeded=True, oom=True),
        current,
    ]
    target = rollback_target(current, history)
    assert target == {"num_ctx": 2048}


def test_rollback_target_returns_none_when_no_good_history():
    current = _result({"num_ctx": 4096}, succeeded=True, oom=True)
    history = [
        _result({"num_ctx": 2048}, succeeded=False),
        current,
    ]
    assert rollback_target(current, history) is None


def test_rollback_target_returns_none_on_empty_history():
    current = _result({"num_ctx": 4096}, succeeded=True, oom=True)
    assert rollback_target(current, []) is None