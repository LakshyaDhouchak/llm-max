"""OS-level CPU and RAM detection.

Unlike GPUs, CPU/RAM aren't vendor-pluggable — every machine has exactly one
of each, detected the same way via psutil. Kept separate from GpuProvider
implementations because it's not part of that abstraction.
"""

from __future__ import annotations

import platform

import psutil

_MB = 1024 * 1024


def cpu_model_name() -> str | None:
    try:
        if platform.system() == "Linux":
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.lower().startswith("model name"):
                        return line.split(":", 1)[1].strip()
        return platform.processor() or None
    except Exception:
        return None


def cpu_counts() -> tuple[int, int]:
    """Returns (physical_cores, logical_cores)."""
    return (
        psutil.cpu_count(logical=False) or 1,
        psutil.cpu_count(logical=True) or 1,
    )


def ram_mb() -> tuple[int, int]:
    """Returns (total_ram_mb, available_ram_mb)."""
    vmem = psutil.virtual_memory()
    return vmem.total // _MB, vmem.available // _MB