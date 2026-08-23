"""agentd — local HTTP daemon wrapping llm_max core.

Binds to localhost by default (see the uvicorn command in README) — this
is deliberately not a public-facing service. See SECURITY.md's note on
agentd's non-goals.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import actions, hardware, recommendations, status

app = FastAPI(
    title="llm-max agentd",
    description="Local HTTP wrapper around the llm-max core library, for the Phase 4 web UI.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hardware.router)
app.include_router(status.router)
app.include_router(actions.router)
app.include_router(recommendations.router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}