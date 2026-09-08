"""Publication gates, immutable dependencies, and stale-build protection."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
# BaseLoader preserves GitHub's `on` key and exposes all YAML scalars as strings.
WORKFLOW: dict[str, Any] = yaml.load(
    (ROOT / ".github/workflows/publish.yml").read_text(),
    Loader=yaml.BaseLoader,  # noqa: S506 - BaseLoader constructs only strings and containers.
)


def test_build_and_deployment_have_separate_permissions_and_gates() -> None:
    jobs = WORKFLOW["jobs"]
    checks = jobs["checks"]
    deploy = jobs["deploy"]
    assert WORKFLOW["permissions"] == {"contents": "read"}
    assert checks["needs"] == "secret-scan"
    assert "permissions" not in checks
    assert deploy["needs"] == "checks"
    assert deploy["permissions"] == {"contents": "read", "pages": "write", "id-token": "write"}
    assert deploy["environment"]["name"] == "github-pages"
    assert all("timeout-minutes" in job for job in jobs.values())
    assert "refs/heads/main" in deploy["if"]
    assert "github.ref_protected" in deploy["if"]
    assert "github.event_name == 'push'" in deploy["if"]
    assert "inputs.operation == 'publish'" in deploy["if"]
    assert "[nopublish]" in deploy["if"]
    assert "pull_request_target" not in WORKFLOW["on"]


def test_the_verified_artifact_is_uploaded_without_rebuilding_in_deployment() -> None:
    steps = WORKFLOW["jobs"]["checks"]["steps"]
    commands = [step["run"] for step in steps if "run" in step]
    assert commands == ["bash scripts/github/setup.sh", "make check", "make verify-site"]
    upload = steps[-1]
    assert upload["uses"].startswith("actions/upload-pages-artifact@")
    assert upload["with"]["path"] == "site"
    assert "if" not in upload and "continue-on-error" not in upload
    deploy_actions = [step.get("uses", "") for step in WORKFLOW["jobs"]["deploy"]["steps"]]
    assert not any(action.startswith("actions/checkout@") for action in deploy_actions)
    assert any(action.startswith("actions/deploy-pages@") for action in deploy_actions)


def test_action_references_and_build_runtimes_are_explicit() -> None:
    for job in WORKFLOW["jobs"].values():
        assert job["runs-on"] == "ubuntu-24.04"
        for step in job["steps"]:
            if "uses" in step:
                assert re.fullmatch(r"[\w-]+/[\w-]+@[0-9a-f]{40}", step["uses"])
            if step.get("uses", "").startswith("actions/checkout@"):
                assert step["with"]["persist-credentials"] == "false"
    python_step = next(
        step for step in WORKFLOW["jobs"]["checks"]["steps"] if step.get("uses", "").startswith("actions/setup-python@")
    )
    assert re.fullmatch(r"3\.11\.\d+", python_step["with"]["python-version"])


@pytest.mark.parametrize(
    ("remote_sha", "api_status", "expected"), [("a" * 40, 0, "true"), ("b" * 40, 0, "false"), ("", 1, None)]
)
def test_stale_build_guard_checks_remote_main_and_fails_closed(
    tmp_path: Path, remote_sha: str, api_status: int, expected: str | None
) -> None:
    gh = tmp_path / "gh"
    gh.write_text('#!/bin/sh\nprintf "%s\\n" "$TEST_REMOTE_SHA"\nexit "$TEST_API_STATUS"\n')
    gh.chmod(0o755)
    output = tmp_path / "output"
    env = dict(
        os.environ,
        PATH=f"{tmp_path}:{os.environ['PATH']}",
        CHECKED_SHA="a" * 40,
        GITHUB_OUTPUT=str(output),
        GITHUB_REPOSITORY="example/site",
        TEST_REMOTE_SHA=remote_sha,
        TEST_API_STATUS=str(api_status),
    )
    script = next(step["run"] for step in WORKFLOW["jobs"]["deploy"]["steps"] if step.get("id") == "current")
    bash = shutil.which("bash")
    assert bash is not None
    result = subprocess.run(  # noqa: S603 - execute the tracked guard with a local API stub.
        [bash, "-c", script], env=env, capture_output=True, text=True, check=False
    )
    if expected is None:
        assert result.returncode != 0
        assert not output.exists()
    else:
        assert result.returncode == 0, result.stderr
        assert output.read_text().strip() == f"publish={expected}"


def test_setup_script_parses_as_bash() -> None:
    bash = shutil.which("bash")
    assert bash is not None
    result = subprocess.run(  # noqa: S603 - syntax-check the tracked script with resolved Bash.
        [bash, "-n", str(ROOT / "scripts/github/setup.sh")], capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr
