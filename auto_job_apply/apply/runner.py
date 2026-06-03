from __future__ import annotations

from datetime import datetime, UTC

from auto_job_apply.models.application import ApplicationAttempt


def build_application_attempt(company: str | None, title: str, url: str, status: str, reason: str | None = None) -> ApplicationAttempt:
    return ApplicationAttempt(
        ts=datetime.now(UTC).isoformat(),
        company=company,
        title=title,
        url=url,
        status=status,
        reason=reason,
    )
