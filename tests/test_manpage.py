from __future__ import annotations

from resume_generator.manpage import parse_brad_roff_summary, render_brad_man_txt


def test_parse_unescapes_name_synopsis() -> None:
    roff = "\n".join(
        [
            '.TH BRAD 1 "2026-01-25" "brfid.github.io" ""',
            ".SH NAME",
            r"brad \\- Senior Engineer",
        ]
    )

    summary = parse_brad_roff_summary(roff)
    assert summary.name_line == "brad - Senior Engineer"


def test_render_wraps_and_truncates_description() -> None:
    roff = "\n".join(
        [
            ".SH NAME",
            "brad - Test",
            ".SH DESCRIPTION",
            " ".join(["word"] * 200),
            ".SH CONTACT",
            "Email: test@example.com",
        ]
    )

    summary = parse_brad_roff_summary(roff)
    rendered = render_brad_man_txt(summary, width=40, max_description_lines=4)

    lines = rendered.splitlines()
    desc_idx = lines.index("DESCRIPTION")
    contact_idx = lines.index("CONTACT")
    desc_lines = [line for line in lines[desc_idx + 1 : contact_idx] if line.strip()]

    assert len(desc_lines) == 4
    assert desc_lines[-1].endswith("...")


def test_contact_ignores_br_macro_and_strips_leading_guard() -> None:
    roff = "\n".join(
        [
            ".SH NAME",
            "brad - Test",
            ".SH DESCRIPTION",
            r"\&.Leading dot stays literal",
            ".SH CONTACT",
            "Email: test@example.com",
            ".br",
            "Web: https://example.com",
            ".br",
            "LinkedIn: https://linkedin.com/in/example",
        ]
    )

    summary = parse_brad_roff_summary(roff)
    assert summary.description.startswith(".Leading dot")
    assert summary.contact_lines == (
        "Email: test@example.com",
        "Web: https://example.com",
        "LinkedIn: https://linkedin.com/in/example",
    )
