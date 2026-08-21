"""Emit standard YAML for the vintage bio pipeline.

The landing-page bio is the sole vintage artifact: the resume no longer passes
through the VAX/PDP-11 pipeline (it is rendered by Hugo + Playwright instead).
This module turns the public `site.yaml` fields into the small ASCII YAML subset
that `vintage/machines/vax/bradman.c` parses to compose the bio for the PDP-11
to typeset.

The vintage-side program parses standard YAML including:
- Unquoted strings (default for simple values)
- Quoted strings (when containing YAML special characters)
- Lists with '-' markers
- Nested mappings

The dumper below stays general (lists/mappings supported) even though the bio
subset is currently flat, so the contract can grow without reworking the emitter.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from datetime import date
from typing import Any, cast

from .normalize import to_ascii
from .resume_fields import safe_str

_LINE_BREAK_RE = re.compile(r"[\t\r\n]+")


def _flatten_whitespace(value: str) -> str:
    """Make a scalar single-line while preserving intentional inline spaces."""
    return _LINE_BREAK_RE.sub(" ", value).strip()


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
    # Check for empty or whitespace issues
    if not value or value != value.strip():
        return True
    # Check for characters that need escaping or YAML special chars
    special_chars = ('"', "\\", "#", "[", "]", "{", "}", ",")
    if any(c in value for c in special_chars):
        return True
    # Check for colon followed by space (key indicator) or trailing colon
    return ": " in value or ":\t" in value or value.endswith(":")


def _quote_vintage_yaml_string(value: str) -> str:
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
    flattened = _flatten_whitespace(to_ascii(value))
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
            lines.append(f"{_indent(level)}{key}: {_quote_vintage_yaml_string(value)}")
        elif value is None:
            # Omit None values entirely in the caller; this is defensive.
            continue
        else:
            raise TypeError(f"Unsupported vintage-YAML scalar type for key {key!r}: {type(value)}")
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
            lines.append(f"{_indent(level)}- {_quote_vintage_yaml_string(value)}")
        else:
            raise TypeError(f"Unsupported vintage-YAML list item type: {type(value)}")
    return lines


def build_vintage_bio(
    site: Mapping[str, Any],
    resume: Mapping[str, Any],
    *,
    build_date: date,
    schema_version: str = "v1",
) -> Mapping[str, Any]:
    """Build the bio-only vintage-YAML structure for the landing bio.

    Identity (name, headline) comes from the public `site.yaml`; the bio text
    comes from `resume.yaml`'s `basics.summary`, shared by the landing page,
    resume Summary, and PDF. The rest of the resume document never enters this
    pipeline. Output carries only the fields bradman.c needs to compose the bio.

    Args:
        site: Public landing-page identity parsed from `site.yaml`.
        resume: Parsed `resume.yaml`; only `basics.summary` is read.
        build_date: Build date to embed for reproducibility.
        schema_version: vintage-YAML schema tag.

    Returns:
        A mapping containing only supported scalar/string types.
    """
    out: dict[str, Any] = {
        "schemaVersion": schema_version,
        "buildDate": build_date.isoformat(),
    }

    bio_name = safe_str(site.get("name"))
    bio_headline = safe_str(site.get("headline"))
    basics = resume.get("basics")
    bio_profile = safe_str(basics.get("summary")) if isinstance(basics, Mapping) else None

    if bio_name:
        out["bioName"] = bio_name
    if bio_headline:
        out["bioHeadline"] = bio_headline
    if bio_profile:
        out["bioProfile"] = bio_profile
    return out


def emit_vintage_yaml(value: Mapping[str, Any]) -> str:
    """Emit a vintage-YAML subset document.

    Args:
        value: Mapping produced by `build_vintage_bio`.

    Returns:
        YAML text with LF newlines and a trailing newline.
    """
    # Force stable key ordering by explicit item list.
    ordered_keys = [
        "schemaVersion",
        "buildDate",
        "bioName",
        "bioHeadline",
        "bioProfile",
    ]
    items: list[tuple[str, Any]] = []
    for key in ordered_keys:
        if key in value and value[key] is not None:
            items.append((key, value[key]))

    lines = _dump_mapping(items, level=0)
    text = "\n".join(lines) + "\n"

    if "\t" in text:
        raise ValueError("vintage-YAML output contains a tab character")
    if "\r" in text:
        raise ValueError("vintage-YAML output contains CR characters (must be LF-only)")
    if not text.isascii():
        raise ValueError("vintage-YAML output contains non-ASCII characters")
    return text
