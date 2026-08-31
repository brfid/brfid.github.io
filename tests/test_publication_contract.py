"""Contracts for the site's public surfaces and private-data boundary."""

import tomllib
from pathlib import Path

import pytest

from resume_generator import github_ci

ROOT = Path(__file__).resolve().parents[1]
VALID_COMMIT_SHA = "0123456789abcdef0123456789abcdef01234567"


def _set_valid_publish_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        "GITHUB_REF_NAME": "main",
        "GITHUB_REF_TYPE": "branch",
        "GITHUB_REF_PROTECTED": "true",
        "GITHUB_SHA": VALID_COMMIT_SHA,
        "GITHUB_JOB": "publish-standard",
        "GITHUB_RUN_ID": "42",
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_REPOSITORY": "brfid/brfid.github.io",
        "GITHUB_REPOSITORY_ID": "743333428",
        "GITHUB_SERVER_URL": "https://github.com",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(github_ci, "checked_out_commit", lambda _root: VALID_COMMIT_SHA)


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


def test_github_publish_uses_the_shared_production_verifier() -> None:
    """Publication must build the public PDF and verify the artifact tree after its CI gates."""
    pipeline = (ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
    setup = (ROOT / "scripts" / "github" / "setup.sh").read_text(encoding="utf-8")
    publish = (ROOT / "scripts" / "github" / "publish.py").read_text(encoding="utf-8")

    assert '--require-hashes -r "$lock_file"' in setup
    assert "install_python_environment requirements/publish.lock" in setup
    assert "--no-deps --no-build-isolation -e ." in setup
    assert "pip install --upgrade" not in setup
    assert "bash scripts/github/setup.sh publish" in pipeline
    assert ".venv/bin/python -m scripts.github.publish" in pipeline
    assert 'run([make, "check"], cwd=ROOT)' not in publish
    assert 'run([make, "resume-pdf-public"], cwd=ROOT)' in publish
    assert "make sync-site-data sync-resume-data" not in publish
    assert "PYTHON=python" not in publish
    assert '"scripts/verify_site.py"' in publish
    assert '"--production"' in publish
    assert '"--resume-yaml"' in publish
    assert '"--build-run-url"' in publish
    assert "private_resume_path" not in pipeline
    assert "private_resume_path" not in publish
    assert "actions/upload-pages-artifact@v5" in pipeline
    assert "actions/deploy-pages@v5" in pipeline


def test_github_publish_jobs_require_gates_and_upload_only_on_success() -> None:
    """Both publication modes require shared gates and expose artifacts only after success."""
    pipeline = (ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
    standard_job = pipeline.split("\n  publish-standard:\n", maxsplit=1)[1]
    standard_job = standard_job.split("\n  publish-fast:\n", maxsplit=1)[0]
    fast_job = pipeline.split("\n  publish-fast:\n", maxsplit=1)[1]

    assert "workflow_dispatch:" in pipeline
    assert "operation:" in pipeline
    assert "needs: [checks, secret-scan]" in pipeline
    assert "needs: plan" in standard_job
    assert "needs: plan" in fast_job
    assert "needs.plan.outputs.mode == 'standard'" in standard_job
    assert "needs.plan.outputs.mode == 'fast'" in fast_job
    for job in (standard_job, fast_job):
        assert "concurrency:" in job
        assert "group: pages-production" in job
        assert "cancel-in-progress: false" in job
        assert "continue-on-error: true" not in job.split("Deploy to GitHub Pages", maxsplit=1)[0]
    assert "Upload reusable vintage bundle" in standard_job
    assert "Upload reusable vintage bundle" not in fast_job
    assert "retention-days: 90" in standard_job
    assert 'GITLEAKS_LOG_OPTS: "--all --no-merges"' in pipeline
    assert "--no-banner" not in pipeline


def test_github_publish_identity_is_fixed(monkeypatch: pytest.MonkeyPatch) -> None:
    """The validated context must use fixed production identity, independent of caller overrides."""
    _set_valid_publish_environment(monkeypatch)

    context = github_ci.GitHubJobIdentity.from_environment(
        ROOT,
        expected_branch="main",
        expected_jobs=("publish-standard", "publish-fast"),
        require_protected=True,
    )
    shared = (ROOT / "resume_generator" / "github_ci.py").read_text(encoding="utf-8")

    assert context.branch == "main"
    assert context.commit_sha == VALID_COMMIT_SHA
    assert context.repository_id == 743333428
    assert context.repository == "brfid/brfid.github.io"
    assert context.repository_url == "https://github.com/brfid/brfid.github.io"
    assert context.server_url == "https://github.com"
    assert context.event_name == "push"
    assert context.job_name == "publish-standard"
    assert context.ref_protected is True
    assert context.run_url == "https://github.com/brfid/brfid.github.io/actions/runs/42"
    assert "shell=False" in shared
    assert "shell=True" not in shared


@pytest.mark.parametrize(
    ("variable", "override"),
    (
        ("GITHUB_REF_NAME", "release"),
        ("GITHUB_SHA", "f" * 40),
        ("GITHUB_REPOSITORY_ID", "1"),
        ("GITHUB_REPOSITORY", "someone/brfid.github.io"),
        ("GITHUB_SERVER_URL", "https://example.com"),
    ),
)
def test_github_publish_rejects_identity_overrides(
    monkeypatch: pytest.MonkeyPatch, variable: str, override: str
) -> None:
    """Manual variables must not redirect or reauthorize a production publication."""
    _set_valid_publish_environment(monkeypatch)
    monkeypatch.setenv(variable, override)

    with pytest.raises(ValueError, match=variable):
        github_ci.GitHubJobIdentity.from_environment(
            ROOT,
            expected_branch="main",
            expected_jobs=("publish-standard", "publish-fast"),
            require_protected=True,
        )


@pytest.mark.parametrize(
    ("variable", "override", "message"),
    (
        ("GITHUB_REF_PROTECTED", "false", "protected GitHub ref"),
        ("GITHUB_JOB", "vintage-validation", "GITHUB_JOB"),
        ("GITHUB_EVENT_NAME", "schedule", "GITHUB_EVENT_NAME"),
    ),
)
def test_github_publish_rejects_wrong_job_context(
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
    override: str,
    message: str,
) -> None:
    _set_valid_publish_environment(monkeypatch)
    monkeypatch.setenv(variable, override)

    with pytest.raises(ValueError, match=message):
        github_ci.GitHubJobIdentity.from_environment(
            ROOT,
            expected_branch="main",
            expected_jobs=("publish-standard", "publish-fast"),
            require_protected=True,
        )


def test_github_supply_chain_is_hash_locked() -> None:
    pipeline = (ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
    setup = (ROOT / "scripts" / "github" / "setup.sh").read_text(encoding="utf-8")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert project["build-system"]["requires"] == ["setuptools==84.0.0", "wheel==0.48.0"]
    for lock_name in ("build.lock", "runtime.lock", "publish.lock", "dev.lock"):
        lock = (ROOT / "requirements" / lock_name).read_text(encoding="utf-8")
        assert "--hash=sha256:" in lock
    assert "requirements/hugo.sha256" in setup
    assert "hugo_$(" not in setup
    assert "hugo_${HUGO_VERSION}_checksums.txt" not in setup
    assert "pip install --upgrade" not in setup
    assert ".cache/ms-playwright/" not in pipeline
    assert "fetch-depth: 0" in pipeline
    assert pipeline.count("submodules: recursive") == 3


def test_github_publish_supports_fail_closed_vintage_reuse() -> None:
    """Fast mode must reuse validated provenance while both modes share one publication tail."""
    pipeline = (ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
    publish = (ROOT / "scripts" / "github" / "publish.py").read_text(encoding="utf-8")
    artifacts = (ROOT / "resume_generator" / "github_artifacts.py").read_text(encoding="utf-8")
    reuse = (ROOT / "resume_generator" / "vintage_reuse.py").read_text(encoding="utf-8")
    footer = (ROOT / "hugo" / "layouts" / "_partials" / "footer.html").read_text(encoding="utf-8")

    assert '"[nopublish]"' in pipeline
    assert '"[fast]"' in pipeline
    assert "publish_mode:" in pipeline
    assert "needs.plan.outputs.mode == 'standard'" in pipeline
    assert "needs.plan.outputs.mode == 'fast'" in pipeline
    assert "group: pages-production" in pipeline
    assert "cancel-in-progress: false" in pipeline
    assert "retention-days: 90" in pipeline

    assert 'if mode == "standard":' in publish
    assert "download_latest_matching(" in publish
    assert "compute_fingerprint(" in publish
    assert "validate_bundle(" in publish
    assert "create_bundle(" in publish
    assert '"ALLOW_LOCAL_IMAGE_BUILD": "0"' in publish
    assert "vintage-source.env" not in publish

    assert 'WORKFLOW_FILE = "publish.yml"' in artifacts
    assert 'STANDARD_JOB_NAME = "publish-standard"' in artifacts
    assert "manifest sha256" in artifacts
    assert "checksum does not match" in artifacts
    assert "no reusable vintage result matches" in artifacts
    assert "FINGERPRINT_ROOTS" in reuse
    for guarded_root in ("resume_generator", "scripts", "vintage"):
        assert f'Path("{guarded_root}")' in reuse
    assert "load_image_pair(root)" in reuse
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
    assert ">GitHub Actions run</a>" in footer
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
