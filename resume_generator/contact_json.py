"""Generate simplified contact.json for VAX HTML fragment rendering."""

from __future__ import annotations

import json
from pathlib import Path

from .resume_fields import get_profile_url
from .types import Resume


def generate_contact_json(*, resume: Resume, out_path: Path) -> None:
    """Generate simplified contact.json from resume data.

    This JSON format is designed to be parseable by the VAX C program (bradman.c)
    for generating HTML fragments.

    Args:
        resume: Raw JSON Resume dict.
        out_path: Output path for contact.json.
    """
    basics = resume.get("basics") or {}

    contact_data = {
        "name": str(basics.get("name") or "").strip(),
        "label": str(basics.get("label") or "").strip(),
        "email": str(basics.get("email") or "").strip(),
        "github": get_profile_url(basics, "GitHub") or "",
        "linkedin": get_profile_url(basics, "LinkedIn") or "",
    }

    # Write with minimal formatting for easier C parsing
    out_path.write_text(
        json.dumps(contact_data, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
