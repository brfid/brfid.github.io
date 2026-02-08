from __future__ import annotations

from pathlib import Path

from resume_generator.cli import main
from tests.helpers import write_minimal_resume


def test_cli_html_only_end_to_end_generates_site_tree(tmp_path: Path) -> None:
    resume_src = tmp_path / "resume.yaml"
    write_minimal_resume(resume_src)

    out_dir = tmp_path / "site"

    rc = main(
        [
            "--in",
            str(resume_src),
            "--out",
            str(out_dir),
            "--templates",
            "templates",
            "--html-only",
        ]
    )
    assert rc == 0
    assert (out_dir / "index.html").exists()
    assert (out_dir / "resume" / "index.html").exists()
    assert (out_dir / ".nojekyll").exists()
