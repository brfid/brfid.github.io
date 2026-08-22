from __future__ import annotations

import importlib.util
import subprocess
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

import pytest
from pytest import MonkeyPatch


def _load_verifier() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "verify_site.py"
    spec = importlib.util.spec_from_file_location("verify_site_under_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load verifier from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verifier = _load_verifier()


RUN_URL = "https://github.com/example/site/actions/runs/123456"
BUILD_ID = "build-20260822-120000"
PUBLIC_EMAIL = "public@example.com"


def _write_production_tree(tmp_path: Path) -> tuple[Path, Path]:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "resume.pdf").write_bytes(b"%PDF-1.7\n")
    (site_dir / "build.log.html").write_text("<html>build log</html>\n", encoding="utf-8")
    (site_dir / "pipeline-status.json").write_text(
        f'{{"result": "success", "exit_code": 0, "build_id": "{BUILD_ID}"}}\n',
        encoding="utf-8",
    )
    (site_dir / "index.html").write_text(
        f'<a href="/build.log.html" title="{BUILD_ID}">log</a><a href="{RUN_URL}">run</a>\n',
        encoding="utf-8",
    )
    (site_dir / "resume").mkdir()
    (site_dir / "resume" / "index.html").write_text('<a href="mailto:public@example.com">email</a>\n', encoding="utf-8")
    resume_yaml = tmp_path / "resume.yaml"
    resume_yaml.write_text(f"basics:\n  email: {PUBLIC_EMAIL}\n", encoding="utf-8")
    return site_dir, resume_yaml


