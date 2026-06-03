from __future__ import annotations

from datetime import datetime, UTC

from auto_job_apply.models.job import Job


def normalize_manual_job(url: str, title: str, company: str | None = None, location: str | None = None) -> Job:
    return Job(
        source="manual",
        company=company,
        title=title,
        location=location,
        url=url,
        apply_url=url,
        description=None,
        discovered_at=datetime.now(UTC).isoformat(),
        status="discovered",
    )
