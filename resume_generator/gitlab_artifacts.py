"""Create and retrieve fingerprinted vintage artifacts from GitLab CI."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .vintage_reuse import BUNDLE_FILES, VintageReuseError, validate_source_run_url

API_ROOT = "https://gitlab.com/api/v4"
STANDARD_PIPELINE_NAME = "publish-standard"
STANDARD_JOB_NAME = "publish-standard"
MANIFEST_NAME = "manifest.json"
MANIFEST_SCHEMA_VERSION = 1
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_ARTIFACT_BYTES = 32 * 1024 * 1024
MAX_PIPELINE_PAGES = 10
PER_PAGE = 100
_FINGERPRINT = re.compile(r"[0-9a-f]{64}")
_GIT_SHA = re.compile(r"[0-9a-f]{40,64}")


class GitLabArtifactError(ValueError):
    """Raised when GitLab artifact discovery or validation cannot fail closed."""


@dataclass(frozen=True)
class ArtifactSource:
    """Identify the successful standard pipeline that produced a reusable bundle."""

    pipeline_id: int
    job_id: int
    source_sha: str
    source_pipeline_url: str


def _require_fingerprint(value: str) -> None:
    if _FINGERPRINT.fullmatch(value) is None:
        raise GitLabArtifactError(f"fingerprint must be a lowercase SHA-256 digest: {value!r}")


def _require_source_sha(value: str) -> None:
    if _GIT_SHA.fullmatch(value) is None:
        raise GitLabArtifactError(f"source SHA must be a lowercase Git object ID: {value!r}")


def _require_ref(value: str) -> None:
    if not value or value != value.strip() or "\n" in value or "\r" in value:
        raise GitLabArtifactError(f"ref must be a nonempty single-line string: {value!r}")


def _require_regular_file(path: Path, *, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise GitLabArtifactError(f"{label} is missing or is not a regular file: {path}")
    if path.stat().st_size == 0:
        raise GitLabArtifactError(f"{label} is empty: {path}")


def _sha256_bytes(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _validate_pipeline_identity(
    *,
    project_url: str,
    source_sha: str,
    source_pipeline_id: int,
    source_pipeline_url: str,
) -> None:
    _require_source_sha(source_sha)
    if source_pipeline_id <= 0:
        raise GitLabArtifactError("source pipeline ID must be a positive integer")
    try:
        validate_source_run_url(source_pipeline_url, project_url)
    except VintageReuseError as exc:
        raise GitLabArtifactError(str(exc)) from exc
    expected_url = f"{project_url}/-/pipelines/{source_pipeline_id}"
    if source_pipeline_url != expected_url:
        raise GitLabArtifactError(
            f"source pipeline URL does not match pipeline ID {source_pipeline_id}: {source_pipeline_url!r}"
        )


def create_bundle(  # pylint: disable=too-many-arguments
    source_dir: Path,
    output_root: Path,
    *,
    fingerprint: str,
    project_id: int,
    project_url: str,
    ref: str,
    source_sha: str,
    source_pipeline_id: int,
    source_pipeline_url: str,
) -> Path:
    """Copy the exact reusable files and write their immutable GitLab manifest."""
    _require_fingerprint(fingerprint)
    _require_ref(ref)
    if project_id <= 0:
        raise GitLabArtifactError("project ID must be a positive integer")
    _validate_pipeline_identity(
        project_url=project_url,
        source_sha=source_sha,
        source_pipeline_id=source_pipeline_id,
        source_pipeline_url=source_pipeline_url,
    )

    target = output_root / fingerprint
    if output_root.is_symlink() or target.exists():
        raise GitLabArtifactError(f"reusable artifact destination already exists or is unsafe: {target}")

    target.mkdir(parents=True)
    try:
        checksums: dict[str, str] = {}
        for name in BUNDLE_FILES:
            source = source_dir / name
            _require_regular_file(source, label=f"vintage bundle file {name}")
            destination = target / name
            shutil.copyfile(source, destination)
            checksums[name] = _sha256_file(destination)

        manifest = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "mode": "standard",
            "fingerprint": fingerprint,
            "project_id": project_id,
            "project_url": project_url,
            "ref": ref,
            "source_sha": source_sha,
            "source_pipeline_id": source_pipeline_id,
            "source_pipeline_url": source_pipeline_url,
            "sha256": checksums,
        }
        _atomic_write_text(target / MANIFEST_NAME, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    except (OSError, UnicodeError, GitLabArtifactError):
        shutil.rmtree(target, ignore_errors=True)
        raise
    return target


def _request_bytes(
    url: str,
    *,
    allow_not_found: bool,
    size_limit: int,
) -> bytes | None:
    if not url.startswith(f"{API_ROOT}/projects/"):
        raise GitLabArtifactError(f"refusing unexpected GitLab API URL: {url!r}")
    headers = {"Accept": "application/json", "User-Agent": "brfid-gitlab-reuse/1"}
    request = Request(  # noqa: S310 - URL is restricted to GitLab's HTTPS API
        url,
        headers=headers,
    )
    try:
        with urlopen(  # noqa: S310 - request contains the exact validated HTTPS URL
            request, timeout=30
        ) as response:
            contents = cast(bytes, response.read(size_limit + 1))
    except HTTPError as exc:
        if exc.code == 404 and allow_not_found:
            return None
        raise GitLabArtifactError(f"GitLab API returned HTTP {exc.code} for {url}") from exc
    except (TimeoutError, URLError) as exc:
        raise GitLabArtifactError(f"GitLab API request failed for {url}: {exc}") from exc
    if len(contents) > size_limit:
        raise GitLabArtifactError(f"GitLab API response exceeded {size_limit} bytes: {url}")
    return contents


def _request_json(url: str) -> Any:
    contents = _request_bytes(
        url,
        allow_not_found=False,
        size_limit=MAX_JSON_BYTES,
    )
    if contents is None:
        raise GitLabArtifactError(f"GitLab API unexpectedly returned no response: {url}")
    try:
        return json.loads(contents)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GitLabArtifactError(f"GitLab API returned invalid JSON for {url}: {exc}") from exc


def _mapping(value: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GitLabArtifactError(f"{label} must be a JSON object")
    return cast(Mapping[str, Any], value)


def _list(value: Any, *, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise GitLabArtifactError(f"{label} must be a JSON array")
    return value


def _positive_int(value: Any, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise GitLabArtifactError(f"{label} must be a positive integer")
    return value


def _parse_created_at(value: Any, *, pipeline_id: int) -> datetime:
    if not isinstance(value, str):
        raise GitLabArtifactError(f"pipeline {pipeline_id} created_at must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GitLabArtifactError(f"pipeline {pipeline_id} has invalid created_at {value!r}") from exc
    if parsed.tzinfo is None:
        raise GitLabArtifactError(f"pipeline {pipeline_id} created_at lacks a timezone")
    return parsed.astimezone(UTC)


def _pipeline_pages(project_id: int, *, ref: str) -> list[Mapping[str, Any]]:
    pipelines: list[Mapping[str, Any]] = []
    for page in range(1, MAX_PIPELINE_PAGES + 1):
        query = urlencode(
            {
                "ref": ref,
                "status": "success",
                "name": STANDARD_PIPELINE_NAME,
                "order_by": "id",
                "sort": "desc",
                "per_page": PER_PAGE,
                "page": page,
            }
        )
        url = f"{API_ROOT}/projects/{project_id}/pipelines?{query}"
        values = _list(_request_json(url), label="pipelines response")
        pipelines.extend(_mapping(value, label="pipeline") for value in values)
        if len(values) < PER_PAGE:
            return pipelines
    raise GitLabArtifactError(f"pipeline search exceeded {MAX_PIPELINE_PAGES * PER_PAGE} successful standard pipelines")


def _standard_job(project_id: int, pipeline_id: int) -> int | None:
    query = urlencode(
        [
            ("scope[]", "success"),
            ("include_retried", "false"),
            ("per_page", str(PER_PAGE)),
        ]
    )
    url = f"{API_ROOT}/projects/{project_id}/pipelines/{pipeline_id}/jobs?{query}"
    values = _list(_request_json(url), label=f"pipeline {pipeline_id} jobs response")
    matching: list[int] = []
    for raw_job in values:
        job = _mapping(raw_job, label=f"pipeline {pipeline_id} job")
        if job.get("name") != STANDARD_JOB_NAME or job.get("status") != "success":
            continue
        matching.append(_positive_int(job.get("id"), label=f"pipeline {pipeline_id} job ID"))
    return max(matching) if matching else None


def _artifact_url(project_id: int, job_id: int, relative_path: str) -> str:
    encoded_path = quote(relative_path, safe="/")
    return f"{API_ROOT}/projects/{project_id}/jobs/{job_id}/artifacts/{encoded_path}"


def _validate_manifest(  # pylint: disable=too-many-arguments
    value: Any,
    *,
    fingerprint: str,
    project_id: int,
    project_url: str,
    ref: str,
    source: ArtifactSource,
) -> Mapping[str, str]:
    manifest = _mapping(value, label="reusable vintage manifest")
    expected_keys = {
        "schema_version",
        "mode",
        "fingerprint",
        "project_id",
        "project_url",
        "ref",
        "source_sha",
        "source_pipeline_id",
        "source_pipeline_url",
        "sha256",
    }
    if set(manifest) != expected_keys:
        raise GitLabArtifactError("reusable vintage manifest has unexpected or missing fields")
    expected_values = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "mode": "standard",
        "fingerprint": fingerprint,
        "project_id": project_id,
        "project_url": project_url,
        "ref": ref,
        "source_sha": source.source_sha,
        "source_pipeline_id": source.pipeline_id,
        "source_pipeline_url": source.source_pipeline_url,
    }
    for field, expected in expected_values.items():
        if manifest.get(field) != expected:
            raise GitLabArtifactError(f"reusable vintage manifest {field} does not match its source pipeline")
    checksums = _mapping(manifest.get("sha256"), label="reusable vintage manifest sha256")
    if set(checksums) != set(BUNDLE_FILES):
        raise GitLabArtifactError("reusable vintage manifest must checksum exactly the three bundle files")
    for name, checksum in checksums.items():
        if not isinstance(name, str) or not isinstance(checksum, str) or _FINGERPRINT.fullmatch(checksum) is None:
            raise GitLabArtifactError(f"reusable vintage manifest has an invalid checksum for {name!r}")
    return cast(Mapping[str, str], checksums)


def _download_candidate(  # pylint: disable=too-many-arguments
    *,
    project_id: int,
    job_id: int,
    fingerprint: str,
    project_url: str,
    ref: str,
    source: ArtifactSource,
    output_dir: Path,
) -> None:
    prefix = f"reusable-vintage/{fingerprint}"
    manifest_url = _artifact_url(project_id, job_id, f"{prefix}/{MANIFEST_NAME}")
    manifest_contents = _request_bytes(
        manifest_url,
        allow_not_found=True,
        size_limit=MAX_JSON_BYTES,
    )
    if manifest_contents is None:
        raise FileNotFoundError
    try:
        manifest_value = json.loads(manifest_contents)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GitLabArtifactError("newest matching reusable vintage manifest is invalid JSON") from exc
    checksums = _validate_manifest(
        manifest_value,
        fingerprint=fingerprint,
        project_id=project_id,
        project_url=project_url,
        ref=ref,
        source=source,
    )

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".gitlab-vintage-", dir=output_dir.parent))
    try:
        for name in BUNDLE_FILES:
            contents = _request_bytes(
                _artifact_url(project_id, job_id, f"{prefix}/{name}"),
                allow_not_found=False,
                size_limit=MAX_ARTIFACT_BYTES,
            )
            if not contents:
                raise GitLabArtifactError(f"reusable vintage artifact is missing or empty: {name}")
            if _sha256_bytes(contents) != checksums[name]:
                raise GitLabArtifactError(f"reusable vintage artifact checksum does not match: {name}")
            (temporary / name).write_bytes(contents)

        if output_dir.is_symlink() or (output_dir.exists() and not output_dir.is_dir()):
            raise GitLabArtifactError(f"vintage output directory is unsafe: {output_dir}")
        if output_dir.exists():
            shutil.rmtree(output_dir)
        temporary.replace(output_dir)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)


def download_latest_matching(  # pylint: disable=too-many-arguments,too-many-locals
    output_dir: Path,
    *,
    fingerprint: str,
    project_id: int,
    project_url: str,
    ref: str,
    max_age_days: int = 90,
    now: datetime | None = None,
) -> ArtifactSource:
    """Download the newest matching successful standard artifact or fail closed."""
    _require_fingerprint(fingerprint)
    _require_ref(ref)
    if project_id <= 0:
        raise GitLabArtifactError("project ID must be a positive integer")
    if max_age_days <= 0:
        raise GitLabArtifactError("maximum artifact age must be positive")
    try:
        validate_source_run_url(f"{project_url}/-/pipelines/1", project_url)
    except VintageReuseError as exc:
        raise GitLabArtifactError(str(exc)) from exc

    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        raise GitLabArtifactError("current time must include a timezone")
    cutoff = current_time.astimezone(UTC) - timedelta(days=max_age_days)

    for pipeline in _pipeline_pages(project_id, ref=ref):
        pipeline_id = _positive_int(pipeline.get("id"), label="pipeline ID")
        if _parse_created_at(pipeline.get("created_at"), pipeline_id=pipeline_id) < cutoff:
            break
        pipeline_ref = pipeline.get("ref")
        source_sha = pipeline.get("sha")
        source_pipeline_url = pipeline.get("web_url")
        if pipeline_ref != ref or not isinstance(source_sha, str) or not isinstance(source_pipeline_url, str):
            raise GitLabArtifactError(f"pipeline {pipeline_id} has inconsistent identity fields")
        _validate_pipeline_identity(
            project_url=project_url,
            source_sha=source_sha,
            source_pipeline_id=pipeline_id,
            source_pipeline_url=source_pipeline_url,
        )
        job_id = _standard_job(project_id, pipeline_id)
        if job_id is None:
            continue
        source = ArtifactSource(
            pipeline_id=pipeline_id,
            job_id=job_id,
            source_sha=source_sha,
            source_pipeline_url=source_pipeline_url,
        )
        try:
            _download_candidate(
                project_id=project_id,
                job_id=job_id,
                fingerprint=fingerprint,
                project_url=project_url,
                ref=ref,
                source=source,
                output_dir=output_dir,
            )
        except FileNotFoundError:
            continue
        return source

    raise GitLabArtifactError(
        "no reusable vintage result matches the current bio inputs and a successful main standard publication"
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="create a fingerprinted reusable artifact directory")
    create.add_argument("--source-dir", type=Path, default=Path("build/vintage"))
    create.add_argument("--output-root", type=Path, default=Path("reusable-vintage"))
    create.add_argument("--fingerprint", required=True)
    create.add_argument("--project-id", type=int, required=True)
    create.add_argument("--project-url", required=True)
    create.add_argument("--ref", required=True)
    create.add_argument("--source-sha", required=True)
    create.add_argument("--source-pipeline-id", type=int, required=True)
    create.add_argument("--source-pipeline-url", required=True)

    download = subparsers.add_parser("download", help="download the newest matching standard artifact")
    download.add_argument("--output-dir", type=Path, default=Path("build/vintage"))
    download.add_argument("--fingerprint", required=True)
    download.add_argument("--project-id", type=int, required=True)
    download.add_argument("--project-url", required=True)
    download.add_argument("--ref", required=True)
    download.add_argument("--max-age-days", type=int, default=90)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Create or retrieve one reusable GitLab vintage artifact bundle."""
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "create":
            target = create_bundle(
                args.source_dir,
                args.output_root,
                fingerprint=args.fingerprint,
                project_id=args.project_id,
                project_url=args.project_url,
                ref=args.ref,
                source_sha=args.source_sha,
                source_pipeline_id=args.source_pipeline_id,
                source_pipeline_url=args.source_pipeline_url,
            )
            print(f"GitLab vintage artifact: created {target}")
            return 0

        source = download_latest_matching(
            args.output_dir,
            fingerprint=args.fingerprint,
            project_id=args.project_id,
            project_url=args.project_url,
            ref=args.ref,
            max_age_days=args.max_age_days,
        )
    except (GitLabArtifactError, OSError) as exc:
        print(f"GitLab vintage artifact: {exc}", file=sys.stderr)
        return 1

    print(f"GitLab vintage artifact: downloaded pipeline {source.pipeline_id} into {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
