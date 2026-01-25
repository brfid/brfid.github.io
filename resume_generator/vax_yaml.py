"""Emit a constrained, VAX-friendly YAML subset from a JSON Resume input.

The VAX-side program (`vax/bradman.c`) parses only a tiny subset of YAML. This module
generates that subset deterministically so the guest does not need a full YAML library.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any, cast

from .normalize import format_date_range
from .types import Resume

_WHITESPACE_RE = re.compile(r"\s+")


def _flatten_whitespace(value: str) -> str:
    """Collapse all whitespace to single spaces and strip ends."""
    return _WHITESPACE_RE.sub(" ", value).strip()


def _quote_vax_yaml_string(value: str) -> str:
    """Quote a string as required by the VAX-YAML subset.

    The subset requires:
    - Double-quoted scalars only
    - Single-line strings only (no embedded newlines)
    - Escaped `\\` and `"`

    Args:
        value: Raw string.

    Returns:
        A YAML scalar like `"Hello \"world\""` (including surrounding quotes).
    """
    flattened = _flatten_whitespace(value)
    escaped = flattened.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _indent(level: int) -> str:
    return " " * (2 * level)


def _dump_mapping(items: Iterable[tuple[str, Any]], *, level: int) -> list[str]:
    lines: list[str] = []
    for key, value in items:
        if isinstance(value, Mapping):
            lines.append(f"{_indent(level)}{key}:")
            lines.extend(_dump_mapping(cast(Mapping[str, Any], value).items(), level=level + 1))
        elif isinstance(value, list):
            lines.append(f"{_indent(level)}{key}:")
            lines.extend(_dump_list(value, level=level + 1))
        elif isinstance(value, str):
            lines.append(f"{_indent(level)}{key}: {_quote_vax_yaml_string(value)}")
        elif value is None:
            # Omit None values entirely in the caller; this is defensive.
            continue
        else:
            raise TypeError(f"Unsupported VAX-YAML scalar type for key {key!r}: {type(value)}")
    return lines


def _dump_list(values: list[Any], *, level: int) -> list[str]:
    lines: list[str] = []
    for value in values:
        if isinstance(value, Mapping):
            lines.append(f"{_indent(level)}-")
            lines.extend(_dump_mapping(cast(Mapping[str, Any], value).items(), level=level + 1))
        elif isinstance(value, list):
            lines.append(f"{_indent(level)}-")
            lines.extend(_dump_list(value, level=level + 1))
        elif isinstance(value, str):
            lines.append(f"{_indent(level)}- {_quote_vax_yaml_string(value)}")
        else:
            raise TypeError(f"Unsupported VAX-YAML list item type: {type(value)}")
    return lines


@dataclass(frozen=True)
class VaxYamlEmitOptions:
    """Options controlling what fields are emitted."""

    schema_version: str = "v1"
    max_work_items: int = 6
    max_work_highlights: int = 2
    max_skill_groups: int = 5
    max_skill_keywords: int = 8


def _get_profile_url(basics: Mapping[str, Any], network: str) -> str | None:
    profiles = basics.get("profiles") or []
    if not isinstance(profiles, list):
        return None
    for profile in profiles:
        if not isinstance(profile, Mapping):
            continue
        if str(profile.get("network") or "").strip().lower() != network.lower():
            continue
        url = str(profile.get("url") or "").strip()
        if url:
            return url
    return None


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_vax_resume_v1(
    resume: Resume,
    *,
    build_date: date,
    options: VaxYamlEmitOptions | None = None,
) -> Mapping[str, Any]:
    """Build the VAX-YAML v1 data structure from a JSON Resume dict.

    Args:
        resume: Parsed JSON Resume dict (from `resume.yaml`).
        build_date: Build date to embed for reproducibility.
        options: Optional emission limits.

    Returns:
        A nested mapping/list structure containing only supported subset types.
    """
    opts = options or VaxYamlEmitOptions()

    basics = cast(Mapping[str, Any], (resume.get("basics") or {}))

    name = _safe_str(basics.get("name")) or ""
    label = _safe_str(basics.get("label")) or ""
    summary = _safe_str(basics.get("summary")) or ""

    contact: dict[str, str] = {}
    email = _safe_str(basics.get("email"))
    if email:
        contact["email"] = email
    url = _get_profile_url(basics, "Personal") or _safe_str(basics.get("url"))
    if url:
        contact["url"] = url
    linkedin = _get_profile_url(basics, "LinkedIn")
    if linkedin:
        contact["linkedin"] = linkedin

    work_items_raw = cast(list[Mapping[str, Any]], (resume.get("work") or []))
    work_items: list[dict[str, Any]] = []
    for item in work_items_raw:
        company = _safe_str(item.get("name")) or _safe_str(item.get("company"))
        position = _safe_str(item.get("position"))
        if not company and not position:
            continue

        date_range = format_date_range(
            _safe_str(item.get("startDate")),
            _safe_str(item.get("endDate")),
        )
        location = _safe_str(item.get("location"))

        highlights_raw = item.get("highlights") or []
        highlights: list[str] = []
        if isinstance(highlights_raw, list):
            for hl in highlights_raw:
                text = _safe_str(hl)
                if text:
                    highlights.append(text)

        work_out: dict[str, Any] = {}
        if company:
            work_out["company"] = company
        if position:
            work_out["position"] = position
        if date_range:
            work_out["dateRange"] = date_range
        if location:
            work_out["location"] = location
        if highlights:
            work_out["highlights"] = highlights[: opts.max_work_highlights]
        work_items.append(work_out)
        if len(work_items) >= opts.max_work_items:
            break

    skills_raw = cast(list[Mapping[str, Any]], (resume.get("skills") or []))
    skills: list[dict[str, Any]] = []
    for skill in skills_raw:
        group = _safe_str(skill.get("name")) or _safe_str(skill.get("group"))
        if not group:
            continue
        keywords_raw = skill.get("keywords") or []
        keywords: list[str] = []
        if isinstance(keywords_raw, list):
            for kw in keywords_raw:
                text = _safe_str(kw)
                if text:
                    keywords.append(text)
        out_skill: dict[str, Any] = {"group": group}
        if keywords:
            out_skill["keywords"] = keywords[: opts.max_skill_keywords]
        skills.append(out_skill)
        if len(skills) >= opts.max_skill_groups:
            break

    out: dict[str, Any] = {
        "schemaVersion": opts.schema_version,
        "buildDate": build_date.isoformat(),
        "name": name,
        "label": label,
        "summary": summary,
    }
    if contact:
        out["contact"] = contact
    if work_items:
        out["work"] = work_items
    if skills:
        out["skills"] = skills
    return out


def emit_vax_yaml(value: Mapping[str, Any]) -> str:
    """Emit a VAX-YAML subset document.

    Args:
        value: Mapping produced by `build_vax_resume_v1`.

    Returns:
        YAML text with LF newlines and a trailing newline.
    """
    # Force stable key ordering by explicit item list.
    ordered_keys = [
        "schemaVersion",
        "buildDate",
        "name",
        "label",
        "contact",
        "summary",
        "work",
        "skills",
    ]
    items: list[tuple[str, Any]] = []
    for key in ordered_keys:
        if key in value and value[key] is not None:
            items.append((key, value[key]))

    lines = _dump_mapping(items, level=0)
    text = "\n".join(lines) + "\n"

    if "\t" in text:
        raise ValueError("VAX-YAML output contains a tab character")
    if "\r" in text:
        raise ValueError("VAX-YAML output contains CR characters (must be LF-only)")
    return text
