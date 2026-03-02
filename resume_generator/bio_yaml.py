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
import sys
from typing import TypedDict


class BioData(TypedDict, total=False):
    """Typed dict for Hugo landing page bio data parsed from brad.bio.txt."""

    name: str
    label: str
    summary: str
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
    contact = [ln for ln in lines[blank1 + 1:] if ln.strip()]

    return BioData(
        name=name,
        label=label,
        summary=summary,
        email=contact[0] if len(contact) > 0 else "",
        url=contact[1] if len(contact) > 1 else "",
        linkedin=contact[2] if len(contact) > 2 else "",
    )


def bio_to_yaml(data: BioData) -> str:
    """Serialise a BioData dict to YAML text for hugo/data/bio.yaml.

    Uses json.dumps for quoting (safe superset of YAML scalar quoting for
    simple strings; avoids a PyYAML dependency).

    Args:
        data: BioData dict, may include optional build_log / build_id fields.

    Returns:
        YAML string.
    """
    lines = [
        f"name: {json.dumps(data.get('name', ''))}",
        f"label: {json.dumps(data.get('label', ''))}",
        f"summary: {json.dumps(data.get('summary', ''))}",
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
    """Extract build_id from the first line of build.log.txt.

    Expected first line format: ``BUILD <build-id>``

    Args:
        build_log_path: Path to hugo/static/build.log.txt.

    Returns:
        Build ID string, or empty string if not found.
    """
    if not build_log_path.exists():
        return ""
    parts = build_log_path.read_text(encoding="utf-8").splitlines()[0].split()
    return parts[1] if len(parts) >= 2 else ""


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
    default_log = pathlib.Path("hugo/static/build.log.txt")
    build_log = pathlib.Path(args[2]) if len(args) >= 3 else default_log

    if not src.exists() or src.stat().st_size == 0:
        print(f"bio_yaml: {src} is missing or empty — skipping", file=sys.stderr)
        return 0

    text = src.read_text(encoding="utf-8")
    data = parse_bio_txt(text)
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
