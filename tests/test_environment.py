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


def test_full_checkout_and_github_jobs_install_the_pdf_extra() -> None:
    """Interactive and hosted PDF environments must consume locks with the exact runtime."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    setup = (ROOT / "scripts" / "github" / "setup.sh").read_text(encoding="utf-8")
    pipeline = (ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
    dev_lock = (ROOT / "requirements" / "dev.lock").read_text(encoding="utf-8")
    publish_lock = (ROOT / "requirements" / "publish.lock").read_text(encoding="utf-8")

    assert "--require-hashes -r requirements/dev.lock" in readme
    assert '"$lock_file"' in setup
    assert "install_python_environment requirements/dev.lock" in setup
    assert "install_python_environment requirements/publish.lock" in setup
    assert "playwright==1.62.0" in dev_lock
    assert "playwright==1.62.0" in publish_lock
    assert "bash scripts/github/setup.sh checks" in pipeline
    assert "bash scripts/github/setup.sh publish" in pipeline
