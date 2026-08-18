"""Hardware x model fit estimation.

Pure logic, no I/O — takes a HardwareProfile and ModelSpec(s) already loaded
by catalog.loader, and returns a tiered compatibility verdict.
"""

from __future__ import annotations

from llm_max.catalog.loader import load_catalog
from llm_max.compatibility.policies import (
    CPU_ONLY_RAM_HEADROOM_MB,
    MAY_BE_SLOW_VRAM_FLOOR_RATIO,
    TIER_SORT_ORDER,
)
from llm_max.domain import (
    CompatibilityTier,
    HardwareProfile,
    ModelCompatibility,
    ModelSpec,
)


def classify(model: ModelSpec, hw: HardwareProfile) -> ModelCompatibility:
    """Classify a single model against a hardware profile.

    Logic:
      - With a GPU: compare best-GPU free VRAM against min/recommended VRAM.
      - Without a GPU: fall back to a conservative RAM-based CPU estimate.
    """
    if hw.has_gpu:
        return _classify_gpu(model, hw)
    return _classify_cpu_only(model, hw)


def _classify_gpu(model: ModelSpec, hw: HardwareProfile) -> ModelCompatibility:
    best_gpu = max(hw.gpus, key=lambda g: g.free_vram_mb)
    free_vram = best_gpu.free_vram_mb

    if free_vram >= model.recommended_vram_mb:
        return ModelCompatibility(
            model=model,
            tier=CompatibilityTier.GREAT_FIT,
            reason=(
                f"{free_vram} MB free VRAM on {best_gpu.name} comfortably "
                f"exceeds the {model.recommended_vram_mb} MB recommended."
            ),
        )
    if free_vram >= model.min_vram_mb:
        return ModelCompatibility(
            model=model,
            tier=CompatibilityTier.WILL_RUN,
            reason=(
                f"{free_vram} MB free VRAM meets the {model.min_vram_mb} MB "
                f"minimum but is below the {model.recommended_vram_mb} MB "
                "recommended — expect reduced context size or batch size."
            ),
        )
    if free_vram >= model.min_vram_mb * MAY_BE_SLOW_VRAM_FLOOR_RATIO:
        return ModelCompatibility(
            model=model,
            tier=CompatibilityTier.MAY_BE_SLOW,
            reason=(
                f"Only {free_vram} MB free VRAM vs. {model.min_vram_mb} MB "
                "minimum — will likely require CPU offload, slowing "
                "inference significantly."
            ),
        )
    return ModelCompatibility(
        model=model,
        tier=CompatibilityTier.NOT_RECOMMENDED,
        reason=(
            f"{free_vram} MB free VRAM is far below the "
            f"{model.min_vram_mb} MB minimum required."
        ),
    )


def _classify_cpu_only(model: ModelSpec, hw: HardwareProfile) -> ModelCompatibility:
    if hw.available_ram_mb >= model.min_ram_mb + CPU_ONLY_RAM_HEADROOM_MB:
        return ModelCompatibility(
            model=model,
            tier=CompatibilityTier.MAY_BE_SLOW,
            reason=(
                "No GPU detected — running on CPU only. RAM is sufficient "
                f"({hw.available_ram_mb} MB available) but expect noticeably "
                "lower throughput than GPU inference."
            ),
        )
    return ModelCompatibility(
        model=model,
        tier=CompatibilityTier.NOT_RECOMMENDED,
        reason=(
            f"No GPU detected and only {hw.available_ram_mb} MB RAM available "
            f"vs. {model.min_ram_mb} MB minimum needed for CPU inference."
        ),
    )


def classify_all(hw: HardwareProfile) -> list[ModelCompatibility]:
    """Classify every catalog model against the given hardware, best-fit first."""
    results = [classify(m, hw) for m in load_catalog()]
    return sorted(results, key=lambda r: TIER_SORT_ORDER[r.tier.value])