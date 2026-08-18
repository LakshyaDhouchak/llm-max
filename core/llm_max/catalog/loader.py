from __future__ import annotations

import json
from importlib import resources

from llm_max.catalog.validators import validate_catalog_entries
from llm_max.domain import ModelSpec


def load_catalog() -> list[ModelSpec]:
    """Load and validate the curated model catalog from models.json."""
    raw = resources.files("llm_max.catalog").joinpath("models.json").read_text()
    entries = json.loads(raw)
    validate_catalog_entries(entries)
    return [ModelSpec(**entry) for entry in entries]