"""Common helpers for safely reading untyped JSON payload structures."""

from __future__ import annotations

from backend.domain.foundation.json_types import JsonValue


def _object(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise TypeError("Expected a JSON object")
    return value


def _string(value: JsonValue) -> str:
    if not isinstance(value, str):
        raise TypeError("Expected a JSON string")
    return value


def _optional_text(value: JsonValue) -> str | None:
    if value is None:
        return None
    text = _string(value)
    return text if text.strip() else None


def _optional_name_text(value: JsonValue) -> str | None:
    """任意名称の不在を識別し、実在する原表記は変更しない。"""
    if value is None:
        return None
    text = _string(value)
    return text if text.strip() else None


def _strings(value: JsonValue) -> list[str]:
    if not isinstance(value, list):
        raise TypeError("Expected a JSON array")
    return [_string(item) for item in value]


def _objects(value: JsonValue) -> list[dict[str, JsonValue]]:
    if not isinstance(value, list):
        raise TypeError("Expected a JSON array")
    return [_object(item) for item in value]


def _string_object(value: JsonValue) -> dict[str, str]:
    return {key: _string(item) for key, item in _object(value).items()}
