# LLM Max — Architecture

> "Your hardware. Your models. Maximum performance."

This document is the source-of-truth design for LLM Max before any code is written.
It defines component boundaries, data flow, storage, and the repo layout.

---

## 1. Component Map

┌─────────────────────────────────────────────────────────────────────┐
│                         USER'S MACHINE                              │
│                                                                     │
│  ┌────────────────────┐        ┌──────────────────────────────┐     │
│  │   llm-max CLI      │        │  llm-max-agentd (local API)  │     │
│  │   (Python, Click)  │◄──────►│  FastAPI, runs as daemon     │     │
│  │                    │        │  wraps the same core lib     │     │
│  └─────────┬──────────┘        └───────────┬──────────────────┘     │
│            │                               │                        │
│            ▼                               ▼                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              llm-max-core (Python library)                  │    │
│  │  - hardware_profiler   (GPU/CPU/RAM detection)              │    │
│  │  - runtime_adapters     (Ollama / vLLM / llama.cpp)         │    │
│  │  - model_catalog        (compatibility scoring)             │    │
│  │  - benchmarker          (latency/throughput sampling)       │    │
│  │  - autotuner            (LangGraph state machine)           │    │
│  │  - telemetry_producer   (Avro → Kafka, optional)            │    │
│  └───────┬───────────────────────┬───────────────────┬─────────┘    │
│          │                       │                   │              │
│          ▼                       ▼                   ▼              │
│    ┌──────────┐           ┌───────────┐       ┌──────────────┐      │
│    │  MySQL   │           │   Redis   │       │ Kafka (opt.) │      │
│    │ (Flyway) │           │ (live     │       │ + Schema     │      │
│    │ history  │           │  status)  │       │  Registry    │      │
│    └────┬─────┘           └─────┬─────┘       └──────┬───────┘      │
│         │                       │                     │             │
└─────────┼───────────────────────┼─────────────────────┼─────────────┘
          │                       │                     │
          ▼                       ▼                     ▼
┌───────────────────────────────────────────────────────────────────┐
│                    OPTIONAL WEB UI (opt-in service)               │
│  ┌─────────────────────────┐    ┌─────────────────────────────┐   │
│  │  Spring Boot backend    │    │  Kafka Streams app (Java)   │   │
│  │  REST API over MySQL/   │    │  windowed p95/throughput    │   │
│  │  Redis, calls agentd    │    │  aggregation → MySQL/Redis  │   │
│  │  for actions            │    │                             │   │
│  └─────────────────────────┘    └─────────────────────────────┘   │
│              │                                                    │
│              ▼                                                    │
│      React/simple frontend (dashboard)                            │
└───────────────────────────────────────────────────────────────────┘

**Key principle:** the CLI works completely standalone with zero services running
(MySQL/Redis/Kafka are all optional, degrade gracefully to file-based storage
if absent). The web UI and Kafka pipeline are opt-in layers on top.

---

## 2. Why each piece of tech lives where it does

| Component | Tech | Reasoning |
|---|---|---|
| Hardware profiling, runtime process control | **Python** | `pynvml`, `psutil`, subprocess control — this is systems work Python does natively; Java has no comparable ecosystem here |
| Autotuner (measure → adjust → evaluate → rollback loop) | **Python + LangGraph** | This loop *is* a state graph. LangGraph gives you explicit states, conditional edges (rollback on SLO breach), and persistence for free — better fit than hand-rolled control flow |
| Local daemon exposing CLI actions over HTTP | **Python (FastAPI)** | Thin wrapper so the (optional) web UI can trigger `pull`/`run`/`tune` remotely without duplicating logic |
| Config + benchmark history | **MySQL + Flyway** | You want versioned, queryable history ("show me every tuning run for llama3:8b on this GPU over the last month") — relational fits, Flyway gives you clean migrations as the schema evolves |
| Live/ephemeral status (current GPU%, active model, last-5-min latency) | **Redis** | Fast reads for `llm-max status` and the dashboard; TTL'd keys, no need for durability |
| Telemetry stream (raw metric samples) | **Kafka + Avro + Schema Registry** | *Optional, v2.* Only worth it once you want rolling windowed aggregates (p95 over sliding windows) rather than point samples. Schema Registry keeps the telemetry contract stable as you add fields |
| Windowed aggregation (p95, throughput, stability score) | **Kafka Streams (Java)** | Natural fit — this is exactly what Kafka Streams is for: consume raw samples, produce rolling aggregates |
| Web dashboard backend | **Spring Boot** | REST API over MySQL/Redis, orchestrates calls to the local agentd, serves the frontend |
| Packaging/distribution | **Docker** | `docker-compose` bundles MySQL + Redis + (optional) Kafka + Spring UI for anyone who wants the full stack; CLI itself ships as a standalone pip package / binary, no Docker required |

