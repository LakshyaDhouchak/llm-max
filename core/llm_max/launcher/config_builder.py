"""Builds runtime options (e.g. Ollama's num_ctx) tuned to available hardware.

This is a simple, honest heuristic — not real benchmarking. It exists so
`llm-max run` doesn't hand a "will run" or "may be slow" model the same
generous defaults as a "great fit" model and then wonder why it OOMs or
crawls. Phase 3's autotuner replaces this heuristic with actual measured
benchmarking; this is the placeholder that makes launcher/ meaningful
before that lands.
"""

from __future__ import annotations

from llm_max.domain import HardwareProfile, ModelSpec

# Context-size tiers, keyed by how comfortably the model fits in free VRAM.
# These are deliberately conservative defaults, not tuned/measured values.
_GENEROUS_CTX = 4096
_MODERATE_CTX = 2048
_CONSERVATIVE_CTX = 1024


def build_run_config(model: ModelSpec, hw: HardwareProfile) -> dict:
    """Compute runtime options for `model` given the current `hw` profile.

    Returns a dict suitable for passing as `options` to a RuntimeAdapter's
    `run()` (e.g. {"num_ctx": 2048} for Ollama). Returns {} when there's no
    GPU to reason about — CPU-only runs use the runtime's own defaults
    rather than guessing.
    """
    if not hw.has_gpu:
        return {}

    best_gpu = max(hw.gpus, key=lambda g: g.free_vram_mb)
    free_vram = best_gpu.free_vram_mb

    if free_vram >= model.recommended_vram_mb:
        return {"num_ctx": _GENEROUS_CTX}
    if free_vram >= model.min_vram_mb:
        return {"num_ctx": _MODERATE_CTX}
    return {"num_ctx": _CONSERVATIVE_CTX}