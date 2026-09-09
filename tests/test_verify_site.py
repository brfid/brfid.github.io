from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from site_tools import verify as verifier

PUBLIC_EMAIL = "public@example.com"


def _write_public_tree(tmp_path: Path) -> tuple[Path, Path]:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "resume.pdf").write_bytes(b"%PDF-1.7\n")
    resume_yaml = tmp_path / "resume.yaml"
    resume_yaml.write_text(f"basics:\n  email: {PUBLIC_EMAIL}\n", encoding="utf-8")
    return site_dir, resume_yaml


def test_default_verification_requires_the_public_pdf(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    site_dir, resume_yaml = _write_public_tree(tmp_path)
    (site_dir / "resume.pdf").unlink()
    monkeypatch.setattr(verifier, "verify_site", lambda _site_dir: [])
    assert verifier.main([str(site_dir), "--resume-yaml", str(resume_yaml)]) == 1


def test_public_pdf_accepts_tagged_phone_free_content(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    site_dir, resume_yaml = _write_public_tree(tmp_path)

    def inspect(command: str, arguments: Sequence[str], errors: list[str]) -> str:
        del errors
        assert arguments[0] == str((site_dir / "resume.pdf").resolve())
        return f"Bradley Fidler\n{PUBLIC_EMAIL}\n" if command == "pdftotext" else "Tagged: yes\n"

    monkeypatch.setattr(verifier, "run_external", inspect)
    assert verifier.verify_resume_artifacts(site_dir, resume_yaml=resume_yaml) == []


def test_public_pdf_rejects_phone_leaks_extra_pdfs_and_untagged_content(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    site_dir, resume_yaml = _write_public_tree(tmp_path)
    (site_dir / "application.PDF").write_bytes(b"private PDF")

    def inspect(command: str, arguments: Sequence[str], errors: list[str]) -> str:
        del arguments, errors
        return "Bradley Fidler\n(206) 555-0100\n" if command == "pdftotext" else "Tagged: no\n"

    monkeypatch.setattr(verifier, "run_external", inspect)
    errors = verifier.verify_resume_artifacts(site_dir, resume_yaml=resume_yaml)
    assert any("application.PDF" in error for error in errors)
    assert "resume.pdf: missing the public basics.email" in errors
    assert "resume.pdf: contains a plausible US phone number" in errors
    assert "resume.pdf: PDF is not tagged" in errors


def test_missing_pdf_never_invokes_inspection_tools(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    site_dir, resume_yaml = _write_public_tree(tmp_path)
    (site_dir / "resume.pdf").unlink()

    def unexpected(*args: object) -> str:
        raise AssertionError(f"PDF tools must not run without a PDF: {args}")

    monkeypatch.setattr(verifier, "run_external", unexpected)
    assert "missing, empty, or unsafe public artifact: resume.pdf" in verifier.verify_resume_artifacts(
        site_dir, resume_yaml=resume_yaml
    )


def test_pdf_inspection_timeout_is_a_verification_failure(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(verifier.shutil, "which", lambda _command: "/tools/pdfinfo")

    def stalled(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        raise subprocess.TimeoutExpired("pdfinfo", 30)

    monkeypatch.setattr(verifier.subprocess, "run", stalled)
    errors: list[str] = []
    assert verifier.run_external("pdfinfo", ["resume.pdf"], errors) is None
    assert any("could not run pdfinfo" in error for error in errors)


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


@pytest.mark.parametrize(
    "relative_path",
    (
        "posts/index.html",
        "posts/example/index.html",
        "posts/page/2/index.html",
        "posts/page/10/index.html",
        "posts/page/1/index.html",
        "index.html",
        "resume/index.html",
        "about/index.html",
        "404.html",
        "posts/future-article/index.html",
    ),
)
def test_robots_policy_requires_noindex_on_every_html_page(tmp_path: Path, relative_path: str) -> None:
    page = tmp_path / relative_path
    page.parent.mkdir(parents=True, exist_ok=True)
    policy = "noindex, nofollow, noarchive, nosnippet, noimageindex"
    page.write_text(f'<meta name="robots" content="{policy}">\n', encoding="utf-8")
    errors: list[str] = []

    verifier.verify_robots(tmp_path, errors)

    assert errors == []


@pytest.mark.parametrize("crawler", ("robots", "googlebot", "bingbot"))
@pytest.mark.parametrize("directive", ("index", "follow", "all"))
def test_robots_check_rejects_indexing_permissions_on_posts(tmp_path: Path, crawler: str, directive: str) -> None:
    post = tmp_path / "posts" / "example" / "index.html"
    post.parent.mkdir(parents=True)
    post.write_text(
        '<meta name="robots" content="noindex, nofollow, noarchive, nosnippet, noimageindex">\n'
        f'<meta name="{crawler}" content="{directive}">\n',
        encoding="utf-8",
    )
    errors: list[str] = []

    verifier.verify_robots(tmp_path, errors)

    assert errors == ["posts/example/index.html: conflicting robots index/follow policy"]


def test_robots_check_rejects_the_previous_indexable_blog_policy(tmp_path: Path) -> None:
    post = tmp_path / "posts" / "example" / "index.html"
    post.parent.mkdir(parents=True)
    post.write_text(
        '<meta name="robots" content="index, follow, noarchive">\n',
        encoding="utf-8",
    )
    errors: list[str] = []

    verifier.verify_robots(tmp_path, errors)

    assert errors == [
        "posts/example/index.html: missing full robots no-index policy",
        "posts/example/index.html: conflicting robots index/follow policy",
    ]


@pytest.mark.parametrize("missing", ("noindex", "nofollow", "noarchive", "nosnippet", "noimageindex"))
def test_robots_check_requires_every_exclusion_on_posts(tmp_path: Path, missing: str) -> None:
    post = tmp_path / "posts" / "example" / "index.html"
    post.parent.mkdir(parents=True)
    policy = ", ".join(
        directive
        for directive in ("noindex", "nofollow", "noarchive", "nosnippet", "noimageindex")
        if directive != missing
    )
    post.write_text(f'<meta name="robots" content="{policy}">\n', encoding="utf-8")
    errors: list[str] = []

    verifier.verify_robots(tmp_path, errors)

    assert errors == ["posts/example/index.html: missing full robots no-index policy"]


def test_robots_check_rejects_an_html_page_without_a_policy(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html></html>\n", encoding="utf-8")
    errors: list[str] = []

    verifier.verify_robots(tmp_path, errors)

    assert errors == ["index.html: missing full robots no-index policy"]


def test_sitemap_check_accepts_an_absent_sitemap(tmp_path: Path) -> None:
    errors: list[str] = []

    verifier.verify_no_sitemap(tmp_path, errors)

    assert errors == []


@pytest.mark.parametrize(
    "contents", ("", "<urlset />", "<urlset><url><loc>https://brfid.github.io/posts/</loc></url></urlset>")
)
def test_sitemap_check_rejects_any_retained_sitemap(tmp_path: Path, contents: str) -> None:
    (tmp_path / "sitemap.xml").write_text(
        contents,
        encoding="utf-8",
    )
    errors: list[str] = []

    verifier.verify_no_sitemap(tmp_path, errors)

    assert errors == ["sitemap.xml: must not be published while all HTML is excluded from indexing"]


def test_sitemap_check_rejects_a_broken_sitemap_symlink(tmp_path: Path) -> None:
    (tmp_path / "sitemap.xml").symlink_to(tmp_path / "missing.xml")
    errors: list[str] = []

    verifier.verify_no_sitemap(tmp_path, errors)

    assert errors == ["sitemap.xml: must not be published while all HTML is excluded from indexing"]


def test_robots_file_preserves_html_crawling_and_artifact_exclusions(tmp_path: Path) -> None:
    robots = tmp_path / "robots.txt"
    crawl_policy = "User-agent: *\nAllow: /\nDisallow: /resume.pdf\nDisallow: /index.xml\nDisallow: /posts/index.xml\n"
    robots.write_text(crawl_policy, encoding="utf-8")
    errors: list[str] = []
    verifier.verify_robots_file(tmp_path, errors)
    assert errors == []

    robots.write_text(crawl_policy + "\nSitemap: https://brfid.github.io/sitemap.xml\n", encoding="utf-8")
    verifier.verify_robots_file(tmp_path, errors)
    assert any("unexpected directives" in error for error in errors)


@pytest.mark.parametrize(
    "changed_line",
    ("Allow: /", "Disallow: /resume.pdf", "Disallow: /index.xml", "Disallow: /posts/index.xml"),
)
def test_robots_file_rejects_missing_crawl_contract_directives(tmp_path: Path, changed_line: str) -> None:
    lines = ("User-agent: *", "Allow: /", "Disallow: /resume.pdf", "Disallow: /index.xml", "Disallow: /posts/index.xml")
    (tmp_path / "robots.txt").write_text("\n".join(line for line in lines if line != changed_line), encoding="utf-8")
    errors: list[str] = []

    verifier.verify_robots_file(tmp_path, errors)

    assert any("unexpected directives" in error for error in errors)


@pytest.mark.parametrize("blocked_path", ("/", "/posts/", "/posts/example/"))
def test_robots_file_rejects_html_crawl_blocks(tmp_path: Path, blocked_path: str) -> None:
    crawl_policy = "User-agent: *\nAllow: /\nDisallow: /resume.pdf\nDisallow: /index.xml\nDisallow: /posts/index.xml\n"
    (tmp_path / "robots.txt").write_text(crawl_policy + f"Disallow: {blocked_path}\n", encoding="utf-8")
    errors: list[str] = []

    verifier.verify_robots_file(tmp_path, errors)

    assert any("unexpected directives" in error for error in errors)


def _write_feeds(
    site_dir: Path,
    *,
    link: str = f"{verifier.PUBLIC_ORIGIN}/posts/example/",
    description: str = "Post",
    content: str | None = "<p>Full article.</p>",
) -> None:
    encoded = "" if content is None else f"<content:encoded><![CDATA[{content}]]></content:encoded>"
    feed = (
        '<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item>'
        f"<description>{description}</description><link>{link}</link>{encoded}"
        "</item></channel></rss>\n"
    )
    for relative_path in ("index.xml", "posts/index.xml"):
        path = site_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(feed, encoding="utf-8")


def test_feed_check_allows_literal_entities_but_rejects_double_escaped_quotes(
    tmp_path: Path,
) -> None:
    site_dir = tmp_path / "site"
    post = site_dir / "posts" / "example" / "index.html"
    post.parent.mkdir(parents=True)
    post.write_text("<html></html>\n", encoding="utf-8")

    _write_feeds(site_dir, description="Write &amp;amp; literally")
    errors: list[str] = []
    verifier.verify_feeds(site_dir, errors)
    assert errors == []

    _write_feeds(site_dir, description="Broken apostrophe: &amp;#39;")
    errors = []
    verifier.verify_feeds(site_dir, errors)
    assert len(errors) == 2
    assert all("double-escaped entity" in error for error in errors)


def test_run_external_uses_an_argument_list(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(verifier.shutil, "which", lambda _command: "/tools/pdftotext")

    def _run(arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(arguments)
        assert kwargs == {"check": False, "capture_output": True, "text": True, "timeout": 30}
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

    for directory in (posts_source, source_resource.parent, site_dir, site_dir / "posts" / "published-post"):
        (directory / ".DS_Store").write_bytes(b"Finder metadata")
    for directory in (source_resource.parent, site_dir / "posts" / "published-post"):
        nested = directory / "scans"
        nested.mkdir(exist_ok=True)
        (nested / ".DS_Store").touch()

    verifier.verify_output_policy(site_dir, posts_source, errors)

    assert errors == []


@pytest.mark.parametrize("name", (".private", ".DS_Store.txt", ".DS_Store.png"))
def test_output_policy_still_rejects_other_hidden_files(tmp_path: Path, name: str) -> None:
    posts_source = _write_post_source(tmp_path)
    source = posts_source / "published-post" / name
    source.write_bytes(b"not Finder metadata")
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / name).write_bytes(b"not Finder metadata")
    errors: list[str] = []

    verifier.verify_output_policy(site_dir, posts_source, errors)

    assert f"published post resource has a hidden path component: {source}" in errors
    assert f"rendered output path is not allowed: {name}" in errors


def test_output_policy_rejects_symlinks_named_like_finder_metadata(tmp_path: Path) -> None:
    posts_source = _write_post_source(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"not Finder metadata")
    (posts_source / ".DS_Store").symlink_to(outside)
    resource = posts_source / "published-post" / ".DS_Store"
    resource.symlink_to(outside)
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / ".DS_Store").symlink_to(outside)
    errors: list[str] = []

    verifier.verify_output_policy(site_dir, posts_source, errors)

    assert f"post bundle is not a regular directory: {posts_source / '.DS_Store'}" in errors
    assert f"published post resource is a symbolic link: {resource}" in errors
    assert "rendered output is a symbolic link or special entry: .DS_Store" in errors


def test_output_policy_rejects_drafts_archives_metadata_and_symlinks(tmp_path: Path) -> None:
    posts_source = _write_post_source(tmp_path, slug="draft-post", draft=True)
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    _write_stylesheet(site_dir)
    rejected = (
        "draft.yaml",
        "source.tar.gz",
        "sitemap.xml",
        "UPPER.HTML",
        "diagnostics/pipeline.log",
        "build.log.html",
        "pipeline-status.json",
        "brad.bio.txt",
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
    _write_feeds(site_dir, link=link)
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
    _write_feeds(site_dir, link=link)
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
    _write_feeds(site_dir, link=link, description=token)
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
    _write_feeds(site_dir, link=link, description=description)
    errors: list[str] = []

    verifier.verify_feeds(site_dir, errors)

    assert len(errors) == 2
    assert all("decoded content: contains a plausible international phone number" in error for error in errors)
    assert all("7946" not in error for error in errors)


@pytest.mark.parametrize("content", (None, "", " \n"))
def test_feed_check_requires_full_text(tmp_path: Path, content: str | None) -> None:
    target = tmp_path / "posts" / "example" / "index.html"
    target.parent.mkdir(parents=True)
    target.write_text("<html></html>\n", encoding="utf-8")
    _write_feeds(tmp_path, content=content)
    errors: list[str] = []

    verifier.verify_feeds(tmp_path, errors)

    assert errors == [f"{feed}: item 1: missing full-text content:encoded" for feed in ("index.xml", "posts/index.xml")]


def test_feed_scan_decodes_full_text_attributes(tmp_path: Path) -> None:
    target = tmp_path / "posts" / "example" / "index.html"
    target.parent.mkdir(parents=True)
    target.write_text("<html></html>\n", encoding="utf-8")
    _write_feeds(tmp_path, content='<span title="&#43;44 20 7946 0958">Post</span>')
    errors: list[str] = []

    verifier.verify_feeds(tmp_path, errors)

    assert len(errors) == 2
    assert all("decoded content: contains a plausible international phone number" in error for error in errors)
    assert all("7946" not in error for error in errors)
