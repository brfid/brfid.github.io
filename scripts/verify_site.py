"""Verify contracts that only exist in Hugo's rendered output."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse, urlsplit

import yaml

from resume_generator.pipeline_status import PipelineStatusIssueCode, validate_pipeline_status

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ORIGIN = "https://brfid.gitlab.io"
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
CORE_ALLOWED_FILES = frozenset(REQUIRED_FILES) | {
    "build.log.html",
    "pipeline-status.json",
    "resume.pdf",
}
STATIC_ALLOWED_FILES = frozenset(
    {
        "apple-touch-icon.png",
        "favicon-16x16.png",
        "favicon-32x32.png",
        "favicon.ico",
        "favicon.svg",
        "fonts/newsreader-latin-ext.woff2",
        "fonts/newsreader-latin.woff2",
        "fonts/plex-mono-400-latin-ext.woff2",
        "fonts/plex-mono-400-latin.woff2",
        "fonts/plex-mono-500-latin-ext.woff2",
        "fonts/plex-mono-500-latin.woff2",
        "safari-pinned-tab.svg",
    }
)
STYLESHEET_PATH = re.compile(r"assets/css/stylesheet\.[0-9a-f]{64}\.css")
POST_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
POST_RESOURCE_SUFFIXES = frozenset({".avif", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"})
HUGO_CONFIG = tomllib.loads((ROOT / "hugo" / "hugo.toml").read_text(encoding="utf-8"))
PAGER_SIZE = HUGO_CONFIG["pagination"]["pagerSize"]
TEXT_OUTPUT_SUFFIXES = frozenset({".css", ".html", ".json", ".svg", ".txt", ".xml"})
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
PLAUSIBLE_INTERNATIONAL_PHONE = re.compile(r"(?<![A-Za-z0-9])(?:\+|00\s*)[1-9]\d{0,2}(?:[\s().-]*\d){6,14}(?!\d)")
SECRET_PATTERNS = (
    ("private-key material", re.compile(r"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----")),
    ("GitHub access token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("GitLab access token", re.compile(r"\bgl(?:pat|cbt|deploy|ft|rt|soat)-[A-Za-z0-9_-]{20,}\b")),
    ("AWS access key ID", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    (
        "credential assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)"
            r"\s*[:=]\s*[\"']?[A-Za-z0-9/+_.-]{16,}"
        ),
    ),
)
TAGGED_PDF = re.compile(r"^Tagged:\s+yes\s*$", re.MULTILINE)


def _published_post_outputs(posts_source_dir: Path, errors: list[str]) -> tuple[set[str], set[str]]:
    """Return allowed post pages and source-backed public resources."""
    pages: set[str] = set()
    resources: set[str] = set()
    if posts_source_dir.is_symlink() or not posts_source_dir.is_dir():
        errors.append(f"post source directory is missing or unsafe: {posts_source_dir}")
        return pages, resources

    for bundle in sorted(posts_source_dir.iterdir()):
        if bundle.name.startswith("_"):
            continue
        if bundle.is_symlink() or not bundle.is_dir():
            errors.append(f"post bundle is not a regular directory: {bundle}")
            continue
        if POST_SLUG.fullmatch(bundle.name) is None:
            errors.append(f"post bundle has an unsafe slug: {bundle.name!r}")
            continue
        index = bundle / "index.md"
        if index.is_symlink() or not index.is_file():
            errors.append(f"post bundle has no regular index.md: {bundle}")
            continue
        try:
            source = index.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"could not read post front matter {index}: {exc}")
            continue
        if not source.startswith("---\n") or "\n---\n" not in source[4:]:
            errors.append(f"post must use YAML front matter: {index}")
            continue
        front_matter_text = source[4:].split("\n---\n", maxsplit=1)[0]
        try:
            front_matter = yaml.safe_load(front_matter_text)
        except yaml.YAMLError as exc:
            errors.append(f"post has invalid YAML front matter {index}: {exc}")
            continue
        if not isinstance(front_matter, dict):
            errors.append(f"post front matter must be a mapping: {index}")
            continue
        if front_matter.get("draft") is not False:
            continue

        pages.add(f"posts/{bundle.name}/index.html")
        for resource in sorted(bundle.rglob("*")):
            if resource == index:
                continue
            if resource.is_symlink():
                errors.append(f"published post resource is a symbolic link: {resource}")
                continue
            if resource.is_dir():
                continue
            if not resource.is_file():
                errors.append(f"published post resource is not a regular file: {resource}")
                continue
            relative_resource = resource.relative_to(bundle)
            if any(part.startswith(".") for part in relative_resource.parts):
                errors.append(f"published post resource has a hidden path component: {resource}")
                continue
            if resource.suffix != resource.suffix.lower() or resource.suffix not in POST_RESOURCE_SUFFIXES:
                errors.append(f"published post resource type is not allowed: {resource}")
                continue
            resources.add(f"posts/{bundle.name}/{relative_resource.as_posix()}")
    return pages, resources


def _rendered_files(site_dir: Path, errors: list[str]) -> dict[str, Path]:
    """Enumerate only nonempty regular files without traversing directory links."""
    files: dict[str, Path] = {}
    if site_dir.is_symlink() or not site_dir.is_dir():
        errors.append(f"site directory is missing or unsafe: {site_dir}")
        return files

    for directory, child_directories, child_files in os.walk(site_dir, followlinks=False):
        directory_path = Path(directory)
        for name in list(child_directories):
            child = directory_path / name
            try:
                mode = child.lstat().st_mode
            except OSError as exc:
                errors.append(f"could not inspect rendered directory {child}: {exc}")
                child_directories.remove(name)
                continue
            if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                relative_child = child.relative_to(site_dir)
                errors.append(f"rendered directory is a symbolic link or special entry: {relative_child!s}")
                child_directories.remove(name)
        for name in child_files:
            child = directory_path / name
            relative_path = child.relative_to(site_dir).as_posix()
            try:
                status = child.lstat()
            except OSError as exc:
                errors.append(f"could not inspect rendered output {relative_path}: {exc}")
                continue
            if not stat.S_ISREG(status.st_mode):
                errors.append(f"rendered output is a symbolic link or special entry: {relative_path}")
                continue
            if status.st_size == 0:
                errors.append(f"rendered output is empty: {relative_path}")
            files[relative_path] = child
    return files


def verify_output_policy(site_dir: Path, posts_source_dir: Path, errors: list[str]) -> None:
    """Fail closed unless every rendered path belongs to the explicit Pages contract."""
    post_pages, post_resources = _published_post_outputs(posts_source_dir, errors)
    files = _rendered_files(site_dir, errors)
    if isinstance(PAGER_SIZE, bool) or not isinstance(PAGER_SIZE, int) or PAGER_SIZE <= 0:
        errors.append("Hugo pagination.pagerSize must be a positive integer")
        pagination_paths: set[str] = set()
    else:
        page_count = (len(post_pages) + PAGER_SIZE - 1) // PAGER_SIZE
        pagination_paths = {f"posts/page/{page}/index.html" for page in range(1, page_count + 1)}
    allowed = CORE_ALLOWED_FILES | STATIC_ALLOWED_FILES | post_pages | post_resources | pagination_paths

    stylesheet_paths = sorted(path for path in files if STYLESHEET_PATH.fullmatch(path))
    record(
        len(stylesheet_paths) == 1,
        errors,
        f"rendered output must contain exactly one fingerprinted stylesheet; found {stylesheet_paths!r}",
    )
    for relative_path in sorted(files):
        if relative_path in allowed:
            continue
        if STYLESHEET_PATH.fullmatch(relative_path):
            continue
        errors.append(f"rendered output path is not allowed: {relative_path}")
    for expected_page in sorted(post_pages | pagination_paths):
        record(expected_page in files, errors, f"published page is missing from rendered output: {expected_page}")


def _nested_strings(value: object) -> list[str]:
    """Return every string value in a parsed JSON-compatible structure."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for key, child in value.items():
            strings.extend(_nested_strings(key))
            strings.extend(_nested_strings(child))
        return strings
    if isinstance(value, list):
        strings = []
        for child in value:
            strings.extend(_nested_strings(child))
        return strings
    return []


