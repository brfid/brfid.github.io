"""Tests for the vintage source and rendered-artifact contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from resume_generator.vintage_contract import (
    VintageBioInput,
    VintageContractError,
    main,
    validate_rendered_bio,
    vintage_input_from_mappings,
)

EXPECTED = VintageBioInput(
    name="Bradley Fidler",
    headline="Principal Technical Writer | Documentation Platforms",
    summary="First sentence. Second sentence.",
)

RENDERED = """\
Bradley Fidler
Principal Technical Writer | Documentation Platforms

First  sentence. Second
sentence.
"""


def test_rendered_bio_matches_sources_after_nroff_spacing() -> None:
    data = validate_rendered_bio(RENDERED, EXPECTED)
    assert data["about"] == "First sentence. Second sentence."


@pytest.mark.parametrize("text", ["", "Only a name\n", "Name\nHeadline\n"])
def test_rendered_bio_requires_complete_shape(text: str) -> None:
    with pytest.raises(VintageContractError, match="missing|required"):
        validate_rendered_bio(text, EXPECTED)


def test_rendered_bio_reports_semantic_mismatch() -> None:
    with pytest.raises(VintageContractError, match="headline"):
        validate_rendered_bio(RENDERED.replace("Documentation Platforms", "Wrong"), EXPECTED)


@pytest.mark.parametrize(
    ("site", "resume", "message"),
    [
        ({"name": "N", "headline": "H"}, {}, "basics"),
        ({"name": "N", "headline": "H"}, {"basics": {"summary": ""}}, "non-empty"),
        ({"name": "N", "headline": "H"}, {"basics": {"summary": "curly ’ quote"}}, "ASCII"),
        ({"name": "N", "headline": "H"}, {"basics": {"summary": "two\nlines"}}, "single printable"),
    ],
)
def test_vintage_input_contract_rejects_invalid_sources(
    site: dict[str, str], resume: dict[str, object], message: str
) -> None:
    with pytest.raises(VintageContractError, match=message):
        vintage_input_from_mappings(site, resume)


def test_cli_validates_public_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bio = tmp_path / "brad.bio.txt"
    bio.write_text(RENDERED, encoding="utf-8")
    site = tmp_path / "site.yaml"
    site.write_text(
        'name: "Bradley Fidler"\nheadline: "Principal Technical Writer | Documentation Platforms"\n',
        encoding="utf-8",
    )
    resume = tmp_path / "resume.yaml"
    resume.write_text('basics:\n  summary: "First sentence. Second sentence."\n', encoding="utf-8")

    assert main([str(bio), str(site), str(resume)]) == 0
    assert "matches" in capsys.readouterr().out


def test_cli_fails_closed_on_missing_bio(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    site = tmp_path / "site.yaml"
    site.write_text('name: "N"\nheadline: "H"\n', encoding="utf-8")
    resume = tmp_path / "resume.yaml"
    resume.write_text('basics:\n  summary: "S"\n', encoding="utf-8")

    assert main([str(tmp_path / "missing.txt"), str(site), str(resume)]) == 1
    assert "No such file" in capsys.readouterr().err
