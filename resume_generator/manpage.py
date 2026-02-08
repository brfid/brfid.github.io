"""Convert a small subset of man(7) roff into publishable text.

This is intentionally narrow: it targets the deterministic roff emitted by
`vax/bradman.c` (NAME/DESCRIPTION/CONTACT) so the host can render a stable
`site/brad.man.txt` without depending on `groff`, `mandoc`, or a VAX-side
`nroff` installation.
"""

from __future__ import annotations

import argparse
import textwrap
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BradManSummary:
    """Minimal brad(1) summary used on the landing page."""

    name_line: str
    description: str
    contact_lines: tuple[str, ...]


def _unescape_roff_text(value: str) -> str:
    # The VAX generator uses `\&` to prevent leading '.'/' from being treated as a macro.
    if value.startswith("\\&"):
        value = value[2:]

    # Common roff escapes used by `vax/bradman.c`.
    value = value.replace("\\\\-", "-")
    value = value.replace("\\-", "-")
    value = value.replace("\\\\(bu", "•")
    value = value.replace("\\(bu", "•")

    # The generator doubles literal backslashes in data.
    value = value.replace("\\\\", "\\")
    return value


def parse_brad_roff_summary(roff: str) -> BradManSummary:
    """Parse the minimal summary from a `brad.1` roff source string."""
    section: str | None = None
    name_lines: list[str] = []
    description_lines: list[str] = []
    contact_lines: list[str] = []

    for raw_line in roff.splitlines():
        line = raw_line.rstrip("\r\n")

        if not line:
            continue

        if line.startswith("."):
            parts = line[1:].split(maxsplit=1)
            macro = parts[0] if parts else ""
            arg = parts[1] if len(parts) > 1 else ""

            if macro == "SH":
                section = arg.strip().upper()
                continue
            if macro in {"TH", "TP", "SS", "B", "I", "IP"}:
                # Outside the minimal summary we intentionally ignore these,
                # and within the minimal summary the content arrives on plain lines.
                continue
            if macro == "br":
                # Explicit line break in CONTACT; ignore because we store each content line.
                continue
            continue

        text = _unescape_roff_text(line).strip()
        if not text:
            continue

        if section == "NAME":
            name_lines.append(text)
        elif section == "DESCRIPTION":
            description_lines.append(text)
        elif section == "CONTACT":
            contact_lines.append(text)

    name_line = " ".join(name_lines).strip()
    description = " ".join(description_lines).strip()
    return BradManSummary(
        name_line=name_line,
        description=description,
        contact_lines=tuple(contact_lines),
    )


def render_brad_man_txt(
    summary: BradManSummary,
    *,
    width: int = 66,
) -> str:
    """Render a stable, manpage-style text excerpt for embedding on the landing page."""
    indent = " " * 4
    body_width = max(10, width - len(indent))

    out_lines: list[str] = []

    out_lines.append("DESCRIPTION")
    wrapped = textwrap.wrap(summary.description, width=body_width, break_long_words=False)
    # Don't truncate - show full description
    for line in wrapped:
        out_lines.append(f"{indent}{line}".rstrip())
    out_lines.append("")

    out_lines.append("CONTACT")
    if summary.contact_lines:
        for line in summary.contact_lines:
            out_lines.append(f"{indent}{line}".rstrip())
    else:
        out_lines.append(f"{indent}(none)")
    out_lines.append("")

    return "\n".join(out_lines)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m resume_generator.manpage")
    parser.add_argument("--in", dest="src", required=True, help="Path to brad.1 roff input")
    parser.add_argument("--out", dest="out", required=True, help="Path to output file")
    parser.add_argument(
        "--format",
        choices=["text"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument("--width", type=int, default=66, help="Wrap width (default: 66)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the manpage conversion CLI.

    Args:
        argv: Optional CLI args; defaults to ``sys.argv`` behavior.

    Returns:
        Process exit code.
    """
    args = _parse_args(argv)
    src = Path(args.src)
    out = Path(args.out)

    roff = src.read_text(encoding="utf-8")
    summary = parse_brad_roff_summary(roff)
    rendered = render_brad_man_txt(
        summary,
        width=int(args.width),
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8")
    print(f"Wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
