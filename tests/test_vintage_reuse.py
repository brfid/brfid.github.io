"""Tests for reusable vintage artifact validation and fingerprinting."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from resume_generator.vintage_reuse import (
    BUNDLE_FILES,
    FINGERPRINT_FILES,
    VintageReuseError,
    compute_fingerprint,
    main,
    validate_bundle,
)

NAME = "Test User"
HEADLINE = "Principal Technical Writer"
SUMMARY = "Keeps documentation true as products change."
BUILD_ID = "build-20260824-120000"
SOURCE_SHA = "a" * 40
PROJECT_URL = "https://gitlab.com/example/site"
SOURCE_RUN_URL = "https://gitlab.com/example/site/-/pipelines/123456"
BIO_TEXT = f"{NAME}\n{HEADLINE}\n\n{SUMMARY}\n"


def _write_public_inputs(
    root: Path,
    *,
    name: str = NAME,
    headline: str = HEADLINE,
    summary: str = SUMMARY,
    link: str = "https://example.com/one",
    email: str = "one@example.com",
) -> tuple[Path, Path]:
    site_yaml = root / "site.yaml"
    site_yaml.write_text(
        f"name: {name}\nheadline: {headline}\nlinks:\n  - url: {link}\n",
        encoding="utf-8",
    )
    resume_yaml = root / "resume.yaml"
    resume_yaml.write_text(
        f"basics:\n  summary: {summary}\n  email: {email}\nwork:\n  - name: Irrelevant employer\n",
        encoding="utf-8",
    )
    return site_yaml, resume_yaml


def _write_fingerprint_tree(root: Path) -> tuple[Path, Path]:
    for relative_path in FINGERPRINT_FILES:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"fixture for {relative_path.as_posix()}\n", encoding="utf-8")
    vintage_file = root / "vintage" / "machines" / "fixture.txt"
    vintage_file.parent.mkdir(parents=True)
    vintage_file.write_text("vintage fixture\n", encoding="utf-8")
    return _write_public_inputs(root)


def _base_status() -> dict[str, object]:
    return {
        "pipeline": "edcloud-vintage",
        "build_id": BUILD_ID,
        "git_sha": SOURCE_SHA,
        "completed_at": "2026-08-24T12:00:00Z",
        "exit_code": 0,
        "result": "success",
        "stages": {},
    }


def _build_log(build_id: str = BUILD_ID) -> str:
    return (
        "<!DOCTYPE html>\n"
        "<html><head>"
        f"<title>{build_id}: vintage pipeline log</title>"
        "</head><body>"
        f'<p class="build-id">build {build_id}</p>'
        "</body></html>\n"
    )


def _write_bundle(root: Path) -> tuple[Path, Path, Path]:
    site_yaml, resume_yaml = _write_public_inputs(root)
    bundle_dir = root / "build" / "vintage"
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "brad.bio.txt").write_text(BIO_TEXT, encoding="utf-8")
    (bundle_dir / "build.log.html").write_text(_build_log(), encoding="utf-8")
    (bundle_dir / "pipeline-status.json").write_text(json.dumps(_base_status()) + "\n", encoding="utf-8")
    return bundle_dir, site_yaml, resume_yaml


def _validate(bundle_dir: Path, site_yaml: Path, resume_yaml: Path) -> None:
    validate_bundle(
        bundle_dir,
        site_yaml,
        resume_yaml,
        source_sha=SOURCE_SHA,
        source_run_url=SOURCE_RUN_URL,
        project_url=PROJECT_URL,
    )


def test_fingerprint_is_deterministic_and_sha256(tmp_path: Path) -> None:
    site_yaml, resume_yaml = _write_fingerprint_tree(tmp_path)

    first = compute_fingerprint(tmp_path, site_yaml, resume_yaml)
    second = compute_fingerprint(tmp_path, site_yaml, resume_yaml)

    assert first == second
    assert re.fullmatch(r"[0-9a-f]{64}", first)


def test_irrelevant_site_and_resume_fields_do_not_change_fingerprint(tmp_path: Path) -> None:
    site_yaml, resume_yaml = _write_fingerprint_tree(tmp_path)
    original = compute_fingerprint(tmp_path, site_yaml, resume_yaml)

    _write_public_inputs(
        tmp_path,
        link="https://example.com/two",
        email="two@example.com",
    )

    assert compute_fingerprint(tmp_path, site_yaml, resume_yaml) == original


@pytest.mark.parametrize(
    ("changed_field", "value"),
    (("name", "Another User"), ("headline", "Another Headline"), ("summary", "Another summary.")),
)
def test_each_public_vintage_field_changes_fingerprint(tmp_path: Path, changed_field: str, value: str) -> None:
    site_yaml, resume_yaml = _write_fingerprint_tree(tmp_path)
    original = compute_fingerprint(tmp_path, site_yaml, resume_yaml)
    values = {"name": NAME, "headline": HEADLINE, "summary": SUMMARY}
    values[changed_field] = value

    _write_public_inputs(tmp_path, **values)

    assert compute_fingerprint(tmp_path, site_yaml, resume_yaml) != original


@pytest.mark.parametrize("relative_path", FINGERPRINT_FILES, ids=lambda path: path.as_posix())
def test_each_guarded_file_changes_fingerprint(tmp_path: Path, relative_path: Path) -> None:
    site_yaml, resume_yaml = _write_fingerprint_tree(tmp_path)
    original = compute_fingerprint(tmp_path, site_yaml, resume_yaml)
    path = tmp_path / relative_path

    path.write_bytes(path.read_bytes() + b"changed\n")

    assert compute_fingerprint(tmp_path, site_yaml, resume_yaml) != original


def test_every_file_under_vintage_is_guarded(tmp_path: Path) -> None:
    site_yaml, resume_yaml = _write_fingerprint_tree(tmp_path)
    original = compute_fingerprint(tmp_path, site_yaml, resume_yaml)
    extra = tmp_path / "vintage" / "machines" / "new-machine" / "input.bin"
    extra.parent.mkdir()
    extra.write_bytes(b"new vintage input")

    with_extra_file = compute_fingerprint(tmp_path, site_yaml, resume_yaml)
    extra.write_bytes(b"changed vintage input")

    assert with_extra_file != original
    assert compute_fingerprint(tmp_path, site_yaml, resume_yaml) != with_extra_file


def test_ignored_vintage_files_do_not_change_fingerprint(tmp_path: Path) -> None:
    git = shutil.which("git")
    if git is None:
        pytest.skip("git is required for ignore-aware fingerprinting")
    site_yaml, resume_yaml = _write_fingerprint_tree(tmp_path)
    subprocess.run(  # noqa: S603 - executable is resolved and arguments are not passed to a shell
        [git, "init", "--quiet", str(tmp_path)],
        check=True,
    )
    (tmp_path / ".gitignore").write_text(".DS_Store\n", encoding="utf-8")
    original = compute_fingerprint(tmp_path, site_yaml, resume_yaml)

    ignored = tmp_path / "vintage" / ".DS_Store"
    ignored.write_bytes(b"local metadata")

    assert compute_fingerprint(tmp_path, site_yaml, resume_yaml) == original

    source = tmp_path / "vintage" / "new-source.txt"
    source.write_text("new vintage source\n", encoding="utf-8")

    assert compute_fingerprint(tmp_path, site_yaml, resume_yaml) != original


def test_fingerprint_reports_a_missing_guarded_file(tmp_path: Path) -> None:
    site_yaml, resume_yaml = _write_fingerprint_tree(tmp_path)
    missing = tmp_path / FINGERPRINT_FILES[0]
    missing.unlink()

    with pytest.raises(VintageReuseError, match="fingerprint input is missing"):
        compute_fingerprint(tmp_path, site_yaml, resume_yaml)


def test_validate_bundle_accepts_matching_successful_artifacts(tmp_path: Path) -> None:
    bundle_dir, site_yaml, resume_yaml = _write_bundle(tmp_path)

    validated = validate_bundle(
        bundle_dir,
        site_yaml,
        resume_yaml,
        source_sha=SOURCE_SHA,
        source_run_url=SOURCE_RUN_URL,
        project_url=PROJECT_URL,
    )

    assert validated.build_id == BUILD_ID
    assert validated.source_run_url == SOURCE_RUN_URL


@pytest.mark.parametrize("artifact", BUNDLE_FILES)
def test_validate_bundle_rejects_each_missing_artifact(tmp_path: Path, artifact: str) -> None:
    bundle_dir, site_yaml, resume_yaml = _write_bundle(tmp_path)
    (bundle_dir / artifact).unlink()

    with pytest.raises(VintageReuseError, match=rf"reusable vintage artifact {re.escape(artifact)} is missing"):
        _validate(bundle_dir, site_yaml, resume_yaml)


def test_validate_bundle_rejects_malformed_status_json(tmp_path: Path) -> None:
    bundle_dir, site_yaml, resume_yaml = _write_bundle(tmp_path)
    (bundle_dir / "pipeline-status.json").write_text("{not JSON}\n", encoding="utf-8")

    with pytest.raises(VintageReuseError, match="pipeline status is not valid UTF-8 JSON"):
        _validate(bundle_dir, site_yaml, resume_yaml)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("pipeline", "another-pipeline", "must name 'edcloud-vintage'"),
        ("result", "failure", "result must be 'success'"),
        ("exit_code", 1, "exit_code must be the integer 0"),
        ("exit_code", False, "exit_code must be the integer 0"),
        ("build_id", "", "build_id must be a nonempty string"),
    ),
)
def test_validate_bundle_rejects_failed_or_malformed_status(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    bundle_dir, site_yaml, resume_yaml = _write_bundle(tmp_path)
    status = _base_status()
    status[field] = value
    (bundle_dir / "pipeline-status.json").write_text(json.dumps(status), encoding="utf-8")

    with pytest.raises(VintageReuseError, match=re.escape(message)):
        _validate(bundle_dir, site_yaml, resume_yaml)


def test_validate_bundle_rejects_source_sha_mismatch(tmp_path: Path) -> None:
    bundle_dir, site_yaml, resume_yaml = _write_bundle(tmp_path)

    with pytest.raises(VintageReuseError, match="git_sha does not match source SHA"):
        validate_bundle(
            bundle_dir,
            site_yaml,
            resume_yaml,
            source_sha="b" * 40,
            source_run_url=SOURCE_RUN_URL,
            project_url=PROJECT_URL,
        )


@pytest.mark.parametrize(
    "source_run_url",
    (
        "http://gitlab.com/example/site/-/pipelines/123456",
        "https://gitlab.com/another/site/-/pipelines/123456",
        "https://gitlab.com/example/site/-/pipelines/not-a-number",
        "https://gitlab.com/example/site/-/pipelines/123456/",
        "https://gitlab.com/example/site/-/pipelines/123456?attempt=2",
    ),
)
def test_validate_bundle_rejects_nonexact_source_run_url(tmp_path: Path, source_run_url: str) -> None:
    bundle_dir, site_yaml, resume_yaml = _write_bundle(tmp_path)

    with pytest.raises(VintageReuseError, match="source GitLab pipeline URL must exactly match"):
        validate_bundle(
            bundle_dir,
            site_yaml,
            resume_yaml,
            source_sha=SOURCE_SHA,
            source_run_url=source_run_url,
            project_url=PROJECT_URL,
        )


def test_validate_bundle_rejects_build_log_for_another_build(tmp_path: Path) -> None:
    bundle_dir, site_yaml, resume_yaml = _write_bundle(tmp_path)
    (bundle_dir / "build.log.html").write_text(_build_log("build-another"), encoding="utf-8")

    with pytest.raises(VintageReuseError, match="build log is not tied to build_id"):
        _validate(bundle_dir, site_yaml, resume_yaml)


def test_validate_bundle_rejects_bio_mismatch(tmp_path: Path) -> None:
    bundle_dir, site_yaml, resume_yaml = _write_bundle(tmp_path)
    (bundle_dir / "brad.bio.txt").write_text(
        f"{NAME}\n{HEADLINE}\n\nA different summary.\n",
        encoding="utf-8",
    )

    with pytest.raises(VintageReuseError, match="bio does not match current public inputs"):
        _validate(bundle_dir, site_yaml, resume_yaml)


def test_cli_defaults_fingerprint_and_validate_from_repository_root(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_fingerprint_tree(tmp_path)
    _write_bundle(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert main(["fingerprint"]) == 0
    assert re.fullmatch(r"[0-9a-f]{64}\n", capsys.readouterr().out)

    assert (
        main(
            [
                "validate",
                "--source-sha",
                SOURCE_SHA,
                "--source-run-url",
                SOURCE_RUN_URL,
                "--project-url",
                PROJECT_URL,
            ]
        )
        == 0
    )
    assert f"validated {BUILD_ID} from {SOURCE_RUN_URL}" in capsys.readouterr().out


def test_validate_cli_returns_nonzero_with_clear_missing_artifact_error(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_public_inputs(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = main(
        [
            "validate",
            "--source-sha",
            SOURCE_SHA,
            "--source-run-url",
            SOURCE_RUN_URL,
            "--project-url",
            PROJECT_URL,
        ]
    )

    assert result == 1
    assert "reusable vintage artifact brad.bio.txt is missing" in capsys.readouterr().err
