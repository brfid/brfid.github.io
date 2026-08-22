"""Verify contracts that only exist in Hugo's rendered output."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

import yaml

REQUIRED_FILES = (
    "404.html",
    "about/index.html",
    "index.html",
    "index.xml",
    "posts/index.html",
    "posts/index.xml",
    "resume/index.html",
    "robots.txt",
)
REQUIRED_ROBOTS_DIRECTIVES = frozenset({"noarchive", "nofollow", "noimageindex", "noindex", "nosnippet"})
EXPECTED_ROBOTS_LINES = (
    "User-agent: *",
    "Allow: /",
    "Disallow: /pipeline-status.json",
    "Disallow: /resume.pdf",
    "Disallow: /index.xml",
    "Disallow: /posts/index.xml",
)
DOUBLE_ESCAPED_QUOTE = re.compile(r"&#(?:34|39|x22|x27);", re.IGNORECASE)
PRODUCTION_REQUIRED_FILES = ("resume.pdf", "build.log.html", "pipeline-status.json")
PLAUSIBLE_US_PHONE = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]?)?(?:\([2-9]\d{2}\)|[2-9]\d{2})[\s.-]?[2-9]\d{2}[\s.-]?\d{4}(?!\d)"
)
TAGGED_PDF = re.compile(r"^Tagged:\s+yes\s*$", re.MULTILINE)


class RenderedPageParser(HTMLParser):
    """Collect the small set of HTML fields used by the verifier."""

    def __init__(self) -> None:
        """Initialize collected metadata, links, and JSON-LD blocks."""
        super().__init__()
        self.robots: list[str] = []
        self.anchors: list[dict[str, str]] = []
        self.json_ld: list[str] = []
        self.text: list[str] = []
        self._json_ld_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collect relevant attributes and begin JSON-LD capture."""
        attributes = {name: value or "" for name, value in attrs}
        if tag == "meta" and attributes.get("name", "").lower() == "robots":
            self.robots.append(attributes.get("content", ""))
        elif tag == "a":
            self.anchors.append(attributes)
        elif tag == "script" and attributes.get("type", "").lower() == "application/ld+json":
            self._json_ld_parts = []

    def handle_data(self, data: str) -> None:
        """Capture rendered text and any active JSON-LD script."""
        self.text.append(data)
        if self._json_ld_parts is not None:
            self._json_ld_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        """Finish JSON-LD capture when its script closes."""
        if tag == "script" and self._json_ld_parts is not None:
            self.json_ld.append("".join(self._json_ld_parts))
            self._json_ld_parts = None


def parse_html(path: Path) -> RenderedPageParser:
    """Parse one rendered HTML file."""
    parser = RenderedPageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


def record(condition: bool, errors: list[str], message: str) -> None:
    """Record a failed contract without hiding later failures."""
    if not condition:
        errors.append(message)


def verify_required_files(site_dir: Path, errors: list[str]) -> bool:
    """Check public routes and return whether a required input is missing."""
    missing = False
    for relative_path in REQUIRED_FILES:
        path = site_dir / relative_path
        available = path.is_file() and path.stat().st_size > 0
        record(available, errors, f"missing or empty: {relative_path}")
        missing = missing or not available
    record(not (site_dir / "sitemap.xml").exists(), errors, "unexpected sitemap.xml")
    return missing


def verify_robots(site_dir: Path, errors: list[str]) -> None:
    """Check the full no-index policy on every rendered HTML page."""
    for path in sorted(site_dir.rglob("*.html")):
        parser = parse_html(path)
        directives = [
            {directive.strip().lower() for directive in content.split(",") if directive.strip()}
            for content in parser.robots
        ]
        all_directives = set().union(*directives) if directives else set()
        relative_path = path.relative_to(site_dir)
        record(
            any(directive_set >= REQUIRED_ROBOTS_DIRECTIVES for directive_set in directives),
            errors,
            f"{relative_path}: missing full robots no-index policy",
        )
        record(
            all_directives.isdisjoint({"all", "follow", "index"}),
            errors,
            f"{relative_path}: conflicting robots index/follow policy",
        )


