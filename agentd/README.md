# llm-max agentd

Local HTTP daemon wrapping `llm_max` core, so the (future) Java Spring
Boot `webui/backend` can trigger scans, pulls, runs, and tuning without
needing a Python runtime of its own.

## Run

```bash
cd agentd
pip install -e ../core
pip install -e ".[dev]"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive API docs: http://127.0.0.1:8000/docs

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/hardware/scan` | Fresh hardware scan |
| GET | `/models` | Model compatibility for this machine |
| GET | `/status` | Hardware status (Redis-cached if enabled) |
| GET | `/history` | Recent run history |
| POST | `/models/{id}/pull` | Streamed NDJSON pull progress |
| POST | `/models/{id}/run` | Run a prompt, persist the result |
| POST | `/models/{id}/tune` | One-shot benchmark-and-tune |
| GET | `/autopilot/{id}/status` | Current tuned config + lock state |
| POST | `/autopilot/{id}/disable` | Lock a model's config |

**Note:** `autopilot enable` is intentionally not exposed here — see the
docstring in `app/routes/recommendations.py` for why.

## Tests

```bash
pytest tests/ -v
```

Binds to `127.0.0.1` by default — not intended to be exposed beyond
localhost. See the repo root `SECURITY.md`.