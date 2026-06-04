from __future__ import annotations

from datetime import datetime, UTC

from auto_job_apply.models.application import ApplicationAttempt


def build_application_attempt(
    company: str | None,
    title: str,
    url: str,
    status: str,
    reason: str | None = None,
    resume_path: str | None = None,
    cover_letter_path: str | None = None,
    screenshot_path: str | None = None,
    confirmation_text: str | None = None,
) -> ApplicationAttempt:
    return ApplicationAttempt(
        ts=datetime.now(UTC).isoformat(),
        company=company,
        title=title,
        url=url,
        status=status,
        resume_path=resume_path,
        cover_letter_path=cover_letter_path,
        screenshot_path=screenshot_path,
        reason=reason,
        confirmation_text=confirmation_text,
    )
