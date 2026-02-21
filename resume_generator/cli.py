"""CLI for generating the static resume site (HTML + optional PDF)."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
class VintageOptions:
    """Vintage stage options for the build."""

    enabled: bool
    mode: str
    transcript: Path | None


@dataclass(frozen=True)
class BuildRequest:
    """Parsed build request for generating the site."""

    src: Path
    out_dir: Path
    templates_dir: Path
    build_dir: Path
    html_only: bool
    vintage: VintageOptions
    arpanet: bool = False
    arpanet_execute: bool = False


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

    if req.vintage.enabled:
        # pylint: disable=import-outside-toplevel
        from .vintage_stage import VintageStageConfig, VintageStageRunner

        config = VintageStageConfig(
            resume_path=req.src,
            site_dir=req.out_dir,
            build_dir=req.build_dir,
            mode=req.vintage.mode,
            transcript_path=req.vintage.transcript,
        )
        runner: Any
        if req.arpanet:
            # pylint: disable=import-outside-toplevel
            from .vintage_arpanet_stage import VintageArpanetStageRunner

            runner = VintageArpanetStageRunner(
                config=config,
                repo_root=Path.cwd(),
                execute_commands=req.arpanet_execute,
            )
        else:
            runner = VintageStageRunner(config=config, repo_root=Path.cwd())
        runner.run()
        print(f"Wrote: {runner.paths.brad_man_txt_path}")
        print(f"Wrote: {runner.paths.vintage_build_log_path}")

    # Auto-discover portfolio data adjacent to resume source
    portfolio_src = req.src.parent / "portfolio.yaml"
    portfolio_nav_path: str | None = "/portfolio/" if portfolio_src.exists() else None

    # Build landing page after vintage stage so it can link to vintage-build.log
    landing_path = build_landing_page(
        resume=resume,
        out_dir=req.out_dir,
        templates_dir=req.templates_dir,
        portfolio_path=portfolio_nav_path,
    )

    nojekyll_path = req.out_dir / ".nojekyll"
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
            out_dir=req.out_dir,
            templates_dir=req.templates_dir,
            author=author,
        )
        print(f"Wrote: {portfolio_out}")

    manifest_path = write_manifest(root=req.out_dir, out_path=req.out_dir / "vintage-manifest.txt")
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
        "--with-vintage",
        action="store_true",
        help="Run the vintage stage after generating the resume (local compile or docker).",
    )
    parser.add_argument(
        "--with-arpanet",
        action="store_true",
        help="Enable ARPANET transfer-stage scaffolding (requires --with-vintage).",
    )
    parser.add_argument(
        "--arpanet-execute",
        action="store_true",
        help="Execute ARPANET scaffold commands (requires --with-arpanet).",
    )
    parser.add_argument(
        "--vintage-mode",
        choices=["local", "docker"],
        default="local",
        help="Vintage stage mode when `--with-vintage` is set (default: local).",
    )
    parser.add_argument(
        "--build-dir",
        default="build",
        help="Build directory for intermediate artifacts (default: build).",
    )
    parser.add_argument(
        "--vintage-transcript",
        default=None,
        help="Replay docker/SIMH transcript (docker mode only).",
    )

    args = parser.parse_args(argv)
    if args.with_arpanet and not args.with_vintage:
        parser.error("--with-arpanet requires --with-vintage")
    if args.arpanet_execute and not args.with_arpanet:
        parser.error("--arpanet-execute requires --with-arpanet")

    build_site(
        BuildRequest(
            src=Path(args.src),
            out_dir=Path(args.out),
            templates_dir=Path(args.templates),
            build_dir=Path(args.build_dir),
            html_only=bool(args.html_only),
            vintage=VintageOptions(
                enabled=bool(args.with_vintage),
                mode=str(args.vintage_mode),
                transcript=Path(args.vintage_transcript) if args.vintage_transcript else None,
            ),
            arpanet=bool(args.with_arpanet),
            arpanet_execute=bool(args.arpanet_execute),
        )
    )
    return 0
