"""Shared test fixtures — mock hardware profiles, reused across unit tests."""

from __future__ import annotations

from llm_max.domain import GpuInfo, HardwareProfile


def gpu_hardware_profile(
    free_vram_mb: int, total_vram_mb: int | None = None
) -> HardwareProfile:
    """A HardwareProfile with a single mock GPU."""
    return HardwareProfile(
        gpus=[
            GpuInfo(
                index=0,
                name="Test GPU",
                total_vram_mb=total_vram_mb or free_vram_mb,
                free_vram_mb=free_vram_mb,
                used_vram_mb=0,
            )
        ],
        cpu_cores_physical=4,
        cpu_cores_logical=8,
        total_ram_mb=16000,
        available_ram_mb=12000,
    )


def cpu_only_hardware_profile(available_ram_mb: int) -> HardwareProfile:
    """A HardwareProfile with no GPU (CPU-only machine)."""
    return HardwareProfile(
        gpus=[],
        cpu_cores_physical=4,
        cpu_cores_logical=8,
        total_ram_mb=available_ram_mb + 2000,
        available_ram_mb=available_ram_mb,
    )