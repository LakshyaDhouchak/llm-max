"""Controllable fake GpuProvider for tests.

Lets tests exercise detector.scan_hardware() with any GPU scenario (no GPU,
one GPU, multiple GPUs, a provider that raises) without touching pynvml or
real hardware.
"""

from __future__ import annotations

from llm_max.domain import GpuInfo
from llm_max.profiler.base import GpuProvider


class FakeGpuProvider(GpuProvider):
    vendor = "fake"

    def __init__(
        self,
        gpus: list[GpuInfo] | None = None,
        available: bool = True,
        raise_on_detect: bool = False,
    ):
        self._gpus = gpus or []
        self._available = available
        self._raise_on_detect = raise_on_detect

    def is_available(self) -> bool:
        return self._available

    def detect(self) -> list[GpuInfo]:
        if self._raise_on_detect:
            raise RuntimeError("simulated provider failure")
        return self._gpus


def make_gpu(
    index: int = 0,
    name: str = "Fake GPU",
    free_vram_mb: int = 8000,
    total_vram_mb: int | None = None,
) -> GpuInfo:
    """Convenience constructor for a single fake GpuInfo."""
    return GpuInfo(
        index=index,
        name=name,
        total_vram_mb=total_vram_mb or free_vram_mb,
        free_vram_mb=free_vram_mb,
        used_vram_mb=(total_vram_mb or free_vram_mb) - free_vram_mb,
    )