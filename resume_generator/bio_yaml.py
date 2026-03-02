"""Parse brad.bio.txt pipeline output into hugo/data/bio.yaml.

brad.bio.txt format (produced by bradman.c -mode bio):

    Bradley Fidler
    Principal Technical Writer ...

    Summary paragraph text that may span
    multiple lines.

    email@example.com
    https://example.com
    https://linkedin.com/in/...

This module is the canonical parser. The deploy.yml "Generate bio data for Hugo"
step calls this as a CLI: ``python -m resume_generator.bio_yaml <src> <dst>``.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
from typing import TypedDict


class BioData(TypedDict, total=False):
    """Typed dict for Hugo landing page bio data parsed from brad.bio.txt."""

    name: str
    label: str
    summary: str
    about: str
    email: str
    url: str
    linkedin: str
    build_log: bool
    build_id: str


def parse_bio_txt(text: str) -> BioData:
    """Parse brad.bio.txt content into a BioData dict.

    Args:
        text: Contents of brad.bio.txt.

    Returns:
        Dict with name, label, summary, email, url, linkedin fields.
        build_log and build_id are NOT set here — callers add them.
    """
    lines = text.strip().splitlines()

    name = lines[0] if len(lines) > 0 else ""
    label = lines[1] if len(lines) > 1 else ""

    # First blank line at index >= 2 separates summary from contact block.
    try:
        blank1 = next(i for i, ln in enumerate(lines) if i >= 2 and not ln.strip())
    except StopIteration:
        blank1 = len(lines)

    summary = " ".join(ln for ln in lines[2:blank1] if ln.strip())
    contact = [ln for ln in lines[blank1 + 1 :] if ln.strip()]

    return BioData(
        name=name,
        label=label,
        summary=summary,
        email=contact[0] if len(contact) > 0 else "",
        url=contact[1] if len(contact) > 1 else "",
        linkedin=contact[2] if len(contact) > 2 else "",
    )


def _read_about_from_yaml(text: str) -> str:
    """Extract the 'about' field from an existing bio.yaml.

    Handles both block scalar (>-) and quoted string forms so the field
    survives a round-trip whether bio.yaml was hand-edited or written by
    bio_to_yaml.

    Args:
        text: Contents of an existing bio.yaml file.

    Returns:
        The about value as a plain string, or empty string if absent.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not line.startswith("about:"):
            continue
        val = line[len("about:") :].strip()
        if val in (">-", ">"):
            # Block scalar: collect all indented continuation lines.
            block_lines: list[str] = []
            for j in range(i + 1, len(lines)):
                bl = lines[j]
                if bl and not bl[0].isspace():
                    break  # next key starts
                stripped = bl.strip()
                if stripped:
                    block_lines.append(stripped)
            return " ".join(block_lines)
        if val.startswith('"') or val.startswith("'"):
            try:
                return str(json.loads(val))
            except Exception:
                return val.strip("\"'")
        return val
    return ""


def bio_to_yaml(data: BioData) -> str:
    """Serialise a BioData dict to YAML text for hugo/data/bio.yaml.

    Uses json.dumps for quoting (safe superset of YAML scalar quoting for
    simple strings; avoids a PyYAML dependency). The optional ``about``
    field is emitted as a >- block scalar so it is readable when hand-edited.

    Args:
        data: BioData dict, may include optional about / build_log / build_id.

    Returns:
        YAML string.
    """
    lines = [
        f"name: {json.dumps(data.get('name', ''))}",
        f"label: {json.dumps(data.get('label', ''))}",
        f"summary: {json.dumps(data.get('summary', ''))}",
    ]
    if data.get("about"):
        lines.append(f"about: >-\n  {data['about']}")
    lines += [
        f"email: {json.dumps(data.get('email', ''))}",
        f"url: {json.dumps(data.get('url', ''))}",
        f"linkedin: {json.dumps(data.get('linkedin', ''))}",
    ]
    if data.get("build_log"):
        lines.append("build_log: true")
    if data.get("build_id"):
        lines.append(f"build_id: {json.dumps(data['build_id'])}")
    return "\n".join(lines) + "\n"


def _read_build_id(build_log_path: pathlib.Path) -> str:
    """Extract build_id from build.log.html.

    Parses the ``<title>`` element: ``<title>build-ID — ...</title>``.

    Args:
        build_log_path: Path to hugo/static/build.log.html.

    Returns:
        Build ID string, or empty string if not found.
    """
    if not build_log_path.exists():
        return ""
    text = build_log_path.read_text(encoding="utf-8")
    m = re.search(r"<title>(build-[^\s<]+)", text)
    return m.group(1) if m else ""


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: parse bio txt, write bio yaml.

    Usage::

        python -m resume_generator.bio_yaml <src_bio_txt> <dst_bio_yaml> [<build_log_txt>]

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        0 on success, 1 on error.
    """
    args = argv if argv is not None else sys.argv[1:]
    if len(args) < 2:
        print("Usage: bio_yaml <src_bio_txt> <dst_bio_yaml> [<build_log_txt>]", file=sys.stderr)
        return 1

    src = pathlib.Path(args[0])
    dst = pathlib.Path(args[1])
    default_log = pathlib.Path("hugo/static/build.log.html")
    build_log = pathlib.Path(args[2]) if len(args) >= 3 else default_log

    if not src.exists() or src.stat().st_size == 0:
        print(f"bio_yaml: {src} is missing or empty — skipping", file=sys.stderr)
        return 0

    text = src.read_text(encoding="utf-8")
    data = parse_bio_txt(text)

    # Carry forward pipeline-agnostic fields (e.g. 'about') from the
    # existing dst so they survive vintage deploys.
    if dst.exists():
        existing = dst.read_text(encoding="utf-8")
        about = _read_about_from_yaml(existing)
        if about:
            data["about"] = about

    data["build_log"] = True
    build_id = _read_build_id(build_log)
    if build_id:
        data["build_id"] = build_id

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(bio_to_yaml(data), encoding="utf-8")
    print(f"bio_yaml: wrote {dst} (build_id={build_id!r})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
