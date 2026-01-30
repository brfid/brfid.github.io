"""Render the landing page (`site/index.html`) from templates and optional artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .resume_fields import get_profile_url
from .types import Resume


@dataclass(frozen=True)
class LandingContext:  # pylint: disable=too-many-instance-attributes
    """Template context for the landing page."""

    name: str
    label: str | None
    linkedin_url: str | None
    resume_html_path: str
    resume_pdf_path: str
    man_description: str | None
    man_contact: str | None
    vax_log_excerpt: str | None
    vax_log_path: str | None


def _env_for_templates(templates_dir: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _read_optional_text(path: Path) -> str | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    return text.strip() or None


def _excerpt_lines(text: str, *, max_lines: int = 14) -> str:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    excerpt = lines[:max_lines]
    return "\n".join(excerpt).rstrip()


def _parse_man_sections(man_text: str) -> tuple[str | None, str | None]:
    """Parse DESCRIPTION and CONTACT sections from brad.man.txt.

    Args:
        man_text: The raw brad.man.txt content.

    Returns:
        Tuple of (description, contact) text. Each is None if not found.
    """
    lines = man_text.splitlines()
    current_section: str | None = None
    description_lines: list[str] = []
    contact_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped == "DESCRIPTION":
            current_section = "DESCRIPTION"
        elif stripped == "CONTACT":
            current_section = "CONTACT"
        elif stripped:  # Non-empty content line
            if current_section == "DESCRIPTION":
                # Strip leading whitespace and join as continuous text
                description_lines.append(stripped)
            elif current_section == "CONTACT":
                # Keep contact lines separate but strip indentation
                contact_lines.append(stripped)

    # Join description as a single paragraph
    description = " ".join(description_lines) if description_lines else None
    # Keep contact lines separated
    contact = "\n".join(contact_lines) if contact_lines else None
    return description, contact


def _build_context(*, resume: Resume, out_dir: Path) -> LandingContext:
    """Build the landing template context.

    Args:
        resume: Raw JSON Resume dict.
        out_dir: Output directory (typically `site/`).

    Returns:
        Landing context for the template.
    """
    basics = resume.get("basics") or {}
    name = str(basics.get("name") or "Resume").strip() or "Resume"
    label_raw = str(basics.get("label") or "").strip()
    label = label_raw or None

    man_text = _read_optional_text(out_dir / "brad.man.txt")
    man_description, man_contact = _parse_man_sections(man_text) if man_text else (None, None)

    vax_log = _read_optional_text(out_dir / "vax-build.log")
    vax_log_excerpt = _excerpt_lines(vax_log) if vax_log else None
    vax_log_path = "/vax-build.log" if vax_log else None

    return LandingContext(
        name=name,
        label=label,
        linkedin_url=get_profile_url(basics, "LinkedIn"),
        resume_html_path="/resume/",
        resume_pdf_path="/resume.pdf",
        man_description=man_description,
        man_contact=man_contact,
        vax_log_excerpt=vax_log_excerpt,
        vax_log_path=vax_log_path,
    )


def build_landing_page(
    *,
    resume: Resume,
    out_dir: Path,
    templates_dir: Path,
    template_name: str = "index.html.j2",
) -> Path:
    """Render the landing page to `<out_dir>/index.html`.

    Args:
        resume: Raw JSON Resume dict.
        out_dir: Output directory (typically `site/`).
        templates_dir: Directory containing the landing template.
        template_name: Template file name (default: `index.html.j2`).

    Returns:
        Path to the generated HTML file.
    """
    ctx = _build_context(resume=resume, out_dir=out_dir)

    env = _env_for_templates(templates_dir)
    template = env.get_template(template_name)
    html = template.render(**ctx.__dict__)

    out_dir.mkdir(parents=True, exist_ok=True)
    index_path = out_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    return index_path
