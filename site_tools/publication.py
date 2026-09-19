"""Derive approved public routes from Hugo configuration and post sources."""

from __future__ import annotations

import datetime as dt
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

PUBLIC_ORIGIN = "https://brfid.github.io"
POST_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
POST_RESOURCE_SUFFIXES = frozenset({".avif", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"})
UNSUPPORTED_ROUTING_FIELDS = frozenset({"url", "type", "layout", "outputs", "headless", "build"})


@dataclass(frozen=True)
class SourceCatalog:
    """Expected routes and resources derived from trusted public source files."""

    origin: str
    pager_size: int
    post_pages: frozenset[str]
    aliases: dict[str, str]
    resources: frozenset[str]

    @property
    def pagination_pages(self) -> frozenset[str]:
        """Return Hugo's expected paginator routes, including page 1."""
        if self.pager_size <= 0:
            return frozenset()
        page_count = (len(self.post_pages) + self.pager_size - 1) // self.pager_size
        return frozenset(f"posts/page/{page}/index.html" for page in range(1, page_count + 1))


def _is_finder_metadata(path: Path) -> bool:
    """Ignore only regular Finder metadata."""
    return path.name == ".DS_Store" and not path.is_symlink() and path.is_file()


def _alias_output(alias: str) -> str | None:
    """Map a simple, local post alias to its rendered HTML path."""
    parsed = urlsplit(alias)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or not alias.startswith("/posts/"):
        return None
    if unquote(alias) != alias or "\\" in alias or "//" in alias:
        return None
    segments = alias.strip("/").split("/")
    if len(segments) != 2 or segments[0] != "posts" or POST_SLUG.fullmatch(segments[1]) is None:
        return None
    if alias != f"/posts/{segments[1]}/":
        return None
    return f"posts/{segments[1]}/index.html"


def _is_future(value: object, *, path: Path, errors: list[str], build_date: dt.date) -> bool:
    """Require date-only post dates and reject posts Hugo would publish later."""
    if value is None:
        return False
    if isinstance(value, dt.datetime) or (isinstance(value, str) and len(value) > 10):
        errors.append(f"post date timestamps are unsupported by the publication gate: {path}")
        return True
    try:
        if isinstance(value, dt.date):
            day = value
        elif isinstance(value, str):
            day = dt.date.fromisoformat(value[:10])
        else:
            raise ValueError
    except ValueError:
        errors.append(f"post has an invalid date: {path}")
        return True
    if day > build_date:
        errors.append(f"future-dated post is unsupported by the publication gate: {path}")
        return True
    return False


# pylint: disable=too-many-locals,too-many-branches,too-many-statements
def discover_posts(posts_source_dir: Path, *, origin: str, pager_size: int, errors: list[str]) -> SourceCatalog:
    """Read published bundles and validate their canonical and alias routes."""
    pages: set[str] = set()
    aliases: dict[str, str] = {}
    resources: set[str] = set()
    if posts_source_dir.is_symlink() or not posts_source_dir.is_dir():
        errors.append(f"post source directory is missing or unsafe: {posts_source_dir}")
        return SourceCatalog(origin, pager_size, frozenset(), aliases, frozenset())

    build_date = dt.datetime.now(dt.UTC).date()
    for bundle in sorted(posts_source_dir.iterdir()):
        if bundle.name.startswith("_") or _is_finder_metadata(bundle):
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
        except (OSError, UnicodeError):
            errors.append(f"could not read post front matter: {index}")
            continue
        if not source.startswith("---\n") or "\n---\n" not in source[4:]:
            errors.append(f"post must use YAML front matter: {index}")
            continue
        front_matter_text = source[4:].split("\n---\n", maxsplit=1)[0]
        try:
            front_matter = yaml.safe_load(front_matter_text)
        except yaml.YAMLError:
            errors.append(f"post has invalid YAML front matter: {index}")
            continue
        if not isinstance(front_matter, dict):
            errors.append(f"post front matter must be a mapping: {index}")
            continue
        keys = {str(key).lower(): key for key in front_matter}
        if len(keys) != len(front_matter):
            errors.append(f"post front matter repeats a field with different casing: {index}")
            continue
        if "draft" not in keys or front_matter[keys["draft"]] is not False:
            continue

        unsupported = UNSUPPORTED_ROUTING_FIELDS.intersection(keys)
        if unsupported:
            errors.append(f"post uses unsupported routing fields {sorted(unsupported)!r}: {index}")
            continue
        if "slug" in keys and front_matter[keys["slug"]] != bundle.name:
            errors.append(f"post slug must match its bundle directory: {index}")
            continue
        if "publishdate" in keys or "expirydate" in keys:
            errors.append(f"post scheduling fields are unsupported by the publication gate: {index}")
            continue
        post_date = front_matter[keys["date"]] if "date" in keys else None
        if _is_future(post_date, path=index, errors=errors, build_date=build_date):
            continue
        if "hiddeninrss" in keys and front_matter[keys["hiddeninrss"]] is True:
            errors.append(f"published post cannot be hidden from the complete RSS feeds: {index}")
            continue

        canonical = f"posts/{bundle.name}/index.html"
        pages.add(canonical)
        raw_aliases = front_matter.get(keys["aliases"], []) if "aliases" in keys else []
        if not isinstance(raw_aliases, list):
            errors.append(f"post aliases must be a list: {index}")
            raw_aliases = []
        for alias in raw_aliases:
            output = _alias_output(alias) if isinstance(alias, str) else None
            if output is None:
                errors.append(f"post has an unsafe alias: {index}")
                continue
            if output in aliases or output == canonical:
                errors.append(f"post alias collides with another route: {output}")
                continue
            aliases[output] = canonical

        for resource in sorted(bundle.rglob("*")):
            if resource == index or _is_finder_metadata(resource):
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

    reserved = pages | {"about/index.html", "posts/index.html", "resume/index.html", "index.html"}
    if pager_size > 0:
        reserved |= set(SourceCatalog(origin, pager_size, frozenset(pages), {}, frozenset()).pagination_pages)
    for alias in aliases:
        if alias in reserved:
            errors.append(f"post alias collides with another route: {alias}")
    return SourceCatalog(origin, pager_size, frozenset(pages), aliases, frozenset(resources))


# pylint: enable=too-many-locals,too-many-branches,too-many-statements
def load_catalog(
    repository_root: Path, errors: list[str], *, posts_source_dir: Path | None = None
) -> SourceCatalog | None:
    """Load Hugo configuration at the verification boundary, then inspect post sources.

    Args:
        repository_root: Root containing `hugo/hugo.toml`.
        errors: Receives source and configuration diagnostics without source excerpts.
        posts_source_dir: Optional controlled post corpus for contract tests.

    Returns:
        The source catalog, or `None` when configuration cannot be read.
    """
    config_path = repository_root / "hugo/hugo.toml"
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError):
        errors.append(f"Hugo configuration is missing or invalid: {config_path}")
        return None
    base_url = config.get("baseURL")
    origin = base_url.rstrip("/") if isinstance(base_url, str) else ""
    if origin != PUBLIC_ORIGIN:
        errors.append(f"Hugo baseURL must be {PUBLIC_ORIGIN}: {config_path}")
    pager_size = config.get("pagination", {}).get("pagerSize") if isinstance(config.get("pagination"), dict) else None
    if isinstance(pager_size, bool) or not isinstance(pager_size, int) or pager_size <= 0:
        errors.append("Hugo pagination.pagerSize must be a positive integer")
        pager_size = 0
    rss = config.get("services", {}).get("rss", {}) if isinstance(config.get("services"), dict) else {}
    if isinstance(rss, dict) and rss.get("limit", 0) not in (0, None):
        errors.append("Hugo RSS limit must be unlimited for complete feeds")
    if config.get("buildFuture") is not False or config.get("buildDrafts") is not False:
        errors.append("Hugo must disable future and draft publication")
    if config.get("disableAliases") is not False:
        errors.append("Hugo must enable source-declared aliases")
    posts_source_dir = posts_source_dir or repository_root / "hugo/content/posts"
    return discover_posts(posts_source_dir, origin=PUBLIC_ORIGIN, pager_size=pager_size, errors=errors)
