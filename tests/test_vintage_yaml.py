from __future__ import annotations

from datetime import date

import pytest

from resume_generator.vintage_contract import VintageContractError
from resume_generator.vintage_yaml import build_vintage_bio, emit_vintage_yaml


def test_emit_bio_uses_fixed_quoted_scalar_contract() -> None:
    site = {"name": "Test User", "headline": 'Principal "Docs" \\ Writer'}
    resume = {"basics": {"summary": "One public summary."}}

    built = build_vintage_bio(site, resume, build_date=date(2026, 1, 25))
    text = emit_vintage_yaml(built)

    assert "\t" not in text
    assert "\r" not in text
    assert text.splitlines() == [
        'schemaVersion: "v1"',
        'buildDate: "2026-01-25"',
        'bioName: "Test User"',
        'bioHeadline: "Principal \\"Docs\\" \\\\ Writer"',
        'bioProfile: "One public summary."',
    ]
    assert 'bioHeadline: "Principal \\"Docs\\" \\\\ Writer"' in text


def test_build_bio_rejects_non_ascii_public_input() -> None:
    """Shared public copy must not silently diverge through transliteration."""
    site = {"name": "Test User", "headline": "Principal Technical Writer"}
    resume = {"basics": {"summary": "Runs docs—loves it. “Great” results."}}

    with pytest.raises(VintageContractError, match="ASCII"):
        build_vintage_bio(site, resume, build_date=date(2026, 1, 1))


def test_build_bio_rejects_multiline_public_input() -> None:
    """The guest contract is one printable line per scalar."""
    site = {"name": "Test User", "headline": "Principal Technical Writer"}
    resume = {"basics": {"summary": "First sentence.\nSecond sentence."}}

    with pytest.raises(VintageContractError, match="single printable line"):
        build_vintage_bio(site, resume, build_date=date(2026, 1, 25))


def test_bio_maps_identity_from_site_and_text_from_resume() -> None:
    """Identity comes from site.yaml; bio text comes from basics.summary."""
    site = {"name": "Public Name", "headline": "Public headline"}
    resume = {"basics": {"summary": "Public shared summary."}}

    built = build_vintage_bio(site, resume, build_date=date(2026, 1, 25))

    assert built["bioName"] == "Public Name"
    assert built["bioHeadline"] == "Public headline"
    assert built["bioProfile"] == "Public shared summary."

    text = emit_vintage_yaml(built)
    assert 'bioName: "Public Name"' in text
    assert 'bioHeadline: "Public headline"' in text
    assert 'bioProfile: "Public shared summary."' in text


def test_bio_rejects_absent_fields() -> None:
    """Every field needed for a truthful published bio is required."""
    with pytest.raises(VintageContractError, match="basics"):
        build_vintage_bio({"name": "Only Name"}, {}, build_date=date(2026, 1, 25))


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
    assert 'bioProfile: "B"' in text


def test_emitter_rejects_keys_outside_fixed_contract() -> None:
    with pytest.raises(ValueError, match="keys do not match"):
        emit_vintage_yaml({"schemaVersion": "v1", "extra": "unused"})
