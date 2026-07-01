from __future__ import annotations

from pathlib import Path

from resume_generator.cli import build_html
from tests.helpers import write_minimal_resume


def test_build_html_writes_resume_page(tmp_path: Path) -> None:
    resume_src = tmp_path / "resume.yaml"
    write_minimal_resume(resume_src)

    out_dir = tmp_path / "site"

    index_path, resume = build_html(
        src=resume_src,
        out_dir=out_dir,
        templates_dir=Path("templates"),
    )

    assert index_path == out_dir / "resume" / "index.html"
    assert index_path.exists()
    assert resume["basics"]["name"] == "Test User"
