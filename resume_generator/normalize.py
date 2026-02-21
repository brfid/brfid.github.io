"""Normalize JSON Resume data for rendering.

This module converts raw JSON Resume structures into a "view model" that is
stable and convenient for templates (sorted lists, computed date ranges, etc.).
"""

from __future__ import annotations

from datetime import date
from typing import Any, TypeVar, cast

from .types import ProjectItemView, Resume, ResumeView, WorkItemView


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


DateRangeItem = TypeVar("DateRangeItem", WorkItemView, ProjectItemView)


def _add_date_ranges(items: list[DateRangeItem]) -> None:
    """Mutate resume items in place, adding a computed ``dateRange`` display field.

    Args:
        items: List of work or project items.
    """
    for item in items:
        date_range = format_date_range(item.get("startDate"), item.get("endDate"))
        if date_range is not None:
            item["dateRange"] = date_range


def normalize_resume(resume: Resume) -> ResumeView:
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
        # Sort descending by endDate then startDate.
        # Missing endDate (current job) sorts as far future so it appears first.
        end = item.get("endDate") or "9999-12-31"
        start = item.get("startDate") or ""
        return (end, start)

    work_raw = cast(list[dict[str, Any]], (resume.get("work") or []))
    projects_raw = cast(list[dict[str, Any]], (resume.get("projects") or []))
    work = cast(list[WorkItemView], sorted(work_raw, key=_date_key, reverse=True))
    projects = cast(list[ProjectItemView], sorted(projects_raw, key=_date_key, reverse=True))

    # Add computed ranges for templating convenience.
    _add_date_ranges(work)
    _add_date_ranges(projects)

    out = cast(ResumeView, dict(resume))
    out["basics"] = basics
    out["basics"]["profiles"] = profiles
    out["work"] = work
    out["projects"] = projects
    return out
