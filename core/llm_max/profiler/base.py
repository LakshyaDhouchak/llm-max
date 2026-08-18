"""Abstraction for GPU detection backends.

One provider per vendor (NVIDIA now; Apple Silicon/AMD ROCm later).
detector.py tries each registered provider and combines whatever GPUs they
find. This is what lets tests inject a FakeGpuProvider instead of requiring
real hardware, and what lets a future multi-vendor machine (e.g. an NVIDIA
eGPU on Apple Silicon) report GPUs from more than one provider at once.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from llm_max.domain import GpuInfo


class GpuProvider(ABC):
    """One vendor's GPU detection backend."""

    vendor: str

    @abstractmethod
    def is_available(self) -> bool:
        """Whether this vendor's tooling/drivers are present on this machine.

        Must never raise — absence of a vendor's hardware/drivers is a
        normal, expected case, not an error condition.
        """

    @abstractmethod
    def detect(self) -> list[GpuInfo]:
        """Detect this vendor's GPUs. Returns [] if none found or on error.

        Implementations should catch their own vendor-specific exceptions
        (missing driver, permissions, etc.) and return [] rather than raise,
        so one broken provider never crashes the whole hardware scan.
        """