from llm_max.compatibility import classify, classify_all
from llm_max.domain import CompatibilityTier, ModelSpec
from tests.fixtures.hardware import cpu_only_hardware_profile, gpu_hardware_profile

SMALL_MODEL = ModelSpec(
    id="test:1b",
    display_name="Test 1B",
    family="test",
    param_size_b=1,
    min_vram_mb=2000,
    recommended_vram_mb=3000,
    min_ram_mb=4000,
)


def test_great_fit_when_vram_exceeds_recommended():
    hw = gpu_hardware_profile(free_vram_mb=8000)
    result = classify(SMALL_MODEL, hw)
    assert result.tier == CompatibilityTier.GREAT_FIT


def test_will_run_when_vram_between_min_and_recommended():
    hw = gpu_hardware_profile(free_vram_mb=2500)
    result = classify(SMALL_MODEL, hw)
    assert result.tier == CompatibilityTier.WILL_RUN


def test_may_be_slow_when_vram_below_min_but_close():
    hw = gpu_hardware_profile(free_vram_mb=1500)  # 75% of the 2000 min
    result = classify(SMALL_MODEL, hw)
    assert result.tier == CompatibilityTier.MAY_BE_SLOW


def test_not_recommended_when_vram_far_below_min():
    hw = gpu_hardware_profile(free_vram_mb=500)
    result = classify(SMALL_MODEL, hw)
    assert result.tier == CompatibilityTier.NOT_RECOMMENDED


def test_cpu_only_may_be_slow_with_enough_ram():
    hw = cpu_only_hardware_profile(available_ram_mb=10000)
    result = classify(SMALL_MODEL, hw)
    assert result.tier == CompatibilityTier.MAY_BE_SLOW


def test_cpu_only_not_recommended_with_insufficient_ram():
    hw = cpu_only_hardware_profile(available_ram_mb=3000)
    result = classify(SMALL_MODEL, hw)
    assert result.tier == CompatibilityTier.NOT_RECOMMENDED


def test_classify_all_sorts_best_fit_first():
    hw = gpu_hardware_profile(free_vram_mb=8000)
    results = classify_all(hw)
    tiers = [r.tier for r in results]
    assert tiers == sorted(
        tiers,
        key=lambda t: [
            CompatibilityTier.GREAT_FIT,
            CompatibilityTier.WILL_RUN,
            CompatibilityTier.MAY_BE_SLOW,
            CompatibilityTier.NOT_RECOMMENDED,
        ].index(t),
    )