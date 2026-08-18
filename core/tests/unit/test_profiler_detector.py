from llm_max.profiler.detector import scan_hardware
from tests.fakes.fake_hardware_provider import FakeGpuProvider, make_gpu


def test_no_providers_means_no_gpus():
    profile = scan_hardware(providers=[])
    assert profile.gpus == []
    assert profile.has_gpu is False


def test_single_available_provider_reports_its_gpus():
    provider = FakeGpuProvider(gpus=[make_gpu(index=0, free_vram_mb=8000)])
    profile = scan_hardware(providers=[provider])

    assert profile.has_gpu is True
    assert len(profile.gpus) == 1
    assert profile.gpus[0].free_vram_mb == 8000


def test_unavailable_provider_is_skipped():
    provider = FakeGpuProvider(gpus=[make_gpu()], available=False)
    profile = scan_hardware(providers=[provider])
    assert profile.gpus == []


def test_multiple_providers_combine_gpus():
    provider_a = FakeGpuProvider(gpus=[make_gpu(index=0, name="GPU A")])
    provider_b = FakeGpuProvider(gpus=[make_gpu(index=0, name="GPU B")])
    profile = scan_hardware(providers=[provider_a, provider_b])

    assert len(profile.gpus) == 2
    assert {g.name for g in profile.gpus} == {"GPU A", "GPU B"}


def test_provider_that_raises_on_detect_does_not_crash_scan():
    good_provider = FakeGpuProvider(gpus=[make_gpu(name="Good GPU")])
    bad_provider = FakeGpuProvider(available=True, raise_on_detect=True)

    profile = scan_hardware(providers=[bad_provider, good_provider])

    # The failing provider is skipped; the good one still contributes.
    assert len(profile.gpus) == 1
    assert profile.gpus[0].name == "Good GPU"


def test_scan_hardware_always_includes_system_info():
    profile = scan_hardware(providers=[])
    assert profile.cpu_cores_physical >= 1
    assert profile.cpu_cores_logical >= 1
    assert profile.total_ram_mb > 0