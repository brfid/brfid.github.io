"""CLI for generating the static resume site (HTML + optional PDF)."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
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


@dataclass(frozen=True)
class BuildRequest:
    """Parsed build request for generating the site."""

    src: Path
    out_dir: Path
    templates_dir: Path
    build_dir: Path
    html_only: bool
    with_vax: bool
    vax_mode: str


def build_site(req: BuildRequest) -> None:
    """Build the site and optional artifacts.

    Args:
        req: Build request.
    """
    resume_index_path, resume = build_html(
        src=req.src,
        out_dir=req.out_dir,
        templates_dir=req.templates_dir,
    )

    if not req.html_only:
        # pylint: disable=import-outside-toplevel
        from .pdf import build_pdf

        build_pdf(out_dir=req.out_dir, resume_url_path="/resume/", pdf_name="resume.pdf")

    landing_path = build_landing_page(
        resume=resume,
        out_dir=req.out_dir,
        templates_dir=req.templates_dir,
    )

    nojekyll_path = req.out_dir / ".nojekyll"
    if not nojekyll_path.exists():
        write_text(nojekyll_path, "")

    print(f"Wrote: {resume_index_path}")
    print(f"Wrote: {landing_path}")

    if req.with_vax:
        # pylint: disable=import-outside-toplevel
        from .vax_stage import VaxStageConfig, VaxStageRunner

        runner = VaxStageRunner(
            config=VaxStageConfig(
                resume_path=req.src,
                site_dir=req.out_dir,
                build_dir=req.build_dir,
                mode=req.vax_mode,
            ),
            repo_root=Path.cwd(),
        )
        runner.run()
        print(f"Wrote: {runner.paths.brad_man_txt_path}")
        print(f"Wrote: {runner.paths.vax_build_log_path}")

    manifest_path = write_manifest(root=req.out_dir, out_path=req.out_dir / "vax-manifest.txt")
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
    parser.add_argument(
        "--with-vax",
        action="store_true",
        help="Run the VAX stage after generating the resume (local compile or docker).",
    )
    parser.add_argument(
        "--vax-mode",
        choices=["local", "docker"],
        default="local",
        help="VAX stage mode when `--with-vax` is set (default: local).",
    )
    parser.add_argument(
        "--build-dir",
        default="build",
        help="Build directory for intermediate artifacts (default: build).",
    )

    args = parser.parse_args(argv)
    build_site(
        BuildRequest(
            src=Path(args.src),
            out_dir=Path(args.out),
            templates_dir=Path(args.templates),
            build_dir=Path(args.build_dir),
            html_only=bool(args.html_only),
            with_vax=bool(args.with_vax),
            vax_mode=str(args.vax_mode),
        )
    )
    return 0
