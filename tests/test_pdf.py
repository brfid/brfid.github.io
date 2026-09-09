from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from playwright.sync_api import Browser, Page
from pytest import MonkeyPatch

from site_tools.pdf import _serve_directory, build_pdf, load_private_phone


@pytest.fixture
def renderer(monkeypatch: MonkeyPatch) -> tuple[MagicMock, MagicMock]:
    page = MagicMock(spec=Page)
    page.goto.return_value.ok = True
    page.evaluate.return_value = []

    def write_pdf(**options: object) -> None:
        Path(str(options["path"])).write_bytes(b"%PDF-1.4\n")

    page.pdf.side_effect = write_pdf
    browser = MagicMock(spec=Browser)
    browser.new_page.return_value = page
    runtime = MagicMock()
    runtime.chromium.launch.return_value = browser
    monkeypatch.setattr("playwright.sync_api.sync_playwright", lambda: nullcontext(runtime))
    monkeypatch.setattr("site_tools.pdf._serve_directory", lambda _root: nullcontext(43123))
    return page, browser


def test_serve_directory_serves_files(tmp_path: Path) -> None:
    import urllib.request

    (tmp_path / "index.html").write_text("hello", encoding="utf-8")
    with (
        _serve_directory(tmp_path) as port,
        urllib.request.urlopen(f"http://127.0.0.1:{port}/index.html", timeout=2) as response,
    ):
        assert response.read().decode("utf-8") == "hello"


@pytest.mark.parametrize("private", (False, True))
def test_build_pdf_writes_target_with_required_print_options(
    tmp_path: Path, renderer: tuple[MagicMock, MagicMock], private: bool
) -> None:
    page, browser = renderer
    site_dir = tmp_path / "site"
    pdf_path = tmp_path / "local" / "application.pdf" if private else site_dir / "resume.pdf"
    overlay = tmp_path / "resume.private.yaml"
    overlay.write_text('basics:\n  phone: "+1-555-0100"\n', encoding="utf-8")

    assert (
        build_pdf(
            site_dir=site_dir,
            resume_url_path="/resume/",
            pdf_path=pdf_path,
            private_resume_path=overlay if private else None,
        )
        == pdf_path
    )

    assert pdf_path.is_file()
    page.emulate_media.assert_called_once_with(media="print", color_scheme="light")
    page.goto.assert_called_once_with("http://127.0.0.1:43123/resume/", wait_until="load")
    page.pdf.assert_called_once_with(
        path=str(pdf_path), print_background=True, tagged=True, outline=True, prefer_css_page_size=True
    )
    browser.close.assert_called_once_with()
    evaluations = page.evaluate.call_args_list
    assert len(evaluations) == (2 if private else 1)
    if private:
        assert "private phone injection target" in evaluations[0].args[0]
        assert evaluations[0].args[1] == "+1-555-0100"
    font_expression = evaluations[-1].args[0]
    for required in (
        "document.fonts.load",
        "faces.length > 0",
        "await document.fonts.ready",
        "document.fonts.check",
        '"Newsreader"',
        '"IBM Plex Mono"',
    ):
        assert required in font_expression


def test_load_private_phone_returns_none_when_overlay_is_not_requested() -> None:
    assert load_private_phone(None) is None


def test_load_private_phone_rejects_missing_overlay(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="private resume overlay does not exist"):
        load_private_phone(tmp_path / "missing.yaml")


def test_load_private_phone_rejects_non_file_overlay(tmp_path: Path) -> None:
    private_resume = tmp_path / "resume.private.yaml"
    private_resume.mkdir()

    with pytest.raises(ValueError, match="private resume overlay must be a regular file"):
        load_private_phone(private_resume)


def test_load_private_phone_rejects_invalid_overlay(tmp_path: Path) -> None:
    private_resume = tmp_path / "resume.private.yaml"
    private_resume.write_text("basics:\n  phone:\n    unexpected: mapping\n", encoding="utf-8")

    with pytest.raises(ValueError, match="basics.phone must be a non-empty string"):
        load_private_phone(private_resume)


def test_build_pdf_rejects_resolved_private_output_inside_site_before_creating_directories(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    pdf_path = other_dir / ".." / "site" / "private" / "bradley-fidler-resume.pdf"
    private_resume = tmp_path / "resume.private.yaml"
    private_resume.write_text('basics:\n  phone: "+1-555-0100"\n', encoding="utf-8")

    with pytest.raises(ValueError, match="private resume PDF must be written outside"):
        build_pdf(
            site_dir=site_dir,
            resume_url_path="/resume/",
            pdf_path=pdf_path,
            private_resume_path=private_resume,
        )

    assert not site_dir.exists()
    assert not pdf_path.resolve().parent.exists()


def test_build_pdf_rejects_missing_private_overlay_before_creating_directories(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    pdf_path = tmp_path / "local" / "bradley-fidler-resume.pdf"

    with pytest.raises(FileNotFoundError, match="private resume overlay does not exist"):
        build_pdf(
            site_dir=site_dir,
            resume_url_path="/resume/",
            pdf_path=pdf_path,
            private_resume_path=tmp_path / "missing.yaml",
        )

    assert not site_dir.exists()
    assert not pdf_path.parent.exists()


@pytest.mark.parametrize(
    ("failure", "message"),
    (
        ("navigation", "navigation failed"),
        ("missing-response", "did not load cleanly .no response."),
        ("not-found", "did not load cleanly .404."),
        ("fonts", "required resume fonts did not load: Newsreader, IBM Plex Mono"),
        ("pdf", "pdf creation failed"),
    ),
)
def test_build_pdf_closes_browser_and_propagates_rendering_failures(
    tmp_path: Path, renderer: tuple[MagicMock, MagicMock], failure: str, message: str
) -> None:
    page, browser = renderer
    if failure == "navigation":
        page.goto.side_effect = RuntimeError("navigation failed")
    elif failure == "missing-response":
        page.goto.return_value = None
    elif failure == "not-found":
        page.goto.return_value.ok = False
        page.goto.return_value.status = 404
    elif failure == "fonts":
        page.evaluate.return_value = ["Newsreader", "IBM Plex Mono"]
    else:
        page.pdf.side_effect = RuntimeError("pdf creation failed")
    site_dir = tmp_path / "site"
    pdf_path = site_dir / "resume.pdf"

    with pytest.raises(RuntimeError, match=message):
        build_pdf(site_dir=site_dir, resume_url_path="/resume/", pdf_path=pdf_path)

    assert not pdf_path.exists()
    browser.close.assert_called_once_with()
    if failure != "pdf":
        page.pdf.assert_not_called()
