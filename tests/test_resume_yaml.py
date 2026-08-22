from pathlib import Path
from typing import Any

import yaml


def _assert_optional_strings(item: dict[str, Any], fields: tuple[str, ...]) -> None:
    for field in fields:
        if field in item:
            assert isinstance(item[field], str), f"{field} must be a string: {item[field]!r}"


def test_resume_human_authored_fields_remain_strings() -> None:
    resume: Any = yaml.safe_load(Path("resume.yaml").read_text(encoding="utf-8"))
    assert isinstance(resume, dict)
    assert set(resume) == {"basics", "work", "volunteer", "education", "publications", "skills"}

    basics = resume["basics"]
    assert isinstance(basics, dict)
    assert "phone" not in basics, "public resume.yaml must not contain a phone number"
    _assert_optional_strings(basics, ("name", "label", "email", "summary"))

    for employer in resume["work"]:
        assert isinstance(employer, dict)
        _assert_optional_strings(employer, ("name", "position", "summary", "location", "url"))
        highlights = employer.get("highlights", [])
        assert isinstance(highlights, list)
        assert all(isinstance(highlight, str) for highlight in highlights)
        for position in employer.get("positions", []):
            assert isinstance(position, dict)
            _assert_optional_strings(position, ("position", "summary"))
            position_highlights = position.get("highlights", [])
            assert isinstance(position_highlights, list)
            assert all(isinstance(highlight, str) for highlight in position_highlights)

    section_fields = {
        "education": ("institution", "area", "studyType"),
        "publications": ("name", "publisher", "summary", "url"),
        "volunteer": ("organization", "summary"),
    }
    for section, fields in section_fields.items():
        for item in resume.get(section, []):
            assert isinstance(item, dict)
            _assert_optional_strings(item, fields)

    for skill in resume.get("skills", []):
        assert isinstance(skill, dict)
        _assert_optional_strings(skill, ("name",))
        keywords = skill.get("keywords", [])
        assert isinstance(keywords, list)
        assert all(isinstance(keyword, str) for keyword in keywords)
