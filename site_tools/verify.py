"""Verify the generated public HTML, feeds, assets, and resume PDF."""

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
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urljoin, urlparse, urlsplit

import yaml

from site_tools.publication import PUBLIC_ORIGIN, SourceCatalog, load_catalog

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "404.html",
    "about/index.html",
    "index.html",
    "index.xml",
    "posts/doc-rot-maintenance-gap/index.html",
    "posts/index.html",
    "posts/index.xml",
    "resume/index.html",
    "robots.txt",
)
CORE_ALLOWED_FILES = frozenset(REQUIRED_FILES) | {
    "resume.pdf",
}
LEGACY_ALIAS_TARGETS = {
    "about/index.html": "resume/index.html",
    "posts/doc-rot-maintenance-gap/index.html": "posts/doc-rot-e2e/index.html",
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
        "fonts/source-serif4-italic.woff2",
        "fonts/source-serif4-roman.woff2",
        "safari-pinned-tab.svg",
    }
)
STYLESHEET_PATH = re.compile(r"assets/css/stylesheet\.[0-9a-f]{64}\.css")
TEXT_OUTPUT_SUFFIXES = frozenset({".css", ".html", ".json", ".svg", ".txt", ".xml"})
REQUIRED_ROBOTS_DIRECTIVES = frozenset({"noarchive", "nofollow", "noimageindex", "noindex", "nosnippet"})
EXPECTED_ROBOTS_LINES = (
    "User-agent: archive.org_bot",
    "User-agent: ia_archiver",
    "User-agent: CCBot",
    "Disallow: /",
    "User-agent: *",
    "Allow: /",
    "Disallow: /resume.pdf",
    "Disallow: /index.xml",
    "Disallow: /posts/index.xml",
)
DOUBLE_ESCAPED_QUOTE = re.compile(r"&#(?:34|39|x22|x27);", re.IGNORECASE)
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


def _is_finder_metadata(path: Path) -> bool:
    """Ignore regular Finder metadata without exempting symlinks or other hidden files."""
    return path.name == ".DS_Store" and not path.is_symlink() and path.is_file()


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
            if _is_finder_metadata(child):
                continue
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


def verify_output_policy(
    site_dir: Path,
    posts_source_dir: Path,
    errors: list[str],
    *,
    catalog: SourceCatalog | None = None,
    files: dict[str, Path] | None = None,
) -> set[str]:
    """Check source-backed output paths and return canonical post pages."""
    if catalog is None:
        catalog = load_catalog(ROOT, errors, posts_source_dir=posts_source_dir)
    if files is None:
        files = _rendered_files(site_dir, errors)
    if catalog is None:
        return set()
    post_pages = set(catalog.post_pages)
    pagination_paths = set(catalog.pagination_pages)
    allowed = (
        CORE_ALLOWED_FILES
        | STATIC_ALLOWED_FILES
        | post_pages
        | catalog.resources
        | catalog.aliases.keys()
        | pagination_paths
    )

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
    for expected_page in sorted(post_pages | pagination_paths | catalog.aliases.keys()):
        record(expected_page in files, errors, f"published page is missing from rendered output: {expected_page}")
    return post_pages


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


def verify_public_text(site_dir: Path, errors: list[str], *, texts: dict[str, str] | None = None) -> None:
    """Scan raw and decoded text-like output without echoing any matched value."""
    if texts is None:
        texts = load_rendered_artifact(site_dir, errors).texts
    for relative_path, contents in sorted(texts.items()):
        _record_sensitive_text([contents], label=relative_path, errors=errors)
        decoded = _decoded_structured_strings(Path(relative_path), contents, errors)
        if decoded:
            _record_sensitive_text(decoded, label=f"{relative_path}: decoded data", errors=errors)


