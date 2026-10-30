import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
FIELD_DICTIONARY_PATH = ROOT_DIR / "data" / "control_plane" / "field_dictionary.json"


@lru_cache(maxsize=1)
def _load_field_dictionary() -> dict[str, Any]:
    if not FIELD_DICTIONARY_PATH.exists():
        return {}
    with FIELD_DICTIONARY_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _build_alias_index(field_dictionary: dict[str, Any]) -> dict[str, str]:
    alias_index: dict[str, str] = {}
    alias_groups = field_dictionary.get("normalization_rules", {}).get("alias_groups", [])
    for group in alias_groups:
        canonical = group.get("canonical_field")
        if not canonical:
            continue
        alias_index[canonical] = canonical
        for alias in group.get("aliases", []):
            alias_index[str(alias)] = canonical

    for field in field_dictionary.get("fields", []):
        canonical = field.get("field_id")
        if not canonical:
            continue
        alias_index[canonical] = canonical
        for alias in field.get("aliases", []):
            alias_index[str(alias)] = canonical
    return alias_index


def _build_semantic_tag_map(field_dictionary: dict[str, Any]) -> dict[str, list[str]]:
    tag_map: dict[str, list[str]] = {}
    for field in field_dictionary.get("fields", []):
        canonical = field.get("field_id")
        tags = field.get("tags", [])
        if canonical and tags:
            tag_map[canonical] = [str(tag) for tag in tags]
    return tag_map


def extract_metadata(record: dict[str, Any]) -> dict[str, Any]:
    field_dictionary = _load_field_dictionary()
    alias_index = _build_alias_index(field_dictionary)
    semantic_tag_map = _build_semantic_tag_map(field_dictionary)

    original_fields = list(record.keys())
    canonical_fields = [alias_index.get(field, field) for field in original_fields]
    normalized_record = {
        alias_index.get(field, field): value for field, value in record.items()
    }

    numeric_fields = [
        field for field, value in normalized_record.items() if isinstance(value, (int, float))
    ]

    tags: set[str] = set()
    for field in canonical_fields:
        for tag in semantic_tag_map.get(field, []):
            tags.add(tag)

    if not tags:
        if any("temp" in field or "vibration" in field for field in canonical_fields):
            tags.add("predictive-maintenance")
        if any("defect" in field or "inspection" in field for field in canonical_fields):
            tags.add("quality-inspection")
        if any("energy" in field for field in canonical_fields):
            tags.add("energy-optimization")
        if not tags:
            tags.add("general-manufacturing")

    return {
        "fields": canonical_fields,
        "original_fields": original_fields,
        "numeric_fields": numeric_fields,
        "semantic_tags": sorted(tags),
        "record_count_estimate": 1,
    }
