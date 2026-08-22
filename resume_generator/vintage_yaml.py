"""Emit the fixed five-scalar YAML document consumed by the VAX guest."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from .vintage_contract import vintage_input_from_mappings

VINTAGE_SCHEMA_VERSION = "v1"
VINTAGE_KEYS = (
    "schemaVersion",
    "buildDate",
    "bioName",
    "bioHeadline",
    "bioProfile",
)


def _quoted_ascii_scalar(value: str, *, key: str) -> str:
    """Return one guest-safe quoted scalar from an ASCII, single-line string."""
    if not value:
        raise ValueError(f"{key} must not be empty")
    if not value.isascii():
        raise ValueError(f"{key} must contain ASCII only")
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise ValueError(f"{key} must be a single printable line")
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def build_vintage_bio(
    site: Mapping[str, Any],
    resume: Mapping[str, Any],
    *,
    build_date: date,
) -> dict[str, str]:
    """Build the guest mapping from public identity and resume data."""
    source = vintage_input_from_mappings(site, resume)
    return {
        "schemaVersion": VINTAGE_SCHEMA_VERSION,
        "buildDate": build_date.isoformat(),
        "bioName": source.name,
        "bioHeadline": source.headline,
        "bioProfile": source.summary,
    }


def emit_vintage_yaml(value: Mapping[str, Any]) -> str:
    """Serialize the guest mapping in its required key order."""
    actual_keys = set(value)
    required_keys = set(VINTAGE_KEYS)
    if actual_keys != required_keys:
        missing = sorted(required_keys - actual_keys)
        extra = sorted(actual_keys - required_keys)
        raise ValueError(f"vintage input keys do not match contract (missing={missing}, extra={extra})")

    lines: list[str] = []
    for key in VINTAGE_KEYS:
        scalar = value[key]
        if not isinstance(scalar, str):
            raise TypeError(f"{key} must be a string, got {type(scalar).__name__}")
        lines.append(f"{key}: {_quoted_ascii_scalar(scalar, key=key)}")
    return "\n".join(lines) + "\n"
