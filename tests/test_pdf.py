from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from pytest import MonkeyPatch

from resume_generator.pdf import _serve_directory, build_pdf


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
    out_dir = tmp_path / "site"
    out_dir.mkdir(parents=True)
    (out_dir / "resume").mkdir()
    (out_dir / "resume" / "index.html").write_text("<html>ok</html>", encoding="utf-8")

    calls: dict[str, object] = {}

    class _FakePage:
        def emulate_media(self, *, media: str) -> None:
            calls["media"] = media

        def goto(self, url: str, *, wait_until: str) -> None:
            calls["url"] = url
            calls["wait_until"] = wait_until

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

    pdf_path = build_pdf(out_dir=out_dir, resume_url_path="/resume/", pdf_name="resume.pdf")

    assert pdf_path == out_dir / "resume.pdf"
    assert pdf_path.exists()
    assert calls["media"] == "print"
    assert calls["wait_until"] == "networkidle"
    assert calls["launched"] is True
    assert calls["closed"] is True
    assert str(calls["url"]).startswith("http://127.0.0.1:")


def test_build_pdf_propagates_navigation_errors(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    out_dir = tmp_path / "site"
    out_dir.mkdir(parents=True)
    (out_dir / "resume").mkdir()
    (out_dir / "resume" / "index.html").write_text("<html>ok</html>", encoding="utf-8")

    class _FailingPage:
        def emulate_media(self, *, media: str) -> None:
            del media

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
        build_pdf(out_dir=out_dir, resume_url_path="/resume/", pdf_name="resume.pdf")

    assert not (out_dir / "resume.pdf").exists()
