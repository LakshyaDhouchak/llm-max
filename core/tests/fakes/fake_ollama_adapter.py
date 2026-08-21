"""In-memory fake RuntimeAdapter.

Used by tests for components that depend on a RuntimeAdapter without
needing a real Ollama server running (launcher/, bench/).
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
        run_responses: list[dict] | None = None,
        raise_on_run: Exception | None = None,
        raise_on_call_number: int | None = None,
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
        # If set, returns a different response per call, in order
        # (cycling if there are more calls than responses).
        self._run_responses = run_responses
        # If set, every call to run() raises this exception.
        self._raise_on_run = raise_on_run
        # If set, only the Nth call (1-indexed) raises _raise_on_run;
        # earlier calls return normally. Lets tests simulate "fails
        # partway through a benchmark" rather than "fails immediately".
        self._raise_on_call_number = raise_on_call_number
        self.pulled_models: list[str] = []
        self.run_calls: list[tuple[str, str, dict | None]] = []

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
        call_number = len(self.run_calls)

        if self._raise_on_run is not None:
            if self._raise_on_call_number is None or call_number == self._raise_on_call_number:
                raise self._raise_on_run

        if self._run_responses is not None:
            return self._run_responses[(call_number - 1) % len(self._run_responses)]

        return self._run_response