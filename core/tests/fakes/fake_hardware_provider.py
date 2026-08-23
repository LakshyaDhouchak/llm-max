"""Re-exports the canonical FakeGpuProvider/make_gpu from llm_max.testing.fakes.
See fake_ollama_adapter.py in this same directory for why."""

from llm_max.testing.fakes.fake_hardware_provider import FakeGpuProvider, make_gpu

__all__ = ["FakeGpuProvider", "make_gpu"]