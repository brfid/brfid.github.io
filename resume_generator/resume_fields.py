"""Small helpers for reading JSON Resume fields safely."""

from __future__ import annotations

from collections.abc import Mapping
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


def get_profile_url(basics: Mapping[str, Any], network: str) -> str | None:
    """Return the URL for a specific `basics.profiles[].network` entry.

    Args:
        basics: `resume["basics"]` mapping.
        network: Profile network name (case-insensitive), e.g. "LinkedIn".

    Returns:
        The first matching profile URL, or None.
    """
    profiles = basics.get("profiles") or []
    if not isinstance(profiles, list):
        return None
    network_lower = network.strip().lower()
    for profile in profiles:
        if not isinstance(profile, Mapping):
            continue
        if str(profile.get("network") or "").strip().lower() != network_lower:
            continue
        url = safe_str(profile.get("url"))
        if url:
            return url
    return None
