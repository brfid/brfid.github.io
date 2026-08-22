from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from pytest import MonkeyPatch

import resume_generator.pdf as pdf_module
from resume_generator.pdf import _serve_directory, build_pdf, load_private_phone


@contextmanager
def _fake_serve_directory(_root: Path) -> Iterator[int]:
    yield 43123


def _install_fake_playwright(
    monkeypatch: MonkeyPatch,
    *,
    page: Any,
    calls: dict[str, object],
) -> None:
    """Install one-page Playwright and local-server fakes for build_pdf tests."""

    class _FakeBrowser:
        def new_page(self) -> Any:
            return page

        def close(self) -> None:
            calls["closed"] = True

    class _FakeChromium:
        def launch(self) -> _FakeBrowser:
            calls["launched"] = True
            return _FakeBrowser()

    class _FakePlaywright:
        chromium = _FakeChromium()

    class _FakeSyncPlaywright:
        def __enter__(self) -> _FakePlaywright:
            return _FakePlaywright()

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: Any,
        ) -> None:
            return None

    fake_sync_api = ModuleType("playwright.sync_api")

    def _sync_playwright() -> _FakeSyncPlaywright:
        return _FakeSyncPlaywright()

    fake_sync_api.sync_playwright = _sync_playwright  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_sync_api)
    monkeypatch.setattr(pdf_module, "_serve_directory", _fake_serve_directory)