def _decoded_structured_strings(path: Path, contents: str, errors: list[str]) -> list[str]:
    """Decode strings from public JSON or XML without resolving external content."""
    relative_path = path.name
    if path.suffix.lower() == ".json":
        try:
            return _nested_strings(json.loads(contents))
        except json.JSONDecodeError as exc:
            errors.append(f"{relative_path}: rendered JSON is invalid: {exc}")
            return []
    if path.suffix.lower() in {".svg", ".xml"}:
        try:
            root = ET.fromstring(contents)  # noqa: S314 - rendered local output with no external resolver
        except ET.ParseError as exc:
            errors.append(f"{relative_path}: rendered XML is invalid: {exc}")
            return []
        strings: list[str] = []
        for element in root.iter():
            strings.extend(element.attrib.values())
            if element.text:
                strings.append(element.text)
            if element.tail:
                strings.append(element.tail)
        text_parts = list(root.itertext())
        strings.extend(("".join(text_parts), " ".join(" ".join(text_parts).split())))
        return strings
    return []


def _record_sensitive_text(values: Sequence[str], *, label: str, errors: list[str]) -> None:
    """Record redacted privacy failures across already decoded text values."""
    record(
        all(PLAUSIBLE_US_PHONE.search(value) is None for value in values),
        errors,
        f"{label}: contains a plausible US phone number",
    )
    record(
        all(PLAUSIBLE_INTERNATIONAL_PHONE.search(value) is None for value in values),
        errors,
        f"{label}: contains a plausible international phone number",
    )
    for secret_label, pattern in SECRET_PATTERNS:
        record(
            all(pattern.search(value) is None for value in values),
            errors,
            f"{label}: contains possible {secret_label}",
        )


