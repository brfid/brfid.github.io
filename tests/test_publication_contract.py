"""Exercise Hugo and browser behavior with controlled publication content."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, expect, sync_playwright

from site_tools.http import serve_directory

ROOT = Path(__file__).resolve().parents[1]


def render_site(root: Path, *, extra_posts: int = 0) -> Path:
    """Render repository templates with a small synthetic post collection."""
    source = root / "hugo"
    shutil.copytree(
        ROOT / "hugo", source, ignore=shutil.ignore_patterns(".git", "data", ".hugo_build.lock", "resources")
    )
    posts = source / "content/posts"
    shutil.rmtree(posts)
    posts.mkdir()
    (posts / "_index.md").write_text('---\ntitle: "Blog"\n---\n', encoding="utf-8")
    (source / "data").mkdir()
    for name in ("resume.yaml", "site.yaml"):
        shutil.copy2(ROOT / name, source / "data" / name)

    corpus = {
        "described-contract": (
            'title: "Described contract"\ndate: 2020-01-04\ndescription: "Controlled description."\ndraft: false',
            "A post without code.\n\n{{< maintenance-grid >}}\n",
        ),
        "render-contract": (
            'title: "Render contract"\ndate: 2020-01-03\ndraft: false',
            "Fallback summary.\n\n<!--more-->\n\n## Examples\n\n```text\nHighlighted example\n```\n\n"
            "    Plain example\n",
        ),
        "reading-contract": (
            'title: "Reading contract"\ndate: 2020-01-02\ndraft: false',
            f"{' '.join(['body'] * 212)}.[^contract]\n\n[^contract]: {' '.join(['note'] * 212)}\n",
        ),
        "draft-contract": (
            'title: "Draft contract"\ndate: 2020-01-01\ndraft: true',
            "This draft must not be published.\n",
        ),
    }
    for slug, (front_matter, body) in corpus.items():
        bundle = posts / slug
        bundle.mkdir()
        (bundle / "index.md").write_text(f"---\n{front_matter}\n---\n\n{body}", encoding="utf-8")
    for number in range(extra_posts):
        bundle = posts / f"extra-{number:02d}"
        bundle.mkdir()
        (bundle / "index.md").write_text(
            f"---\ntitle: Extra {number}\ndate: 2021-01-{number + 1:02d}\ndraft: false\n---\n\nExtra body.\n",
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
    return output


@pytest.fixture(scope="module")
def rendered_site(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[Browser, str]]:
    output = render_site(tmp_path_factory.mktemp("rendered-site"))
    with serve_directory(output) as port, sync_playwright() as playwright:
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


def test_navigation_and_keyboard_access(web_page: tuple[Page, str]) -> None:
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


def test_theme_choice_persists_and_no_script_mode_uses_system_theme(web_page: tuple[Page, str]) -> None:
    page, origin = web_page
    page.goto(origin)
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


def test_summaries_and_comparison_grid(web_page: tuple[Page, str]) -> None:
    page, origin = web_page
    page.goto(f"{origin}/posts/")
    card = page.locator("article").filter(has=page.get_by_role("heading", name="Described contract", exact=True))
    expect(card.locator(".entry-content")).to_have_text("Controlled description.")
    fallback = page.locator("article").filter(has=page.get_by_role("heading", name="Render contract", exact=True))
    expect(fallback.locator(".entry-content")).to_have_text("Fallback summary. ...")

    page.goto(f"{origin}/posts/described-contract/")
    expect(page.get_by_role("navigation", name="Post navigation")).to_be_visible()
    table = page.get_by_role("table")
    assert table.locator("caption").inner_text().strip()
    expect(table.locator('th[scope="col"]')).to_have_count(3)
    expect(table.locator('th[scope="row"]')).to_have_count(2)
    expect(page.locator(".copy-code")).to_have_count(0)


def test_highlighted_and_plain_code_can_be_copied(web_page: tuple[Page, str]) -> None:
    page, origin = web_page
    page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=origin)
    page.goto(f"{origin}/posts/render-contract/")
    expect(page.locator(".copy-code")).to_have_count(2)
    for number in range(2):
        code = page.locator("pre > code").nth(number)
        code.hover()
        button = page.locator(".copy-code").nth(number)
        button.click()
        expect(button).to_have_text("copied!")
        assert page.evaluate("navigator.clipboard.readText()") == code.text_content()


def test_reading_time_separates_article_and_notes(web_page: tuple[Page, str]) -> None:
    page, origin = web_page
    page.goto(f"{origin}/posts/")
    reading_card = page.locator("article").filter(has=page.get_by_role("heading", name="Reading contract", exact=True))
    expect(reading_card.locator(".reading-time")).to_have_text("(1 min read + 1 min notes)")

    page.goto(f"{origin}/posts/reading-contract/")
    expect(page.locator(".post-meta .reading-time")).to_have_text("(1 min read + 1 min notes)")
    page.goto(f"{origin}/posts/render-contract/")
    expect(page.locator(".post-meta .reading-time")).to_have_text("1 min read")


def test_pagination_and_drafts_use_controlled_posts(tmp_path: Path) -> None:
    output = render_site(tmp_path, extra_posts=10)
    first_page = (output / "posts/index.html").read_text(encoding="utf-8")
    second_page = (output / "posts/page/2/index.html").read_text(encoding="utf-8")
    assert "Described contract" not in first_page
    assert "Described contract" in second_page
    assert not (output / "posts/draft-contract/index.html").exists()


def test_resume_print_styles_are_scoped_to_the_resume(web_page: tuple[Page, str]) -> None:
    page, origin = web_page
    page.emulate_media(media="print")
    page.goto(f"{origin}/resume/")
    expect(page.locator("body")).to_have_css("page", "resume")
    expect(page.locator(".header")).to_be_hidden()
    resume_title_size = page.locator("h1").evaluate("el => getComputedStyle(el).fontSize")
    page.goto(f"{origin}/posts/described-contract/")
    expect(page.locator("body")).to_have_css("page", "auto")
    expect(page.locator(".header")).to_be_visible()
    expect(page.locator("h1")).not_to_have_css("font-size", resume_title_size)
    css = (ROOT / "hugo/assets/css/extended/resume.css").read_text(encoding="utf-8")
    assert "@page resume {" in css
    assert "@page {" not in css
