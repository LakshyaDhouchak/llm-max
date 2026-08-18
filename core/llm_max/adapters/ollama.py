"""Adapter for Ollama's local REST API (default: http://localhost:11434).

Ollama API reference (subset used here):
  GET  /api/tags          -> list installed models
  POST /api/pull          -> pull a model (streamed NDJSON progress)
  POST /api/generate      -> run a prompt (non-chat, simplest path for v1)
"""

from __future__ import annotations

import time
from collections.abc import Iterator

import requests

from llm_max.adapters.base import RuntimeAdapter
from llm_max.domain import InstalledModel

DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaAdapter(RuntimeAdapter):
    name = "ollama"

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def list_installed(self) -> list[InstalledModel]:
        resp = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return [
            InstalledModel(
                id=m["name"],
                size_mb=m.get("size", 0) // (1024 * 1024) if m.get("size") else None,
                digest=m.get("digest"),
            )
            for m in data.get("models", [])
        ]

    def pull(self, model_id: str) -> Iterator[dict]:
        with requests.post(
            f"{self.base_url}/api/pull",
            json={"name": model_id, "stream": True},
            stream=True,
            timeout=None,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                import json

                yield json.loads(line)

    def run(self, model_id: str, prompt: str, options: dict | None = None) -> dict:
        payload = {
            "model": model_id,
            "prompt": prompt,
            "stream": False,
        }
        if options:
            payload["options"] = options

        start = time.perf_counter()
        resp = requests.post(
            f"{self.base_url}/api/generate", json=payload, timeout=None
        )
        elapsed_s = time.perf_counter() - start
        resp.raise_for_status()
        data = resp.json()

        eval_count = data.get("eval_count", 0)
        eval_duration_ns = data.get("eval_duration", 0)
        tokens_per_sec = (
            eval_count / (eval_duration_ns / 1e9) if eval_duration_ns else None
        )

        return {
            "response": data.get("response", ""),
            "total_duration_s": round(elapsed_s, 3),
            "tokens_generated": eval_count,
            "tokens_per_sec": round(tokens_per_sec, 2) if tokens_per_sec else None,
            "raw": data,
        }