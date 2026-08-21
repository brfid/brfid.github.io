"""Render the published HTML log for the vintage build pipeline."""

from __future__ import annotations

import argparse
import html
import json
import re
from collections.abc import Mapping
from pathlib import Path

_TIMESTAMP = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
_MISSING_CONSOLE_OUTPUT = "<em>(no console output captured)</em>"

_CSS = """
* { box-sizing: border-box; }
body { font-family: ui-monospace, SFMono-Regular, Menlo, 'Courier New', monospace;
       font-size: 12px; background: #0d1117; color: #e6edf3;
       margin: 0; padding: 20px 24px; line-height: 1.6; }
h1 { font-size: 13px; color: #8b949e; font-weight: normal; margin: 0 0 20px; }
h1 a { color: #58a6ff; text-decoration: none; }
h1 a:hover { text-decoration: underline; }
details { margin: 0 0 4px; border: 1px solid #30363d; border-radius: 6px; overflow: hidden; }
summary { padding: 8px 14px; background: #161b22; cursor: pointer;
          list-style: none; display: flex; align-items: baseline; gap: 10px;
          user-select: none; }
summary::-webkit-details-marker { display: none; }
.arrow { color: #58a6ff; font-size: 10px; width: 10px; flex-shrink: 0; }
details:not([open]) .arrow::after { content: "▶"; }
details[open] .arrow::after { content: "▼"; }
.step-name { color: #e6edf3; font-weight: bold; }
.step-meta { color: #8b949e; flex: 1; }
.step-ts   { color: #6e7681; font-size: 11px; }
pre { margin: 0; padding: 12px 16px; overflow-x: auto;
      white-space: pre-wrap; word-break: break-all;
      background: #0d1117; color: #c9d1d9;
      border-top: 1px solid #30363d; font-size: 11.5px; line-height: 1.55; }
.ts   { color: #6e7681; }
.ok   { color: #3fb950; }
.info { color: #58a6ff; }
em { color: #6e7681; font-style: normal; }
"""


def load_console_sections(path: Path | None) -> dict[str, str]:
    """Load named console sections from a JSON Lines file.

    Malformed and incomplete entries are ignored so a partial diagnostic file
    does not prevent the rest of the build log from rendering.

    Args:
        path: JSON Lines file emitted by the pexpect stages, or ``None``.

    Returns:
        Mapping from section identifier to captured console text.
    """
    if path is None or not path.is_file():
        return {}

    sections: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        section = entry.get("section")
        content = entry.get("content")
        if isinstance(section, str) and isinstance(content, str):
            sections[section] = content
    return sections


def _find_timestamp(log_lines: list[str], pattern: str) -> str:
    for line in log_lines:
        match = re.search(pattern, line)
        if match:
            return match.group(1)
    return ""


def _find_line(log_lines: list[str], pattern: str) -> str:
    for line in log_lines:
        if re.search(pattern, line):
            return line.strip()
    return ""


def _console_section(sections: Mapping[str, str], name: str) -> str:
    raw = sections.get(name, "").strip()
    return html.escape(raw) if raw else _MISSING_CONSOLE_OUTPUT


def _timestamp_span(timestamp: str) -> str:
    return f'<span class="ts">{html.escape(timestamp)}</span>' if timestamp else ""


def _details(
    title: str,
    meta: str,
    timestamp: str,
    content_html: str,
    *,
    open_by_default: bool = False,
) -> str:
    open_attribute = " open" if open_by_default else ""
    timestamp_html = f' <span class="step-ts">{html.escape(timestamp)}</span>' if timestamp else ""
    return (
        f"<details{open_attribute}>\n"
        '  <summary><span class="arrow"></span>'
        f'<span class="step-name">{title}</span>'
        f'<span class="step-meta">{meta}</span>{timestamp_html}</summary>\n'
        f"  <pre>{content_html}</pre>\n"
        "</details>"
    )


