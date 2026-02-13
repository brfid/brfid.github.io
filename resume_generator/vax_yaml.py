"""Emit standard YAML from a JSON Resume input for VAX processing.

The VAX-side program (`vax/bradman.c`) now parses standard YAML including:
- Unquoted strings (default for simple values)
- Quoted strings (when containing YAML special characters)
- Lists with '-' markers
- Nested mappings

This module generates clean, readable YAML that is both human-friendly and VAX-compatible.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any, cast

from .normalize import format_date_range
from .resume_fields import get_profile_url, safe_str
from .types import Resume

_WHITESPACE_RE = re.compile(r"\s+")


def _flatten_whitespace(value: str) -> str:
    """Collapse all whitespace to single spaces and strip ends."""
    return _WHITESPACE_RE.sub(" ", value).strip()


def _needs_quoting(value: str) -> bool:
    """Check if a string needs quoting for YAML.

    Strings need quoting if they contain YAML special characters:
    - Quotes or backslashes (need escaping)
    - : followed by space (key indicator)
    - # (comment)
    - [ ] { } , (flow indicators)
    - Leading/trailing whitespace

    Args:
        value: String to check.

    Returns:
        True if quoting is required, False if can be unquoted.
    """
    if not value:
        return True
    # Check for leading/trailing whitespace
    if value != value.strip():
        return True
    # Check for characters that need escaping
    if '"' in value or '\\' in value:
        return True
    # Check for YAML special chars that require quoting
    if '#' in value or '[' in value or ']' in value:
        return True
    if '{' in value or '}' in value or ',' in value:
        return True
    # Check for colon followed by space (key indicator)
    if ': ' in value or ':\t' in value:
        return True
    # Check if ends with colon
    if value.endswith(':'):
        return True
    return False


def _quote_vax_yaml_string(value: str) -> str:
    r"""Quote a string if required by YAML syntax.

    Now supports both quoted and unquoted strings:
    - Unquoted if safe (no YAML special characters)
    - Quoted if contains special characters like `: ` or `#`
    - Single-line strings only (no embedded newlines)
    - Escaped `\\` and `"` in quoted strings

    Args:
        value: Raw string.

    Returns:
        A YAML scalar, quoted or unquoted as needed.
    """
    flattened = _flatten_whitespace(value)
    if not _needs_quoting(flattened):
        return flattened
    # Quote and escape
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


def _build_contact(basics: Mapping[str, Any]) -> dict[str, str]:
    contact: dict[str, str] = {}
    email = safe_str(basics.get("email"))
    if email:
        contact["email"] = email

    url = get_profile_url(basics, "Personal") or safe_str(basics.get("url"))
    if url:
        contact["url"] = url

    linkedin = get_profile_url(basics, "LinkedIn")
    if linkedin:
        contact["linkedin"] = linkedin
    return contact


def _build_work_items(resume: Resume, opts: VaxYamlEmitOptions) -> list[dict[str, Any]]:
    work_items_raw = cast(list[Mapping[str, Any]], (resume.get("work") or []))
    out: list[dict[str, Any]] = []
    for item in work_items_raw:
        company = safe_str(item.get("name")) or safe_str(item.get("company"))
        position = safe_str(item.get("position"))
        if not company and not position:
            continue

        date_range = format_date_range(
            safe_str(item.get("startDate")),
            safe_str(item.get("endDate")),
        )
        location = safe_str(item.get("location"))

        highlights: list[str] = []
        highlights_raw = item.get("highlights") or []
        if isinstance(highlights_raw, list):
            for hl in highlights_raw:
                text = safe_str(hl)
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

        out.append(work_out)
        if len(out) >= opts.max_work_items:
            break
    return out


def _build_skills(resume: Resume, opts: VaxYamlEmitOptions) -> list[dict[str, Any]]:
    skills_raw = cast(list[Mapping[str, Any]], (resume.get("skills") or []))
    out: list[dict[str, Any]] = []
    for skill in skills_raw:
        group = safe_str(skill.get("name")) or safe_str(skill.get("group"))
        if not group:
            continue

        keywords: list[str] = []
        keywords_raw = skill.get("keywords") or []
        if isinstance(keywords_raw, list):
            for kw in keywords_raw:
                text = safe_str(kw)
                if text:
                    keywords.append(text)

        out_skill: dict[str, Any] = {"group": group}
        if keywords:
            out_skill["keywords"] = keywords[: opts.max_skill_keywords]
        out.append(out_skill)
        if len(out) >= opts.max_skill_groups:
            break
    return out


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

    name = safe_str(basics.get("name")) or ""
    label = safe_str(basics.get("label")) or ""
    summary = safe_str(basics.get("summary")) or ""

    out: dict[str, Any] = {
        "schemaVersion": opts.schema_version,
        "buildDate": build_date.isoformat(),
        "name": name,
        "label": label,
        "summary": summary,
    }

    contact = _build_contact(basics)
    if contact:
        out["contact"] = contact

    work_items = _build_work_items(resume, opts)
    if work_items:
        out["work"] = work_items

    skills = _build_skills(resume, opts)
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
