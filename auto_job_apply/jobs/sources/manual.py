from __future__ import annotations

from auto_job_apply.jobs.discovery import discover_from_manual_urls
from auto_job_apply.models.job import Job


def discover_manual_source(title: str, urls: list[str]) -> list[Job]:
    return discover_from_manual_urls(title=title, urls=urls)
