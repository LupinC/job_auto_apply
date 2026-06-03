from __future__ import annotations

from auto_job_apply.models.job import Job


def _canonical_url(url: str) -> str:
    return url.strip().lower().rstrip("/")


def dedupe_jobs(jobs: list[Job]) -> list[Job]:
    seen: set[str] = set()
    output: list[Job] = []
    for job in jobs:
        key_candidates = [
            _canonical_url(str(job.apply_url or job.url)),
            _canonical_url(str(job.url)),
            f"{(job.company or '').strip().lower()}|{job.title.strip().lower()}|{(job.location or '').strip().lower()}",
        ]
        key = next((k for k in key_candidates if k and k != "||"), "")
        if key in seen:
            continue
        seen.add(key)
        output.append(job)
    return output
