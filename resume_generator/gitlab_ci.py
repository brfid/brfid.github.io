"""Shared process, environment, identity, and generated-path helpers for GitLab jobs."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

JOB_ERRORS = (OSError, RuntimeError, ValueError, subprocess.CalledProcessError)
EXPECTED_PROJECT_ID = 85834009
EXPECTED_PROJECT_PATH = "brfid/brfid.gitlab.io"
EXPECTED_PROJECT_URL = "https://gitlab.com/brfid/brfid.gitlab.io"
EXPECTED_SERVER_HOST = "gitlab.com"
PUBLICATION_BRANCH = "main"
_GIT_SHA = re.compile(r"[0-9a-f]{40}")


def required_environment(names: Sequence[str]) -> dict[str, str]:
    """Return required nonempty environment values or raise with the missing name."""
    values: dict[str, str] = {}
    for name in names:
        value = os.environ.get(name, "")
        if not value:
            raise ValueError(f"missing required GitLab CI variable: {name}")
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
class GitLabJobIdentity:
    """Validated immutable identity for a job in this GitLab project."""

    branch: str
    commit_sha: str
    job_name: str
    pipeline_id: int
    pipeline_source: str
    pipeline_url: str
    project_id: int
    project_path: str
    project_url: str
    ref_protected: bool
    server_host: str

    @classmethod
    def from_environment(
        cls,
        root: Path,
        *,
        expected_branch: str | None = None,
        expected_jobs: Sequence[str] = (),
        expected_sources: Sequence[str] = ("push", "web", "api"),
        require_protected: bool = False,
    ) -> GitLabJobIdentity:
        """Load CI identity and reject project, ref, source, job, or checkout overrides."""
        names = (
            "CI_COMMIT_BRANCH",
            "CI_COMMIT_REF_PROTECTED",
            "CI_COMMIT_SHA",
            "CI_JOB_NAME",
            "CI_PIPELINE_ID",
            "CI_PIPELINE_SOURCE",
            "CI_PIPELINE_URL",
            "CI_PROJECT_ID",
            "CI_PROJECT_PATH",
            "CI_PROJECT_URL",
            "CI_SERVER_HOST",
        )
        values = required_environment(names)

        try:
            project_id = int(values["CI_PROJECT_ID"])
        except ValueError as exc:
            raise ValueError("CI_PROJECT_ID must be an integer") from exc
        if project_id != EXPECTED_PROJECT_ID:
            raise ValueError(f"CI_PROJECT_ID must be {EXPECTED_PROJECT_ID}")

        expected_project = {
            "CI_PROJECT_PATH": EXPECTED_PROJECT_PATH,
            "CI_PROJECT_URL": EXPECTED_PROJECT_URL,
            "CI_SERVER_HOST": EXPECTED_SERVER_HOST,
        }
        for name, expected in expected_project.items():
            if values[name] != expected:
                raise ValueError(f"{name} must be {expected!r}, got {values[name]!r}")

        branch = values["CI_COMMIT_BRANCH"]
        if branch != branch.strip() or any(character in branch for character in "\r\n"):
            raise ValueError("CI_COMMIT_BRANCH must be a nonempty single-line ref")
        if expected_branch is not None and branch != expected_branch:
            raise ValueError(f"CI_COMMIT_BRANCH must be {expected_branch!r}, got {branch!r}")

        commit_sha = values["CI_COMMIT_SHA"]
        if _GIT_SHA.fullmatch(commit_sha) is None:
            raise ValueError("CI_COMMIT_SHA must be a lowercase 40-character Git object ID")
        if commit_sha != checked_out_commit(root):
            raise ValueError("CI_COMMIT_SHA does not match checked-out HEAD")

        try:
            pipeline_id = int(values["CI_PIPELINE_ID"])
        except ValueError as exc:
            raise ValueError("CI_PIPELINE_ID must be an integer") from exc
        if pipeline_id <= 0:
            raise ValueError("CI_PIPELINE_ID must be positive")
        expected_pipeline_url = f"{EXPECTED_PROJECT_URL}/-/pipelines/{pipeline_id}"
        if values["CI_PIPELINE_URL"] != expected_pipeline_url:
            raise ValueError(f"CI_PIPELINE_URL must be {expected_pipeline_url!r}, got {values['CI_PIPELINE_URL']!r}")

        pipeline_source = values["CI_PIPELINE_SOURCE"]
        if pipeline_source not in expected_sources:
            raise ValueError(f"CI_PIPELINE_SOURCE is not allowed for this job: {pipeline_source!r}")
        job_name = values["CI_JOB_NAME"]
        if expected_jobs and job_name not in expected_jobs:
            raise ValueError(f"CI_JOB_NAME is not allowed for this operation: {job_name!r}")

        protected_value = values["CI_COMMIT_REF_PROTECTED"]
        if protected_value not in {"true", "false"}:
            raise ValueError("CI_COMMIT_REF_PROTECTED must be 'true' or 'false'")
        ref_protected = protected_value == "true"
        if require_protected and not ref_protected:
            raise ValueError("publication requires a protected GitLab ref")

        return cls(
            branch=branch,
            commit_sha=commit_sha,
            job_name=job_name,
            pipeline_id=pipeline_id,
            pipeline_source=pipeline_source,
            pipeline_url=values["CI_PIPELINE_URL"],
            project_id=project_id,
            project_path=values["CI_PROJECT_PATH"],
            project_url=values["CI_PROJECT_URL"],
            ref_protected=ref_protected,
            server_host=values["CI_SERVER_HOST"],
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
