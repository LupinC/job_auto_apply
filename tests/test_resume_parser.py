from __future__ import annotations

from pathlib import Path

import pytest

from auto_job_apply.errors import ResumeParseError
from auto_job_apply.resume.parser import parse_resume


def test_resume_parser_missing_file_graceful() -> None:
    with pytest.raises(ResumeParseError):
        parse_resume(Path("does_not_exist_resume.pdf"))


def test_profile_extraction_validates_schema(tmp_path: Path) -> None:
    resume = tmp_path / "resume.txt"
    resume.write_text(
        "Jane Doe\n"
        "jane@example.com\n"
        "+1 415-555-1212\n"
        "https://linkedin.com/in/janedoe\n"
        "Python AWS React\n",
        encoding="utf-8",
    )

    profile = parse_resume(resume)
    assert profile.full_name == "Jane Doe"
    assert str(profile.email) == "jane@example.com"
    assert "Python" in profile.skills
