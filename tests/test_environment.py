"""Contracts for local prerequisite validation and dependency setup."""

from pathlib import Path

import pytest

from site_tools import environment as check_environment


def test_installed_playwright_matches_the_project_pin() -> None:
    check_environment.check_playwright_version()


@pytest.mark.parametrize(
    ("dependency", "installed", "error"),
    (
        ("playwright==9.8.7", "9.8.7", None),
        ("playwright==9.8.7", "9.8.6", "Playwright 9.8.7 is required; found 9.8.6"),
        ("playwright>=9", "9.8.7", "exact Playwright pin in project dependencies"),
    ),
)
def test_environment_validates_the_declared_playwright_dependency(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, dependency: str, installed: str, error: str | None
) -> None:
    project_file = tmp_path / "pyproject.toml"
    project_file.write_text(f'[project]\ndependencies = ["{dependency}"]\n', encoding="utf-8")
    monkeypatch.setattr(check_environment, "PROJECT_FILE", project_file)
    monkeypatch.setattr(check_environment.metadata, "version", lambda _package: installed)

    if error is None:
        check_environment.check_playwright_version()
    else:
        with pytest.raises(RuntimeError, match=error):
            check_environment.check_playwright_version()
