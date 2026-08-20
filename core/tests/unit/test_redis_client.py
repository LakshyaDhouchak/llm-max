from llm_max.domain import GpuInfo, HardwareProfile
from llm_max.storage.redis_client import StatusCache

SAMPLE_PROFILE = HardwareProfile(
    gpus=[GpuInfo(index=0, name="Test GPU", total_vram_mb=8000, free_vram_mb=6000, used_vram_mb=2000)],
    cpu_cores_physical=4,
    cpu_cores_logical=8,
    total_ram_mb=16000,
    available_ram_mb=12000,
)


def test_set_last_scan_returns_true_on_success(mocker):
    fake_client = mocker.Mock()
    mocker.patch("redis.Redis", return_value=fake_client)

    cache = StatusCache()
    result = cache.set_last_scan(SAMPLE_PROFILE)

    assert result is True
    fake_client.set.assert_called_once()


def test_set_last_scan_returns_false_when_redis_unreachable(mocker):
    mocker.patch("redis.Redis", side_effect=ConnectionError())

    cache = StatusCache()
    result = cache.set_last_scan(SAMPLE_PROFILE)

    assert result is False


def test_get_last_scan_returns_none_when_no_cache(mocker):
    fake_client = mocker.Mock()
    fake_client.get.return_value = None
    mocker.patch("redis.Redis", return_value=fake_client)

    cache = StatusCache()
    assert cache.get_last_scan() is None


def test_get_last_scan_returns_none_when_redis_unreachable(mocker):
    mocker.patch("redis.Redis", side_effect=ConnectionError())

    cache = StatusCache()
    assert cache.get_last_scan() is None


def test_get_last_scan_deserializes_cached_profile(mocker):
    fake_client = mocker.Mock()
    fake_client.get.return_value = SAMPLE_PROFILE.model_dump_json()
    mocker.patch("redis.Redis", return_value=fake_client)

    cache = StatusCache()
    result = cache.get_last_scan()

    assert result is not None
    assert result.gpus[0].name == "Test GPU"
    assert result.total_ram_mb == 16000


def test_is_available_true_when_ping_succeeds(mocker):
    fake_client = mocker.Mock()
    fake_client.ping.return_value = True
    mocker.patch("redis.Redis", return_value=fake_client)

    assert StatusCache().is_available() is True


def test_is_available_false_when_redis_unreachable(mocker):
    mocker.patch("redis.Redis", side_effect=ConnectionError())
    assert StatusCache().is_available() is False