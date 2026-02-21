"""Render resume outputs (HTML/CSS) from resume source inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .normalize import normalize_resume
from .types import Resume, ResumeView


def load_resume(path: Path) -> Resume:
    """Load resume data from disk.

    Args:
        path: Path to a YAML or JSON file.

    Returns:
        Parsed resume object as a dict.
    """
    with path.open("r", encoding="utf-8") as f:
        if path.suffix.lower() == ".json":
            return cast(Resume, json.load(f))
        return cast(Resume, yaml.safe_load(f))


def make_jinja_env(templates_dir: Path) -> Environment:
    """Create a Jinja2 environment configured for HTML templates.

    Shared by both the resume and landing renderers so settings stay in sync.

    Args:
        templates_dir: Directory to load templates from.

    Returns:
        Configured Jinja2 environment.
    """
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


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
    env = make_jinja_env(templates_dir)

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
