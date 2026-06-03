from __future__ import annotations

from auto_job_apply.apply.field_mapper import map_field_label


def test_field_mapper_common_labels() -> None:
    assert map_field_label("First Name") == "profile.first_name"
    assert map_field_label("Email Address") == "profile.email"
    assert map_field_label("Require sponsorship?") == "answer_bank.needs_sponsorship"
