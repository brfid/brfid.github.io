from __future__ import annotations

from typing import cast

from resume_generator.normalize import format_date_range, normalize_resume, to_ascii
from resume_generator.types import Resume


def test_format_date_range_present() -> None:
    assert format_date_range("2020-01-01", None) == "Jan 2020 – Present"


def test_format_date_range_both() -> None:
    assert format_date_range("2020-01-01", "2021-02-01") == "Jan 2020 – Feb 2021"


def test_to_ascii_substitutes_typographic_chars() -> None:
    assert to_ascii("em\u2014dash") == "em--dash"
    assert to_ascii("en\u2013dash") == "en-dash"
    assert to_ascii("\u2018left\u2019") == "'left'"
    assert to_ascii("\u201cleft\u201d") == '"left"'
    assert to_ascii("\u2026") == "..."
    assert to_ascii("\u00a0") == " "
    assert to_ascii("\u2022") == "*"


def test_to_ascii_passthrough_ascii() -> None:
    text = "hello, world: 123 [test] {ok} #tag"
    assert to_ascii(text) == text


def test_to_ascii_decomposes_accented() -> None:
    # é → NFKD → 'e' (ASCII) + combining acute (non-ASCII → '?')
    # The base letter passes through; the combining mark is replaced.
    assert to_ascii("caf\u00e9") == "cafe?"


def test_to_ascii_output_is_ascii() -> None:
    assert to_ascii("fancy \u2014 \u201cquoted\u201d text").isascii()


def test_normalize_sorts_work_reverse_chronological() -> None:
    resume = {
        "basics": {"name": "Test"},
        "work": [
            {"company": "Old", "startDate": "2019-01-01", "endDate": "2020-01-01"},
            {"company": "New", "startDate": "2021-01-01", "endDate": "2022-01-01"},
        ],
    }

    view = normalize_resume(cast(Resume, resume))
    assert view["work"][0]["company"] == "New"
    assert "dateRange" in view["work"][0]
