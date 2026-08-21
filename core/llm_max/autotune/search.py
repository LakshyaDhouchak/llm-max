"""Generates candidate configs to benchmark against a baseline.

v1 deliberately varies only num_ctx — the single biggest throughput/fit
lever for the runtimes we support (see docs/PHASE3_DESIGN.md section 3).
A full grid over context x batch x quantization would multiply benchmark
runs (each costing real wall-clock time) without a corresponding increase
in confidence for a first version of this loop.
"""

from __future__ import annotations

_CTX_FLOOR = 512
_CTX_CEILING = 8192
_DEFAULT_BASELINE_CTX = 2048


def generate_candidates(baseline_config: dict) -> list[dict]:
    """Given a baseline config (e.g. {"num_ctx": 2048}), return a small set
    of candidate configs to benchmark: the baseline itself, one step down
    (half the context, floor-bounded), and one step up (double the
    context, ceiling-bounded). Duplicates (e.g. baseline already at the
    floor/ceiling) are removed, so this may return fewer than 3.
    """
    baseline_ctx = baseline_config.get("num_ctx", _DEFAULT_BASELINE_CTX)

    lower = max(_CTX_FLOOR, baseline_ctx // 2)
    upper = min(_CTX_CEILING, baseline_ctx * 2)

    unique_ctx_values = sorted({baseline_ctx, lower, upper})
    return [{"num_ctx": ctx} for ctx in unique_ctx_values]