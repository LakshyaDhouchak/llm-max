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

### Windows: "llm-max is not recognized" after install

If `pip install` succeeds but `llm-max` or `pytest` aren't found afterward,
pip installed them to your user Scripts folder, which isn't on PATH yet —
this is a common pip/Windows issue, not specific to this project. Fix it
once, permanently, per user account:

```powershell
[Environment]::SetEnvironmentVariable(
    "Path",
    $env:Path + ";$env:APPDATA\Python\Python3XX\Scripts",  # match your Python version, e.g. Python314
    "User"
)
```

Then **close and reopen PowerShell** (PATH changes only apply to new
sessions) and retry. The exact path was shown in your `pip install` output
as a warning — copy it from there rather than guessing the version number.

**Alternative (no restart needed):** run the tools by their full path once
to confirm they work, e.g.
`& "$env:APPDATA\Python\Python3XX\Scripts\llm-max.exe" --help`.

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