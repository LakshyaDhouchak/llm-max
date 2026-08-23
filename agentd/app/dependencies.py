"""FastAPI dependency providers.

Thin wrappers around llm_max core factories (get_storage, OllamaAdapter,
scan_hardware) so routes declare what they need via Depends() rather than
importing and constructing these directly — this is what makes route tests
able to override a single dependency (e.g. swap in a fake adapter) without
monkeypatching internals.
"""

from __future__ import annotations

from llm_max.adapters.base import RuntimeAdapter
from llm_max.adapters.ollama import OllamaAdapter
from llm_max.storage import get_storage as _get_storage
from llm_max.storage.base import Storage


def get_adapter() -> RuntimeAdapter:
    return OllamaAdapter()


def get_storage() -> Storage:
    return _get_storage()