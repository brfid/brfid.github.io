"""CLI for generating the static resume site (HTML + optional PDF)."""

from __future__ import annotations

import argparse
from pathlib import Path

from .landing import build_landing_page
from .manifest import write_manifest
from .render import copy_file, load_resume, render_resume_html, write_text
from .types import Resume


def build_html(*, src: Path, out_dir: Path, templates_dir: Path) -> tuple[Path, Resume]:
    """Generate resume HTML + CSS into the output directory.

    Args:
        src: Path to JSON Resume input file.
        out_dir: Output directory for published site (typically `site/`).
        templates_dir: Directory containing `resume.html.j2` and `resume.css`.

    Returns:
        Tuple of:
          - Path to the generated resume HTML file (`.../resume/index.html`)
          - Loaded resume dict
    """
    resume: Resume = load_resume(src)
    html = render_resume_html(resume=resume, templates_dir=templates_dir)

    resume_dir = out_dir / "resume"
    index_path = resume_dir / "index.html"
    css_src = templates_dir / "resume.css"
    css_dst = resume_dir / "resume.css"

    write_text(index_path, html)
    if css_src.exists():
        copy_file(css_src, css_dst)
    return index_path, resume


def build_site(*, src: Path, out_dir: Path, templates_dir: Path, html_only: bool) -> None:
    """Build the site and optional artifacts.

    Args:
        src: Path to resume YAML/JSON source file.
        out_dir: Output site directory.
        templates_dir: Templates directory.
        html_only: Whether to skip PDF generation.
    """
    resume_index_path, resume = build_html(
        src=src,
        out_dir=out_dir,
        templates_dir=templates_dir,
    )

    if not html_only:
        # pylint: disable=import-outside-toplevel
        from .pdf import build_pdf

        build_pdf(out_dir=out_dir, resume_url_path="/resume/", pdf_name="resume.pdf")

    # Auto-discover portfolio data adjacent to resume source
    portfolio_src = src.parent / "portfolio.yaml"
    portfolio_nav_path: str | None = "/portfolio/" if portfolio_src.exists() else None

    landing_path = build_landing_page(
        resume=resume,
        out_dir=out_dir,
        templates_dir=templates_dir,
        portfolio_path=portfolio_nav_path,
    )

    nojekyll_path = out_dir / ".nojekyll"
    if not nojekyll_path.exists():
        write_text(nojekyll_path, "")

    print(f"Wrote: {resume_index_path}")
    print(f"Wrote: {landing_path}")

    # Build portfolio page if data file exists (progressive enhancement)
    if portfolio_src.exists():
        # pylint: disable=import-outside-toplevel
        from .portfolio import build_portfolio_page

        basics = resume.get("basics") or {}
        author = str(basics.get("name") or "").strip()
        portfolio_out = build_portfolio_page(
            portfolio_src=portfolio_src,
            out_dir=out_dir,
            templates_dir=templates_dir,
            author=author,
        )
        print(f"Wrote: {portfolio_out}")

    manifest_path = write_manifest(root=out_dir, out_path=out_dir / "vintage-manifest.txt")
    print(f"Wrote: {manifest_path}")


def main(argv: list[str] | None = None) -> int:
    """Entry point for the resume generator CLI.

    Args:
        argv: Optional argument list (primarily for tests).

    Returns:
        Process exit code (0 on success).
    """
    parser = argparse.ArgumentParser(prog="resume-gen")
    parser.add_argument(
        "--in",
        dest="src",
        default="resume.yaml",
        help="Path to resume source (default: resume.yaml)",
    )
    parser.add_argument(
        "--out",
        dest="out",
        default="site",
        help="Output directory for static site (default: site)",
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
    build_site(
        src=Path(args.src),
        out_dir=Path(args.out),
        templates_dir=Path(args.templates),
        html_only=bool(args.html_only),
    )
    return 0
