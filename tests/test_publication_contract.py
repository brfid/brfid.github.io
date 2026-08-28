"""Contracts for the site's public surfaces and private-data boundary."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_production_config_publishes_resume() -> None:
    """The production Hugo build must include the public resume content."""
    content = (ROOT / "hugo" / "content" / "resume.md").read_text(encoding="utf-8")

    assert "draft: true" not in content


def test_production_config_publishes_blog_mechanics() -> None:
    """The blog index, feed, navigation, and draft scaffold must stay available."""
    config = tomllib.loads((ROOT / "hugo" / "hugo.toml").read_text(encoding="utf-8"))
    section = (ROOT / "hugo" / "content" / "posts" / "_index.md").read_text(encoding="utf-8")
    archetype = (ROOT / "hugo" / "archetypes" / "posts" / "index.md").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    menu_items = {item["identifier"]: item for item in config["menu"]["main"]}

    assert "RSS" not in config["disableKinds"]
    assert config["outputs"]["home"] == ["HTML", "RSS"]
    assert config["pagination"]["pagerSize"] == 10
    assert config["params"]["mainSections"] == ["posts"]
    assert config["params"]["ShowRssButtonInSectionTermList"] is True
    assert set(menu_items) == {"posts", "resume", "source"}
    assert menu_items["posts"]["pageRef"] == "/posts"
    assert "url" not in menu_items["posts"]
    assert menu_items["resume"]["pageRef"] == "/resume"
    assert "url" not in menu_items["resume"]
    assert menu_items["resume"]["params"]["companionurl"] == "/resume.pdf"
    assert menu_items["source"]["url"] == "https://gitlab.com/brfid/brfid.gitlab.io"
    assert "params" not in menu_items["source"]
    assert config["params"]["author"] == "Bradley Fidler"
    assert config["params"]["hideAuthor"] is True
    assert 'title: "Blog"' in section
    assert "draft: true" in archetype
    assert "preview-drafts:" in makefile
    assert "--buildDrafts" in makefile.split("preview-drafts:", maxsplit=1)[1].split("\n\n", maxsplit=1)[0]


def test_public_pdf_target_cannot_load_private_phone_overlay() -> None:
    """Only the explicit application-PDF target may name the private overlay."""
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    public_target = makefile.split("resume-pdf-public:", maxsplit=1)[1].split("\n\n", maxsplit=1)[0]
    default_target = makefile.split("resume-pdf:", maxsplit=1)[1].split("\n\n", maxsplit=1)[0]
    application_target = makefile.split("resume-pdf-application:", maxsplit=1)[1].split("\n\n", maxsplit=1)[0]

    assert "private_resume_path" not in public_target
    assert "resume.private.yaml" not in public_target
    assert "private_resume_path" not in default_target
    assert "resume.private.yaml" not in default_target
    assert "pdf_path=Path('site/resume.pdf')" in default_target
    assert "hugo-build-production" in public_target
    assert "pdf_path=Path('site/resume.pdf')" in public_target
    assert "resume-pdf-application: resume-pdf" in makefile
    assert "private_resume_path=Path('resume.private.yaml')" in application_target
    assert "pdf_path=Path('local/bradley-fidler-resume.pdf')" in application_target
    assert "pdf_path=Path('site/resume.pdf')" not in application_target


def test_data_sync_bootstraps_generated_hugo_directory() -> None:
    """A fresh checkout must not depend on an untracked Hugo data directory."""
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    site_target = makefile.split("sync-site-data:", maxsplit=1)[1].split("\n\n", maxsplit=1)[0]
    resume_target = makefile.split("sync-resume-data:", maxsplit=1)[1].split("\n\n", maxsplit=1)[0]

    assert "mkdir -p hugo/data" in site_target
    assert "mkdir -p hugo/data" in resume_target


def test_hugo_build_destinations_are_fixed_and_warnings_are_fatal() -> None:
    """Local and production builds must use fixed destinations and explicit provenance modes."""
    config = tomllib.loads((ROOT / "hugo" / "hugo.toml").read_text(encoding="utf-8"))
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    verify_target = makefile.split("verify-site:", maxsplit=1)[1].split("\n\n", maxsplit=1)[0]
    build_target = makefile.split("hugo-build:", maxsplit=1)[1].split("\n\n", maxsplit=1)[0]
    production_target = makefile.split("hugo-build-production:", maxsplit=1)[1].split("\n\n", maxsplit=1)[0]

    assert "SITE_CHECK_DIR" not in makefile
    assert config["publishDir"] == "../site"
    assert "$(abspath build/site-check)" in verify_target
    assert "clear-local-provenance" in verify_target
    assert "clear-local-provenance" in build_target
    assert "require-production-provenance" in production_target
    assert "--panicOnWarning" in verify_target
    assert "--panicOnWarning" in build_target
    assert "--panicOnWarning" in production_target


def test_gitlab_publish_uses_the_shared_production_verifier() -> None:
    """Publication must pass quality checks, build the public PDF, and verify the artifact tree."""
    pipeline = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    setup = (ROOT / "scripts" / "gitlab" / "setup.sh").read_text(encoding="utf-8")
    publish = (ROOT / "scripts" / "gitlab" / "publish.py").read_text(encoding="utf-8")

    assert ".venv/bin/python -m pip install -e '.[dev,pdf]'" in setup
    assert "bash scripts/gitlab/setup.sh publish" in pipeline
    assert ".venv/bin/python -m scripts.gitlab.publish" in pipeline
    assert 'run([make, "check"], cwd=ROOT)' in publish
    assert publish.index('run([make, "check"], cwd=ROOT)') < publish.index("compute_fingerprint(")
    assert 'run([make, "resume-pdf-public"], cwd=ROOT)' in publish
    assert "make sync-site-data sync-resume-data" not in publish
    assert "PYTHON=python" not in publish
    assert '"scripts/verify_site.py"' in publish
    assert '"--production"' in publish
    assert '"--resume-yaml"' in publish
    assert '"--build-run-url"' in publish
    assert "private_resume_path" not in pipeline
    assert "private_resume_path" not in publish
    assert "pages:\n    publish: site" in pipeline


def test_gitlab_publish_supports_fail_closed_vintage_reuse() -> None:
    """Fast mode must reuse validated provenance while both modes share one publication tail."""
    pipeline = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    publish = (ROOT / "scripts" / "gitlab" / "publish.py").read_text(encoding="utf-8")
    artifacts = (ROOT / "resume_generator" / "gitlab_artifacts.py").read_text(encoding="utf-8")
    reuse = (ROOT / "resume_generator" / "vintage_reuse.py").read_text(encoding="utf-8")
    footer = (ROOT / "hugo" / "layouts" / "_partials" / "footer.html").read_text(encoding="utf-8")

    assert r"\[nopublish\]" in pipeline
    assert r"\[fast\]" in pipeline
    assert 'RUN_PUBLISH_MODE: "standard"' in pipeline
    assert 'RUN_PUBLISH_MODE: "fast"' in pipeline
    assert "resource_group: pages-production" in pipeline
    assert "on_new_commit: none" in pipeline
    assert "interruptible: false" in pipeline
    assert "expire_in: 90 days" in pipeline
    assert "access: all" in pipeline

    assert 'if mode == "standard":' in publish
    assert "download_latest_matching(" in publish
    assert "compute_fingerprint(" in publish
    assert "validate_bundle(" in publish
    assert "create_bundle(" in publish
    assert '"ALLOW_LOCAL_IMAGE_BUILD": "0"' in publish
    assert "vintage-source.env" not in publish

    assert 'STANDARD_PIPELINE_NAME = "publish-standard"' in artifacts
    assert 'STANDARD_JOB_NAME = "publish-standard"' in artifacts
    assert "manifest sha256" in artifacts
    assert "checksum does not match" in artifacts
    assert "no reusable vintage result matches" in artifacts
    assert 'Path(".gitlab-ci.yml")' in reuse
    for implementation in (
        "resume_generator/gitlab_artifacts.py",
        "resume_generator/gitlab_ci.py",
        "scripts/gitlab/publish.py",
        "scripts/gitlab/setup.sh",
    ):
        assert f'Path("{implementation}")' in reuse
    for artifact in ("brad.bio.txt", "build.log.html", "pipeline-status.json"):
        assert f'"{artifact}"' in reuse
        assert f'"{artifact}"' in publish

    publish_body = publish.split("def publish(", maxsplit=1)[1].split("def main(", maxsplit=1)[0]
    validate_index = publish_body.index("validate_bundle(")
    stage_index = publish_body.index("_stage_vintage_for_hugo(")
    pdf_index = publish_body.index('"resume-pdf-public"')
    verify_index = publish_body.index('"scripts/verify_site.py"')
    retain_index = publish_body.index("create_bundle(")
    assert validate_index < stage_index < pdf_index < verify_index < retain_index
    assert "build_bio_yaml(" in publish
    assert "<span>Build:" in footer


def test_site_chrome_preserves_navigation_accessibility_contract() -> None:
    """Repo-owned chrome must retain its landmarks, current state, and skip path."""
    base = (ROOT / "hugo" / "layouts" / "baseof.html").read_text(encoding="utf-8")
    header = (ROOT / "hugo" / "layouts" / "_partials" / "header.html").read_text(encoding="utf-8")
    post_nav = (ROOT / "hugo" / "layouts" / "_partials" / "post_nav_links.html").read_text(encoding="utf-8")
    footer = (ROOT / "hugo" / "layouts" / "_partials" / "footer.html").read_text(encoding="utf-8")
    extended_head = (ROOT / "hugo" / "layouts" / "_partials" / "extend_head.html").read_text(encoding="utf-8")
    theme = (ROOT / "hugo" / "assets" / "css" / "extended" / "theme.css").read_text(encoding="utf-8")
    navigation = (ROOT / "hugo" / "assets" / "css" / "extended" / "navigation.css").read_text(encoding="utf-8")

    assert 'class="skip-link" href="#main-content"' in base
    assert 'id="main-content" tabindex="-1"' in base
    assert 'aria-label="Primary navigation"' in header
    assert 'aria-current="page"' in header
    assert "IsMenuCurrent" in header
    assert "HasMenuCurrent" in header
    assert 'aria-current="location"' in header
    assert "#menu a[aria-current]" in navigation
    assert 'class="menu-companion-link"' in header
    assert 'class="menu-utility-item"' in header
    assert "#menu .menu-utility-item" in theme
    assert "--interactive-hover:" in theme
    assert ':root[data-theme="auto"]' in theme
    assert "@media (prefers-color-scheme: dark)" in theme
    assert "<noscript>" not in extended_head
    assert "color: var(--interactive-hover);" in theme
    assert 'aria-label="Post navigation"' in post_nav
    assert 'aria-label", `Switch to ${nextTheme} theme; ${currentTheme} theme is active`' in footer
    assert 'meta[name="theme-color"]' in footer
    assert ">Hugo</a>" in footer
    assert ">PaperMod</a>" in footer
    assert ">VAX/PDP-11 log</a>" in footer
    assert ">GitLab pipeline</a>" in footer
    assert ">Site source</a>" not in footer


def test_content_templates_preserve_clear_summaries_and_semantics() -> None:
    """Blog cards and dense content must keep their explicit, accessible structure."""
    list_template = (ROOT / "hugo" / "layouts" / "list.html").read_text(encoding="utf-8")
    resume_template = (ROOT / "hugo" / "layouts" / "resume.html").read_text(encoding="utf-8")
    grid = (ROOT / "hugo" / "layouts" / "_shortcodes" / "maintenance-grid.html").read_text(encoding="utf-8")

    assert "with .Description" in list_template
    assert ".Summary" in list_template
    assert 'class="section-feed-link"' in list_template
    assert 'href="/resume.pdf"' in resume_template
    assert '<h3 class="resume-item-title' in resume_template
    assert '<h4 class="resume-item-title"' in resume_template
    assert '<caption class="table-caption-sr">' in grid
    assert 'scope="col"' in grid
    assert 'scope="row"' in grid


def test_resume_print_styles_are_scoped_to_the_resume() -> None:
    """Resume PDF geometry and typography must not leak into printed posts."""
    base = (ROOT / "hugo" / "layouts" / "baseof.html").read_text(encoding="utf-8")
    resume_css = (ROOT / "hugo" / "assets" / "css" / "extended" / "resume.css").read_text(encoding="utf-8")

    assert "else if eq .Layout `resume`" in base
    assert '<body class="resume-page" id="top">' in base
    assert "@page resume {" in resume_css
    assert "@page {" not in resume_css
    assert "page: resume;" in resume_css
    assert "body.resume-page .post-title" in resume_css
    assert "body.resume-page .post-content h2" in resume_css
    assert "body.resume-page a" in resume_css
