"""Tests for resume_generator.bio_yaml."""

from __future__ import annotations

import pathlib

from resume_generator.bio_yaml import (
    BioData,
    _read_about_from_resume_yaml,
    _read_build_id,
    bio_to_yaml,
    main,
    parse_bio_txt,
)

SAMPLE_BIO = """\
Bradley Fidler
Principal Technical Writer -- API documentation, platform engineering, AI workflows
I lead principal-level documentation systems for platform teams.

- Built docs CI quality gates adopted across engineering.
- Reduced API onboarding time with executable reference patterns.

I build documentation platforms and the tooling that powers them.

brfid@icloud.com
https://brfid.github.io
https://www.linkedin.com/in/brfid/
"""


def test_parse_basic_fields() -> None:
    data = parse_bio_txt(SAMPLE_BIO)
    assert data["name"] == "Bradley Fidler"
    assert (
        data["label"]
        == "Principal Technical Writer -- API documentation, platform engineering, AI workflows"
    )
    assert data["principal_headline"] == "I lead principal-level documentation systems for platform teams."
    assert data["impact_highlights"] == [
        "Built docs CI quality gates adopted across engineering.",
        "Reduced API onboarding time with executable reference patterns.",
    ]
    assert data["summary"] == "I build documentation platforms and the tooling that powers them."
    assert data["email"] == "brfid@icloud.com"
    assert data["url"] == "https://brfid.github.io"
    assert data["linkedin"] == "https://www.linkedin.com/in/brfid/"


def test_parse_missing_contact() -> None:
    # No blank between label and summary; no contact block.
    text = "Name\nLabel\nSummary line.\n"
    data = parse_bio_txt(text)
    assert data["principal_headline"] == ""
    assert data["impact_highlights"] == []
    assert data["summary"] == "Summary line."
    assert data["email"] == ""
    assert data["url"] == ""
    assert data["linkedin"] == ""


def test_parse_no_blank_line() -> None:
    text = "Name\nLabel\nSummary without blank."
    data = parse_bio_txt(text)
    assert data["summary"] == "Summary without blank."


def test_parse_legacy_bio_format_back_compatible() -> None:
    legacy = """\
Name
Label
Legacy summary line.

test@example.com
https://example.com
https://linkedin.com/in/example
"""
    data = parse_bio_txt(legacy)
    assert data["principal_headline"] == ""
    assert data["impact_highlights"] == []
    assert data["summary"] == "Legacy summary line."
    assert data["email"] == "test@example.com"


def test_bio_to_yaml_no_build_log() -> None:
    data: BioData = {
        "name": "Jane Doe",
        "label": "Writer",
        "principal_headline": "Principal headline",
        "impact_highlights": ["A", "B"],
        "summary": "Summary.",
        "email": "jane@example.com",
        "url": "https://example.com",
        "linkedin": "https://linkedin.com/in/jane",
    }
    yaml = bio_to_yaml(data)
    assert "build_log" not in yaml
    assert "build_id" not in yaml
    assert '"Jane Doe"' in yaml
    assert "principal_headline:" in yaml
    assert "impact_highlights:" in yaml


def test_bio_to_yaml_with_build_log() -> None:
    data: BioData = {
        "name": "Jane Doe",
        "label": "Writer",
        "summary": "Summary.",
        "email": "",
        "url": "",
        "linkedin": "",
        "build_log": True,
        "build_id": "build-20260301-120000",
    }
    yaml = bio_to_yaml(data)
    assert "build_log: true" in yaml
    assert '"build-20260301-120000"' in yaml


def test_bio_to_yaml_special_chars() -> None:
    data: BioData = {
        "name": 'Name "Quoted"',
        "label": "Label",
        "summary": "Sum",
        "email": "",
        "url": "",
        "linkedin": "",
    }
    yaml = bio_to_yaml(data)
    # json.dumps escapes double quotes; result must be valid YAML
    assert "Name" in yaml
    assert "Quoted" in yaml


def test_read_build_id_present(tmp_path: pathlib.Path) -> None:
    log = tmp_path / "build.log.html"
    log.write_text("<title>build-20260301-120000 — vintage pipeline log</title>\n")
    assert _read_build_id(log) == "build-20260301-120000"


def test_read_build_id_missing(tmp_path: pathlib.Path) -> None:
    assert _read_build_id(tmp_path / "nonexistent.html") == ""


