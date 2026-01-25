from __future__ import annotations

from pathlib import Path

from resume_generator.cli import main


def test_cli_html_only_writes_site(tmp_path: Path) -> None:
    resume_src = tmp_path / "resume.yaml"
    resume_src.write_text(
        "\n".join(
            [
                "basics:",
                "  name: Test User",
                "  label: Engineer",
                "  profiles:",
                "    - network: LinkedIn",
                "      url: https://linkedin.com/in/test",
                "work: []",
                "skills: []",
                "",
            ]
        ),
        encoding="utf-8",
    )

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
