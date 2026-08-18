from llm_max.profiler.nvidia import NvidiaGpuProvider


def test_is_available_never_raises_without_nvidia_hardware():
    """On a machine with no NVIDIA GPU/driver (like CI), is_available()
    must return False, never raise."""
    provider = NvidiaGpuProvider()
    result = provider.is_available()
    assert isinstance(result, bool)


def test_detect_returns_empty_list_without_nvidia_hardware():
    """detect() must degrade to [] rather than raise when there's no
    NVIDIA GPU, no driver, or pynvml isn't installed."""
    provider = NvidiaGpuProvider()
    gpus = provider.detect()
    assert isinstance(gpus, list)


def test_vendor_is_nvidia():
    assert NvidiaGpuProvider().vendor == "nvidia"


def test_detect_handles_missing_pynvml(mocker):
    """If pynvml itself isn't importable, detect() returns [] rather than
    raising ImportError."""
    mocker.patch.dict("sys.modules", {"pynvml": None})
    provider = NvidiaGpuProvider()
    assert provider.detect() == []