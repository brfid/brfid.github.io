"""Create and retrieve fingerprinted vintage artifacts from GitHub Actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

from .vintage_reuse import BUNDLE_FILES, VintageReuseError, validate_source_run_url

API_ROOT = "https://api.github.com"
WORKFLOW_FILE = "publish.yml"
STANDARD_JOB_NAME = "publish-standard"
MANIFEST_NAME = "manifest.json"
MANIFEST_SCHEMA_VERSION = 1
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_ARTIFACT_ZIP_BYTES = 64 * 1024 * 1024
MAX_ARTIFACT_MEMBER_BYTES = 32 * 1024 * 1024
MAX_RUN_PAGES = 10
PER_PAGE = 100
_FINGERPRINT = re.compile(r"[0-9a-f]{64}")
_GIT_SHA = re.compile(r"[0-9a-f]{40,64}")
_REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})


class GitHubArtifactError(ValueError):
    """Raised when GitHub Actions artifact discovery or validation cannot fail closed."""


@dataclass(frozen=True)
class ArtifactSource:
    """Identify the successful standard-mode run that produced a reusable bundle."""

    run_id: int
    job_id: int
    source_sha: str
    source_run_url: str


def _require_fingerprint(value: str) -> None:
    if _FINGERPRINT.fullmatch(value) is None:
        raise GitHubArtifactError(f"fingerprint must be a lowercase SHA-256 digest: {value!r}")


def _require_source_sha(value: str) -> None:
    if _GIT_SHA.fullmatch(value) is None:
        raise GitHubArtifactError(f"source SHA must be a lowercase Git object ID: {value!r}")


def _require_ref(value: str) -> None:
    if not value or value != value.strip() or "\n" in value or "\r" in value:
        raise GitHubArtifactError(f"ref must be a nonempty single-line string: {value!r}")


def _require_regular_file(path: Path, *, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise GitHubArtifactError(f"{label} is missing or is not a regular file: {path}")
    if path.stat().st_size == 0:
        raise GitHubArtifactError(f"{label} is empty: {path}")


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


def artifact_name(fingerprint: str) -> str:
    """Return the reusable bundle's artifact name for one fingerprint."""
    _require_fingerprint(fingerprint)
    return f"reusable-vintage-{fingerprint}"


def _validate_run_identity(
    *,
    repository_url: str,
    source_sha: str,
    source_run_id: int,
    source_run_url: str,
) -> None:
    _require_source_sha(source_sha)
    if source_run_id <= 0:
        raise GitHubArtifactError("source run ID must be a positive integer")
    try:
        validate_source_run_url(source_run_url, repository_url)
    except VintageReuseError as exc:
        raise GitHubArtifactError(str(exc)) from exc
    expected_url = f"{repository_url}/actions/runs/{source_run_id}"
    if source_run_url != expected_url:
        raise GitHubArtifactError(f"source run URL does not match run ID {source_run_id}: {source_run_url!r}")


def create_bundle(  # pylint: disable=too-many-arguments
    source_dir: Path,
    output_root: Path,
    *,
    fingerprint: str,
    repository: str,
    repository_url: str,
    ref: str,
    source_sha: str,
    source_run_id: int,
    source_run_url: str,
) -> Path:
    """Copy the exact reusable files and write their immutable GitHub manifest."""
    _require_fingerprint(fingerprint)
    _require_ref(ref)
    if not repository:
        raise GitHubArtifactError("repository must be a nonempty string")
    _validate_run_identity(
        repository_url=repository_url,
        source_sha=source_sha,
        source_run_id=source_run_id,
        source_run_url=source_run_url,
    )

    target = output_root / fingerprint
    if output_root.is_symlink() or target.exists():
        raise GitHubArtifactError(f"reusable artifact destination already exists or is unsafe: {target}")

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
            "repository": repository,
            "repository_url": repository_url,
            "ref": ref,
            "source_sha": source_sha,
            "source_run_id": source_run_id,
            "source_run_url": source_run_url,
            "sha256": checksums,
        }
        _atomic_write_text(target / MANIFEST_NAME, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    except (OSError, UnicodeError, GitHubArtifactError):
        shutil.rmtree(target, ignore_errors=True)
        raise
    return target


def _require_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise GitHubArtifactError("missing required environment variable: GITHUB_TOKEN")
    return token


def _api_request_json(url: str, *, token: str) -> Any:
    if not url.startswith(f"{API_ROOT}/repos/"):
        raise GitHubArtifactError(f"refusing unexpected GitHub API URL: {url!r}")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "brfid-github-reuse/1",
    }
    request = Request(url, headers=headers)  # noqa: S310 - URL is restricted to GitHub's HTTPS API
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - request URL is validated above
            contents = cast(bytes, response.read(MAX_JSON_BYTES + 1))
    except HTTPError as exc:
        raise GitHubArtifactError(f"GitHub API returned HTTP {exc.code} for {url}") from exc
    except (TimeoutError, URLError) as exc:
        raise GitHubArtifactError(f"GitHub API request failed for {url}: {exc}") from exc
    if len(contents) > MAX_JSON_BYTES:
        raise GitHubArtifactError(f"GitHub API response exceeded {MAX_JSON_BYTES} bytes: {url}")
    try:
        return json.loads(contents)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GitHubArtifactError(f"GitHub API returned invalid JSON for {url}: {exc}") from exc