def test_main_writes_yaml(tmp_path: pathlib.Path) -> None:
    src = tmp_path / "brad.bio.txt"
    src.write_text(SAMPLE_BIO, encoding="utf-8")
    dst = tmp_path / "bio.yaml"
    build_log = tmp_path / "build.log.html"
    build_log.write_text("<title>build-test-123 — vintage pipeline log</title>\n")

    rc = main([str(src), str(dst), str(build_log)])

    assert rc == 0
    assert dst.exists()
    content = dst.read_text(encoding="utf-8")
    assert "Bradley Fidler" in content
    assert "build_log: true" in content
    assert "build-test-123" in content


def test_main_missing_src(tmp_path: pathlib.Path) -> None:
    dst = tmp_path / "bio.yaml"
    rc = main([str(tmp_path / "missing.txt"), str(dst)])
    assert rc == 0
    assert not dst.exists()


def test_main_no_args() -> None:
    rc = main([])
    assert rc == 1


# --- about field ---


def test_read_about_from_resume_yaml_present(tmp_path: pathlib.Path) -> None:
    resume = tmp_path / "resume.yaml"
    resume.write_text(
        'tagline: "T"\nabout: >-\n  Most of my career has been about structure.\n'
        "basics:\n  name: X\n"
    )
    assert _read_about_from_resume_yaml(str(resume)) == "Most of my career has been about structure."


def test_read_about_from_resume_yaml_absent(tmp_path: pathlib.Path) -> None:
    resume = tmp_path / "resume.yaml"
    resume.write_text('tagline: "T"\nbasics:\n  name: X\n')
    assert _read_about_from_resume_yaml(str(resume)) == ""


def test_bio_to_yaml_with_about() -> None:
    data: BioData = {
        "name": "Jane Doe",
        "label": "Writer",
        "summary": "Summary.",
        "about": "About paragraph.",
        "email": "",
        "url": "",
        "linkedin": "",
    }
    out = bio_to_yaml(data)
    assert "about:" in out
    assert "About paragraph." in out


def test_bio_to_yaml_multiline_about_preserves_paragraphs() -> None:
    about = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    data: BioData = {
        "name": "Jane Doe",
        "label": "Writer",
        "summary": "Summary.",
        "about": about,
        "email": "",
        "url": "",
        "linkedin": "",
    }
    out = bio_to_yaml(data)
    # json.dumps encodes \n as \\n; round-tripping through yaml.safe_load must
    # recover the original multi-paragraph string.
    import yaml as _yaml  # local import to keep test dependency explicit
    parsed = _yaml.safe_load(out)
    assert parsed["about"] == about


def test_bio_to_yaml_no_about() -> None:
    data: BioData = {
        "name": "Jane",
        "label": "L",
        "summary": "S",
        "email": "",
        "url": "",
        "linkedin": "",
    }
    assert "about" not in bio_to_yaml(data)


def test_main_reads_about_from_resume_yaml(tmp_path: pathlib.Path) -> None:
    src = tmp_path / "brad.bio.txt"
    src.write_text(SAMPLE_BIO, encoding="utf-8")
    dst = tmp_path / "bio.yaml"
    resume = tmp_path / "resume.yaml"
    resume.write_text('tagline: "T"\nabout: >-\n  About from resume.\n')

    rc = main([str(src), str(dst), str(tmp_path / "nonexistent.html"), str(resume)])

    assert rc == 0
    content = dst.read_text(encoding="utf-8")
    assert "About from resume." in content
    assert "Bradley Fidler" in content


def test_main_no_resume_yaml_no_about(tmp_path: pathlib.Path) -> None:
    src = tmp_path / "brad.bio.txt"
    src.write_text(SAMPLE_BIO, encoding="utf-8")
    dst = tmp_path / "bio.yaml"
    # Pass a nonexistent resume.yaml — no about, no crash.
    rc = main([str(src), str(dst), str(tmp_path / "nonexistent.html"), str(tmp_path / "no-resume.yaml")])
    assert rc == 0
    assert "about" not in dst.read_text(encoding="utf-8")


def test_read_about_from_resume_yaml_literal_block(tmp_path: pathlib.Path) -> None:
    # Regression: |- was returned as the literal string "|-" before the fix.
    resume = tmp_path / "resume.yaml"
    resume.write_text(
        'tagline: "T"\nabout: |-\n  Literal block scalar content.\nbasics:\n  name: X\n'
    )
    assert _read_about_from_resume_yaml(str(resume)) == "Literal block scalar content."


def test_read_about_from_resume_yaml_literal_block_multiline(tmp_path: pathlib.Path) -> None:
    resume = tmp_path / "resume.yaml"
    resume.write_text(
        "tagline: T\nabout: |-\n  First paragraph.\n\n  Second paragraph.\nbasics:\n  name: X\n"
    )
    result = _read_about_from_resume_yaml(str(resume))
    assert "First paragraph." in result
    assert "Second paragraph." in result
    assert "\n\n" in result
