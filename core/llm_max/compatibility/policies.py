"""Policy constants for the compatibility estimator.

Kept separate from estimator.py so the thresholds that define "great fit" vs
"will run" vs "may be slow" are easy to find, tune, and unit-test in
isolation as real-world benchmark data comes in (Phase 3).
"""

from __future__ import annotations

# GPU path: below this fraction of a model's min_vram_mb, we no longer call
# it "may be slow" (CPU offload) and instead call it "not recommended".
MAY_BE_SLOW_VRAM_FLOOR_RATIO = 0.7

# CPU-only path: RAM needed beyond the model's min_ram_mb before CPU-only
# inference is classified "may be slow" rather than "not recommended".
# CPU inference is slow and memory-hungry (KV cache, OS, other processes),
# so we're stricter here than on the GPU path.
CPU_ONLY_RAM_HEADROOM_MB = 4000

TIER_SORT_ORDER = {
    "great_fit": 0,
    "will_run": 1,
    "may_be_slow": 2,
    "not_recommended": 3,
}