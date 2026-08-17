# Contributing to LLM Max

Thanks for your interest in contributing! This project is in early development
(Phase 1 — see [README.md](README.md) for the roadmap).

## Dev setup

```bash
git clone https://github.com/<you>/llm-max.git
cd llm-max/core
pip install -e ".[dev]"
```

## Running tests

```bash
cd core
pytest tests/ -v
```

## Project structure

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design and
component boundaries before making structural changes.

## Adding a new runtime adapter (e.g. vLLM, llama.cpp)

Implement the `RuntimeAdapter` interface in `core/llm_max/adapters/base.py`.
Look at `ollama.py` as the reference implementation. Adapters must:

- Never raise on `is_available()` — return `False` instead.
- Degrade gracefully if the runtime isn't installed/running.

## Adding a model to the catalog

Add an entry to `core/llm_max/catalog/models.json` following the existing
schema (`ModelSpec` in `core/llm_max/models.py`). VRAM figures should be for
the most common quantization (`Q4_K_M`) unless noted.

## Code style

- Python: `black` formatting, type hints on public functions.
- Keep the CLI core (`core/llm_max/`) free of Java/Docker/service
  dependencies — it must always work standalone.

## Pull requests

- Keep PRs focused on one change.
- Add/update tests for any logic change (especially `catalog/classify`).
- Reference the relevant roadmap phase in your PR description if applicable.
