"""Shared process, environment, identity, and generated-path helpers for GitHub Actions jobs."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

JOB_ERRORS = (OSError, RuntimeError, ValueError, subprocess.CalledProcessError)
EXPECTED_REPOSITORY_ID = 743333428
EXPECTED_REPOSITORY = "brfid/brfid.github.io"
EXPECTED_REPOSITORY_URL = "https://github.com/brfid/brfid.github.io"
EXPECTED_SERVER_URL = "https://github.com"
PUBLICATION_BRANCH = "main"
_GIT_SHA = re.compile(r"[0-9a-f]{40}")


def required_environment(names: Sequence[str]) -> dict[str, str]:
    """Return required nonempty environment values or raise with the missing name."""
    values: dict[str, str] = {}
    for name in names:
        value = os.environ.get(name, "")
        if not value:
            raise ValueError(f"missing required GitHub Actions variable: {name}")
        values[name] = value
    return values


def executable(name: str) -> str:
    """Return an executable's absolute path or raise a clear environment error."""
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"required executable not found: {name}")
    return path


def checked_out_commit(root: Path) -> str:
    """Return the exact commit checked out at HEAD without invoking a shell."""
    result = subprocess.run(  # noqa: S603 - Git is resolved before running a fixed argument list
        [executable("git"), "rev-parse", "--verify", "HEAD^{commit}"],
        check=True,
        cwd=root,
        shell=False,
        stdout=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


@dataclass(frozen=True)
class GitHubJobIdentity:
    """Validated immutable identity for a job in this GitHub repository."""

    branch: str
    commit_sha: str
    job_name: str
    run_id: int
    event_name: str
    run_url: str
    repository: str
    repository_id: int
    repository_url: str
    ref_protected: bool
    server_url: str

    @classmethod
    def from_environment(
        cls,
        root: Path,
        *,
        expected_branch: str | None = None,
        expected_jobs: Sequence[str] = (),
        expected_events: Sequence[str] = ("push", "workflow_dispatch", "pull_request"),
        require_protected: bool = False,
    ) -> GitHubJobIdentity:
        """Load CI identity and reject repository, ref, event, job, or checkout overrides.

        ``GITHUB_REF_PROTECTED`` is not one of GitHub Actions' automatic environment
        variables; it must be wired explicitly per job from the ``github.ref_protected``
        workflow context (``env: GITHUB_REF_PROTECTED: ${{ github.ref_protected }}``).
        """
        names = (
            "GITHUB_REF_NAME",
            "GITHUB_REF_TYPE",
            "GITHUB_REF_PROTECTED",
            "GITHUB_SHA",
            "GITHUB_JOB",
            "GITHUB_RUN_ID",
            "GITHUB_EVENT_NAME",
            "GITHUB_REPOSITORY",
            "GITHUB_REPOSITORY_ID",
            "GITHUB_SERVER_URL",
        )
        values = required_environment(names)

        if values["GITHUB_SERVER_URL"] != EXPECTED_SERVER_URL:
            raise ValueError(f"GITHUB_SERVER_URL must be {EXPECTED_SERVER_URL!r}, got {values['GITHUB_SERVER_URL']!r}")
        if values["GITHUB_REPOSITORY"] != EXPECTED_REPOSITORY:
            raise ValueError(f"GITHUB_REPOSITORY must be {EXPECTED_REPOSITORY!r}, got {values['GITHUB_REPOSITORY']!r}")
        try:
            repository_id = int(values["GITHUB_REPOSITORY_ID"])
        except ValueError as exc:
            raise ValueError("GITHUB_REPOSITORY_ID must be an integer") from exc
        if repository_id != EXPECTED_REPOSITORY_ID:
            raise ValueError(f"GITHUB_REPOSITORY_ID must be {EXPECTED_REPOSITORY_ID}")

        if values["GITHUB_REF_TYPE"] != "branch":
            raise ValueError(f"GITHUB_REF_TYPE must be 'branch', got {values['GITHUB_REF_TYPE']!r}")
        branch = values["GITHUB_REF_NAME"]
        if branch != branch.strip() or any(character in branch for character in "\r\n"):
            raise ValueError("GITHUB_REF_NAME must be a nonempty single-line ref")
        if expected_branch is not None and branch != expected_branch:
            raise ValueError(f"GITHUB_REF_NAME must be {expected_branch!r}, got {branch!r}")

        commit_sha = values["GITHUB_SHA"]
        if _GIT_SHA.fullmatch(commit_sha) is None:
            raise ValueError("GITHUB_SHA must be a lowercase 40-character Git object ID")
        if commit_sha != checked_out_commit(root):
            raise ValueError("GITHUB_SHA does not match checked-out HEAD")

        try:
            run_id = int(values["GITHUB_RUN_ID"])
        except ValueError as exc:
            raise ValueError("GITHUB_RUN_ID must be an integer") from exc
        if run_id <= 0:
            raise ValueError("GITHUB_RUN_ID must be positive")
        run_url = f"{EXPECTED_REPOSITORY_URL}/actions/runs/{run_id}"

        event_name = values["GITHUB_EVENT_NAME"]
        if event_name not in expected_events:
            raise ValueError(f"GITHUB_EVENT_NAME is not allowed for this job: {event_name!r}")
        job_name = values["GITHUB_JOB"]
        if expected_jobs and job_name not in expected_jobs:
            raise ValueError(f"GITHUB_JOB is not allowed for this operation: {job_name!r}")

        protected_value = values["GITHUB_REF_PROTECTED"]
        if protected_value not in {"true", "false"}:
            raise ValueError("GITHUB_REF_PROTECTED must be 'true' or 'false'")
        ref_protected = protected_value == "true"
        if require_protected and not ref_protected:
            raise ValueError("publication requires a protected GitHub ref")

        return cls(
            branch=branch,
            commit_sha=commit_sha,
            job_name=job_name,
            run_id=run_id,
            event_name=event_name,
            run_url=run_url,
            repository=values["GITHUB_REPOSITORY"],
            repository_id=repository_id,
            repository_url=EXPECTED_REPOSITORY_URL,
            ref_protected=ref_protected,
            server_url=values["GITHUB_SERVER_URL"],
        )


def reset_directory(path: Path, *, create: bool) -> None:
    """Remove a generated directory without following a symbolic link."""
    if path.is_symlink():
        raise RuntimeError(f"refusing generated output through a symbolic link: {path}")
    if path.exists():
        if not path.is_dir():
            raise RuntimeError(f"generated output path is not a directory: {path}")
        shutil.rmtree(path)
    if create:
        path.mkdir(parents=True)


def run(  # pylint: disable=too-many-arguments
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
    input_text: str | None = None,
    check: bool = True,
    quiet: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run one fixed argument list without invoking a shell."""
    return subprocess.run(  # noqa: S603 - callers resolve executables and pass argument lists
        list(command),
        check=check,
        cwd=cwd,
        env=env,
        input=input_text,
        text=True,
        stdout=subprocess.DEVNULL if quiet else None,
        stderr=subprocess.DEVNULL if quiet else None,
    )
