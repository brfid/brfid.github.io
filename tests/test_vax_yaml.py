from __future__ import annotations

from datetime import date
from typing import cast

from resume_generator.types import Resume
from resume_generator.vax_yaml import VaxYamlEmitOptions, build_vax_resume_v1, emit_vax_yaml


def test_emit_vax_yaml_uses_double_quotes_and_two_space_indent() -> None:
    resume = {
        "basics": {
            "name": "Test User",
            "label": 'Senior "Dev" \\ Writer',
            "email": "test@example.com",
            "summary": "Line1\nLine2\tLine3",
            "profiles": [{"network": "LinkedIn", "url": "https://linkedin.com/in/test"}],
        },
        "work": [
            {
                "name": "ExampleCo",
                "position": "Engineer",
                "startDate": "2020-01-01",
                "endDate": "2021-02-01",
                "highlights": ["Did things"],
            }
        ],
        "skills": [{"name": "Tools", "keywords": ["Python", "pytest"]}],
    }

    built = build_vax_resume_v1(cast(Resume, resume), build_date=date(2026, 1, 25))
    text = emit_vax_yaml(built)

    assert "\t" not in text
    assert "\r" not in text
    assert 'schemaVersion: "v1"' in text
    assert 'label: "Senior \\"Dev\\" \\\\ Writer"' in text
    assert 'summary: "Line1 Line2 Line3"' in text
    assert "  email: " in text

    # Ensure list indentation is exactly 2 spaces at top level sequences.
    assert "\nwork:\n  -\n    company: " in text


def test_build_limits_work_and_skills() -> None:
    resume = {
        "basics": {"name": "Test", "label": "X", "summary": "Y"},
        "work": [{"name": f"C{i}", "position": "P"} for i in range(10)],
        "skills": [{"name": f"S{i}", "keywords": ["A"]} for i in range(10)],
    }
    opts = VaxYamlEmitOptions(max_work_items=2, max_skill_groups=3)
    built = build_vax_resume_v1(cast(Resume, resume), build_date=date(2026, 1, 25), options=opts)
    assert len(built["work"]) == 2
    assert len(built["skills"]) == 3
