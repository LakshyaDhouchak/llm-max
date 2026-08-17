# LLM Max

> Your hardware. Your models. Maximum performance.

LLM Max profiles your machine's GPU/CPU/RAM, tells you which local LLMs will
run well on it, and automatically tunes your chosen model to get the most
throughput/latency out of your hardware.

**Status:** early development (Phase 1 — CLI core).

## Quick start (dev)

```bash
cd core
pip install -e ".[dev]"
llm-max scan
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design.

## Roadmap

- [x] Phase 1 — CLI core: `scan`, `models`, `pull`, `run`, `history` (Ollama, NVIDIA-only, local SQLite persistence)
- [ ] Phase 2 — Team/server persistence (MySQL + Flyway, Redis), `launcher/` orchestration
- [ ] Phase 3 — Autotuner (LangGraph) + benchmark harness + recommendations engine
- [ ] Phase 4 — Web UI (Spring Boot + React) + local agentd daemon + observability
- [ ] Phase 5 — Streaming telemetry (Kafka + Schema Registry + Avro, optional)
- [ ] Future — Fleet deployment (systemd, Helm, Kubernetes)

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full target folder structure.

## License

MIT — see [LICENSE](LICENSE).
