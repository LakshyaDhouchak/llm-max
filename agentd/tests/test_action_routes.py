def test_run_returns_result_and_persists(client, fake_storage):
    resp = client.post("/models/llama3.2:1b/run", json={"prompt": "hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["response"] == "fake response"
    assert "run_record" in body
    assert body["run_record"]["model_id"] == "llama3.2:1b"
    assert len(fake_storage.saved_runs) == 1


def test_run_defaults_prompt_when_omitted(client):
    resp = client.post("/models/llama3.2:1b/run", json={})
    assert resp.status_code == 200


def test_run_returns_503_when_adapter_unavailable(client, fake_adapter):
    fake_adapter._available = False
    resp = client.post("/models/llama3.2:1b/run", json={"prompt": "hi"})
    assert resp.status_code == 503


def test_pull_streams_ndjson_events(client, fake_adapter):
    resp = client.post("/models/llama3.2:1b/pull")
    assert resp.status_code == 200
    lines = [l for l in resp.text.strip().split("\n") if l]
    assert len(lines) >= 2
    assert "pulling manifest" in lines[0]
    assert "success" in lines[-1]


def test_pull_streams_error_when_adapter_unavailable(client, fake_adapter):
    fake_adapter._available = False
    resp = client.post("/models/llama3.2:1b/pull")
    assert resp.status_code == 200  # stream itself starts fine
    assert "error" in resp.text


def test_tune_returns_session(client):
    resp = client.post("/models/llama3.2:1b/tune", json={"dry_run": True})
    assert resp.status_code == 200
    body = resp.json()
    assert "outcome" in body
    assert "baseline" in body
    assert "candidates" in body


def test_tune_dry_run_does_not_save_config(client, fake_storage):
    client.post("/models/llama3.2:1b/tune", json={"dry_run": True})
    assert fake_storage.get_tuned_config("llama3.2:1b") is None


def test_tune_returns_503_when_adapter_unavailable(client, fake_adapter):
    fake_adapter._available = False
    resp = client.post("/models/llama3.2:1b/tune", json={"dry_run": True})
    assert resp.status_code == 503