def verify_robots_file(site_dir: Path, errors: list[str]) -> None:
    """Check the crawl policy for HTML and public machine-readable artifacts."""
    lines = [
        line.strip()
        for line in (site_dir / "robots.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    record(
        lines == list(EXPECTED_ROBOTS_LINES),
        errors,
        f"robots.txt: unexpected directives: {lines!r}",
    )
    record("Disallow: /" not in lines, errors, "robots.txt: blanket crawl block hides the HTML no-index policy")


def verify_homepage_schema(site_dir: Path, errors: list[str]) -> None:
    """Require parseable homepage JSON-LD with `@type: Person`."""
    parser = parse_html(site_dir / "index.html")
    record(bool(parser.json_ld), errors, "index.html: missing JSON-LD")
    has_person = False
    for document in parser.json_ld:
        try:
            data = json.loads(document)
        except json.JSONDecodeError as error:
            errors.append(f"index.html: invalid JSON-LD: {error}")
            continue
        has_person = has_person or (isinstance(data, dict) and data.get("@type") == "Person")
    record(has_person, errors, "index.html: missing Person JSON-LD")


def rendered_path_for_url(site_dir: Path, url: str) -> Path:
    """Map a rendered page URL to its expected file under the site root."""
    path = unquote(urlparse(url).path)
    candidate = site_dir / path.lstrip("/")
    if path.endswith("/") or not candidate.suffix:
        candidate /= "index.html"
    return candidate


def verify_feeds(site_dir: Path, errors: list[str]) -> None:
    """Check feed XML, post targets, and numeric-quote double escaping."""
    for relative_path in ("index.xml", "posts/index.xml"):
        feed_path = site_dir / relative_path
        try:
            # The input is the local Hugo build, not externally supplied XML.
            root = ET.parse(feed_path).getroot()  # noqa: S314
        except ET.ParseError as error:
            errors.append(f"{relative_path}: invalid XML: {error}")
            continue

        items = root.findall("./channel/item")
        record(bool(items), errors, f"{relative_path}: feed has no items")
        for item in items:
            description = item.findtext("description", default="")
            link = item.findtext("link", default="").strip()
            record(
                DOUBLE_ESCAPED_QUOTE.search(description) is None,
                errors,
                f"{relative_path}: description contains a double-escaped entity: {description!r}",
            )
            record("/resume/" not in urlparse(link).path, errors, f"{relative_path}: resume leaked into feed")
            record(bool(link), errors, f"{relative_path}: item has no link")
            if link:
                target = rendered_path_for_url(site_dir, link)
                record(target.is_file(), errors, f"{relative_path}: item link has no rendered page: {link}")


def find_menu_link(parser: RenderedPageParser, path: str) -> dict[str, str] | None:
    """Find a primary-menu link by its URL path."""
    for anchor in parser.anchors:
        classes = anchor.get("class", "").split()
        if "menu-primary-link" in classes and urlparse(anchor.get("href", "")).path == path:
            return anchor
    return None


def find_link(parser: RenderedPageParser, path: str, required_class: str | None = None) -> dict[str, str] | None:
    """Find a rendered link by URL path and optional CSS class."""
    for anchor in parser.anchors:
        if urlparse(anchor.get("href", "")).path != path:
            continue
        if required_class is None or required_class in anchor.get("class", "").split():
            return anchor
    return None


def verify_primary_links(site_dir: Path, errors: list[str]) -> None:
    """Check primary routes and contextual feed/PDF actions."""
    homepage = parse_html(site_dir / "index.html")
    for path in ("/posts/", "/resume/"):
        record(find_menu_link(homepage, path) is not None, errors, f"index.html: missing primary link to {path}")

    posts = parse_html(site_dir / "posts/index.html")
    record(
        find_link(posts, "/posts/index.xml", "section-feed-link") is not None,
        errors,
        "posts/index.html: missing section RSS link",
    )

    resume = parse_html(site_dir / "resume/index.html")
    record(
        find_link(resume, "/resume.pdf", "resume-download-link") is not None,
        errors,
        "resume/index.html: missing resume PDF link",
    )


def verify_menu_state(site_dir: Path, errors: list[str]) -> None:
    """Check exact and descendant current states in the rendered menu."""
    expected_states = {
        "posts/index.html": ("/posts/", "page"),
        "resume/index.html": ("/resume/", "page"),
    }
    for post_path in site_dir.glob("posts/*/index.html"):
        expected_states[str(post_path.relative_to(site_dir))] = ("/posts/", "location")

    for relative_path, (menu_path, expected_state) in sorted(expected_states.items()):
        parser = parse_html(site_dir / relative_path)
        link = find_menu_link(parser, menu_path)
        record(link is not None, errors, f"{relative_path}: missing menu link to {menu_path}")
        if link is not None:
            record(
                link.get("aria-current") == expected_state,
                errors,
                f"{relative_path}: {menu_path} has aria-current={link.get('aria-current')!r}, "
                f"expected {expected_state!r}",
            )


def is_nonempty_file(path: Path) -> bool:
    """Return whether a path is a nonempty regular file."""
    return path.is_file() and path.stat().st_size > 0


def read_public_email(resume_yaml: Path, errors: list[str]) -> str | None:
    """Read the public resume email, recording malformed input as a contract error."""
    if not is_nonempty_file(resume_yaml):
        errors.append(f"resume YAML is missing or empty: {resume_yaml}")
        return None
    try:
        data = yaml.safe_load(resume_yaml.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        errors.append(f"could not read resume YAML {resume_yaml}: {error}")
        return None
    if not isinstance(data, dict) or not isinstance(data.get("basics"), dict):
        errors.append(f"resume YAML has no basics mapping: {resume_yaml}")
        return None
    email = data["basics"].get("email")
    if not isinstance(email, str) or not email.strip():
        errors.append(f"resume YAML has no public basics.email: {resume_yaml}")
        return None
    return email.strip()


def read_build_id(status_path: Path, errors: list[str]) -> str | None:
    """Read and validate the production pipeline result, returning its build ID."""
    try:
        status = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        errors.append(f"pipeline-status.json: could not read valid JSON: {error}")
        return None
    if not isinstance(status, dict):
        errors.append("pipeline-status.json: expected a JSON object")
        return None

    record(status.get("result") == "success", errors, "pipeline-status.json: result is not 'success'")
    exit_code = status.get("exit_code")
    record(
        isinstance(exit_code, int) and not isinstance(exit_code, bool) and exit_code == 0,
        errors,
        "pipeline-status.json: exit_code is not 0",
    )
    build_id = status.get("build_id")
    if not isinstance(build_id, str) or not build_id.strip():
        errors.append("pipeline-status.json: build_id is missing or empty")
        return None
    return build_id


def run_external(command: str, arguments: Sequence[str], errors: list[str]) -> str | None:
    """Run a required inspection command and return stdout on success."""
    executable = shutil.which(command)
    if executable is None:
        errors.append(f"required external command not found: {command}")
        return None
    try:
        result = subprocess.run(  # noqa: S603 - executable is resolved and arguments are never passed to a shell
            [executable, *arguments],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        errors.append(f"could not run {command}: {error}")
        return None
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        errors.append(f"{command} failed with exit code {result.returncode}: {detail}")
        return None
    return result.stdout


def verify_html_privacy(site_dir: Path, errors: list[str]) -> None:
    """Reject telephone links and visible phone numbers in rendered HTML."""
    for path in sorted(site_dir.rglob("*.html")):
        parser = parse_html(path)
        relative_path = path.relative_to(site_dir)
        has_phone_link = any(anchor.get("href", "").strip().lower().startswith("tel:") for anchor in parser.anchors)
        record(not has_phone_link, errors, f"{relative_path}: contains a telephone link")
        visible_text = " ".join(parser.text)
        record(
            PLAUSIBLE_US_PHONE.search(visible_text) is None,
            errors,
            f"{relative_path}: contains a plausible US phone number",
        )


def verify_resume_pdf(site_dir: Path, public_email: str | None, errors: list[str]) -> None:
    """Check the public email, phone exclusion, and tagged-PDF flag."""
    pdf_path = site_dir / "resume.pdf"
    text = run_external("pdftotext", [str(pdf_path.resolve()), "-"], errors)
    if text is not None:
        if public_email is not None:
            record(public_email in text, errors, "resume.pdf: missing the public basics.email")
        record(PLAUSIBLE_US_PHONE.search(text) is None, errors, "resume.pdf: contains a plausible US phone number")

    info = run_external("pdfinfo", [str(pdf_path.resolve())], errors)
    if info is not None:
        record(TAGGED_PDF.search(info) is not None, errors, "resume.pdf: PDF is not tagged")


def verify_provenance_links(
    site_dir: Path,
    *,
    build_id: str | None,
    build_run_url: str,
    errors: list[str],
) -> None:
    """Check that the homepage exposes the exact production build provenance."""
    homepage = site_dir / "index.html"
    if not is_nonempty_file(homepage):
        return
    parser = parse_html(homepage)
    build_log_links = [anchor for anchor in parser.anchors if anchor.get("href") == "/build.log.html"]
    record(bool(build_log_links), errors, "index.html: missing exact link to /build.log.html")
    if build_id is not None and build_log_links:
        record(
            any(anchor.get("title") == build_id for anchor in build_log_links),
            errors,
            f"index.html: build-log link title does not match build_id {build_id!r}",
        )
    record(
        any(anchor.get("href") == build_run_url for anchor in parser.anchors),
        errors,
        f"index.html: missing exact build run URL {build_run_url!r}",
    )


def verify_production_site(site_dir: Path, *, resume_yaml: Path, build_run_url: str) -> list[str]:
    """Return production-only artifact, privacy, and provenance failures."""
    errors: list[str] = []
    available = {
        relative_path: is_nonempty_file(site_dir / relative_path) for relative_path in PRODUCTION_REQUIRED_FILES
    }
    for relative_path, exists in available.items():
        record(exists, errors, f"missing or empty production artifact: {relative_path}")

    pdfs = sorted(
        path.relative_to(site_dir) for path in site_dir.rglob("*") if path.is_file() and path.suffix.lower() == ".pdf"
    )
    record(pdfs == [Path("resume.pdf")], errors, f"production site PDFs must be exactly ['resume.pdf']; found {pdfs!r}")

    raw_bios = sorted(path.relative_to(site_dir) for path in site_dir.rglob("brad.bio.txt"))
    record(not raw_bios, errors, f"raw brad.bio.txt was published: {raw_bios!r}")
    verify_html_privacy(site_dir, errors)

    public_email = read_public_email(resume_yaml, errors)
    if available["resume.pdf"]:
        verify_resume_pdf(site_dir, public_email, errors)

    build_id = read_build_id(site_dir / "pipeline-status.json", errors) if available["pipeline-status.json"] else None
    verify_provenance_links(
        site_dir,
        build_id=build_id,
        build_run_url=build_run_url,
        errors=errors,
    )
    return errors


def verify_site(site_dir: Path) -> list[str]:
    """Return rendered-site failures that can be checked from available inputs."""
    errors: list[str] = []
    if verify_required_files(site_dir, errors):
        return errors
    verify_robots(site_dir, errors)
    verify_robots_file(site_dir, errors)
    verify_homepage_schema(site_dir, errors)
    verify_feeds(site_dir, errors)
    verify_primary_links(site_dir, errors)
    verify_menu_state(site_dir, errors)
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    """Run rendered-site verification from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site_dir", type=Path, help="Hugo destination directory")
    parser.add_argument(
        "--production", action="store_true", help="Verify production-only artifacts and privacy contracts"
    )
    parser.add_argument("--resume-yaml", type=Path, help="Public resume YAML used to build the production PDF")
    parser.add_argument("--build-run-url", help="Exact GitHub Actions run URL rendered on the homepage")
    args = parser.parse_args(argv)

    errors = verify_site(args.site_dir)
    if args.production:
        if args.resume_yaml is None:
            parser.error("--production requires --resume-yaml PATH")
        if not args.build_run_url:
            parser.error("--production requires --build-run-url URL")
        errors.extend(
            verify_production_site(
                args.site_dir,
                resume_yaml=args.resume_yaml,
                build_run_url=args.build_run_url,
            )
        )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Verified rendered site: {args.site_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
