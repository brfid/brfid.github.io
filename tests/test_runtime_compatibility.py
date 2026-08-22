"""Syntax checks for scripts executed outside the development interpreter."""

from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VAX_GUEST_PYTHON_SOURCES = (
    ROOT / "scripts" / "vax_pexpect.py",
    ROOT / "scripts" / "simh_session.py",
)


def test_vax_guest_controller_sources_parse_as_python_39() -> None:
    """The VAX image's Python 3.9 must be able to parse its mounted sources."""
    for source_path in VAX_GUEST_PYTHON_SOURCES:
        source = source_path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(source_path), feature_version=(3, 9))


def test_vintage_runner_has_valid_bash_syntax() -> None:
    """The vintage runner must pass Bash's parser before a workflow invokes it."""
    runners = sorted((ROOT / "scripts").glob("*vintage-runner.sh"))
    assert len(runners) == 1, f"expected one vintage runner, found: {runners}"

    bash = shutil.which("bash")
    assert bash is not None, "bash is required to validate the vintage runner"
    result = subprocess.run(  # noqa: S603 - bash is resolved and the repository path is fixed
        [bash, "-n", runners[0]],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
