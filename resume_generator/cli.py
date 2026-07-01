"""Generate the resume HTML page used as the source for the resume PDF."""

from __future__ import annotations

from pathlib import Path

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
