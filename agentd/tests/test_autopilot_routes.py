from llm_max.domain import TunedConfig


def test_autopilot_status_no_config_yet(client):
    resp = client.get("/autopilot/llama3.2:1b/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_config"] is False
    assert body["config"] is None


def test_autopilot_status_returns_config(client, fake_storage):
    fake_storage.save_tuned_config(TunedConfig(model_id="llama3.2:1b", config={"num_ctx": 2048}))
    resp = client.get("/autopilot/llama3.2:1b/status")
    body = resp.json()
    assert body["has_config"] is True
    assert body["config"] == {"num_ctx": 2048}
    assert body["is_locked"] is False


def test_autopilot_disable_without_config_returns_404(client):
    resp = client.post("/autopilot/llama3.2:1b/disable")
    assert resp.status_code == 404


def test_autopilot_disable_locks_existing_config(client, fake_storage):
    fake_storage.save_tuned_config(TunedConfig(model_id="llama3.2:1b", config={"num_ctx": 2048}))
    resp = client.post("/autopilot/llama3.2:1b/disable")
    assert resp.status_code == 200
    assert resp.json() == {"model_id": "llama3.2:1b", "locked": True}

    status_resp = client.get("/autopilot/llama3.2:1b/status")
    assert status_resp.json()["is_locked"] is True


def test_no_enable_endpoint_exists(client):
    """Deliberate: autopilot enable is not exposed via HTTP in v1 — see
    the module docstring in app/routes/recommendations.py."""
    resp = client.post("/autopilot/llama3.2:1b/enable")
    assert resp.status_code == 404