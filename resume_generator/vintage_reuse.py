"""Fingerprint vintage inputs and validate reusable vintage build artifacts."""

from __future__ import annotations

import argparse
import hashlib
import html
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

from .image_manifest import ImageManifestError, load_image_pair
from .pipeline_status import PipelineStatusError, require_successful_pipeline_status
from .vintage_contract import (
    VintageContractError,
    validate_rendered_bio,
    vintage_input_from_mappings,
)

FINGERPRINT_ROOTS = (
    Path(".gitlab-ci.yml"),
    Path("pyproject.toml"),
    Path("requirements/build.lock"),
    Path("requirements/publish.lock"),
    Path("requirements/runtime.lock"),
    Path("resume_generator"),
    Path("scripts"),
    Path("vintage"),
)
FINGERPRINT_EXCLUDED = frozenset(
    {
        Path("resume_generator/pdf.py"),
        Path("scripts/check_environment.py"),
        Path("scripts/verify_site.py"),
    }
)
BUNDLE_FILES = ("brad.bio.txt", "build.log.html", "pipeline-status.json")
PIPELINE_NAME = "edcloud-vintage"
_FINGERPRINT_DOMAIN = b"brfid-vintage-reuse-v1"
_PROJECT_URL = re.compile(r"https://gitlab\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


class VintageReuseError(ValueError):
    """Raised when reusable vintage state is absent, stale, or inconsistent."""


@dataclass(frozen=True)
class ValidatedVintageBundle:
    """Identity consumed after validating a reusable vintage bundle."""

    build_id: str
    source_run_url: str


def _load_mapping(path: Path, *, label: str) -> Mapping[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise VintageReuseError(f"could not read {label} {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise VintageReuseError(f"{label} must contain a top-level mapping: {path}")
    return cast(Mapping[str, Any], value)


def _require_regular_file(path: Path, *, label: str, nonempty: bool) -> None:
    if path.is_symlink() or not path.is_file():
        raise VintageReuseError(f"{label} is missing or is not a regular file: {path}")
    if nonempty and path.stat().st_size == 0:
        raise VintageReuseError(f"{label} is empty: {path}")


def _fingerprinted_files(root: Path) -> list[Path]:
    for relative_path in FINGERPRINT_ROOTS:
        path = root / relative_path
        if path.is_symlink() or not path.exists():
            raise VintageReuseError(f"fingerprint root is missing or unsafe: {path}")
        if not path.is_file() and not path.is_dir():
            raise VintageReuseError(f"fingerprint root is not a regular file or directory: {path}")

    git_dir = root / ".git"
    if git_dir.exists():
        git = shutil.which("git")
        if git is None:
            raise VintageReuseError("git is required to enumerate nonignored fingerprint inputs")
        result = subprocess.run(  # noqa: S603 - executable is resolved and arguments are not passed to a shell
            [
                git,
                "-C",
                str(root),
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
                "--",
                *(path.as_posix() for path in FINGERPRINT_ROOTS),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            detail = result.stderr.strip() or "no output"
            raise VintageReuseError(f"could not enumerate fingerprint inputs with git: {detail}")
        candidates = [root / value for value in result.stdout.split("\0") if value]
    else:
        candidates = []
        for relative_path in FINGERPRINT_ROOTS:
            path = root / relative_path
            candidates.extend([path] if path.is_file() else path.rglob("*"))

    files: list[Path] = []
    for path in candidates:
        relative_path = path.relative_to(root)
        if relative_path in FINGERPRINT_EXCLUDED:
            continue
        if path.is_symlink():
            raise VintageReuseError(f"fingerprint input must not be a symbolic link: {path}")
        if path.is_file():
            files.append(path)
        elif not path.is_dir():
            raise VintageReuseError(f"fingerprint input is not a regular file: {path}")
    if not files:
        raise VintageReuseError("fingerprint roots contain no source files")
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def compute_fingerprint(root: Path, site_yaml: Path, resume_yaml: Path) -> str:
    """Return a deterministic digest of exact bio inputs and vintage implementation files."""
    root = root.resolve()
    if not root.is_dir():
        raise VintageReuseError(f"repository root is missing or is not a directory: {root}")
    try:
        load_image_pair(root)
    except ImageManifestError as exc:
        raise VintageReuseError(f"vintage image pair is invalid: {exc}") from exc

    site = _load_mapping(site_yaml, label="site YAML")
    resume = _load_mapping(resume_yaml, label="resume YAML")
    try:
        vintage_input = vintage_input_from_mappings(site, resume)
    except VintageContractError as exc:
        raise VintageReuseError(f"public vintage input is invalid: {exc}") from exc

    digest = hashlib.sha256()

    def add_record(label: str, value: bytes) -> None:
        label_bytes = label.encode("utf-8")
        digest.update(len(label_bytes).to_bytes(8, byteorder="big"))
        digest.update(label_bytes)
        digest.update(len(value).to_bytes(8, byteorder="big"))
        digest.update(value)

    add_record("domain", _FINGERPRINT_DOMAIN)
    for field, value in (
        ("name", vintage_input.name),
        ("headline", vintage_input.headline),
        ("summary", vintage_input.summary),
    ):
        add_record(f"vintage-input:{field}", value.encode("ascii"))

    for path in _fingerprinted_files(root):
        relative_path = path.relative_to(root).as_posix()
        try:
            contents = path.read_bytes()
        except OSError as exc:
            raise VintageReuseError(f"could not read fingerprint input {path}: {exc}") from exc
        add_record(f"file:{relative_path}", contents)
    return digest.hexdigest()


def validate_source_run_url(source_run_url: str, project_url: str) -> None:
    """Require an exact pipeline URL under the configured GitLab project."""
    if _PROJECT_URL.fullmatch(project_url) is None:
        raise VintageReuseError(f"project URL must identify a GitLab.com project: {project_url!r}")
    pattern = rf"{re.escape(project_url)}/-/pipelines/[1-9][0-9]*"
    if re.fullmatch(pattern, source_run_url) is None:
        raise VintageReuseError(
            f"source GitLab pipeline URL must exactly match {project_url}/-/pipelines/<digits>: {source_run_url!r}"
        )


def _validate_build_log(path: Path, *, build_id: str) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise VintageReuseError(f"could not read vintage build log {path}: {exc}") from exc
    escaped_build_id = html.escape(build_id)
    expected_title = f"<title>{escaped_build_id}: vintage pipeline log</title>"
    expected_label = f'<p class="build-id">build {escaped_build_id}</p>'
    if expected_title not in text or expected_label not in text:
        raise VintageReuseError(f"vintage build log is not tied to build_id {build_id!r}: {path}")


def validate_bundle(  # pylint: disable=too-many-arguments
    bundle_dir: Path,
    site_yaml: Path,
    resume_yaml: Path,
    *,
    source_sha: str,
    source_run_url: str,
    project_url: str,
) -> ValidatedVintageBundle:
    """Validate one prior vintage bundle against its source run and current public bio inputs."""
    if not source_sha or source_sha != source_sha.strip():
        raise VintageReuseError("source SHA must be a nonempty string with no surrounding whitespace")
    validate_source_run_url(source_run_url, project_url)

    paths = {name: bundle_dir / name for name in BUNDLE_FILES}
    for name, path in paths.items():
        _require_regular_file(path, label=f"reusable vintage artifact {name}", nonempty=True)

    try:
        build_id = require_successful_pipeline_status(
            paths["pipeline-status.json"],
            expected_pipeline=PIPELINE_NAME,
            expected_git_sha=source_sha,
        )
    except PipelineStatusError as exc:
        raise VintageReuseError(f"pipeline status {exc}") from exc
    _validate_build_log(paths["build.log.html"], build_id=build_id)

    site = _load_mapping(site_yaml, label="site YAML")
    resume = _load_mapping(resume_yaml, label="resume YAML")
    try:
        expected = vintage_input_from_mappings(site, resume)
        rendered_bio = paths["brad.bio.txt"].read_text(encoding="utf-8")
        validate_rendered_bio(rendered_bio, expected)
    except (OSError, UnicodeError, VintageContractError) as exc:
        raise VintageReuseError(f"reusable vintage bio does not match current public inputs: {exc}") from exc

    return ValidatedVintageBundle(
        build_id=build_id,
        source_run_url=source_run_url,
    )


def _root_relative(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    fingerprint_parser = subparsers.add_parser("fingerprint", help="hash public bio and vintage implementation inputs")
    fingerprint_parser.add_argument("--root", type=Path, default=Path("."), help="repository root (default: .)")
    fingerprint_parser.add_argument("--site-yaml", type=Path, default=Path("site.yaml"))
    fingerprint_parser.add_argument("--resume-yaml", type=Path, default=Path("resume.yaml"))

    validate_parser = subparsers.add_parser("validate", help="validate an extracted prior vintage artifact bundle")
    validate_parser.add_argument("--root", type=Path, default=Path("."), help="repository root (default: .)")
    validate_parser.add_argument("--bundle-dir", type=Path, default=Path("build/vintage"))
    validate_parser.add_argument("--site-yaml", type=Path, default=Path("site.yaml"))
    validate_parser.add_argument("--resume-yaml", type=Path, default=Path("resume.yaml"))
    validate_parser.add_argument("--source-sha", required=True)
    validate_parser.add_argument("--source-run-url", required=True)
    validate_parser.add_argument("--project-url", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run a fingerprint or reusable-bundle validation command."""
    args = _build_parser().parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "fingerprint":
            fingerprint = compute_fingerprint(
                root,
                _root_relative(root, args.site_yaml),
                _root_relative(root, args.resume_yaml),
            )
            print(fingerprint)
            return 0

        bundle = validate_bundle(
            _root_relative(root, args.bundle_dir),
            _root_relative(root, args.site_yaml),
            _root_relative(root, args.resume_yaml),
            source_sha=args.source_sha,
            source_run_url=args.source_run_url,
            project_url=args.project_url,
        )
    except VintageReuseError as exc:
        print(f"vintage reuse: {exc}", file=sys.stderr)
        return 1

    print(f"vintage reuse: validated {bundle.build_id} from {bundle.source_run_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
