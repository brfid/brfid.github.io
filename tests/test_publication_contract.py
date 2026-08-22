"""Contracts for the site's public surfaces and private-data boundary."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_production_config_publishes_resume() -> None:
    """The production Hugo build must include the resume and its navigation."""
    config = tomllib.loads((ROOT / "hugo" / "hugo.toml").read_text(encoding="utf-8"))
    content = (ROOT / "hugo" / "content" / "resume.md").read_text(encoding="utf-8")

    assert config["params"]["resumeEnabled"] is True
    assert "draft: false" in content
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
    assert menu_items["posts"]["url"] == "/posts/"
    assert menu_items["resume"]["url"] == "/resume/"
    assert menu_items["resume"]["params"]["companionurl"] == "/resume.pdf"
    assert menu_items["source"]["url"] == "https://github.com/brfid/brfid.github.io"
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


def test_deploy_requires_phone_free_resume_html_and_pdf() -> None:
    """Deployment must build and validate both public resume formats."""
    workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")

    assert "make sync-site-data sync-resume-data" in workflow
    assert "make resume-pdf-public PYTHON=python" in workflow
    assert "test -s site/resume/index.html" in workflow
    assert "test -s site/resume.pdf" in workflow
    assert "grep -Fq '/resume.pdf' site/resume/index.html" in workflow
    assert "Resume page is missing the PDF download link" in workflow
    assert "pdftotext site/resume.pdf" in workflow
    assert "pdfinfo site/resume.pdf" in workflow
    assert "'^Tagged:[[:space:]]+yes$'" in workflow
    assert "public resume PDF is not tagged for accessibility" in workflow
    assert "public resume PDF contains a telephone number" in workflow
    assert "test ! -e site/bradley-fidler-resume.pdf" in workflow
    assert "private_resume_path" not in workflow


def test_deploy_requires_blog_routes_and_feeds() -> None:
    """Deployment must fail if the restored blog surface disappears."""
    workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    robots = (ROOT / "hugo" / "static" / "robots.txt").read_text(encoding="utf-8")

    assert "test -s site/posts/index.html" in workflow
    assert "test -s site/index.xml" in workflow
    assert "test -s site/posts/index.xml" in workflow
    assert "landing page is missing the Blog link" in workflow
    assert "public RSS feed contains the resume" in workflow
    assert "Disallow: /index.xml" in robots
    assert "Disallow: /posts/index.xml" in robots


def test_site_chrome_preserves_navigation_accessibility_contract() -> None:
    """Repo-owned chrome must retain its landmarks, current state, and skip path."""
    base = (ROOT / "hugo" / "layouts" / "baseof.html").read_text(encoding="utf-8")
    header = (ROOT / "hugo" / "layouts" / "_partials" / "header.html").read_text(encoding="utf-8")
    post_nav = (ROOT / "hugo" / "layouts" / "_partials" / "post_nav_links.html").read_text(encoding="utf-8")
    footer = (ROOT / "hugo" / "layouts" / "partials" / "footer.html").read_text(encoding="utf-8")
    theme = (ROOT / "hugo" / "assets" / "css" / "extended" / "theme.css").read_text(encoding="utf-8")
    resume_css = (ROOT / "hugo" / "assets" / "css" / "extended" / "resume.css").read_text(encoding="utf-8")

    assert 'class="skip-link" href="#main-content"' in base
    assert 'id="main-content" tabindex="-1"' in base
    assert 'aria-label="Primary navigation"' in header
    assert 'aria-current="page"' in header
    assert 'class="menu-companion-link"' in header
    assert 'class="menu-utility-item"' in header
    assert "#menu .menu-utility-item" in theme
    assert "--interactive-hover:" in theme
    assert "--interactive-highlight" not in theme
    assert "color: var(--interactive-hover);" in theme
    assert ".resume-download-link {\n  color: var(--forest);" not in resume_css
    assert 'aria-label="Post navigation"' in post_nav
    assert 'aria-label", `Switch to ${nextTheme} theme; ${currentTheme} theme is active`' in footer
    assert 'meta[name="theme-color"]' in footer
    assert ">Hugo</a>" in footer
    assert ">PaperMod</a>" in footer
    assert ">VAX/PDP-11 log</a>" in footer
    assert ">Actions run</a>" in footer
    assert ">Site source</a>" not in footer


def test_content_templates_preserve_clear_summaries_and_semantics() -> None:
    """Blog cards and dense content must keep their explicit, accessible structure."""
    list_template = (ROOT / "hugo" / "layouts" / "list.html").read_text(encoding="utf-8")
    resume_template = (ROOT / "hugo" / "layouts" / "_default" / "resume.html").read_text(encoding="utf-8")
    grid = (ROOT / "hugo" / "layouts" / "shortcodes" / "maintenance-grid.html").read_text(encoding="utf-8")

    assert "with .Description" in list_template
    assert ".Summary" in list_template
    assert 'class="section-feed-link"' in list_template
    assert 'href="/resume.pdf"' in resume_template
    assert '<h3 class="resume-item-title' in resume_template
    assert '<h4 class="resume-item-title resume-role-title"' in resume_template
    assert '<caption class="table-caption-sr">' in grid
    assert 'scope="col"' in grid
    assert 'scope="row"' in grid