def test_default_main_does_not_run_production_checks(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    site_dir = tmp_path / "site"
    monkeypatch.setattr(verifier, "verify_site", lambda _site_dir: [])

    def _unexpected_production_check(*args: object, **kwargs: object) -> list[str]:
        del args, kwargs
        raise AssertionError("default verification must not run production checks")

    monkeypatch.setattr(verifier, "verify_production_site", _unexpected_production_check)

    assert verifier.main([str(site_dir)]) == 0
    assert capsys.readouterr().out == f"Verified rendered site: {site_dir}\n"


def test_robots_check_rejects_a_conflicting_index_directive(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "index.html").write_text(
        '<meta name="robots" content="noindex, nofollow, noarchive, nosnippet, noimageindex">\n'
        '<meta name="robots" content="index, follow">\n',
        encoding="utf-8",
    )
    errors: list[str] = []

    verifier.verify_robots(site_dir, errors)

    assert errors == ["index.html: conflicting robots index/follow policy"]


def test_linked_build_log_must_exist_in_rendered_tree(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "index.html").write_text('<a href="/build.log.html">build log</a>\n', encoding="utf-8")
    errors: list[str] = []

    verifier.verify_linked_artifacts(site_dir, errors)

    assert errors == ["index.html: links to missing or empty build.log.html"]

    (site_dir / "build.log.html").write_text("<html>build log</html>\n", encoding="utf-8")
    errors = []
    verifier.verify_linked_artifacts(site_dir, errors)
    assert errors == []


def test_feed_check_allows_literal_entities_but_rejects_double_escaped_quotes(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    post = site_dir / "posts" / "example" / "index.html"
    post.parent.mkdir(parents=True)
    post.write_text("<html></html>\n", encoding="utf-8")

    def _write_feeds(description: str) -> None:
        feed = (
            "<rss><channel><item>"
            f"<description>{description}</description>"
            "<link>https://example.com/posts/example/</link>"
            "</item></channel></rss>\n"
        )
        (site_dir / "index.xml").write_text(feed, encoding="utf-8")
        (site_dir / "posts" / "index.xml").write_text(feed, encoding="utf-8")

    _write_feeds("Write &amp;amp; literally")
    errors: list[str] = []
    verifier.verify_feeds(site_dir, errors)
    assert errors == []

    _write_feeds("Broken apostrophe: &amp;#39;")
    errors = []
    verifier.verify_feeds(site_dir, errors)
    assert len(errors) == 2
    assert all("double-escaped entity" in error for error in errors)


def test_production_main_passes_explicit_inputs_to_production_checks(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    site_dir = tmp_path / "site"
    resume_yaml = tmp_path / "resume.yaml"
    calls: list[tuple[Path, Path, str]] = []
    monkeypatch.setattr(verifier, "verify_site", lambda _site_dir: [])

    def _verify_production_site(
        checked_site_dir: Path,
        *,
        resume_yaml: Path,
        build_run_url: str,
    ) -> list[str]:
        calls.append((checked_site_dir, resume_yaml, build_run_url))
        return []

    monkeypatch.setattr(verifier, "verify_production_site", _verify_production_site)

    assert (
        verifier.main(
            [
                str(site_dir),
                "--production",
                "--resume-yaml",
                str(resume_yaml),
                "--build-run-url",
                RUN_URL,
            ]
        )
        == 0
    )
    assert calls == [(site_dir, resume_yaml, RUN_URL)]


def test_production_site_accepts_complete_public_artifacts(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    site_dir, resume_yaml = _write_production_tree(tmp_path)
    outputs = {
        "pdftotext": f"Bradley Fidler\n{PUBLIC_EMAIL}\n",
        "pdfinfo": "Title: Resume\nTagged:          yes\nPages: 2\n",
    }

    def _run_external(command: str, arguments: Sequence[str], errors: list[str]) -> str:
        del errors
        assert arguments[0] == str((site_dir / "resume.pdf").resolve())
        assert arguments[1:] == (["-"] if command == "pdftotext" else [])
        return outputs[command]

    monkeypatch.setattr(verifier, "run_external", _run_external)

    assert verifier.verify_production_site(site_dir, resume_yaml=resume_yaml, build_run_url=RUN_URL) == []


def test_production_site_collects_privacy_status_and_provenance_errors(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    site_dir, resume_yaml = _write_production_tree(tmp_path)
    (site_dir / "application.PDF").write_bytes(b"private PDF")
    (site_dir / "brad.bio.txt").write_text("raw vintage output\n", encoding="utf-8")
    (site_dir / "pipeline-status.json").write_text(
        f'{{"result": "failure", "exit_code": 1, "build_id": "{BUILD_ID}"}}\n',
        encoding="utf-8",
    )
    (site_dir / "index.html").write_text(
        f'<a href="/build.log.html" title="wrong-build">log</a><a href="{RUN_URL}/wrong">run</a>\n',
        encoding="utf-8",
    )
    (site_dir / "resume" / "index.html").write_text(
        '<a href="TEL:+1 (206) 555-0100">phone</a><p>Call (206) 555-0100</p>\n',
        encoding="utf-8",
    )

    def _run_external(command: str, arguments: Sequence[str], errors: list[str]) -> str:
        del arguments, errors
        if command == "pdftotext":
            return "Bradley Fidler\n(206) 555-0100\n"
        return "Tagged:          no\n"

    monkeypatch.setattr(verifier, "run_external", _run_external)

    errors = verifier.verify_production_site(site_dir, resume_yaml=resume_yaml, build_run_url=RUN_URL)

    assert any("application.PDF" in error for error in errors)
    assert any("raw brad.bio.txt" in error for error in errors)
    assert any("resume/index.html: contains a telephone link" in error for error in errors)
    assert any("resume/index.html: contains a plausible US phone number" in error for error in errors)
    assert "resume.pdf: missing the public basics.email" in errors
    assert "resume.pdf: contains a plausible US phone number" in errors
    assert "resume.pdf: PDF is not tagged" in errors
    assert "pipeline-status.json: result is not 'success'" in errors
    assert "pipeline-status.json: exit_code is not 0" in errors
    assert any("build-log link title does not match build_id" in error for error in errors)
    assert any("missing exact build run URL" in error for error in errors)


def test_production_site_reports_missing_artifacts_without_running_pdf_tools(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "index.html").write_text("<html></html>\n", encoding="utf-8")
    resume_yaml = tmp_path / "resume.yaml"
    resume_yaml.write_text(f"basics:\n  email: {PUBLIC_EMAIL}\n", encoding="utf-8")

    def _unexpected_command(*args: object, **kwargs: object) -> str:
        del args, kwargs
        raise AssertionError("PDF tools must not run without resume.pdf")

    monkeypatch.setattr(verifier, "run_external", _unexpected_command)

    errors = verifier.verify_production_site(site_dir, resume_yaml=resume_yaml, build_run_url=RUN_URL)

    assert "missing or empty production artifact: resume.pdf" in errors
    assert "missing or empty production artifact: build.log.html" in errors
    assert "missing or empty production artifact: pipeline-status.json" in errors
    assert any("production site PDFs" in error for error in errors)


def test_run_external_uses_an_argument_list(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(verifier.shutil, "which", lambda _command: "/tools/pdftotext")

    def _run(arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(arguments)
        assert kwargs == {"check": False, "capture_output": True, "text": True}
        return subprocess.CompletedProcess(arguments, 0, stdout="PDF text\n", stderr="")

    monkeypatch.setattr(verifier.subprocess, "run", _run)
    errors: list[str] = []

    output = verifier.run_external("pdftotext", [str(tmp_path / "resume.pdf"), "-"], errors)

    assert output == "PDF text\n"
    assert calls == [["/tools/pdftotext", str(tmp_path / "resume.pdf"), "-"]]
    assert errors == []


def test_run_external_reports_a_missing_command(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(verifier.shutil, "which", lambda _command: None)
    errors: list[str] = []

    assert verifier.run_external("pdfinfo", ["resume.pdf"], errors) is None
    assert errors == ["required external command not found: pdfinfo"]
