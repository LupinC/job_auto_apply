from __future__ import annotations

import pytest

from auto_job_apply.models.answers import AnswerEntry
from auto_job_apply.safety.validation import assert_answer_entry_safe


def test_answer_bank_blocks_unapproved_sensitive_reuse() -> None:
    entry = AnswerEntry(value="I do not wish to answer", sensitive=True, user_approved_reuse=False)
    with pytest.raises(ValueError):
        assert_answer_entry_safe("veteran_status", entry)


def test_answer_bank_allows_approved_sensitive_reuse() -> None:
    entry = AnswerEntry(value="I do not wish to answer", sensitive=True, user_approved_reuse=True)
    assert_answer_entry_safe("veteran_status", entry)
