from __future__ import annotations

from auto_job_apply.models.job import Job


def match_score(target_title: str, candidate_title: str) -> float:
    target = target_title.lower().strip()
    candidate = candidate_title.lower().strip()

    if target == candidate:
        return 1.0
    if target in candidate:
        return 0.85

    target_tokens = set(target.split())
    cand_tokens = set(candidate.split())
    overlap = len(target_tokens & cand_tokens)
    if not target_tokens:
        return 0.0
    return overlap / len(target_tokens)


def rank_jobs(jobs: list[Job], target_title: str) -> list[Job]:
    ranked = []
    for job in jobs:
        score = match_score(target_title, job.title)
        ranked.append(job.model_copy(update={"match_score": score}))
    return sorted(ranked, key=lambda j: j.match_score or 0.0, reverse=True)
