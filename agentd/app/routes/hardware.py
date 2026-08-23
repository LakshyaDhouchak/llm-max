from __future__ import annotations

from fastapi import APIRouter

from llm_max.compatibility import classify_all
from llm_max.domain import HardwareProfile, ModelCompatibility
from llm_max.profiler import scan_hardware

router = APIRouter(tags=["hardware"])


@router.get("/hardware/scan", response_model=HardwareProfile)
def scan() -> HardwareProfile:
    """Profile this machine's GPU/CPU/RAM. Always a fresh scan — for a
    cached version, see GET /status."""
    return scan_hardware()


@router.get("/models", response_model=list[ModelCompatibility])
def models() -> list[ModelCompatibility]:
    """Classify every catalog model against currently detected hardware."""
    hw = scan_hardware()
    return classify_all(hw)