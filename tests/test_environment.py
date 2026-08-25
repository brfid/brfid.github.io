"""Contracts for local prerequisite validation and dependency setup."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# scripts/ is not a package; add it to the path so the checked module keeps the
# same import name that the repository-wide mypy invocation assigns it.
sys.path.insert(0, str(ROOT / "scripts"))

import check_environment  # noqa: E402 - scripts/ is intentionally added above


def test_playwright_pin_lives_in_the_pdf_extra() -> None:
    """PDF tooling must be optional and reproducibly pinned."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = project["project"]["dependencies"]
    pdf_dependencies = project["project"]["optional-dependencies"]["pdf"]

    assert not any(dependency.lower().startswith("playwright") for dependency in dependencies)
    assert [dependency for dependency in pdf_dependencies if dependency.lower().startswith("playwright")] == [
        "playwright==1.62.0"
    ]


def test_environment_check_reads_the_exact_pdf_extra_pin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Version validation must compare the installed package with the PDF extra."""
    project_file = tmp_path / "pyproject.toml"
    project_file.write_text(
        '[project]\nname = "example"\nversion = "0"\ndependencies = []\n'
        '[project.optional-dependencies]\npdf = ["playwright==9.8.7"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(check_environment, "PROJECT_FILE", project_file)
    monkeypatch.setattr(check_environment.metadata, "version", lambda package: "9.8.7")

    check_environment.check_playwright_version()


def test_environment_check_rejects_a_non_exact_pdf_extra_pin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A range cannot define the Chromium build used for PDF pagination."""
    project_file = tmp_path / "pyproject.toml"
    project_file.write_text(
        '[project]\nname = "example"\nversion = "0"\ndependencies = []\n'
        '[project.optional-dependencies]\npdf = ["playwright>=9"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(check_environment, "PROJECT_FILE", project_file)

    with pytest.raises(RuntimeError, match="exact Playwright pin in the pdf extra"):
        check_environment.check_playwright_version()


def test_full_checkout_and_workflows_install_the_pdf_extra() -> None:
    """Interactive PDF targets and automation must install their optional runtime."""
    expected = ".venv/bin/python -m pip install -e '.[dev,pdf]'"
    files = (
        ROOT / "README.md",
        ROOT / ".github" / "workflows" / "ci.yml",
        ROOT / ".github" / "workflows" / "deploy.yml",
    )

    for path in files:
        assert expected in path.read_text(encoding="utf-8")
