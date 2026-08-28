"""Tests for GitLab vintage artifact creation and fail-closed retrieval."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request

import pytest
from pytest import MonkeyPatch

from resume_generator import gitlab_artifacts
from resume_generator.gitlab_artifacts import (
    ArtifactSource,
    GitLabArtifactError,
    create_bundle,
    download_latest_matching,
)
from resume_generator.vintage_reuse import BUNDLE_FILES

FINGERPRINT = "f" * 64
PROJECT_ID = 12345
PROJECT_URL = "https://gitlab.com/example/site"
REF = "main"
SOURCE_SHA = "a" * 40
PIPELINE_ID = 456
JOB_ID = 789
PIPELINE_URL = f"{PROJECT_URL}/-/pipelines/{PIPELINE_ID}"
NOW = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)
CONTENTS = {
    "brad.bio.txt": b"Test User\nPrincipal Technical Writer\n\nProfile.\n",
    "build.log.html": b"<title>build-test: vintage pipeline log</title>\n",
    "pipeline-status.json": b'{"result":"success"}\n',
}


class FakeResponse:
    """Minimal context-managed HTTP response used by urllib tests."""

    def __init__(self, contents: bytes) -> None:
        self.contents = contents

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def read(self, amount: int = -1) -> bytes:
        return self.contents if amount < 0 else self.contents[:amount]


def _write_source_bundle(path: Path) -> None:
    path.mkdir(parents=True)
    for name, contents in CONTENTS.items():
        (path / name).write_bytes(contents)


def _pipeline(pipeline_id: int = PIPELINE_ID, *, sha: str = SOURCE_SHA) -> dict[str, object]:
    return {
        "id": pipeline_id,
        "ref": REF,
        "sha": sha,
        "web_url": f"{PROJECT_URL}/-/pipelines/{pipeline_id}",
        "created_at": "2026-08-26T12:00:00Z",
    }


def _manifest(pipeline_id: int = PIPELINE_ID) -> dict[str, object]:
    return {
        "schema_version": 1,
        "mode": "standard",
        "fingerprint": FINGERPRINT,
        "project_id": PROJECT_ID,
        "project_url": PROJECT_URL,
        "ref": REF,
        "source_sha": SOURCE_SHA,
        "source_pipeline_id": pipeline_id,
        "source_pipeline_url": f"{PROJECT_URL}/-/pipelines/{pipeline_id}",
        "sha256": {name: hashlib.sha256(contents).hexdigest() for name, contents in CONTENTS.items()},
    }


def _artifact_name(url: str) -> str | None:
    marker = f"/artifacts/reusable-vintage/{FINGERPRINT}/"
    path = urlparse(url).path
    return path.split(marker, maxsplit=1)[1] if marker in path else None


def _install_api(
    monkeypatch: MonkeyPatch,
    *,
    pipelines: list[dict[str, object]] | None = None,
    manifest_by_job: dict[int, dict[str, object] | None] | None = None,
    contents: dict[str, bytes] | None = None,
    requested: list[str] | None = None,
) -> None:
    pipeline_values = pipelines if pipelines is not None else [_pipeline()]
    manifests = manifest_by_job if manifest_by_job is not None else {JOB_ID: _manifest()}
    bundle_contents = contents if contents is not None else CONTENTS

    def _urlopen(request: Request, timeout: int) -> FakeResponse:
        assert timeout == 30
        url = request.full_url
        if requested is not None:
            requested.append(url)
        path = urlparse(url).path
        if path.endswith("/pipelines"):
            return FakeResponse(json.dumps(pipeline_values).encode())
        if path.endswith("/jobs"):
            pipeline_id = int(path.split("/pipelines/", maxsplit=1)[1].split("/", maxsplit=1)[0])
            job_id = JOB_ID + (PIPELINE_ID - pipeline_id)
            return FakeResponse(json.dumps([{"id": job_id, "name": "publish-standard", "status": "success"}]).encode())

        artifact_name = _artifact_name(url)
        if artifact_name is not None:
            job_id = int(path.split("/jobs/", maxsplit=1)[1].split("/", maxsplit=1)[0])
            if artifact_name == "manifest.json":
                manifest = manifests.get(job_id)
                if manifest is None:
                    raise HTTPError(url, 404, "not found", hdrs=Message(), fp=None)
                return FakeResponse(json.dumps(manifest).encode())
            return FakeResponse(bundle_contents[artifact_name])
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr(gitlab_artifacts, "urlopen", _urlopen)


def test_create_bundle_copies_exact_files_and_writes_manifest(tmp_path: Path) -> None:
    source = tmp_path / "build" / "vintage"
    output = tmp_path / "reusable-vintage"
    _write_source_bundle(source)

    target = create_bundle(
        source,
        output,
        fingerprint=FINGERPRINT,
        project_id=PROJECT_ID,
        project_url=PROJECT_URL,
        ref=REF,
        source_sha=SOURCE_SHA,
        source_pipeline_id=PIPELINE_ID,
        source_pipeline_url=PIPELINE_URL,
    )

    assert target == output / FINGERPRINT
    assert {path.name for path in target.iterdir()} == {*BUNDLE_FILES, "manifest.json"}
    for name, contents in CONTENTS.items():
        assert (target / name).read_bytes() == contents
    assert json.loads((target / "manifest.json").read_text(encoding="utf-8")) == _manifest()


def test_create_bundle_rejects_an_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / "build" / "vintage"
    output = tmp_path / "reusable-vintage"
    _write_source_bundle(source)
    (output / FINGERPRINT).mkdir(parents=True)

    with pytest.raises(GitLabArtifactError, match="destination already exists"):
        create_bundle(
            source,
            output,
            fingerprint=FINGERPRINT,
            project_id=PROJECT_ID,
            project_url=PROJECT_URL,
            ref=REF,
            source_sha=SOURCE_SHA,
            source_pipeline_id=PIPELINE_ID,
            source_pipeline_url=PIPELINE_URL,
        )


def test_download_latest_matching_validates_manifest_and_checksums(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    requested: list[str] = []
    _install_api(monkeypatch, requested=requested)
    output = tmp_path / "build" / "vintage"

    source = download_latest_matching(
        output,
        fingerprint=FINGERPRINT,
        project_id=PROJECT_ID,
        project_url=PROJECT_URL,
        ref=REF,
        now=NOW,
    )

    assert source == ArtifactSource(PIPELINE_ID, JOB_ID, SOURCE_SHA, PIPELINE_URL)
    assert {path.name for path in output.iterdir()} == set(BUNDLE_FILES)
    for name, contents in CONTENTS.items():
        assert (output / name).read_bytes() == contents
    assert any("name=publish-standard" in url for url in requested)


def test_download_skips_newer_standard_artifact_without_matching_fingerprint(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    older_pipeline_id = PIPELINE_ID - 1
    older_job_id = JOB_ID + 1
    _install_api(
        monkeypatch,
        pipelines=[_pipeline(), _pipeline(older_pipeline_id)],
        manifest_by_job={JOB_ID: None, older_job_id: _manifest(older_pipeline_id)},
    )

    source = download_latest_matching(
        tmp_path / "vintage",
        fingerprint=FINGERPRINT,
        project_id=PROJECT_ID,
        project_url=PROJECT_URL,
        ref=REF,
        now=NOW,
    )

    assert source.pipeline_id == older_pipeline_id
    assert source.job_id == older_job_id


def test_download_fails_on_malformed_newest_matching_manifest_without_fallback(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    older_pipeline_id = PIPELINE_ID - 1
    older_job_id = JOB_ID + 1
    malformed = _manifest()
    malformed["project_id"] = 999
    requested: list[str] = []
    _install_api(
        monkeypatch,
        pipelines=[_pipeline(), _pipeline(older_pipeline_id)],
        manifest_by_job={JOB_ID: malformed, older_job_id: _manifest(older_pipeline_id)},
        requested=requested,
    )

    with pytest.raises(GitLabArtifactError, match="project_id does not match"):
        download_latest_matching(
            tmp_path / "vintage",
            fingerprint=FINGERPRINT,
            project_id=PROJECT_ID,
            project_url=PROJECT_URL,
            ref=REF,
            now=NOW,
        )

    assert not any(f"/jobs/{older_job_id}/artifacts/" in url for url in requested)


def test_download_checksum_failure_keeps_existing_output_untouched(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    corrupt = dict(CONTENTS)
    corrupt["brad.bio.txt"] = b"corrupt\n"
    _install_api(monkeypatch, contents=corrupt)
    output = tmp_path / "vintage"
    output.mkdir()
    (output / "prior.txt").write_text("prior\n", encoding="utf-8")

    with pytest.raises(GitLabArtifactError, match="checksum does not match"):
        download_latest_matching(
            output,
            fingerprint=FINGERPRINT,
            project_id=PROJECT_ID,
            project_url=PROJECT_URL,
            ref=REF,
            now=NOW,
        )

    assert (output / "prior.txt").read_text(encoding="utf-8") == "prior\n"


def test_download_fails_when_no_matching_artifact_exists(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    _install_api(monkeypatch, manifest_by_job={JOB_ID: None})

    with pytest.raises(GitLabArtifactError, match="no reusable vintage result matches"):
        download_latest_matching(
            tmp_path / "vintage",
            fingerprint=FINGERPRINT,
            project_id=PROJECT_ID,
            project_url=PROJECT_URL,
            ref=REF,
            now=NOW,
        )
