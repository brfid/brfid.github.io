from __future__ import annotations

from resume_generator.normalize import format_date_range, normalize_resume


def test_format_date_range_present() -> None:
    assert format_date_range("2020-01-01", None) == "Jan 2020 – Present"


def test_format_date_range_both() -> None:
    assert format_date_range("2020-01-01", "2021-02-01") == "Jan 2020 – Feb 2021"


def test_normalize_sorts_work_reverse_chronological() -> None:
    resume = {
        "basics": {"name": "Test"},
        "work": [
            {"company": "Old", "startDate": "2019-01-01", "endDate": "2020-01-01"},
            {"company": "New", "startDate": "2021-01-01", "endDate": "2022-01-01"},
        ],
    }

    view = normalize_resume(resume)
    assert view["work"][0]["company"] == "New"
    assert "dateRange" in view["work"][0]
