from __future__ import annotations

from pathlib import Path

from resume_generator.cli import build_html


def test_build_html_renders_real_resume_yaml(tmp_path: Path) -> None:
    """build_html() should render the actual repo resume.yaml through the real templates."""
    index_path, resume = build_html(
        src=Path("resume.yaml"),
        out_dir=tmp_path / "site",
        templates_dir=Path("templates"),
    )

    assert index_path.exists()
    assert resume["basics"]["name"]
    assert "<html" in index_path.read_text(encoding="utf-8").lower()
