import pytest

from llm_max.autotune.engine import RuntimeUnavailableError, TuningEngine
from llm_max.autotune.state import TuningOutcome
from llm_max.domain import TunedConfig
from tests.fakes.fake_ollama_adapter import FakeOllamaAdapter
from tests.fakes.fake_storage import InMemoryStorage


def _response(tokens_per_sec: float, duration: float = 1.0) -> dict:
    return {
        "response": "ok",
        "total_duration_s": duration,
        "tokens_generated": int(tokens_per_sec * duration),
        "tokens_per_sec": tokens_per_sec,
        "raw": {},
    }


def test_tune_once_raises_when_adapter_unavailable():
    adapter = FakeOllamaAdapter(available=False)
    engine = TuningEngine(adapter=adapter, storage=InMemoryStorage())

    with pytest.raises(RuntimeUnavailableError):
        engine.tune_once("model:1b")


def test_tune_once_keeps_baseline_when_flat():
    adapter = FakeOllamaAdapter(run_response=_response(50.0))
    engine = TuningEngine(adapter=adapter, storage=InMemoryStorage())

    session = engine.tune_once("model:1b", baseline_config={"num_ctx": 2048})

    assert session.outcome == TuningOutcome.KEPT_BASELINE
    assert session.winner.config == {"num_ctx": 2048}


def test_tune_once_accepts_better_candidate():
    class VariableAdapter(FakeOllamaAdapter):
        def run(self, model_id, prompt, options=None):
            ctx = (options or {}).get("num_ctx")
            tps = 100.0 if ctx == 4096 else 50.0
            self.run_calls.append((model_id, prompt, options))
            return _response(tps)

    adapter = VariableAdapter()
    engine = TuningEngine(adapter=adapter, storage=InMemoryStorage())

    session = engine.tune_once("model:1b", baseline_config={"num_ctx": 2048})

    assert session.outcome == TuningOutcome.ACCEPTED_NEW
    assert session.winner.config == {"num_ctx": 4096}


def test_tune_once_keeps_baseline_when_all_candidates_oom():
    adapter = FakeOllamaAdapter(raise_on_run=RuntimeError("CUDA out of memory"))
    engine = TuningEngine(adapter=adapter, storage=InMemoryStorage())

    session = engine.tune_once("model:1b", baseline_config={"num_ctx": 2048})

    assert session.outcome == TuningOutcome.KEPT_BASELINE
    assert "failed" in session.reason or "memory" in session.reason


def test_apply_saves_winner_to_storage():
    adapter = FakeOllamaAdapter(run_response=_response(50.0))
    storage = InMemoryStorage()
    engine = TuningEngine(adapter=adapter, storage=storage)

    session = engine.tune_once("model:1b", baseline_config={"num_ctx": 2048})
    saved = engine.apply(session)

    assert saved.model_id == "model:1b"
    assert storage.get_tuned_config("model:1b") is not None


def test_apply_logs_adjust_event():
    adapter = FakeOllamaAdapter(run_response=_response(50.0))
    storage = InMemoryStorage()
    engine = TuningEngine(adapter=adapter, storage=storage)

    session = engine.tune_once("model:1b", baseline_config={"num_ctx": 2048})
    engine.apply(session)

    events = storage.list_autopilot_events(model_id="model:1b")
    assert len(events) == 1
    assert events[0].event_type == "adjust"


def test_autopilot_loop_stops_after_max_iterations():
    adapter = FakeOllamaAdapter(run_response=_response(50.0))
    engine = TuningEngine(adapter=adapter, storage=InMemoryStorage())

    sleeps = []
    sessions = list(
        engine.autopilot_loop(
            "model:1b",
            max_iterations=3,
            sleep_fn=lambda s: sleeps.append(s),
        )
    )

    assert len(sessions) == 3
    assert len(sleeps) == 2


def test_autopilot_loop_stops_when_locked():
    storage = InMemoryStorage()
    storage.save_tuned_config(TunedConfig(model_id="model:1b", config={"num_ctx": 2048}))
    storage.lock_config("model:1b")

    adapter = FakeOllamaAdapter(run_response=_response(50.0))
    engine = TuningEngine(adapter=adapter, storage=storage)

    sessions = list(engine.autopilot_loop("model:1b", max_iterations=5, sleep_fn=lambda s: None))

    assert len(sessions) == 1
    assert sessions[0].outcome == TuningOutcome.LOCKED


def test_autopilot_loop_rolls_back_using_seeded_history():
    """The realistic rollback scenario: a previously-saved config (4096)
    starts failing (e.g. another process took VRAM). Seeded history
    provides a known-good alternative (2048) to revert to — this is the
    same shape autopilot builds up naturally over real iterations, seeded
    directly here for a deterministic, non-brittle test."""
    storage = InMemoryStorage()
    storage.save_tuned_config(TunedConfig(model_id="model:1b", config={"num_ctx": 4096}))

    adapter = FakeOllamaAdapter(raise_on_run=RuntimeError("CUDA out of memory"))
    engine = TuningEngine(adapter=adapter, storage=storage)

    from llm_max.autotune.state import TuningCandidateResult
    from llm_max.bench.metrics import BenchmarkResult

    good_history = [
        TuningCandidateResult(
            config={"num_ctx": 2048},
            benchmark=BenchmarkResult(
                config={"num_ctx": 2048},
                tokens_per_sec=50.0,
                samples_completed=3,
                samples_attempted=3,
            ),
        ),
    ]

    session = next(
        engine.autopilot_loop(
            "model:1b",
            max_iterations=1,
            sleep_fn=lambda s: None,
            initial_history=good_history,
        )
    )

    assert session.outcome == TuningOutcome.ROLLED_BACK
    assert session.winner.config == {"num_ctx": 2048}
    assert storage.get_tuned_config("model:1b").config == {"num_ctx": 2048}