def test_serve_directory_serves_files(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("hello", encoding="utf-8")

    with _serve_directory(tmp_path) as port:
        import urllib.request

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/index.html", timeout=2) as resp:
            body = resp.read().decode("utf-8")

    assert body == "hello"


def test_build_pdf_uses_playwright_and_writes_target_path(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir(parents=True)
    (site_dir / "resume").mkdir()
    (site_dir / "resume" / "index.html").write_text("<html>ok</html>", encoding="utf-8")
    application_pdf = tmp_path / "local" / "bradley-fidler-resume.pdf"
    private_resume = tmp_path / "resume.private.yaml"
    private_resume.write_text('basics:\n  phone: "+1-555-0100"\n', encoding="utf-8")

    calls: dict[str, object] = {}

    class _FakeResponse:
        ok = True
        status = 200

    class _FakePage:
        def emulate_media(self, *, media: str, color_scheme: str = "light") -> None:
            calls["media"] = media
            calls["color_scheme"] = color_scheme

        def goto(self, url: str, *, wait_until: str) -> _FakeResponse:
            calls["url"] = url
            calls["wait_until"] = wait_until
            return _FakeResponse()

        def evaluate(self, expression: str, argument: object = None) -> object:
            calls.setdefault("evaluated", [])
            evaluated = calls["evaluated"]
            assert isinstance(evaluated, list)
            evaluated.append((expression, argument))
            return [] if "document.fonts.check" in expression else None

        def pdf(self, **kwargs: object) -> None:
            calls["pdf"] = kwargs
            path = kwargs["path"]
            Path(str(path)).write_bytes(b"%PDF-1.4\n")

    _install_fake_playwright(monkeypatch, page=_FakePage(), calls=calls)

    pdf_path = build_pdf(
        site_dir=site_dir,
        resume_url_path="/resume/",
        pdf_path=application_pdf,
        private_resume_path=private_resume,
    )

    assert pdf_path == application_pdf
    assert pdf_path.exists()
    assert calls["media"] == "print"
    assert calls["wait_until"] == "load"
    evaluated = calls["evaluated"]
    assert isinstance(evaluated, list)
    assert "private phone injection target" in evaluated[0][0]
    assert evaluated[0][1] == "+1-555-0100"
    assert "document.fonts.load" in evaluated[1][0]
    assert "faces.length > 0" in evaluated[1][0]
    assert "await document.fonts.ready" in evaluated[1][0]
    assert "document.fonts.check" in evaluated[1][0]
    assert '"Newsreader"' in evaluated[1][0]
    assert '"IBM Plex Mono"' in evaluated[1][0]
    assert evaluated[1][1] is None
    pdf_kwargs = calls["pdf"]
    assert isinstance(pdf_kwargs, dict)
    assert pdf_kwargs["prefer_css_page_size"] is True
    assert pdf_kwargs["print_background"] is True
    assert pdf_kwargs["tagged"] is True
    assert pdf_kwargs["outline"] is True
    assert calls["launched"] is True
    assert calls["closed"] is True
    assert str(calls["url"]).startswith("http://127.0.0.1:")


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


def test_build_pdf_propagates_navigation_errors(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir(parents=True)
    (site_dir / "resume").mkdir()
    (site_dir / "resume" / "index.html").write_text("<html>ok</html>", encoding="utf-8")
    pdf_path = site_dir / "resume.pdf"
    calls: dict[str, object] = {}

    class _FailingPage:
        def emulate_media(self, *, media: str, color_scheme: str = "light") -> None:
            del media, color_scheme

        def goto(self, url: str, *, wait_until: str) -> None:
            del url, wait_until
            raise RuntimeError("navigation failed")

    _install_fake_playwright(monkeypatch, page=_FailingPage(), calls=calls)

    with pytest.raises(RuntimeError, match="navigation failed"):
        build_pdf(site_dir=site_dir, resume_url_path="/resume/", pdf_path=pdf_path)

    assert not pdf_path.exists()
    assert calls["closed"] is True


def test_build_pdf_rejects_missing_required_fonts_and_closes_browser(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    site_dir = tmp_path / "site"
    pdf_path = site_dir / "resume.pdf"
    calls: dict[str, object] = {}

    class _OkResponse:
        ok = True
        status = 200

    class _MissingFontsPage:
        def emulate_media(self, *, media: str, color_scheme: str = "light") -> None:
            del media, color_scheme

        def goto(self, url: str, *, wait_until: str) -> _OkResponse:
            del url, wait_until
            return _OkResponse()

        def evaluate(self, expression: str, argument: object = None) -> list[str]:
            del argument
            calls["font_expression"] = expression
            return ["Newsreader", "IBM Plex Mono"]

        def pdf(self, **kwargs: object) -> None:  # pragma: no cover - must not run
            del kwargs
            raise AssertionError("pdf() should not run before fonts are loaded")

    _install_fake_playwright(monkeypatch, page=_MissingFontsPage(), calls=calls)

    with pytest.raises(RuntimeError, match="required resume fonts did not load: Newsreader, IBM Plex Mono"):
        build_pdf(site_dir=site_dir, resume_url_path="/resume/", pdf_path=pdf_path)

    assert "document.fonts.load" in str(calls["font_expression"])
    assert "faces.length > 0" in str(calls["font_expression"])
    assert "await document.fonts.ready" in str(calls["font_expression"])
    assert "document.fonts.check" in str(calls["font_expression"])
    assert '"Newsreader"' in str(calls["font_expression"])
    assert '"IBM Plex Mono"' in str(calls["font_expression"])
    assert calls["closed"] is True
    assert not pdf_path.exists()


def test_build_pdf_closes_browser_when_pdf_creation_fails(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    site_dir = tmp_path / "site"
    pdf_path = site_dir / "resume.pdf"
    calls: dict[str, object] = {}

    class _OkResponse:
        ok = True
        status = 200

    class _FailingPdfPage:
        def emulate_media(self, *, media: str, color_scheme: str = "light") -> None:
            del media, color_scheme

        def goto(self, url: str, *, wait_until: str) -> _OkResponse:
            del url, wait_until
            return _OkResponse()

        def evaluate(self, expression: str, argument: object = None) -> list[str]:
            del expression, argument
            return []

        def pdf(self, **kwargs: object) -> None:
            del kwargs
            raise RuntimeError("pdf creation failed")

    _install_fake_playwright(monkeypatch, page=_FailingPdfPage(), calls=calls)

    with pytest.raises(RuntimeError, match="pdf creation failed"):
        build_pdf(site_dir=site_dir, resume_url_path="/resume/", pdf_path=pdf_path)

    assert calls["closed"] is True
    assert not pdf_path.exists()


def test_build_pdf_rejects_non_ok_response(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir(parents=True)
    pdf_path = site_dir / "resume.pdf"
    calls: dict[str, object] = {}

    class _NotFoundResponse:
        ok = False
        status = 404

    class _NotFoundPage:
        def emulate_media(self, *, media: str, color_scheme: str = "light") -> None:
            del media, color_scheme

        def goto(self, url: str, *, wait_until: str) -> _NotFoundResponse:
            del url, wait_until
            return _NotFoundResponse()

        def pdf(self, **kwargs: object) -> None:  # pragma: no cover - must not run
            raise AssertionError("pdf() should not be reached on a non-OK response")

    _install_fake_playwright(monkeypatch, page=_NotFoundPage(), calls=calls)

    with pytest.raises(RuntimeError, match="did not load cleanly .404."):
        build_pdf(site_dir=site_dir, resume_url_path="/resume/", pdf_path=pdf_path)

    assert not pdf_path.exists()
    assert calls["closed"] is True