def render_build_log(*, log_text: str, build_id: str, sections: Mapping[str, str]) -> str:
    """Render a complete HTML build log from host and guest console records.

    Args:
        log_text: Full host-side vintage runner log.
        build_id: Public identifier for this build.
        sections: Named VAX/PDP-11 console sections captured by pexpect.

    Returns:
        Standalone HTML document suitable for ``hugo/static/build.log.html``.
    """
    log_lines = log_text.splitlines()

    host_timestamp = _find_timestamp(log_lines, rf"\[({_TIMESTAMP})\] prepare-host")
    yaml_timestamp = _find_timestamp(log_lines, rf"\[({_TIMESTAMP})\] generate-vintage-yaml")
    vax_timestamp = _find_timestamp(log_lines, rf"\[({_TIMESTAMP})\] stage-b-vax")
    pdp11_timestamp = _find_timestamp(log_lines, rf"\[({_TIMESTAMP})\] stage-a-pdp11")
    artifact_timestamp = _find_timestamp(log_lines, rf"\[({_TIMESTAMP})\] emit-artifact")
    compile_timestamp = _find_timestamp(log_lines, rf"\[vax_pexpect\] ({_TIMESTAMP})\s+Compiling:")
    nroff_timestamp = _find_timestamp(log_lines, rf"\[pdp11_pexpect\] ({_TIMESTAMP})\s+nroff complete")

    yaml_line = _find_line(log_lines, r"Wrote: build/vintage/bio")
    spool_line = _find_line(log_lines, r"\[uucp\] Wrote spool:")
    bio_txt_line = _find_line(log_lines, r"Wrote:.*brad\.bio\.txt")

    host_lines: list[str] = []
    if host_timestamp:
        host_lines.append(f'{_timestamp_span(host_timestamp)}  <span class="ok">pipeline started</span>')
    if yaml_timestamp:
        host_lines.append(f"{_timestamp_span(yaml_timestamp)}  site.yaml → bio.vintage.yaml")
    if yaml_line:
        host_lines.append(f"  {html.escape(yaml_line)}")
    host_content = "\n".join(host_lines) if host_lines else "<em>(no events)</em>"

    routing_lines: list[str] = []
    if pdp11_timestamp:
        routing_lines.append(f"{_timestamp_span(pdp11_timestamp)}  routing brad.bio.uu → PDP-11")
    if spool_line:
        routing_lines.append(f"  {html.escape(spool_line)}")
    routing_content = "\n".join(routing_lines) if routing_lines else "<em>(no events)</em>"

    artifact_lines: list[str] = []
    if artifact_timestamp:
        artifact_lines.append(f'{_timestamp_span(artifact_timestamp)}  <span class="ok">pipeline complete</span>')
    if bio_txt_line:
        artifact_lines.append(f"  {html.escape(bio_txt_line)}")
    artifact_content = "\n".join(artifact_lines) if artifact_lines else "<em>(no events)</em>"

    escaped_build_id = html.escape(build_id)
    heading = (
        "vintage pipeline &middot; "
        '<a href="https://github.com/brfid/brfid.github.io">brfid/brfid.github.io</a>'
        f" &middot; {escaped_build_id}"
    )
    parts = [
        f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8">
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet, noimageindex">
<title>{escaped_build_id} — vintage pipeline log</title>
<style>{_CSS}</style>
</head>
<body>
<h1>{heading}</h1>
"""
    ]
    parts.append(_details("host", "pipeline setup", host_timestamp, host_content, open_by_default=True))
    parts.append(
        _details("VAX 4.3BSD", "SIMH vax780 &middot; boot", vax_timestamp, _console_section(sections, "vax-boot"))
    )
    parts.append(
        _details(
            "VAX 4.3BSD",
            "compile bradman.c &rarr; brad.bio.roff &rarr; uuencode",
            compile_timestamp,
            _console_section(sections, "vax-compile") + "\n\n" + _console_section(sections, "vax-run"),
            open_by_default=True,
        )
    )
    parts.append(_details("host", "UUCP routing brad.bio.uu &rarr; PDP-11", pdp11_timestamp, routing_content))
    parts.append(
        _details(
            "PDP-11 2.11BSD",
            "SIMH pdp11 &middot; boot",
            pdp11_timestamp,
            _console_section(sections, "pdp11-boot"),
        )
    )
    parts.append(
        _details(
            "PDP-11 2.11BSD",
            "nroff &rarr; brad.bio.txt",
            nroff_timestamp,
            _console_section(sections, "pdp11-nroff"),
            open_by_default=True,
        )
    )
    parts.append(_details("host", "artifact extraction", artifact_timestamp, artifact_content, open_by_default=True))
    parts.append("</body>\n</html>\n")
    return "".join(parts)


def render_build_log_files(*, log_path: Path, build_id: str, sections_path: Path | None = None) -> str:
    """Read build records from disk and render the published HTML log."""
    return render_build_log(
        log_text=log_path.read_text(encoding="utf-8"),
        build_id=build_id,
        sections=load_console_sections(sections_path),
    )


def main(argv: list[str] | None = None) -> int:
    """Render a build log to stdout for the shell pipeline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log_path", type=Path, help="Host-side vintage pipeline log")
    parser.add_argument("build_id", help="Public build identifier")
    parser.add_argument("sections_path", nargs="?", type=Path, help="Optional pexpect console JSON Lines file")
    args = parser.parse_args(argv)

    print(
        render_build_log_files(
            log_path=args.log_path,
            build_id=args.build_id,
            sections_path=args.sections_path,
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
