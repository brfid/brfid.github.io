"""Tests for GitHub Actions vintage artifact creation and fail-closed retrieval."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import UTC, datetime
from email.message import Message
from io import BytesIO
from pathlib import Path
from typing import cast
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request

import pytest
from pytest import MonkeyPatch

from resume_generator import github_artifacts
from resume_generator.github_artifacts import (
    ArtifactSource,
    GitHubArtifactError,
    artifact_name,
    create_bundle,
    download_latest_matching,
)
from resume_generator.vintage_reuse import BUNDLE_FILES

FINGERPRINT = "f" * 64
REPOSITORY = "example/site"
REPOSITORY_URL = "https://github.com/example/site"
REF = "main"
SOURCE_SHA = "a" * 40
RUN_ID = 456
JOB_ID = 789
ARTIFACT_ID = 999
SOURCE_RUN_URL = f"{REPOSITORY_URL}/actions/runs/{RUN_ID}"
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


def _run(run_id: int = RUN_ID, *, sha: str = SOURCE_SHA) -> dict[str, object]:
    return {
        "id": run_id,
        "head_branch": REF,
        "head_sha": sha,
        "html_url": f"{REPOSITORY_URL}/actions/runs/{run_id}",
        "created_at": "2026-08-26T12:00:00Z",
    }


def _manifest(run_id: int = RUN_ID) -> dict[str, object]:
    return {
        "schema_version": 1,
        "mode": "standard",
        "fingerprint": FINGERPRINT,
        "repository": REPOSITORY,
        "repository_url": REPOSITORY_URL,
        "ref": REF,
        "source_sha": SOURCE_SHA,
        "source_run_id": run_id,
        "source_run_url": f"{REPOSITORY_URL}/actions/runs/{run_id}",
        "sha256": {name: hashlib.sha256(contents).hexdigest() for name, contents in CONTENTS.items()},
    }


def _zip_bytes(manifest: dict[str, object], contents: dict[str, bytes]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        for name, data in contents.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def _install_api(  # pylint: disable=too-many-arguments,too-many-locals
    monkeypatch: MonkeyPatch,
    *,
    runs: list[dict[str, object]] | None = None,
    jobs_by_run: dict[int, list[dict[str, object]]] | None = None,
    artifact_by_run: dict[int, dict[str, object] | None] | None = None,
    manifest_by_run: dict[int, dict[str, object]] | None = None,
    contents: dict[str, bytes] | None = None,
    requested: list[str] | None = None,
) -> None:
    run_values = runs if runs is not None else [_run()]
    default_jobs = {RUN_ID: [{"id": JOB_ID, "name": "publish-standard", "conclusion": "success"}]}
    jobs = jobs_by_run if jobs_by_run is not None else default_jobs
    artifacts = (
        artifact_by_run
        if artifact_by_run is not None
        else {RUN_ID: {"id": ARTIFACT_ID, "name": artifact_name(FINGERPRINT), "expired": False}}
    )
    manifests = manifest_by_run if manifest_by_run is not None else {RUN_ID: _manifest()}
    bundle_contents = contents if contents is not None else CONTENTS

    zips: dict[int, bytes] = {}
    for run_id, artifact in artifacts.items():
        manifest = manifests.get(run_id)
        if artifact is not None and manifest is not None:
            zips[cast(int, artifact["id"])] = _zip_bytes(manifest, bundle_contents)

    def _urlopen(request: Request, timeout: int) -> FakeResponse:
        url = request.full_url
        if requested is not None:
            requested.append(url)
        if url.startswith("https://blob.example/"):
            assert timeout == 60
            artifact_id = int(url.rsplit("/", maxsplit=1)[-1])
            return FakeResponse(zips[artifact_id])
        assert timeout == 30
        path = urlparse(url).path
        if path.endswith("/runs"):
            return FakeResponse(json.dumps({"workflow_runs": run_values}).encode())
        if path.endswith("/jobs"):
            run_id = int(path.split("/runs/", maxsplit=1)[1].split("/", maxsplit=1)[0])
            return FakeResponse(json.dumps({"jobs": jobs.get(run_id, [])}).encode())
        if path.endswith("/artifacts"):
            run_id = int(path.split("/runs/", maxsplit=1)[1].split("/", maxsplit=1)[0])
            artifact = artifacts.get(run_id)
            values = [artifact] if artifact is not None else []
            return FakeResponse(json.dumps({"artifacts": values}).encode())
        raise AssertionError(f"unexpected URL: {url}")

    class _FakeOpener:
        def open(self, request: Request, timeout: int) -> FakeResponse:
            assert timeout == 30
            url = request.full_url
            if requested is not None:
                requested.append(url)
            artifact_id = int(url.rsplit("/", maxsplit=2)[-2])
            headers = Message()
            headers["Location"] = f"https://blob.example/{artifact_id}"
            raise HTTPError(url, 302, "Found", hdrs=headers, fp=None)

    monkeypatch.setattr(github_artifacts, "urlopen", _urlopen)
    monkeypatch.setattr(github_artifacts, "build_opener", lambda *_handlers: _FakeOpener())
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")


def test_create_bundle_copies_exact_files_and_writes_manifest(tmp_path: Path) -> None:
    source = tmp_path / "build" / "vintage"
    output = tmp_path / "reusable-vintage"
    _write_source_bundle(source)

    target = create_bundle(
        source,
        output,
        fingerprint=FINGERPRINT,
        repository=REPOSITORY,
        repository_url=REPOSITORY_URL,
        ref=REF,
        source_sha=SOURCE_SHA,
        source_run_id=RUN_ID,
        source_run_url=SOURCE_RUN_URL,
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

    with pytest.raises(GitHubArtifactError, match="destination already exists"):
        create_bundle(
            source,
            output,
            fingerprint=FINGERPRINT,
            repository=REPOSITORY,
            repository_url=REPOSITORY_URL,
            ref=REF,
            source_sha=SOURCE_SHA,
            source_run_id=RUN_ID,
            source_run_url=SOURCE_RUN_URL,
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
        repository=REPOSITORY,
        repository_url=REPOSITORY_URL,
        ref=REF,
        now=NOW,
    )

    assert source == ArtifactSource(RUN_ID, JOB_ID, SOURCE_SHA, SOURCE_RUN_URL)
    assert {path.name for path in output.iterdir()} == set(BUNDLE_FILES)
    for name, contents in CONTENTS.items():
        assert (output / name).read_bytes() == contents
    assert any("/workflows/publish.yml/runs" in url for url in requested)


def test_download_skips_newer_standard_artifact_without_matching_fingerprint(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    older_run_id = RUN_ID - 1
    older_job_id = JOB_ID + 1
    older_artifact_id = ARTIFACT_ID + 1
    _install_api(
        monkeypatch,
        runs=[_run(), _run(older_run_id)],
        jobs_by_run={
            RUN_ID: [{"id": JOB_ID, "name": "publish-standard", "conclusion": "success"}],
            older_run_id: [{"id": older_job_id, "name": "publish-standard", "conclusion": "success"}],
        },
        artifact_by_run={
            RUN_ID: None,
            older_run_id: {"id": older_artifact_id, "name": artifact_name(FINGERPRINT), "expired": False},
        },
        manifest_by_run={older_run_id: _manifest(older_run_id)},
    )

    source = download_latest_matching(
        tmp_path / "vintage",
        fingerprint=FINGERPRINT,
        repository=REPOSITORY,
        repository_url=REPOSITORY_URL,
        ref=REF,
        now=NOW,
    )

    assert source.run_id == older_run_id
    assert source.job_id == older_job_id


def test_download_fails_on_malformed_newest_matching_manifest_without_fallback(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    older_run_id = RUN_ID - 1
    older_job_id = JOB_ID + 1
    older_artifact_id = ARTIFACT_ID + 1
    malformed = _manifest()
    malformed["repository"] = "someone/else"
    requested: list[str] = []
    _install_api(
        monkeypatch,
        runs=[_run(), _run(older_run_id)],
        jobs_by_run={
            RUN_ID: [{"id": JOB_ID, "name": "publish-standard", "conclusion": "success"}],
            older_run_id: [{"id": older_job_id, "name": "publish-standard", "conclusion": "success"}],
        },
        artifact_by_run={
            RUN_ID: {"id": ARTIFACT_ID, "name": artifact_name(FINGERPRINT), "expired": False},
            older_run_id: {"id": older_artifact_id, "name": artifact_name(FINGERPRINT), "expired": False},
        },
        manifest_by_run={RUN_ID: malformed, older_run_id: _manifest(older_run_id)},
        requested=requested,
    )

    with pytest.raises(GitHubArtifactError, match="repository does not match"):
        download_latest_matching(
            tmp_path / "vintage",
            fingerprint=FINGERPRINT,
            repository=REPOSITORY,
            repository_url=REPOSITORY_URL,
            ref=REF,
            now=NOW,
        )

    assert not any(f"/runs/{older_run_id}/" in url for url in requested)


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

    with pytest.raises(GitHubArtifactError, match="checksum does not match"):
        download_latest_matching(
            output,
            fingerprint=FINGERPRINT,
            repository=REPOSITORY,
            repository_url=REPOSITORY_URL,
            ref=REF,
            now=NOW,
        )

    assert (output / "prior.txt").read_text(encoding="utf-8") == "prior\n"


def test_download_fails_when_no_matching_artifact_exists(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    _install_api(monkeypatch, artifact_by_run={RUN_ID: None}, manifest_by_run={})

    with pytest.raises(GitHubArtifactError, match="no reusable vintage result matches"):
        download_latest_matching(
            tmp_path / "vintage",
            fingerprint=FINGERPRINT,
            repository=REPOSITORY,
            repository_url=REPOSITORY_URL,
            ref=REF,
            now=NOW,
        )
