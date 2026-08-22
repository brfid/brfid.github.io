"""Tests for the published vintage build-log renderer."""

from __future__ import annotations

from pathlib import Path

import pytest

from resume_generator.build_log import load_console_sections, main, render_build_log, render_build_log_files

ROOT = Path(__file__).resolve().parents[1]

SAMPLE_LOG = """\
[2026-08-19 12:00:00] prepare-host
[2026-08-19 12:00:01] generate-vintage-yaml
Wrote: build/vintage/bio.vintage.yaml (5 lines)
[2026-08-19 12:00:02] stage-b-vax
[vax_pexpect] 2026-08-19 12:00:03  Compiling: cc -O -o bradman /tmp/bradman.c
[uucp] Wrote spool: build/vintage/brad.bio.uu (6 lines)
[2026-08-19 12:00:04] stage-a-pdp11
[pdp11_pexpect] 2026-08-19 12:00:05  nroff complete
Wrote: build/vintage/brad.bio.txt (5 lines) <unsafe>
[2026-08-19 12:00:06] emit-artifact
"""


def test_render_build_log_combines_host_and_guest_records() -> None:
    rendered = render_build_log(
        log_text=SAMPLE_LOG,
        build_id="build-20260819-120000",
        sections={
            "vax-boot": "VAX boot <ok>",
            "vax-compile": "cc bradman.c",
            "vax-run": "bradman complete",
            "pdp11-boot": "PDP-11 boot",
            "pdp11-nroff": "nroff output",
        },
    )

    assert "<title>build-20260819-120000 — vintage pipeline log</title>" in rendered
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in rendered
    assert '<meta name="robots" content="noindex, nofollow, noarchive, nosnippet, noimageindex">' in rendered
    assert '<main id="build-log" aria-labelledby="log-title">' in rendered
    assert '<a href="/">Home</a>' in rendered
    assert ">Site source</a>" in rendered
    assert "2026-08-19 12:00:03" in rendered
    assert "VAX boot &lt;ok&gt;" in rendered
    assert "Wrote: build/vintage/brad.bio.txt (5 lines) &lt;unsafe&gt;" in rendered
    assert "nroff &rarr; brad.bio.txt" in rendered


def test_render_build_log_includes_responsive_and_keyboard_styles() -> None:
    rendered = render_build_log(log_text="", build_id="build-empty", sections={})

    assert "a:focus-visible" in rendered
    assert "summary:focus-visible" in rendered
    assert "@media (max-width: 620px)" in rendered
    assert "overflow-wrap: anywhere" in rendered
    assert "white-space: pre-wrap" in rendered


def test_render_build_log_marks_missing_console_sections() -> None:
    rendered = render_build_log(log_text="", build_id="build-empty", sections={})
    assert rendered.count("(no console output captured)") == 5
    assert rendered.count("(no events)") == 3


def test_load_console_sections_ignores_malformed_entries(tmp_path: Path) -> None:
    sections_path = tmp_path / "sections.jsonl"
    sections_path.write_text(
        "\n".join(
            [
                '{"section": "vax-boot", "content": "booted"}',
                "not json",
                '["not", "an", "object"]',
                '{"section": 123, "content": "ignored"}',
            ]
        ),
        encoding="utf-8",
    )

    assert load_console_sections(sections_path) == {"vax-boot": "booted"}
    assert load_console_sections(tmp_path / "missing.jsonl") == {}


def test_render_build_log_files_reads_inputs(tmp_path: Path) -> None:
    log_path = tmp_path / "pipeline.log"
    log_path.write_text(SAMPLE_LOG, encoding="utf-8")
    sections_path = tmp_path / "sections.jsonl"
    sections_path.write_text('{"section": "vax-boot", "content": "booted"}\n', encoding="utf-8")

    rendered = render_build_log_files(
        log_path=log_path,
        build_id="build-from-files",
        sections_path=sections_path,
    )

    assert "<title>build-from-files — vintage pipeline log</title>" in rendered
    assert "booted" in rendered


def test_main_renders_build_log_to_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log_path = tmp_path / "pipeline.log"
    log_path.write_text(SAMPLE_LOG, encoding="utf-8")

    result = main([str(log_path), "build-from-cli"])

    assert result == 0
    assert "<title>build-from-cli — vintage pipeline log</title>" in capsys.readouterr().out


def test_404_template_provides_semantic_recovery_routes() -> None:
    template = (ROOT / "hugo" / "layouts" / "404.html").read_text(encoding="utf-8")

    assert '<section class="error-page" aria-labelledby="not-found-title">' in template
    assert '<h1 id="not-found-title">Page not found</h1>' in template
    assert '<nav aria-label="Continue on this site">' in template
    assert ">Home</a>" in template
    assert ">Blog</a>" in template
    assert ">Resume</a>" in template
