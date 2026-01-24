"""CLI for generating the static resume site (HTML + optional PDF)."""

from __future__ import annotations

import argparse
from pathlib import Path

from .render import copy_file, load_resume_json, render_resume_html, write_text


def build_html(*, src: Path, out_dir: Path, templates_dir: Path) -> Path:
    """Generate resume HTML + CSS into the output directory.

    Args:
        src: Path to JSON Resume input file.
        out_dir: Output directory for published site (typically `public/`).
        templates_dir: Directory containing `resume.html.j2` and `resume.css`.

    Returns:
        Path to the generated HTML file (`.../resume/index.html`).
    """
    resume = load_resume_json(src)
    html = render_resume_html(resume=resume, templates_dir=templates_dir)

    resume_dir = out_dir / "resume"
    index_path = resume_dir / "index.html"
    css_src = templates_dir / "resume.css"
    css_dst = resume_dir / "resume.css"

    write_text(index_path, html)
    if css_src.exists():
        copy_file(css_src, css_dst)
    return index_path


def main(argv: list[str] | None = None) -> int:
    """Entry point for the `resume-site` console script.

    Args:
        argv: Optional argument list (primarily for tests).

    Returns:
        Process exit code (0 on success).
    """
    parser = argparse.ArgumentParser(prog="resume-site")
    parser.add_argument(
        "--in",
        dest="src",
        default="resume/resume.json",
        help="Path to JSON Resume source (default: resume/resume.json)",
    )
    parser.add_argument(
        "--out",
        dest="out",
        default="public",
        help="Output directory for static site (default: public)",
    )
    parser.add_argument(
        "--templates",
        dest="templates",
        default="templates",
        help="Templates directory (default: templates)",
    )
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="Only generate HTML/CSS (skip PDF).",
    )

    args = parser.parse_args(argv)
    src = Path(args.src)
    out_dir = Path(args.out)
    templates_dir = Path(args.templates)

    index_path = build_html(src=src, out_dir=out_dir, templates_dir=templates_dir)

    if not args.html_only:
        from .pdf import build_pdf

        build_pdf(out_dir=out_dir, resume_url_path="/resume/", pdf_name="resume.pdf")

    print(f"Wrote: {index_path}")
    return 0
