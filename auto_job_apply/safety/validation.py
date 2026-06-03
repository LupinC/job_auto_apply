from __future__ import annotations

from auto_job_apply.constants import SENSITIVE_ANSWER_KEYS
from auto_job_apply.models.answers import AnswerEntry


def assert_answer_entry_safe(key: str, entry: AnswerEntry) -> None:
    if key in SENSITIVE_ANSWER_KEYS and not entry.user_approved_reuse:
        raise ValueError(f"Sensitive answer {key} requires explicit reuse approval")
