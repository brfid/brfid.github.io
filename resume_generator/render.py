"""Render resume outputs (HTML/CSS) from JSON Resume inputs."""

from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .normalize import normalize_resume
from .types import Resume, ResumeView


def load_resume_json(path: Path) -> Resume:
    """Load JSON Resume data from disk.

    Args:
        path: Path to a JSON file.

    Returns:
        Parsed JSON object as a dict.
    """
    with path.open("r", encoding="utf-8") as f:
        # JSON Resume is a JSON object at the top level.
        return json.load(f)


def render_resume_html(
    *,
    resume: Resume,
    templates_dir: Path,
    template_name: str = "resume.html.j2",
) -> str:
    """Render resume HTML using Jinja2 templates.

    Args:
        resume: Raw JSON Resume dictionary.
        templates_dir: Directory containing templates.
        template_name: Template file name.

    Returns:
        Rendered HTML as a string.
    """
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template = env.get_template(template_name)
    view: ResumeView = normalize_resume(resume)
    return template.render(resume=view)


def write_text(path: Path, content: str) -> None:
    """Write a UTF-8 text file, creating parent directories as needed.

    Args:
        path: Destination path.
        content: Text content to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def copy_file(src: Path, dst: Path) -> None:
    """Copy a file as bytes, creating parent directories as needed.

    Args:
        src: Source path.
        dst: Destination path.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())
