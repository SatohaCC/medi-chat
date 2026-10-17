"""外部のJSONを標準Python値へ変換する。"""

import json

from ..domain.foundation.json_types import JsonValue


def parse_json_object(value: str) -> dict[str, JsonValue]:
    payload = _json_value(json.loads(value))
    if not isinstance(payload, dict):
        raise TypeError("Stored payload must be a JSON object")
    return payload


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        result: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")
            result[key] = _json_value(item)
        return result
    raise TypeError("Stored payload contains a non-JSON value")
