from llm_max.profiler.system import cpu_counts, cpu_model_name, ram_mb


def test_cpu_counts_returns_positive_integers():
    physical, logical = cpu_counts()
    assert physical >= 1
    assert logical >= 1
    assert logical >= physical


def test_ram_mb_returns_positive_integers():
    total, available = ram_mb()
    assert total > 0
    assert available > 0
    assert available <= total


def test_cpu_model_name_does_not_raise():
    # May return None on unusual platforms, but must never raise.
    result = cpu_model_name()
    assert result is None or isinstance(result, str)