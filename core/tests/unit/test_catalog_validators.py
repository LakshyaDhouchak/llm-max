import pytest

from llm_max.catalog.validators import CatalogValidationError, validate_catalog_entries

VALID_ENTRY = {
    "id": "test:1b",
    "display_name": "Test 1B",
    "family": "test",
    "param_size_b": 1,
    "min_vram_mb": 2000,
    "recommended_vram_mb": 3000,
    "min_ram_mb": 4000,
}


def test_valid_entries_pass():
    validate_catalog_entries([VALID_ENTRY])  # should not raise


def test_missing_required_field_raises():
    entry = {k: v for k, v in VALID_ENTRY.items() if k != "min_vram_mb"}
    with pytest.raises(CatalogValidationError, match="missing required fields"):
        validate_catalog_entries([entry])


def test_duplicate_id_raises():
    with pytest.raises(CatalogValidationError, match="Duplicate catalog id"):
        validate_catalog_entries([VALID_ENTRY, dict(VALID_ENTRY)])


def test_recommended_below_min_vram_raises():
    entry = dict(VALID_ENTRY, min_vram_mb=5000, recommended_vram_mb=3000)
    with pytest.raises(CatalogValidationError, match="recommended_vram_mb"):
        validate_catalog_entries([entry])


def test_zero_param_size_raises():
    entry = dict(VALID_ENTRY, param_size_b=0)
    with pytest.raises(CatalogValidationError, match="param_size_b must be > 0"):
        validate_catalog_entries([entry])


def test_real_catalog_file_is_valid():
    """The actual shipped models.json must always pass validation."""
    from llm_max.catalog import load_catalog

    models = load_catalog()
    assert len(models) > 0