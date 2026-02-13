from __future__ import annotations

from pathlib import Path
from typing import cast

from resume_generator.landing import build_landing_page
from resume_generator.types import Resume


def test_build_landing_page_omits_optional_sections(tmp_path: Path) -> None:
    templates_dir = Path("templates")
    resume = {"basics": {"name": "Test User", "label": "Engineer"}}  # minimal
    out_dir = tmp_path / "site"

    index_path = build_landing_page(
        resume=cast(Resume, resume),
        out_dir=out_dir,
        templates_dir=templates_dir,
    )

    html = index_path.read_text(encoding="utf-8")
    assert "Test User" in html
    # Without contact.html fragment, we get minimal fallback
    assert "<header>" in html
    assert "Resume (HTML)" in html
    assert "Resume (PDF)" in html


def test_build_landing_page_includes_html_fragment(tmp_path: Path) -> None:
    templates_dir = Path("templates")
    resume = {
        "basics": {
            "name": "Test User",
            "label": "Engineer",
            "email": "test@example.com",
            "profiles": [
                {"network": "LinkedIn", "url": "https://linkedin.com/in/test"},
                {"network": "GitHub", "url": "https://github.com/test"},
            ],
        }
    }
    out_dir = tmp_path / "site"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Create a VAX-generated HTML fragment
    contact_html = """<header>
  <h1>Test User</h1>
  <p class="subtitle">Engineer</p>
  <p class="contact-email">test@example.com</p>
  <nav>
    <a class="pill" href="https://linkedin.com/in/test" rel="me noopener noreferrer">LinkedIn</a>
    <a class="pill" href="https://github.com/test" rel="me noopener noreferrer">GitHub</a>
  </nav>
</header>"""
    (out_dir / "contact.html").write_text(contact_html, encoding="utf-8")

    log_text = "\n".join([f"line {i}" for i in range(30)]) + "\n"
    (out_dir / "vax-build.log").write_text(log_text, encoding="utf-8")

    index_path = build_landing_page(
        resume=cast(Resume, resume),
        out_dir=out_dir,
        templates_dir=templates_dir,
    )

    html = index_path.read_text(encoding="utf-8")
    assert "<h1>Test User</h1>" in html
    assert "Engineer" in html
    assert "test@example.com" in html
    assert 'href="/vax-build.log"' in html  # link to full log is present
    assert "linkedin.com/in/test" in html
    assert "github.com/test" in html
    # Resume links added by JavaScript
    assert "Resume (HTML)" in html
    assert "Resume (PDF)" in html


def test_build_landing_page_includes_build_info_widget(tmp_path: Path) -> None:
    templates_dir = Path("templates")
    resume = {"basics": {"name": "Test User"}}
    out_dir = tmp_path / "site"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Create build info files
    build_info_dir = out_dir / "build-info"
    build_info_dir.mkdir()

    build_info_html = """<div class="build-info">
  <button class="build-badge">Build: test-123 <span class="status success">✓</span></button>
  <div class="build-details">Test build details</div>
</div>"""
    (build_info_dir / "build-info.html").write_text(build_info_html, encoding="utf-8")
    (build_info_dir / "build-info.css").write_text(".build-info { }", encoding="utf-8")

    index_path = build_landing_page(
        resume=cast(Resume, resume),
        out_dir=out_dir,
        templates_dir=templates_dir,
    )

    html = index_path.read_text(encoding="utf-8")
    assert "build-info.css" in html
    assert "build-badge" in html
    assert "Build: test-123" in html
    assert "Test build details" in html