class RenderedPageParser(HTMLParser):
    """Collect the small set of HTML fields used by the verifier."""

    def __init__(self) -> None:
        """Initialize collected metadata, links, and JSON-LD blocks."""
        super().__init__()
        self.robots: list[str] = []
        self.crawler_robots: list[str] = []
        self.anchors: list[dict[str, str]] = []
        self.canonical_urls: list[str] = []
        self.refresh_urls: list[str] = []
        self.attribute_values: list[str] = []
        self.json_ld: list[str] = []
        self.text: list[str] = []
        self.article_body_parts: list[str] = []
        self._body_depth = 0
        self._json_ld_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collect relevant attributes and begin JSON-LD capture."""
        attributes = {name: value or "" for name, value in attrs}
        if self._body_depth:
            self.article_body_parts.append(self.get_starttag_text() or f"<{tag}>")
            if tag == "div":
                self._body_depth += 1
        elif tag == "div" and {"post-content", "md-content"} <= set(attributes.get("class", "").split()):
            self._body_depth = 1
        self.attribute_values.extend(value for value in attributes.values() if value)
        if tag == "meta" and attributes.get("name", "").lower() == "robots":
            self.robots.append(attributes.get("content", ""))
        elif tag == "meta" and attributes.get("name", "").lower() in {"googlebot", "googlebot-news", "bingbot"}:
            self.crawler_robots.append(attributes.get("content", ""))
        elif tag == "a":
            self.anchors.append(attributes)
        elif tag == "link" and "canonical" in attributes.get("rel", "").split():
            self.canonical_urls.append(attributes.get("href", ""))
        elif tag == "meta" and attributes.get("http-equiv", "").lower() == "refresh":
            self.refresh_urls.append(attributes.get("content", ""))
        elif tag == "script" and attributes.get("type", "").lower() == "application/ld+json":
            self._json_ld_parts = []

    def handle_data(self, data: str) -> None:
        """Capture rendered text and any active JSON-LD script."""
        self.text.append(data)
        if self._body_depth:
            self.article_body_parts.append(html.escape(data, quote=False))
        if self._json_ld_parts is not None:
            self._json_ld_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        """Finish JSON-LD capture when its script closes."""
        if self._body_depth:
            if tag == "div":
                self._body_depth -= 1
            if self._body_depth:
                self.article_body_parts.append(f"</{tag}>")
        if tag == "script" and self._json_ld_parts is not None:
            self.json_ld.append("".join(self._json_ld_parts))
            self._json_ld_parts = None


@dataclass
class RenderedArtifact:
    """Safe file inventory and decoded documents for one verification run."""

    files: dict[str, Path]
    texts: dict[str, str]
    pages: dict[str, RenderedPageParser]


def load_rendered_artifact(site_dir: Path, errors: list[str]) -> RenderedArtifact:
    """Inventory once, then read and parse each safe text file at most once."""
    files = _rendered_files(site_dir, errors)
    texts: dict[str, str] = {}
    pages: dict[str, RenderedPageParser] = {}
    for relative_path, path in sorted(files.items()):
        if path.suffix.lower() not in TEXT_OUTPUT_SUFFIXES:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            errors.append(f"could not read rendered text: {relative_path}")
            continue
        texts[relative_path] = source
        if path.suffix.lower() == ".html":
            parser = RenderedPageParser()
            try:
                parser.feed(source)
                parser.close()
            except ValueError:
                errors.append(f"could not parse rendered HTML: {relative_path}")
                continue
            pages[relative_path] = parser
    return RenderedArtifact(files, texts, pages)


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


def verify_required_files(site_dir: Path, errors: list[str], *, files: dict[str, Path] | None = None) -> bool:
    """Check public routes and return whether a required input is missing."""
    if files is None:
        files = _rendered_files(site_dir, errors)
    missing = False
    for relative_path in REQUIRED_FILES:
        path = files.get(relative_path)
        try:
            available = path is not None and path.stat().st_size > 0
        except OSError:
            available = False
        record(available, errors, f"missing or empty: {relative_path}")
        missing = missing or not available
    return missing


def verify_robots(site_dir: Path, errors: list[str], *, pages: dict[str, RenderedPageParser] | None = None) -> None:
    """Require the complete no-index policy on every HTML page."""
    if pages is None:
        pages = load_rendered_artifact(site_dir, errors).pages
    for relative_path, parser in sorted(pages.items()):
        directives = [
            {directive.strip().lower() for directive in content.split(",") if directive.strip()}
            for content in parser.robots
        ]
        all_directives = set().union(*directives) if directives else set()
        for content in parser.crawler_robots:
            all_directives.update(directive.strip().lower() for directive in content.split(",") if directive.strip())
        record(
            any(directive_set >= REQUIRED_ROBOTS_DIRECTIVES for directive_set in directives),
            errors,
            f"{relative_path}: missing full robots no-index policy",
        )
        record(
            all_directives <= REQUIRED_ROBOTS_DIRECTIVES,
            errors,
            f"{relative_path}: conflicting robots index/follow policy",
        )


def verify_no_sitemap(site_dir: Path, errors: list[str]) -> None:
    """Reject a stale sitemap when every HTML page is excluded from indexing."""
    sitemap = site_dir / "sitemap.xml"
    record(
        not sitemap.exists() and not sitemap.is_symlink(),
        errors,
        "sitemap.xml: must not be published while all HTML is excluded from indexing",
    )


def verify_robots_file(site_dir: Path, errors: list[str], *, texts: dict[str, str] | None = None) -> None:
    """Check the crawl policy for HTML and public machine-readable artifacts."""
    if texts is None:
        texts = load_rendered_artifact(site_dir, errors).texts
    contents = texts.get("robots.txt")
    if contents is None:
        return
    lines = [line.strip() for line in contents.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    record(
        lines == list(EXPECTED_ROBOTS_LINES),
        errors,
        f"robots.txt: unexpected directives: {lines!r}",
    )


def verify_homepage_schema(
    site_dir: Path, errors: list[str], *, pages: dict[str, RenderedPageParser] | None = None
) -> None:
    """Require parseable homepage JSON-LD with `@type: Person`."""
    if pages is None:
        pages = load_rendered_artifact(site_dir, errors).pages
    parser = pages.get("index.html")
    if parser is None:
        return
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


class _BodySignature(HTMLParser):
    """Capture article text, structure, destinations, and note relationships."""

    BLOCK_TAGS = frozenset({"p", "li", "ol", "ul", "blockquote", "pre", "code", "table", "tr", "th", "td"})
    HEADINGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})

    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []
        self.blocks: list[str] = []
        self.headings: list[tuple[str, str]] = []
        self.links: list[str] = []
        self.images: list[tuple[str, str]] = []
        self.note_ids: list[str] = []
        self._heading: tuple[str, list[str]] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag in self.BLOCK_TAGS:
            self.blocks.append(tag)
        if tag in self.HEADINGS:
            self._heading = (tag, [])
        if tag == "a":
            self.links.append(attributes.get("href") or "")
        if tag == "img":
            self.images.append((attributes.get("src") or "", attributes.get("alt") or ""))
        if tag in {"sup", "li"} and (attributes.get("id") or "").startswith(("fn:", "fnref:")):
            self.note_ids.append(attributes["id"] or "")

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)
        if self._heading is not None:
            self._heading[1].append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._heading is not None and self._heading[0] == tag:
            self.headings.append((tag, " ".join("".join(self._heading[1]).split())))
            self._heading = None

    def signature(self) -> tuple[object, ...]:
        """Return a stable comparison that ignores HTML serialization details."""
        return (
            " ".join("".join(self.text_parts).split()),
            tuple(self.blocks),
            tuple(self.headings),
            tuple(self.links),
            tuple(self.images),
            tuple(self.note_ids),
        )


def body_signature(fragment: str) -> tuple[object, ...]:
    """Normalize a rendered article or RSS body for completeness checks."""
    parser = _BodySignature()
    parser.feed(fragment)
    parser.close()
    return parser.signature()


def verify_feeds(
    site_dir: Path,
    errors: list[str],
    *,
    texts: dict[str, str] | None = None,
    catalog: SourceCatalog | None = None,
    pages: dict[str, RenderedPageParser] | None = None,
) -> None:
    """Require full-text feed items, safe post targets, and correctly escaped descriptions."""
    if texts is None:
        texts = load_rendered_artifact(site_dir, errors).texts
    expected = (
        {f"{catalog.origin}/{path.removesuffix('index.html')}": path for path in catalog.post_pages}
        if catalog is not None
        else {}
    )
    for relative_path in ("index.xml", "posts/index.xml"):
        contents = texts.get(relative_path)
        if contents is None:
            continue
        try:
            # The input is the local Hugo build, not externally supplied XML.
            root = ET.fromstring(contents)  # noqa: S314
        except ET.ParseError as error:
            errors.append(f"{relative_path}: invalid XML: {error}")
            continue

        items = root.findall("./channel/item")
        record(bool(items), errors, f"{relative_path}: feed has no items")
        seen: set[str] = set()
        for item_number, item in enumerate(items, start=1):
            description = item.findtext("description", default="")
            content = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded", default="")
            link = item.findtext("link", default="").strip()
            item_label = f"{relative_path}: item {item_number}"
            record(bool(content.strip()), errors, f"{item_label}: missing full-text content:encoded")
            _record_sensitive_text(
                [description, content, link, *decoded_html_values(description), *decoded_html_values(content)],
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
            if catalog is not None:
                record(link in expected, errors, f"{item_label}: item target is not a canonical published post")
                record(link not in seen, errors, f"{item_label}: duplicate canonical post")
                seen.add(link)
                record(
                    item.findtext("guid", default="").strip() == link, errors, f"{item_label}: GUID differs from link"
                )
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
            if catalog is not None and pages is not None and link in expected and content.strip():
                article = pages.get(expected[link])
                if article is not None:
                    record(
                        body_signature(content) == body_signature("".join(article.article_body_parts)),
                        errors,
                        f"{item_label}: full-text body differs from rendered article",
                    )
        if catalog is not None:
            for missing in sorted(expected.keys() - seen):
                errors.append(f"{relative_path}: missing published post item: {missing}")


def _local_link_path(href: str, source_page: str, origin: str) -> str | None:
    """Resolve safe local navigation forms without accepting foreign origins."""
    parsed = urlsplit(href)
    if parsed.query or parsed.fragment or unquote(parsed.path) != parsed.path:
        return None
    if "\\" in parsed.path or parsed.path.startswith("//"):
        return None
    if any(segment in {".", ".."} for segment in parsed.path.split("/")):
        return None
    page_url = f"{origin}/{source_page.removesuffix('index.html')}"
    resolved = urlsplit(urljoin(page_url, href))
    if f"{resolved.scheme}://{resolved.netloc}" != origin:
        return None
    return resolved.path


def find_link(
    parser: RenderedPageParser,
    path: str,
    required_class: str | None = None,
    *,
    source_page: str = "index.html",
    origin: str = PUBLIC_ORIGIN,
) -> dict[str, str] | None:
    """Find a safe rendered link by resolved origin and path."""
    for anchor in parser.anchors:
        if _local_link_path(anchor.get("href", ""), source_page, origin) != path:
            continue
        if required_class is None or required_class in anchor.get("class", "").split():
            return anchor
    return None


def verify_primary_links(
    site_dir: Path, errors: list[str], *, pages: dict[str, RenderedPageParser] | None = None
) -> None:
    """Check primary routes and contextual feed/PDF actions."""
    if pages is None:
        pages = load_rendered_artifact(site_dir, errors).pages
    homepage = pages.get("index.html")
    if homepage is not None:
        for path in ("/posts/", "/resume/"):
            record(
                find_link(homepage, path, "menu-primary-link", source_page="index.html") is not None,
                errors,
                f"index.html: missing primary link to {path}",
            )

    posts = pages.get("posts/index.html")
    if posts is not None:
        record(
            find_link(posts, "/posts/index.xml", "section-feed-link", source_page="posts/index.html") is not None,
            errors,
            "posts/index.html: missing section RSS link",
        )

    resume = pages.get("resume/index.html")
    if resume is not None:
        record(
            find_link(resume, "/resume.pdf", "resume-download-link", source_page="resume/index.html") is not None,
            errors,
            "resume/index.html: missing resume PDF link",
        )


def verify_menu_state(
    site_dir: Path,
    post_pages: set[str],
    errors: list[str],
    *,
    pages: dict[str, RenderedPageParser] | None = None,
) -> None:
    """Check current menu states on source-backed canonical pages."""
    if pages is None:
        pages = load_rendered_artifact(site_dir, errors).pages
    expected_states = {
        "posts/index.html": ("/posts/", "page"),
        "resume/index.html": ("/resume/", "page"),
    }
    for post_path in post_pages:
        expected_states[post_path] = ("/posts/", "location")

    for relative_path, (menu_path, expected_state) in sorted(expected_states.items()):
        parser = pages.get(relative_path)
        if parser is None:
            continue
        link = find_link(parser, menu_path, "menu-primary-link", source_page=relative_path)
        record(link is not None, errors, f"{relative_path}: missing menu link to {menu_path}")
        if link is not None:
            record(
                link.get("aria-current") == expected_state,
                errors,
                f"{relative_path}: {menu_path} has aria-current={link.get('aria-current')!r}, "
                f"expected {expected_state!r}",
            )


def verify_aliases(catalog: SourceCatalog, pages: dict[str, RenderedPageParser], errors: list[str]) -> None:
    """Require each compatibility redirect to point at its approved canonical page."""
    aliases = LEGACY_ALIAS_TARGETS | catalog.aliases
    for alias_path, target_path in sorted(aliases.items()):
        page = pages.get(alias_path)
        if page is None:
            continue
        expected = f"{catalog.origin}/{target_path.removesuffix('index.html')}"
        record(
            page.canonical_urls == [expected],
            errors,
            f"{alias_path}: incorrect canonical redirect target",
        )
        record(
            page.refresh_urls == [f"0; url={expected}"],
            errors,
            f"{alias_path}: incorrect refresh redirect target",
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
    except (OSError, UnicodeError, yaml.YAMLError):
        errors.append(f"could not read resume YAML: {resume_yaml}")
        return None
    if not isinstance(data, dict) or not isinstance(data.get("basics"), dict):
        errors.append(f"resume YAML has no basics mapping: {resume_yaml}")
        return None
    email = data["basics"].get("email")
    if not isinstance(email, str) or not email.strip():
        errors.append(f"resume YAML has no public basics.email: {resume_yaml}")
        return None
    return email.strip()


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
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        errors.append(f"could not run {command}: {error}")
        return None
    if result.returncode:
        errors.append(f"{command} failed with exit code {result.returncode}")
        return None
    return result.stdout


def verify_html_privacy(
    site_dir: Path, errors: list[str], *, pages: dict[str, RenderedPageParser] | None = None
) -> None:
    """Reject telephone links and decoded privacy leaks in rendered HTML."""
    if pages is None:
        pages = load_rendered_artifact(site_dir, errors).pages
    for relative_path, parser in sorted(pages.items()):
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
        _record_sensitive_text([text], label="resume.pdf", errors=errors)

    info = run_external("pdfinfo", [str(pdf_path.resolve())], errors)
    if info is not None:
        record(TAGGED_PDF.search(info) is not None, errors, "resume.pdf: PDF is not tagged")


def verify_resume_artifacts(site_dir: Path, *, resume_yaml: Path, files: dict[str, Path] | None = None) -> list[str]:
    """Require one complete public PDF in every verified build."""
    errors: list[str] = []
    if files is None:
        files = _rendered_files(site_dir, errors)
    pdfs = sorted(Path(path) for path in files if Path(path).suffix.lower() == ".pdf")
    record(pdfs == [Path("resume.pdf")], errors, f"site PDFs must be exactly ['resume.pdf']; found {pdfs!r}")
    public_email = read_public_email(resume_yaml, errors)
    pdf = site_dir / "resume.pdf"
    if "resume.pdf" not in files or pdf.is_symlink() or not is_nonempty_file(pdf):
        errors.append("missing, empty, or unsafe public artifact: resume.pdf")
    else:
        verify_resume_pdf(site_dir, public_email, errors)
    return errors


def verify_site(
    site_dir: Path, *, catalog: SourceCatalog | None = None, artifact: RenderedArtifact | None = None
) -> list[str]:
    """Validate public HTML, feeds, indexing, and the allowed output paths."""
    errors: list[str] = []
    if artifact is None:
        artifact = load_rendered_artifact(site_dir, errors)
        if catalog is None:
            catalog = load_catalog(ROOT, errors)
    post_pages: set[str] = set()
    if catalog is not None:
        post_pages = verify_output_policy(
            site_dir, ROOT / "hugo/content/posts", errors, catalog=catalog, files=artifact.files
        )
    verify_public_text(site_dir, errors, texts=artifact.texts)
    verify_html_privacy(site_dir, errors, pages=artifact.pages)
    verify_required_files(site_dir, errors, files=artifact.files)
    verify_robots(site_dir, errors, pages=artifact.pages)
    verify_robots_file(site_dir, errors, texts=artifact.texts)
    verify_no_sitemap(site_dir, errors)
    verify_homepage_schema(site_dir, errors, pages=artifact.pages)
    verify_feeds(site_dir, errors, texts=artifact.texts, catalog=catalog, pages=artifact.pages)
    verify_primary_links(site_dir, errors, pages=artifact.pages)
    verify_menu_state(site_dir, post_pages, errors, pages=artifact.pages)
    if catalog is not None:
        verify_aliases(catalog, artifact.pages, errors)
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    """Run rendered-site verification from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site_dir", type=Path, help="Hugo destination directory")
    parser.add_argument(
        "--source-root", type=Path, default=ROOT, help="Repository containing Hugo configuration and posts"
    )
    parser.add_argument("--resume-yaml", type=Path, help="Canonical public resume source")
    args = parser.parse_args(argv)

    errors: list[str] = []
    catalog = load_catalog(args.source_root, errors)
    artifact = load_rendered_artifact(args.site_dir, errors)
    errors.extend(verify_site(args.site_dir, catalog=catalog, artifact=artifact))
    resume_yaml = args.resume_yaml or args.source_root / "resume.yaml"
    errors.extend(verify_resume_artifacts(args.site_dir, resume_yaml=resume_yaml, files=artifact.files))
    errors = list(dict.fromkeys(errors))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Verified rendered site: {args.site_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
