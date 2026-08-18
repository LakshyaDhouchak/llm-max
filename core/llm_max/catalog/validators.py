from __future__ import annotations

_REQUIRED_FIELDS = {
    "id",
    "display_name",
    "family",
    "param_size_b",
    "min_vram_mb",
    "recommended_vram_mb",
    "min_ram_mb",
}


class CatalogValidationError(ValueError):
    """Raised when a catalog entry is missing fields or has inconsistent values."""


def validate_catalog_entries(entries: list[dict]) -> None:
    """Validate raw catalog JSON before it's parsed into ModelSpec objects.

    Catches authoring mistakes early (missing fields, impossible VRAM ranges,
    duplicate ids) rather than letting them surface as confusing runtime bugs
    in the compatibility estimator.
    """
    seen_ids: set[str] = set()

    for i, entry in enumerate(entries):
        missing = _REQUIRED_FIELDS - entry.keys()
        if missing:
            raise CatalogValidationError(
                f"Catalog entry #{i} ({entry.get('id', '?')}) missing "
                f"required fields: {sorted(missing)}"
            )

        entry_id = entry["id"]
        if entry_id in seen_ids:
            raise CatalogValidationError(f"Duplicate catalog id: {entry_id!r}")
        seen_ids.add(entry_id)

        if entry["recommended_vram_mb"] < entry["min_vram_mb"]:
            raise CatalogValidationError(
                f"{entry_id}: recommended_vram_mb "
                f"({entry['recommended_vram_mb']}) is less than min_vram_mb "
                f"({entry['min_vram_mb']})"
            )

        if entry["param_size_b"] <= 0:
            raise CatalogValidationError(f"{entry_id}: param_size_b must be > 0")