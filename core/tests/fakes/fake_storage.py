"""Re-exports the canonical InMemoryStorage from llm_max.testing.fakes.
See fake_ollama_adapter.py in this same directory for why."""

from llm_max.testing.fakes.fake_storage import InMemoryStorage

__all__ = ["InMemoryStorage"]