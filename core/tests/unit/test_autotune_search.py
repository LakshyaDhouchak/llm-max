from llm_max.autotune.search import generate_candidates


def test_generates_three_candidates_for_typical_baseline():
    candidates = generate_candidates({"num_ctx": 2048})
    ctx_values = sorted(c["num_ctx"] for c in candidates)
    assert ctx_values == [1024, 2048, 4096]


def test_baseline_included_among_candidates():
    candidates = generate_candidates({"num_ctx": 2048})
    assert {"num_ctx": 2048} in candidates


def test_lower_bound_respects_floor():
    candidates = generate_candidates({"num_ctx": 512})
    ctx_values = sorted(c["num_ctx"] for c in candidates)
    assert min(ctx_values) >= 512


def test_upper_bound_respects_ceiling():
    candidates = generate_candidates({"num_ctx": 8192})
    ctx_values = sorted(c["num_ctx"] for c in candidates)
    assert max(ctx_values) <= 8192


def test_missing_num_ctx_uses_default_baseline():
    candidates = generate_candidates({})
    assert len(candidates) >= 1
    assert all("num_ctx" in c for c in candidates)


def test_no_duplicate_candidates():
    candidates = generate_candidates({"num_ctx": 512})
    ctx_values = [c["num_ctx"] for c in candidates]
    assert len(ctx_values) == len(set(ctx_values))