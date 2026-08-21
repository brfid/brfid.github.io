from __future__ import annotations

from datetime import date

from resume_generator.vintage_yaml import build_vintage_bio, emit_vintage_yaml


def test_emit_bio_uses_quoting_and_two_space_indent() -> None:
    site = {"name": "Test User", "headline": 'Principal "Docs" \\ Writer'}
    resume = {"basics": {"summary": "First line.\nSecond line.\tThird line."}}

    built = build_vintage_bio(site, resume, build_date=date(2026, 1, 25))
    text = emit_vintage_yaml(built)

    assert "\t" not in text
    assert "\r" not in text
    assert "schemaVersion: v1" in text
    assert "buildDate: 2026-01-25" in text
    # Simple strings are unquoted.
    assert "bioName: Test User" in text
    # Strings with special characters are quoted and escaped.
    assert 'bioHeadline: "Principal \\"Docs\\" \\\\ Writer"' in text
    # Newlines/tabs in the summary flatten to single spaces.
    assert "bioProfile: First line. Second line. Third line." in text


def test_emit_bio_is_ascii_clean() -> None:
    """Unicode in source data must be transliterated; output must be ASCII-only."""
    site = {"name": "Test User", "headline": "Principal Technical Writer"}
    # em dash, curly quotes — common when copy-pasting from Word.
    resume = {"basics": {"summary": "Runs docs—loves it. “Great” results."}}

    built = build_vintage_bio(site, resume, build_date=date(2026, 1, 1))
    text = emit_vintage_yaml(built)

    assert text.isascii()
    assert "--" in text  # em dash → --
    assert "Great" in text  # curly quotes → straight


def test_bio_preserves_intentional_inline_spaces() -> None:
    """The summary should survive the vintage round trip byte for byte."""
    resume = {"basics": {"summary": "First sentence.  Second sentence."}}

    built = build_vintage_bio({}, resume, build_date=date(2026, 1, 25))

    assert "bioProfile: First sentence.  Second sentence." in emit_vintage_yaml(built)


def test_bio_maps_identity_from_site_and_text_from_resume() -> None:
    """Identity comes from site.yaml; bio text comes from basics.summary."""
    site = {"name": "Public Name", "headline": "Public headline"}
    resume = {"basics": {"summary": "Public shared summary."}}

    built = build_vintage_bio(site, resume, build_date=date(2026, 1, 25))

    assert built["bioName"] == "Public Name"
    assert built["bioHeadline"] == "Public headline"
    assert built["bioProfile"] == "Public shared summary."

    text = emit_vintage_yaml(built)
    assert "bioName: Public Name" in text
    assert "bioHeadline: Public headline" in text
    assert "bioProfile: Public shared summary." in text


def test_bio_omits_absent_fields() -> None:
    """Missing fields are omitted rather than emitted empty."""
    built = build_vintage_bio({"name": "Only Name"}, {}, build_date=date(2026, 1, 25))

    assert built["bioName"] == "Only Name"
    assert "bioHeadline" not in built
    assert "bioProfile" not in built

    text = emit_vintage_yaml(built)
    assert "bioHeadline" not in text
    assert "bioProfile" not in text


def test_bio_has_no_resume_document_fields() -> None:
    """The bio pipeline must carry only bio fields even if handed a full resume."""
    site = {"name": "N", "headline": "H"}
    resume = {
        "basics": {"summary": "B", "email": "person@example.com"},
        "work": [{"name": "Co"}],
        "skills": [{"name": "S"}],
    }

    text = emit_vintage_yaml(build_vintage_bio(site, resume, build_date=date(2026, 1, 25)))

    for resume_key in ("work:", "skills:", "contact:", "summary:", "impactHighlights:", "basics:"):
        assert resume_key not in text
    assert "bioProfile: B" in text
