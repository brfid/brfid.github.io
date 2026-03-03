"""Parse brad.bio.txt pipeline output into hugo/data/bio.yaml.

brad.bio.txt format (produced by bradman.c -mode bio):

    Bradley Fidler
    Principal Technical Writer ...
    Principal value proposition headline

    - Impact highlight one
    - Impact highlight two

    Summary paragraph text that may span
    multiple lines.

    email@example.com
    https://example.com
    https://linkedin.com/in/...

This module is the canonical parser. The deploy.yml "Generate bio data for Hugo"
step calls this as a CLI::

    python -m resume_generator.bio_yaml <src_bio_txt> <dst_bio_yaml> \
        [<build_log_html>] [<resume_yaml>]
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
from typing import TypedDict

import yaml


class BioData(TypedDict, total=False):
    """Typed dict for Hugo landing page bio data parsed from brad.bio.txt."""

    name: str
    label: str
    principal_headline: str
    impact_highlights: list[str]
    summary: str
    about: str
    email: str
    url: str
    linkedin: str
    build_log: bool
    build_id: str


def _is_contact_line(line: str) -> bool:
    """Return True if *line* looks like a contact-info line (email or URL)."""
    stripped = line.strip()
    return bool(stripped) and ("@" in stripped or stripped.startswith("http://") or stripped.startswith("https://"))


def _split_paragraphs(lines: list[str]) -> list[list[str]]:
    """Partition *lines* into paragraphs separated by blank lines.

    Returns a list of non-empty groups; leading/trailing blank lines are ignored.
    """
    paragraphs: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip():
            current.append(line)
        elif current:
            paragraphs.append(current)
            current = []
    if current:
        paragraphs.append(current)
    return paragraphs


def parse_bio_txt(text: str) -> BioData:
    """Parse brad.bio.txt content into a BioData dict.

    Args:
        text: Contents of brad.bio.txt.

    Returns:
        Dict with name, label, principal_headline, impact_highlights,
        summary, email, url, linkedin fields.
        build_log and build_id are NOT set here — callers add them.
    """
    lines = text.strip().splitlines()

    name = lines[0] if lines else ""
    label = lines[1] if len(lines) > 1 else ""

    # Detect the optional principal_headline (new-format only):
    # line 2 must be non-blank and non-bullet; line 3 must be blank;
    # and the first line of the body (line 4) must not already be contact info.
    principal_headline = ""
    body_start = 2
    no_contact_follows = len(lines) <= 4 or not _is_contact_line(lines[4])
    if (
        len(lines) > 3
        and lines[2].strip()
        and not lines[2].lstrip().startswith("- ")
        and not lines[3].strip()
        and no_contact_follows
    ):
        principal_headline = lines[2].strip()
        body_start = 4  # skip the headline and its trailing blank line

    # Split the remaining body into paragraphs (groups of non-blank lines).
    paragraphs = _split_paragraphs(lines[body_start:])

    # Classify paragraphs in order: optional impact bullets → summary → contact.
    impact_highlights: list[str] = []
    if paragraphs and all(ln.lstrip().startswith("- ") for ln in paragraphs[0]):
        impact_highlights = [ln.lstrip()[2:].strip() for ln in paragraphs[0]]
        paragraphs = paragraphs[1:]

    summary = ""
    if paragraphs:
        summary = " ".join(ln for ln in paragraphs[0] if ln.strip())
        paragraphs = paragraphs[1:]

    contact = [ln.strip() for para in paragraphs for ln in para if ln.strip()]

    return BioData(
        name=name,
        label=label,
        principal_headline=principal_headline,
        impact_highlights=impact_highlights,
        summary=summary,
        email=contact[0] if contact else "",
        url=contact[1] if len(contact) > 1 else "",
        linkedin=contact[2] if len(contact) > 2 else "",
    )


def _read_about_from_resume_yaml(path: str) -> str:
    """Extract the top-level 'about' field from resume.yaml.

    Uses yaml.safe_load so all YAML scalar styles (|-, >, >-, quoted, plain)
    are handled correctly.

    Args:
        path: Path to resume.yaml.

    Returns:
        The about value as a plain string, or empty string if absent/unreadable.
    """
    p = pathlib.Path(path)
    if not p.exists():
        return ""
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return str(data.get("about", "") or "")
        return ""
    except yaml.YAMLError:
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
        f"principal_headline: {json.dumps(data.get('principal_headline', ''))}",
    ]
    highlights = [h for h in data.get("impact_highlights", []) if h]
    if highlights:
        lines.append("impact_highlights:")
        for item in highlights:
            lines.append(f"  - {json.dumps(item)}")
    lines += [
        f"summary: {json.dumps(data.get('summary', ''))}",
    ]
    if data.get("about"):
        lines.append(f"about: {json.dumps(data['about'])}")
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

        python -m resume_generator.bio_yaml <src_bio_txt> <dst_bio_yaml> \
            [<build_log_html>] [<resume_yaml>]

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        0 on success, 1 on error.
    """
    args = argv if argv is not None else sys.argv[1:]
    if len(args) < 2:
        print(
            "Usage: bio_yaml <src_bio_txt> <dst_bio_yaml> [<build_log_html>] [<resume_yaml>]",
            file=sys.stderr,
        )
        return 1

    src = pathlib.Path(args[0])
    dst = pathlib.Path(args[1])
    default_log = pathlib.Path("hugo/static/build.log.html")
    build_log = pathlib.Path(args[2]) if len(args) >= 3 else default_log
    resume_yaml = args[3] if len(args) >= 4 else "resume.yaml"

    if not src.exists() or src.stat().st_size == 0:
        print(f"bio_yaml: {src} is missing or empty — skipping", file=sys.stderr)
        return 0

    text = src.read_text(encoding="utf-8")
    data = parse_bio_txt(text)

    about = _read_about_from_resume_yaml(resume_yaml)
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
