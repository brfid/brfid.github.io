"""Tests for resume_generator.bio_yaml."""

from __future__ import annotations

import pathlib

import yaml as _yaml

from resume_generator.bio_yaml import (
    BioData,
    _read_build_id,
    bio_to_yaml,
    main,
    parse_bio_txt,
)

# Representative nroff output: name, headline, blank line, then prose that
# nroff filled and justified to a fixed measure. The double spaces and hard
# line breaks are justification/fill artifacts (the pipeline runs `.nh`, so
# there are no mid-word hyphen breaks); parse_bio_txt collapses them to prose.
SAMPLE_BIO = """\
Bradley Fidler
Principal Technical Writer

I  run  technical documentation at a mid-sized B2B cybersecurity
company.  Before this, I wrote lessons learned analyses of
distributed systems, and taught technology history in college.
"""


def test_parse_basic_fields() -> None:
    data = parse_bio_txt(SAMPLE_BIO)
    assert data["name"] == "Bradley Fidler"
    assert data["principal_headline"] == "Principal Technical Writer"
    # The prose is reflowed: fill line breaks and justification double-spaces
    # are collapsed back to a single flowing, single-spaced sentence.
    assert data["about"].startswith("I run technical documentation")
    assert "\n" not in data["about"]
    assert "  " not in data["about"]
    assert "company. Before this" in data["about"]
    assert data["about"].endswith("technology history in college.")


def test_parse_about_reflows_multiple_paragraphs() -> None:
    text = (
        "Bradley Fidler\n"
        "Principal Technical Writer\n"
        "\n"
        "First  paragraph  wrapped\n"
        "across two lines.\n"
        "\n"
        "Second  paragraph  also\n"
        "wrapped across lines.\n"
    )
    data = parse_bio_txt(text)
    # Each paragraph collapses to one line; a blank line separates them.
    assert data["about"] == ("First paragraph wrapped across two lines.\n\nSecond paragraph also wrapped across lines.")


def test_parse_headline_only() -> None:
    text = "Only Name\nOnly Headline\n"
    data = parse_bio_txt(text)
    assert data["name"] == "Only Name"
    assert data["principal_headline"] == "Only Headline"
    assert data["about"] == ""


def test_parse_name_only() -> None:
    data = parse_bio_txt("Only Name\n")
    assert data["name"] == "Only Name"
    assert data["principal_headline"] == ""
    assert data["about"] == ""


def test_parse_empty() -> None:
    data = parse_bio_txt("")
    assert data["name"] == ""
    assert data["principal_headline"] == ""
    assert data["about"] == ""


def test_bio_to_yaml_no_build_log() -> None:
    data: BioData = {
        "name": "Jane Doe",
        "principal_headline": "Principal Technical Writer",
        "about": "Profile statement.",
    }
    out = bio_to_yaml(data)
    assert "build_log" not in out
    assert "build_id" not in out
    assert "build_run_url" not in out
    assert '"Jane Doe"' in out
    assert "principal_headline:" in out
    assert "about:" in out


def test_bio_to_yaml_with_build_log() -> None:
    data: BioData = {
        "name": "Jane Doe",
        "principal_headline": "Writer",
        "about": "Profile statement.",
        "build_log": True,
        "build_id": "build-20260301-120000",
        "build_run_url": "https://github.com/example/site/actions/runs/123456",
    }
    out = bio_to_yaml(data)
    assert "build_log: true" in out
    assert '"build-20260301-120000"' in out
    assert 'build_run_url: "https://github.com/example/site/actions/runs/123456"' in out


def test_bio_to_yaml_special_chars() -> None:
    data: BioData = {
        "name": 'Name "Quoted"',
        "principal_headline": "Headline",
        "about": "Sum",
    }
    out = bio_to_yaml(data)
    # json.dumps escapes double quotes; the result must remain valid YAML.
    assert _yaml.safe_load(out)["name"] == 'Name "Quoted"'


def test_bio_to_yaml_about_round_trips_through_yaml() -> None:
    """The reflowed prose must survive serialisation unchanged."""
    data = parse_bio_txt(SAMPLE_BIO)
    out = bio_to_yaml(data)
    parsed = _yaml.safe_load(out)
    assert parsed["about"] == data["about"]
    assert "I run technical" in parsed["about"]


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

    rc = main(
        [
            str(src),
            str(dst),
            str(build_log),
            "https://github.com/example/site/actions/runs/123456",
        ]
    )

    assert rc == 0
    assert dst.exists()
    content = dst.read_text(encoding="utf-8")
    assert "Bradley Fidler" in content
    assert "build_log: true" in content
    assert "build-test-123" in content
    assert "https://github.com/example/site/actions/runs/123456" in content


def test_main_omits_build_log_metadata_when_log_is_missing(tmp_path: pathlib.Path) -> None:
    src = tmp_path / "brad.bio.txt"
    src.write_text(SAMPLE_BIO, encoding="utf-8")
    dst = tmp_path / "bio.yaml"

    rc = main(
        [
            str(src),
            str(dst),
            str(tmp_path / "missing-build.log.html"),
            "https://github.com/example/site/actions/runs/123456",
        ]
    )

    assert rc == 0
    content = dst.read_text(encoding="utf-8")
    assert "build_log:" not in content
    assert "build_id:" not in content
    assert 'build_run_url: "https://github.com/example/site/actions/runs/123456"' in content


def test_main_missing_src(tmp_path: pathlib.Path) -> None:
    dst = tmp_path / "bio.yaml"
    rc = main([str(tmp_path / "missing.txt"), str(dst)])
    assert rc == 0
    assert not dst.exists()


def test_main_no_args() -> None:
    rc = main([])
    assert rc == 1