def verify_public_text(site_dir: Path, errors: list[str]) -> None:
    """Scan raw and decoded text-like output without echoing any matched value."""
    for path in sorted(site_dir.rglob("*")):
        if path.suffix.lower() not in TEXT_OUTPUT_SUFFIXES or path.is_symlink() or not path.is_file():
            continue
        relative_path = path.relative_to(site_dir)
        try:
            contents = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"could not read rendered text {relative_path}: {exc}")
            continue
        _record_sensitive_text([contents], label=str(relative_path), errors=errors)
        decoded = _decoded_structured_strings(path, contents, errors)
        if decoded:
            _record_sensitive_text(decoded, label=f"{relative_path}: decoded data", errors=errors)


class RenderedPageParser(HTMLParser):
    """Collect the small set of HTML fields used by the verifier."""

    def __init__(self) -> None:
        """Initialize collected metadata, links, and JSON-LD blocks."""
        super().__init__()
        self.robots: list[str] = []
        self.anchors: list[dict[str, str]] = []
        self.attribute_values: list[str] = []
        self.json_ld: list[str] = []
        self.text: list[str] = []
        self._json_ld_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collect relevant attributes and begin JSON-LD capture."""
        attributes = {name: value or "" for name, value in attrs}
        self.attribute_values.extend(value for value in attributes.values() if value)
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


def _fully_unescape_html(value: str) -> str:
    """Decode up to three nested HTML-entity layers, stopping once stable."""
    for _ in range(3):
        decoded = html.unescape(value)
        if decoded == value:
            break
        value = decoded
    return value


def decoded_html_values(source: str) -> list[str]:
    """Return decoded attributes and both text-node concatenation forms for an HTML fragment."""
    parser = RenderedPageParser()
    parser.feed(source)
    parser.close()
    values = [
        *parser.attribute_values,
        "".join(parser.text),
        " ".join(" ".join(parser.text).split()),
    ]
    return [_fully_unescape_html(value) for value in values]


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
    record(
        "Disallow: /" not in lines,
        errors,
        "robots.txt: blanket crawl block hides the HTML no-index policy",
    )


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
    """Map one exact-origin, unencoded feed URL beneath the rendered site root."""
    parsed = urlsplit(url)
    if f"{parsed.scheme}://{parsed.netloc}" != PUBLIC_ORIGIN:
        raise ValueError(f"link origin must be exactly {PUBLIC_ORIGIN}")
    if parsed.query or parsed.fragment:
        raise ValueError("link must not contain a query or fragment")
    decoded_path = unquote(parsed.path)
    if decoded_path != parsed.path:
        raise ValueError("link path must not contain percent encoding")
    if not decoded_path.startswith("/") or decoded_path.startswith("//") or "\\" in decoded_path:
        raise ValueError("link path must be one absolute URL path")
    pure_path = PurePosixPath(decoded_path)
    if any(part in {"", ".", ".."} for part in pure_path.parts[1:]):
        raise ValueError("link path contains an unsafe segment")

    site_root = site_dir.resolve(strict=True)
    candidate = site_root.joinpath(*pure_path.parts[1:])
    if decoded_path.endswith("/") or not candidate.suffix:
        candidate /= "index.html"
    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(site_root):
        raise ValueError("link target escapes the rendered site root")
    return resolved


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
        for item_number, item in enumerate(items, start=1):
            description = item.findtext("description", default="")
            link = item.findtext("link", default="").strip()
            item_label = f"{relative_path}: item {item_number}"
            _record_sensitive_text(
                [description, link, *decoded_html_values(description)],
                label=f"{item_label}: decoded content",
                errors=errors,
            )
            record(
                DOUBLE_ESCAPED_QUOTE.search(description) is None,
                errors,
                f"{item_label}: description contains a double-escaped entity",
            )
            record(
                "/resume/" not in urlparse(link).path,
                errors,
                f"{item_label}: resume leaked into feed",
            )
            record(bool(link), errors, f"{item_label}: item has no link")
            if link:
                try:
                    target = rendered_path_for_url(site_dir, link)
                except (OSError, ValueError) as error:
                    errors.append(f"{item_label}: unsafe item link: {error}")
                    continue
                record(
                    target.is_file() and not target.is_symlink(),
                    errors,
                    f"{item_label}: item link has no regular rendered page",
                )


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
        record(
            find_menu_link(homepage, path) is not None,
            errors,
            f"index.html: missing primary link to {path}",
        )

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


def verify_linked_artifacts(site_dir: Path, errors: list[str]) -> None:
    """Require locally linked generated artifacts to exist in the rendered tree."""
    homepage = site_dir / "index.html"
    if not homepage.is_file():
        return
    parser = parse_html(homepage)
    if any(anchor.get("href") == "/build.log.html" for anchor in parser.anchors):
        record(
            is_nonempty_file(site_dir / "build.log.html"),
            errors,
            "index.html: links to missing or empty build.log.html",
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
    validation = validate_pipeline_status(status_path)
    messages = {
        PipelineStatusIssueCode.OBJECT: "expected a JSON object",
        PipelineStatusIssueCode.RESULT: "result is not 'success'",
        PipelineStatusIssueCode.EXIT_CODE: "exit_code is not 0",
        PipelineStatusIssueCode.BUILD_ID: "build_id is missing or empty",
    }
    for issue in validation.issues:
        if issue.code is PipelineStatusIssueCode.READ:
            message = f"could not read valid JSON: {issue.detail}"
        else:
            message = messages.get(issue.code, issue.message)
        errors.append(f"pipeline-status.json: {message}")
    return validation.build_id


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
    """Reject telephone links and decoded privacy leaks in rendered HTML."""
    for path in sorted(site_dir.rglob("*.html")):
        parser = parse_html(path)
        relative_path = path.relative_to(site_dir)
        has_phone_link = any(anchor.get("href", "").strip().lower().startswith("tel:") for anchor in parser.anchors)
        record(not has_phone_link, errors, f"{relative_path}: contains a telephone link")
        decoded_values = [
            *parser.attribute_values,
            "".join(parser.text),
            " ".join(" ".join(parser.text).split()),
        ]
        _record_sensitive_text(
            [_fully_unescape_html(value) for value in decoded_values],
            label=f"{relative_path}: decoded HTML",
            errors=errors,
        )


def verify_resume_pdf(site_dir: Path, public_email: str | None, errors: list[str]) -> None:
    """Check the public email, phone exclusion, and tagged-PDF flag."""
    pdf_path = site_dir / "resume.pdf"
    text = run_external("pdftotext", [str(pdf_path.resolve()), "-"], errors)
    if text is not None:
        if public_email is not None:
            record(public_email in text, errors, "resume.pdf: missing the public basics.email")
        record(
            PLAUSIBLE_US_PHONE.search(text) is None,
            errors,
            "resume.pdf: contains a plausible US phone number",
        )
        record(
            PLAUSIBLE_INTERNATIONAL_PHONE.search(text) is None,
            errors,
            "resume.pdf: contains a plausible international phone number",
        )
        for label, pattern in SECRET_PATTERNS:
            record(pattern.search(text) is None, errors, f"resume.pdf: contains possible {label}")

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
    """Check that the homepage exposes the exact vintage provenance."""
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
    record(
        pdfs == [Path("resume.pdf")],
        errors,
        f"production site PDFs must be exactly ['resume.pdf']; found {pdfs!r}",
    )

    raw_bios = sorted(path.relative_to(site_dir) for path in site_dir.rglob("brad.bio.txt"))
    record(not raw_bios, errors, f"raw brad.bio.txt was published: {raw_bios!r}")
    verify_public_text(site_dir, errors)
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
    verify_output_policy(site_dir, ROOT / "hugo" / "content" / "posts", errors)
    verify_public_text(site_dir, errors)
    verify_html_privacy(site_dir, errors)
    if verify_required_files(site_dir, errors):
        return errors
    verify_robots(site_dir, errors)
    verify_robots_file(site_dir, errors)
    verify_homepage_schema(site_dir, errors)
    verify_feeds(site_dir, errors)
    verify_primary_links(site_dir, errors)
    verify_menu_state(site_dir, errors)
    verify_linked_artifacts(site_dir, errors)
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    """Run rendered-site verification from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site_dir", type=Path, help="Hugo destination directory")
    parser.add_argument(
        "--production",
        action="store_true",
        help="Verify production-only artifacts and privacy contracts",
    )
    parser.add_argument("--resume-yaml", type=Path, help="Public resume YAML used to build the production PDF")
    parser.add_argument("--build-run-url", help="Exact vintage GitLab pipeline URL rendered on the homepage")
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
    errors = list(dict.fromkeys(errors))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Verified rendered site: {args.site_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
