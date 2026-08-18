"""Canned Ollama REST API response payloads for adapter unit tests.

Shapes match Ollama's actual /api/tags, /api/pull, and /api/generate
responses (as of the Ollama API used in adapters/ollama.py).
"""

from __future__ import annotations

TAGS_RESPONSE = {
    "models": [
        {
            "name": "llama3.1:8b",
            "size": 4900000000,
            "digest": "sha256:abc123",
        },
        {
            "name": "mistral:7b",
            "size": 4100000000,
            "digest": "sha256:def456",
        },
    ]
}

TAGS_RESPONSE_EMPTY = {"models": []}

PULL_STREAM_LINES = [
    b'{"status": "pulling manifest"}',
    b'{"status": "downloading", "completed": 1000, "total": 5000}',
    b'{"status": "downloading", "completed": 5000, "total": 5000}',
    b'{"status": "verifying sha256 digest"}',
    b'{"status": "success"}',
]

GENERATE_RESPONSE = {
    "model": "llama3.1:8b",
    "response": "Hello! I'm an AI assistant.",
    "done": True,
    "eval_count": 42,
    "eval_duration": 2_100_000_000,  # nanoseconds -> 20 tok/s
}

GENERATE_RESPONSE_NO_TIMING = {
    "model": "llama3.1:8b",
    "response": "Hello!",
    "done": True,
    "eval_count": 0,
    "eval_duration": 0,
}