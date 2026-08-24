"""Convert the nroff-rendered bio to Hugo YAML data."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections.abc import Sequence
from typing import TypedDict


class BioData(TypedDict, total=False):
    """Fields consumed by the Hugo landing page."""

    name: str
    principal_headline: str
    about: str
    build_log: bool
    build_id: str
    build_run_url: str


def _split_paragraphs(lines: list[str]) -> list[list[str]]:
    """Return nonempty line groups separated by blank lines."""
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
    """Parse name, headline, and reflowed summary from nroff output."""
    paragraphs = _split_paragraphs(text.splitlines())

    header = paragraphs[0] if paragraphs else []
    name = header[0].strip() if header else ""
    principal_headline = header[1].strip() if len(header) > 1 else ""

    # Remove nroff line filling and justification while retaining paragraphs.
    prose = [re.sub(r"\s+", " ", " ".join(group)).strip() for group in paragraphs[1:]]
    about = "\n\n".join(prose)

    return BioData(
        name=name,
        principal_headline=principal_headline,
        about=about,
    )


def require_complete_bio(data: BioData) -> tuple[str, str, str]:
    """Return required bio fields or raise when the rendered shape is incomplete."""
    name = data.get("name", "").strip()
    headline = data.get("principal_headline", "").strip()
    about = data.get("about", "").strip()
    missing = [label for label, value in (("name", name), ("headline", headline), ("about", about)) if not value]
    if missing:
        raise ValueError(f"rendered bio is missing required fields: {', '.join(missing)}")
    return name, headline, about


def bio_to_yaml(data: BioData) -> str:
    r"""Serialize bio data as YAML with JSON-compatible quoted scalars."""
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


def _read_successful_build_id(status_path: pathlib.Path) -> str:
    """Read a successful build ID from the structured pipeline status file."""
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if not isinstance(status, dict):
        raise ValueError("pipeline status must be a JSON object")
    if status.get("result") != "success" or status.get("exit_code") != 0:
        raise ValueError("pipeline status does not describe a successful build")
    build_id = status.get("build_id")
    if not isinstance(build_id, str) or not build_id.strip():
        raise ValueError("pipeline status has no build_id")
    return build_id


def main(argv: Sequence[str] | None = None) -> int:
    """Convert one rendered bio file and return the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src", type=pathlib.Path, help="Rendered brad.bio.txt")
    parser.add_argument("dst", type=pathlib.Path, help="Destination hugo/data/bio.yaml")
    parser.add_argument(
        "--build-log",
        type=pathlib.Path,
        default=pathlib.Path("hugo/static/build.log.html"),
        help="Published build-log HTML, when available",
    )
    parser.add_argument("--pipeline-status", type=pathlib.Path, help="Structured pipeline-status.json")
    parser.add_argument("--build-run-url", default="", help="GitHub Actions run associated with the vintage result")
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if not arguments:
        parser.print_usage(sys.stderr)
        return 1
    args = parser.parse_args(arguments)

    if not args.src.exists() or args.src.stat().st_size == 0:
        print(f"bio_yaml: {args.src} is missing or empty", file=sys.stderr)
        return 1

    try:
        text = args.src.read_text(encoding="utf-8")
        data = parse_bio_txt(text)
        require_complete_bio(data)

        build_log_available = args.build_log.is_file() and args.build_log.stat().st_size > 0
        build_id = ""
        if args.pipeline_status is not None:
            if not build_log_available:
                raise ValueError("pipeline status was provided but the build log is missing or empty")
            build_id = _read_successful_build_id(args.pipeline_status)
        if build_log_available:
            data["build_log"] = True
        if build_id:
            data["build_id"] = build_id
        if args.build_run_url:
            data["build_run_url"] = args.build_run_url

        args.dst.parent.mkdir(parents=True, exist_ok=True)
        args.dst.write_text(bio_to_yaml(data), encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"bio_yaml: {exc}", file=sys.stderr)
        return 1

    print(f"bio_yaml: wrote {args.dst} (build_id={build_id!r})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
