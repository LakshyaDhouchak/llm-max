"""Orchestrates pull/run: coordinates a RuntimeAdapter, config_builder, and
Storage so the CLI (and later, agentd) don't duplicate this logic.

Before this existed, cli.py talked to OllamaAdapter and SqliteStore/
MySqlStore directly — fine for two commands, but it meant every future
caller (agentd's HTTP routes, a future `tune` command) would have had to
re-implement "run, then save the result" and "look up hardware-tuned
options" themselves. LauncherService is that logic, written once.
"""

from __future__ import annotations

from collections.abc import Iterator

from llm_max.adapters.base import RuntimeAdapter
from llm_max.domain import HardwareProfile, ModelSpec, RunRecord
from llm_max.launcher.config_builder import build_run_config
from llm_max.storage.base import Storage


class RuntimeUnavailableError(RuntimeError):
    """Raised when the configured runtime (e.g. Ollama) isn't reachable."""


class LauncherService:
    def __init__(
        self,
        adapter: RuntimeAdapter,
        storage: Storage,
        hardware_provider=None,
    ):
        self.adapter = adapter
        self.storage = storage
        # Injectable for tests; defaults to the real scan_hardware() lazily
        # so importing this module never triggers a hardware scan.
        self._hardware_provider = hardware_provider

    def _scan(self) -> HardwareProfile:
        if self._hardware_provider is not None:
            return self._hardware_provider()
        from llm_max.profiler import scan_hardware

        return scan_hardware()

    def pull(self, model_id: str) -> Iterator[dict]:
        """Pull a model, yielding progress events. Raises
        RuntimeUnavailableError if the runtime isn't reachable."""
        if not self.adapter.is_available():
            raise RuntimeUnavailableError(
                f"{self.adapter.name} runtime is not available"
            )
        yield from self.adapter.pull(model_id)

    def run(
        self, model_id: str, prompt: str, model_spec: ModelSpec | None = None
    ) -> dict:
        """Run a prompt, tuning options to hardware if a ModelSpec is given,
        and persist the result. Returns the adapter's result dict plus the
        saved RunRecord under 'run_record'.

        Raises RuntimeUnavailableError if the runtime isn't reachable.
        """
        if not self.adapter.is_available():
            raise RuntimeUnavailableError(
                f"{self.adapter.name} runtime is not available"
            )

        options = None
        if model_spec is not None:
            hw = self._scan()
            built = build_run_config(model_spec, hw)
            options = built or None

        result = self.adapter.run(model_id, prompt, options=options)

        record = self.storage.save_run(
            RunRecord(
                model_id=model_id,
                runtime=self.adapter.name,
                prompt=prompt,
                tokens_generated=result["tokens_generated"],
                total_duration_s=result["total_duration_s"],
                tokens_per_sec=result["tokens_per_sec"],
            )
        )

        return {**result, "run_record": record}