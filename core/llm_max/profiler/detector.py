"""Combines system (CPU/RAM) detection and pluggable GpuProviders into a
single HardwareProfile.

`scan_hardware()` accepts an optional list of providers so tests can inject
fakes instead of requiring real GPU hardware/drivers. Production code (the
CLI) calls it with no arguments and gets the default provider set.
"""

from __future__ import annotations

from llm_max.domain import GpuInfo, HardwareProfile
from llm_max.profiler.base import GpuProvider
from llm_max.profiler.nvidia import NvidiaGpuProvider
from llm_max.profiler.system import cpu_counts, cpu_model_name, ram_mb


def default_gpu_providers() -> list[GpuProvider]:
    return [NvidiaGpuProvider()]


def scan_hardware(providers: list[GpuProvider] | None = None) -> HardwareProfile:
    """Run a full hardware scan and return a HardwareProfile.

    Tries each GPU provider in turn (only if `is_available()`), combining
    whatever GPUs they report. A provider raising or reporting unavailable
    never blocks the scan — absence of a vendor's hardware is normal.
    """
    providers = providers if providers is not None else default_gpu_providers()

    gpus: list[GpuInfo] = []
    for provider in providers:
        try:
            if provider.is_available():
                gpus.extend(provider.detect())
        except Exception:
            # A misbehaving provider should never take down the whole scan.
            continue

    physical_cores, logical_cores = cpu_counts()
    total_ram, available_ram = ram_mb()

    return HardwareProfile(
        gpus=gpus,
        cpu_cores_physical=physical_cores,
        cpu_cores_logical=logical_cores,
        cpu_model=cpu_model_name(),
        total_ram_mb=total_ram,
        available_ram_mb=available_ram,
    )