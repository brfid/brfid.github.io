#!/usr/bin/env python3
"""Verify the retired GitHub Pages output redirects only to the GitLab site."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from html.parser import HTMLParser
from pathlib import Path

DESTINATION_BASE = "https://brfid.gitlab.io"
ROBOTS_DIRECTIVE = "noindex, nofollow, noarchive, nosnippet, noimageindex"
EXPECTED_REDIRECTS: Mapping[Path, str] = {
    Path("index.html"): "/",
    Path("404.html"): "/",
    Path("resume/index.html"): "/resume/",
    Path("about/index.html"): "/about/",
    Path("posts/index.html"): "/posts/",
    Path("posts/stracheys-principle/index.html"): "/posts/stracheys-principle/",
    Path("posts/doc-rot-maintenance-gap/index.html"): "/posts/doc-rot-maintenance-gap/",
}
ROBOTS_TEXT = """# HTML remains crawlable so crawlers can observe its noindex directive.
User-agent: *
Allow: /
"""
EXPECTED_SCRIPT_LINES = (
    "(() => {",
    f'const destination = new URL("{DESTINATION_BASE}");',
    "destination.pathname = window.location.pathname;",
    "destination.search = window.location.search;",
    "destination.hash = window.location.hash;",
    "window.location.replace(destination.href);",
    "})();",
)


class RedirectParser(HTMLParser):
    """Collect the redirect contract from one generated HTML document."""

    def __init__(self) -> None:
        """Initialize an empty redirect contract."""
        super().__init__(convert_charrefs=True)
        self.html_language = ""
        self.meta: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.anchors: list[dict[str, str]] = []
        self.script_attributes: list[dict[str, str]] = []
        self.script_parts: list[str] = []
        self.unsafe_attributes: list[str] = []
        self._inside_script = False

    @staticmethod
    def _attributes(values: list[tuple[str, str | None]]) -> dict[str, str]:
        return {name: value or "" for name, value in values}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collect relevant attributes from an opening tag."""
        attributes = self._attributes(attrs)
        for name, value in attributes.items():
            if name.lower().startswith("on") or value.lstrip().lower().startswith("javascript:"):
                self.unsafe_attributes.append(f"{tag}[{name}]")
        if tag == "html":
            self.html_language = attributes.get("lang", "")
        elif tag == "meta":
            self.meta.append(attributes)
        elif tag == "link":
            self.links.append(attributes)
        elif tag == "a":
            self.anchors.append(attributes)
        elif tag == "script":
            self.script_attributes.append(attributes)
            self._inside_script = True

    def handle_endtag(self, tag: str) -> None:
        """Stop collecting script text at a closing script tag."""
        if tag == "script":
            self._inside_script = False

    def handle_data(self, data: str) -> None:
        """Collect inline script text for redirect checks."""
        if self._inside_script:
            self.script_parts.append(data)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _regular_file(path: Path) -> None:
    _require(not path.is_symlink() and path.is_file(), f"missing or unsafe redirect output: {path}")


def _verify_document(path: Path, target_path: str) -> None:
    _regular_file(path)
    parser = RedirectParser()
    parser.feed(path.read_text(encoding="utf-8"))
    target = f"{DESTINATION_BASE}{target_path}"

    _require(parser.html_language == "en", f"redirect page lacks lang=en: {path}")
    robots_meta = [item for item in parser.meta if item.get("name") == "robots"]
    _require(
        robots_meta == [{"name": "robots", "content": ROBOTS_DIRECTIVE}],
        f"redirect page lacks the exact noindex contract: {path}",
    )
    refresh_meta = [item for item in parser.meta if item.get("http-equiv", "").lower() == "refresh"]
    _require(
        refresh_meta == [{"http-equiv": "refresh", "content": f"0; url={target}"}],
        f"redirect page has the wrong refresh target: {path}",
    )
    _require(
        parser.links == [{"rel": "canonical", "href": target}],
        f"redirect page has the wrong canonical target: {path}",
    )
    _require(
        parser.anchors == [{"href": target}],
        f"redirect page lacks the exact fallback link: {path}",
    )
    _require(not parser.unsafe_attributes, f"redirect page has active attributes: {path}")
    _require(
        parser.script_attributes == [{}],
        f"redirect page must contain one inline script: {path}",
    )
    script = "\n".join(parser.script_parts)
    script_lines = tuple(line.strip() for line in script.splitlines() if line.strip())
    _require(script_lines == EXPECTED_SCRIPT_LINES, f"redirect script changed: {path}")


def verify_redirect(output_dir: Path) -> None:
    """Verify the exact redirect-only GitHub Pages tree."""
    _require(
        output_dir.is_dir() and not output_dir.is_symlink(),
        f"unsafe output directory: {output_dir}",
    )
    expected_files = set(EXPECTED_REDIRECTS) | {Path("robots.txt")}
    actual_files: set[Path] = set()
    for candidate in output_dir.rglob("*"):
        _require(not candidate.is_symlink(), f"redirect output contains a symbolic link: {candidate}")
        if candidate.is_file():
            actual_files.add(candidate.relative_to(output_dir))
    _require(
        actual_files == expected_files,
        f"unexpected redirect output files: {sorted(actual_files ^ expected_files)}",
    )

    for relative_path, target_path in EXPECTED_REDIRECTS.items():
        _verify_document(output_dir / relative_path, target_path)

    robots = output_dir / "robots.txt"
    _regular_file(robots)
    _require(robots.read_text(encoding="utf-8") == ROBOTS_TEXT, "redirect robots.txt changed")


def main(argv: Sequence[str] | None = None) -> int:
    """Verify a generated redirect tree from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)
    try:
        verify_redirect(args.output_dir)
    except (OSError, ValueError) as exc:
        print(f"redirect verification: {exc}", file=sys.stderr)
        return 1
    print(f"Verified GitHub Pages redirect: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
