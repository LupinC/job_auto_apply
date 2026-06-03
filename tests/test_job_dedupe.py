from __future__ import annotations

from auto_job_apply.jobs.dedupe import dedupe_jobs
from auto_job_apply.models.job import Job


def test_job_dedupe_by_url() -> None:
    j1 = Job(source="manual", title="Software Engineer II", url="https://example.com/job/1", apply_url="https://example.com/job/1")
    j2 = Job(source="manual", title="Software Engineer II", url="https://example.com/job/1/")

    out = dedupe_jobs([j1, j2])
    assert len(out) == 1
