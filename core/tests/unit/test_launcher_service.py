import pytest

from llm_max.domain import ModelSpec
from llm_max.launcher.service import LauncherService, RuntimeUnavailableError
from tests.fakes.fake_hardware_provider import FakeGpuProvider, make_gpu
from tests.fakes.fake_ollama_adapter import FakeOllamaAdapter
from tests.fakes.fake_storage import InMemoryStorage


def _hardware_provider_with_gpu(free_vram_mb: int):
    from llm_max.profiler.detector import scan_hardware

    def provider():
        return scan_hardware(providers=[FakeGpuProvider(gpus=[make_gpu(free_vram_mb=free_vram_mb)])])

    return provider


def test_run_raises_when_adapter_unavailable():
    adapter = FakeOllamaAdapter(available=False)
    service = LauncherService(adapter=adapter, storage=InMemoryStorage())

    with pytest.raises(RuntimeUnavailableError):
        service.run("model:1b", "hello")


def test_run_saves_result_to_storage():
    adapter = FakeOllamaAdapter()
    storage = InMemoryStorage()
    service = LauncherService(adapter=adapter, storage=storage)

    result = service.run("model:1b", "hello")

    assert result["response"] == "fake response"
    assert len(storage.saved_runs) == 1
    assert storage.saved_runs[0].model_id == "model:1b"
    assert result["run_record"].id == 1


def test_run_without_model_spec_passes_no_options():
    adapter = FakeOllamaAdapter()
    service = LauncherService(adapter=adapter, storage=InMemoryStorage())

    service.run("model:1b", "hello")

    assert adapter.run_calls == [("model:1b", "hello", None)]


def test_run_with_model_spec_tunes_options_to_hardware():
    model = ModelSpec(
        id="model:7b", display_name="7B", family="x", param_size_b=7,
        min_vram_mb=5000, recommended_vram_mb=8000, min_ram_mb=10000,
    )
    adapter = FakeOllamaAdapter()
    service = LauncherService(
        adapter=adapter,
        storage=InMemoryStorage(),
        hardware_provider=_hardware_provider_with_gpu(free_vram_mb=6000),
    )

    service.run("model:7b", "hello", model_spec=model)

    assert adapter.run_calls == [("model:7b", "hello", {"num_ctx": 2048})]


def test_pull_raises_when_adapter_unavailable():
    adapter = FakeOllamaAdapter(available=False)
    service = LauncherService(adapter=adapter, storage=InMemoryStorage())

    with pytest.raises(RuntimeUnavailableError):
        list(service.pull("model:1b"))


def test_pull_delegates_to_adapter():
    adapter = FakeOllamaAdapter()
    service = LauncherService(adapter=adapter, storage=InMemoryStorage())

    events = list(service.pull("model:1b"))

    assert adapter.pulled_models == ["model:1b"]
    assert events[-1]["status"] == "success"