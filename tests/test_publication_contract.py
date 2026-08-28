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


def test_pages_deploy_publishes_only_the_verified_redirect() -> None:
    """Pages must deploy the dedicated redirect without legacy build dependencies."""
    workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    build = "hugo --source redirect --destination ../site --cleanDestinationDir --panicOnWarning"
    verify = "python3 scripts/verify_redirect.py site"

    assert "name: Publish redirect" in workflow
    assert "actions/checkout@v7" in workflow
    assert 'hugo-version: "0.163.3"' in workflow
    assert "actions/configure-pages@v5" in workflow
    assert "if: github.ref == 'refs/heads/main'" in workflow
    assert build in workflow
    assert verify in workflow
    assert "actions/upload-pages-artifact@v5" in workflow
    assert "with:\n          path: site" in workflow
    assert workflow.count("actions/deploy-pages@v5") == 3
    assert "pages: write" in workflow
    assert "id-token: write" in workflow
    assert workflow.index(build) < workflow.index(verify)
    assert workflow.index(verify) < workflow.index("actions/upload-pages-artifact@v5")
    assert workflow.index("actions/upload-pages-artifact@v5") < workflow.index("actions/deploy-pages@v5")

    for retired_dependency in (
        "submodules:",
        "pip install",
        "playwright",
        "make check",
        "resume-pdf",
        "vintage",
        "pipeline-status",
        "build.log",
        "[fast]",
        "[nopublish]",
    ):
        assert retired_dependency not in workflow.lower()


def test_redirect_source_fixes_the_destination_and_disables_legacy_outputs() -> None:
    """The redirect must preserve locations without accepting a visitor-controlled host."""
    config = tomllib.loads((ROOT / "redirect" / "hugo.toml").read_text(encoding="utf-8"))
    partial = (ROOT / "redirect" / "layouts" / "partials" / "redirect.html").read_text(encoding="utf-8")
    fallback = (ROOT / "redirect" / "layouts" / "404.html").read_text(encoding="utf-8")
    robots = (ROOT / "redirect" / "static" / "robots.txt").read_text(encoding="utf-8")

    assert config["baseURL"] == "https://brfid.github.io/"
    assert config["locale"] == "en-US"
    assert set(config["disableKinds"]) == {"RSS", "sitemap", "taxonomy", "term"}
    assert config["params"]["destinationBaseURL"] == "https://brfid.gitlab.io"
    assert '{{ partial "redirect.html" (dict "TargetPath" "/") }}' in fallback
    assert "new URL({{ site.Params.destinationBaseURL" in partial
    assert "destination.pathname = window.location.pathname" in partial
    assert "destination.search = window.location.search" in partial
    assert "destination.hash = window.location.hash" in partial
    assert "window.location.replace(destination.href)" in partial
    assert "noindex, nofollow, noarchive, nosnippet, noimageindex" in partial
    assert (
        robots == "# HTML remains crawlable so crawlers can observe its noindex directive.\nUser-agent: *\nAllow: /\n"
    )


def test_deploy_is_the_only_workflow_allowed_to_publish_pages() -> None:
    """Manual vintage maintenance must remain disconnected from GitHub Pages."""
    workflows = ROOT / ".github" / "workflows"
    publishers = [
        path.name
        for pattern in ("*.yml", "*.yaml")
        for path in workflows.glob(pattern)
        if "actions/deploy-pages" in path.read_text(encoding="utf-8")
    ]

    assert publishers == ["deploy.yml"]


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
    assert ">Actions run</a>" in footer
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
