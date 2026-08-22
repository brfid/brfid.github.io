"""Tests for resume_generator.bio_yaml."""

from __future__ import annotations

import pathlib

import pytest
import yaml as _yaml

from resume_generator.bio_yaml import (
    BioData,
    _read_successful_build_id,
    bio_to_yaml,
    main,
    parse_bio_txt,
    require_complete_bio,
)

# Nroff-filled input with justification spacing and hard line breaks.
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
    assert _yaml.safe_load(out)["name"] == 'Name "Quoted"'


def test_bio_to_yaml_about_round_trips_through_yaml() -> None:
    """The reflowed prose must survive serialization unchanged."""
    data = parse_bio_txt(SAMPLE_BIO)
    out = bio_to_yaml(data)
    parsed = _yaml.safe_load(out)
    assert parsed["about"] == data["about"]
    assert "I run technical" in parsed["about"]


def test_require_complete_bio_rejects_incomplete_shape() -> None:
    with pytest.raises(ValueError, match="headline, about"):
        require_complete_bio(BioData(name="Only Name"))


def test_read_build_id_from_success_status(tmp_path: pathlib.Path) -> None:
    status = tmp_path / "pipeline-status.json"
    status.write_text(
        '{"build_id": "build-20260301-120000", "result": "success", "exit_code": 0}\n',
        encoding="utf-8",
    )
    assert _read_successful_build_id(status) == "build-20260301-120000"


def test_read_build_id_rejects_failure_status(tmp_path: pathlib.Path) -> None:
    status = tmp_path / "pipeline-status.json"
    status.write_text('{"build_id": "build-failed", "result": "failure", "exit_code": 1}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="successful"):
        _read_successful_build_id(status)


def test_main_writes_yaml(tmp_path: pathlib.Path) -> None:
    src = tmp_path / "brad.bio.txt"
    src.write_text(SAMPLE_BIO, encoding="utf-8")
    dst = tmp_path / "bio.yaml"
    build_log = tmp_path / "build.log.html"
    build_log.write_text("<title>presentation wording is not metadata</title>\n")
    status = tmp_path / "pipeline-status.json"
    status.write_text('{"build_id": "build-test-123", "result": "success", "exit_code": 0}\n', encoding="utf-8")

    rc = main(
        [
            str(src),
            str(dst),
            "--build-log",
            str(build_log),
            "--pipeline-status",
            str(status),
            "--build-run-url",
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
            "--build-log",
            str(tmp_path / "missing-build.log.html"),
            "--build-run-url",
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
    assert rc == 1
    assert not dst.exists()


def test_main_rejects_incomplete_bio(tmp_path: pathlib.Path) -> None:
    src = tmp_path / "brad.bio.txt"
    src.write_text("Only Name\n", encoding="utf-8")
    dst = tmp_path / "bio.yaml"

    assert main([str(src), str(dst)]) == 1
    assert not dst.exists()


def test_main_no_args() -> None:
    rc = main([])
    assert rc == 1
