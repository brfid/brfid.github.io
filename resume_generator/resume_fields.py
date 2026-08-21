"""Small helpers for reading JSON Resume / site fields safely."""

from __future__ import annotations

from typing import Any


def safe_str(value: Any) -> str | None:
    """Normalize a value into a trimmed string.

    Args:
        value: Any value from a parsed resume structure.

    Returns:
        Trimmed string, or None if the value is missing/empty.
    """
    if value is None:
        return None
    text = str(value).strip()
    return text or None
