"""Common interface all runtime adapters (Ollama, vLLM, llama.cpp) implement.

Keeping this abstract now, even with only one adapter, is what lets us add
vLLM/llama.cpp later without touching CLI or catalog code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from llm_max.domain import InstalledModel


class RuntimeAdapter(ABC):
    name: str

    @abstractmethod
    def is_available(self) -> bool:
        """Whether this runtime is installed/reachable on this machine."""

    @abstractmethod
    def list_installed(self) -> list[InstalledModel]:
        """List models already pulled/available in this runtime."""

    @abstractmethod
    def pull(self, model_id: str) -> Iterator[dict]:
        """Pull/download a model. Yields progress events."""

    @abstractmethod
    def run(self, model_id: str, prompt: str, options: dict | None = None) -> dict:
        """Run a single prompt against the model. Returns response + timing info."""