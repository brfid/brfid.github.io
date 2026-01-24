"""Normalize JSON Resume data for rendering.

This module converts raw JSON Resume structures into a "view model" that is
stable and convenient for templates (sorted lists, computed date ranges, etc.).
"""

from __future__ import annotations

from datetime import date
from typing import Any


def _parse_iso_date(value: str | None) -> date | None:
    """Parse a YYYY-MM-DD date string into a `date`.

    Args:
        value: ISO date string (typically YYYY-MM-DD) or None.

    Returns:
        A `date` if parsing succeeds; otherwise None.
    """
    if not value:
        return None
    try:
        # JSON Resume typically uses YYYY-MM-DD.
        return date.fromisoformat(value)
    except ValueError:
        return None


def _format_month_year(value: date | None) -> str | None:
    """Format a date into a short month/year string.

    Args:
        value: Parsed date or None.

    Returns:
        String like "Jan 2026", or None.
    """
    if not value:
        return None
    return value.strftime("%b %Y")


def format_date_range(start: str | None, end: str | None) -> str | None:
    """Create a human-friendly date range string for resume items.

    This prefers month/year formatting when values parse as ISO dates, and falls
    back to the raw string otherwise.

    Args:
        start: Start date string or None.
        end: End date string or None.

    Returns:
        A formatted date range, or None if both are missing.
    """
    start_d = _parse_iso_date(start)
    end_d = _parse_iso_date(end)
    start_s = _format_month_year(start_d) or start
    end_s = _format_month_year(end_d) or end

    if start_s and end_s:
        return f"{start_s} – {end_s}"
    if start_s and not end_s:
        return f"{start_s} – Present"
    if not start_s and end_s:
        return f"Until {end_s}"
    return None


def normalize_resume(resume: dict[str, Any]) -> dict[str, Any]:
    """Normalize a JSON Resume dict for rendering.

    Current behaviors:
    - Ensures `basics.profiles` is a list of dicts.
    - Sorts `work` and `projects` in reverse chronological order (best-effort).
    - Adds `dateRange` to `work` and `projects` items for templates.

    Args:
        resume: Raw JSON Resume dictionary.

    Returns:
        A normalized resume dictionary safe for templating.
    """
    basics = resume.get("basics") or {}

    profiles = basics.get("profiles") or []
    profiles = [p for p in profiles if isinstance(p, dict)]

    def _date_key(item: dict[str, Any]) -> tuple[str, str]:
        # Sort descending by endDate then startDate; missing dates sort last.
        end = item.get("endDate") or ""
        start = item.get("startDate") or ""
        return (end, start)

    work = sorted((resume.get("work") or []), key=_date_key, reverse=True)
    projects = sorted((resume.get("projects") or []), key=_date_key, reverse=True)

    # Add computed ranges for templating convenience.
    for item in work:
        if isinstance(item, dict):
            item["dateRange"] = format_date_range(item.get("startDate"), item.get("endDate"))
    for item in projects:
        if isinstance(item, dict):
            item["dateRange"] = format_date_range(item.get("startDate"), item.get("endDate"))

    out: dict[str, Any] = dict(resume)
    out["basics"] = basics
    out["basics"]["profiles"] = profiles
    out["work"] = work
    out["projects"] = projects
    return out
