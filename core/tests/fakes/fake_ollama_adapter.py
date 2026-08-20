"""In-memory fake RuntimeAdapter.

Used by tests for components that depend on a RuntimeAdapter (currently
none in Phase 1; will matter once launcher/ orchestrates pull/run/tune)
without needing a real Ollama server running.
"""

from __future__ import annotations

from collections.abc import Iterator

from llm_max.adapters.base import RuntimeAdapter
from llm_max.domain import InstalledModel


class FakeOllamaAdapter(RuntimeAdapter):
    name = "fake-ollama"

    def __init__(
        self,
        available: bool = True,
        installed: list[InstalledModel] | None = None,
        run_response: dict | None = None,
    ):
        self._available = available
        self._installed = installed or []
        self._run_response = run_response or {
            "response": "fake response",
            "total_duration_s": 1.0,
            "tokens_generated": 10,
            "tokens_per_sec": 10.0,
            "raw": {},
        }
        self.pulled_models: list[str] = []
        self.run_calls: list[tuple[str, str]] = []

    def is_available(self) -> bool:
        return self._available

    def list_installed(self) -> list[InstalledModel]:
        return self._installed

    def pull(self, model_id: str) -> Iterator[dict]:
        self.pulled_models.append(model_id)
        yield {"status": "pulling manifest"}
        yield {"status": "success"}
        self._installed.append(InstalledModel(id=model_id))

    def run(self, model_id: str, prompt: str, options: dict | None = None) -> dict:
        self.run_calls.append((model_id, prompt, options))
        return self._run_response