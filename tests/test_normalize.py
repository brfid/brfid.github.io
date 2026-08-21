from __future__ import annotations

from resume_generator.normalize import to_ascii


def test_to_ascii_substitutes_typographic_chars() -> None:
    assert to_ascii("em—dash") == "em--dash"
    assert to_ascii("en–dash") == "en-dash"
    assert to_ascii("‘left’") == "'left'"
    assert to_ascii("“left”") == '"left"'
    assert to_ascii("…") == "..."
    assert to_ascii(" ") == " "
    assert to_ascii("•") == "*"


def test_to_ascii_passthrough_ascii() -> None:
    text = "hello, world: 123 [test] {ok} #tag"
    assert to_ascii(text) == text


def test_to_ascii_decomposes_accented() -> None:
    # é → NFKD → 'e' (ASCII) + combining acute (non-ASCII → '?')
    # The base letter passes through; the combining mark is replaced.
    assert to_ascii("café") == "cafe?"


def test_to_ascii_output_is_ascii() -> None:
    assert to_ascii("fancy — “quoted” text").isascii()
