from __future__ import annotations

from auto_job_apply.jobs.matcher import match_score


def test_job_matcher_exact_title_beats_weak_match() -> None:
    exact = match_score("Software Engineer II", "Software Engineer II")
    weak = match_score("Software Engineer II", "Support Technician")
    assert exact > weak
