"""Check local Hugo, Python, and PDF-generation prerequisites without installing them."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tomllib
from importlib import metadata
from pathlib import Path

INSTALL_LOCATION = re.compile(r"^\s*Install location:\s+(.+?)\s*$", re.MULTILINE)
HUGO_VERSION = re.compile(r"\bhugo v(\d+)\.(\d+)\.(\d+)", re.IGNORECASE)
MINIMUM_HUGO_VERSION = (0, 156, 0)
PROJECT_FILE = Path(__file__).resolve().parents[1] / "pyproject.toml"
PLAYWRIGHT_PIN = re.compile(r"^playwright==([^;\s]+)$", re.IGNORECASE)


def check_hugo() -> None:
    """Require the supported extended Hugo executable."""
    executable = shutil.which("hugo")
    if executable is None:
        raise RuntimeError("Hugo not found")
    result = subprocess.run(  # noqa: S603 - shutil resolved the executable path
        [executable, "version"],
        check=False,
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip() or result.stderr.strip()
    match = HUGO_VERSION.search(output)
    if result.returncode or match is None:
        raise RuntimeError(f"could not read Hugo version: {output or 'no output'}")
    version = tuple(int(component) for component in match.groups())
    if version < MINIMUM_HUGO_VERSION:
        raise RuntimeError(f"Hugo 0.156.0 or newer is required; found {'.'.join(match.groups())}")
    if "+extended" not in output.lower():
        raise RuntimeError("Hugo extended is required")


def playwright_install_locations() -> list[Path]:
    """Return the browser paths expected by the installed Playwright package."""
    result = subprocess.run(  # noqa: S603 - fixed module and arguments under the selected interpreter
        [sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "Playwright is not installed"
        raise RuntimeError(detail)
    locations = [Path(match) for match in INSTALL_LOCATION.findall(result.stdout)]
    if not locations:
        raise RuntimeError("Playwright did not report its Chromium install locations")
    return locations


def check_playwright_version() -> None:
    """Require the installed Playwright package to match the project pin."""
    project = tomllib.loads(PROJECT_FILE.read_text(encoding="utf-8"))
    dependencies = project.get("project", {}).get("optional-dependencies", {}).get("pdf", [])
    expected = next(
        (match.group(1) for dependency in dependencies if (match := PLAYWRIGHT_PIN.fullmatch(dependency))),
        None,
    )
    if expected is None:
        raise RuntimeError(f"could not find an exact Playwright pin in the pdf extra in {PROJECT_FILE}")
    try:
        installed = metadata.version("playwright")
    except metadata.PackageNotFoundError as error:
        raise RuntimeError("Playwright is not installed") from error
    if installed != expected:
        raise RuntimeError(f"Playwright {expected} is required; found {installed}")


def contains_executable(path: Path) -> bool:
    """Return whether an install directory contains an executable file."""
    return path.is_dir() and any(candidate.is_file() and os.access(candidate, os.X_OK) for candidate in path.rglob("*"))


def main() -> int:
    """Validate Hugo, the selected interpreter, and its pinned browser."""
    if sys.version_info < (3, 11):  # noqa: UP036 - this script validates the selected runtime
        print("Python 3.11 or newer is required", file=sys.stderr)
        return 1
    try:
        check_hugo()
        check_playwright_version()
        locations = playwright_install_locations()
    except (OSError, RuntimeError, tomllib.TOMLDecodeError) as error:
        print(f"Environment check failed: {error}", file=sys.stderr)
        return 1

    missing = [path for path in locations if not contains_executable(path)]
    if missing:
        for path in missing:
            print(f"Playwright browser files not found: {path}", file=sys.stderr)
        print(f"Run: {sys.executable} -m playwright install chromium", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