class _NoRedirect(HTTPRedirectHandler):
    """Surface a redirect's Location instead of following it and resending auth headers."""

    def redirect_request(  # pylint: disable=too-many-arguments,too-many-positional-arguments,unused-argument
        self, _req: Any, _fp: Any, _code: int, _msg: str, _headers: Any, _newurl: str
    ) -> None:
        return None


def _download_artifact_zip(repository: str, artifact_id: int, *, token: str) -> bytes:
    api_url = f"{API_ROOT}/repos/{repository}/actions/artifacts/{artifact_id}/zip"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "brfid-github-reuse/1",
    }
    opener = build_opener(_NoRedirect)
    request = Request(api_url, headers=headers)  # noqa: S310 - URL is restricted to GitHub's HTTPS API
    try:
        opener.open(request, timeout=30)  # noqa: S310 - request URL is validated above
    except HTTPError as exc:
        if exc.code not in _REDIRECT_CODES:
            raise GitHubArtifactError(f"GitHub API returned HTTP {exc.code} for {api_url}") from exc
        location = exc.headers.get("Location") if exc.headers is not None else None
        if not location:
            raise GitHubArtifactError(f"artifact download redirect had no Location header: {api_url}") from exc
    except (TimeoutError, URLError) as exc:
        raise GitHubArtifactError(f"GitHub API request failed for {api_url}: {exc}") from exc
    else:
        raise GitHubArtifactError(f"expected a redirect to a signed download URL: {api_url}")

    # The signed blob URL carries its own short-lived token; do not resend our Authorization header to it.
    blob_request = Request(location, headers={"User-Agent": "brfid-github-reuse/1"})  # noqa: S310
    try:
        with urlopen(blob_request, timeout=60) as response:  # noqa: S310 - Location comes from GitHub's own API
            contents = cast(bytes, response.read(MAX_ARTIFACT_ZIP_BYTES + 1))
    except (HTTPError, TimeoutError, URLError) as exc:
        raise GitHubArtifactError(f"could not download artifact {artifact_id}: {exc}") from exc
    if len(contents) > MAX_ARTIFACT_ZIP_BYTES:
        raise GitHubArtifactError(f"artifact {artifact_id} zip exceeded {MAX_ARTIFACT_ZIP_BYTES} bytes")
    return contents


def _extract_member(archive: zipfile.ZipFile, name: str) -> bytes:
    try:
        info = archive.getinfo(name)
    except KeyError as exc:
        raise GitHubArtifactError(f"artifact zip is missing {name}") from exc
    if info.file_size > MAX_ARTIFACT_MEMBER_BYTES:
        raise GitHubArtifactError(f"artifact member {name} exceeded {MAX_ARTIFACT_MEMBER_BYTES} bytes")
    return archive.read(info)


