"""Tests for promoted vintage image provenance."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from resume_generator.image_manifest import (
    IMAGE_INPUT_PATHS,
    IMAGE_MANIFEST_PATH,
    ImageManifestError,
    compute_image_inputs_sha256,
    load_image_pair,
    main,
    render_image_manifest,
    validate_image_labels,
    verify_image_source_commit,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "a" * 40
VAX_REF = f"ghcr.io/brfid/vax-pexpect@sha256:{'1' * 64}"
PDP11_REF = f"ghcr.io/brfid/pdp11-pexpect@sha256:{'2' * 64}"


def _run_git(git: str, root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - git is resolved with shutil.which and arguments are test constants
        [git, "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )


def _commit_image_inputs(root: Path) -> str:
    git = shutil.which("git")
    if git is None:
        pytest.skip("git is required for source-commit verification")
    _run_git(git, root, "init", "--quiet")
    _run_git(git, root, "config", "user.name", "Test User")
    _run_git(git, root, "config", "user.email", "test@example.com")
    _run_git(git, root, "add", ".")
    _run_git(git, root, "commit", "--quiet", "-m", "image inputs")
    return _run_git(git, root, "rev-parse", "HEAD").stdout.strip()


def _write_inputs(root: Path) -> None:
    for relative_path in IMAGE_INPUT_PATHS:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"fixture for {relative_path.as_posix()}\n", encoding="utf-8")


def _write_manifest(root: Path, *, source_sha: str = SOURCE_SHA) -> Path:
    manifest = root / IMAGE_MANIFEST_PATH
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        render_image_manifest(
            source_sha=source_sha,
            image_inputs_sha256=compute_image_inputs_sha256(root),
            vax=VAX_REF,
            pdp11=PDP11_REF,
        ),
        encoding="utf-8",
    )
    return manifest


def test_repository_image_pair_matches_image_owned_source() -> None:
    pair = load_image_pair(ROOT)
    verify_image_source_commit(ROOT, pair)

    assert pair.source_sha == "155972f9f9985266ab9add48ff0a47bda370c477"
    assert pair.vax.endswith("@sha256:bffb6a8b073813eda542fbe92b76075ca745b125639bab43c6d63f8b20b82c54")
    assert pair.pdp11.endswith("@sha256:04e9ded9fa0f80f6d8d41ec07bcd108849dfaf99f39bb670acfe763695fb1ab9")


def test_image_input_digest_is_deterministic_and_covers_every_owned_input(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    original = compute_image_inputs_sha256(tmp_path)

    assert re.fullmatch(r"[0-9a-f]{64}", original)
    assert compute_image_inputs_sha256(tmp_path) == original
    for relative_path in IMAGE_INPUT_PATHS:
        path = tmp_path / relative_path
        prior = path.read_bytes()
        path.write_bytes(prior + b"changed\n")
        assert compute_image_inputs_sha256(tmp_path) != original
        path.write_bytes(prior)


def test_manifest_rejects_changed_image_owned_source(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    _write_manifest(tmp_path)
    (tmp_path / IMAGE_INPUT_PATHS[0]).write_text("changed image policy\n", encoding="utf-8")

    with pytest.raises(ImageManifestError, match="does not match the current image-owned source"):
        load_image_pair(tmp_path)


@pytest.mark.parametrize("field", ("schema_version", "source_sha", "image_inputs_sha256", "vax", "pdp11"))
def test_manifest_rejects_missing_fields(tmp_path: Path, field: str) -> None:
    _write_inputs(tmp_path)
    manifest = _write_manifest(tmp_path)
    document = json.loads(manifest.read_text(encoding="utf-8"))
    del document[field]
    manifest.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ImageManifestError, match="unexpected or missing fields"):
        load_image_pair(tmp_path)


def test_manifest_rejects_mutable_or_cross_project_references(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    manifest = _write_manifest(tmp_path)
    document = json.loads(manifest.read_text(encoding="utf-8"))
    document["vax"] = "ghcr.io/another/vax-pexpect:latest"
    manifest.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ImageManifestError, match="image manifest vax is invalid"):
        load_image_pair(tmp_path)


def test_manifest_cli_prints_only_the_validated_requested_reference(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_inputs(tmp_path)
    source_sha = _commit_image_inputs(tmp_path)
    _write_manifest(tmp_path, source_sha=source_sha)

    assert main(["--root", str(tmp_path), "field", "pdp11"]) == 0
    assert capsys.readouterr().out == f"{PDP11_REF}\n"


def test_repository_image_pair_requires_both_provenance_labels() -> None:
    pair = load_image_pair(ROOT)

    for machine in ("vax", "pdp11"):
        validate_image_labels(
            pair,
            machine=machine,
            revision=pair.source_sha,
            image_inputs_sha256=pair.image_inputs_sha256,
        )
        with pytest.raises(ImageManifestError, match="missing the required"):
            validate_image_labels(
                pair,
                machine=machine,
                revision=pair.source_sha,
                image_inputs_sha256=None,
            )
    with pytest.raises(ImageManifestError, match="revision label does not match"):
        validate_image_labels(
            pair,
            machine="vax",
            revision="b" * 40,
            image_inputs_sha256=pair.image_inputs_sha256,
        )


def test_image_pairs_require_the_input_digest_label(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    _write_manifest(tmp_path)
    pair = load_image_pair(tmp_path)

    validate_image_labels(
        pair,
        machine="pdp11",
        revision=pair.source_sha,
        image_inputs_sha256=pair.image_inputs_sha256,
    )
    with pytest.raises(ImageManifestError, match="missing the required"):
        validate_image_labels(
            pair,
            machine="pdp11",
            revision=pair.source_sha,
            image_inputs_sha256=None,
        )
    with pytest.raises(ImageManifestError, match="input label does not match"):
        validate_image_labels(
            pair,
            machine="pdp11",
            revision=pair.source_sha,
            image_inputs_sha256="f" * 64,
        )


def test_source_commit_digest_must_match_the_promoted_manifest(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    source_sha = _commit_image_inputs(tmp_path)
    (tmp_path / IMAGE_INPUT_PATHS[0]).write_text("different current policy\n", encoding="utf-8")
    _write_manifest(tmp_path, source_sha=source_sha)
    pair = load_image_pair(tmp_path)

    with pytest.raises(ImageManifestError, match="does not match its recorded source commit"):
        verify_image_source_commit(tmp_path, pair)
