"""Read and validate structured vintage pipeline status files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, cast


class PipelineStatusIssueCode(Enum):
    """Stable categories for pipeline-status validation failures."""

    READ = "read"
    OBJECT = "object"
    PIPELINE = "pipeline"
    RESULT = "result"
    EXIT_CODE = "exit_code"
    BUILD_ID = "build_id"
    GIT_SHA = "git_sha"


@dataclass(frozen=True)
class PipelineStatusIssue:
    """One pipeline-status validation failure."""

    code: PipelineStatusIssueCode
    message: str
    detail: str = ""


@dataclass(frozen=True)
class PipelineStatusValidation:
    """Validated build identity plus every status failure found."""

    build_id: str | None
    issues: tuple[PipelineStatusIssue, ...]


class PipelineStatusError(ValueError):
    """Raised when a caller requires a successful pipeline status."""

    def __init__(self, issues: tuple[PipelineStatusIssue, ...]) -> None:
        """Combine structured validation issues into one failure."""
        self.issues = issues
        super().__init__("; ".join(issue.message for issue in issues))


def validate_pipeline_status(
    path: Path,
    *,
    expected_pipeline: str | None = None,
    expected_git_sha: str | None = None,
) -> PipelineStatusValidation:
    """Return a build ID and all violations of the successful-status contract."""
    try:
        value: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        issue = PipelineStatusIssue(
            PipelineStatusIssueCode.READ,
            f"is not valid UTF-8 JSON: {path}: {exc}",
            str(exc),
        )
        return PipelineStatusValidation(build_id=None, issues=(issue,))

    if not isinstance(value, dict):
        issue = PipelineStatusIssue(
            PipelineStatusIssueCode.OBJECT,
            f"must be a JSON object: {path}",
        )
        return PipelineStatusValidation(build_id=None, issues=(issue,))
    status = cast(dict[str, object], value)

    issues: list[PipelineStatusIssue] = []
    if expected_pipeline is not None and status.get("pipeline") != expected_pipeline:
        issues.append(
            PipelineStatusIssue(
                PipelineStatusIssueCode.PIPELINE,
                f"must name {expected_pipeline!r}",
            )
        )
    if status.get("result") != "success":
        issues.append(
            PipelineStatusIssue(
                PipelineStatusIssueCode.RESULT,
                "result must be 'success'",
            )
        )
    exit_code = status.get("exit_code")
    if not isinstance(exit_code, int) or isinstance(exit_code, bool) or exit_code != 0:
        issues.append(
            PipelineStatusIssue(
                PipelineStatusIssueCode.EXIT_CODE,
                "exit_code must be the integer 0",
            )
        )
    raw_build_id = status.get("build_id")
    build_id = raw_build_id if isinstance(raw_build_id, str) and raw_build_id.strip() else None
    if build_id is None:
        issues.append(
            PipelineStatusIssue(
                PipelineStatusIssueCode.BUILD_ID,
                "build_id must be a nonempty string",
            )
        )
    if expected_git_sha is not None and status.get("git_sha") != expected_git_sha:
        issues.append(
            PipelineStatusIssue(
                PipelineStatusIssueCode.GIT_SHA,
                f"git_sha does not match source SHA: {status.get('git_sha')!r} != {expected_git_sha!r}",
            )
        )
    return PipelineStatusValidation(build_id=build_id, issues=tuple(issues))


def require_successful_pipeline_status(
    path: Path,
    *,
    expected_pipeline: str | None = None,
    expected_git_sha: str | None = None,
) -> str:
    """Return the build ID or raise for any unsuccessful or malformed status."""
    validation = validate_pipeline_status(
        path,
        expected_pipeline=expected_pipeline,
        expected_git_sha=expected_git_sha,
    )
    if validation.issues:
        raise PipelineStatusError(validation.issues)
    if validation.build_id is None:  # pragma: no cover - enforced by validate_pipeline_status
        raise RuntimeError("pipeline status validation returned no build ID")
    return validation.build_id
