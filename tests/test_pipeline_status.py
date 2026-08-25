"""Tests for the shared pipeline-status contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from resume_generator.pipeline_status import (
    PipelineStatusError,
    PipelineStatusIssueCode,
    require_successful_pipeline_status,
    validate_pipeline_status,
)


def _write_status(path: Path, **updates: object) -> None:
    status: dict[str, object] = {
        "pipeline": "edcloud-vintage",
        "result": "success",
        "exit_code": 0,
        "build_id": "build-20260825-120000",
        "git_sha": "a" * 40,
    }
    status.update(updates)
    path.write_text(json.dumps(status) + "\n", encoding="utf-8")


def test_require_successful_status_returns_build_id(tmp_path: Path) -> None:
    path = tmp_path / "pipeline-status.json"
    _write_status(path)

    assert (
        require_successful_pipeline_status(
            path,
            expected_pipeline="edcloud-vintage",
            expected_git_sha="a" * 40,
        )
        == "build-20260825-120000"
    )


def test_validation_collects_failures_and_preserves_valid_build_id(tmp_path: Path) -> None:
    path = tmp_path / "pipeline-status.json"
    _write_status(path, result="failure", exit_code=False)

    validation = validate_pipeline_status(path)

    assert validation.build_id == "build-20260825-120000"
    assert [issue.code for issue in validation.issues] == [
        PipelineStatusIssueCode.RESULT,
        PipelineStatusIssueCode.EXIT_CODE,
    ]
    with pytest.raises(PipelineStatusError, match="result must be 'success'.*integer 0"):
        require_successful_pipeline_status(path)


def test_validation_checks_requested_pipeline_identity(tmp_path: Path) -> None:
    path = tmp_path / "pipeline-status.json"
    _write_status(path, pipeline="other", git_sha="b" * 40)

    validation = validate_pipeline_status(
        path,
        expected_pipeline="edcloud-vintage",
        expected_git_sha="a" * 40,
    )

    assert [issue.code for issue in validation.issues] == [
        PipelineStatusIssueCode.PIPELINE,
        PipelineStatusIssueCode.GIT_SHA,
    ]


@pytest.mark.parametrize(
    ("contents", "code"),
    (("{not JSON}\n", PipelineStatusIssueCode.READ), ("[]\n", PipelineStatusIssueCode.OBJECT)),
)
def test_validation_rejects_malformed_top_level_value(
    tmp_path: Path,
    contents: str,
    code: PipelineStatusIssueCode,
) -> None:
    path = tmp_path / "pipeline-status.json"
    path.write_text(contents, encoding="utf-8")

    validation = validate_pipeline_status(path)

    assert validation.build_id is None
    assert [issue.code for issue in validation.issues] == [code]
