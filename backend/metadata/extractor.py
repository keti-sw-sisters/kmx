from typing import Any


def extract_metadata(record: dict[str, Any]) -> dict[str, Any]:
    keys = list(record.keys())
    numeric_fields = [k for k, v in record.items() if isinstance(v, (int, float))]
    tags = []
    if "temperature" in keys or "vibration" in keys:
        tags.append("predictive-maintenance")
    if "defect_rate" in keys or "inspection_score" in keys:
        tags.append("quality-inspection")
    if "energy_kwh" in keys:
        tags.append("energy-optimization")
    if not tags:
        tags.append("general-manufacturing")

    return {
        "fields": keys,
        "numeric_fields": numeric_fields,
        "semantic_tags": tags,
        "record_count_estimate": 1,
    }
