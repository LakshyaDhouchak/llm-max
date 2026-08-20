from llm_max.domain import ModelSpec
from llm_max.launcher.config_builder import build_run_config
from tests.fixtures.hardware import cpu_only_hardware_profile, gpu_hardware_profile

MODEL = ModelSpec(
    id="test:7b",
    display_name="Test 7B",
    family="test",
    param_size_b=7,
    min_vram_mb=5000,
    recommended_vram_mb=8000,
    min_ram_mb=10000,
)


def test_generous_context_when_vram_comfortable():
    hw = gpu_hardware_profile(free_vram_mb=10000)
    config = build_run_config(MODEL, hw)
    assert config["num_ctx"] == 4096


def test_moderate_context_when_vram_meets_minimum():
    hw = gpu_hardware_profile(free_vram_mb=6000)
    config = build_run_config(MODEL, hw)
    assert config["num_ctx"] == 2048


def test_conservative_context_when_vram_below_minimum():
    hw = gpu_hardware_profile(free_vram_mb=3000)
    config = build_run_config(MODEL, hw)
    assert config["num_ctx"] == 1024


def test_empty_config_when_no_gpu():
    hw = cpu_only_hardware_profile(available_ram_mb=16000)
    config = build_run_config(MODEL, hw)
    assert config == {}