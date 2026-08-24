# llm-max webui backend

Spring Boot REST API for the (future) web UI frontend. Calls `agentd` for
all actions — this layer never talks to `llm_max` core directly.

## Not yet compiled/tested by me

Every other package in this repo (`core/`, `agentd/`) was actually
installed, run, and tested in a sandboxed environment before being handed
to you. This one wasn't — Maven Central (`repo.maven.apache.org`) is
blocked by the sandbox's network policy (403 Forbidden), so `mvn compile`
could not run here. The code was written carefully and reviewed by hand
(in particular the Jackson snake_case-to-camelCase mapping between
agentd's Python JSON and these Java DTOs, and the RestClient/timeout
wiring), but you are the first real compile of this code. Run the
commands below and paste back whatever fails.

## Run

\`\`\`bash
cd webui/backend
mvn spring-boot:run
\`\`\`

Or build a jar first:
\`\`\`bash
mvn clean package
java -jar target/webui-backend-0.1.0.jar
\`\`\`

Requires `agentd` running separately (default expected at
`http://127.0.0.1:8000` — override with the `AGENTD_URL` env var).

## Test

\`\`\`bash
mvn test
\`\`\`

## Endpoints

| Method | Path | Calls agentd |
|---|---|---|
| GET | `/api/hardware/scan` | `GET /hardware/scan` |
| GET | `/api/models` | `GET /models` |
| GET | `/api/status` | `GET /status` |
| GET | `/api/history?modelId=&limit=` | `GET /history` |
| POST | `/api/models/{id}/run` | `POST /models/{id}/run` |
| POST | `/api/models/{id}/tune` | `POST /models/{id}/tune` |
| GET | `/api/autopilot/{id}/status` | `GET /autopilot/{id}/status` |
| POST | `/api/autopilot/{id}/disable` | `POST /autopilot/{id}/disable` |

Not yet implemented: `/models/{id}/pull` (streaming proxy — deferred) and
`autopilot enable` (deliberately excluded, matching agentd's own scoping).

## Error handling

- agentd unreachable at all: `502 Bad Gateway`, `{"error": "..."}`
- agentd returns its own error (e.g. 503 Ollama not running, 404 no tuned
  config): that status code and agentd's own message pass straight through.