def _mapping(value: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GitHubArtifactError(f"{label} must be a JSON object")
    return cast(Mapping[str, Any], value)


def _list(value: Any, *, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise GitHubArtifactError(f"{label} must be a JSON array")
    return value


def _positive_int(value: Any, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise GitHubArtifactError(f"{label} must be a positive integer")
    return value


def _parse_created_at(value: Any, *, run_id: int) -> datetime:
    if not isinstance(value, str):
        raise GitHubArtifactError(f"run {run_id} created_at must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GitHubArtifactError(f"run {run_id} has invalid created_at {value!r}") from exc
    if parsed.tzinfo is None:
        raise GitHubArtifactError(f"run {run_id} created_at lacks a timezone")
    return parsed.astimezone(UTC)


def _run_pages(repository: str, *, ref: str, token: str) -> list[Mapping[str, Any]]:
    runs: list[Mapping[str, Any]] = []
    for page in range(1, MAX_RUN_PAGES + 1):
        url = (
            f"{API_ROOT}/repos/{repository}/actions/workflows/{WORKFLOW_FILE}/runs"
            f"?branch={ref}&status=success&per_page={PER_PAGE}&page={page}"
        )
        response = _mapping(_api_request_json(url, token=token), label="workflow runs response")
        values = _list(response.get("workflow_runs"), label="workflow_runs")
        runs.extend(_mapping(value, label="workflow run") for value in values)
        if len(values) < PER_PAGE:
            return runs
    raise GitHubArtifactError(f"run search exceeded {MAX_RUN_PAGES * PER_PAGE} successful workflow runs")


def _standard_job(repository: str, run_id: int, *, token: str) -> int | None:
    url = f"{API_ROOT}/repos/{repository}/actions/runs/{run_id}/jobs?per_page={PER_PAGE}"
    response = _mapping(_api_request_json(url, token=token), label=f"run {run_id} jobs response")
    values = _list(response.get("jobs"), label=f"run {run_id} jobs")
    matching: list[int] = []
    for raw_job in values:
        job = _mapping(raw_job, label=f"run {run_id} job")
        if job.get("name") != STANDARD_JOB_NAME or job.get("conclusion") != "success":
            continue
        matching.append(_positive_int(job.get("id"), label=f"run {run_id} job ID"))
    return max(matching) if matching else None


def _find_bundle_artifact(repository: str, run_id: int, *, fingerprint: str, token: str) -> int | None:
    name = artifact_name(fingerprint)
    url = f"{API_ROOT}/repos/{repository}/actions/runs/{run_id}/artifacts?per_page={PER_PAGE}"
    response = _mapping(_api_request_json(url, token=token), label=f"run {run_id} artifacts response")
    values = _list(response.get("artifacts"), label=f"run {run_id} artifacts")
    for raw_artifact in values:
        artifact = _mapping(raw_artifact, label=f"run {run_id} artifact")
        if artifact.get("name") != name or artifact.get("expired"):
            continue
        return _positive_int(artifact.get("id"), label=f"run {run_id} artifact ID")
    return None


def _validate_manifest(  # pylint: disable=too-many-arguments
    value: Any,
    *,
    fingerprint: str,
    repository: str,
    repository_url: str,
    ref: str,
    source: ArtifactSource,
) -> Mapping[str, str]:
    manifest = _mapping(value, label="reusable vintage manifest")
    expected_keys = {
        "schema_version",
        "mode",
        "fingerprint",
        "repository",
        "repository_url",
        "ref",
        "source_sha",
        "source_run_id",
        "source_run_url",
        "sha256",
    }
    if set(manifest) != expected_keys:
        raise GitHubArtifactError("reusable vintage manifest has unexpected or missing fields")
    expected_values = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "mode": "standard",
        "fingerprint": fingerprint,
        "repository": repository,
        "repository_url": repository_url,
        "ref": ref,
        "source_sha": source.source_sha,
        "source_run_id": source.run_id,
        "source_run_url": source.source_run_url,
    }
    for field, expected in expected_values.items():
        if manifest.get(field) != expected:
            raise GitHubArtifactError(f"reusable vintage manifest {field} does not match its source run")
    checksums = _mapping(manifest.get("sha256"), label="reusable vintage manifest sha256")
    if set(checksums) != set(BUNDLE_FILES):
        raise GitHubArtifactError("reusable vintage manifest must checksum exactly the three bundle files")
    for name, checksum in checksums.items():
        if not isinstance(name, str) or not isinstance(checksum, str) or _FINGERPRINT.fullmatch(checksum) is None:
            raise GitHubArtifactError(f"reusable vintage manifest has an invalid checksum for {name!r}")
    return cast(Mapping[str, str], checksums)


def _download_candidate(  # pylint: disable=too-many-arguments
    *,
    repository: str,
    run_id: int,
    fingerprint: str,
    repository_url: str,
    ref: str,
    source: ArtifactSource,
    output_dir: Path,
    token: str,
) -> None:
    artifact_id = _find_bundle_artifact(repository, run_id, fingerprint=fingerprint, token=token)
    if artifact_id is None:
        raise FileNotFoundError

    zip_bytes = _download_artifact_zip(repository, artifact_id, token=token)
    try:
        archive = zipfile.ZipFile(BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise GitHubArtifactError(f"artifact {artifact_id} is not a valid zip archive") from exc

    with archive:
        try:
            manifest_value = json.loads(_extract_member(archive, MANIFEST_NAME))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GitHubArtifactError("newest matching reusable vintage manifest is invalid JSON") from exc
        checksums = _validate_manifest(
            manifest_value,
            fingerprint=fingerprint,
            repository=repository,
            repository_url=repository_url,
            ref=ref,
            source=source,
        )

        output_dir.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".github-vintage-", dir=output_dir.parent))
        try:
            for name in BUNDLE_FILES:
                contents = _extract_member(archive, name)
                if not contents:
                    raise GitHubArtifactError(f"reusable vintage artifact is missing or empty: {name}")
                if _sha256_bytes(contents) != checksums[name]:
                    raise GitHubArtifactError(f"reusable vintage artifact checksum does not match: {name}")
                (temporary / name).write_bytes(contents)

            if output_dir.is_symlink() or (output_dir.exists() and not output_dir.is_dir()):
                raise GitHubArtifactError(f"vintage output directory is unsafe: {output_dir}")
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
    repository: str,
    repository_url: str,
    ref: str,
    max_age_days: int = 90,
    now: datetime | None = None,
) -> ArtifactSource:
    """Download the newest matching successful standard-mode artifact or fail closed."""
    _require_fingerprint(fingerprint)
    _require_ref(ref)
    if not repository:
        raise GitHubArtifactError("repository must be a nonempty string")
    if max_age_days <= 0:
        raise GitHubArtifactError("maximum artifact age must be positive")
    try:
        validate_source_run_url(f"{repository_url}/actions/runs/1", repository_url)
    except VintageReuseError as exc:
        raise GitHubArtifactError(str(exc)) from exc

    token = _require_token()
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        raise GitHubArtifactError("current time must include a timezone")
    cutoff = current_time.astimezone(UTC) - timedelta(days=max_age_days)

    for candidate in _run_pages(repository, ref=ref, token=token):
        run_id = _positive_int(candidate.get("id"), label="run ID")
        if _parse_created_at(candidate.get("created_at"), run_id=run_id) < cutoff:
            break
        run_ref = candidate.get("head_branch")
        source_sha = candidate.get("head_sha")
        source_run_url = candidate.get("html_url")
        if run_ref != ref or not isinstance(source_sha, str) or not isinstance(source_run_url, str):
            raise GitHubArtifactError(f"run {run_id} has inconsistent identity fields")
        _validate_run_identity(
            repository_url=repository_url,
            source_sha=source_sha,
            source_run_id=run_id,
            source_run_url=source_run_url,
        )
        job_id = _standard_job(repository, run_id, token=token)
        if job_id is None:
            continue
        source = ArtifactSource(
            run_id=run_id,
            job_id=job_id,
            source_sha=source_sha,
            source_run_url=source_run_url,
        )
        try:
            _download_candidate(
                repository=repository,
                run_id=run_id,
                fingerprint=fingerprint,
                repository_url=repository_url,
                ref=ref,
                source=source,
                output_dir=output_dir,
                token=token,
            )
        except FileNotFoundError:
            continue
        return source

    raise GitHubArtifactError(
        "no reusable vintage result matches the current bio inputs and a successful main standard publication"
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="create a fingerprinted reusable artifact directory")
    create.add_argument("--source-dir", type=Path, default=Path("build/vintage"))
    create.add_argument("--output-root", type=Path, default=Path("reusable-vintage"))
    create.add_argument("--fingerprint", required=True)
    create.add_argument("--repository", required=True)
    create.add_argument("--repository-url", required=True)
    create.add_argument("--ref", required=True)
    create.add_argument("--source-sha", required=True)
    create.add_argument("--source-run-id", type=int, required=True)
    create.add_argument("--source-run-url", required=True)

    download = subparsers.add_parser("download", help="download the newest matching standard artifact")
    download.add_argument("--output-dir", type=Path, default=Path("build/vintage"))
    download.add_argument("--fingerprint", required=True)
    download.add_argument("--repository", required=True)
    download.add_argument("--repository-url", required=True)
    download.add_argument("--ref", required=True)
    download.add_argument("--max-age-days", type=int, default=90)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Create or retrieve one reusable GitHub Actions vintage artifact bundle."""
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "create":
            target = create_bundle(
                args.source_dir,
                args.output_root,
                fingerprint=args.fingerprint,
                repository=args.repository,
                repository_url=args.repository_url,
                ref=args.ref,
                source_sha=args.source_sha,
                source_run_id=args.source_run_id,
                source_run_url=args.source_run_url,
            )
            print(f"GitHub vintage artifact: created {target}")
            return 0

        source = download_latest_matching(
            args.output_dir,
            fingerprint=args.fingerprint,
            repository=args.repository,
            repository_url=args.repository_url,
            ref=args.ref,
            max_age_days=args.max_age_days,
        )
    except (GitHubArtifactError, OSError) as exc:
        print(f"GitHub vintage artifact: {exc}", file=sys.stderr)
        return 1

    print(f"GitHub vintage artifact: downloaded run {source.run_id} into {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
