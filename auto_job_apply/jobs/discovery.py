from __future__ import annotations

from auto_job_apply.jobs.normalizer import normalize_manual_job
from auto_job_apply.models.job import Job


def discover_from_manual_urls(title: str, urls: list[str]) -> list[Job]:
    jobs: list[Job] = []
    for raw in urls:
        clean = raw.strip()
        if not clean:
            continue
        jobs.append(normalize_manual_job(url=clean, title=title))
    return jobs
