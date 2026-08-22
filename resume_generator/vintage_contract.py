"""Validate the public input and rendered output of the vintage bio pipeline."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .bio_yaml import BioData, parse_bio_txt, require_complete_bio


class VintageContractError(ValueError):
    """Raised when vintage input or output violates the publish contract."""


@dataclass(frozen=True)
class VintageBioInput:
    """The three public strings that must survive the vintage round trip."""

    name: str
    headline: str
    summary: str


def _required_public_string(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise VintageContractError(f"{field} must be a string")
    if not value or value != value.strip():
        raise VintageContractError(f"{field} must be non-empty with no surrounding whitespace")
    if not value.isascii():
        raise VintageContractError(f"{field} must contain ASCII only for the vintage pipeline")
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise VintageContractError(f"{field} must be a single printable line")
    return value


def vintage_input_from_mappings(site: Mapping[str, Any], resume: Mapping[str, Any]) -> VintageBioInput:
    """Extract and validate the exact public input consumed by the vintage path."""
    basics = resume.get("basics")
    if not isinstance(basics, Mapping):
        raise VintageContractError("resume.yaml basics must be a mapping")
    return VintageBioInput(
        name=_required_public_string(site.get("name"), field="site.yaml name"),
        headline=_required_public_string(site.get("headline"), field="site.yaml headline"),
        summary=_required_public_string(basics.get("summary"), field="resume.yaml basics.summary"),
    )


def validate_rendered_bio(text: str, expected: VintageBioInput) -> BioData:
    """Validate one rendered bio against the public source strings.

    ``nroff`` changes line breaks and inter-word spacing while filling and
    justifying the summary, so summary comparison normalizes whitespace only.
    Name and headline must remain byte-for-byte identical.
    """
    if not text.strip():
        raise VintageContractError("rendered bio is missing or empty")
    data = parse_bio_txt(text)
    try:
        name, headline, about = require_complete_bio(data)
    except ValueError as exc:
        raise VintageContractError(str(exc)) from exc

    mismatches: list[str] = []
    if name != expected.name:
        mismatches.append(f"name {name!r} != {expected.name!r}")
    if headline != expected.headline:
        mismatches.append(f"headline {headline!r} != {expected.headline!r}")
    actual_summary = " ".join(about.split())
    expected_summary = " ".join(expected.summary.split())
    if actual_summary != expected_summary:
        mismatches.append(f"summary {actual_summary!r} != {expected_summary!r}")
    if mismatches:
        raise VintageContractError("rendered bio does not match public sources: " + "; ".join(mismatches))
    return data


def _load_mapping(path: Path, *, label: str) -> Mapping[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise VintageContractError(f"{label} must contain a top-level mapping")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    """Validate a rendered bio file against ``site.yaml`` and ``resume.yaml``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bio_txt", type=Path, help="Rendered brad.bio.txt")
    parser.add_argument("site_yaml", type=Path, help="Public site.yaml")
    parser.add_argument("resume_yaml", type=Path, help="Public resume.yaml")
    args = parser.parse_args(argv)

    try:
        text = args.bio_txt.read_text(encoding="utf-8")
        site = _load_mapping(args.site_yaml, label="site.yaml")
        resume = _load_mapping(args.resume_yaml, label="resume.yaml")
        expected = vintage_input_from_mappings(site, resume)
        validate_rendered_bio(text, expected)
    except (OSError, UnicodeError, yaml.YAMLError, VintageContractError) as exc:
        print(f"vintage contract: {exc}", file=sys.stderr)
        return 1

    print("vintage contract: rendered bio matches site.yaml and resume.yaml basics.summary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
