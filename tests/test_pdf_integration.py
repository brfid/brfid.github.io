"""Exercise the private PDF boundary with a real local browser."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from site_tools.pdf import build_pdf
from site_tools.verify import verify_resume_artifacts
from tests.test_publication_contract import ROOT, render_site

pytestmark = pytest.mark.integration


def test_private_pdf_injection_stays_outside_the_public_site(tmp_path: Path) -> None:
    site_dir = render_site(tmp_path)
    public_pdf = site_dir / "resume.pdf"
    private_pdf = tmp_path / "local/application.pdf"
    overlay = tmp_path / "synthetic-private.yaml"
    phone = "415-555-0199"
    overlay.write_text(f'basics:\n  phone: "{phone}"\n', encoding="utf-8")

    build_pdf(site_dir=site_dir, resume_url_path="/resume/", pdf_path=public_pdf)
    build_pdf(site_dir=site_dir, resume_url_path="/resume/", pdf_path=private_pdf, private_resume_path=overlay)
    pdftotext = shutil.which("pdftotext")
    assert pdftotext is not None
    public_text = subprocess.run(  # noqa: S603 - inspect PDFs generated in this test.
        [pdftotext, str(public_pdf), "-"], capture_output=True, text=True, check=True
    ).stdout
    private_text = subprocess.run(  # noqa: S603 - inspect PDFs generated in this test.
        [pdftotext, str(private_pdf), "-"], capture_output=True, text=True, check=True
    ).stdout

    assert phone not in (site_dir / "resume/index.html").read_text(encoding="utf-8")
    assert phone not in public_text
    assert phone in private_text
    assert not private_pdf.is_relative_to(site_dir)
    assert verify_resume_artifacts(site_dir, resume_yaml=ROOT / "resume.yaml") == []
