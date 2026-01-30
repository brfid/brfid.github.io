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
    assert "brad(1)" not in html
    assert "<h2>build</h2>" not in html


def test_build_landing_page_includes_man_and_build_log(tmp_path: Path) -> None:
    templates_dir = Path("templates")
    resume = {
        "basics": {
            "name": "Test User",
            "label": "Engineer",
            "profiles": [{"network": "LinkedIn", "url": "https://linkedin.com/in/test"}],
        }
    }
    out_dir = tmp_path / "site"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "brad.man.txt").write_text("NAME\n    brad - Test\n", encoding="utf-8")
    log_text = "\n".join([f"line {i}" for i in range(30)]) + "\n"
    (out_dir / "vax-build.log").write_text(log_text, encoding="utf-8")

    index_path = build_landing_page(
        resume=cast(Resume, resume),
        out_dir=out_dir,
        templates_dir=templates_dir,
    )

    html = index_path.read_text(encoding="utf-8")
    assert "brad(1)" in html
    assert "NAME" in html
    assert "<h2>build</h2>" not in html  # build log excerpt hidden by default
    assert "line 0" not in html  # build log content not shown inline
    assert 'href="/vax-build.log"' in html  # link to full log is present
    assert "linkedin.com/in/test" in html