**Honest note on Kafka:** for a single-machine, single-user tool (which is the
stated v1 scope), Kafka is genuinely optional complexity. It earns its place
when you want (a) proper windowed metrics instead of instantaneous snapshots,
or (b) a future multi-machine "fleet" mode where several hosts report into one
place. Recommend treating it as a **v2 feature flag** — the telemetry_producer
module writes to Kafka *if configured*, otherwise writes straight to Redis/MySQL.

---

## 3. Data model (MySQL, Flyway-managed)

Core tables for v1:

```sql
-- hardware profile snapshots (versioned per host)
hardware_profiles (id, host_id, gpu_info JSON, cpu_info JSON, ram_mb, detected_at)

-- curated model catalog
models (id, name, family, param_size, quant_variants JSON, min_vram_mb, notes)

-- compatibility classification result (computed, cached)
model_compatibility (id, host_id, model_id, tier ENUM('great_fit','will_run','may_be_slow','not_recommended'), computed_at)

-- a specific tuned configuration for a model on a host
tuned_configs (id, host_id, model_id, runtime, config JSON, is_locked, created_at)

-- benchmark run results (before/after, autotuner iterations)
benchmark_runs (id, tuned_config_id, iteration, context_size, batch_size,
                quant_level, throughput_tps, p95_latency_ms, oom_occurred, created_at)

-- autopilot event log (for rollback/audit trail)
autopilot_events (id, host_id, model_id, event_type ENUM('adjust','rollback','lock'),
                   details JSON, created_at)
```

Flyway migration `V1__init_schema.sql` covers all of the above; future changes
are additive migrations, never manual schema edits.

---

## 4. Repo structure (monorepo)

This is the full target structure. Status markers show what's actually built
(✅) vs. planned (⏳) as of the current phase — see section 5 for the phase
breakdown. `deploy/` (systemd/Helm/Kubernetes) is confirmed in scope for a
future fleet-deployment phase, even though early phases are single-machine.

llm-max/
├── core/                                   # Python CLI + optimization engine
│   ├── llm_max/
│   │   ├── __init__.py
│   │   ├── cli.py                          # ✅ scan, models, pull, run, history
│   │   ├── config.py                       # ⏳ env vars + ~/.llm-max/config.yaml
│   │   ├── domain.py                       # ✅ Pydantic domain entities
│   │   ├── profiler/
│   │   │   ├── __init__.py                 # ✅
│   │   │   ├── base.py                     # ✅ GpuProvider ABC
│   │   │   ├── detector.py                 # ✅ combines system info + GpuProviders
│   │   │   ├── system.py                   # ✅ CPU/RAM (vendor-independent)
│   │   │   ├── nvidia.py                   # ✅ NvidiaGpuProvider (pynvml)
│   │   │   ├── apple_silicon.py            # ⏳ future
│   │   │   └── amd_rocm.py                 # ⏳ future
│   │   ├── adapters/
│   │   │   ├── base.py                     # ✅ RuntimeAdapter ABC
│   │   │   ├── ollama.py                   # ✅ done
│   │   │   ├── vllm.py                     # ⏳ future
│   │   │   └── llama_cpp.py                # ⏳ future
│   │   ├── catalog/                        # ✅ data layer
│   │   │   ├── loader.py                   # ✅ load + validate
│   │   │   ├── validators.py               # ✅ schema validation
│   │   │   └── models.json                 # ✅ curated catalog
│   │   ├── compatibility/                  # ✅ policy/logic layer (split from catalog)
│   │   │   ├── estimator.py                # ✅ classify / classify_all
│   │   │   └── policies.py                 # ✅ tunable tier thresholds
│   │   ├── launcher/                       # ⏳ Phase 2 — pull/run orchestration
│   │   │   ├── service.py
│   │   │   └── config_builder.py
│   │   ├── bench/                          # ⏳ Phase 3
│   │   ├── autotune/                       # ⏳ Phase 3 — LangGraph loop
│   │   ├── recommendations/                # ⏳ Phase 3
│   │   ├── storage/                        # ✅ Phase 1/2 — persistence
│   │   │   ├── base.py                     # ✅ Storage interface
│   │   │   ├── sqlite_store.py             # ✅ local, zero-infra (run history, tuned configs)
│   │   │   ├── mysql_client.py             # ⏳ Phase 2 — team/server deployment
│   │   │   └── redis_client.py             # ⏳ Phase 2 — live status cache
│   │   ├── telemetry/                      # ⏳ Phase 5 — opt-in, privacy-first
│   │   │   ├── producer.py
│   │   │   └── privacy.py                  # consent/redaction, not an afterthought
│   │   └── observability/                  # ⏳ Phase 4 — logging, metrics, health
│   ├── tests/
│   │   ├── unit/                           # ✅ 42 passing tests
│   │   ├── fixtures/                       # ✅ shared mock hardware profiles + Ollama response payloads
│   │   ├── fakes/                          # ✅ FakeGpuProvider, FakeOllamaAdapter
│   │   ├── integration/                    # ⏳ real Ollama/NVIDIA integration tests
│   │   └── e2e/                            # ⏳ full scan→models→pull→run flow
│   ├── pyproject.toml                      # ✅
│   └── README.md                           # ✅
│
├── agentd/                                 # ⏳ Phase 4 — local FastAPI daemon
├── contracts/                              # ⏳ shared Avro/OpenAPI source of truth
│   ├── avro/telemetry_event.avsc
│   └── openapi/agentd.openapi.yaml
├── migrations/                             # ⏳ Phase 2 — Flyway
│   └── sql/V1__init_schema.sql
├── streaming/                              # ⏳ Phase 5 — Kafka Streams (Java)
├── webui/                                  # ⏳ Phase 4 — Spring Boot + React
│   ├── backend/
│   └── frontend/
├── docker/                                 # ⏳ Phase 2+ orchestration
│   ├── docker-compose.min.yml              # core + MySQL + Redis
│   ├── docker-compose.full.yml             # + webui, Kafka, observability
│   └── prometheus/ + grafana/
├── deploy/                                 # ⏳ future — fleet deployment (confirmed in scope)
│   ├── systemd/llm-max-agentd.service
│   ├── helm/llm-max/
│   └── kubernetes/
├── examples/                               # ⏳ usage walkthroughs
├── docs/
│   ├── ARCHITECTURE.md                     # ✅ this file
│   ├── ROADMAP.md                          # ⏳
│   ├── CLI_REFERENCE.md                    # ⏳
│   ├── RUNTIME_ADAPTER_GUIDE.md            # ⏳
│   ├── HARDWARE_PROVIDER_GUIDE.md          # ⏳
│   ├── TUNING_SAFETY.md                    # ⏳
│   ├── TELEMETRY_PRIVACY.md                # ⏳
│   └── OPERATIONS.md                       # ⏳
├── .github/
│   ├── ISSUE_TEMPLATE/                     # ✅
│   ├── PULL_REQUEST_TEMPLATE.md            # ✅
│   └── workflows/
│       ├── ci-core.yml                     # ✅
│       ├── ci-webui.yml                    # ⏳
│       ├── ci-streaming.yml                # ⏳
│       └── release.yml                     # ⏳
├── .env.example                            # ✅
├── .pre-commit-config.yaml                 # ✅
├── Makefile                                # ✅
├── .gitignore                              # ✅
├── LICENSE                                 # ✅
├── README.md                               # ✅
├── CONTRIBUTING.md                         # ✅
├── CODE_OF_CONDUCT.md                      # ✅
├── SECURITY.md                             # ✅
└── CHANGELOG.md                            # ✅

