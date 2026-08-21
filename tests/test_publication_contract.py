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
    assert menu_items["posts"]["url"] == "/posts/"
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
    assert "pdftotext site/resume.pdf" in workflow
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
