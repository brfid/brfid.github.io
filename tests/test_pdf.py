from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from pytest import MonkeyPatch

from resume_generator.pdf import _serve_directory, build_pdf, load_private_phone


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

        def evaluate(self, expression: str, argument: object = None) -> None:
            calls.setdefault("evaluated", [])
            evaluated = calls["evaluated"]
            assert isinstance(evaluated, list)
            evaluated.append((expression, argument))

        def pdf(self, **kwargs: object) -> None:
            calls["pdf"] = kwargs
            path = kwargs["path"]
            Path(str(path)).write_bytes(b"%PDF-1.4\n")

    class _FakeBrowser:
        def new_page(self) -> _FakePage:
            return _FakePage()

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

    monkeypatch.setitem(__import__("sys").modules, "playwright.sync_api", fake_sync_api)

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
    assert evaluated[1] == ("() => document.fonts.ready", None)
    pdf_kwargs = calls["pdf"]
    assert isinstance(pdf_kwargs, dict)
    assert pdf_kwargs["prefer_css_page_size"] is True
    assert pdf_kwargs["print_background"] is True
    assert pdf_kwargs["tagged"] is True
    assert pdf_kwargs["outline"] is True
    assert calls["launched"] is True
    assert calls["closed"] is True
    assert str(calls["url"]).startswith("http://127.0.0.1:")


def test_load_private_phone_returns_none_when_overlay_is_absent(tmp_path: Path) -> None:
    assert load_private_phone(tmp_path / "missing.yaml") is None
    assert load_private_phone(None) is None


def test_load_private_phone_rejects_invalid_overlay(tmp_path: Path) -> None:
    private_resume = tmp_path / "resume.private.yaml"
    private_resume.write_text("basics:\n  phone:\n    unexpected: mapping\n", encoding="utf-8")

    with pytest.raises(ValueError, match="basics.phone must be a non-empty string"):
        load_private_phone(private_resume)


def test_build_pdf_propagates_navigation_errors(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir(parents=True)
    (site_dir / "resume").mkdir()
    (site_dir / "resume" / "index.html").write_text("<html>ok</html>", encoding="utf-8")
    pdf_path = site_dir / "resume.pdf"

    class _FailingPage:
        def emulate_media(self, *, media: str, color_scheme: str = "light") -> None:
            del media, color_scheme

        def goto(self, url: str, *, wait_until: str) -> None:
            del url, wait_until
            raise RuntimeError("navigation failed")

    class _FakeBrowser:
        def new_page(self) -> _FailingPage:
            return _FailingPage()

        def close(self) -> None:
            return None

    class _FakeChromium:
        def launch(self) -> _FakeBrowser:
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
    monkeypatch.setitem(__import__("sys").modules, "playwright.sync_api", fake_sync_api)

    with pytest.raises(RuntimeError, match="navigation failed"):
        build_pdf(site_dir=site_dir, resume_url_path="/resume/", pdf_path=pdf_path)

    assert not pdf_path.exists()


def test_build_pdf_rejects_non_ok_response(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir(parents=True)
    pdf_path = site_dir / "resume.pdf"

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

    class _FakeBrowser:
        def new_page(self) -> _NotFoundPage:
            return _NotFoundPage()

        def close(self) -> None:
            return None

    class _FakeChromium:
        def launch(self) -> _FakeBrowser:
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
    monkeypatch.setitem(__import__("sys").modules, "playwright.sync_api", fake_sync_api)

    with pytest.raises(RuntimeError, match="did not load cleanly .404."):
        build_pdf(site_dir=site_dir, resume_url_path="/resume/", pdf_path=pdf_path)

    assert not pdf_path.exists()
