# Security Policy

## Supported Versions

LLM Max is in early development (pre-1.0). Only the latest commit on `main`
is currently supported with security fixes.

| Version | Supported |
|---|---|
| main (unreleased) | ✅ |
| < 0.1.0 | ❌ |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Instead, use GitHub's private vulnerability reporting:

1. Go to the repository's **Security** tab
2. Click **Report a vulnerability**
3. Provide a description, reproduction steps, and impact assessment

You should expect an initial response within 5 business days. We'll work
with you to understand and address the issue, and will credit you in the
fix (unless you prefer otherwise).

## Scope

Given LLM Max's design, particular attention should be paid to:

- **`adapters/`** — any code that constructs requests to local runtime APIs
  (Ollama, future vLLM/llama.cpp). Injection or SSRF-style issues here are
  high priority.
- **`storage/`** — SQL query construction (currently parameterized; any
  change that introduces string-interpolated SQL is a regression).
- **`telemetry/`** (future) — anything related to what data leaves the
  user's machine. Telemetry is designed to be opt-in and privacy-first;
  any code path that transmits data without explicit consent is a
  vulnerability, not just a bug.

## Non-Goals

LLM Max is a local, single-user tool by default. It does not (yet) expose
network services beyond talking to a local LLM runtime — the local FastAPI
daemon (`agentd/`, planned Phase 4) will bind to localhost only unless a
user explicitly configures otherwise, and that configuration surface will
get its own security review before shipping.