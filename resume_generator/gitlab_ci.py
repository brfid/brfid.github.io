"""Shared process, environment, and generated-path helpers for GitLab jobs."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

JOB_ERRORS = (OSError, RuntimeError, ValueError, subprocess.CalledProcessError)


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
