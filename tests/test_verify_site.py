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
PRIOR_RUN_URL = "https://github.com/example/site/actions/runs/100001"
BUILD_ID = "build-20260822-120000"
PUBLIC_EMAIL = "public@example.com"


def _write_production_tree(tmp_path: Path, *, build_run_url: str = RUN_URL) -> tuple[Path, Path]:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "resume.pdf").write_bytes(b"%PDF-1.7\n")
    (site_dir / "build.log.html").write_text("<html>build log</html>\n", encoding="utf-8")
    (site_dir / "pipeline-status.json").write_text(
        f'{{"result": "success", "exit_code": 0, "build_id": "{BUILD_ID}"}}\n',
        encoding="utf-8",
    )
    (site_dir / "index.html").write_text(
        f'<a href="/build.log.html" title="{BUILD_ID}">log</a><a href="{build_run_url}">run</a>\n',
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


def test_feed_check_allows_literal_entities_but_rejects_double_escaped_quotes(
    tmp_path: Path,
) -> None:
    site_dir = tmp_path / "site"
    post = site_dir / "posts" / "example" / "index.html"
    post.parent.mkdir(parents=True)
    post.write_text("<html></html>\n", encoding="utf-8")

    def _write_feeds(description: str) -> None:
        feed = (
            "<rss><channel><item>"
            f"<description>{description}</description>"
            f"<link>{verifier.PUBLIC_ORIGIN}/posts/example/</link>"
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


def test_production_site_accepts_a_prior_vintage_run(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """A new site deployment may identify the older run that produced its reused vintage result."""
    site_dir, resume_yaml = _write_production_tree(tmp_path, build_run_url=PRIOR_RUN_URL)

    def _run_external(command: str, arguments: Sequence[str], errors: list[str]) -> str:
        del arguments, errors
        if command == "pdftotext":
            return f"Bradley Fidler\n{PUBLIC_EMAIL}\n"
        return "Tagged:          yes\n"

    monkeypatch.setattr(verifier, "run_external", _run_external)

    assert verifier.verify_production_site(site_dir, resume_yaml=resume_yaml, build_run_url=PRIOR_RUN_URL) == []


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


def _write_post_source(tmp_path: Path, slug: str = "published-post", *, draft: bool = False) -> Path:
    posts = tmp_path / "content" / "posts"
    bundle = posts / slug
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "index.md").write_text(
        f"---\ntitle: Test post\ndraft: {'true' if draft else 'false'}\n---\n\nBody.\n",
        encoding="utf-8",
    )
    return posts


def _write_stylesheet(site_dir: Path) -> None:
    stylesheet = site_dir / "assets" / "css" / f"stylesheet.{'a' * 64}.css"
    stylesheet.parent.mkdir(parents=True, exist_ok=True)
    stylesheet.write_text("body {}\n", encoding="utf-8")


def test_output_policy_accepts_only_contract_paths_and_source_backed_resources(tmp_path: Path) -> None:
    posts_source = _write_post_source(tmp_path)
    source_resource = posts_source / "published-post" / "figure.svg"
    source_resource.write_text("<svg></svg>\n", encoding="utf-8")
    site_dir = tmp_path / "site"
    (site_dir / "posts" / "published-post").mkdir(parents=True)
    (site_dir / "posts" / "published-post" / "index.html").write_text("<html></html>\n", encoding="utf-8")
    (site_dir / "posts" / "published-post" / "figure.svg").write_text("<svg></svg>\n", encoding="utf-8")
    (site_dir / "posts" / "page" / "1").mkdir(parents=True)
    (site_dir / "posts" / "page" / "1" / "index.html").write_text("<html></html>\n", encoding="utf-8")
    (site_dir / "favicon.svg").write_text("<svg></svg>\n", encoding="utf-8")
    _write_stylesheet(site_dir)
    errors: list[str] = []

    verifier.verify_output_policy(site_dir, posts_source, errors)

    assert errors == []


def test_output_policy_rejects_drafts_archives_metadata_and_symlinks(tmp_path: Path) -> None:
    posts_source = _write_post_source(tmp_path, slug="draft-post", draft=True)
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    _write_stylesheet(site_dir)
    rejected = (
        "draft.yaml",
        "source.tar.gz",
        "UPPER.HTML",
        "diagnostics/pipeline.log",
        "posts/draft-post/index.html",
        "posts/page/999/index.html",
    )
    for relative_path in rejected:
        path = site_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not public\n", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    (site_dir / "linked.txt").symlink_to(outside)
    errors: list[str] = []

    verifier.verify_output_policy(site_dir, posts_source, errors)

    for relative_path in rejected:
        assert any(relative_path in error for error in errors)
    assert any("symbolic link or special entry: linked.txt" in error for error in errors)


def test_output_policy_rejects_unbacked_and_unapproved_post_resources(tmp_path: Path) -> None:
    posts_source = _write_post_source(tmp_path)
    (posts_source / "published-post" / "private.yaml").write_text("private: true\n", encoding="utf-8")
    site_dir = tmp_path / "site"
    (site_dir / "posts" / "published-post").mkdir(parents=True)
    (site_dir / "posts" / "published-post" / "index.html").write_text("<html></html>\n", encoding="utf-8")
    (site_dir / "posts" / "published-post" / "unbacked.png").write_bytes(b"png")
    _write_stylesheet(site_dir)
    errors: list[str] = []

    verifier.verify_output_policy(site_dir, posts_source, errors)

    assert any("published post resource type is not allowed" in error for error in errors)
    assert any("posts/published-post/unbacked.png" in error for error in errors)


@pytest.mark.parametrize(
    "link",
    (
        "https://example.com/posts/example/",
        "http://brfid.github.io/posts/example/",
        "https://brfid.github.io/%2e%2e/private/",
        "https://brfid.github.io/posts/../../private/",
        "https://brfid.github.io/posts/example/?preview=true",
    ),
)
def test_feed_check_rejects_cross_origin_or_escaping_links(tmp_path: Path, link: str) -> None:
    site_dir = tmp_path / "site"
    target = site_dir / "posts" / "example" / "index.html"
    target.parent.mkdir(parents=True)
    target.write_text("<html></html>\n", encoding="utf-8")
    feed = f"<rss><channel><item><description>Post</description><link>{link}</link></item></channel></rss>\n"
    (site_dir / "index.xml").write_text(feed, encoding="utf-8")
    (site_dir / "posts" / "index.xml").write_text(feed, encoding="utf-8")
    errors: list[str] = []

    verifier.verify_feeds(site_dir, errors)

    assert len(errors) == 2
    assert all("unsafe item link" in error for error in errors)


def test_feed_check_rejects_a_symlink_escape(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    (site_dir / "posts").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "index.html").write_text("<html></html>\n", encoding="utf-8")
    (site_dir / "posts" / "escape").symlink_to(outside, target_is_directory=True)
    link = f"{verifier.PUBLIC_ORIGIN}/posts/escape/"
    feed = f"<rss><channel><item><description>Post</description><link>{link}</link></item></channel></rss>\n"
    (site_dir / "index.xml").write_text(feed, encoding="utf-8")
    (site_dir / "posts" / "index.xml").write_text(feed, encoding="utf-8")
    errors: list[str] = []

    verifier.verify_feeds(site_dir, errors)

    assert len(errors) == 2
    assert all("escapes the rendered site root" in error for error in errors)


def test_text_scan_redacts_international_phones_and_secrets(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    token = "gl" + "pat-" + "A" * 24
    (site_dir / "index.html").write_text(
        f"<p>Call +44 20 7946 0958</p><p>{token}</p>\n",
        encoding="utf-8",
    )
    errors: list[str] = []

    verifier.verify_public_text(site_dir, errors)

    assert "index.html: contains a plausible international phone number" in errors
    assert "index.html: contains possible GitLab access token" in errors
    assert all(token not in error for error in errors)


def test_html_privacy_scan_decodes_entities_and_adjacent_text_nodes(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "index.html").write_text(
        "<p>+1&#32;<span>415</span>&nbsp;<span>555</span>&#32;2671</p>\n",
        encoding="utf-8",
    )
    errors: list[str] = []

    verifier.verify_html_privacy(site_dir, errors)

    assert any("decoded HTML: contains a plausible US phone number" in error for error in errors)
    assert all("415" not in error for error in errors)


def test_output_policy_rejects_nested_post_resource_directory_symlink(tmp_path: Path) -> None:
    posts_source = _write_post_source(tmp_path)
    outside = tmp_path / "outside-resources"
    outside.mkdir()
    (outside / "image.png").write_bytes(b"png")
    (posts_source / "published-post" / "linked-assets").symlink_to(outside, target_is_directory=True)
    site_dir = tmp_path / "site"
    (site_dir / "posts" / "published-post").mkdir(parents=True)
    (site_dir / "posts" / "published-post" / "index.html").write_text("<html></html>\n", encoding="utf-8")
    (site_dir / "posts" / "page" / "1").mkdir(parents=True)
    (site_dir / "posts" / "page" / "1" / "index.html").write_text("<html></html>\n", encoding="utf-8")
    _write_stylesheet(site_dir)
    errors: list[str] = []

    verifier.verify_output_policy(site_dir, posts_source, errors)

    assert any("published post resource is a symbolic link" in error for error in errors)


def test_feed_errors_never_echo_a_rejected_secret_value(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    (site_dir / "posts").mkdir(parents=True)
    token = "github" + "_pat_" + "A" * 30
    link = f"{verifier.PUBLIC_ORIGIN}/posts/missing/?token={token}"
    feed = f"<rss><channel><item><description>{token}</description><link>{link}</link></item></channel></rss>\n"
    (site_dir / "index.xml").write_text(feed, encoding="utf-8")
    (site_dir / "posts" / "index.xml").write_text(feed, encoding="utf-8")
    errors: list[str] = []

    verifier.verify_feeds(site_dir, errors)

    assert errors
    assert all(token not in error for error in errors)


def test_text_scan_recognizes_fine_grained_github_tokens_without_echoing_them(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    token = "github" + "_pat_" + "A" * 30
    (site_dir / "index.html").write_text(f"<p>{token}</p>\n", encoding="utf-8")
    errors: list[str] = []

    verifier.verify_public_text(site_dir, errors)

    assert "index.html: contains possible GitHub access token" in errors
    assert all(token not in error for error in errors)


def test_structured_scan_decodes_json_escaped_secrets(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    token = "github" + "_pat_" + "A" * 30
    escaped = "".join(f"\\u{ord(character):04x}" for character in token)
    (site_dir / "pipeline-status.json").write_text(f'{{"value": "{escaped}"}}\n', encoding="utf-8")
    errors: list[str] = []

    verifier.verify_public_text(site_dir, errors)

    assert "pipeline-status.json: decoded data: contains possible GitHub access token" in errors
    assert all(token not in error for error in errors)


def test_structured_scan_decodes_xml_entity_phones(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    phone = "00 49 30 901820"
    encoded = "".join(f"&#{ord(character)};" for character in phone)
    (site_dir / "index.xml").write_text(f"<root>{encoded}</root>\n", encoding="utf-8")
    errors: list[str] = []

    verifier.verify_public_text(site_dir, errors)

    assert "index.xml: decoded data: contains a plausible international phone number" in errors
    assert all(phone not in error for error in errors)


def test_html_privacy_scan_decodes_sensitive_attribute_values(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "index.html").write_text(
        '<meta name="description" content="Call &amp;#43;44 20 7946 0958">\n',
        encoding="utf-8",
    )
    errors: list[str] = []

    verifier.verify_html_privacy(site_dir, errors)

    assert any("decoded HTML: contains a plausible international phone number" in error for error in errors)
    assert all("7946" not in error for error in errors)


def test_structured_scan_concatenates_split_xml_text(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "icon.svg").write_text(
        "<svg><text>+44 </text><tspan>20 </tspan><tspan>7946 0958</tspan></svg>\n",
        encoding="utf-8",
    )
    errors: list[str] = []

    verifier.verify_public_text(site_dir, errors)

    assert "icon.svg: decoded data: contains a plausible international phone number" in errors


def test_feed_scan_decodes_html_description_attributes(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    target = site_dir / "posts" / "example" / "index.html"
    target.parent.mkdir(parents=True)
    target.write_text("<html></html>\n", encoding="utf-8")
    description = "&lt;span title=&quot;&amp;#43;44 20 7946 0958&quot;&gt;Post&lt;/span&gt;"
    link = f"{verifier.PUBLIC_ORIGIN}/posts/example/"
    feed = f"<rss><channel><item><description>{description}</description><link>{link}</link></item></channel></rss>\n"
    (site_dir / "index.xml").write_text(feed, encoding="utf-8")
    (site_dir / "posts" / "index.xml").write_text(feed, encoding="utf-8")
    errors: list[str] = []

    verifier.verify_feeds(site_dir, errors)

    assert len(errors) == 2
    assert all("decoded content: contains a plausible international phone number" in error for error in errors)
    assert all("7946" not in error for error in errors)