**Note on `deploy/`:** the product spec's own non-goals say "focus on
single-machine, single-user scenarios" — Helm/Kubernetes assets are fleet
deployment tooling, which is a deliberate scope expansion beyond the
original spec, made explicitly rather than by accident. This should be
revisited as a real phase (with its own success criteria) once single-machine
mode is solid, not built opportunistically alongside it.

---

## 5. Phased roadmap

**Phase 1 — CLI core (Python only, no services)**
`scan`, `models`, `pull`, `run` — file-based config storage (`~/.llm-max/`).
Proves the core value prop with zero infra dependency.

**Phase 2 — Persistence**
Add MySQL + Flyway for history, Redis for live status. `status` and `recommend`
commands become useful. Docker Compose for local services.

**Phase 3 — Autotuner**
LangGraph-based tuning loop, `tune` and `autopilot` commands, benchmark_runs
+ autopilot_events tables get used for real.

**Phase 4 — Web UI**
Spring Boot backend + agentd + frontend dashboard. Everything in the spec's
"Status & Recommendations" and dashboard sections.

**Phase 5 — Streaming observability (optional)**
Kafka + Schema Registry + Avro schemas for telemetry, Kafka Streams app for
windowed p95/throughput, Prometheus/Grafana integration.

---

## 6. Decisions

| Question | Decision |
|---|---|
| First runtime adapter | **Ollama** (simple REST API, biggest install base) |
| GPU vendor scope, v1 | **NVIDIA only**, via `pynvml` |
| Kafka phase timing | **Not decided yet** — revisit after Phase 1 ships, once we know whether Redis-only status/telemetry actually feels limiting in practice |
| Model catalog source | *Open* — hand-curated JSON vs. live pull from Ollama's model registry |
| Packaging | *Open* — decide after Phase 1, once the dependency footprint (`pynvml`, etc.) is known |

Two open items remain (catalog source, packaging) — low-stakes enough to decide
once Phase 1 code exists rather than up front.