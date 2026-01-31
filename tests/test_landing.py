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
    assert "<h2>About</h2>" not in html  # No man page sections without brad.man.txt
    assert "<h2>Contact</h2>" not in html
    assert "<h2>build</h2>" not in html


def test_build_landing_page_includes_man_sections(tmp_path: Path) -> None:
    templates_dir = Path("templates")
    resume = {
        "basics": {
            "name": "Test User",
            "label": "Engineer",
            "profiles": [
                {"network": "LinkedIn", "url": "https://linkedin.com/in/test"},
                {"network": "GitHub", "url": "https://github.com/test"},
            ],
        }
    }
    out_dir = tmp_path / "site"
    out_dir.mkdir(parents=True, exist_ok=True)
    man_content = "DESCRIPTION\n    Test description\nCONTACT\n    Email: test@example.com\n"
    (out_dir / "brad.man.txt").write_text(man_content, encoding="utf-8")
    log_text = "\n".join([f"line {i}" for i in range(30)]) + "\n"
    (out_dir / "vax-build.log").write_text(log_text, encoding="utf-8")

    index_path = build_landing_page(
        resume=cast(Resume, resume),
        out_dir=out_dir,
        templates_dir=templates_dir,
    )

    html = index_path.read_text(encoding="utf-8")
    assert "<h2>About</h2>" in html
    assert "<h2>Contact</h2>" in html
    assert "Test description" in html
    assert "test@example.com" in html
    assert "<h2>build</h2>" not in html  # build log excerpt hidden by default
    assert "line 0" not in html  # build log content not shown inline
    assert 'href="/vax-build.log"' in html  # link to full log is present
    assert "linkedin.com/in/test" in html
    assert "github.com/test" in html