def test_rollback_logs_event():
    storage = InMemoryStorage()
    storage.save_tuned_config(TunedConfig(model_id="model:1b", config={"num_ctx": 4096}))
    adapter = FakeOllamaAdapter(raise_on_run=RuntimeError("CUDA out of memory"))
    engine = TuningEngine(adapter=adapter, storage=storage)

    from llm_max.autotune.state import TuningCandidateResult
    from llm_max.bench.metrics import BenchmarkResult

    good_history = [
        TuningCandidateResult(
            config={"num_ctx": 2048},
            benchmark=BenchmarkResult(config={"num_ctx": 2048}, tokens_per_sec=50.0, samples_completed=3, samples_attempted=3),
        ),
    ]

    next(engine.autopilot_loop("model:1b", max_iterations=1, sleep_fn=lambda s: None, initial_history=good_history))

    events = storage.list_autopilot_events(model_id="model:1b")
    assert len(events) == 1
    assert events[0].event_type == "rollback"


def test_locked_config_logs_event():
    storage = InMemoryStorage()
    storage.save_tuned_config(TunedConfig(model_id="model:1b", config={"num_ctx": 2048}))
    storage.lock_config("model:1b")

    adapter = FakeOllamaAdapter(run_response=_response(50.0))
    engine = TuningEngine(adapter=adapter, storage=storage)

    list(engine.autopilot_loop("model:1b", max_iterations=5, sleep_fn=lambda s: None))

    events = storage.list_autopilot_events(model_id="model:1b")
    assert len(events) == 1
    assert events[0].event_type == "lock"


def test_rate_limit_blocks_adjustment_after_cap_reached():
    """With max_adjustments_per_day=1, the first genuinely-better config
    gets applied; a second one shortly after (same simulated day) should
    be blocked, not applied."""

    class AlternatingAdapter(FakeOllamaAdapter):
        """First iteration: 4096 wins. Second iteration (baseline now
        4096): make 8192 look even better, to try to trigger a second
        adjustment within the same rate-limit window."""

        def run(self, model_id, prompt, options=None):
            ctx = (options or {}).get("num_ctx")
            tps = {1024: 40.0, 2048: 50.0, 4096: 100.0, 8192: 200.0}.get(ctx, 50.0)
            self.run_calls.append((model_id, prompt, options))
            return _response(tps)

    storage = InMemoryStorage()
    adapter = AlternatingAdapter()
    engine = TuningEngine(adapter=adapter, storage=storage)

    fake_now = {"t": 1000.0}
    sessions = list(
        engine.autopilot_loop(
            "model:1b",
            max_iterations=2,
            sleep_fn=lambda s: None,
            max_adjustments_per_day=1,
            now_fn=lambda: fake_now["t"],
        )
    )

    assert sessions[0].outcome == TuningOutcome.ACCEPTED_NEW
    assert sessions[0].winner.config == {"num_ctx": 4096}

    assert sessions[1].outcome == TuningOutcome.RATE_LIMITED
    assert storage.get_tuned_config("model:1b").config == {"num_ctx": 4096}


def test_rate_limit_resets_after_24_hours():
    class AlternatingAdapter(FakeOllamaAdapter):
        def run(self, model_id, prompt, options=None):
            ctx = (options or {}).get("num_ctx")
            tps = {1024: 40.0, 2048: 50.0, 4096: 100.0, 8192: 200.0}.get(ctx, 50.0)
            self.run_calls.append((model_id, prompt, options))
            return _response(tps)

    storage = InMemoryStorage()
    adapter = AlternatingAdapter()
    engine = TuningEngine(adapter=adapter, storage=storage)

    fake_now = {"t": 1000.0}

    def advancing_sleep(seconds):
        fake_now["t"] += 90000  # jump forward >24h between iterations

    sessions = list(
        engine.autopilot_loop(
            "model:1b",
            max_iterations=2,
            sleep_fn=advancing_sleep,
            max_adjustments_per_day=1,
            now_fn=lambda: fake_now["t"],
        )
    )

    assert sessions[0].outcome == TuningOutcome.ACCEPTED_NEW
    assert sessions[1].outcome == TuningOutcome.ACCEPTED_NEW
    assert sessions[1].winner.config == {"num_ctx": 8192}


def test_rate_limit_disabled_when_none():
    class AlternatingAdapter(FakeOllamaAdapter):
        def run(self, model_id, prompt, options=None):
            ctx = (options or {}).get("num_ctx")
            tps = {1024: 40.0, 2048: 50.0, 4096: 100.0, 8192: 200.0}.get(ctx, 50.0)
            self.run_calls.append((model_id, prompt, options))
            return _response(tps)

    storage = InMemoryStorage()
    adapter = AlternatingAdapter()
    engine = TuningEngine(adapter=adapter, storage=storage)

    sessions = list(
        engine.autopilot_loop(
            "model:1b",
            max_iterations=2,
            sleep_fn=lambda s: None,
            max_adjustments_per_day=None,
        )
    )

    assert sessions[0].outcome == TuningOutcome.ACCEPTED_NEW
    assert sessions[1].outcome == TuningOutcome.ACCEPTED_NEW