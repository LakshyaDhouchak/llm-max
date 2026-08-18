"""NVIDIA GPU detection via pynvml (NVML bindings)."""

from __future__ import annotations

from llm_max.domain import GpuInfo
from llm_max.profiler.base import GpuProvider

_MB = 1024 * 1024


class NvidiaGpuProvider(GpuProvider):
    vendor = "nvidia"

    def is_available(self) -> bool:
        try:
            import pynvml

            pynvml.nvmlInit()
            pynvml.nvmlShutdown()
            return True
        except Exception:
            return False

    def detect(self) -> list[GpuInfo]:
        try:
            import pynvml
        except ImportError:
            return []

        gpus: list[GpuInfo] = []
        try:
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()

            for i in range(device_count):
                gpus.append(self._read_device(pynvml, i))

            pynvml.nvmlShutdown()
        except Exception:
            # Driver not installed, no NVIDIA card, permissions issue, etc.
            # Treat as "no GPU detected" rather than crashing the scan.
            return []

        return gpus

    @staticmethod
    def _read_device(pynvml, index: int) -> GpuInfo:
        handle = pynvml.nvmlDeviceGetHandleByIndex(index)
        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode("utf-8")

        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)

        compute_cap = None
        try:
            major, minor = pynvml.nvmlDeviceGetCudaComputeCapability(handle)
            compute_cap = f"{major}.{minor}"
        except Exception:
            pass

        util_pct = None
        try:
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            util_pct = util.gpu
        except Exception:
            pass

        temp_c = None
        try:
            temp_c = pynvml.nvmlDeviceGetTemperature(
                handle, pynvml.NVML_TEMPERATURE_GPU
            )
        except Exception:
            pass

        return GpuInfo(
            index=index,
            name=name,
            total_vram_mb=mem.total // _MB,
            free_vram_mb=mem.free // _MB,
            used_vram_mb=mem.used // _MB,
            compute_capability=compute_cap,
            utilization_pct=util_pct,
            temperature_c=temp_c,
        )