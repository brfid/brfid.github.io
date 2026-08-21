"""Parse brad.bio.txt pipeline output into hugo/data/bio.yaml.

brad.bio.txt is the nroff-rendered bio produced by the vintage pipeline
(bradman.c on the VAX composes troff; the PDP-11 fills and justifies it). Its
shape is three parts separated by a blank line::

    Bradley Fidler
    Principal Technical Writer

    I  run  technical  documentation  at  a mid-sized B2B cybersecurity
    company.  Before this, I wrote lessons learned analyses of distributed
    systems, and taught technology history in college.

The first two lines are the name and headline; the remaining lines are the
prose. nroff filled and justified that prose to a fixed 60-column measure, but
that column geometry is a rendering artifact, not content: the landing page
sets the bio as humanist serif prose, so this parser collapses the fill back to
flowing single-spaced sentences (blank lines still separate paragraphs).

This module is the canonical parser. The deploy.yml "Generate bio data for Hugo"
step calls this as a CLI::

    python -m resume_generator.bio_yaml <src_bio_txt> <dst_bio_yaml> \
        [<build_log_html>] [<build_run_url>]
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
    principal_headline: str
    about: str
    build_log: bool
    build_id: str
    build_run_url: str


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
    """Parse the nroff-rendered brad.bio.txt into a BioData dict.

    Args:
        text: Contents of brad.bio.txt.

    Returns:
        Dict with name, principal_headline, and about. The name/headline are
        trimmed; the about prose is reflowed to flowing sentences (nroff's
        fixed-width line breaks and justification padding are collapsed to
        single-spaced prose, with blank lines preserved as paragraph breaks).
        Build metadata is NOT set here — callers add it.
    """
    paragraphs = _split_paragraphs(text.splitlines())

    header = paragraphs[0] if paragraphs else []
    name = header[0].strip() if header else ""
    principal_headline = header[1].strip() if len(header) > 1 else ""

    # Collapse each prose paragraph's fill/justification (runs of spaces and
    # hard line breaks at the 60-column measure) back into one flowing line;
    # keep paragraph boundaries as a blank line between them.
    prose = [re.sub(r"\s+", " ", " ".join(group)).strip() for group in paragraphs[1:]]
    about = "\n\n".join(prose)

    return BioData(
        name=name,
        principal_headline=principal_headline,
        about=about,
    )


def bio_to_yaml(data: BioData) -> str:
    r"""Serialise a BioData dict to YAML text for hugo/data/bio.yaml.

    Uses json.dumps for quoting (a safe superset of YAML scalar quoting for
    simple strings; also encodes embedded newlines in `about` as \n, which
    Hugo's YAML reader restores). Avoids a PyYAML dependency.

    Args:
        data: BioData dict, may include optional build metadata.

    Returns:
        YAML string.
    """
    lines = [
        f"name: {json.dumps(data.get('name', ''))}",
        f"principal_headline: {json.dumps(data.get('principal_headline', ''))}",
        f"about: {json.dumps(data.get('about', ''))}",
    ]
    if data.get("build_log"):
        lines.append("build_log: true")
    if data.get("build_id"):
        lines.append(f"build_id: {json.dumps(data['build_id'])}")
    if data.get("build_run_url"):
        lines.append(f"build_run_url: {json.dumps(data['build_run_url'])}")
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
            [<build_log_html>] [<build_run_url>]

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        0 on success, 1 on error.
    """
    args = argv if argv is not None else sys.argv[1:]
    if len(args) < 2:
        print(
            "Usage: bio_yaml <src_bio_txt> <dst_bio_yaml> [<build_log_html>] [<build_run_url>]",
            file=sys.stderr,
        )
        return 1

    src = pathlib.Path(args[0])
    dst = pathlib.Path(args[1])
    default_log = pathlib.Path("hugo/static/build.log.html")
    build_log = pathlib.Path(args[2]) if len(args) >= 3 else default_log
    build_run_url = args[3] if len(args) >= 4 else ""

    if not src.exists() or src.stat().st_size == 0:
        print(f"bio_yaml: {src} is missing or empty — skipping", file=sys.stderr)
        return 0

    text = src.read_text(encoding="utf-8")
    data = parse_bio_txt(text)

    build_log_available = build_log.is_file() and build_log.stat().st_size > 0
    build_id = ""
    if build_log_available:
        data["build_log"] = True
        build_id = _read_build_id(build_log)
        if build_id:
            data["build_id"] = build_id
    if build_run_url:
        data["build_run_url"] = build_run_url

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(bio_to_yaml(data), encoding="utf-8")
    print(f"bio_yaml: wrote {dst} (build_id={build_id!r})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
