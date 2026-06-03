from __future__ import annotations

from pydantic import BaseModel, HttpUrl


class Job(BaseModel):
    source: str
    company: str | None = None
    title: str
    location: str | None = None
    url: HttpUrl
    apply_url: HttpUrl | None = None
    description: str | None = None
    discovered_at: str | None = None
    match_score: float | None = None
    status: str = "discovered"
