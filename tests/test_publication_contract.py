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


def test_deploy_uses_the_shared_production_verifier() -> None:
    """Deployment must pass quality checks, build the public PDF, and verify the artifact tree."""
    workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")

    assert ".venv/bin/python -m pip install -e '.[dev,pdf]'" in workflow
    assert "run: make check" in workflow
    assert workflow.index("run: make check") < workflow.index("name: Run vintage pipeline")
    assert "make resume-pdf-public" in workflow
    assert "make sync-site-data sync-resume-data" not in workflow
    assert "PYTHON=python" not in workflow
    assert ".venv/bin/python scripts/verify_site.py site" in workflow
    assert "--production" in workflow
    assert "--resume-yaml resume.yaml" in workflow
    assert '--build-run-url "$VINTAGE_RUN_URL"' in workflow
    assert "private_resume_path" not in workflow
    assert "deployments: write" not in workflow


def test_deploy_supports_fail_closed_vintage_reuse() -> None:
    """Fast mode must reuse validated provenance while both modes share one deploy tail."""
    workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    footer = (ROOT / "hugo" / "layouts" / "_partials" / "footer.html").read_text(encoding="utf-8")
    mode_step = workflow.split("- name: Select publish mode", maxsplit=1)[1].split("- name: Set up Hugo", maxsplit=1)[0]
    reuse_step = workflow.split("- name: Download reusable vintage result", maxsplit=1)[1].split(
        "- name: Run vintage pipeline", maxsplit=1
    )[0]
    standard_step = workflow.split("- name: Run vintage pipeline", maxsplit=1)[1].split(
        "- name: Select vintage provenance", maxsplit=1
    )[0]
    retention_step = workflow.split("- name: Retain reusable vintage result", maxsplit=1)[1].split(
        "- name: Upload Pages artifact", maxsplit=1
    )[0]

    assert "publish_mode:" in workflow
    assert "default: standard" in workflow
    assert "[fast]" in workflow
    assert "actions: read" in workflow
    assert "mode=standard" in mode_step
    assert '"$GITHUB_EVENT_NAME" == "workflow_dispatch"' in mode_step
    assert '"$GITHUB_EVENT_NAME" == "push"' in mode_step
    assert "if: steps.mode.outputs.mode == 'fast'" in reuse_step
    assert "if: steps.mode.outputs.mode == 'standard'" in standard_step
    assert "if: steps.mode.outputs.mode == 'standard'" in retention_step
    assert "resume_generator.vintage_reuse fingerprint" in workflow
    assert '[[ ! "$fingerprint" =~ ^[0-9a-f]{64}$ ]]' in workflow
    assert "resume_generator.vintage_reuse validate" in workflow
    assert "No reusable vintage result matches" in workflow
    assert "source_run_url=${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${source_run_id}" in workflow
    assert "'.conclusion'" in reuse_step
    assert "'.head_branch'" in reuse_step
    assert "'.head_sha'" in reuse_step
    assert "'.path'" in reuse_step
    assert '".github/workflows/deploy.yml"' in reuse_step
    assert "VINTAGE_SHA" in workflow
    assert "VINTAGE_RUN_URL" in workflow
    assert "vintage-production-${{ steps.vintage-fingerprint.outputs.value }}" in workflow
    assert "retention-days: 90" in workflow
    for artifact in ("brad.bio.txt", "build.log.html", "pipeline-status.json"):
        assert f"build/vintage/{artifact}" in workflow

    provenance = workflow.index("name: Select vintage provenance")
    assert workflow.index("name: Download reusable vintage result") < provenance
    assert workflow.index("name: Run vintage pipeline") < provenance
    assert provenance < workflow.index("name: Generate bio data for Hugo")
    assert workflow.index("name: Generate bio data for Hugo") < workflow.index("make resume-pdf-public")
    assert workflow.index("make resume-pdf-public") < workflow.index("name: Verify production output")
    assert workflow.index("name: Verify production output") < workflow.index("name: Retain reusable vintage result")
    assert workflow.index("name: Retain reusable vintage result") < workflow.index("name: Upload Pages artifact")
    assert "continue-on-error" not in retention_step
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
