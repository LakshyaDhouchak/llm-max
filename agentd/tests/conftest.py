"""Shared fixtures for agentd route tests.

Imports the shared fakes from llm_max.testing.fakes — the one real copy,
also used by core's own test suite (see core/tests/fakes/*.py, which are
thin re-export shims pointing here). Nothing agentd-specific needed: this
is a normal package import, with no risk of colliding with core's `tests`
package, since llm_max.testing lives inside the properly namespaced,
already-installed llm_max package rather than under any `tests/` folder.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from llm_max.testing.fakes import FakeOllamaAdapter, InMemoryStorage

from app.dependencies import get_adapter, get_storage
from app.main import app


@pytest.fixture
def fake_adapter():
    return FakeOllamaAdapter()


@pytest.fixture
def fake_storage():
    return InMemoryStorage()


@pytest.fixture
def client(fake_adapter, fake_storage):
    app.dependency_overrides[get_adapter] = lambda: fake_adapter
    app.dependency_overrides[get_storage] = lambda: fake_storage
    yield TestClient(app)
    app.dependency_overrides.clear()