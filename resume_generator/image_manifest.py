"""Bind immutable vintage image references to the source inputs that built them."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

IMAGE_MANIFEST_PATH = Path("vintage/image-pair.json")
IMAGE_INPUT_PATHS = (
    Path(".dockerignore"),
    Path("vintage/machines/pdp11/Dockerfile.pdp11-pexpect"),
    Path("vintage/machines/pdp11/configs/pdp11-pexpect.ini"),
    Path("vintage/machines/vax/Dockerfile.vax-pexpect"),
    Path("vintage/machines/vax/configs/vax780-pexpect.ini"),
)
IMAGE_INPUTS_LABEL = "io.brfid.vintage.image-inputs-sha256"
IMAGE_MANIFEST_SCHEMA_VERSION = 1
IMAGE_REGISTRY_PREFIX = "registry.gitlab.com/brfid/brfid.gitlab.io"
_IMAGE_INPUTS_DOMAIN = b"brfid-vintage-image-inputs-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_GIT_SHA = re.compile(r"[0-9a-f]{40}")


class ImageManifestError(ValueError):
    """Raised when the promoted image pair is malformed or stale."""


@dataclass(frozen=True)
class ImagePair:
    """Validated immutable references and the source identity that produced them."""

    source_sha: str
    image_inputs_sha256: str
    vax: str
    pdp11: str


_LEGACY_UNLABELED_PAIR = ImagePair(
    source_sha="af9de038b7c9a9759108b79b2a97ffb897cc2936",
    image_inputs_sha256="8c00d86c8fd119ef8bc31194557760e85b6384a522111996a4a34b7e7e033ca4",
    vax=(
        "registry.gitlab.com/brfid/brfid.gitlab.io/vax-pexpect@"
        "sha256:00038ee9451a1da6cbee453f2aeba986cdb3ceb94738dff293ced909f35308d4"
    ),
    pdp11=(
        "registry.gitlab.com/brfid/brfid.gitlab.io/pdp11-pexpect@"
        "sha256:4c566d778d6ef3ca6f6a788f2e6a1aaba1c360912edb9d15043a10cacaa2a38f"
    ),
)


def _add_record(digest: Any, label: str, contents: bytes) -> None:
    label_bytes = label.encode("utf-8")
    digest.update(len(label_bytes).to_bytes(8, byteorder="big"))
    digest.update(label_bytes)
    digest.update(len(contents).to_bytes(8, byteorder="big"))
    digest.update(contents)


def _require_regular_file(path: Path, *, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise ImageManifestError(f"{label} is missing or is not a regular file: {path}")


def _digest_image_inputs(records: Sequence[tuple[Path, bytes]]) -> str:
    digest = hashlib.sha256()
    _add_record(digest, "domain", _IMAGE_INPUTS_DOMAIN)
    for relative_path, contents in records:
        _add_record(digest, relative_path.as_posix(), contents)
    return digest.hexdigest()


def compute_image_inputs_sha256(root: Path) -> str:
    """Hash the exact repository inputs owned by the promoted emulator images."""
    root = root.resolve()
    if not root.is_dir():
        raise ImageManifestError(f"repository root is missing or is not a directory: {root}")

    records: list[tuple[Path, bytes]] = []
    for relative_path in IMAGE_INPUT_PATHS:
        path = root / relative_path
        _require_regular_file(path, label="image input")
        try:
            contents = path.read_bytes()
        except OSError as exc:
            raise ImageManifestError(f"could not read image input {path}: {exc}") from exc
        records.append((relative_path, contents))
    return _digest_image_inputs(records)


def _load_mapping(path: Path) -> Mapping[str, Any]:
    _require_regular_file(path, label="image manifest")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ImageManifestError(f"could not read valid image manifest JSON {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise ImageManifestError(f"image manifest must contain a JSON object: {path}")
    return cast(Mapping[str, Any], value)


def _require_string(manifest: Mapping[str, Any], field: str, pattern: re.Pattern[str]) -> str:
    value = manifest.get(field)
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ImageManifestError(f"image manifest {field} is invalid")
    return value


def _image_reference_pattern(machine: str) -> re.Pattern[str]:
    repository = re.escape(f"{IMAGE_REGISTRY_PREFIX}/{machine}-pexpect")
    return re.compile(rf"{repository}@sha256:[0-9a-f]{{64}}")


def image_manifest_document(*, source_sha: str, image_inputs_sha256: str, vax: str, pdp11: str) -> dict[str, Any]:
    """Build the canonical manifest object emitted by image promotion."""
    return {
        "schema_version": IMAGE_MANIFEST_SCHEMA_VERSION,
        "source_sha": source_sha,
        "image_inputs_sha256": image_inputs_sha256,
        "vax": vax,
        "pdp11": pdp11,
    }


def render_image_manifest(*, source_sha: str, image_inputs_sha256: str, vax: str, pdp11: str) -> str:
    """Render a canonical image manifest after validating every field."""
    document = image_manifest_document(
        source_sha=source_sha,
        image_inputs_sha256=image_inputs_sha256,
        vax=vax,
        pdp11=pdp11,
    )
    _validate_manifest_fields(document)
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def _validate_manifest_fields(manifest: Mapping[str, Any]) -> ImagePair:
    expected_fields = {"schema_version", "source_sha", "image_inputs_sha256", "vax", "pdp11"}
    if set(manifest) != expected_fields:
        raise ImageManifestError("image manifest has unexpected or missing fields")
    if manifest.get("schema_version") != IMAGE_MANIFEST_SCHEMA_VERSION or isinstance(
        manifest.get("schema_version"), bool
    ):
        raise ImageManifestError(f"image manifest schema_version must be {IMAGE_MANIFEST_SCHEMA_VERSION}")

    return ImagePair(
        source_sha=_require_string(manifest, "source_sha", _GIT_SHA),
        image_inputs_sha256=_require_string(manifest, "image_inputs_sha256", _SHA256),
        vax=_require_string(manifest, "vax", _image_reference_pattern("vax")),
        pdp11=_require_string(manifest, "pdp11", _image_reference_pattern("pdp11")),
    )


def load_image_pair(root: Path, manifest_path: Path | None = None) -> ImagePair:
    """Load the promoted pair and fail when its image-owned source has changed."""
    root = root.resolve()
    path = manifest_path or root / IMAGE_MANIFEST_PATH
    pair = _validate_manifest_fields(_load_mapping(path))
    current_digest = compute_image_inputs_sha256(root)
    if pair.image_inputs_sha256 != current_digest:
        raise ImageManifestError(
            "promoted image pair does not match the current image-owned source; build, validate, and promote a new pair"
        )
    return pair


def verify_image_source_commit(root: Path, pair: ImagePair) -> None:
    """Require the manifest digest to match its recorded Git commit's image inputs."""
    root = root.resolve()
    git = shutil.which("git")
    if git is None:
        raise ImageManifestError("git is required to verify the promoted image source commit")
    commit = subprocess.run(  # noqa: S603 - Git is resolved and all arguments are fixed or validated
        [git, "-C", str(root), "cat-file", "-e", f"{pair.source_sha}^{{commit}}"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if commit.returncode:
        raise ImageManifestError("image manifest source_sha is not a commit in this repository")

    records: list[tuple[Path, bytes]] = []
    for relative_path in IMAGE_INPUT_PATHS:
        result = subprocess.run(  # noqa: S603 - Git is resolved and paths are repository constants
            [git, "-C", str(root), "cat-file", "blob", f"{pair.source_sha}:{relative_path.as_posix()}"],
            check=False,
            capture_output=True,
        )
        if result.returncode:
            raise ImageManifestError(f"image input is absent from the manifest source commit: {relative_path}")
        records.append((relative_path, result.stdout))
    if _digest_image_inputs(records) != pair.image_inputs_sha256:
        raise ImageManifestError("image manifest input digest does not match its recorded source commit")


def validate_image_labels(
    pair: ImagePair,
    *,
    machine: str,
    revision: str,
    image_inputs_sha256: str | None,
) -> None:
    """Bind one pulled digest to the source identity recorded by the promoted pair."""
    if machine not in {"vax", "pdp11"}:
        raise ImageManifestError(f"unsupported vintage machine: {machine!r}")
    if revision != pair.source_sha:
        raise ImageManifestError(f"{machine} image revision label does not match the promoted source commit")
    if image_inputs_sha256 is not None:
        if image_inputs_sha256 != pair.image_inputs_sha256:
            raise ImageManifestError(f"{machine} image input label does not match the promoted source digest")
        return
    if pair != _LEGACY_UNLABELED_PAIR:
        raise ImageManifestError(f"{machine} image is missing the required {IMAGE_INPUTS_LABEL} label")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="repository root (default: .)")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify", help="validate the promoted pair and its source inputs")
    subparsers.add_parser("inputs-sha256", help="print the current image-owned source digest")
    field = subparsers.add_parser("field", help="print one validated manifest field")
    field.add_argument("name", choices=("source_sha", "image_inputs_sha256", "vax", "pdp11"))
    labels = subparsers.add_parser("validate-labels", help="validate labels read from one pulled image")
    labels.add_argument("machine", choices=("vax", "pdp11"))
    labels.add_argument("revision")
    labels.add_argument("image_inputs_sha256", help="digest label, or - when the label is absent")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Validate the image manifest or print one trusted reference for the runner."""
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "inputs-sha256":
            print(compute_image_inputs_sha256(args.root))
            return 0
        pair = load_image_pair(args.root)
        verify_image_source_commit(args.root, pair)
        if args.command == "field":
            print(getattr(pair, args.name))
        elif args.command == "validate-labels":
            image_inputs_sha256 = None if args.image_inputs_sha256 == "-" else args.image_inputs_sha256
            validate_image_labels(
                pair,
                machine=args.machine,
                revision=args.revision,
                image_inputs_sha256=image_inputs_sha256,
            )
        else:
            print(f"Validated vintage image pair from {pair.source_sha}")
    except ImageManifestError as exc:
        print(f"vintage image manifest: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
