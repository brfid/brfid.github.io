"""Exercise Hugo output and browser behavior without using the preview directory."""

import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from playwright.sync_api import Browser, Page, expect, sync_playwright

from site_tools.pdf import _serve_directory

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def rendered_site(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[Browser, str]]:
    root = tmp_path_factory.mktemp("rendered-site")
    source = root / "hugo"
    shutil.copytree(
        ROOT / "hugo", source, ignore=shutil.ignore_patterns(".git", "data", ".hugo_build.lock", "resources")
    )
    (source / "data").mkdir()
    for name in ("resume.yaml", "site.yaml"):
        shutil.copy2(ROOT / name, source / "data" / name)
    # Exercise summary fallback and both highlighted and plain code independently of article edits.
    post = source / "content/posts/render-contract/index.md"
    post.parent.mkdir()
    post.write_text(
        "---\ntitle: Render contract\ndate: 2020-01-01\ndraft: false\n---\n\n"
        "Fallback summary.\n\n<!--more-->\n\n## Examples\n\n```text\nHighlighted example\n```\n\n"
        "    Plain example\n",
        encoding="utf-8",
    )
    output = root / "site"
    hugo = shutil.which("hugo")
    assert hugo is not None, "Install Hugo using the README setup instructions"
    subprocess.run(  # noqa: S603 - render repository sources into an isolated test directory.
        [hugo, "--source", str(source), "--destination", str(output), "--panicOnWarning"],
        check=True,
        capture_output=True,
        text=True,
    )
    with _serve_directory(output) as port, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            yield browser, f"http://127.0.0.1:{port}"
        finally:
            browser.close()


@pytest.fixture
def web_page(rendered_site: tuple[Browser, str]) -> Iterator[tuple[Page, str]]:
    browser, origin = rendered_site
    page = browser.new_page(color_scheme="light")
    try:
        yield page, origin
    finally:
        page.close()


def test_navigation_and_theme_controls(web_page: tuple[Page, str]) -> None:
    page, origin = web_page
    page.goto(origin)
    expect(page.get_by_role("navigation", name="Primary navigation")).to_be_visible()
    page.keyboard.press("Tab")
    skip = page.get_by_role("link", name="Skip to content")
    expect(skip).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.get_by_role("main")).to_be_focused()
    expect(page.get_by_role("link", name="Download resume PDF")).to_have_attribute("download", "")
    for name in ("Hugo", "PaperMod"):
        expect(page.get_by_role("contentinfo").get_by_role("link", name=name, exact=True)).to_be_visible()

    blog = page.get_by_role("link", name="Blog", exact=True)
    original_color = blog.evaluate("el => getComputedStyle(el).color")
    blog.hover()
    expect(blog).not_to_have_css("color", original_color)
    page.get_by_role("button", name="Switch to dark theme; light theme is active").click()
    expect(page.get_by_role("button", name="Switch to light theme; dark theme is active")).to_be_visible()
    theme = page.locator("html").evaluate("el => getComputedStyle(el).getPropertyValue('--theme').trim()")
    expect(page.locator('meta[name="theme-color"]')).to_have_attribute("content", theme)
    dark_background = page.locator("body").evaluate("el => getComputedStyle(el).backgroundColor")
    page.reload()
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")

    browser = page.context.browser
    assert browser is not None
    no_script = browser.new_page(java_script_enabled=False, color_scheme="dark")
    try:
        no_script.goto(origin)
        expect(no_script.locator("body")).to_have_css("background-color", dark_background)
    finally:
        no_script.close()


def test_content_semantics_and_conditional_code_copy(web_page: tuple[Page, str]) -> None:
    page, origin = web_page
    source = (ROOT / "hugo/content/posts/doc-rot-maintenance-gap/index.md").read_text(encoding="utf-8")
    post = yaml.safe_load(source.split("---", 2)[1])
    page.goto(f"{origin}/posts/")
    card = page.locator("article").filter(has=page.get_by_role("heading", name=post["title"], exact=True))
    expect(card.locator(".entry-content")).to_have_text(post["description"])
    fallback = page.locator("article").filter(has=page.get_by_role("heading", name="Render contract", exact=True))
    expect(fallback.locator(".entry-content")).to_have_text("Fallback summary. ...")

    page.goto(f"{origin}/posts/doc-rot-maintenance-gap/")
    expect(page.get_by_role("navigation", name="Post navigation")).to_be_visible()
    table = page.get_by_role("table")
    assert table.locator("caption").inner_text().strip()
    expect(table.locator('th[scope="col"]')).to_have_count(3)
    expect(table.locator('th[scope="row"]')).to_have_count(2)
    scripts_without_code = page.locator("script").count()
    expect(page.locator(".copy-code")).to_have_count(0)

    page.goto(f"{origin}/posts/render-contract/")
    expect(page.locator(".copy-code")).to_have_count(2)
    assert page.locator("script").count() == scripts_without_code + 1
    page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=origin)
    page.locator("pre").first.hover()
    page.locator(".copy-code").first.click()
    expect(page.locator(".copy-code").first).to_have_text("copied!")
    assert page.evaluate("navigator.clipboard.readText()") == page.locator("pre > code").first.text_content()

    page.goto(f"{origin}/resume/")
    assert page.locator("script").count() == scripts_without_code
    assert page.get_by_role("heading", level=3).count() > 0
    assert page.get_by_role("heading", level=4).count() > 0


def test_resume_print_styles_are_scoped_to_the_resume(web_page: tuple[Page, str]) -> None:
    page, origin = web_page
    page.emulate_media(media="print")
    page.goto(f"{origin}/resume/")
    expect(page.locator("body")).to_have_css("page", "resume")
    expect(page.locator(".header")).to_be_hidden()
    resume_title_size = page.locator("h1").evaluate("el => getComputedStyle(el).fontSize")
    page.goto(f"{origin}/posts/doc-rot-maintenance-gap/")
    expect(page.locator("body")).to_have_css("page", "auto")
    expect(page.locator(".header")).to_be_visible()
    expect(page.locator("h1")).not_to_have_css("font-size", resume_title_size)
    # Page margins are a CSS rule, not an element's computed style.
    css = (ROOT / "hugo/assets/css/extended/resume.css").read_text(encoding="utf-8")
    assert "@page resume {" in css
    assert "@page {" not in css
