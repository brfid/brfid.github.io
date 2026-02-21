"""Build a deterministic manifest for published site outputs."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ManifestEntry:
    """A single manifest entry for a published file."""

    relpath: str
    size_bytes: int
    sha256: str


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest_entries(
    *,
    root: Path,
    exclude_relpaths: set[str] | None = None,
) -> list[ManifestEntry]:
    """Build manifest entries for all files under a root directory.

    Args:
        root: Directory containing published outputs (typically `site/`).
        exclude_relpaths: Optional set of repo-relative paths (POSIX style) to exclude.

    Returns:
        List of manifest entries sorted by relative path.
    """
    excludes = exclude_relpaths or set()

    entries: list[ManifestEntry] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel in excludes:
            continue
        entries.append(
            ManifestEntry(
                relpath=rel,
                size_bytes=path.stat().st_size,
                sha256=_sha256_file(path),
            )
        )
    return entries


def render_manifest(entries: list[ManifestEntry]) -> str:
    """Render a stable manifest text file.

    Format:
      `<sha256>  <size_bytes>  <relative_path>`

    Args:
        entries: Entries as returned by `build_manifest_entries`.

    Returns:
        Manifest text with LF newlines and a trailing newline.
    """
    lines = [f"{e.sha256}  {e.size_bytes}  {e.relpath}" for e in entries]
    return "\n".join(lines).rstrip() + "\n"


def write_manifest(*, root: Path, out_path: Path) -> Path:
    """Write a deterministic manifest for files under `root`.

    Args:
        root: Directory to scan (typically `site/`).
        out_path: Destination path for the manifest (typically `site/vintage-manifest.txt`).

    Returns:
        The written path.
    """
    try:
        rel = out_path.relative_to(root).as_posix()
    except ValueError:
        rel = None
    excludes = {rel} if rel else set()
    entries = build_manifest_entries(root=root, exclude_relpaths=excludes)
    out_path.write_text(render_manifest(entries), encoding="utf-8")
    return out_path
