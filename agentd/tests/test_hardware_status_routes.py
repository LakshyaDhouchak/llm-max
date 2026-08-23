def test_health():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_hardware_scan_returns_profile(client):
    resp = client.get("/hardware/scan")
    assert resp.status_code == 200
    body = resp.json()
    assert "cpu_cores_physical" in body
    assert "gpus" in body


def test_models_returns_compatibility_list(client):
    resp = client.get("/models")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) > 0
    assert "tier" in body[0]
    assert "reason" in body[0]


def test_status_fresh_scan_when_redis_disabled(client, monkeypatch):
    monkeypatch.delenv("LLM_MAX_REDIS_ENABLED", raising=False)
    resp = client.get("/status")
    assert resp.status_code == 200
    assert "cpu_cores_physical" in resp.json()


def test_history_empty_by_default(client):
    resp = client.get("/history")
    assert resp.status_code == 200
    assert resp.json() == []


def test_history_reflects_storage_state(client, fake_storage):
    from llm_max.domain import RunRecord

    fake_storage.save_run(
        RunRecord(model_id="model:1b", prompt="hi", tokens_generated=10, total_duration_s=1.0)
    )
    resp = client.get("/history")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["model_id"] == "model:1b"


def test_history_respects_limit(client, fake_storage):
    from llm_max.domain import RunRecord

    for i in range(5):
        fake_storage.save_run(
            RunRecord(model_id="model:1b", prompt=f"p{i}", tokens_generated=1, total_duration_s=1.0)
        )
    resp = client.get("/history", params={"limit": 2})
    assert len(resp.json()) == 2